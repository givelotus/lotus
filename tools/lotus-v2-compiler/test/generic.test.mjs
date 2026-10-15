import test from 'node:test';
import assert from 'node:assert/strict';
import { compileContract, methodLeafHash, contractRootHash } from '../dist/generic.js';
import { unhex } from '../dist/compiler.js';
import { schnorr } from '@noble/curves/secp256k1';
import { generateContractPython, generateContractTypeScript } from '../dist/bindings.js';
import { optimizeInstructions } from '../dist/optimizer.js';
import { CompileError } from '../dist/diagnostics.js';
import { readFileSync, existsSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { join } from 'node:path';

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
    assert.equal(method.scriptHex, prior.scriptHex.replaceAll('007d', '7a').replaceAll('bb65', 'bc').replaceAll('4e65', ''));
    assert.equal(method.staticResources.scriptBytes, method.scriptHex.length / 2);
    assert.equal(method.sourceMap.at(-1).byteEnd, method.staticResources.scriptBytes);
  }
  assert.equal(optimized.methods.find(x => x.name === 'reused').sourceMap.filter(x => x.op === 'CHECKSIGVERIFY').length, 2);
});

test('loop and unknown opcodes block argument last-use removal', () => {
  const span = { start: 0, end: 1 };
  const entry = (op, byte, delta) => ({ wire: Uint8Array.of(byte), map: { op, source: span, byteStart: 0, byteEnd: 1 }, delta });
  for (const [op, byte] of [['ENUMERATE_OUTPUTS', 0x68], ['ENUMERATE_INPUTS', 0x67], ['FUTURE_CONTROL', 0xf0]]) {
    const source = [entry('ZERO',0,1), entry('PICK',0x7d,0), entry(op,byte,0),
      entry('DROP',0x79,-1), entry('N(1)',0x4e,1)];
    const optimized = optimizeInstructions(source,1);
    assert(optimized.some(x => x.map.op === 'DROP'));
    assert(optimized.some(x => x.map.op === op));
  }
});

test('bounded symbolic pass folds literal arithmetic and hashes without erasing bindings or errors', () => {
  const arithmetic = 'contract C { function m(x: Bool) { require((1 + 2) * (3 + 4) == 21); require(x); } }';
  const options = { contract: 'C', bindings: {} };
  const plain = compileContract(arithmetic, { ...options, optimize: false }).methods[0];
  const fast = compileContract(arithmetic, options).methods[0];
  assert(fast.staticResources.opcodes < plain.staticResources.opcodes);
  assert.equal(fast.sourceMap.some(x => ['ADD','MUL','EQUALVERIFY'].includes(x.op)), false);
  assert.equal(fast.sourceMap.at(-1).byteEnd, fast.staticResources.scriptBytes);

  const boundHash = 'contract H<x: Bytes32, expected: Bytes32> { function m() { require(sha256(x) == expected); } }';
  const a = compileContract(boundHash, { contract: 'H', bindings: { H: { x: '00'.repeat(32), expected: zero } } });
  const b = compileContract(boundHash, { contract: 'H', bindings: { H: { x: '01'.repeat(32), expected: zero } } });
  assert.notEqual(a.methods[0].scriptHex, b.methods[0].scriptHex);
  assert.equal(a.methods[0].sourceMap.some(x => x.op === 'SHA256'), false);
  assert(a.methods[0].scriptHex.includes(zero));

  const max = (1n << 127n) - 1n;
  const failing = `contract C { function m() { require(${max} + 1 > 0); } }`;
  assert(compileContract(failing, { contract: 'C', bindings: {} }).methods[0].sourceMap.some(x => x.op === 'ADD'));
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
  const source = `contract Target { function one(x: Bool) { require(x); } function two(x: Bool) { require(!x); } }
contract Verifier<root: ContractRootHash, leaf: MethodLeafHash> {
  function check() { require(contract_root(Target) == root); require(leaf_hash(Target.one) == leaf); }
}`;
  const target = compileContract(source, { contract: 'Target', bindings: {} });
  const verifier = compileContract(source, { contract: 'Verifier', bindings: { Verifier: { root: target.policy.root, leaf: target.methods[0].leaf } } });
  assert(verifier.methods[0].scriptHex.includes(target.policy.root));
  assert(verifier.methods[0].scriptHex.includes(target.methods[0].leaf));
  const mismatched = compileContract(source, { contract: 'Verifier', bindings: { Verifier: { root: zero, leaf: target.methods[0].leaf } } });
  assert.notEqual(verifier.methods[0].scriptHex, mismatched.methods[0].scriptHex);
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
  const a = compileContract(source, { contract: 'C', bindings: {}, optimize: false });
  assert(a.methods[0].scriptHex.includes('00'.repeat(15) + '80'));
  assert(compileContract(source, { contract: 'C', bindings: {} }).methods[0].scriptHex.length < a.methods[0].scriptHex.length);
  const underflow = min - 1n;
  assert.throws(() => compileContract(`contract C { function m() { require(${underflow} == 0); } }`, { contract: 'C', bindings: {} }), /signed 128-bit range/);
  const overflow = 1n << 127n;
  assert.throws(() => compileContract(`contract C { function m() { require(${overflow} == 0); } }`, { contract: 'C', bindings: {} }), /signed 128-bit range/);
});

test('a single-return helper matches the direct expression and statement helpers inline', () => {
  const bindings = { C: { owner: key3, other: key4 } };
  const via = `function id(x: Bytes32): Bytes32 { return sha256(x); }
    contract C<owner: PublicKey, other: PublicKey> { function m(x: Bytes32) { require(id(x) == id(x)); } }`;
  const direct = `contract C<owner: PublicKey, other: PublicKey> { function m(x: Bytes32) { require(sha256(x) == sha256(x)); } }`;
  assert.equal(compileContract(via, { contract: 'C', bindings }).methods[0].scriptHex,
    compileContract(direct, { contract: 'C', bindings }).methods[0].scriptHex);
  const source = `function authorized(sig: Signature, owner: PublicKey): Bool {
      let ok: Bool = checksig(sig, owner);
      require(ok);
      return ok;
    }
    contract C<owner: PublicKey, other: PublicKey> {
      function spend(sig: Signature) { require(authorized(sig, owner)); }
    }`;
  const plain = compileContract(source, { contract: 'C', bindings, optimize: false }).methods[0];
  const optimized = compileContract(source, { contract: 'C', bindings }).methods[0];
  assert.equal(plain.staticResources.helperExpansions, 1);
  assert.equal(plain.scriptHex, `007d20${key3}bb007d65007d4e7e7965794e`);
  assert.equal(optimized.scriptHex.includes(key3), true);
  assert.ok(plain.sourceMap.some(entry => entry.op === 'CHECKSIG' && entry.expandedFrom));
  assert.equal(plain.sourceMap.some(entry => entry.op === 'IF'), false);
  const ops = optimized.sourceMap.map(entry => entry.op);
  assert.ok(ops.includes('CHECKSIG') || ops.includes('CHECKSIGVERIFY'));
  assert.equal(ops.includes('ROLL') || ops.includes('DUP'), true);
});

test('errors inside a statement helper point at the helper and note the call', () => {
  const source = `function gate(x: Int): Bool {\n  let ok: Bool = missing;\n  return ok;\n}\ncontract C { function m() { require(gate(1)); } }`;
  const error = (() => { try { compileContract(source, { contract: 'C', bindings: {} }); } catch (caught) { return caught; } })();
  assert.ok(error instanceof CompileError);
  assert.equal(error.diagnostics[0].code, 'E0301');
  assert.equal(error.diagnostics[0].primary.span.start, source.indexOf('missing'));
  assert.equal(error.diagnostics[0].related[0].message, 'in expansion of helper gate called here');
  const mismatch = `function gate(x: Int): Bool {\n  let ok: Bool = x;\n  return true;\n}\ncontract C { function m() { require(gate(1)); } }`;
  assert.throws(() => compileContract(mismatch, { contract: 'C', bindings: {} }), /let ok expects Bool, got Int/);
  const shadowed = 'function f(x: Int): Int { let x: Int = 1; return x; } contract C { function m() { require(f(1) == 1); } }';
  assert.throws(() => compileContract(shadowed, { contract: 'C', bindings: {} }), /let x shadows a binding/);
  const loop = 'function f(): Bool { for i in tx.inputs { require(true); } return true; } contract C { function m() { require(f()); } }';
  const rejected = (() => { try { compileContract(loop, { contract: 'C', bindings: {} }); } catch (caught) { return caught; } })();
  assert.ok(rejected instanceof CompileError);
  assert.equal(rejected.diagnostics[0].code, 'E0122');
  assert.equal(rejected.diagnostics[0].primary.span.start, loop.indexOf('for'));
  assert.equal(rejected.diagnostics[0].primary.span.end, loop.indexOf('for') + 3);
  assert.throws(() => compileContract('function f(): Bool { return true; require(false); } contract C { function m() { require(f()); } }', { contract: 'C', bindings: {} }), /statement after return/);
  assert.throws(() => compileContract('function f(x: Bool): Bool { if (x) { return true; } else { return false; } } contract C { function m(x: Bool) { require(f(x)); } }', { contract: 'C', bindings: {} }), /return must be the final statement/);
  assert.throws(() => compileContract('function f(): Bool { require(true); } contract C { function m() { require(f()); } }', { contract: 'C', bindings: {} }), /helper must end with return/);
  const branched = `function pick(flag: Bool): Bool { if (flag) { require(true); } else { require(false); } return true; }
    contract C { function m(flag: Bool) { require(pick(flag)); } }`;
  const branchedOps = compileContract(branched, { contract: 'C', bindings: {}, optimize: false }).methods[0].sourceMap.map(entry => entry.op);
  assert.ok(branchedOps.includes('IF') && branchedOps.includes('ELSE') && branchedOps.includes('ENDIF'));
  assert.throws(() => compileContract('function a(x: Bool): Bool { let y: Bool = b(x); return y; } function b(x: Bool): Bool { let y: Bool = a(x); return y; } contract C { function m() { require(a(true)); } }', { contract: 'C', bindings: {} }), /recursive helper/);
});

test('require of && becomes one verifying conjunct and || stays short-circuit', t => {
  const source = `contract Pay<a: PublicKey, b: PublicKey> {
    function spend(s: Signature, t: Signature) { require(checksig(s, a) && checksig(t, b)); }
    function either(s: Signature, t: Signature) { require(checksig(s, a) || checksig(t, b)); }
    function nested(s: Signature, t: Signature, u: Signature) { require((checksig(s, a) && checksig(t, b)) && checksig(u, a)); }
    function single(s: Signature) { require(checksig(s, a)); }
  }`;
  const bindings = { Pay: { a: key3, b: key4 } };
  const plain = compileContract(source, { contract: 'Pay', bindings, optimize: false });
  const optimized = compileContract(source, { contract: 'Pay', bindings });
  const ops = (artifact, name) => artifact.methods.find(method => method.name === name).sourceMap.map(entry => entry.op);
  assert.deepEqual(ops(plain, 'spend'), ['N(1)', 'PICK', 'PUSH_32', 'CHECKSIG', 'VERIFY', 'ZERO', 'PICK', 'PUSH_32', 'CHECKSIG', 'VERIFY', 'DROP', 'DROP', 'N(1)']);
  assert.deepEqual(ops(optimized, 'spend'), ['N(1)', 'PICK', 'PUSH_32', 'CHECKSIGVERIFY', 'DUP', 'PUSH_32', 'CHECKSIGVERIFY', 'DROP', 'DROP', 'N(1)']);
  assert.equal(ops(plain, 'spend').includes('IF'), false);
  assert.deepEqual(ops(optimized, 'nested').filter(op => op === 'CHECKSIGVERIFY'), ['CHECKSIGVERIFY', 'CHECKSIGVERIFY', 'CHECKSIGVERIFY']);
  assert.equal(ops(optimized, 'nested').includes('IF'), false);
  assert.deepEqual(ops(optimized, 'single'), ['PUSH_32', 'CHECKSIGVERIFY', 'N(1)']);
  assert.ok(ops(plain, 'either').includes('IF') && ops(optimized, 'either').includes('IF'));
  assert.equal(ops(optimized, 'either').includes('CHECKSIGVERIFY'), false);
  const sign = secret => Buffer.from(schnorr.sign(new Uint8Array(32), unhex(`00`.repeat(31) + secret), new Uint8Array(32))).toString('hex');
  const valid = sign('03'), other = sign('04');
  const reference = process.env.LOTUS_V2_REFERENCE_PATH ?? join(import.meta.dirname, '../../lotus-v2-reference');
  const python = process.env.LOTUS_V2_PYTHON ?? 'python3';
  const vmReady = existsSync(join(reference, 'lotus_v2_reference/vm.py')) &&
    spawnSync(python, ['-c', 'import blake3, coincurve'], { encoding: 'utf8' }).status === 0;
  if (!vmReady) {
    t.diagnostic('reference VM was not run');
    return;
  }
  const sameBindings = { Pay: { a: key3, b: key3 } };
  const samePlain = compileContract(source, { contract: 'Pay', bindings: sameBindings, optimize: false }).methods.find(method => method.name === 'spend').scriptHex;
  const sameOptimized = compileContract(source, { contract: 'Pay', bindings: sameBindings }).methods.find(method => method.name === 'spend').scriptHex;
  const spendBefore = plain.methods.find(method => method.name === 'spend').scriptHex;
  const spendAfter = optimized.methods.find(method => method.name === 'spend').scriptHex;
  const helper = `function authorized(sig: Signature, owner: PublicKey): Bool {
      let ok: Bool = checksig(sig, owner);
      require(ok);
      return ok;
    }
    contract H<owner: PublicKey> { function spend(sig: Signature) { require(authorized(sig, owner)); } }`;
  const helperOptions = { contract: 'H', bindings: { H: { owner: key3 } } };
  const helperBefore = compileContract(helper, { ...helperOptions, optimize: false }).methods[0].scriptHex;
  const helperAfter = compileContract(helper, helperOptions).methods[0].scriptHex;
  const fixtures = [
    { name: 'both signatures valid', before: samePlain, after: sameOptimized, args: [valid, valid], signing: true, expected: 'ok' },
    { name: 'first signature invalid', before: samePlain, after: sameOptimized, args: ['00' + valid.slice(2), valid], signing: true, expected: 'error' },
    { name: 'distinct keys accept', before: spendBefore, after: spendAfter, args: [valid, other], signing: true, expected: 'ok' },
    { name: 'second signature rejects', before: spendBefore, after: spendAfter, args: [valid, valid], signing: true, expected: 'error' },
    { name: 'let helper accepts', before: helperBefore, after: helperAfter, args: [valid], signing: true, expected: 'ok' },
    { name: 'let helper rejects', before: helperBefore, after: helperAfter, args: ['00' + valid.slice(2)], signing: true, expected: 'error' },
  ];
  const run = spawnSync(python, [new URL('./optimizer-vm.py', import.meta.url).pathname], {
    encoding: 'utf8', input: JSON.stringify(fixtures),
    env: { ...process.env, PYTHONPATH: [reference, process.env.PYTHONPATH].filter(Boolean).join(':') },
  });
  assert.equal(run.status, 0, run.stderr || run.stdout);
  assert.match(run.stdout, /differential passed/);
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
