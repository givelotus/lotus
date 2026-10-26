import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { schnorr } from '@noble/curves/secp256k1';
import { compilePayment, PAYMENT_SOURCE, hex, unhex } from '../dist/compiler.js';
import { preparePayment, finalizePayment, encodeOutput } from '../dist/runtime.js';

const reference = JSON.parse(readFileSync(new URL('../fixtures/reference-signed-payment-v1.json', import.meta.url)));
const artifact = compilePayment(PAYMENT_SOURCE, reference.public_key);
const output = { value: 1000n, branches: artifact.policy.branches, paths: [[0]] };
const context = { profile: 'payment-fixture-p01-v1', chainId: reference.chain_id, prevTxid: '11'.repeat(32), prevIndex: 0, sequence: 0xffffffff, coin: { ...output, value: 2000n }, outputs: [output] };

test('typed Payment source compiles to exact P03 script and P02 branch', () => {
  assert.equal(artifact.scriptHex, `20${reference.public_key}bb`);
  assert.equal(artifact.policy.branches[0], reference.resolved_coin.slice(20, 84));
  assert.deepEqual(artifact.sourceMap.map(x => [x.byteStart, x.byteEnd]), [[0, 33], [33, 34]]);
  assert.equal(hex(encodeOutput(context.coin)), reference.resolved_coin);
  assert.equal(artifact.methods[0].args[0].type, 'Signature');
});

test('generated payment call matches independent signed reference byte-for-byte', () => {
  const plan = preparePayment(artifact, context);
  assert.equal(plan.txid, reference.txid);
  assert.equal(hex(plan.message), reference.signing_message_00);
  assert.equal(plan.signingIntent.feeAtoms, 1000n);
  const signature = schnorr.sign(plan.message, unhex('00'.repeat(31) + '03'), unhex('00'.repeat(32)));
  assert.equal(hex(signature), reference.signature_00);
  const final = finalizePayment(plan, signature);
  assert.equal(hex(final.wire), reference.wire);
  assert.equal(final.txhash, reference.txhash);
  assert.equal(final.txid, reference.txid);
  assert.equal(final.stages.invocation, 'unavailable');
});

test('changed owner, output and chain reject an old signature at cryptographic layer', () => {
  const plan = preparePayment(artifact, context);
  const signature = unhex(reference.signature_00);
  const alteredOwner = compilePayment(PAYMENT_SOURCE, 'e493dbf1c10d80f3581e4904930b1404cc6c13900ee0758474fa94abe8c4cd13');
  const ownerContext = { ...context, coin: { ...context.coin, branches: alteredOwner.policy.branches } };
  assert.throws(() => finalizePayment(preparePayment(alteredOwner, ownerContext), signature), /signature verification failed/);
  assert.throws(() => finalizePayment(preparePayment(artifact, { ...context, outputs: [{ ...output, value: 999n }] }), signature), /signature verification failed/);
  assert.throws(() => finalizePayment(preparePayment(artifact, { ...context, chainId: '44'.repeat(32) }), signature), /signature verification failed/);
  assert.throws(() => finalizePayment({ ...plan, context: { ...context, chainId: '44'.repeat(32) } }, signature), /stale signing plan/);
});

test('unsupported language, invalid input and amounts reject', () => {
  assert.throws(() => compilePayment(PAYMENT_SOURCE.replace('checksig', 'checkdatasig'), reference.public_key), /expected checksig/);
  assert.throws(() => compilePayment(PAYMENT_SOURCE + ' OP_SUCCESS', reference.public_key), /unsupported syntax/);
  assert.throws(() => compilePayment(PAYMENT_SOURCE.replace('owner)', 'someone)'), reference.public_key), /typed name mismatch/);
  assert.throws(() => preparePayment(artifact, { ...context, outputs: [{ ...output, value: -1n }] }), /range/);
  assert.throws(() => preparePayment(artifact, { ...context, coin: { ...context.coin, value: 999n } }), /negative fee/);
});
