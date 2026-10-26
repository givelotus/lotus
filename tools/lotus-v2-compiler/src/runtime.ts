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
// Offline negative-fixture construction only; this does not verify an invocation.
export function encodePaymentWireUnchecked(a: PaymentArtifact, c: PaymentContext, signature: Uint8Array): Uint8Array {
  assertArtifact(a);
  if (!(signature instanceof Uint8Array) || signature.length !== 64) throw new Error('FULL signature must be 64 bytes');
  preparePayment(a, c);
  return wire(a, c, signature);
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
  const lock = c.lock ?? 0n;
  if ((lock & 255n) > 2n || ((lock & 255n) === 0n && lock !== 0n)) throw new Error('invalid P01 lock encoding');
  if (c.sequence !== 0xffffffff && (c.sequence & ~0x40ffff) !== 0) throw new Error('invalid P01 sequence bits');
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

// ---------------------------------------------------------------------------
// SDK Deterministic Transaction CU Simulator & Auto-Change Output Adjuster

export const DEFAULT_FEERATE_PER_KCU = 1000n;
export const DEFAULT_SDK_PADDING_BPS = 500;
export const DEFAULT_TX_KNEE_SHIFT = 17n;
export const DEFAULT_DUST_LIMIT_ATOMS = 546n;

export type SimOutput = {
  flags?: 0 | 1 | 2 | 3;
  value: bigint;
  tokenId?: string;
  branches: string[];
  paths: number[][];
};

export type SimWitnessMethod = {
  name: string;
  invocation?: 'spend' | 'mint';
  mintAmountParam?: string;
  args: { name: string; type: string }[];
  scriptHex: string;
  leaf: string;
  proof: string[];
  root: string;
  staticResources?: {
    scriptBytes: number;
    opcodes: number;
    maxStackItems?: number;
    helperExpansions?: number;
    dynamicSignatureChecks?: number;
  };
};

export type SimWitness = {
  artifact: {
    policy: { root: string };
    methods: SimWitnessMethod[];
  };
  methodName: string;
  args?: Record<string, Uint8Array | bigint | boolean | null>;
};

export type SimInput =
  | {
      kind: 'spend';
      prevTxid?: string;
      prevIndex?: number;
      sequence?: number;
      coin: SimOutput;
      pathIndex?: number;
      witnesses?: SimWitness[];
      scriptBytes?: number;
      proofDepth?: number;
      signatureCount?: number;
      executedCu?: bigint | number;
    }
  | {
      kind: 'mint';
      artifact: {
        policy: { root: string };
        methods: SimWitnessMethod[];
      };
      methodName: string;
      args?: Record<string, Uint8Array | bigint | boolean | null>;
      executedCu?: bigint | number;
    }
  | {
      kind?: 'spend';
      value: bigint;
      flags?: 0 | 1 | 2 | 3;
      tokenId?: string;
      branches?: string[];
      paths?: number[][];
      scriptBytes?: number;
      proofDepth?: number;
      signatureCount?: number;
      executedCu?: bigint | number;
    };

export type FeeSimulationOptions = {
  feeratePerKCu?: bigint | number;
  sdkPaddingBps?: number | bigint;
  executedCu?: bigint | number;
  kneeShift?: bigint | number;
  dustLimitAtoms?: bigint | number;
  changeOutputIndex?: number;
};

export type SimTransactionLike =
  | {
      artifact: PaymentArtifact;
      context: PaymentContext;
      feeratePerKCu?: bigint | number;
      sdkPaddingBps?: number | bigint;
      executedCu?: bigint | number;
      kneeShift?: bigint | number;
      dustLimitAtoms?: bigint | number;
      changeOutputIndex?: number;
    }
  | {
      profile?: string;
      chainId?: string;
      lock?: bigint;
      dustLimitAtoms?: bigint | number;
      wireBytes?: number;
      inputs: readonly SimInput[];
      outputs: readonly SimOutput[];
      feeratePerKCu?: bigint | number;
      sdkPaddingBps?: number | bigint;
      executedCu?: bigint | number;
      kneeShift?: bigint | number;
      changeOutputIndex?: number;
    };

export type TransactionFeeEstimate = {
  wireBytes: number;
  wireCu: bigint;
  inputOutputCu: bigint;
  vmCu: bigint;
  linearCu: bigint;
  quadraticSurchargeCu: bigint;
  effectiveCu: bigint;
  sdkPaddingBps: number;
  paddingCu: bigint;
  paddedCu: bigint;
  feeratePerKCu: bigint;
  cuFeeAtoms: bigint;
  byteFloorAtoms: bigint;
  tokenOutputCount: number;
  dustLimitAtoms: bigint;
  tokenBurnFloorAtoms: bigint;
  minimumFeeAtoms: bigint;
  requiredFeeAtoms: bigint;
};

export type FeeSimulationResult<TOut extends SimOutput = SimOutput> = {
  estimate: TransactionFeeEstimate;
  changeOutputIndex: number;
  totalNativeInputs: bigint;
  nonChangeNativeOutputs: bigint;
  requiredFeeAtoms: bigint;
  feeAtoms: bigint;
  changeValue: bigint;
  adjustedOutputs: TOut[];
  adjustedIntent?: Record<string, unknown> & { outputs: TOut[] };
  adjustedContext?: PaymentContext;
};

function encodeSimOutputBytes(o: SimOutput, overrideValue?: bigint): Uint8Array {
  const flags = (o.flags ?? (o.tokenId !== undefined ? 1 : 0)) as 0 | 1 | 2 | 3;
  const token = !!(flags & 1);
  const val = overrideValue !== undefined ? overrideValue : o.value >= 0n ? o.value : 0n;
  const branches = o.branches?.length ? o.branches : ['11'.repeat(32)];
  const paths = flags & 2 ? [] : o.paths?.length ? o.paths : [[0]];
  return concat(
    Uint8Array.of(flags),
    uint(val, 8),
    ...(token ? [unhex(o.tokenId ?? '11'.repeat(32), 32)] : []),
    cs(branches.length),
    ...branches.map(x => unhex(x, 32)),
    cs(paths.length),
    ...paths.map(p => concat(cs(p.length), ...p.map(cs))),
  );
}

function encodeSimArgBytes(type: string, value: Uint8Array | bigint | boolean | null | undefined): Uint8Array {
  if (type === 'Signature') return new Uint8Array(64);
  if (type === 'Int' || type === 'Amount' || type === 'Bool') return new Uint8Array(16);
  if (['PublicKey', 'Bytes32', 'TokenId', 'MethodLeafHash', 'ContractRootHash'].includes(type)) return new Uint8Array(32);
  if (value instanceof Uint8Array) return value;
  const m = /^Bytes\(([0-9]+)\)$/.exec(type);
  return new Uint8Array(m ? Number(m[1]) : 32);
}

function encodeSimWitnessFull(w: SimWitness): { bytes: Uint8Array; scriptBytes: number; proofDepth: number; opcodes: number; sigChecks: number } {
  const m = w.artifact.methods.find(x => x.name === w.methodName);
  if (!m) throw new Error(`unknown method ${w.methodName}`);
  const script = unhex(m.scriptHex);
  const argBytes = m.args.map(a => bytes(encodeSimArgBytes(a.type, w.args?.[a.name])));
  const full = concat(
    bytes(script),
    cs(m.proof.length),
    ...m.proof.map(x => unhex(x, 32)),
    cs(argBytes.length),
    ...argBytes,
  );
  const sigCount = m.args.filter(a => a.type === 'Signature').length;
  return {
    bytes: full,
    scriptBytes: script.length,
    proofDepth: m.proof.length,
    opcodes: m.staticResources?.opcodes ?? Math.max(1, script.length),
    sigChecks: m.staticResources?.dynamicSignatureChecks ?? sigCount,
  };
}

function isPaymentContextTx(tx: SimTransactionLike): tx is Extract<SimTransactionLike, { artifact: PaymentArtifact; context: PaymentContext }> {
  return 'artifact' in tx && 'context' in tx;
}

/**
 * Deterministically estimate a Lotus V2 transaction's wire size, unified Cost Units (`cu`),
 * parabolic effective cost $C_{\text{tx}}$, SDK-padded CU fee, and mandatory byte / C14a
 * token-output burn floors.
 */
export function estimateTransactionCuAndFee(
  tx: SimTransactionLike,
  options: FeeSimulationOptions = {},
): TransactionFeeEstimate {
  const feerateRaw = options.feeratePerKCu ?? tx.feeratePerKCu ?? DEFAULT_FEERATE_PER_KCU;
  const feeratePerKCu = BigInt(feerateRaw);
  if (feeratePerKCu <= 0n) throw new Error('feeratePerKCu must be positive');

  const paddingRaw = options.sdkPaddingBps ?? tx.sdkPaddingBps ?? DEFAULT_SDK_PADDING_BPS;
  const sdkPaddingBps = Number(paddingRaw);
  if (!Number.isInteger(sdkPaddingBps) || sdkPaddingBps < 0) throw new Error('sdkPaddingBps must be a non-negative integer');

  const kneeShift = BigInt(options.kneeShift ?? tx.kneeShift ?? DEFAULT_TX_KNEE_SHIFT);
  if (kneeShift < 0n) throw new Error('kneeShift must be non-negative');

  const dustRaw = options.dustLimitAtoms ?? tx.dustLimitAtoms ?? DEFAULT_DUST_LIMIT_ATOMS;
  const dustLimitAtoms = BigInt(dustRaw);
  if (dustLimitAtoms < 0n) throw new Error('dustLimitAtoms must be non-negative');

  const explicitExecutedCu = options.executedCu ?? tx.executedCu;
  if (explicitExecutedCu !== undefined && BigInt(explicitExecutedCu) < 0n) {
    throw new Error('executedCu must be non-negative');
  }

  let wireBytes = 0;
  let inputOutputCu = 0n;
  let defaultVmCu = 0n;
  let tokenOutputCount = 0;

  if (isPaymentContextTx(tx)) {
    const { artifact, context } = tx;
    const h = header(context);
    const fullIn = inputParts(artifact, context, new Uint8Array(64)).full;
    const outEncoded = context.outputs.map(o => encodeSimOutputBytes(o));
    wireBytes = h.length + fullIn.length + outEncoded.reduce((s, b) => s + b.length, 0);
    const coinBytes = encodeSimOutputBytes(context.coin).length;
    inputOutputCu = BigInt(coinBytes) + 64n + BigInt(context.outputs.length) * 32n;
    defaultVmCu = 2n * 4n + 200n + 34n;
    tokenOutputCount = 0;
  } else {
    if (!Array.isArray(tx.inputs) || !tx.inputs.length) throw new Error('transaction requires at least one input');
    if (!Array.isArray(tx.outputs)) throw new Error('transaction outputs required');
    let computedInputBytes = 0;
    for (const input of tx.inputs) {
      if (input.kind === 'mint') {
        const w = encodeSimWitnessFull({ artifact: input.artifact, methodName: input.methodName, args: input.args });
        // 32B root + 4B prevIndex(0) + 4B sequence + 1B kind(3) + witness
        computedInputBytes += 32 + 4 + 4 + 1 + w.bytes.length;
        inputOutputCu += 64n + BigInt(w.proofDepth) * 32n;
        defaultVmCu += input.executedCu !== undefined
          ? BigInt(input.executedCu)
          : BigInt(w.opcodes) * 4n + BigInt(w.sigChecks) * 200n + BigInt(w.scriptBytes);
      } else if ('coin' in input && input.coin) {
        const spend = input as Extract<SimInput, { coin: SimOutput }>;
        const coinBytes = encodeSimOutputBytes(spend.coin);
        inputOutputCu += BigInt(coinBytes.length) + 64n;
        if (spend.witnesses && spend.witnesses.length > 0) {
          const encodedWitnesses = spend.witnesses.map(encodeSimWitnessFull);
          const wsLen = encodedWitnesses.reduce((s: number, w) => s + w.bytes.length, 0);
          computedInputBytes += 32 + 4 + 4 + 1 + cs(spend.pathIndex ?? 0).length + cs(encodedWitnesses.length).length + wsLen;
          for (const w of encodedWitnesses) {
            inputOutputCu += BigInt(w.proofDepth) * 32n;
            if (spend.executedCu === undefined) {
              defaultVmCu += BigInt(w.opcodes) * 4n + BigInt(w.sigChecks) * 200n + BigInt(w.scriptBytes);
            }
          }
          if (spend.executedCu !== undefined) defaultVmCu += BigInt(spend.executedCu);
        } else {
          const scriptBytes = spend.scriptBytes ?? 34;
          const proofDepth = spend.proofDepth ?? 0;
          const sigCount = spend.signatureCount ?? 1;
          const witnessLen = cs(scriptBytes).length + scriptBytes + cs(proofDepth).length + proofDepth * 32 + 1 + sigCount * 65;
          computedInputBytes += 32 + 4 + 4 + 1 + 1 + 1 + witnessLen;
          inputOutputCu += BigInt(proofDepth) * 32n;
          defaultVmCu += spend.executedCu !== undefined
            ? BigInt(spend.executedCu)
            : BigInt(scriptBytes) + BigInt(sigCount) * 200n + 8n;
        }
      } else {
        const light = input as Extract<SimInput, { value: bigint }>;
        const coinBytes = encodeSimOutputBytes({
          flags: light.flags ?? 0,
          value: light.value,
          ...(light.tokenId ? { tokenId: light.tokenId } : {}),
          branches: light.branches ?? ['11'.repeat(32)],
          paths: light.paths ?? [[0]],
        });
        const scriptBytes = light.scriptBytes ?? 34;
        const proofDepth = light.proofDepth ?? 0;
        const sigCount = light.signatureCount ?? 1;
        const witnessLen = cs(scriptBytes).length + scriptBytes + cs(proofDepth).length + proofDepth * 32 + 1 + sigCount * 65;
        computedInputBytes += 32 + 4 + 4 + 1 + 1 + 1 + witnessLen;
        inputOutputCu += BigInt(coinBytes.length) + 64n + BigInt(proofDepth) * 32n;
        defaultVmCu += light.executedCu !== undefined
          ? BigInt(light.executedCu)
          : BigInt(scriptBytes) + BigInt(sigCount) * 200n + 8n;
      }
    }
    let computedOutputBytes = 0;
    for (const o of tx.outputs) {
      const encoded = encodeSimOutputBytes(o);
      computedOutputBytes += encoded.length;
      const isToken = !!(((o.flags ?? 0) & 1) || o.tokenId !== undefined);
      if (isToken) {
        tokenOutputCount++;
        inputOutputCu += 64n;
      } else {
        inputOutputCu += 32n;
      }
    }
    wireBytes = tx.wireBytes !== undefined ? tx.wireBytes : 16 + computedInputBytes + computedOutputBytes;
  }

  const wireCu = BigInt(wireBytes);
  const vmCu = explicitExecutedCu !== undefined ? BigInt(explicitExecutedCu) : defaultVmCu;
  const linearCu = wireCu + inputOutputCu + vmCu;
  const quadraticSurchargeCu = (linearCu * linearCu) >> kneeShift;
  const effectiveCu = linearCu + quadraticSurchargeCu;
  const paddingCu = (effectiveCu * BigInt(sdkPaddingBps) + 9999n) / 10000n;
  const paddedCu = effectiveCu + paddingCu;
  const cuFeeAtoms = (paddedCu * feeratePerKCu + 999n) / 1000n;
  const byteFloorAtoms = BigInt(wireBytes);
  const tokenBurnFloorAtoms = 2n * dustLimitAtoms * BigInt(tokenOutputCount);
  const minimumFeeAtoms = byteFloorAtoms > tokenBurnFloorAtoms ? byteFloorAtoms : tokenBurnFloorAtoms;
  const requiredFeeAtoms = cuFeeAtoms > minimumFeeAtoms ? cuFeeAtoms : minimumFeeAtoms;

  return {
    wireBytes,
    wireCu,
    inputOutputCu,
    vmCu,
    linearCu,
    quadraticSurchargeCu,
    effectiveCu,
    sdkPaddingBps,
    paddingCu,
    paddedCu,
    feeratePerKCu,
    cuFeeAtoms,
    byteFloorAtoms,
    tokenOutputCount,
    dustLimitAtoms,
    tokenBurnFloorAtoms,
    minimumFeeAtoms,
    requiredFeeAtoms,
  };
}

function isNativeSpendableOutput(o: SimOutput): boolean {
  const flags = o.flags ?? (o.tokenId !== undefined ? 1 : 0);
  return flags === 0 && o.tokenId === undefined;
}

/**
 * Simulate transaction CU and mandatory fee floors (including SDK safety padding and C14a
 * token-output burn floors) and automatically adjust the designated native change output's
 * `value`, rejecting if native inputs are insufficient or if change would fall below `dustLimit`.
 */
export function simulateFeeAndAdjustChange<TOut extends SimOutput = SimOutput>(
  tx: SimTransactionLike,
  options: FeeSimulationOptions = {},
): FeeSimulationResult<TOut> {
  const rawOutputs = (isPaymentContextTx(tx) ? tx.context.outputs : tx.outputs) as readonly TOut[];
  if (!Array.isArray(rawOutputs) || !rawOutputs.length) {
    throw new Error('transaction must have at least one output to adjust change');
  }
  const explicitChangeIdx = options.changeOutputIndex ?? tx.changeOutputIndex;
  let changeOutputIndex = -1;
  if (explicitChangeIdx !== undefined) {
    if (!Number.isInteger(explicitChangeIdx) || explicitChangeIdx < 0 || explicitChangeIdx >= rawOutputs.length) {
      throw new Error(`changeOutputIndex ${explicitChangeIdx} is out of range for ${rawOutputs.length} outputs`);
    }
    changeOutputIndex = explicitChangeIdx;
  } else {
    for (let i = rawOutputs.length - 1; i >= 0; i--) {
      if (isNativeSpendableOutput(rawOutputs[i]!)) {
        changeOutputIndex = i;
        break;
      }
    }
    if (changeOutputIndex < 0) {
      throw new Error('no native spendable change output found');
    }
  }
  const targetChangeOutput = rawOutputs[changeOutputIndex]!;
  if (!isNativeSpendableOutput(targetChangeOutput)) {
    throw new Error('designated change output must be a native spendable output');
  }

  let totalNativeInputs = 0n;
  if (isPaymentContextTx(tx)) {
    totalNativeInputs = tx.context.coin.value;
  } else {
    for (const input of tx.inputs) {
      if (input.kind === 'mint') continue;
      if ('coin' in input && input.coin) {
        if (((input.coin.flags ?? 0) & 1) === 0 && input.coin.tokenId === undefined) {
          totalNativeInputs += input.coin.value;
        }
      } else if ('value' in input) {
        if (((input.flags ?? 0) & 1) === 0 && input.tokenId === undefined) {
          totalNativeInputs += input.value;
        }
      }
    }
  }

  let nonChangeNativeOutputs = 0n;
  for (let i = 0; i < rawOutputs.length; i++) {
    if (i === changeOutputIndex) continue;
    const out = rawOutputs[i]!;
    if (((out.flags ?? 0) & 1) === 0 && out.tokenId === undefined) {
      if (out.value < 0n) throw new Error(`output ${i} has negative native value`);
      nonChangeNativeOutputs += out.value;
    }
  }

  // Because output values use fixed-width 8-byte u64 wire encoding, wireBytes and CU are invariant to change value.
  const sanitizedOutputs = rawOutputs.map((o, idx) => (idx === changeOutputIndex ? { ...o, value: 0n } : o));
  const sanitizedTx: SimTransactionLike = isPaymentContextTx(tx)
    ? { ...tx, context: { ...tx.context, outputs: sanitizedOutputs as PaymentOutput[] } }
    : { ...tx, outputs: sanitizedOutputs };

  const estimate = estimateTransactionCuAndFee(sanitizedTx, options);
  const requiredFeeAtoms = estimate.requiredFeeAtoms;
  const requiredTotal = nonChangeNativeOutputs + requiredFeeAtoms;
  if (totalNativeInputs < requiredTotal) {
    throw new Error(
      `insufficient native input funds: inputs total ${totalNativeInputs} atoms, but non-change outputs (${nonChangeNativeOutputs}) + required fee (${requiredFeeAtoms}) require ${requiredTotal} atoms`,
    );
  }
  const changeValue = totalNativeInputs - requiredTotal;
  if (changeValue < estimate.dustLimitAtoms) {
    throw new Error(
      `adjusted change output value (${changeValue} atoms) is below dust limit (${estimate.dustLimitAtoms} atoms)`,
    );
  }

  const adjustedOutputs = rawOutputs.map((o, idx) =>
    idx === changeOutputIndex ? ({ ...o, value: changeValue } as TOut) : ({ ...o } as TOut),
  );

  if (isPaymentContextTx(tx)) {
    const adjustedContext: PaymentContext = {
      ...tx.context,
      outputs: adjustedOutputs as unknown as PaymentOutput[],
    };
    return {
      estimate,
      changeOutputIndex,
      totalNativeInputs,
      nonChangeNativeOutputs,
      requiredFeeAtoms,
      feeAtoms: requiredFeeAtoms,
      changeValue,
      adjustedOutputs,
      adjustedContext,
    };
  }

  const adjustedIntent = {
    ...tx,
    outputs: adjustedOutputs,
  };
  return {
    estimate,
    changeOutputIndex,
    totalNativeInputs,
    nonChangeNativeOutputs,
    requiredFeeAtoms,
    feeAtoms: requiredFeeAtoms,
    changeValue,
    adjustedOutputs,
    adjustedIntent,
  };
}

