import test from 'node:test';
import assert from 'node:assert/strict';
import { existsSync } from 'node:fs';
import { join } from 'node:path';
import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { compileContract } from '../dist/generic.js';
import { optimizeInstructions } from '../dist/optimizer.js';

const reference = process.env.LOTUS_V2_REFERENCE_PATH ?? join(import.meta.dirname, '../../lotus-v2-reference');
const available = existsSync(join(reference, 'lotus_v2_reference/vm.py'));

test('optimized and unoptimized scripts agree in independent P03 VM', { skip: !available }, t => {
  const python = process.env.LOTUS_V2_PYTHON ?? 'python3';
  const probe = spawnSync(python, ['-c', 'import blake3, coincurve'], { encoding: 'utf8' });
  if (probe.status !== 0) { t.skip('install reference requirements-vm.txt and set LOTUS_V2_PYTHON'); return; }
  const sources = [
    ['single', 'contract C { function m(x: Bool) { require(x == true); } }'],
    ['reused', 'contract C { function m(x: Bool) { require(x == true); require(x == true); } }'],
    ['verified fact', 'contract C { function m(x: Bool) { require(x); require(x); } }'],
    ['branch', 'contract C { function m(x: Bool) { if (x) { require(true); } else { require(false); } } }'],
    ['overflow', 'contract C { function m(x: Int) { require(x + 1 > 0); } }'],
    ['identity', 'contract C { function m(x: Bytes32) { require(x == x); } }'],
    ['branch facts', 'contract C { function m(flag: Bool, x: Bytes32) { if (flag) { require(flag); require(x == x); } else { require(!flag); require(x == x); } } }'],
    ['loop', 'contract C { function m(x: Bytes32) { for i in tx.inputs { require(x == x); } } }'],
  ];
  const bools = ['00'.repeat(16), '01' + '00'.repeat(15), '02' + '00'.repeat(15)];
  const maxInt = 'ff'.repeat(15) + '7f';
  const fixtures = [];
  for (const [name, source] of sources) {
    const options = { contract: 'C', bindings: {} };
    const before = compileContract(source, { ...options, optimize: false }).methods[0].scriptHex;
    const after = compileContract(source, options).methods[0].scriptHex;
    if (name === 'identity') assert.ok(after.length < before.length, 'symbolic identity must reduce script bytes');
    if (name === 'branch facts') assert.ok(after.length < before.length, 'branch facts must reduce script bytes');
    if (name === 'loop') assert.ok(after.length < before.length, 'loop body must be optimized recursively');
    const inputs = name === 'overflow' ? ['00'.repeat(16), '01' + '00'.repeat(15), maxInt] :
      name === 'identity' || name === 'loop' ? ['00'.repeat(32), 'ab'.repeat(32)] : bools;
    for (const arg of inputs) {
      const args = name === 'branch facts' ? [arg, 'ab'.repeat(32)] : [arg];
      const expected = name === 'overflow' ? (arg === maxInt ? 'error' : 'ok') :
        name === 'branch facts' ? (arg === bools[2] ? 'error' : 'ok') :
        name === 'identity' || name === 'loop' ? 'ok' :
        (arg === bools[1] ? 'ok' : 'error');
      fixtures.push({ name: `${name}:${arg.slice(0, 4)}`, before, after, args, expected,
        ...(name === 'loop' ? { input_count: 2 } : {}) });
    }
  }
  const constant = 'contract C { function m(x: Bool) { require((1 + 2) * (3 + 4) == 21); require(x); } }';
  const constantOptions = { contract: 'C', bindings: {} };
  const constantBefore = compileContract(constant, { ...constantOptions, optimize: false }).methods[0].scriptHex;
  const constantAfter = compileContract(constant, constantOptions).methods[0].scriptHex;
  for (const [arg, expected] of [[bools[1], 'ok'], [bools[0], 'error']])
    fixtures.push({ name: `constant arithmetic:${expected}`, before: constantBefore, after: constantAfter, args: [arg], expected });
  const max = (1n << 127n) - 1n;
  const overflowLiteral = `contract C { function m() { require(${max} + 1 > 0); } }`;
  fixtures.push({ name: 'constant overflow retained',
    before: compileContract(overflowLiteral, { contract: 'C', bindings: {}, optimize: false }).methods[0].scriptHex,
    after: compileContract(overflowLiteral, { contract: 'C', bindings: {} }).methods[0].scriptHex,
    args: [], expected: 'error' });
  const boundHash = 'contract H<x: Bytes32, expected: Bytes32> { function m() { require(sha256(x) == expected); } }';
  const raw = Buffer.alloc(32), digest = createHash('sha256').update(raw).digest('hex');
  const hashOptions = { contract: 'H', bindings: { H: { x: raw.toString('hex'), expected: digest } } };
  fixtures.push({ name: 'bound hash preserves equality',
    before: compileContract(boundHash, { ...hashOptions, optimize: false }).methods[0].scriptHex,
    after: compileContract(boundHash, hashOptions).methods[0].scriptHex,
    args: [], expected: 'ok' });
  const payment = 'contract Payment<owner: PublicKey> { function spend(sig: Signature) { require(checksig(sig, owner)); } }';
  const paymentOptions = { contract: 'Payment', bindings: { Payment: { owner: 'f9308a019258c31049344f85f89d5229b531c845836f99b08601f113bce036f9' } } };
  const paymentBefore = compileContract(payment, { ...paymentOptions, optimize: false }).methods[0].scriptHex;
  const paymentAfter = compileContract(payment, paymentOptions).methods[0].scriptHex;
  const validSignature = 'e907831f80848d1069a5371b402410364bdf1c5f8307b0084c55f1ce2dca8215' +
    '25f66a4a85ea8b71e482a74f382d2ce5ebeee8fdb2172f477df4900d310536c0';
  for (const [name, signature, expected] of [
    ['valid signature', validSignature, 'ok'],
    ['invalid signature', '00' + validSignature.slice(2), 'error'],
    ['invalid signature length', '', 'error'],
  ]) fixtures.push({ name, before: paymentBefore, after: paymentAfter, args: [signature], signing: true, expected });
  const run = spawnSync(python, [new URL('./optimizer-vm.py', import.meta.url).pathname], {
    encoding: 'utf8', input: JSON.stringify(fixtures),
    env: { ...process.env, PYTHONPATH: [reference, process.env.PYTHONPATH].filter(Boolean).join(':') },
  });
  assert.equal(run.status, 0, run.stderr || run.stdout);
  assert.match(run.stdout, /differential passed/);
});

test('symbolic optimizer reaches an idempotent bounded fixed point', () => {
  const source = 'contract C { function m(flag: Bool, x: Bytes32) { if (flag) { require(flag); require(x == x); } else { require(!flag); require(x == x); } } }';
  const method = compileContract(source, { contract: 'C', bindings: {} }).methods[0];
  const bytes = Buffer.from(method.scriptHex, 'hex');
  const delta = new Map([['PICK', 0], ['IF', -1], ['ELSE', 0], ['ENDIF', 0], ['DROP', -1]]);
  const entries = method.sourceMap.map(map => ({ wire: bytes.subarray(map.byteStart, map.byteEnd), map,
    delta: delta.get(map.op) ?? 1, foldable: map.op.startsWith('N(') || map.op === 'ZERO' }));
  const again = optimizeInstructions(entries, 2);
  assert.deepEqual(again.map(x => [...x.wire]), entries.map(x => [...x.wire]));
});
