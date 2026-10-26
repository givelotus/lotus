import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { hex, unhex } from '../dist/compiler.js';
import { finalizeContractCall, prepareContractCall } from '../dist/call-runtime.js';

const fixture = JSON.parse(readFileSync(new URL('../fixtures/generic-payment-v2.json', import.meta.url)));
const output = o => ({ value: BigInt(o.valueAtoms), branches: o.branches, paths: o.paths });
const context = { profile: fixture.context.profile, chainId: fixture.context.chainId,
  prevTxid: fixture.context.prevTxid, prevIndex: fixture.context.prevIndex, sequence: fixture.context.sequence,
  coin: output(fixture.context.coin), outputs: fixture.context.outputs.map(output) };

test('signed generic Payment fixture reproduces exact P01 core/full commitments', () => {
  const plan = prepareContractCall(fixture.artifact, 'spend', context, { signature: null });
  const final = finalizeContractCall(plan, { signature: unhex(fixture.valid.signature) });
  assert.equal(plan.requests[0].digest, fixture.valid.message);
  assert.equal(plan.requests[0].leaf, fixture.valid.leaf);
  assert.equal(plan.requests[0].feeAtoms.toString(), fixture.valid.feeAtoms);
  assert.equal(hex(final.wire), fixture.valid.wire);
  assert.equal(final.txid, fixture.valid.txid);
  assert.equal(final.txhash, fixture.valid.txhash);
});
