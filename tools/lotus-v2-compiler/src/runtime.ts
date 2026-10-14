import { schnorr } from '@noble/curves/secp256k1';
import { bytes, concat, cs, hex, tagged, uint, unhex, type PaymentArtifact } from './compiler.js';

export type PaymentOutput = { value: bigint; branches: string[]; paths: number[][]; flags?: 0 };
export type PaymentCoin = PaymentOutput & { flags?: 0 };
export type PaymentContext = { chainId: string; prevTxid: string; prevIndex: number; sequence: number; coin: PaymentCoin; outputs: PaymentOutput[]; lock?: bigint; profile: 'payment-fixture-p01-v1' };
export type PaymentPlan = { artifact: PaymentArtifact; context: PaymentContext; unsignedWire: Uint8Array; txid: string; message: Uint8Array; signingIntent: { chainId: string; mode: 0; inputIndex: 0; branchIndex: 0; leaf: string; outputs: PaymentOutput[]; feeAtoms: bigint } };
export type PaymentFinal = { wire: Uint8Array; txid: string; txhash: string; message: string; signature: string; stages: { assembly: 'passed'; framing: 'passed'; signature: 'passed'; invocation: 'unavailable'; contextual: 'unavailable'; block: 'unavailable' } };

function u32(n: number): Uint8Array { if (!Number.isInteger(n) || n < 0 || n > 0xffffffff) throw new Error('u32 range'); return uint(BigInt(n), 4); }
function validateOutput(o: PaymentOutput): void {
  if (o.flags !== undefined && o.flags !== 0) throw new Error('only native spendable output supported');
  uint(o.value, 8);
  if (o.branches.length < 1 || o.branches.length > 16 || o.paths.length < 1 || o.paths.length > 16) throw new Error('output branch/path count');
  const roots = o.branches.map(x => hex(unhex(x, 32)));
  if (new Set(roots).size !== roots.length) throw new Error('duplicate branches');
  let prev = '';
  for (const path of o.paths) {
    if (!path.length || path.length > 16 || path.some((x, i) => !Number.isInteger(x) || x < 0 || x >= roots.length || (i > 0 && x <= path[i - 1]!))) throw new Error('invalid path');
    const key = path.map(x => String.fromCharCode(x + 1)).join('');
    if (prev && !(prev < key)) throw new Error('path order'); prev = key;
  }
}
export function encodeOutput(o: PaymentOutput): Uint8Array {
  validateOutput(o);
  return concat(Uint8Array.of(0), uint(o.value, 8), cs(o.branches.length), ...o.branches.map(x => unhex(x, 32)), cs(o.paths.length), ...o.paths.map(path => concat(cs(path.length), ...path.map(cs))));
}
function indexedRoot(leaves: Uint8Array[]): Uint8Array {
  if (!leaves.length) return tagged('merkleidx', Uint8Array.of(2));
  let nodes = leaves; let level = 0;
  while (nodes.length > 1) {
    if (nodes.length & 1) nodes = [...nodes, new Uint8Array(32)];
    const next: Uint8Array[] = [];
    for (let i = 0; i < nodes.length; i += 2) next.push(tagged('merkleidx', concat(Uint8Array.of(1), uint(BigInt(level), 2), nodes[i]!, nodes[i + 1]!)));
    nodes = next; level++;
  }
  return nodes[0]!;
}
function inputParts(a: PaymentArtifact, c: PaymentContext, signature?: Uint8Array): { core: Uint8Array; full: Uint8Array } {
  const script = unhex(a.scriptHex); const prefix = concat(unhex(c.prevTxid, 32), u32(c.prevIndex), u32(c.sequence), Uint8Array.of(1), cs(0), cs(1), bytes(script), cs(0));
  return { core: prefix, full: concat(prefix, cs(signature ? 1 : 0), ...(signature ? [bytes(signature)] : [])) };
}
function header(c: PaymentContext): Uint8Array { return concat(u32(7), uint(c.lock ?? 0n, 8), uint(1n, 2), uint(BigInt(c.outputs.length), 2)); }
function outputLeaves(c: PaymentContext): Uint8Array[] { return c.outputs.map(o => tagged('output', bytes(encodeOutput(o)))); }
function txid(a: PaymentArtifact, c: PaymentContext): Uint8Array {
  const root = indexedRoot([tagged('inputcore', inputParts(a, c).core)]);
  return tagged('txid', concat(unhex(c.chainId, 32), header(c), root, indexedRoot(outputLeaves(c))));
}
function wire(a: PaymentArtifact, c: PaymentContext, signature?: Uint8Array): Uint8Array {
  return concat(header(c), inputParts(a, c, signature).full, ...c.outputs.map(encodeOutput));
}
function assertArtifact(a: PaymentArtifact): void {
  if (a.schema !== 'lotus-v2/payment-artifact/1' || a.target !== 'P01-P02-P03-candidate-2026-10-14' || a.methods.length !== 1 || a.methods[0]?.name !== 'spend') throw new Error('unsupported artifact');
  const script = unhex(a.scriptHex, 34);
  if (script[0] !== 0x20 || script[33] !== 0xbb) throw new Error('unsupported script');
  const leaf = hex(tagged('branch', concat(Uint8Array.of(0), bytes(script))));
  if (a.policy.leaf !== leaf || a.policy.branches.length !== 1 || a.policy.branches[0] !== leaf || JSON.stringify(a.policy.paths) !== '[[0]]') throw new Error('artifact policy mismatch');
}
export function preparePayment(a: PaymentArtifact, c: PaymentContext): PaymentPlan {
  assertArtifact(a);
  if (c.profile !== 'payment-fixture-p01-v1') throw new Error('unsupported profile');
  unhex(c.chainId, 32); unhex(c.prevTxid, 32); u32(c.prevIndex); u32(c.sequence); uint(c.lock ?? 0n, 8);
  if (!c.outputs.length || c.outputs.length > 32) throw new Error('fixture profile output count');
  validateOutput(c.coin); c.outputs.forEach(validateOutput);
  if (c.coin.branches.length !== 1 || c.coin.branches[0] !== a.policy.leaf || JSON.stringify(c.coin.paths) !== '[[0]]') throw new Error('resolved coin policy mismatch');
  const sum = c.outputs.reduce((n, o) => n + o.value, 0n);
  if (sum > c.coin.value) throw new Error('negative fee');
  const id = txid(a, c);
  const coinRoot = indexedRoot([tagged('coinentry', bytes(encodeOutput(c.coin)))]);
  const selector = concat(Uint8Array.of(1), u32(0), u32(0), unhex(a.policy.leaf, 32));
  const message = tagged('sighash', concat(unhex(c.chainId, 32), Uint8Array.of(0), id, coinRoot, selector));
  return { artifact: a, context: c, unsignedWire: wire(a, c), txid: hex(id), message,
    signingIntent: { chainId: c.chainId, mode: 0, inputIndex: 0, branchIndex: 0, leaf: a.policy.leaf, outputs: c.outputs, feeAtoms: c.coin.value - sum } };
}
export function finalizePayment(plan: PaymentPlan, signature: Uint8Array): PaymentFinal {
  const fresh = preparePayment(plan.artifact, plan.context);
  if (hex(fresh.message) !== hex(plan.message) || fresh.txid !== plan.txid) throw new Error('stale signing plan');
  if (!(signature instanceof Uint8Array) || signature.length !== 64) throw new Error('FULL signature must be 64 bytes');
  const pubkey = unhex(plan.artifact.scriptHex.slice(2, 66), 32);
  if (!schnorr.verify(signature, fresh.message, pubkey)) throw new Error('signature verification failed');
  const full = inputParts(plan.artifact, plan.context, signature).full;
  const fullRoot = indexedRoot([tagged('inputfull', full)]);
  const txhash = tagged('txhash', concat(unhex(plan.context.chainId, 32), header(plan.context), fullRoot, indexedRoot(outputLeaves(plan.context))));
  return { wire: wire(plan.artifact, plan.context, signature), txid: fresh.txid, txhash: hex(txhash), message: hex(fresh.message), signature: hex(signature),
    stages: { assembly: 'passed', framing: 'passed', signature: 'passed', invocation: 'unavailable', contextual: 'unavailable', block: 'unavailable' } };
}
