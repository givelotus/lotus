import test from 'node:test';
import assert from 'node:assert/strict';
import { compileContract, methodLeafHash, contractRootHash } from '../dist/generic.js';
import { unhex } from '../dist/compiler.js';
import { generateContractTypeScript } from '../dist/bindings.js';
import { readFileSync } from 'node:fs';

const key3 = 'f9308a019258c31049344f85f89d5229b531c845836f99b08601f113bce036f9';
const key4 = 'e493dbf1c10d80f3581e4904930b1404cc6c13900ee0758474fa94abe8c4cd13';
const zero = '00'.repeat(32);
const vault = `function digest(x: Bytes32): Bytes32 { return sha256(x); }
contract Vault<owner: PublicKey, expected: Bytes32> {
  function spend(sig: Signature) { require(checksig(sig, owner)); }
  function reveal(data: Bytes32) { require(digest(data) == expected); }
  function claim(sig: Signature, data: Bytes32) {
    if (checksig(sig, owner)) { require(blake3(data) == expected); }
    else { require(hash256(data) == expected); }
  }
}`;
function make(owner = key3) { return compileContract(vault, { contract: 'Vault', bindings: { Vault: { owner, expected: zero } } }); }

test('bound templates change policy and build deterministic sorted method proofs', () => {
  const a = make(), b = make(key4);
  assert.equal(a.schema, 'lotus-v2/contract-artifact/2');
  assert.equal(a.methods.length, 3);
  assert.notEqual(a.policy.root, b.policy.root);
  assert.deepEqual(make(), a);
  assert.deepEqual(a.policy.paths, [[0]]);
  for (const m of a.methods) {
    assert.equal(m.root, a.policy.root);
    assert(m.proof.length >= 1 && m.proof.length <= 2);
    assert(m.staticResources.scriptBytes <= 8192);
    assert.deepEqual(unhex(m.scriptHex).length, m.staticResources.scriptBytes);
  }
  assert.equal(methodLeafHash(a, 'reveal').kind, 'MethodLeafHash');
  assert.equal(contractRootHash(a).kind, 'ContractRootHash');
  assert.match(generateContractTypeScript(a), /prepareSpend\(context: CallContext/);
});

test('pure helper inlining yields same script as direct expression and preserves origin', () => {
  const direct = vault.replace('digest(data) == expected', 'sha256(data) == expected');
  const a = make().methods.find(m => m.name === 'reveal');
  const b = compileContract(direct, { contract: 'Vault', bindings: { Vault: { owner: key3, expected: zero } } }).methods.find(m => m.name === 'reveal');
  assert.equal(a.scriptHex, b.scriptHex);
  assert(a.sourceMap.some(x => x.expandedFrom !== undefined));
  assert(a.sourceMap.every(x => x.byteStart < x.byteEnd));
});

test('UTF-8 source spans, strict template types and reserved names', () => {
  const source = `// café\n${vault}`;
  const a = compileContract(source, { contract: 'Vault', bindings: { Vault: { owner: key3, expected: zero } } });
  assert(a.methods[0].sourceMap[0].source.start > make().methods[0].sourceMap[0].source.start + 8);
  assert.throws(() => compileContract(vault, { contract: 'Vault', bindings: { Vault: { owner: zero, expected: zero } } }), /x-only curve point/);
  assert.throws(() => compileContract(vault, { contract: 'Vault', bindings: { Vault: { owner: key3 } } }), /constructor arity/);
  assert.throws(() => compileContract('contract class { function spend() { require(true); } }', { contract: 'class', bindings: {} }), /reserved name/);
  assert.throws(() => compileContract('contract A { function m(x: Int) { require(sha256(x) == x); } }', { contract: 'A', bindings: {} }), /expects byte/);
});

test('fully bound cross-contract root and method leaf builtins are distinct', () => {
  const source = `contract Target { function one() { require(1 == 1); } function two() { require(2 == 2); } }
contract Verifier<root: ContractRootHash, leaf: MethodLeafHash> {
  function check() { require(contract_root(Target) == root); require(leaf_hash(Target.one) == leaf); }
}`;
  const target = compileContract(source, { contract: 'Target', bindings: {} });
  const verifier = compileContract(source, { contract: 'Verifier', bindings: { Verifier: { root: target.policy.root, leaf: target.methods[0].leaf } } });
  assert(verifier.methods[0].scriptHex.includes(target.policy.root));
  assert(verifier.methods[0].scriptHex.includes(target.methods[0].leaf));
  assert.throws(() => compileContract(source, { contract: 'Verifier', bindings: { Verifier: { root: target.policy.root } } }), /constructor arity/);
});

test('recursive helpers and hash-dependency cycles reject', () => {
  const helper = 'function a(x: Bool): Bool { return b(x); } function b(x: Bool): Bool { return a(x); } contract C { function m() { require(a(true)); } }';
  assert.throws(() => compileContract(helper, { contract: 'C', bindings: {} }), /recursive helper/);
  const self = 'contract C { function m() { require(leaf_hash(C.m) == leaf_hash(C.m)); } }';
  assert.throws(() => compileContract(self, { contract: 'C', bindings: {} }), /dependency cycle/);
  const root = 'contract C { function m() { require(contract_root(C) == contract_root(C)); } }';
  assert.throws(() => compileContract(root, { contract: 'C', bindings: {} }), /dependency cycle/);
  const mutual = 'contract A { function m() { require(contract_root(B) == contract_root(B)); } } contract B { function m() { require(contract_root(A) == contract_root(A)); } }';
  assert.throws(() => compileContract(mutual, { contract: 'A', bindings: {} }), /dependency cycle/);
});

test('unassigned syntax, oversized bytes, invalid argument types and duplicate leaves reject', () => {
  assert.throws(() => compileContract('contract C { function m() { require(OP_SUCCESS); } }', { contract: 'C', bindings: {} }), /unbound name/);
  assert.throws(() => compileContract('contract C<x: Bytes(8193)> { function m() { require(true); } }', { contract: 'C', bindings: {} }), /Bytes bound/);
  assert.throws(() => compileContract('contract C { function a() { require(true); } function b() { require(true); } }', { contract: 'C', bindings: {} }), /duplicate method leaf/);
  assert.throws(() => compileContract('contract C { function m(x: Bytes32) { require(checksig(x, x)); } }', { contract: 'C', bindings: {} }), /checksig expects/);
});

test('emitted builtins use the pinned assigned P03 opcode bytes', () => {
  const registry = JSON.parse(readFileSync(new URL('../../../docs/lotus-v2/tools/opcodes.json', import.meta.url)));
  const assigned = new Map(registry.opcodes.map(x => [x.name, x.byte]));
  assert.equal(assigned.get('SHA256'), 'b8');
  assert.equal(assigned.get('HASH256'), 'b9');
  assert.equal(assigned.get('BLAKE3'), 'ba');
  assert.equal(assigned.get('CHECKSIG'), 'bb');
  assert.equal(assigned.get('EQUAL'), '91');
  const a = make();
  assert(a.methods.some(m => m.sourceMap.some(x => x.op === 'SHA256')));
  assert(a.methods.some(m => m.sourceMap.some(x => x.op === 'HASH256')));
  assert(a.methods.some(m => m.sourceMap.some(x => x.op === 'BLAKE3')));
});

test('helper expansion and parser expression bounds reject unbounded source', () => {
  const terms = Array(257).fill('id(true)').join(' || ');
  const source = `function id(x: Bool): Bool { return x; } contract C { function m() { require(${terms}); } }`;
  assert.throws(() => compileContract(source, { contract: 'C', bindings: {} }), /helper expansion budget/);
  const nested = '('.repeat(66) + 'true' + ')'.repeat(66);
  assert.throws(() => compileContract(`contract C { function m() { require(${nested}); } }`, { contract: 'C', bindings: {} }), /expression depth/);
});
