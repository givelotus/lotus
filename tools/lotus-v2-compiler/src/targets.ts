/** Compiler target capabilities are implemented slices, not network support claims. */
export type TargetId = 'lotus-v2' | 'ecash';
export type SemanticCapability = 'bytes' | 'bool' | 'sha256' | 'hash256' | 'byte-equality' | 'require' | 'if'
  | 'lotus-int128' | 'transaction-signature' | 'transaction-reflection' | 'lotus-loop' | 'lotus-token';
export type SourceSpan = { start: number; end: number; file?: string };
export type TargetDiagnostic = { code: string; message: string; span?: SourceSpan; capability?: string };
export type CapabilityRequirement = { capability: SemanticCapability; span?: SourceSpan };
export type TargetDescriptor = {
  readonly id: TargetId;
  readonly revision: string;
  readonly profile: string;
  readonly capabilities: readonly SemanticCapability[];
  readonly limits: Readonly<{ maxScriptBytes: number; maxElementBytes: number; maxStackItems: number | null; maxOps: number }>;
  readonly capabilityScope: 'compiler-implemented';
  /** null stack limit requires the caller's explicit invocation profile. */
  readonly limitsScope: 'compiler' | 'vm-consensus';
  readonly semantics: Readonly<{
    booleanEncoding: 'canonical-int128-le' | 'minimal-scriptnum';
    booleanConsumers: 'canonical-zero-or-one' | 'script-truthiness-with-minimalif';
    integerModel: 'signed-int128' | 'not-supported-by-compiler';
    signatureModel: 'lotus-p01' | 'not-supported-by-compiler';
    entrypoint: 'merkle-branch-per-method' | 'single-method-script';
    commitmentModel: 'lotus-branches-and-paths' | 'external-script-wrapper-required';
  }>;
  /** Exact pin's STANDARD_SCRIPT_VERIFY_FLAGS plus MINIMALIF; research profile, not network defaults. */
  readonly evaluationFlags: readonly string[];
  readonly maxMethods: number;
  readonly evaluationFlagPolicy: 'caller-invocation-profile' | 'standard-plus-minimalif-research';
  readonly sourceTree?: string;
};

export const ECASH_REVISION = '1fb7db17c176cdea8a2c60d887891589382ee4e3';
const portable = ['bytes', 'bool', 'sha256', 'hash256', 'byte-equality', 'require', 'if'] as const;
const lotusOnly = ['lotus-int128', 'transaction-signature', 'transaction-reflection', 'lotus-loop', 'lotus-token'] as const;

const lotus: TargetDescriptor = Object.freeze({
  id: 'lotus-v2', revision: 'P01-P02-P03-candidate-2026-10-14', profile: 'P01-P02-P03-candidate-2026-10-14',
  capabilities: Object.freeze([...portable, ...lotusOnly]), capabilityScope: 'compiler-implemented', limitsScope: 'compiler',
  limits: Object.freeze({ maxScriptBytes: 8192, maxElementBytes: 8192, maxStackItems: null, maxOps: 4096 }),
  semantics: Object.freeze({ booleanEncoding: 'canonical-int128-le', booleanConsumers: 'canonical-zero-or-one',
    integerModel: 'signed-int128', signatureModel: 'lotus-p01', entrypoint: 'merkle-branch-per-method',
    commitmentModel: 'lotus-branches-and-paths' }),
  evaluationFlags: Object.freeze([]), maxMethods: 16, evaluationFlagPolicy: 'caller-invocation-profile',
});
const ecash: TargetDescriptor = Object.freeze({
  id: 'ecash', revision: ECASH_REVISION, profile: 'ecash-script-minimal-cleanstack-1fb7db17',
  capabilities: Object.freeze([...portable]), capabilityScope: 'compiler-implemented', limitsScope: 'vm-consensus',
  limits: Object.freeze({ maxScriptBytes: 10000, maxElementBytes: 520, maxStackItems: 1000, maxOps: 201 }),
  semantics: Object.freeze({ booleanEncoding: 'minimal-scriptnum', booleanConsumers: 'script-truthiness-with-minimalif',
    integerModel: 'not-supported-by-compiler', signatureModel: 'not-supported-by-compiler',
    entrypoint: 'single-method-script', commitmentModel: 'external-script-wrapper-required' }),
  maxMethods: 1, evaluationFlagPolicy: 'standard-plus-minimalif-research',
  sourceTree: 'b2e4a0a9f57c593129028352d5dbb0c4ff294cdb',
  evaluationFlags: Object.freeze(['P2SH', 'STRICTENC', 'SIGHASH_FORKID', 'LOW_S', 'NULLFAIL', 'MINIMALDATA',
    'SCHNORR_MULTISIG', 'ENFORCE_SIGCHECKS', 'DERSIG', 'SIGPUSHONLY', 'DISCOURAGE_UPGRADABLE_NOPS',
    'CLEANSTACK', 'CHECKLOCKTIMEVERIFY', 'CHECKSEQUENCEVERIFY', 'DISALLOW_SEGWIT_RECOVERY', 'INPUT_SIGCHECKS', 'MINIMALIF']),
});

/** Exact identifiers only: aliases and inherited defaults are caller policy. */
export function resolveTarget(id: string): TargetDescriptor {
  if (id === 'lotus-v2') return lotus;
  if (id === 'ecash') return ecash;
  throw new Error(`Unknown compiler target ${JSON.stringify(id)}; expected lotus-v2 or ecash`);
}

const ecashReasons: Readonly<Record<typeof lotusOnly[number], string>> = Object.freeze({
  'lotus-int128': 'Lotus Int requires exact sixteen-byte signed int128 arithmetic; the eCash compiler slice has no equivalent integer lowering.',
  'transaction-signature': 'Lotus transaction-signature semantics require the P01 authenticated message and key/signature ABI; eCash uses a different transaction/signature ABI and its signing lowering is not implemented.',
  'transaction-reflection': 'Lotus transaction reflection requires authenticated input/output and branch/path semantics; equivalent eCash compiler lowering is not implemented.',
  'lotus-loop': 'Lotus input/output enumeration requires transaction-context iteration; the eCash compiler slice implements no equivalent loop lowering.',
  'lotus-token': 'Lotus token mint/spend semantics and continuation commitments are not implemented by the eCash compiler slice.',
});

/** Reject semantic obligations before bytecode emission; preserve occurrence spans. */
export function checkCapabilities(target: TargetDescriptor, requirements: readonly CapabilityRequirement[]): TargetDiagnostic[] {
  return requirements.flatMap(requirement => {
    if (target.capabilities.includes(requirement.capability)) return [];
    const reason = target.id === 'ecash' && Object.hasOwn(ecashReasons, requirement.capability)
      ? ecashReasons[requirement.capability as keyof typeof ecashReasons]
      : `Capability ${JSON.stringify(requirement.capability)} is not implemented by target ${target.id}.`;
    return [{ code: 'E1201', message: `${target.id} (${target.revision}): ${reason}`,
      ...(requirement.span ? { span: { ...requirement.span } } : {}), capability: requirement.capability }];
  });
}

/** eCash method dispatch must be designed explicitly, never inherited from Lotus. */
export function checkEntrypoint(target: TargetDescriptor, methodCount: number, span?: SourceSpan): TargetDiagnostic[] {
  if (!Number.isSafeInteger(methodCount) || methodCount < 1) return [{ code: 'E1202',
    message: 'A target entrypoint requires a positive safe integer method count.', ...(span ? { span: { ...span } } : {}) }];
  if (target.semantics.entrypoint === 'single-method-script' && methodCount !== 1) return [{ code: 'E1202',
    message: `${target.id} emits one method script; ${methodCount} methods require an explicit selector/dispatch ABI, which is not implemented. Lotus branch proofs cannot select eCash entrypoints.`,
    ...(span ? { span: { ...span } } : {}) }];
  if (methodCount > target.maxMethods) return [{ code: 'E1202',
    message: `${target.id} compiler supports at most ${target.maxMethods} methods; received ${methodCount}.`,
    ...(span ? { span: { ...span } } : {}) }];
  return [];
}
