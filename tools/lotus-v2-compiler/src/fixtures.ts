import { schnorr } from '@noble/curves/secp256k1';
import { compilePayment, hex, unhex } from './compiler.js';
import { encodeOutput, encodePaymentWireUnchecked, finalizePayment, preparePayment, type PaymentContext, type PaymentOutput } from './runtime.js';

export type PaymentFixtureInput = {
  source: string; owner: string; testSecret: string; chainId: string;
  outpoint: { txid: string; index: number }; sequence: number; lock: bigint;
  coin: PaymentOutput; outputs: PaymentOutput[];
  profile: 'payment-fixture-p01-v1'; signingMode: 0;
};
type JsonOutput = { valueAtoms: string; branches: string[]; paths: number[][]; flags: 0 };
export type PaymentFixture = {
  schema: 'lotus-v2/payment-fixture/1'; source: string; artifact: ReturnType<typeof compilePayment>;
  context: { chainId: string; outpoint: { txid: string; index: number }; sequence: number; lock: string; profile: 'payment-fixture-p01-v1'; signingMode: 0; coin: JsonOutput; coinWire: string; outputs: JsonOutput[] };
  valid: { wire: string; txid: string; txhash: string; message: string; signature: string; feeAtoms: string; expectedStage: 'signature'; stages: ReturnType<typeof finalizePayment>['stages'] };
  mutations: { name: string; wire: string; context: { chainId: string; owner: string; coin: JsonOutput; coinWire: string; outputs: JsonOutput[] }; expectedStage: 'signature'; expectedReason: string }[];
};
function jsonOutput(o: PaymentOutput): JsonOutput { return { flags: 0, valueAtoms: o.value.toString(), branches: [...o.branches], paths: o.paths.map(p => [...p]) }; }
function alterRoot(root: string): string { return (root[0] === '0' ? '1' : '0') + root.slice(1); }
export function buildPaymentFixture(input: PaymentFixtureInput): PaymentFixture {
  if (input.signingMode !== 0) throw new Error('fixture builder supports FULL signing mode 0 only');
  const secret = unhex(input.testSecret, 32);
  if (hex(schnorr.getPublicKey(secret)) !== input.owner) throw new Error('owner does not match deterministic fixture key');
  const artifact = compilePayment(input.source, input.owner);
  const base: PaymentContext = { profile: input.profile, chainId: input.chainId, prevTxid: input.outpoint.txid, prevIndex: input.outpoint.index,
    sequence: input.sequence, lock: input.lock, coin: input.coin, outputs: input.outputs };
  const plan = preparePayment(artifact, base);
  if (base.outputs[0]!.value === 0n) throw new Error('first output must have positive value for named mutation');
  const signature = schnorr.sign(plan.message, secret, new Uint8Array(32));
  const valid = finalizePayment(plan, signature);
  const variants: { name: string; context: PaymentContext; artifact: typeof artifact }[] = [
    { name: 'changed-output-value', context: { ...base, outputs: [{ ...base.outputs[0]!, value: base.outputs[0]!.value - 1n }, ...base.outputs.slice(1)] }, artifact },
    { name: 'changed-chain-id', context: { ...base, chainId: alterRoot(base.chainId) }, artifact },
  ];
  const alternativeSecret = input.testSecret === '00'.repeat(31) + '03' ? '00'.repeat(31) + '04' : '00'.repeat(31) + '03';
  const changedOwner = compilePayment(input.source, hex(schnorr.getPublicKey(unhex(alternativeSecret, 32))));
  variants.push({ name: 'changed-owner', context: { ...base, coin: { ...base.coin, branches: changedOwner.policy.branches } }, artifact: changedOwner });
  const mutations = variants.map(({ name, context, artifact: selected }) => {
    let reason = '';
    try { finalizePayment(preparePayment(selected, context), signature); } catch (err) { reason = (err as Error).message; }
    if (reason !== 'signature verification failed') throw new Error(`mutation ${name} failed at unexpected stage: ${reason}`);
    return { name, wire: hex(encodePaymentWireUnchecked(selected, context, signature)),
      context: { chainId: context.chainId, owner: selected.scriptHex.slice(2, 66), coin: jsonOutput(context.coin), coinWire: hex(encodeOutput(context.coin)), outputs: context.outputs.map(jsonOutput) },
      expectedStage: 'signature' as const, expectedReason: reason };
  });
  return { schema: 'lotus-v2/payment-fixture/1', source: input.source, artifact,
    context: { chainId: base.chainId, outpoint: { txid: base.prevTxid, index: base.prevIndex }, sequence: base.sequence, lock: base.lock!.toString(), profile: base.profile,
      signingMode: 0, coin: jsonOutput(base.coin), coinWire: hex(encodeOutput(base.coin)), outputs: base.outputs.map(jsonOutput) },
    valid: { wire: hex(valid.wire), txid: valid.txid, txhash: valid.txhash, message: valid.message, signature: valid.signature,
      feeAtoms: plan.signingIntent.feeAtoms.toString(), expectedStage: 'signature', stages: valid.stages }, mutations };
}
