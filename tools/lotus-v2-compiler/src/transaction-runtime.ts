/** Offline P01 multi-input planner. Execution and chain context are outside this module. */
import { bytes, concat, cs, hex, tagged, uint, unhex } from "./compiler.js";
import {
  assertContractArtifact,
  encodeCallValue,
  type CallValue,
  type ContractArtifact,
} from "./call-runtime.js";
const PROFILE = "P01-P02-P03-candidate-2026-10-14",
  U128 = (1n << 128n) - 1n,
  I128 = (1n << 127n) - 1n;
export type AssetOutput = {
  flags: 0 | 1 | 2 | 3;
  value: bigint;
  tokenId?: string;
  branches: string[];
  paths: number[][];
};
export type SelectedWitness = {
  artifact: ContractArtifact;
  methodName: string;
  args: Record<string, CallValue>;
};
export type SpendInput = {
  kind: "spend";
  prevTxid: string;
  prevIndex: number;
  sequence: number;
  coin: AssetOutput;
  pathIndex: number;
  witnesses: SelectedWitness[];
};
export type MintInput = {
  kind: "mint";
  artifact: ContractArtifact;
  methodName: string;
  args: Record<string, CallValue>;
};
export type PlannedInput = SpendInput | MintInput;
export type TransactionIntent = {
  profile: typeof PROFILE;
  chainId: string;
  lock?: bigint;
  dustLimitAtoms: bigint;
  inputs: PlannedInput[];
  outputs: AssetOutput[];
};
export type FullSignatureRequest = {
  key: string;
  argument: string;
  mode: 0;
  digest: string;
  inputIndex: number;
  witnessIndex: number;
  branchIndex?: number;
  tokenId?: string;
  positiveDelta?: bigint;
  leaf: string;
  feeAtoms: bigint;
};
const stages = {
  framing: "passed",
  proof: "passed",
  accounting: "passed",
  signature: "unavailable",
  invocation: "unavailable",
  contextual: "unavailable",
  block: "unavailable",
} as const;
export type TransactionPlan = {
  intent: TransactionIntent;
  seal: string;
  unsignedWire: Uint8Array;
  projectedFullBytes: number;
  txid: string;
  feeAtoms: bigint;
  minimumFeeAtoms: bigint;
  tokenDeltas: Record<string, bigint>;
  tokenBurns: Record<string, bigint>;
  requests: FullSignatureRequest[];
  stages: typeof stages;
};
export type TransactionFinal = {
  wire: Uint8Array;
  txid: string;
  txhash: string;
  stages: typeof stages;
};
function u32(n: number) {
  if (!Number.isInteger(n) || n < 0 || n > 0xffffffff) throw Error("u32 range");
  return uint(BigInt(n), 4);
}
function add(a: bigint, b: bigint) {
  const x = a + b;
  if (x > U128) throw Error("u128 aggregate overflow");
  return x;
}
function snapshot(x: unknown) {
  return JSON.stringify(x, (_, v) =>
    typeof v === "bigint" ? v.toString() : v instanceof Uint8Array ? hex(v) : v,
  );
}
function comparePath(a: number[], b: number[]) {
  for (let i = 0; i < Math.min(a.length, b.length); i++)
    if (a[i] !== b[i]) return a[i]! - b[i]!;
  return a.length - b.length;
}
export function encodeAssetOutput(o: AssetOutput): Uint8Array {
  if (
    ![0, 1, 2, 3].includes(o.flags) ||
    !Array.isArray(o.branches) ||
    !Array.isArray(o.paths)
  )
    throw Error("output flags or policy");
  const token = !!(o.flags & 1),
    burn = !!(o.flags & 2);
  if (token) {
    if (!o.tokenId || o.tokenId === "00".repeat(32))
      throw Error("token ID required");
    unhex(o.tokenId, 32);
  } else if (o.tokenId !== undefined) throw Error("native output has token ID");
  if (
    o.branches.length < 1 ||
    o.branches.length > 16 ||
    new Set(o.branches).size !== o.branches.length
  )
    throw Error("output branch count or duplicate");
  o.branches.forEach((x) => unhex(x, 32));
  if (burn ? o.paths.length !== 0 : o.paths.length < 1 || o.paths.length > 16)
    throw Error("output path count");
  let prev: number[] | undefined;
  for (const p of o.paths) {
    if (
      !Array.isArray(p) ||
      p.length < 1 ||
      p.length > 16 ||
      p.some(
        (v, i) =>
          !Number.isInteger(v) ||
          v < 0 ||
          v >= o.branches.length ||
          (i > 0 && v <= p[i - 1]!),
      )
    )
      throw Error("invalid output path");
    if (prev && comparePath(prev, p) >= 0) throw Error("output path order");
    prev = p;
  }
  return concat(
    Uint8Array.of(o.flags),
    uint(o.value, 8),
    ...(token ? [unhex(o.tokenId!, 32)] : []),
    cs(o.branches.length),
    ...o.branches.map((x) => unhex(x, 32)),
    cs(o.paths.length),
    ...o.paths.map((p) => concat(cs(p.length), ...p.map(cs))),
  );
}
function indexedRoot(leaves: Uint8Array[]): Uint8Array {
  if (!leaves.length) return tagged("merkleidx", Uint8Array.of(2));
  let nodes = leaves,
    level = 0;
  while (nodes.length > 1) {
    if (nodes.length & 1) nodes = [...nodes, new Uint8Array(32)];
    const next: Uint8Array[] = [];
    for (let i = 0; i < nodes.length; i += 2)
      next.push(
        tagged(
          "merkleidx",
          concat(
            Uint8Array.of(1),
            uint(BigInt(level), 2),
            nodes[i]!,
            nodes[i + 1]!,
          ),
        ),
      );
    nodes = next;
    level++;
  }
  return nodes[0]!;
}
function witnesses(input: PlannedInput): SelectedWitness[] {
  return input.kind === "mint"
    ? [
        {
          artifact: input.artifact,
          methodName: input.methodName,
          args: input.args,
        },
      ]
    : input.witnesses;
}
function selected(w: SelectedWitness, root: string, kind: "spend" | "mint") {
  assertContractArtifact(w.artifact);
  const a = w.artifact as ContractArtifact & { kind?: string };
  const m = a.methods.find((x) => x.name === w.methodName) as
    | (ContractArtifact["methods"][number] & { invocation?: string })
    | undefined;
  if (!m) throw Error("unknown method");
  if (
    kind === "mint"
      ? a.kind !== "token" || m.invocation !== "mint"
      : a.kind === "token" || m.invocation === "mint"
  )
    throw Error("wrong artifact or method invocation kind");
  if (m.root !== root || a.policy.root !== root)
    throw Error("witness branch root mismatch");
  if (m.args.length > 32) throw Error("candidate call argument cap");
  if (
    Object.keys(w.args).sort().join(",") !==
    m.args
      .map((x) => x.name)
      .sort()
      .join(",")
  )
    throw Error("argument names mismatch");
  for (const arg of m.args) {
    const value = w.args[arg.name];
    if (arg.type === "Signature") {
      if (value !== null)
        throw Error("Signature argument must be empty signing slot");
    } else encodeCallValue(arg.type, value ?? null);
  }
  return m;
}
function coreWitness(w: SelectedWitness): Uint8Array {
  const m = w.artifact.methods.find((x) => x.name === w.methodName)!;
  return concat(
    bytes(unhex(m.scriptHex)),
    cs(m.proof.length),
    ...m.proof.map((x) => unhex(x, 32)),
  );
}
function valuesFor(
  input: PlannedInput,
  index: number,
  sigs?: Record<string, Uint8Array>,
  projected = false,
): Uint8Array[][] {
  return witnesses(input).map((w, j) => {
    const m = w.artifact.methods.find((x) => x.name === w.methodName)!;
    return m.args.map((arg) =>
      arg.type === "Signature"
        ? projected
          ? new Uint8Array(64)
          : sigs
            ? encodeCallValue(
                "Signature",
                sigs[`${index}:${j}:${arg.name}`] ?? null,
              )
            : new Uint8Array()
        : encodeCallValue(arg.type, w.args[arg.name] ?? null),
    );
  });
}
function inputBytes(
  input: PlannedInput,
  values: Uint8Array[][],
  full: boolean,
): Uint8Array {
  const ws = witnesses(input);
  const encode = (w: SelectedWitness, j: number) =>
    full
      ? concat(coreWitness(w), cs(values[j]!.length), ...values[j]!.map(bytes))
      : coreWitness(w);
  if (input.kind === "mint")
    return concat(
      unhex(input.artifact.policy.root, 32),
      u32(0),
      u32(0xffffffff),
      Uint8Array.of(3),
      encode(ws[0]!, 0),
    );
  return concat(
    unhex(input.prevTxid, 32),
    u32(input.prevIndex),
    u32(input.sequence),
    Uint8Array.of(1),
    cs(input.pathIndex),
    cs(ws.length),
    ...ws.map(encode),
  );
}
function hashParts(intent: TransactionIntent, values: Uint8Array[][][]) {
  const header = concat(
    u32(7),
    uint(intent.lock ?? 0n, 8),
    uint(BigInt(intent.inputs.length), 2),
    uint(BigInt(intent.outputs.length), 2),
  );
  const core = intent.inputs.map((x, i) => inputBytes(x, values[i]!, false));
  const full = intent.inputs.map((x, i) => inputBytes(x, values[i]!, true));
  const outputs = intent.outputs.map(encodeAssetOutput),
    outRoot = indexedRoot(outputs.map((x) => tagged("output", bytes(x))));
  const chain = unhex(intent.chainId, 32);
  const id = tagged(
    "txid",
    concat(
      chain,
      header,
      indexedRoot(core.map((x) => tagged("inputcore", x))),
      outRoot,
    ),
  );
  const txhash = tagged(
    "txhash",
    concat(
      chain,
      header,
      indexedRoot(full.map((x) => tagged("inputfull", x))),
      outRoot,
    ),
  );
  const coinsRoot = indexedRoot(
    intent.inputs.map((x) =>
      tagged(
        "coinentry",
        x.kind === "mint" ? Uint8Array.of(0) : bytes(encodeAssetOutput(x.coin)),
      ),
    ),
  );
  return {
    wire: concat(header, ...full, ...outputs),
    txid: hex(id),
    txhash: hex(txhash),
    coinsRoot,
  };
}
function accounting(intent: TransactionIntent) {
  const ins = new Map<string, bigint>(),
    outs = new Map<string, bigint>(),
    explicit = new Map<string, bigint>();
  let nativeIn = 0n,
    nativeOut = 0n,
    tokenOutputs = 0;
  const record = (m: Map<string, bigint>, id: string, v: bigint) =>
    m.set(id, add(m.get(id) ?? 0n, v));
  for (const input of intent.inputs)
    if (input.kind === "spend") {
      const c = input.coin;
      if (c.flags & 2) throw Error("burn output cannot be spent");
      if (c.flags & 1) record(ins, c.tokenId!, c.value);
      else nativeIn = add(nativeIn, c.value);
    }
  for (const o of intent.outputs) {
    if (o.flags & 1) {
      record(outs, o.tokenId!, o.value);
      tokenOutputs++;
      if (o.flags & 2) record(explicit, o.tokenId!, o.value);
    } else nativeOut = add(nativeOut, o.value);
  }
  if (nativeOut > nativeIn) throw Error("negative native fee");
  const deltas: Record<string, bigint> = {},
    burns: Record<string, bigint> = {};
  for (const id of new Set([...ins.keys(), ...outs.keys()])) {
    const a = ins.get(id) ?? 0n,
      b = outs.get(id) ?? 0n;
    if (b > a) {
      const delta = b - a;
      if (delta > I128) throw Error("mint delta exceeds VM int128");
      deltas[id] = delta;
    }
    const burn = (a > b ? a - b : 0n) + (explicit.get(id) ?? 0n);
    if (burn) burns[id] = burn;
  }
  return { fee: nativeIn - nativeOut, deltas, burns, tokenOutputs };
}
export function prepareTransactionCall(
  intent: TransactionIntent,
): TransactionPlan {
  if (intent.profile !== PROFILE) throw Error("unsupported profile");
  unhex(intent.chainId, 32);
  const lock = intent.lock ?? 0n;
  uint(lock, 8);
  if ((lock & 255n) > 2n || ((lock & 255n) === 0n && lock !== 0n))
    throw Error("invalid P01 lock");
  if (typeof intent.dustLimitAtoms !== "bigint" || intent.dustLimitAtoms < 0n)
    throw Error("explicit dust limit required");
  if (
    !intent.inputs.length ||
    intent.inputs.length > 65535 ||
    intent.outputs.length > 65535
  )
    throw Error("input/output count");
  intent.outputs.forEach(encodeAssetOutput);
  const seen = new Set<string>(),
    mintIds: string[] = [];
  let spends = 0;
  for (const input of intent.inputs) {
    if (input.kind === "mint") {
      const id = input.artifact.policy.root;
      unhex(id, 32);
      if (id === "00".repeat(32)) throw Error("zero mint token ID");
      selected(
        {
          artifact: input.artifact,
          methodName: input.methodName,
          args: input.args,
        },
        id,
        "mint",
      );
      const key = `${id}:0`;
      if (seen.has(key)) throw Error("duplicate input outpoint");
      seen.add(key);
      mintIds.push(id);
    } else if (input.kind === "spend") {
      spends++;
      unhex(input.prevTxid, 32);
      u32(input.prevIndex);
      u32(input.sequence);
      if (input.sequence !== 0xffffffff && (input.sequence & ~0x40ffff) !== 0)
        throw Error("invalid P01 sequence");
      const key = `${input.prevTxid}:${input.prevIndex}`;
      if (seen.has(key)) throw Error("duplicate input outpoint");
      seen.add(key);
      encodeAssetOutput(input.coin);
      if (input.coin.flags & 2) throw Error("burn output cannot be spent");
      if (
        !Number.isInteger(input.pathIndex) ||
        input.pathIndex < 0 ||
        input.pathIndex >= input.coin.paths.length
      )
        throw Error("invalid path index");
      const path = input.coin.paths[input.pathIndex]!;
      if (input.witnesses.length !== path.length)
        throw Error("required witness count");
      input.witnesses.forEach((w, j) =>
        selected(w, input.coin.branches[path[j]!]!, "spend"),
      );
    } else throw Error("unsupported input kind");
  }
  if (!spends) throw Error("ordinary transaction needs consuming input");
  const totals = accounting(intent);
  if (
    snapshot([...mintIds].sort()) !==
    snapshot(Object.keys(totals.deltas).sort())
  )
    throw Error("mint inputs do not match positive token deltas");
  const empty = intent.inputs.map((x, i) => valuesFor(x, i)),
    projected = intent.inputs.map((x, i) => valuesFor(x, i, undefined, true));
  const initial = hashParts(intent, empty),
    predicted = hashParts(intent, projected);
  const required = 2n * intent.dustLimitAtoms * BigInt(totals.tokenOutputs);
  const minimumFeeAtoms =
    BigInt(predicted.wire.length) > required
      ? BigInt(predicted.wire.length)
      : required;
  if (totals.fee < minimumFeeAtoms)
    throw Error("native fee below byte or token-output floor");
  const requests: FullSignatureRequest[] = [];
  intent.inputs.forEach((input, i) =>
    witnesses(input).forEach((w, j) => {
      const m = w.artifact.methods.find((x) => x.name === w.methodName)!;
      const branchIndex =
        input.kind === "spend"
          ? input.coin.paths[input.pathIndex]![j]!
          : undefined;
      const selector =
        input.kind === "mint"
          ? concat(
              Uint8Array.of(3),
              unhex(input.artifact.policy.root, 32),
              uint(totals.deltas[input.artifact.policy.root]!, 16),
              unhex(m.leaf, 32),
            )
          : concat(
              Uint8Array.of(1),
              u32(i),
              u32(branchIndex!),
              unhex(m.leaf, 32),
            );
      const digest = hex(
        tagged(
          "sighash",
          concat(
            unhex(intent.chainId, 32),
            Uint8Array.of(0),
            unhex(initial.txid, 32),
            initial.coinsRoot,
            selector,
          ),
        ),
      );
      for (const arg of m.args)
        if (arg.type === "Signature")
          requests.push({
            key: `${i}:${j}:${arg.name}`,
            argument: arg.name,
            mode: 0,
            digest,
            inputIndex: i,
            witnessIndex: j,
            ...(input.kind === "mint"
              ? {
                  tokenId: input.artifact.policy.root,
                  positiveDelta: totals.deltas[input.artifact.policy.root],
                }
              : { branchIndex: branchIndex! }),
            leaf: m.leaf,
            feeAtoms: totals.fee,
          });
    }),
  );
  return {
    intent,
    seal: snapshot(intent),
    unsignedWire: initial.wire,
    projectedFullBytes: predicted.wire.length,
    txid: initial.txid,
    feeAtoms: totals.fee,
    minimumFeeAtoms,
    tokenDeltas: totals.deltas,
    tokenBurns: totals.burns,
    requests,
    stages,
  };
}
export function finalizeTransactionCall(
  plan: TransactionPlan,
  signatures: Record<string, Uint8Array>,
): TransactionFinal {
  if (snapshot(plan.intent) !== plan.seal)
    throw Error("stale transaction plan");
  const fresh = prepareTransactionCall(plan.intent);
  if (
    fresh.txid !== plan.txid ||
    hex(fresh.unsignedWire) !== hex(plan.unsignedWire) ||
    fresh.projectedFullBytes !== plan.projectedFullBytes ||
    fresh.feeAtoms !== plan.feeAtoms ||
    fresh.minimumFeeAtoms !== plan.minimumFeeAtoms ||
    snapshot(fresh.tokenDeltas) !== snapshot(plan.tokenDeltas) ||
    snapshot(fresh.tokenBurns) !== snapshot(plan.tokenBurns) ||
    snapshot(fresh.requests) !== snapshot(plan.requests)
  )
    throw Error("stale transaction plan");
  if (
    snapshot(Object.keys(signatures).sort()) !==
    snapshot(fresh.requests.map((x) => x.key).sort())
  )
    throw Error("signature slots mismatch");
  const final = hashParts(
    plan.intent,
    plan.intent.inputs.map((x, i) => valuesFor(x, i, signatures)),
  );
  if (final.wire.length !== plan.projectedFullBytes)
    throw Error("projected wire length mismatch");
  if (plan.feeAtoms < BigInt(final.wire.length))
    throw Error("native fee below final byte floor");
  return { wire: final.wire, txid: final.txid, txhash: final.txhash, stages };
}

export {
  DEFAULT_DUST_LIMIT_ATOMS,
  DEFAULT_FEERATE_PER_KCU,
  DEFAULT_SDK_PADDING_BPS,
  DEFAULT_TX_KNEE_SHIFT,
  estimateTransactionCuAndFee,
  simulateFeeAndAdjustChange,
  type FeeSimulationOptions,
  type FeeSimulationResult,
  type SimInput,
  type SimOutput,
  type SimTransactionLike,
  type SimWitness,
  type SimWitnessMethod,
  type TransactionFeeEstimate,
} from "./runtime.js";

