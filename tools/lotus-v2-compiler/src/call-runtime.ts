import { schnorr } from '@noble/curves/secp256k1';
import { bytes, concat, cs, hex, tagged, uint, unhex } from './compiler.js';
import { encodeOutput, type PaymentOutput } from './runtime.js';

export type ContractArtifact = {
  schema: 'lotus-v2/contract-artifact/2'; target: 'P01-P02-P03-candidate-2026-10-14'; contract: string;
  constructor: { name: string; type: string }[]; bindings: { name: string; type: string; value: string | boolean }[];
  methods: { name: string; args: { name: string; type: string }[]; scriptHex: string; leaf: string; proof: string[]; root: string }[];
  policy: { branches: string[]; paths: number[][]; root: string; treeRecipe: string };
};
export type CallContext = { chainId: string; prevTxid: string; prevIndex: number; sequence: number; coin: PaymentOutput; outputs: PaymentOutput[]; lock?: bigint; profile: 'P01-P02-P03-candidate-2026-10-14' };
export type CallValue = Uint8Array | bigint | boolean | null;
export type SignatureRequest = { argument: string; mode: 0; digest: string; chainId: string; txid: string; inputIndex: 0; branchIndex: 0; leaf: string; feeAtoms: bigint };
export type CallPlan = { artifact: ContractArtifact; methodName: string; context: CallContext; arguments: Record<string, CallValue>; unsignedWire: Uint8Array; txid: string; requests: SignatureRequest[] };
export type CallFinal = { wire: Uint8Array; txid: string; txhash: string; stages: { assembly: 'passed'; framing: 'passed'; signature: 'unavailable'; invocation: 'unavailable'; contextual: 'unavailable'; block: 'unavailable' } };

function u32(n: number): Uint8Array { if (!Number.isInteger(n) || n < 0 || n > 0xffffffff) throw new Error('u32 range'); return uint(BigInt(n), 4); }
function equal(a: unknown, b: unknown): boolean { return JSON.stringify(a) === JSON.stringify(b); }
function validName(value: string): boolean { return typeof value === 'string' && /^[A-Za-z_][A-Za-z_0-9]*$/.test(value); }
function validType(type: string): boolean { return ['PublicKey', 'Signature', 'Bytes32', 'Int', 'Bool', 'MethodLeafHash', 'ContractRootHash'].includes(type) || /^Bytes\(([1-9][0-9]*)\)$/.test(type) && Number(type.slice(6, -1)) <= 8192; }
function node(a: Uint8Array, b: Uint8Array): Uint8Array {
  let cmp = 0;
  for (let i = 31; i >= 0; i--) if (a[i] !== b[i]) { cmp = a[i]! - b[i]!; break; }
  return tagged('branch', concat(Uint8Array.of(1), ...(cmp <= 0 ? [a, b] : [b, a])));
}
export function methodRoot(scriptHex: string, proof: string[]): string {
  let result = tagged('branch', concat(Uint8Array.of(0), bytes(unhex(scriptHex))));
  if (proof.length > 64) throw new Error('proof depth');
  for (const sibling of proof) result = node(result, unhex(sibling, 32));
  return hex(result);
}
export function assertContractArtifact(a: ContractArtifact): void {
  if (a.schema !== 'lotus-v2/contract-artifact/2' || a.target !== 'P01-P02-P03-candidate-2026-10-14' || !validName(a.contract)) throw new Error('unsupported artifact');
  if (a.policy.treeRecipe !== 'sorted-leaves-largest-power-split-v1' || a.policy.branches.length !== 1 || a.policy.branches[0] !== a.policy.root || !equal(a.policy.paths, [[0]])) throw new Error('unsupported policy');
  unhex(a.policy.root, 32);
  if (!Array.isArray(a.constructor) || !Array.isArray(a.bindings) || a.constructor.length !== a.bindings.length) throw new Error('constructor/binding mismatch');
  if (new Set(a.constructor.map(x => x.name)).size !== a.constructor.length) throw new Error('duplicate constructor names');
  for (let i = 0; i < a.constructor.length; i++) {
    const declaration = a.constructor[i]!, binding = a.bindings[i]!;
    if (!validName(declaration.name) || !validType(declaration.type) || binding.name !== declaration.name || binding.type !== declaration.type) throw new Error('constructor/binding mismatch');
    if (binding.type === 'Bool') { if (typeof binding.value !== 'boolean') throw new Error('noncanonical Bool binding'); }
    else if (binding.type === 'Int') {
      if (typeof binding.value !== 'string' || !/^(0|-?[1-9][0-9]*)$/.test(binding.value)) throw new Error('noncanonical Int binding');
      encodeCallValue('Int', BigInt(binding.value));
    } else {
      if (typeof binding.value !== 'string') throw new Error('noncanonical byte binding');
      const raw = unhex(binding.value);
      if (binding.type === 'Signature') {
        if (raw.length !== 64 && !(raw.length === 65 && (raw[64] === 1 || raw[64] === 2))) throw new Error('noncanonical Signature binding');
      } else encodeCallValue(binding.type, raw);
      if (binding.type === 'PublicKey') try { schnorr.utils.lift_x(BigInt(`0x${binding.value}`)); } catch { throw new Error('PublicKey is not a BIP340 x-only curve point'); }
    }
  }
  if (!Array.isArray(a.methods) || !a.methods.length || a.methods.length > 16 || new Set(a.methods.map(m => m.name)).size !== a.methods.length) throw new Error('invalid methods');
  const leaves: Uint8Array[] = [];
  for (const m of a.methods) {
    if (!validName(m.name) || !Array.isArray(m.args) || new Set(m.args.map(x => x.name)).size !== m.args.length || m.args.some(x => !validName(x.name) || !validType(x.type))) throw new Error('invalid method arguments');
    const script = unhex(m.scriptHex);
    if (!script.length || script.length > 8192) throw new Error('script width');
    const leaf = tagged('branch', concat(Uint8Array.of(0), bytes(script)));
    if (m.leaf !== hex(leaf) || methodRoot(m.scriptHex, m.proof) !== m.root || m.root !== a.policy.root) throw new Error('method proof or root mismatch');
    leaves.push(leaf);
  }
  const ordered = leaves.sort((a,b) => { for (let i = 31; i >= 0; i--) if (a[i] !== b[i]) return a[i]! - b[i]!; return 0; });
  if (new Set(ordered.map(hex)).size !== ordered.length) throw new Error('duplicate method leaf');
  function tree(items: Uint8Array[]): Uint8Array {
    if (items.length === 1) return items[0]!;
    let k = 1; while (k * 2 < items.length) k *= 2;
    return node(tree(items.slice(0, k)), tree(items.slice(k)));
  }
  if (hex(tree(ordered)) !== a.policy.root) throw new Error('method tree recipe mismatch');
}
function methodOf(a: ContractArtifact, name: string): ContractArtifact['methods'][number] {
  assertContractArtifact(a);
  const m = a.methods.find(x => x.name === name);
  if (!m) throw new Error('unknown method');
  const leaf = hex(tagged('branch', concat(Uint8Array.of(0), bytes(unhex(m.scriptHex)))));
  if (m.leaf !== leaf || methodRoot(m.scriptHex, m.proof) !== m.root || m.root !== a.policy.root) throw new Error('method proof or root mismatch');
  if (new Set(m.args.map(x => x.name)).size !== m.args.length) throw new Error('duplicate argument names');
  return m;
}
function int128(n: bigint): Uint8Array {
  if (typeof n !== 'bigint' || n < -(1n << 127n) || n >= (1n << 127n)) throw new Error('int128 range');
  return uint(n < 0n ? (1n << 128n) + n : n, 16);
}
export function encodeCallValue(type: string, value: CallValue): Uint8Array {
  if (type === 'Signature') {
    if (!(value instanceof Uint8Array) || value.length !== 64) throw new Error('FULL signature must be 64 bytes');
    return Uint8Array.from(value);
  }
  if (type === 'Int') return int128(value as bigint);
  if (type === 'Bool') {
    if (typeof value !== 'boolean') throw new Error('Bool required');
    return int128(value ? 1n : 0n);
  }
  const fixed = ['PublicKey', 'Bytes32', 'MethodLeafHash', 'ContractRootHash'].includes(type) ? 32 : undefined;
  const bounded = /^Bytes\(([0-9]+)\)$/.exec(type)?.[1];
  if (!(value instanceof Uint8Array)) throw new Error('byte value required');
  if (fixed !== undefined && value.length !== Number(fixed)) throw new Error(`${type} length`);
  if (bounded !== undefined && value.length > Number(bounded)) throw new Error(`${type} length`);
  if (type !== 'Bytes' && fixed === undefined && bounded === undefined) throw new Error(`unsupported argument type ${type}`);
  if (value.length > 8192) throw new Error('argument too large');
  return Uint8Array.from(value);
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
function core(c: CallContext, m: ContractArtifact['methods'][number]): Uint8Array {
  return concat(unhex(c.prevTxid, 32), u32(c.prevIndex), u32(c.sequence), Uint8Array.of(1), cs(0), cs(1), bytes(unhex(m.scriptHex)), cs(m.proof.length), ...m.proof.map(x => unhex(x, 32)));
}
function header(c: CallContext): Uint8Array { return concat(u32(7), uint(c.lock ?? 0n, 8), uint(1n, 2), uint(BigInt(c.outputs.length), 2)); }
function full(c: CallContext, m: ContractArtifact['methods'][number], values: Uint8Array[]): Uint8Array { return concat(core(c, m), cs(values.length), ...values.map(bytes)); }
function hashes(c: CallContext, m: ContractArtifact['methods'][number], values: Uint8Array[]): { txid: string; txhash: string; message: string; wire: Uint8Array } {
  const h = header(c); const outputBytes = c.outputs.map(encodeOutput); const outRoot = indexedRoot(outputBytes.map(x => tagged('output', bytes(x))));
  const id = tagged('txid', concat(unhex(c.chainId, 32), h, indexedRoot([tagged('inputcore', core(c, m))]), outRoot));
  const th = tagged('txhash', concat(unhex(c.chainId, 32), h, indexedRoot([tagged('inputfull', full(c, m, values))]), outRoot));
  const coinRoot = indexedRoot([tagged('coinentry', bytes(encodeOutput(c.coin)))]);
  const selector = concat(Uint8Array.of(1), u32(0), u32(0), unhex(m.leaf, 32));
  const message = tagged('sighash', concat(unhex(c.chainId, 32), Uint8Array.of(0), id, coinRoot, selector));
  return { txid: hex(id), txhash: hex(th), message: hex(message), wire: concat(h, full(c, m, values), ...outputBytes) };
}
function encodedArgs(m: ContractArtifact['methods'][number], args: Record<string, CallValue>, signatures?: Record<string, Uint8Array>): Uint8Array[] {
  if (Object.keys(args).sort().join(',') !== m.args.map(x => x.name).sort().join(',')) throw new Error('argument names mismatch');
  return m.args.map(x => {
    if (x.type === 'Signature') {
      if (args[x.name] !== null) throw new Error('Signature argument must be an empty signing slot');
      return signatures ? encodeCallValue('Signature', signatures[x.name] ?? null) : new Uint8Array();
    }
    return encodeCallValue(x.type, args[x.name] ?? null);
  });
}
export function prepareContractCall(a: ContractArtifact, methodName: string, c: CallContext, args: Record<string, CallValue>): CallPlan {
  const m = methodOf(a, methodName);
  if (c.profile !== a.target) throw new Error('unsupported profile');
  unhex(c.chainId, 32); unhex(c.prevTxid, 32); u32(c.prevIndex); u32(c.sequence);
  const lock = c.lock ?? 0n; uint(lock, 8);
  if ((lock & 255n) > 2n || ((lock & 255n) === 0n && lock !== 0n)) throw new Error('invalid P01 lock encoding');
  if (c.sequence !== 0xffffffff && (c.sequence & ~0x40ffff) !== 0) throw new Error('invalid P01 sequence bits');
  if (!equal(c.coin.paths, [[0]]) || !equal(c.coin.branches, [a.policy.root])) throw new Error('resolved coin policy mismatch');
  if (c.outputs.length > 65535) throw new Error('too many outputs');
  const encoded = encodedArgs(m, args);
  const amount = c.outputs.reduce((n, o) => n + o.value, 0n);
  if (amount > c.coin.value) throw new Error('negative fee');
  const result = hashes(c, m, encoded);
  const requests = m.args.filter(x => x.type === 'Signature').map(x => ({ argument: x.name, mode: 0 as const, digest: result.message, chainId: c.chainId,
    txid: result.txid, inputIndex: 0 as const, branchIndex: 0 as const, leaf: m.leaf, feeAtoms: c.coin.value - amount }));
  return { artifact: a, methodName, context: c, arguments: args, unsignedWire: result.wire, txid: result.txid, requests };
}
export function finalizeContractCall(plan: CallPlan, signatures: Record<string, Uint8Array>): CallFinal {
  const fresh = prepareContractCall(plan.artifact, plan.methodName, plan.context, plan.arguments);
  if (fresh.txid !== plan.txid || hex(fresh.unsignedWire) !== hex(plan.unsignedWire) || fresh.requests.length !== plan.requests.length ||
      fresh.requests.some((r, i) => r.argument !== plan.requests[i]?.argument || r.digest !== plan.requests[i]?.digest || r.feeAtoms !== plan.requests[i]?.feeAtoms)) throw new Error('stale signing plan');
  if (Object.keys(signatures).sort().join(',') !== fresh.requests.map(x => x.argument).sort().join(',')) throw new Error('signature slots mismatch');
  const result = hashes(plan.context, methodOf(plan.artifact, plan.methodName), encodedArgs(methodOf(plan.artifact, plan.methodName), plan.arguments, signatures));
  return { wire: result.wire, txid: result.txid, txhash: result.txhash,
    stages: { assembly: 'passed', framing: 'passed', signature: 'unavailable', invocation: 'unavailable', contextual: 'unavailable', block: 'unavailable' } };
}
