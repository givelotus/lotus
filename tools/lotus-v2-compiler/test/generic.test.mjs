import test from 'node:test';
import assert from 'node:assert/strict';
import { compileContract, methodLeafHash, contractRootHash } from '../dist/generic.js';
import { unhex } from '../dist/compiler.js';
import { generateContractPython, generateContractTypeScript } from '../dist/bindings.js';
import { readFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';

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

// Test-only stack model for the Payment lowering; this is not a P03 VM.
function runPayment(scriptHex, signatureValid) {
  const script = unhex(scriptHex), stack = [new Uint8Array(64)];
  for (let pc = 0; pc < script.length;) {
    const op = script[pc++];
    if (op === 0) stack.push(new Uint8Array());
    else if (op === 0x20) { stack.push(script.slice(pc, pc + 32)); pc += 32; }
    else if (op === 0x7d) { const depth = stack.pop()?.[0] ?? 0; stack.push(stack[stack.length - depth - 1]); }
    else if (op === 0xbb || op === 0xbc) {
      stack.pop(); stack.pop();
      if (op === 0xbb) stack.push(Uint8Array.of(signatureValid ? 1 : 0));
      else if (!signatureValid) throw new Error('CHECKSIGVERIFY');
    } else if (op === 0x65) { if (stack.pop()?.[0] !== 1) throw new Error('VERIFY'); }
    else if (op === 0x79) stack.pop();
    else if (op === 0x4e) stack.push(Uint8Array.of(1));
    else throw new Error(`unsupported test opcode ${op}`);
  }
  return stack.map(x => Buffer.from(x).toString('hex'));
}

test('optimized Payment consumes its sole argument and fuses CHECKSIGVERIFY', () => {
  const source = 'contract Payment<owner: PublicKey> { function spend(sig: Signature) { require(checksig(sig, owner)); } }';
  const opts = { contract: 'Payment', bindings: { Payment: { owner: key3 } } };
  const plain = compileContract(source, { ...opts, optimize: false }).methods[0];
  const optimized = compileContract(source, opts).methods[0];
  assert.equal(plain.scriptHex, `007d20${key3}bb65794e`);
  assert.equal(optimized.scriptHex, `20${key3}bc4e`);
  assert.deepEqual(runPayment(plain.scriptHex, true), ['01']);
  assert.deepEqual(runPayment(optimized.scriptHex, true), ['01']);
  assert.throws(() => runPayment(plain.scriptHex, false), /VERIFY/);
  assert.throws(() => runPayment(optimized.scriptHex, false), /CHECKSIGVERIFY/);
  assert.equal(plain.staticResources.scriptBytes - optimized.staticResources.scriptBytes, 4);
  assert.equal(plain.staticResources.opcodes - optimized.staticResources.opcodes, 4);
  assert.equal(optimized.staticResources.maxStackItems, 2);
  assert.deepEqual(optimized.sourceMap.map(x => x.op), ['PUSH_32', 'CHECKSIGVERIFY', 'N(1)']);
  assert.deepEqual(optimized.sourceMap[1].optimizedFrom.map(x => x.op), ['CHECKSIG', 'VERIFY']);
  assert.deepEqual(optimized.sourceMap.map(x => [x.byteStart, x.byteEnd]), [[0, 33], [33, 34], [34, 35]]);
});

test('argument reuse and control flow retain copies while safe checksig fusion applies', () => {
  const source = `contract C<owner: PublicKey> {
    function reused(sig: Signature) { require(checksig(sig, owner)); require(checksig(sig, owner)); }
    function branched(sig: Signature) { if (checksig(sig, owner)) { require(true); } else { require(true); } }
  }`;
  const opts = { contract: 'C', bindings: { C: { owner: key3 } } };
  const normal = compileContract(source, { ...opts, optimize: false });
  const optimized = compileContract(source, opts);
  for (const method of optimized.methods) {
    const prior = normal.methods.find(x => x.name === method.name);
    assert.equal((method.scriptHex.match(/007d/g) ?? []).length, (prior.scriptHex.match(/007d/g) ?? []).length);
    assert.equal(method.scriptHex, prior.scriptHex.replaceAll('bb65', 'bc'));
    assert.equal(method.staticResources.scriptBytes, method.scriptHex.length / 2);
    assert.equal(method.sourceMap.at(-1).byteEnd, method.staticResources.scriptBytes);
  }
  assert.equal(optimized.methods.find(x => x.name === 'reused').sourceMap.filter(x => x.op === 'CHECKSIGVERIFY').length, 2);
});

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
  assert.throws(() => compileContract('contract class { function spend() { require(true); } }', { contract: 'class', bindings: {} }), /reserved/);
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

test('type inference visits are bounded before substitution fanout', () => {
  const helpers = ['function f0(x: Bool): Bool { return x; }'];
  for (let i = 1; i <= 14; i++) helpers.push(`function f${i}(x: Bool): Bool { return f${i-1}(x) && f${i-1}(x); }`);
  const source = `${helpers.join(' ')} contract C { function m() { require(f14(true)); } }`;
  assert.throws(() => compileContract(source, { contract: 'C', bindings: {} }), /helper expansion budget/);
  const balanced = n => n === 1 ? 'true' : `(${balanced(Math.floor(n / 2))} || ${balanced(Math.ceil(n / 2))})`;
  const large = `function id(x: Bool): Bool { return x; } contract C { function m() { require(id(${balanced(4200)})); } }`;
  assert.throws(() => compileContract(large, { contract: 'C', bindings: {} }), /type inference visit budget/);
});

test('signed Int minimum parses as one literal and out-of-range values reject', () => {
  const min = -(1n << 127n);
  const source = `contract C { function m() { require(${min} == ${min}); } }`;
  const a = compileContract(source, { contract: 'C', bindings: {} });
  assert(a.methods[0].scriptHex.includes('00'.repeat(15) + '80'));
  const underflow = min - 1n;
  assert.throws(() => compileContract(`contract C { function m() { require(${underflow} == 0); } }`, { contract: 'C', bindings: {} }), /signed 128-bit range/);
  const overflow = 1n << 127n;
  assert.throws(() => compileContract(`contract C { function m() { require(${overflow} == 0); } }`, { contract: 'C', bindings: {} }), /signed 128-bit range/);
});

test('portable identifiers and case-folded method entrypoints avoid generated binding collisions', () => {
  for (const name of ['await','lambda','class']) {
    assert.throws(() => compileContract(`contract ${name} { function spend() { require(true); } }`, { contract:name,bindings:{} }), /reserved/);
  }
  assert.throws(() => compileContract('contract C { function spend() { require(true); } function Spend() { require(false); } }', { contract:'C',bindings:{} }), /duplicate method/);
  const a = make();
  const python = generateContractPython(a);
  const run = spawnSync('python3',['-c','import sys; compile(sys.stdin.read(), "generated.py", "exec")'],{input:python,encoding:'utf8'});
  assert.equal(run.status,0,run.stderr);
  assert.match(python,/def prepareSpend\(/);
});
