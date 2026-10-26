import test from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { schnorr } from '@noble/curves/secp256k1';
import { bytes, concat, hex, tagged, unhex } from '../dist/compiler.js';
import { encodeCallValue, finalizeContractCall, methodRoot, prepareContractCall } from '../dist/call-runtime.js';

const key3 = schnorr.getPublicKey(unhex('00'.repeat(31) + '03'));
const key4 = schnorr.getPublicKey(unhex('00'.repeat(31) + '04'));
const scripts = [key3, key4].map(k => `20${hex(k)}bb`);
const leaves = scripts.map(s => hex(tagged('branch', concat(Uint8Array.of(0), bytes(unhex(s))))));
const root = methodRoot(scripts[0], [leaves[1]]);
const artifact = { schema: 'lotus-v2/contract-artifact/2', target: 'P01-P02-P03-candidate-2026-10-14', contract: 'TwoKeys',
  constructor: [], bindings: [],
  methods: scripts.map((scriptHex, i) => ({ name: `spend${i}`, args: [{ name: 'signature', type: 'Signature' }], scriptHex,
    leaf: leaves[i], proof: [leaves[1-i]], root })),
  policy: { branches: [root], paths: [[0]], root, treeRecipe: 'sorted-leaves-largest-power-split-v1' } };
const output = { value: 1000n, branches: [root], paths: [[0]] };
const context = { profile: artifact.target, chainId: '44'.repeat(32), prevTxid: '11'.repeat(32), prevIndex: 0,
  sequence: 0xffffffff, coin: { ...output, value: 2000n }, outputs: [output] };

test('two methods select distinct P02 leaves and P01 signing messages', () => {
  const plans = [0, 1].map(i => prepareContractCall(artifact, `spend${i}`, context, { signature: null }));
  assert.notEqual(plans[0].txid, plans[1].txid);
  assert.notEqual(plans[0].requests[0].digest, plans[1].requests[0].digest);
  assert.deepEqual(plans.map(p => p.requests[0].leaf), leaves);
  for (const [i, plan] of plans.entries()) {
    const sig = schnorr.sign(unhex(plan.requests[0].digest), unhex('00'.repeat(31) + `0${i+3}`), new Uint8Array(32));
    const complete = finalizeContractCall(plan, { signature: sig });
    assert.equal(complete.txid, plan.txid);
    assert.notEqual(complete.txhash, plan.txid);
    assert.equal(complete.stages.signature, 'unavailable');
  }
});

test('proof, policy, stale output and chain mutations reject', () => {
  assert.throws(() => prepareContractCall({ ...artifact, methods: [{ ...artifact.methods[0], proof: ['00'.repeat(32)] }, artifact.methods[1]] }, 'spend0', context, { signature: null }), /proof or root mismatch/);
  assert.throws(() => prepareContractCall(artifact, 'spend0', { ...context, coin: { ...context.coin, branches: [leaves[0]] } }, { signature: null }), /policy mismatch/);
  assert.throws(() => prepareContractCall({ ...artifact, constructor: [{ name: 'n', type: 'Int' }], bindings: [{ name: 'n', type: 'Int', value: '01' }] }, 'spend0', context, { signature: null }), /noncanonical Int binding/);
  const plan = prepareContractCall(artifact, 'spend0', context, { signature: null });
  context.outputs[0].value = 999n;
  assert.throws(() => finalizeContractCall(plan, { signature: new Uint8Array(64) }), /stale signing plan/);
  context.outputs[0].value = 1000n;
  context.chainId = '45'.repeat(32);
  assert.throws(() => finalizeContractCall(plan, { signature: new Uint8Array(64) }), /stale signing plan/);
  context.chainId = '44'.repeat(32);
});

test('typed values have exact P03 widths and FULL-only signature slots', () => {
  assert.equal(hex(encodeCallValue('Int', -1n)), 'ff'.repeat(16));
  assert.equal(hex(encodeCallValue('Bool', true)), '01' + '00'.repeat(15));
  assert.throws(() => encodeCallValue('Int', 2 ** 53), /int128 range/);
  assert.throws(() => encodeCallValue('Bool', 1n), /Bool required/);
  assert.throws(() => encodeCallValue('Signature', new Uint8Array(65)), /FULL signature/);
  assert.equal(encodeCallValue('Bytes(3)', new Uint8Array(2)).length, 2);
  assert.throws(() => encodeCallValue('Bytes(3)', new Uint8Array(4)), /length/);
  assert.throws(() => encodeCallValue('MethodLeafHash', new Uint8Array(31)), /length/);
  const plan = prepareContractCall(artifact, 'spend0', context, { signature: null });
  assert.throws(() => finalizeContractCall(plan, { signature: new Uint8Array(65) }), /FULL signature/);
  assert.throws(() => finalizeContractCall(plan, {}), /signature slots mismatch/);
});

test('maintained Python runtime reproduces both method wires, IDs and selectors', t => {
  const python = process.env.LOTUS_V2_PYTHON ?? 'python3';
  const probe = spawnSync(python, ['-c', 'import blake3'], { encoding: 'utf8' });
  if (probe.status !== 0) { t.skip('install python/requirements.txt and set LOTUS_V2_PYTHON'); return; }
  for (let i = 0; i < 2; i++) {
    const plan = prepareContractCall(artifact, `spend${i}`, context, { signature: null });
    const signature = schnorr.sign(unhex(plan.requests[0].digest), unhex('00'.repeat(31) + `0${i+3}`), new Uint8Array(32));
    const final = finalizeContractCall(plan, { signature });
    const payload = { artifact, method: `spend${i}`, signature: hex(signature), context: { ...context,
      coin: { ...context.coin, value: context.coin.value.toString() },
      outputs: context.outputs.map(x => ({ ...x, value: x.value.toString() })) } };
    const run = spawnSync(python, ['test/python-call-run.py'], { input: JSON.stringify(payload), encoding: 'utf8' });
    assert.equal(run.status, 0, run.stderr);
    const actual = JSON.parse(run.stdout);
    assert.deepEqual(actual, { wire: hex(final.wire), txid: final.txid, txhash: final.txhash,
      digest: plan.requests[0].digest, leaf: plan.requests[0].leaf });
  }
});
