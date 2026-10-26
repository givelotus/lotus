import { readFileSync } from 'node:fs';
import { schnorr } from '@noble/curves/secp256k1';
import { compilePayment, hex, unhex } from '../dist/compiler.js';
import { preparePayment, finalizePayment } from '../dist/runtime.js';

const source = readFileSync(new URL('./payment.lotus', import.meta.url), 'utf8');
const fixture = JSON.parse(readFileSync(new URL('../fixtures/reference-signed-payment-v1.json', import.meta.url)));
const artifact = compilePayment(source, fixture.public_key);
const coin = { value: 2000n, branches: artifact.policy.branches, paths: [[0]] };
const output = { ...coin, value: 1000n };
const context = { profile: 'payment-fixture-p01-v1', chainId: fixture.chain_id, prevTxid: '11'.repeat(32), prevIndex: 0, sequence: 0xffffffff, coin, outputs: [output] };
const plan = preparePayment(artifact, context);
const signature = schnorr.sign(plan.message, unhex('00'.repeat(31) + '03'), new Uint8Array(32));
const result = finalizePayment(plan, signature);
const match = hex(result.wire) === fixture.wire && result.txid === fixture.txid && result.txhash === fixture.txhash && result.message === fixture.signing_message_00;
if (!match) throw new Error('independent reference mismatch');
console.log(JSON.stringify({
  schema: 'lotus-v2/compiler-payment-verification/1', compilerTarget: artifact.target,
  reference: { repository: '/private/tmp/lotus-v2-reference-output-20261014', commit: 'c0126889', fixture: 'signed-payment-v1.json', exactMatch: match },
  nativeCandidate: { repository: '/private/tmp/lotus-v2-signing-cpp', commit: '40a5479a', fixtureValuesMatch: true, executedByThisDemo: false },
  transaction: { wire: hex(result.wire), txid: result.txid, txhash: result.txhash, signingMessage: result.message, signature: result.signature, feeAtoms: plan.signingIntent.feeAtoms.toString() },
  stages: result.stages,
  specIssues: ['Production ChainID and genesis are unselected', 'P05 fee floor and full VM/accounting are not implemented in this compiler slice', 'Python binding awaits a maintained Python runtime']
}, null, 2));
