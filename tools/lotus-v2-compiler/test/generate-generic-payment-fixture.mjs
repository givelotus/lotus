import { writeFileSync } from 'node:fs';
import { schnorr } from '@noble/curves/secp256k1';
import { hex, unhex } from '../dist/compiler.js';
import { encodeOutput } from '../dist/runtime.js';
import { finalizeContractCall, prepareContractCall } from '../dist/call-runtime.js';

const compilerModule = process.env.LOTUS_V2_GENERIC_MODULE ?? '../dist/generic.js';
const { compileContract } = await import(compilerModule);
const source = 'contract Payment<owner: PublicKey> { function spend(signature: Signature) { require(checksig(signature, owner)); } }';
// Public test key 3; secret stays only in this deterministic offline generator.
const testSecret = unhex('00'.repeat(31) + '03');
const publicTestKey = hex(schnorr.getPublicKey(testSecret));
const artifact = compileContract(source, { contract: 'Payment', bindings: { Payment: { owner: publicTestKey } } });
const output = { value: 1000n, branches: [artifact.policy.root], paths: [[0]] };
const context = { profile: artifact.target, chainId: '44'.repeat(32), prevTxid: '11'.repeat(32), prevIndex: 0,
  sequence: 0xffffffff, coin: { ...output, value: 2000n }, outputs: [output] };
const plan = prepareContractCall(artifact, 'spend', context, { signature: null });
const signature = schnorr.sign(unhex(plan.requests[0].digest), testSecret, new Uint8Array(32));
const final = finalizeContractCall(plan, { signature });
const fixture = { schema: 'lotus-v2/contract-call-fixture/1', source, artifact, publicTestKey,
  context: { chainId: context.chainId, prevTxid: context.prevTxid, prevIndex: context.prevIndex, sequence: context.sequence,
    profile: context.profile, coin: { valueAtoms: context.coin.value.toString(), branches: context.coin.branches, paths: context.coin.paths },
    coinWire: hex(encodeOutput(context.coin)), outputs: context.outputs.map(x => ({ valueAtoms: x.value.toString(), branches: x.branches, paths: x.paths })) },
  valid: { wire: hex(final.wire), txid: final.txid, txhash: final.txhash, message: plan.requests[0].digest,
    signature: hex(signature), leaf: plan.requests[0].leaf, feeAtoms: plan.requests[0].feeAtoms.toString(), stages: final.stages } };
writeFileSync(new URL('../fixtures/generic-payment-v2.json', import.meta.url), JSON.stringify(fixture, null, 2) + '\n');
