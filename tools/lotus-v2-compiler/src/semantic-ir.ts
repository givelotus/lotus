/** Portable typed expression IR. Contains no opcode, transaction or chain constants. */
import type { SourceSpan, CapabilityRequirement, TargetDiagnostic } from './targets.js';

/** Byte widths are exact, including the empty byte string. */
export type SemanticType = { kind: 'bytes'; length: number } | { kind: 'bool' };
export type SemanticExpr =
  | { kind: 'bytes'; hex: string; span: SourceSpan }
  | { kind: 'bool'; value: boolean; span: SourceSpan }
  | { kind: 'arg'; name: string; span: SourceSpan }
  | { kind: 'sha256' | 'hash256'; value: SemanticExpr; span: SourceSpan }
  | { kind: 'equal'; left: SemanticExpr; right: SemanticExpr; span: SourceSpan };
export type SemanticStmt =
  | { kind: 'require'; condition: SemanticExpr; span: SourceSpan }
  | { kind: 'if'; condition: SemanticExpr; then: SemanticStmt[]; otherwise: SemanticStmt[]; span: SourceSpan };
export type SemanticProgram = {
  schema: 'lotus/semantic-ir/1'; entrypoint: string;
  args: { name: string; type: SemanticType; span: SourceSpan }[];
  body: SemanticStmt[]; span: SourceSpan;
};
export type SemanticValidation =
  | { ok: true; program: SemanticProgram; requirements: CapabilityRequirement[] }
  | { ok: false; diagnostics: TargetDiagnostic[] };

/** Parser/validation safety ceilings, not target execution or consensus limits. */
export const SEMANTIC_IR_LIMITS = Object.freeze({ maxBytes: 8192, maxDepth: 64, maxNodes: 8192, maxArgs: 256 });

class InvalidSemanticIR extends Error {
  constructor(readonly diagnostic: TargetDiagnostic) { super(diagnostic.message); }
}
function record(value: unknown): value is Record<string, unknown> {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) return false;
  const proto = Object.getPrototypeOf(value);
  return (proto === null || proto === Object.prototype) && Object.getOwnPropertySymbols(value).length === 0
    && Object.values(Object.getOwnPropertyDescriptors(value)).every(descriptor => Object.hasOwn(descriptor, 'value'));
}
function validSpan(value: unknown): value is SourceSpan {
  return record(value) && Object.keys(value).every(key => ['start', 'end', 'file'].includes(key))
    && Number.isSafeInteger(value.start) && Number.isSafeInteger(value.end)
    && (value.start as number) >= 0 && (value.end as number) >= (value.start as number)
    && (value.file === undefined || typeof value.file === 'string');
}
function copySpan(value: SourceSpan): SourceSpan {
  return value.file === undefined ? { start: value.start, end: value.end } : { start: value.start, end: value.end, file: value.file };
}
function fail(code: string, message: string, value?: unknown): never {
  const span = record(value) && validSpan(value.span) ? copySpan(value.span) : undefined;
  throw new InvalidSemanticIR({ code: `semantic-ir-${code}`, message, ...(span ? { span } : {}) });
}
function shape(value: unknown, fields: string[], context: string): Record<string, unknown> {
  if (!record(value)) fail('shape', `${context} must be a plain object`, value);
  const extra = Object.keys(value).find(key => !fields.includes(key));
  if (extra !== undefined) fail('shape', `unsupported ${context} field ${extra}`, value);
  for (const field of fields) if (!Object.hasOwn(value, field)) fail('shape', `${context} is missing ${field}`, value);
  return value;
}
function span(value: Record<string, unknown>): SourceSpan {
  if (!validSpan(value.span)) fail('span', 'span requires nonnegative safe UTF-8 byte offsets start <= end and optional file', value);
  return copySpan(value.span);
}
function name(value: unknown, context: string, at: unknown): string {
  if (typeof value !== 'string' || !/^[A-Za-z_][A-Za-z_0-9]*$/.test(value)) fail('name', `${context} must be an identifier`, at);
  return value;
}
function denseArray(value: unknown[], context: string): void {
  if (Object.getOwnPropertySymbols(value).length || Object.keys(value).some(key => !/^(0|[1-9][0-9]*)$/.test(key) || Number(key) >= value.length)) fail('shape', `${context} must contain only array entries`);
  for (let i = 0; i < value.length; i++) {
    const descriptor = Object.getOwnPropertyDescriptor(value, String(i));
    if (!descriptor || !Object.hasOwn(descriptor, 'value')) fail('shape', `${context} must be dense and contain no accessors`);
  }
}
function semanticType(value: unknown, at: unknown): SemanticType {
  if (!record(value)) fail('type', 'argument type must be bytes or bool', at);
  if (value.kind === 'bool') { shape(value, ['kind'], 'Boolean type'); return { kind: 'bool' }; }
  if (value.kind === 'bytes') {
    shape(value, ['kind', 'length'], 'byte type');
    if (!Number.isSafeInteger(value.length) || (value.length as number) < 0 || (value.length as number) > SEMANTIC_IR_LIMITS.maxBytes)
      fail('type', `exact byte length must be 0..${SEMANTIC_IR_LIMITS.maxBytes}`, at);
    return { kind: 'bytes', length: value.length as number };
  }
  fail('unsupported', 'only portable bytes and bool types are supported; integers, signatures and reflection require a chain-specific IR', at);
}
function sameType(left: SemanticType, right: SemanticType): boolean {
  return left.kind === right.kind && (left.kind !== 'bytes' || right.kind === 'bytes' && left.length === right.length);
}

/**
 * Validate imported IR before backend selection. Fail closed on unknown constructs.
 * The returned tree and spans are detached copies; capability occurrences retain
 * source order and are not deduplicated. Equal requires matching exact byte widths
 * (or two Bools); byte padding and Boolean/numeric coercion are never implicit.
 * This checks semantics/shape only, not target support, stack bounds or execution.
 */
export function validateSemanticProgram(input: unknown): SemanticValidation {
  const requirements: CapabilityRequirement[] = [];
  const args = new Map<string, SemanticType>();
  const active = new Set<object>();
  let nodes = 0;
  const requireCapability = (capability: CapabilityRequirement['capability'], at: SourceSpan): void => {
    requirements.push({ capability, span: copySpan(at) });
  };
  const typed = (type: SemanticType, at: SourceSpan): SemanticType => {
    requireCapability(type.kind, at); return type;
  };
  const visit = (value: unknown, depth: number): void => {
    if (depth > SEMANTIC_IR_LIMITS.maxDepth) fail('limit', `IR nesting exceeds ${SEMANTIC_IR_LIMITS.maxDepth}`, value);
    if (++nodes > SEMANTIC_IR_LIMITS.maxNodes) fail('limit', `IR node budget exceeds ${SEMANTIC_IR_LIMITS.maxNodes}`, value);
    if (value !== null && typeof value === 'object') {
      if (active.has(value)) fail('cycle', 'cyclic IR is unsupported', value);
      active.add(value);
    }
  };
  const expression = (value: unknown, depth: number): { node: SemanticExpr; type: SemanticType } => {
    visit(value, depth);
    if (!record(value)) fail('shape', 'expression must be a plain object', value);
    let node: SemanticExpr, type: SemanticType;
    const at = span(value);
    switch (value.kind) {
      case 'bytes': {
        shape(value, ['kind', 'hex', 'span'], 'byte constant');
        if (typeof value.hex !== 'string' || value.hex.length > SEMANTIC_IR_LIMITS.maxBytes * 2 || !/^(?:[0-9a-f]{2})*$/.test(value.hex))
          fail('constant', `byte constant must be lowercase even-length hex of at most ${SEMANTIC_IR_LIMITS.maxBytes} bytes`, value);
        node = { kind: 'bytes', hex: value.hex, span: at }; type = { kind: 'bytes', length: value.hex.length / 2 }; break;
      }
      case 'bool':
        shape(value, ['kind', 'value', 'span'], 'Boolean constant');
        if (typeof value.value !== 'boolean') fail('constant', 'Boolean constant must be true or false', value);
        node = { kind: 'bool', value: value.value, span: at }; type = { kind: 'bool' }; break;
      case 'arg': {
        shape(value, ['kind', 'name', 'span'], 'argument reference');
        const arg = name(value.name, 'argument reference', value), found = args.get(arg);
        if (!found) fail('argument', `unbound argument ${arg}`, value);
        node = { kind: 'arg', name: arg, span: at }; type = { ...found }; break;
      }
      case 'sha256': case 'hash256': {
        shape(value, ['kind', 'value', 'span'], 'hash expression');
        const operand = expression(value.value, depth + 1);
        if (operand.type.kind !== 'bytes') fail('type', `${value.kind} requires bytes`, value);
        node = { kind: value.kind, value: operand.node, span: at }; type = { kind: 'bytes', length: 32 };
        requireCapability(value.kind, at); break;
      }
      case 'equal': {
        shape(value, ['kind', 'left', 'right', 'span'], 'equality expression');
        const left = expression(value.left, depth + 1), right = expression(value.right, depth + 1);
        if (!sameType(left.type, right.type)) fail('type', 'equal requires two Bools or byte values of the same exact length', value);
        node = { kind: 'equal', left: left.node, right: right.node, span: at }; type = { kind: 'bool' };
        requireCapability('byte-equality', at); break;
      }
      default: fail('unsupported', `unsupported portable expression ${typeof value.kind === 'string' ? value.kind : typeof value.kind}; chain-specific integer, signature and reflection operations are unavailable`, value);
    }
    typed(type, at); active.delete(value);
    return { node, type };
  };
  const statements = (value: unknown, depth: number): SemanticStmt[] => {
    if (!Array.isArray(value)) fail('shape', 'statement body must be an array');
    if (value.length > SEMANTIC_IR_LIMITS.maxNodes) fail('limit', 'statement array exceeds IR node budget');
    denseArray(value, 'statement array');
    return value.map(raw => {
      visit(raw, depth);
      if (!record(raw)) fail('shape', 'statement must be a plain object', raw);
      const at = span(raw);
      let result: SemanticStmt;
      if (raw.kind === 'require') {
        shape(raw, ['kind', 'condition', 'span'], 'require statement');
        const condition = expression(raw.condition, depth + 1);
        if (condition.type.kind !== 'bool') fail('type', 'require condition must be Bool', raw);
        requireCapability('require', at); result = { kind: 'require', condition: condition.node, span: at };
      } else if (raw.kind === 'if') {
        shape(raw, ['kind', 'condition', 'then', 'otherwise', 'span'], 'if statement');
        const condition = expression(raw.condition, depth + 1);
        if (condition.type.kind !== 'bool') fail('type', 'if condition must be Bool', raw);
        requireCapability('if', at);
        result = { kind: 'if', condition: condition.node, then: statements(raw.then, depth + 1), otherwise: statements(raw.otherwise, depth + 1), span: at };
      } else fail('unsupported', `unsupported portable statement ${typeof raw.kind === 'string' ? raw.kind : typeof raw.kind}; chain-specific invocation, loops and reflection are unavailable`, raw);
      active.delete(raw); return result;
    });
  };
  try {
    const raw = shape(input, ['schema', 'entrypoint', 'args', 'body', 'span'], 'semantic program');
    if (raw.schema !== 'lotus/semantic-ir/1') fail('schema', 'unsupported semantic IR schema', raw);
    const at = span(raw), entrypoint = name(raw.entrypoint, 'entrypoint', raw);
    visit(raw, 0);
    if (!Array.isArray(raw.args)) fail('shape', 'args must be an array', raw);
    if (raw.args.length > SEMANTIC_IR_LIMITS.maxArgs) fail('limit', `argument count exceeds ${SEMANTIC_IR_LIMITS.maxArgs}`, raw);
    denseArray(raw.args, 'argument array');
    const declarations = raw.args.map(arg => {
      visit(arg, 1);
      const item = shape(arg, ['name', 'type', 'span'], 'argument declaration'), location = span(item);
      const identifier = name(item.name, 'argument name', item);
      if (args.has(identifier)) fail('argument', `duplicate argument ${identifier}`, item);
      const type = semanticType(item.type, item); args.set(identifier, type); typed(type, location);
      active.delete(item); return { name: identifier, type, span: location };
    });
    const program: SemanticProgram = { schema: 'lotus/semantic-ir/1', entrypoint, args: declarations, body: statements(raw.body, 1), span: at };
    return { ok: true, program, requirements };
  } catch (error) {
    if (error instanceof InvalidSemanticIR) return { ok: false, diagnostics: [error.diagnostic] };
    throw error;
  }
}
