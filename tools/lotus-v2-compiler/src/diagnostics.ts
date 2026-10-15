/**
 * Structured compiler diagnostics, source positions and clang/rustc-style rendering.
 *
 * Build-time only. Offsets are UTF-8 byte offsets into the exact source text of a
 * file (schema-2 convention). Reported `line:column` positions are 1-based; the
 * column counts **Unicode scalar values** (code points) from the start of the line,
 * so `é` (2 bytes) or `𝔸` (4 bytes) each advance the column by one and a tab counts
 * as one column. The JSON form additionally carries the raw byte offsets. Excerpts
 * expand tabs to the next multiple of 4 display cells and treat East Asian wide
 * characters as two cells and combining marks as zero, so carets line up in a
 * monospace terminal.
 */
import type { Span } from './compiler.js';

export type Severity = 'error' | 'warning' | 'note';
/** A file plus an optional UTF-8 byte range in it. A missing span marks a file-level diagnostic. */
export type Location = { file: string; span?: Span };
export type Label = { file?: string; span: Span; message: string; primary?: boolean };
export type Related = { file: string; span?: Span; message: string };
export type Diagnostic = {
  severity: Severity;
  /** Stable code, `E` + four digits; see DIAGNOSTIC_CODES and docs. */
  code: string;
  message: string;
  /** Absent only for global diagnostics (e.g. malformed compile options). */
  primary?: Location;
  labels: Label[];
  notes: string[];
  help?: string;
  related: Related[];
};

/** Maximum diagnostics reported by one compile before recovery stops. */
export const MAX_DIAGNOSTICS = 20;

/** Stable codes. Messages may be refined; codes are not reused. */
export const DIAGNOSTIC_CODES: Record<string, string> = {
  E0000: 'fatal input/usage error outside source (CLI)',
  E0001: 'unsupported character',
  E0002: 'source exceeds the UTF-8 size limit',
  E0003: 'unterminated block comment',
  E0004: 'unterminated string literal',
  E0101: 'unexpected token (expected-token list)',
  E0102: 'expected identifier',
  E0103: 'unsupported type',
  E0104: 'Bytes(N) bound outside 1..8192',
  E0105: 'expression nesting depth exceeded',
  E0106: 'control nesting depth exceeded',
  E0107: 'statement budget exceeded',
  E0108: 'loop nesting exceeds two',
  E0109: 'unsupported loop collection',
  E0110: 'unsupported assignment operator',
  E0111: 'unsupported statement',
  E0112: 'malformed import',
  E0113: 'import after declarations',
  E0114: 'visibility modifier on a non-declaration',
  E0115: 'reserved or invalid binding name',
  E0116: 'source has no contract',
  E0117: 'more than 16 methods',
  E0118: 'token method first parameter must be Amount',
  E0119: 'empty contract or method',
  E0120: 'qualified name must be called',
  E0121: 'import requires a package build',
  E0122: 'for inside a helper',
  E0123: 'helper return is missing or not final',
  E0201: 'duplicate parameter',
  E0202: 'duplicate helper',
  E0203: 'duplicate method (case-insensitive)',
  E0204: 'duplicate contract',
  E0205: 'method parameter shadows constructor parameter',
  E0206: 'loop variable shadows a binding',
  E0207: 'duplicate method leaf (identical scripts)',
  E0208: 'let shadows a binding',
  E0301: 'unbound name',
  E0302: 'unknown function',
  E0303: 'unknown contract',
  E0304: 'unknown method',
  E0305: 'unbound or invalid record',
  E0401: 'operand type mismatch',
  E0402: 'invalid unary operand',
  E0403: 'invalid binary operator for operand types',
  E0404: 'condition is not Bool',
  E0405: 'builtin argument type mismatch',
  E0406: 'helper argument type mismatch',
  E0407: 'helper result type mismatch',
  E0408: 'numeric local required',
  E0409: 'invalid assignment target',
  E0410: 'local must be initialized at method top level',
  E0411: 'mint method has no coin',
  E0412: 'introspection field misuse',
  E0413: 'Int literal outside signed 128-bit range',
  E0414: 'let binding type mismatch',
  E0501: 'helper arity mismatch',
  E0502: 'builtin arity or argument form',
  E0503: 'recursive helper',
  E0601: 'compile options require contract and bindings',
  E0602: 'constructor arity mismatch',
  E0603: 'missing constructor binding',
  E0604: 'invalid constructor binding value',
  E0605: 'selected contract does not exist',
  E0701: 'MAX_SCRIPT_BYTES exceeded',
  E0702: 'opcode budget exceeded',
  E0703: 'helper expansion budget exceeded',
  E0704: 'type inference visit budget exceeded',
  E0705: 'dependency scan budget exceeded',
  E0706: 'helper dependency depth exceeded',
  E0707: 'MAX_ELEMENT_BYTES exceeded',
  E0801: 'leaf/root dependency cycle',
  E0802: 'compiler scheduler limit exceeded',
  E0901: 'package manifest error',
  E0902: 'path escapes its root',
  E0903: 'symlink escapes its root',
  E0904: 'path collision under case/Unicode folding',
  E0905: 'undeclared file in a source root',
  E0906: 'missing module or file',
  E0907: 'lotus.lock missing',
  E0908: 'lotus.lock digest mismatch',
  E0909: 'lotus.lock stale',
  E0910: 'package version conflict',
  E0911: 'package dependency cycle',
  E0912: 'module parse error',
  E0913: 'unknown dependency alias',
  E0914: 'module not exported',
  E0915: 'missing imported symbol',
  E0916: 'helper not visible',
  E0917: 'duplicate or ambiguous local name',
  E0918: 'module import cycle',
  E0919: 'declaration-only module rule',
  E0920: 'package graph limit exceeded',
  E0921: 'branch or range selector outside package update',
  E0922: 'module not present in the offline cache',
  E0923: 'invalid git locator',
  E0924: 'git fetch failed',
  E0130: 'explicit invocation marker required',
  E0131: 'language version mismatch',
  E0132: 'unsupported language version',
  E0930: 'invalid program instance binding',
  E0931: 'program root dependency cycle',
  E1200: 'unknown compiler target',
  E1201: 'unsupported target capability',
  E1202: 'invalid target entrypoint',
  E1203: 'source feature not implemented for target',
  E1204: 'invalid portable semantic program',
  E1210: 'target script resource limit exceeded',
  E9001: 'internal compiler invariant failed',
};

const encoder = new TextEncoder();
const decoder = new TextDecoder();

export type Position = { line: number; column: number; byteColumn: number };

/** One source file: text, UTF-8 bytes and line starts (byte offsets). */
export class SourceFile {
  readonly bytes: Uint8Array;
  readonly lineStarts: number[];
  constructor(readonly name: string, readonly text: string) {
    this.bytes = encoder.encode(text);
    this.lineStarts = [0];
    for (let i = 0; i < this.bytes.length; i++) if (this.bytes[i] === 0x0a) this.lineStarts.push(i + 1);
  }
  /** 0-based line index containing byte offset. */
  lineIndex(offset: number): number {
    let lo = 0, hi = this.lineStarts.length - 1;
    while (lo < hi) { const mid = (lo + hi + 1) >> 1; if (this.lineStarts[mid]! <= offset) lo = mid; else hi = mid - 1; }
    return lo;
  }
  /** Line text without its terminator (`\n` or `\r\n`). */
  lineText(index: number): string {
    const start = this.lineStarts[index]!, next = this.lineStarts[index + 1];
    let end = next === undefined ? this.bytes.length : next - 1;
    if (end > start && this.bytes[end - 1] === 0x0d) end--;
    return decoder.decode(this.bytes.subarray(start, end));
  }
  get lineCount(): number { return this.lineStarts.length; }
  /** 1-based line and Unicode-scalar column of a byte offset (clamped into the file). */
  position(offset: number): Position {
    const at = Math.max(0, Math.min(offset, this.bytes.length));
    const index = this.lineIndex(at), start = this.lineStarts[index]!;
    return { line: index + 1, column: scalarCount(this.bytes, start, at) + 1, byteColumn: at - start + 1 };
  }
}

function scalarCount(bytes: Uint8Array, from: number, to: number): number {
  let n = 0;
  for (let i = from; i < to; i++) if ((bytes[i]! & 0xc0) !== 0x80) n++;
  return n;
}

/** Display cells of one code point in an excerpt (tab handled by the caller). */
function cellWidth(cp: number): number {
  if (cp < 0x20 || (cp >= 0x7f && cp < 0xa0)) return cp === 0 ? 0 : 1;
  if (/\p{M}/u.test(String.fromCodePoint(cp)) || cp === 0x200b || cp === 0x200d) return 0;
  if ((cp >= 0x1100 && cp <= 0x115f) || (cp >= 0x2e80 && cp <= 0xa4cf) || (cp >= 0xac00 && cp <= 0xd7a3) || (cp >= 0xf900 && cp <= 0xfaff) ||
    (cp >= 0xfe30 && cp <= 0xfe4f) || (cp >= 0xff00 && cp <= 0xff60) || (cp >= 0xffe0 && cp <= 0xffe6) || (cp >= 0x1f300 && cp <= 0x1faff) ||
    (cp >= 0x20000 && cp <= 0x3fffd)) return 2;
  return 1;
}
const TAB = 4;
/** Expand a line for display and return display-cell offsets for each UTF-8 byte offset in it. */
function layout(line: string): { text: string; cellAt: (byte: number) => number; width: number } {
  let text = '', cells = 0;
  const marks: [number, number][] = []; let byte = 0;
  for (const ch of line) {
    const cp = ch.codePointAt(0)!;
    marks.push([byte, cells]);
    if (cp === 9) { const n = TAB - (cells % TAB); text += ' '.repeat(n); cells += n; }
    else { text += ch; cells += cellWidth(cp); }
    byte += encoder.encode(ch).length;
  }
  marks.push([byte, cells]);
  const cellAt = (b: number): number => { let c = 0; for (const [mb, mc] of marks) { if (mb > b) break; c = mc; } return c; };
  return { text, cellAt, width: cells };
}

/** Source registry keyed by the file names used in diagnostics. */
export class SourceManager {
  private readonly files = new Map<string, SourceFile>();
  add(name: string, text: string): SourceFile { const file = new SourceFile(name, text); this.files.set(name, file); return file; }
  get(name: string | undefined): SourceFile | undefined { return name === undefined ? undefined : this.files.get(name); }
  merge(other: SourceManager | undefined): this { if (other) for (const [name, file] of other.files) if (!this.files.has(name)) this.files.set(name, file); return this; }
}

// ---------------------------------------------------------------------------
// Construction helpers

export type DiagnosticExtra = { labels?: Label[]; notes?: string[]; help?: string; related?: Related[]; severity?: Severity };
export function diagnostic(code: string, message: string, primary: Location | undefined, extra: DiagnosticExtra = {}): Diagnostic {
  return { severity: extra.severity ?? 'error', code, message, ...(primary ? { primary } : {}), labels: extra.labels ?? [], notes: extra.notes ?? [],
    ...(extra.help !== undefined ? { help: extra.help } : {}), related: extra.related ?? [] };
}
/** Location of a span, taking the file from the span's own identity when present. */
export function at(span: Span | undefined, fallbackFile = '<source>'): Location {
  return span ? { file: span.file ?? fallbackFile, span } : { file: fallbackFile };
}
function key(d: Diagnostic): string {
  return `${d.code}|${d.primary?.file ?? ''}|${d.primary?.span?.start ?? ''}|${d.primary?.span?.end ?? ''}|${d.message}`;
}
/** Order-preserving de-duplication (same code, primary location and message) and capping. */
export function dedupe(list: Diagnostic[], cap = MAX_DIAGNOSTICS): Diagnostic[] {
  const seen = new Set<string>(); const out: Diagnostic[] = [];
  for (const d of list) { const k = key(d); if (seen.has(k)) continue; seen.add(k); out.push(d); }
  return out.length > cap ? out.slice(0, cap) : out;
}

/**
 * Error thrown by the compiler APIs. `diagnostics` holds every collected diagnostic
 * (first = the one that stopped compilation); `message` is a one-line
 * `file:line:col: error[CODE]: message` header for the first.
 */
export class CompileError extends Error {
  readonly diagnostics: Diagnostic[];
  sources: SourceManager;
  constructor(diagnostics: Diagnostic[], sources?: SourceManager) {
    const list = dedupe(diagnostics);
    super(headline(list[0]!, sources) + (list.length > 1 ? ` (and ${list.length - 1} more error${list.length > 2 ? 's' : ''})` : ''));
    this.name = 'CompileError';
    this.diagnostics = list;
    this.sources = sources ?? new SourceManager();
    Object.defineProperty(this, 'sources', { enumerable: false });
  }
  get code(): string { return this.diagnostics[0]!.code; }
  /** Full rendered text of all diagnostics. */
  render(options: RenderOptions = {}): string { return renderDiagnostics(this.diagnostics, this.sources, options); }
  toJSON(): DiagnosticJson[] { return this.diagnostics.map(d => diagnosticToJson(d, this.sources)); }
}
/** Merge diagnostics from CompileErrors (others rethrown as-is by callers). */
export function mergeErrors(errors: CompileError[], sources?: SourceManager): CompileError {
  const merged = new SourceManager(); if (sources) merged.merge(sources);
  for (const e of errors) merged.merge(e.sources);
  return new CompileError(errors.flatMap(e => e.diagnostics), merged);
}

/**
 * Collects diagnostics for one compile. Recovery may continue until
 * `MAX_DIAGNOSTICS`; the next report then throws, and the first diagnostic is kept.
 * `raise` records one more diagnostic (unless the cap is already full) and stops.
 */
export class DiagnosticBag {
  readonly diagnostics: Diagnostic[] = [];
  constructor(readonly sources: SourceManager, readonly fallbackFile = '<source>') {}
  report(code: string, message: string, span?: Span, extra: DiagnosticExtra = {}): void {
    if (this.diagnostics.length >= MAX_DIAGNOSTICS) this.finish();
    this.diagnostics.push(diagnostic(code, message, span ? at(span, this.fallbackFile) : undefined, extra));
    if (this.diagnostics.length >= MAX_DIAGNOSTICS) this.finish();
  }
  raise(code: string, message: string, span?: Span, extra: DiagnosticExtra = {}): never {
    this.report(code, message, span, extra);
    this.finish();
  }
  finish(): never { throw new CompileError(this.diagnostics, this.sources); }
  /** Throw if any diagnostic was recorded and compilation continued. */
  checkpoint(): void { if (this.diagnostics.length) this.finish(); }
}

function where(loc: Location | undefined, sources?: SourceManager): string {
  if (!loc) return '';
  if (!loc.span) return `${loc.file}: `;
  const file = sources?.get(loc.file);
  if (!file) return `${loc.file}:${loc.span.start}..${loc.span.end}: `;
  const p = file.position(loc.span.start);
  return `${loc.file}:${p.line}:${p.column}: `;
}
export function headline(d: Diagnostic, sources?: SourceManager): string {
  return `${where(d.primary, sources)}${d.severity}[${d.code}]: ${d.message}`;
}

// ---------------------------------------------------------------------------
// Text rendering

export type RenderOptions = { color?: boolean };
type Paint = (style: 'error' | 'warning' | 'note' | 'help' | 'gutter' | 'bold' | 'secondary', text: string) => string;
const ANSI: Record<string, string> = { error: '1;31', warning: '1;33', note: '1;36', help: '1;32', gutter: '1;34', bold: '1', secondary: '1;34' };

/** Whether to colour output for a stream: TTY and NO_COLOR unset (FORCE_COLOR forces). */
export function shouldColor(stream: { isTTY?: boolean }, env: Record<string, string | undefined> = process.env): boolean {
  if (env.NO_COLOR !== undefined && env.NO_COLOR !== '') return false;
  if (env.FORCE_COLOR !== undefined && env.FORCE_COLOR !== '0') return true;
  return !!stream.isTTY;
}

type Mark = { file: string; span: Span; message: string; primary: boolean };

export function renderDiagnostics(list: Diagnostic[], sources: SourceManager = new SourceManager(), options: RenderOptions = {}): string {
  const out = list.map(d => renderDiagnostic(d, sources, options));
  const errors = list.filter(d => d.severity === 'error').length;
  if (errors > 1) out.push(paintWith(options)('bold', `${errors} errors generated.`) + '\n');
  return out.join('');
}

function paintWith(options: RenderOptions): Paint {
  return (style, text) => options.color ? `\x1b[${ANSI[style]}m${text}\x1b[0m` : text;
}

export function renderDiagnostic(d: Diagnostic, sources: SourceManager = new SourceManager(), options: RenderOptions = {}): string {
  const paint = paintWith(options);
  const lines: string[] = [];
  lines.push(`${paint('bold', where(d.primary, sources))}${paint(d.severity, `${d.severity}[${d.code}]`)}${paint('bold', `: ${d.message}`)}`);
  const marks: Mark[] = [];
  if (d.primary?.span) {
    const own = d.labels.find(l => l.primary);
    marks.push({ file: d.primary.file, span: d.primary.span, message: own?.message ?? '', primary: true });
  }
  for (const l of d.labels) if (!l.primary) marks.push({ file: l.file ?? l.span.file ?? d.primary?.file ?? '<source>', span: l.span, message: l.message, primary: false });
  const files = [...new Set(marks.map(m => m.file))];
  const gutter = Math.max(1, ...marks.map(m => { const f = sources.get(m.file); return f ? String(f.position(m.span.end).line).length : 1; }));
  for (const name of files) {
    const file = sources.get(name);
    const group = marks.filter(m => m.file === name);
    if (!file) { for (const m of group) if (m.message || !m.primary) lines.push(`${' '.repeat(gutter)} ${paint('gutter', '=')} ${m.primary ? 'at' : 'see'} ${name}:${m.span.start}..${m.span.end}${m.message ? `: ${m.message}` : ''}`); continue; }
    if (name !== d.primary?.file) { const p = file.position(group[0]!.span.start); lines.push(`${' '.repeat(gutter)}${paint('gutter', '::: ')}${name}:${p.line}:${p.column}`); }
    lines.push(...excerpt(file, group, gutter, paint));
  }
  for (const n of d.notes) lines.push(`${' '.repeat(gutter)} ${paint('gutter', '=')} ${paint('bold', 'note')}: ${n}`);
  if (d.help !== undefined) lines.push(`${' '.repeat(gutter)} ${paint('gutter', '=')} ${paint('help', 'help')}: ${d.help}`);
  let text = lines.join('\n') + '\n';
  for (const r of d.related) text += renderDiagnostic({ severity: 'note', code: '', message: r.message, primary: { file: r.file, ...(r.span ? { span: r.span } : {}) }, labels: [], notes: [], related: [] }, sources, options).replace('note[]', 'note');
  return text;
}

const MAX_SPAN_LINES = 6;
function excerpt(file: SourceFile, marks: Mark[], gutter: number, paint: Paint): string[] {
  // Lines each mark touches (long multi-line spans elide their middle).
  type Row = { line: number; mark: Mark; from: number; to: number; last: boolean };
  const rows: Row[] = []; const shown = new Set<number>();
  for (const m of marks) {
    const first = file.lineIndex(m.span.start);
    const lastLine = m.span.end > m.span.start ? file.lineIndex(m.span.end - 1) : first;
    const touched: number[] = [];
    for (let l = first; l <= lastLine; l++) if (lastLine - first < MAX_SPAN_LINES || l < first + 2 || l > lastLine - 2) touched.push(l);
    for (const l of touched) {
      const start = file.lineStarts[l]!, text = file.lineText(l), lineEnd = start + encoder.encode(text).length;
      let from = l === first ? m.span.start - start : encoder.encode(text).length - encoder.encode(text.trimStart()).length;
      let to = l === lastLine ? Math.min(m.span.end, lineEnd) - start : lineEnd - start;
      if (to < from) to = from;
      rows.push({ line: l, mark: m, from, to, last: l === lastLine });
      shown.add(l);
    }
  }
  const out: string[] = [];
  const bar = paint('gutter', '|');
  out.push(`${' '.repeat(gutter)} ${bar}`);
  let previous = -1;
  for (const l of [...shown].sort((a, b) => a - b)) {
    if (previous >= 0 && l > previous + 1) out.push(paint('gutter', '...'));
    previous = l;
    const view = layout(file.lineText(l));
    out.push(`${paint('gutter', String(l + 1).padStart(gutter))} ${bar} ${view.text}`.trimEnd());
    const here = rows.filter(r => r.line === l).sort((a, b) => Number(b.mark.primary) - Number(a.mark.primary) || a.from - b.from);
    for (const r of here) {
      const startCell = view.cellAt(r.from), endCell = Math.max(view.cellAt(r.to), startCell + 1);
      const len = endCell - startCell;
      const firstRow = r.line === file.lineIndex(r.mark.span.start);
      const underline = r.mark.primary ? (firstRow ? '^' : '~') + '~'.repeat(len - 1) : '-'.repeat(len);
      const message = r.last && r.mark.message ? ` ${r.mark.message}` : '';
      out.push(`${' '.repeat(gutter)} ${bar} ${' '.repeat(startCell)}${paint(r.mark.primary ? 'error' : 'secondary', underline + message)}`);
    }
  }
  return out;
}

// ---------------------------------------------------------------------------
// JSON form (schema lotus-v2/diagnostics/1)

export const DIAGNOSTICS_SCHEMA = 'lotus-v2/diagnostics/1';
export type JsonLocation = { file: string; start?: number; end?: number; line?: number; column?: number; endLine?: number; endColumn?: number; module?: string };
export type DiagnosticJson = { severity: Severity; code: string; message: string; primary: JsonLocation | null;
  labels: (JsonLocation & { message: string; primary: boolean })[]; notes: string[]; help: string | null; related: (JsonLocation & { message: string })[] };

function jsonLocation(file: string, span: Span | undefined, sources?: SourceManager): JsonLocation {
  if (!span) return { file };
  const src = sources?.get(file);
  const base: JsonLocation = { file, start: span.start, end: span.end };
  if (src) { const a = src.position(span.start), b = src.position(span.end); Object.assign(base, { line: a.line, column: a.column, endLine: b.line, endColumn: b.column }); }
  if (span.module !== undefined) base.module = span.module;
  return base;
}
/** Stable JSON (fixed key order). `column`/`endColumn` are 1-based Unicode-scalar columns; `end` is exclusive. */
export function diagnosticToJson(d: Diagnostic, sources?: SourceManager): DiagnosticJson {
  return {
    severity: d.severity, code: d.code, message: d.message,
    primary: d.primary ? jsonLocation(d.primary.file, d.primary.span, sources) : null,
    labels: d.labels.map(l => ({ ...jsonLocation(l.file ?? l.span.file ?? d.primary?.file ?? '<source>', l.span, sources), message: l.message, primary: !!l.primary })),
    notes: [...d.notes], help: d.help ?? null,
    related: d.related.map(r => ({ ...jsonLocation(r.file, r.span, sources), message: r.message })),
  };
}
export function diagnosticsJson(list: Diagnostic[], sources?: SourceManager): string {
  return JSON.stringify({ schema: DIAGNOSTICS_SCHEMA, diagnostics: list.map(d => diagnosticToJson(d, sources)) }, null, 2) + '\n';
}

/** Levenshtein-based suggestion: closest candidate within distance max(1, len/3). Ties break lexicographically. */
export function suggest(name: string, candidates: Iterable<string>): string | undefined {
  const limit = Math.max(1, Math.floor(name.length / 3));
  let best: string | undefined, bestDistance = Infinity;
  for (const c of [...new Set(candidates)].sort()) {
    if (c === name || Math.abs(c.length - name.length) > limit) continue;
    // A case-only difference ranks ahead of any real edit.
    const score = name.toLowerCase() === c.toLowerCase() ? 0.5 : distance(name, c);
    if (score <= limit && score < bestDistance) { best = c; bestDistance = score; }
  }
  return best;
}
function distance(a: string, b: string): number {
  const row = Array.from({ length: b.length + 1 }, (_, i) => i);
  for (let i = 1; i <= a.length; i++) {
    let prev = row[0]!; row[0] = i;
    for (let j = 1; j <= b.length; j++) {
      const tmp = row[j]!;
      row[j] = Math.min(row[j]! + 1, row[j - 1]! + 1, prev + (a[i - 1] === b[j - 1] ? 0 : 1));
      prev = tmp;
    }
  }
  return row[b.length]!;
}

/** Render any thrown value (CompileError or plain Error) as diagnostics text or JSON. */
export function errorDiagnostics(error: unknown, fallbackFile?: string): { diagnostics: Diagnostic[]; sources: SourceManager } {
  if (error instanceof CompileError) return { diagnostics: error.diagnostics, sources: error.sources };
  const message = error instanceof Error ? error.message : String(error);
  return { diagnostics: [diagnostic('E0000', message, fallbackFile !== undefined ? { file: fallbackFile } : undefined)], sources: new SourceManager() };
}
