#!/usr/bin/env node
import { readFileSync, writeFileSync } from 'node:fs';
import { schnorr } from '@noble/curves/secp256k1';
import { compileContract } from '../dist/generic.js';
import { hex, unhex, uint } from '../dist/compiler.js';
import { encodeAssetOutput, prepareTransactionCall, finalizeTransactionCall } from '../dist/transaction-runtime.js';

const source = readFileSync(new URL('../examples/gallery/fungible-token.lotus', import.meta.url), 'utf8');
const testScalar = unhex('00'.repeat(31) + '03'); // Published BIP340 test scalar; no wallet or network key.
const publicKey = hex(schnorr.getPublicKey(testScalar));
const bindings = { TokenWallet: { owner: publicKey }, FungibleToken: { issuer: publicKey } };
const compile = contract => compileContract(source, { contract, bindings });
const wallet = compile('TokenWallet'), rules = compile('FungibleRules'), mint = compile('FungibleToken');
const tokenId = mint.policy.root;
const native = value => ({ flags: 0, value, branches: [wallet.policy.root], paths: [[0]] });
const token = value => ({ flags: 1, value, tokenId, branches: [wallet.policy.root, rules.policy.root], paths: [[0, 1]] });
const witness = (artifact, methodName, args) => ({ artifact, methodName, args });
const nativeSpend = (prevTxid, prevIndex, coin) => ({ kind: 'spend', prevTxid, prevIndex,
  sequence: 0xffffffff, coin, pathIndex: 0, witnesses: [witness(wallet, 'spend', { signature: null })] });
const common = { profile: 'P01-P02-P03-candidate-2026-10-14', chainId: '44'.repeat(32), dustLimitAtoms: 500n };
const mintIntent = { ...common, inputs: [nativeSpend('11'.repeat(32), 0, native(10000n)),
  { kind: 'mint', artifact: mint, methodName: 'issue', args: { signature: null } }],
outputs: [token(1000n), native(7000n)] };
function signatures(plan) {
  return Object.fromEntries(plan.requests.map(request => [request.key,
    schnorr.sign(unhex(request.digest), testScalar, new Uint8Array(32))]));
}
const mintPlan = prepareTransactionCall(mintIntent);
const mintSigs = signatures(mintPlan);
const minted = finalizeTransactionCall(mintPlan, mintSigs);
const transferIntent = { ...common, inputs: [
  { kind: 'spend', prevTxid: minted.txid, prevIndex: 0, sequence: 0xffffffff,
    coin: token(1000n), pathIndex: 0,
    witnesses: [witness(wallet, 'spend', { signature: null }), witness(rules, 'transfer', {})] },
  nativeSpend(minted.txid, 1, native(7000n))],
outputs: [token(700n), token(250n), native(4000n)] };
const transferPlan = prepareTransactionCall(transferIntent);
const transferSigs = signatures(transferPlan);
const transferred = finalizeTransactionCall(transferPlan, transferSigs);

const outputJson = output => ({ flags: output.flags, valueAtoms: output.value.toString(),
  tokenId: output.tokenId ?? null, branches: output.branches, paths: output.paths });
const artifactName = artifact => artifact.contract;
const inputJson = input => input.kind === 'mint' ? { kind: 'mint', artifact: artifactName(input.artifact),
  methodName: input.methodName, args: input.args } : { kind: 'spend', prevTxid: input.prevTxid,
  prevIndex: input.prevIndex, sequence: input.sequence, coin: outputJson(input.coin), pathIndex: input.pathIndex,
  witnesses: input.witnesses.map(w => ({ artifact: artifactName(w.artifact), methodName: w.methodName, args: w.args })) };
function transaction(plan, final, signed) {
  const annotated = plan.requests.map(request => {
    const input = plan.intent.inputs[request.inputIndex];
    const selected = input.kind === 'mint' ? { artifact: input.artifact, methodName: input.methodName } :
      input.witnesses[request.witnessIndex];
    const method = selected.artifact.methods.find(m => m.name === selected.methodName);
    const argumentIndex = method.args.findIndex(arg => arg.name === request.argument);
    if (argumentIndex < 0) throw new Error('signature argument absent from method');
    if (!schnorr.verify(signed[request.key], unhex(request.digest), unhex(publicKey))) throw new Error('fixture signature mismatch');
    return { key: request.key, inputIndex: request.inputIndex, witnessIndex: request.witnessIndex,
      argumentIndex, publicKey, digest: request.digest, signature: hex(signed[request.key]),
      leaf: request.leaf, ...(request.branchIndex === undefined ? {} : { branchIndex: request.branchIndex }),
      ...(request.positiveDelta === undefined ? {} : { positiveDelta: hex(uint(request.positiveDelta, 16)) }) };
  });
  return { profile: plan.intent.profile, chainId: plan.intent.chainId,
    dustLimitAtoms: plan.intent.dustLimitAtoms.toString(), inputs: plan.intent.inputs.map(inputJson),
    outputs: plan.intent.outputs.map(outputJson),
    coinWires: plan.intent.inputs.map(input => input.kind === 'mint' ? null : hex(encodeAssetOutput(input.coin))),
    unsignedWire: hex(plan.unsignedWire), wire: hex(final.wire), txid: final.txid, txhash: final.txhash,
    feeAtoms: plan.feeAtoms.toString(), minimumFeeAtoms: plan.minimumFeeAtoms.toString(),
    projectedFullBytes: plan.projectedFullBytes,
    tokenDeltas: Object.fromEntries(Object.entries(plan.tokenDeltas).map(([id,amount]) => [id,amount.toString()])),
    tokenBurns: Object.fromEntries(Object.entries(plan.tokenBurns).map(([id,amount]) => [id,amount.toString()])),
    requests: annotated };
}
const fixture = { schema: 'lotus-v2/fungible-token-fixture/1', source, publicTestKey: publicKey,
  artifacts: { TokenWallet: wallet, FungibleRules: rules, FungibleToken: mint },
  holderPolicy: { branches: [wallet.policy.root, rules.policy.root], paths: [[0, 1]] },
  transactions: { mint: transaction(mintPlan, minted, mintSigs),
    transfer: transaction(transferPlan, transferred, transferSigs) } };
if (fixture.transactions.mint.tokenDeltas[tokenId] !== '1000' ||
    fixture.transactions.transfer.tokenBurns[tokenId] !== '50') throw new Error('unexpected token accounting');
const output = process.argv[2] ?? new URL('../fixtures/fungible-token-v2.json', import.meta.url);
writeFileSync(output, JSON.stringify(fixture, null, 2) + '\n');
