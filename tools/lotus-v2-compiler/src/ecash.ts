/** Narrow eCash backend. Portable semantic IR only; no Lotus bytecode reuse. */
import { validateSemanticProgram, type SemanticExpr, type SemanticStmt } from './semantic-ir.js';
import { resolveTarget, checkCapabilities, type SourceSpan, type TargetDiagnostic } from './targets.js';

export type EcashArtifact = {
  schema: 'ecash/script-artifact/1'; target: 'ecash'; targetRevision: string; targetProfile: string;
  entrypoint: string;
  args: { name: string; type: { kind: 'bytes'; length: number } | { kind: 'bool' }; span: SourceSpan }[];
  scriptHex: string;
  sourceMap: { op: string; source: SourceSpan; byteStart: number; byteEnd: number }[];
  /** Bounds assume exactly the declared initial args; CLEANSTACK rejects extras. */
  staticResources: { scriptBytes: number; opCount: number; maxStackItems: number; maxElementBytes: number };
};
export type EcashResult = { ok: true; artifact: EcashArtifact } | { ok: false; diagnostics: TargetDiagnostic[] };

/** Data pushes preserve bytes exactly, including one-byte zero (not OP_0). */
function push(value: Uint8Array): number[] {
  if (!value.length) return [0x00];
  if (value.length === 1 && value[0]! >= 1 && value[0]! <= 16) return [0x50 + value[0]!];
  if (value.length === 1 && value[0] === 0x81) return [0x4f];
  if (value.length <= 75) return [value.length, ...value];
  if (value.length <= 255) return [0x4c, value.length, ...value];
  return [0x4d, value.length & 255, value.length >>> 8, ...value];
}
function number(value: number): Uint8Array {
  const result: number[] = [];
  for (; value; value = Math.floor(value / 256)) result.push(value & 255);
  if (result.length && result[result.length - 1]! & 0x80) result.push(0);
  return Uint8Array.from(result);
}

/** Validate the complete input and capabilities before creating any wire bytes. */
export function compileEcash(input: unknown): EcashResult {
  const checked = validateSemanticProgram(input);
  if (!checked.ok) return checked;
  const target = resolveTarget('ecash');
  const diagnostics = checkCapabilities(target, checked.requirements);
  if (diagnostics.length) return { ok: false, diagnostics };
  const program = checked.program;
  const fail = (message: string, span: SourceSpan = program.span): EcashResult => ({ ok: false,
    diagnostics: [{ code: 'E1210', message: `ecash: ${message}`, span: { ...span } }] });
  // Traverse both arms, including statically false ones. No unsupported or
  // oversized constant can hide in a branch that happens not to execute.
  let largest = 0;
  let violation: SourceSpan | undefined;
  function inspect(expr: SemanticExpr): void {
    if (expr.kind === 'bytes') {
      largest = Math.max(largest, expr.hex.length / 2);
      if (expr.hex.length / 2 > target.limits.maxElementBytes) violation ??= expr.span;
    } else if (expr.kind === 'bool') largest = Math.max(largest, 1);
    else if (expr.kind === 'sha256' || expr.kind === 'hash256') { largest = Math.max(largest, 32); inspect(expr.value); }
    else if (expr.kind === 'equal') { inspect(expr.left); inspect(expr.right); }
  }
  function inspectBody(body: SemanticStmt[]): void {
    for (const stmt of body) {
      inspect(stmt.condition);
      if (stmt.kind === 'if') { inspectBody(stmt.then); inspectBody(stmt.otherwise); }
    }
  }
  for (const arg of program.args) {
    const size = arg.type.kind === 'bytes' ? arg.type.length : 1;
    largest = Math.max(largest, size);
    if (size > target.limits.maxElementBytes) violation ??= arg.span;
  }
  inspectBody(program.body);
  if (violation) return fail(`element exceeds ${target.limits.maxElementBytes} bytes`, violation);
  const stackLimit = target.limits.maxStackItems;
  if (stackLimit === null) return fail('concrete stack limit required');
  if (program.args.length > stackLimit) return fail('initial declared stack exceeds limit');

  const wire: number[] = [];
  const sourceMap: EcashArtifact['sourceMap'] = [];
  let depth = program.args.length, peak = depth, ops = 0;
  function emit(op: string, bytes: number[], delta: number, span: SourceSpan, counted = true): void {
    const start = wire.length;
    wire.push(...bytes);
    sourceMap.push({ op, source: { ...span }, byteStart: start, byteEnd: wire.length });
    if (counted && bytes[0]! > 0x60) ops++;
    depth += delta;
    if (depth < 0) throw Error('eCash backend internal stack underflow');
    peak = Math.max(peak, depth);
  }
  function data(value: Uint8Array, span: SourceSpan): void {
    emit('PUSH', push(value), 1, span, false);
    largest = Math.max(largest, value.length);
  }
  function pick(index: number, span: SourceSpan): void {
    const distance = depth - index - 1;
    if (!distance) emit('DUP', [0x76], 1, span);
    else { data(number(distance), span); emit('PICK', [0x79], 0, span); }
  }
  // Args arrive bottom-to-top; originals remain at their fixed bottom indexes.
  // Validate every declaration, including unused inputs, before body execution.
  program.args.forEach((arg, index) => {
    pick(index, arg.span);
    if (arg.type.kind === 'bytes') {
      emit('SIZE', [0x82], 1, arg.span);
      data(number(arg.type.length), arg.span);
      emit('EQUALVERIFY', [0x88], -2, arg.span);
      emit('DROP', [0x75], -1, arg.span);
    } else {
      emit('DUP', [0x76], 1, arg.span);
      data(new Uint8Array(), arg.span);
      emit('EQUAL', [0x87], -1, arg.span);
      emit('SWAP', [0x7c], 0, arg.span);
      data(Uint8Array.of(1), arg.span);
      emit('EQUAL', [0x87], -1, arg.span);
      emit('BOOLOR', [0x9b], -1, arg.span);
      emit('VERIFY', [0x69], -1, arg.span);
    }
  });
  function expression(expr: SemanticExpr): void {
    switch (expr.kind) {
      case 'bytes': data(Uint8Array.from(Buffer.from(expr.hex, 'hex')), expr.span); break;
      case 'bool': data(expr.value ? Uint8Array.of(1) : new Uint8Array(), expr.span); break;
      case 'arg': pick(program.args.findIndex(arg => arg.name === expr.name), expr.span); break;
      case 'sha256': case 'hash256':
        expression(expr.value); emit(expr.kind.toUpperCase(), [expr.kind === 'sha256' ? 0xa8 : 0xaa], 0, expr.span); break;
      case 'equal':
        expression(expr.left); expression(expr.right); emit('EQUAL', [0x87], -1, expr.span); break;
    }
  }
  function body(statements: SemanticStmt[]): void {
    for (const stmt of statements) {
      expression(stmt.condition);
      if (stmt.kind === 'require') emit('VERIFY', [0x69], -1, stmt.span);
      else {
        emit('IF', [0x63], -1, stmt.span);
        const base = depth;
        body(stmt.then);
        if (depth !== base) throw Error('eCash backend internal branch stack imbalance');
        emit('ELSE', [0x67], 0, stmt.span);
        body(stmt.otherwise);
        if (depth !== base) throw Error('eCash backend internal branch stack imbalance');
        emit('ENDIF', [0x68], 0, stmt.span);
      }
    }
  }
  body(program.body);
  for (const arg of program.args) emit('DROP', [0x75], -1, arg.span);
  data(Uint8Array.of(1), program.span);
  if (depth !== 1) throw Error('eCash backend internal final stack imbalance');
  if (wire.length > target.limits.maxScriptBytes) return fail(`script exceeds ${target.limits.maxScriptBytes} bytes`);
  if (ops > target.limits.maxOps) return fail(`script exceeds ${target.limits.maxOps} opcodes (both branches counted)`);
  if (peak > stackLimit) return fail(`stack exceeds ${stackLimit} items`);
  return { ok: true, artifact: {
    schema: 'ecash/script-artifact/1', target: 'ecash', targetRevision: target.revision, targetProfile: target.profile,
    entrypoint: program.entrypoint, args: program.args.map(arg => ({ ...arg, type: { ...arg.type }, span: { ...arg.span } })),
    scriptHex: Buffer.from(wire).toString('hex'), sourceMap,
    staticResources: { scriptBytes: wire.length, opCount: ops, maxStackItems: peak, maxElementBytes: largest },
  } };
}
