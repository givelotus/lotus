import { spawnSync } from 'node:child_process';
import { schnorr } from '@noble/curves/secp256k1';
import { bytes, concat, hex, tagged, unhex } from '../dist/compiler.js';
import { encodeOutput } from '../dist/runtime.js';
import { finalizeContractCall, methodRoot, prepareContractCall } from '../dist/call-runtime.js';

const executable = process.argv[2];
if (!executable) throw new Error('usage: node test/run-native-calls.mjs NATIVE_CHECK_EXECUTABLE');
const publicTestKeys = [3, 4].map(n => schnorr.getPublicKey(unhex('00'.repeat(31) + `0${n}`)));
const scripts = publicTestKeys.map(key => `20${hex(key)}bb`);
const leaves = scripts.map(script => hex(tagged('branch', concat(Uint8Array.of(0), bytes(unhex(script))))));
const root = methodRoot(scripts[0], [leaves[1]]);
const artifact = { schema: 'lotus-v2/contract-artifact/2', target: 'P01-P02-P03-candidate-2026-10-14', contract: 'TwoKeys', constructor: [], bindings: [],
  methods: scripts.map((scriptHex, i) => ({ name: `spend${i}`, args: [{ name: 'signature', type: 'Signature' }], scriptHex,
    leaf: leaves[i], proof: [leaves[1-i]], root })),
  policy: { branches: [root], paths: [[0]], root, treeRecipe: 'sorted-leaves-largest-power-split-v1' } };
const output = { value: 1000n, branches: [root], paths: [[0]] };
const context = { profile: artifact.target, chainId: '44'.repeat(32), prevTxid: '11'.repeat(32), prevIndex: 0,
  sequence: 0xffffffff, coin: { ...output, value: 2000n }, outputs: [output] };

function check(wire, coin, chainId, key, txid, txhash, message, expected) {
  const run = spawnSync(executable, [hex(wire), hex(encodeOutput(coin)), chainId, hex(key), txid, txhash, message, expected], { encoding: 'utf8' });
  if (run.status !== 0) throw new Error(`${expected}: ${run.stderr}`);
}
for (let i = 0; i < 2; i++) {
  const plan = prepareContractCall(artifact, `spend${i}`, context, { signature: null });
  const secret = unhex('00'.repeat(31) + `0${i+3}`);
  const signature = schnorr.sign(unhex(plan.requests[0].digest), secret, new Uint8Array(32));
  const final = finalizeContractCall(plan, { signature });
  check(final.wire, context.coin, context.chainId, publicTestKeys[i], final.txid, final.txhash, plan.requests[0].digest, 'valid');
  check(final.wire, context.coin, '45'.repeat(32), publicTestKeys[i], '-', '-', '-', 'invalid');
  const wrongProofCoin = { ...context.coin, branches: [leaves[i]] };
  check(final.wire, wrongProofCoin, context.chainId, publicTestKeys[i], '-', '-', '-', 'invalid-proof');
  const changedOutputs = { ...context, outputs: [{ ...output, value: 999n }] };
  const changedPlan = prepareContractCall(artifact, `spend${i}`, changedOutputs, { signature: null });
  const changedFinal = finalizeContractCall(changedPlan, { signature });
  check(changedFinal.wire, context.coin, context.chainId, publicTestKeys[i], '-', '-', '-', 'invalid');
  console.log(`method ${i}: native proof/framing/identities/signature checks passed`);
}
