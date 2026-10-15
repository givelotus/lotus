/** Bounded, typed P03 contract frontend. No VM or consensus-validation code. */
import { artifactSpan, bytes, concat, cs, hex, tagged, unhex, uint, type Span } from './compiler.js';
import { schnorr } from '@noble/curves/secp256k1';
import { DiagnosticBag, SourceManager, suggest, type DiagnosticExtra } from './diagnostics.js';
import { assertPortableName } from './names.js';
import { optimizeInstructions, type Instruction } from './optimizer.js';
import { PromiseScheduler, type SchedulerEvent } from './scheduler.js';
export type { SchedulerEvent } from './scheduler.js';

export type ValueType = 'PublicKey' | 'Signature' | 'Bytes32' | `Bytes(${number})` | 'Int' | 'Amount' | 'TokenId' | 'Bool' | 'MethodLeafHash' | 'ContractRootHash' | 'InputIndex' | 'OutputIndex';
export type BoundValue = string | boolean | bigint;
type Token = { text: string; span: Span };
export type Param = { name: string; type: ValueType; span: Span };
export type Expr = { kind: 'name' | 'number' | 'bool' | 'call' | 'binary' | 'unary'; span: Span; value?: string; args?: Expr[]; left?: Expr; right?: Expr };
export type Stmt = { kind: 'require' | 'if' | 'for' | 'assign'; span: Span; expr?: Expr; then?: Stmt[]; otherwise?: Stmt[]; variable?: string; collection?: 'tx.inputs' | 'tx.outputs'; assignOp?: '=' | '+=' | '-=' };
/** Statement-bodied helper. `return` is only legal as the function body's last statement. */
export type HelperStmt = { kind: 'let'; name: string; type: ValueType; expr: Expr; nameSpan: Span; span: Span }
  | { kind: 'require'; expr: Expr; span: Span }
  | { kind: 'if'; expr: Expr; then: HelperStmt[]; otherwise: HelperStmt[]; span: Span }
  | { kind: 'return'; expr: Expr; span: Span };
/** `private` (default, module only), `package` (same package) or `export` (other packages via exported modules). */
export type Visibility = 'private' | 'package' | 'export';
export type Helper = { name: string; params: Param[]; result: ValueType; body: HelperStmt[]; span: Span; visibility: Visibility };
export type Method = { name: string; params: Param[]; body: Stmt[]; span: Span };
export type Contract = { name: string; kind: 'contract' | 'token'; params: Param[]; methods: Method[]; span: Span; visibility: Visibility };
/** Compile-time link to a library contract. Not a VM call. Present only on package artifacts that commit to one. */
export type LinkedContract = { name: string; kind: 'contract' | 'token'; package: string; module: string; packageDigest: string; root: string;
  methods: { name: string; leaf: string }[] };
/** `import TARGET::path::{a, b as c};` or `import TARGET::path as alias;`. TARGET is a dependency alias, `package`, or a quoted module selector (`"host/owner/repo@vX.Y.Z"`). */
export type ImportDecl = { target: string; targetSpan: Span; path: string[]; pathSpan: Span; span: Span;
  items?: { name: string; local: string; span: Span }[]; moduleAlias?: { name: string; span: Span } };
export type Program = { helpers: Map<string, Helper>; contracts: Map<string, Contract>; imports: ImportDecl[] };
type Binding = { type: ValueType; value: string | boolean };
export type MethodArtifact = { name: string; args: { name: string; type: ValueType }[]; invocation?: 'spend' | 'mint'; mintAmountParam?: string; scriptHex: string; leaf: string; proof: string[]; root: string;
  sourceMap: { source: Span; expandedFrom?: Span; optimizedFrom?: { op: string; source: Span; expandedFrom?: Span }[]; byteStart: number; byteEnd: number; op: string }[];
  staticResources: { scriptBytes: number; opcodes: number; maxStackItems: number; helperExpansions: number; dynamicSignatureChecks: number } };
export type ContractArtifact = { schema: 'lotus-v2/contract-artifact/2'; target: 'P01-P02-P03-candidate-2026-10-14'; contract: string; kind?: 'contract' | 'token';
  constructor: { name: string; type: ValueType }[]; bindings: { name: string; type: ValueType; value: string | boolean }[];
  methods: MethodArtifact[]; policy: { branches: [string]; paths: [[0]]; root: string; treeRecipe: 'sorted-leaves-largest-power-split-v1' };
  /** Present only for package builds (CABI-07); see packages.ts. */
  build?: import('./packages.js').BuildGraph;
  /** Library contracts this artifact commits to (CABI-08). Omitted when empty so single-file artifacts stay unchanged. */
  links?: LinkedContract[]; }
export type CompileOptions = { contract: string; bindings: Record<string, Record<string, BoundValue>>; optimize?: boolean };

const MAX_SOURCE = 65536, MAX_SCRIPT = 8192, MAX_OPS = 4096, MAX_EXPANSIONS = 256, MAX_METHODS = 16;
const MAX_INFERENCE_VISITS = 8192;
const MAX_DEPENDENCY_VISITS = 8192;
const INT_MIN = -(1n << 127n), INT_MAX = 1n << 127n;
const INT_RANGE = 'Int exceeds signed 128-bit range';
/** Notes for an inlined helper chain. The expansion stack itself is capped at 16. */
const MAX_INLINE_NOTES = 16;
type Frame = { name: string; at: Span };
type Checked = ValueType | 'Error';
function bindName(name: string, span: Span, bag: DiagnosticBag): void {
  try { assertPortableName(name); }
  catch (error) { bag.raise('E0115', (error as Error).message, span); }
}
function utf8Offset(source: string, utf16: number): number { return new TextEncoder().encode(source.slice(0, utf16)).length; }
function spanAt(file: string, start: number, end: number): Span { return { start, end, file }; }
function cover(start: Span, end: Span): Span {
  return { start: start.start, end: end.end, ...(start.file !== undefined ? { file: start.file } : {}), ...(start.module !== undefined ? { module: start.module } : {}) };
}
/** Top-level `&&` only. Nested `||` stays intact so it is not rewritten as `require`. */
function conjuncts(expr: Expr): Expr[] {
  if (expr.kind === 'binary' && expr.value === '&&' && expr.left && expr.right) return [...conjuncts(expr.left), ...conjuncts(expr.right)];
  return [expr];
}
function helperReturn(body: HelperStmt[]): Extract<HelperStmt, { kind: 'return' }> | undefined {
  const stmt = body.find(item => item.kind === 'return');
  return stmt?.kind === 'return' ? stmt : undefined;
}
function lex(source: string, file: string, bag: DiagnosticBag): Token[] {
  const encoded = new TextEncoder().encode(source);
  if (encoded.length > MAX_SOURCE) bag.raise('E0002', 'source exceeds 65536 UTF-8 bytes', spanAt(file, 0, encoded.length));
  const re = /\s+|\/\/[^\n]*|\/\*[\s\S]*?\*\/|==|!=|>=|<=|\+=|-=|&&|\|\||::|"[^"\\\n]*"|[A-Za-z_][A-Za-z_0-9]*|[0-9]+|[<>{}():;,.!+*\-=]/gy;
  const out: Token[] = []; let pos = 0;
  while (pos < source.length) {
    re.lastIndex = pos; const m = re.exec(source);
    if (!m) {
      const cp = source.codePointAt(pos) ?? 0, width = cp > 0xffff ? 2 : 1;
      const start = utf8Offset(source, pos);
      if (source.startsWith('/*', pos)) bag.raise('E0003', 'unterminated block comment', spanAt(file, start, encoded.length));
      if (source.startsWith('"', pos) || source.startsWith("'", pos)) bag.raise('E0004', 'unterminated string literal', spanAt(file, start, encoded.length));
      bag.raise('E0001', 'unsupported character', spanAt(file, start, utf8Offset(source, pos + width)));
    }
    if (!/^\s|^\//.test(m[0])) out.push({ text: m[0], span: spanAt(file, utf8Offset(source, pos), utf8Offset(source, re.lastIndex)) });
    pos = re.lastIndex;
  }
  out.push({ text: '<eof>', span: spanAt(file, utf8Offset(source, pos), utf8Offset(source, pos)) });
  return out;
}
class Parser {
  private i = 0;
  constructor(private readonly tokens: Token[], private readonly bag: DiagnosticBag) {}
  private peek(): Token { return this.tokens[this.i]!; }
  private fatal(code: string, message: string, span?: Span): never { this.bag.raise(code, message, span); }
  private take(expected?: string): Token {
    const t = this.peek();
    if (expected && t.text !== expected) this.fatal('E0101', `expected ${expected}`, t.span);
    this.i++; return t;
  }
  private ident(): Token { const t = this.take(); if (!/^[A-Za-z_][A-Za-z_0-9]*$/.test(t.text)) this.fatal('E0102', 'expected identifier', t.span); return t; }
  private type(): ValueType {
    const t = this.ident();
    if (t.text === 'Bytes') {
      this.take('('); const n = this.take(); this.take(')');
      if (!/^[0-9]+$/.test(n.text) || Number(n.text) < 1 || Number(n.text) > 8192) this.fatal('E0104', 'Bytes bound 1..8192', n.span);
      return `Bytes(${Number(n.text)})`;
    }
    if (['PublicKey','Signature','Bytes32','Int','Amount','TokenId','Bool','MethodLeafHash','ContractRootHash'].includes(t.text)) return t.text as ValueType;
    this.fatal('E0103', `unsupported type ${t.text}`, t.span);
  }
  private params(close: string): Param[] {
    const out: Param[] = [];
    if (this.peek().text !== close) while (true) {
      const name = this.ident(); this.take(':'); const type = this.type();
      bindName(name.text, name.span, this.bag);
      if (out.some(x => x.name === name.text)) this.fatal('E0201', `duplicate parameter ${name.text}`, name.span);
      out.push({ name: name.text, type, span: name.span });
      if (this.peek().text !== ',') break; this.take(',');
    }
    this.take(close); return out;
  }
  private expression(min = 0, depth = 0): Expr {
    if (depth > 64) this.fatal('E0105', 'expression depth exceeded', this.peek().span);
    let left: Expr;
    const start = this.peek();
    if (start.text === '!' || start.text === '-') { this.take(); const inner = this.expression(7,depth + 1); left = { kind: 'unary', value: start.text, right: inner, span: cover(start.span, inner.span) }; }
    else if (start.text === '(') { this.take(); left = this.expression(0,depth + 1); this.take(')'); }
    else if (/^[0-9]+$/.test(start.text)) { this.take(); left = { kind: 'number', value: start.text, span: start.span }; }
    else if (start.text === 'true' || start.text === 'false') { this.take(); left = { kind: 'bool', value: start.text, span: start.span }; }
    else {
      const name = this.ident(); let value = name.text;
      if (this.peek().text === '::') {
        // `alias::helper(...)` or a contract reference `alias::Contract` / `alias::Contract.method`.
        this.take('::'); value += '::' + this.ident().text;
      }
      while (this.peek().text === '.') { this.take('.'); value += '.' + this.ident().text; }
      if (this.peek().text === '(') {
        this.take('('); const args: Expr[] = [];
        if (this.peek().text !== ')') while (true) { args.push(this.expression(0,depth + 1)); if (this.peek().text !== ',') break; this.take(','); }
        const end = this.take(')'); left = { kind: 'call', value, args, span: cover(name.span, end.span) };
      } else left = { kind: 'name', value, span: cover(name.span, this.tokens[this.i - 1]!.span) };
    }
    const precedence: Record<string, number> = { '||': 1, '&&': 2, '==': 3, '!=': 3, '<': 4, '>': 4, '<=':4, '>=':4, '+': 5, '-': 5, '*': 6 };
    while ((precedence[this.peek().text] ?? 0) >= min && precedence[this.peek().text]) {
      const op = this.take(); const right = this.expression(precedence[op.text]! + 1,depth + 1);
      left = { kind: 'binary', value: op.text, left, right, span: cover(left.span, right.span) };
    }
    return left;
  }
  private statements(depth = 0, loops = 0): Stmt[] {
    if (depth > 16) this.fatal('E0106', 'control nesting depth exceeded', this.peek().span);
    this.take('{'); const out: Stmt[] = [];
    while (this.peek().text !== '}') {
      const start = this.take();
      if (start.text === 'require') { this.take('('); const expr = this.expression(); this.take(')'); const end = this.take(';'); out.push({ kind: 'require', expr, span: cover(start.span, end.span) }); }
      else if (start.text === 'if') { const expr = this.expression(); const then = this.statements(depth + 1,loops); const otherwise = this.peek().text === 'else' ? (this.take('else'), this.statements(depth + 1,loops)) : []; out.push({ kind: 'if', expr, then, otherwise, span: cover(start.span, this.tokens[this.i - 1]!.span) }); }
      else if (start.text === 'for') {
        if (loops >= 2) this.fatal('E0108', 'loop nesting exceeds two', start.span);
        const variable = this.ident(); this.take('in'); const collection = this.ident().text + '.' + (this.take('.'), this.ident().text);
        if (collection !== 'tx.inputs' && collection !== 'tx.outputs') this.fatal('E0109', `unsupported collection ${collection}`, start.span);
        const then = this.statements(depth + 1,loops + 1);
        out.push({ kind: 'for', variable: variable.text, collection, then, span: cover(start.span, this.tokens[this.i - 1]!.span) });
      }
      else if (/^[A-Za-z_][A-Za-z_0-9]*$/.test(start.text)) {
        const op = this.take(); if (!['=','+=','-='].includes(op.text)) this.fatal('E0110', `unsupported assignment ${op.text}`, op.span);
        const expr = this.expression(); const end = this.take(';');
        out.push({ kind:'assign', variable:start.text, assignOp:op.text as '='|'+='|'-=', expr, span: cover(start.span, end.span) });
      }
      else this.fatal('E0111', `unsupported statement ${start.text}`, start.span);
      if (out.length > 256) this.fatal('E0107', 'statement budget exceeded', start.span);
    }
    this.take('}'); return out;
  }
  /**
   * Helper statements. `for` is rejected: inlining it into a method loop would
   * nest past the consensus cap of two without a second loop implementation.
   * `return` is only the last statement of the function body, not of an `if`.
   */
  private helperBody(depth = 0, nested = false): HelperStmt[] {
    if (depth > 16) this.fatal('E0106', 'control nesting depth exceeded', this.peek().span);
    this.take('{'); const out: HelperStmt[] = [];
    while (this.peek().text !== '}') {
      if (out.at(-1)?.kind === 'return') this.fatal('E0123', 'statement after return', this.peek().span);
      const start = this.peek();
      if (start.text === 'let') {
        this.take(); const name = this.ident(); bindName(name.text, name.span, this.bag); this.take(':'); const type = this.type(); this.take('=');
        const expr = this.expression(); const end = this.take(';');
        out.push({ kind: 'let', name: name.text, type, expr, nameSpan: name.span, span: cover(start.span, end.span) });
      } else if (start.text === 'require') {
        this.take(); this.take('('); const expr = this.expression(); this.take(')'); const end = this.take(';');
        out.push({ kind: 'require', expr, span: cover(start.span, end.span) });
      } else if (start.text === 'if') {
        this.take(); const expr = this.expression(); const then = this.helperBody(depth + 1, true);
        const otherwise = this.peek().text === 'else' ? (this.take('else'), this.helperBody(depth + 1, true)) : [];
        out.push({ kind: 'if', expr, then, otherwise, span: cover(start.span, this.tokens[this.i - 1]!.span) });
      } else if (start.text === 'for') this.fatal('E0122', 'for is not allowed inside a helper', start.span);
      else if (start.text === 'return') {
        if (nested) this.fatal('E0123', 'return must be the final statement of the helper', start.span);
        this.take(); const expr = this.expression(); const end = this.take(';');
        out.push({ kind: 'return', expr, span: cover(start.span, end.span) });
      } else this.fatal('E0111', `unsupported statement ${this.take().text}`, start.span);
      if (out.length > 256) this.fatal('E0107', 'statement budget exceeded', start.span);
    }
    const end = this.take('}');
    if (!nested && out.at(-1)?.kind !== 'return') this.fatal('E0123', 'helper must end with return', end.span);
    return out;
  }
  private importDecl(start: Token): ImportDecl {
    const target = this.take();
    let targetText = target.text;
    if (targetText.startsWith('"')) {
      if (targetText.length < 2 || !targetText.endsWith('"')) this.fatal('E0004', 'unterminated string literal', target.span);
      targetText = targetText.slice(1, -1);
      if (!targetText) this.fatal('E0112', 'empty import path', target.span);
    } else if (targetText !== 'package' && !/^[A-Za-z_][A-Za-z_0-9]*$/.test(targetText)) this.fatal('E0112', 'expected dependency alias, package, or quoted module path', target.span);
    if (targetText !== 'package' && !targetText.includes('/')) bindName(targetText, target.span, this.bag);
    const path: string[] = []; let items: ImportDecl['items']; let pathEnd = target.span;
    while (this.peek().text === '::') {
      this.take('::');
      if (this.peek().text === '{') {
        this.take('{'); items = [];
        while (this.peek().text !== '}') {
          const name = this.ident(); bindName(name.text, name.span, this.bag); let local = name;
          if (this.peek().text === 'as') { this.take('as'); local = this.ident(); bindName(local.text, local.span, this.bag); }
          items.push({ name: name.text, local: local.text, span: cover(name.span, local.span) });
          if (this.peek().text !== ',') break; this.take(',');
        }
        this.take('}');
        if (!items.length) this.fatal('E0112', 'empty import list', start.span);
        break;
      }
      const segment = this.ident(); path.push(segment.text); pathEnd = segment.span;
    }
    if (!path.length) this.fatal('E0112', 'import requires a module path', start.span);
    let moduleAlias: ImportDecl['moduleAlias'];
    if (!items) {
      if (this.peek().text !== 'as') this.fatal('E0112', "import requires ::{names} or 'as alias'", this.peek().span);
      this.take('as'); const alias = this.ident(); bindName(alias.text, alias.span, this.bag); moduleAlias = { name: alias.text, span: alias.span };
    }
    const end = this.take(';');
    return { target: targetText, targetSpan: target.span, path, pathSpan: cover(target.span, pathEnd),
      span: cover(start.span, end.span), ...(items ? { items } : {}), ...(moduleAlias ? { moduleAlias } : {}) };
  }
  parse(requireContract = true): Program {
    const helpers = new Map<string, Helper>(); const contracts = new Map<string, Contract>(); const imports: ImportDecl[] = [];
    while (this.peek().text !== '<eof>') {
      let start = this.take();
      if (start.text === 'import') {
        if (helpers.size || contracts.size) this.fatal('E0113', 'import must precede declarations', start.span);
        imports.push(this.importDecl(start)); continue;
      }
      let visibility: Visibility = 'private';
      if (start.text === 'export' || start.text === 'package') {
        visibility = start.text;
        if (!['function', 'contract', 'token'].includes(this.peek().text)) this.fatal('E0114', `${start.text} applies only to a function, contract or token`, start.span);
        const modifier = start; start = this.take(); start = { text: start.text, span: cover(modifier.span, start.span) };
      }
      if (start.text === 'function') {
        const name = this.ident(); this.take('('); const params = this.params(')'); this.take(':'); const result = this.type(); const body = this.helperBody();
        bindName(name.text, name.span, this.bag);
        if (helpers.has(name.text)) this.fatal('E0202', `duplicate helper ${name.text}`, name.span);
        helpers.set(name.text, { name: name.text, params, result, body, span: cover(start.span, this.tokens[this.i - 1]!.span), visibility });
      } else if (start.text === 'contract' || start.text === 'token') {
        const name = this.ident(); bindName(name.text, name.span, this.bag); const params = this.peek().text === '<' ? (this.take('<'), this.params('>')) : [];
        this.take('{'); const methods: Method[] = [];
        while (this.peek().text !== '}') {
          this.take('function'); const method = this.ident(); bindName(method.text, method.span, this.bag); this.take('('); const args = this.params(')'); const body = this.statements();
          if (!body.length || methods.some(x => x.name.toLowerCase() === method.text.toLowerCase())) this.fatal('E0203', `empty or duplicate method ${method.text}`, method.span);
          if (start.text === 'token' && (args[0]?.type !== 'Amount')) this.fatal('E0118', `token method ${method.text} first parameter must be Amount`, args[0]?.span ?? method.span);
          methods.push({ name: method.text, params: args, body, span: cover(method.span, this.tokens[this.i - 1]!.span) });
          if (methods.length > MAX_METHODS) this.fatal('E0117', 'more than 16 methods', method.span);
        }
        const end = this.take('}'); if (!methods.length || contracts.has(name.text)) this.fatal('E0204', `empty or duplicate contract ${name.text}`, name.span);
        contracts.set(name.text, { name: name.text, kind:start.text as 'contract'|'token', params, methods, span: cover(start.span, end.span), visibility });
      } else this.fatal('E0101', 'expected contract or helper', start.span);
    }
    if (requireContract && !contracts.size) this.fatal('E0116', 'source has no contract', this.peek().span);
    return { helpers, contracts, imports };
  }
}

function encodedInt(value: bigint): Uint8Array {
  if (value < -(1n << 127n) || value >= (1n << 127n)) throw new Error('Int exceeds signed 128-bit range');
  return uint(value < 0n ? (1n << 128n) + value : value, 16);
}
function literal(value: BoundValue, type: ValueType): { bytes: Uint8Array; binding: Binding } {
  if (type === 'Int' || type === 'Amount') {
    const text = typeof value === 'bigint' ? value.toString() : value;
    if (typeof text !== 'string' || !/^(0|-?[1-9][0-9]*)$/.test(text)) throw new Error('Int binding requires canonical decimal string or bigint');
    const n = BigInt(text); return { bytes: encodedInt(n), binding: { type, value: n.toString() } };
  }
  if (type === 'Bool') { if (typeof value !== 'boolean') throw new Error('Bool binding requires boolean'); return { bytes: encodedInt(value ? 1n : 0n), binding: { type, value } }; }
  if (typeof value !== 'string') throw new Error(`${type} binding requires lowercase hex`);
  const x = unhex(value);
  const exact32 = ['PublicKey','Bytes32','MethodLeafHash','ContractRootHash','TokenId'].includes(type);
  const limit = exact32 ? 32 : type === 'Signature' ? 64 : type.startsWith('Bytes(') ? Number(type.slice(6, -1)) : 0;
  if (!limit || (exact32 ? x.length !== 32 : type === 'Signature' ? x.length !== 64 : x.length > limit)) throw new Error(`${type} binding width`);
  if (type === 'PublicKey') { try { schnorr.utils.lift_x(BigInt(`0x${value}`)); } catch { throw new Error('PublicKey is not a BIP340 x-only curve point'); } }
  return { bytes: x, binding: { type, value } };
}

function compareLE(a: Uint8Array, b: Uint8Array): number { for (let i = 31; i >= 0; i--) if (a[i] !== b[i]) return a[i]! - b[i]!; return 0; }
function nodeHash(a: Uint8Array, b: Uint8Array): Uint8Array { return tagged('branch', concat(Uint8Array.of(1), ...(compareLE(a,b) <= 0 ? [a,b] : [b,a]))); }
function leafHash(script: Uint8Array): Uint8Array { return tagged('branch', concat(Uint8Array.of(0), bytes(script))); }
type Tree = { root: Uint8Array; proofs: Map<string, Uint8Array[]> };
function tree(leaves: { name: string; hash: Uint8Array }[]): Tree {
  if (!leaves.length) throw new Error('empty method tree');
  const sorted = [...leaves].sort((a,b) => compareLE(a.hash,b.hash));
  for (let i = 1; i < sorted.length; i++) if (compareLE(sorted[i - 1]!.hash, sorted[i]!.hash) === 0) throw new Error('duplicate method leaf');
  function build(items: typeof sorted): Tree {
    if (items.length === 1) return { root: items[0]!.hash, proofs: new Map([[items[0]!.name, []]]) };
    let k = 1; while (k * 2 < items.length) k *= 2;
    const a = build(items.slice(0,k)), b = build(items.slice(k));
    const proofs = new Map<string, Uint8Array[]>();
    for (const [name,p] of a.proofs) proofs.set(name,[...p,b.root]);
    for (const [name,p] of b.proofs) proofs.set(name,[...p,a.root]);
    return { root: nodeHash(a.root,b.root), proofs };
  }
  return build(sorted);
}

type EVar = { kind: 'argument'; type: ValueType; index: number } | { kind:'local'; type: ValueType; index:number } |
  { kind: 'constant'; type: ValueType; data: Uint8Array } |
  { kind: 'substitute'; type: ValueType; expr: Expr; env: Env; origin: Span; frames: Frame[] };
type Env = Map<string, EVar>;
type Compiled = { script: Uint8Array; leaf: Uint8Array; map: MethodArtifact['sourceMap']; resources: MethodArtifact['staticResources'] };
const OPCODES = { VERIFY: 0x65, IF: 0x61, ELSE: 0x63, ENDIF: 0x64, ENUMERATE_INPUTS:0x67, ENUMERATE_OUTPUTS:0x68, ENDENUMERATE:0x6a, DROP: 0x79, PICK: 0x7d, ROLL:0x7e,
  UTXOREQUIRESBRANCH:0xdd, UTXOBRANCHCOUNT:0xd8, UTXOBRANCH:0xd9, OUTPUTBRANCHCOUNT:0xe3, OUTPUTBRANCH:0xe4, OUTPUTEXCLUSIVEBRANCH:0xe9, OUTPUTCONTINUESBRANCH:0xea, CHECKLOCKTIMEVERIFY:0xf3, CHECKSEQUENCEVERIFY:0xf4, SWAP:0x80, BRANCHROOT:0xf2, INPUTINDEX:0xd0, INPUTFLAGS:0xd1, UTXOVALUE:0xd6, UTXOTOKENID:0xd7, OUTPUTVALUE:0xe1, OUTPUTTOKENID:0xe2, OUTPUTREQUIRESBRANCH:0xe8, NUMEQUAL:0xa6, GREATERTHANOREQUAL:0xac,
  EQUAL: 0x91, NOT: 0x9c, ADD: 0x9e, SUB: 0x9f, MUL: 0xa0, BOOLAND: 0xa4, BOOLOR: 0xa5,
  LESSTHAN: 0xa9, GREATERTHAN: 0xaa, SHA256: 0xb8, HASH256: 0xb9, BLAKE3: 0xba, CHECKSIG: 0xbb, CHECKSIGVERIFY: 0xbc, NEGATE: 0x9a } as const;
class Emitter {
  private instructions: Instruction[] = [];
  private length = 0;
  readonly map: MethodArtifact['sourceMap'] = [];
  height: number; maxHeight: number; opcodes = 0; signatureChecks = 0; expansions = 0;
  /** Inline chain of the expression currently being lowered. */
  frames: Frame[] = [];
  constructor(readonly args: number, private readonly fail: (code: string, message: string, span: Span, frames: Frame[]) => never) { this.height = args; this.maxHeight = args; }
  private append(data: Uint8Array, op: string, span: Span, origin?: Span, delta = 0, foldable = false): void {
    if (this.length + data.length > MAX_SCRIPT) this.fail('E0701', 'MAX_SCRIPT_BYTES exceeded', span, this.frames);
    if (++this.opcodes > MAX_OPS) this.fail('E0702', 'opcode budget exceeded', span, this.frames);
    // Artifacts and traces keep `{start,end[,module]}` only; `file` is diagnostic-only.
    this.map.push({ source: artifactSpan(span), ...(origin ? { expandedFrom: artifactSpan(origin) } : {}), byteStart: this.length, byteEnd: this.length + data.length, op });
    this.instructions.push({ wire: data, map: this.map.at(-1)!, delta, foldable }); this.length += data.length; this.height += delta;
    if (this.height < 0) this.fail('E9001', 'compiler stack underflow', span, this.frames);
    this.maxHeight = Math.max(this.maxHeight, this.height);
  }
  push(data: Uint8Array, span: Span, origin?: Span, foldable = false): void {
    if (data.length > 8192) this.fail('E0707', 'MAX_ELEMENT_BYTES exceeded', span, this.frames);
    const wire = data.length > 0 && data.length <= 75 ? concat(Uint8Array.of(data.length), data) : concat(Uint8Array.of(0x4c), bytes(data));
    this.append(wire, data.length <= 75 && data.length > 0 ? `PUSH_${data.length}` : 'PUSHDATA', span, origin, 1, foldable);
  }
  number(n: bigint, span: Span, origin?: Span): void {
    if (n === 0n) this.append(Uint8Array.of(0), 'ZERO', span, origin, 1, true);
    else if (n === -1n) this.append(Uint8Array.of(0x4d), 'NEGATIVE_ONE', span, origin, 1, true);
    else if (n >= 1n && n <= 16n) this.append(Uint8Array.of(0x4d + Number(n)), `N(${n})`, span, origin, 1, true);
    else this.push(encodedInt(n), span, origin, true);
  }
  op(name: keyof typeof OPCODES, span: Span, origin?: Span, delta = 0): void { this.append(Uint8Array.of(OPCODES[name]), name, span, origin, delta); if (name === 'CHECKSIG') this.signatureChecks++; }
  control(name: 'IF'|'ELSE'|'ENDIF', span: Span, origin?: Span): void { this.op(name, span, origin, name === 'IF' ? -1 : 0); }
  finish(optimize: boolean): { script: Uint8Array; map: MethodArtifact['sourceMap']; resources: Pick<MethodArtifact['staticResources'], 'scriptBytes'|'opcodes'|'maxStackItems'> } {
    const entries = optimize ? optimizeInstructions(this.instructions, this.args) : this.instructions;
    const structured = entries.some(entry => ['IF','ELSE','ENDIF','ENUMERATE_INPUTS','ENUMERATE_OUTPUTS','ENDENUMERATE'].includes(entry.map.op));
    const map: MethodArtifact['sourceMap'] = [];
    let offset = 0, height = this.args, maxStackItems = height;
    for (const entry of entries) {
      map.push({ ...entry.map, byteStart: offset, byteEnd: offset + entry.wire.length });
      offset += entry.wire.length;
      if (!structured) { height += entry.delta; if (height < 0) this.fail('E9001', 'optimized compiler stack underflow', entry.map.source, this.frames); maxStackItems = Math.max(maxStackItems, height); }
    }
    if (structured) { height = this.height; maxStackItems = this.maxHeight; }
    if (height !== 1) this.fail('E9001', 'optimized method final stack mismatch', map.at(-1)?.source ?? { start: 0, end: 0 }, this.frames);
    return { script: concat(...entries.map(entry => entry.wire)), map,
      resources: { scriptBytes: offset, opcodes: entries.length, maxStackItems } };
  }
  get bytes(): number { return this.length; }
}

class Compiler {
  private scheduledJob?: string;
  private enforceScheduledJobs = false;
  private dependencyVisits = 0;
  private readonly helperDependencies = new Map<string, string[]>();
  private methodMemo = new Map<string, Compiled>();
  private methodActive = new Set<string>();
  private rootMemo = new Map<string, Tree>();
  private rootActive = new Set<string>();
  private bindingMemo = new Map<string, Map<string, { bytes: Uint8Array; binding: Binding }>>();
  constructor(private readonly program: Program, private readonly options: CompileOptions, private readonly diag: DiagnosticBag) {}
  /** Record a diagnostic, including the inline-expansion chain, and keep going until the cap. */
  private problem(code: string, message: string, span: Span | undefined, frames: Frame[] = [], extra: DiagnosticExtra = {}): 'Error' {
    const related = frames.slice(-MAX_INLINE_NOTES).reverse().map(frame => ({
      file: frame.at.file ?? this.diag.fallbackFile, span: frame.at, message: `in expansion of helper ${frame.name} called here`,
    }));
    this.diag.report(code, message, span, { ...extra, related: [...(extra.related ?? []), ...related] });
    return 'Error';
  }
  private fatal(code: string, message: string, span?: Span, frames: Frame[] = [], extra: DiagnosticExtra = {}): never {
    this.problem(code, message, span, frames, extra); this.diag.finish();
  }
  private hint(name: string, scope?: Env): DiagnosticExtra {
    const best = suggest(name, [...(scope ? scope.keys() : []), ...this.program.helpers.keys(), ...this.program.contracts.keys(),
      'checksig', 'sha256', 'hash256', 'blake3', 'leaf_hash', 'contract_root', 'merkle_root', 'num_bytes', 'check_lock', 'check_sequence']);
    return best ? { help: `did you mean '${best}'?` } : {};
  }
  private contract(name: string, span?: Span): Contract { const c = this.program.contracts.get(name); if (!c) this.fatal(span ? 'E0303' : 'E0605', `unknown contract ${name}`, span ?? this.program.contracts.values().next().value?.span); return c; }
  private bound(name: string): Map<string, { bytes: Uint8Array; binding: Binding }> {
    const old = this.bindingMemo.get(name); if (old) return old;
    const c = this.contract(name); const input = this.options.bindings[name] ?? (c.params.length === 0 ? {} : undefined);
    if (!input || Object.keys(input).length !== c.params.length) this.fatal('E0602', `constructor arity mismatch for ${name}`, c.span);
    const out = new Map<string, { bytes: Uint8Array; binding: Binding }>();
    for (const p of c.params) {
      if (!Object.hasOwn(input, p.name)) this.fatal('E0603', `missing constructor binding ${name}.${p.name}`, p.span);
      try { out.set(p.name, literal(input[p.name]!, p.type)); }
      catch (error) { this.fatal('E0604', (error as Error).message, p.span); }
    }
    this.bindingMemo.set(name, out); return out;
  }
  private findMethod(contract: string, method: string, span?: Span): Method {
    const m = this.contract(contract, span).methods.find(x => x.name === method);
    if (!m) this.fatal('E0304', `unknown method ${contract}.${method}`, span);
    return m;
  }
  private dependencies(method: Method): string[] {
    const found = new Set<string>();
    const scanHelper = (body: HelperStmt[], target: Set<string>, helpers: string[]): void => {
      for (const stmt of body) {
        if (stmt.kind === 'if') { scan(stmt.expr, target, helpers); scanHelper(stmt.then, target, helpers); scanHelper(stmt.otherwise, target, helpers); }
        else scan(stmt.expr, target, helpers);
      }
    };
    const scan = (expr: Expr, target: Set<string>, helpers: string[]): void => {
      if (++this.dependencyVisits > MAX_DEPENDENCY_VISITS) this.fatal('E0705', 'dependency scan visit budget exceeded', expr.span);
      if (expr.kind === 'call') {
        const args = expr.args ?? [];
        if (expr.value === 'leaf_hash' && args.length === 1 && args[0]?.kind === 'name') {
          const path = args[0].value!.split('.');
          if (path.length === 2) {
            target.add(`leaf:${path[0]}.${path[1]}`);
          }
        } else if ((expr.value === 'contract_root' || expr.value === 'merkle_root') && args.length === 1 && args[0]?.kind === 'name' && !args[0].value!.includes('.')) {
          target.add(`root:${args[0].value}`);
        } else {
          for (const arg of args) scan(arg, target, helpers);
          const helper = this.program.helpers.get(expr.value!);
          if (helper && !helpers.includes(helper.name)) {
            let dependencies = this.helperDependencies.get(helper.name);
            if (!dependencies) {
              if (helpers.length >= 16) this.fatal('E0706', 'helper dependency depth exceeded', expr.span);
              const inner = new Set<string>();
              scanHelper(helper.body, inner, [...helpers, helper.name]);
              dependencies = [...inner];
              this.helperDependencies.set(helper.name, dependencies);
            }
            for (const dependency of dependencies) target.add(dependency);
          }
        }
      } else {
        if (expr.left) scan(expr.left, target, helpers);
        if (expr.right) scan(expr.right, target, helpers);
      }
    };
    const statements = (body: Stmt[]): void => {
      for (const stmt of body) {
        if (stmt.expr) scan(stmt.expr, found, []);
        if (stmt.then) statements(stmt.then);
        if (stmt.otherwise) statements(stmt.otherwise);
      }
    };
    statements(method.body);
    return [...found];
  }
  async compileAsync(onEvent?: (event: SchedulerEvent) => void): Promise<ContractArtifact> {
    this.contract(this.options.contract);
    const scheduler = new PromiseScheduler<void>(onEvent);
    this.enforceScheduledJobs = true;
    const execute = (name: string, job: () => void): void => {
      this.scheduledJob = name;
      try { job(); } finally { this.scheduledJob = undefined; }
    };
    // Register all declarations from the single parsed program. Jobs compile
    // only after their leaf/root dependencies have completed successfully.
    for (const contract of this.program.contracts.values()) {
      for (const method of contract.methods) {
        const name = `leaf:${contract.name}.${method.name}`;
        scheduler.register(name, () => this.dependencies(method), () => execute(name, () => { this.method(contract.name, method.name); }), artifactSpan(method.span));
      }
      const name = `root:${contract.name}`;
      scheduler.register(name, contract.methods.map(method => `leaf:${contract.name}.${method.name}`), () => execute(name, () => { this.root(contract.name); }), artifactSpan(contract.span));
    }
    await scheduler.run(`root:${this.options.contract}`);
    this.enforceScheduledJobs = false;
    return this.compile();
  }
  private root(name: string): Tree {
    const old = this.rootMemo.get(name); if (old) return old;
    if (this.enforceScheduledJobs && this.scheduledJob !== `root:${name}`) this.fatal('E9001', `unscheduled root dependency ${name}`, this.contract(name).span);
    if (this.rootActive.has(name)) this.fatal('E0801', `contract-root dependency cycle at ${name}`, this.contract(name).span);
    this.rootActive.add(name);
    try {
      this.bound(name);
      const leaves = this.contract(name).methods.map(m => ({ name: m.name, hash: this.method(name,m.name).leaf }));
      let result: Tree;
      try { result = tree(leaves); }
      catch (error) {
        const message = (error as Error).message;
        this.fatal(message === 'duplicate method leaf' ? 'E0207' : 'E0119', message, this.contract(name).span);
      }
      this.rootMemo.set(name, result); return result;
    } finally { this.rootActive.delete(name); }
  }
  private method(contractName: string, methodName: string): Compiled {
    const key = `${contractName}.${methodName}`; const old = this.methodMemo.get(key); if (old) return old;
    if (this.enforceScheduledJobs && this.scheduledJob !== `leaf:${key}`) this.fatal('E9001', `unscheduled leaf dependency ${key}`, this.findMethod(contractName, methodName).span);
    if (this.methodActive.has(key)) this.fatal('E0801', `method-leaf dependency cycle at ${key}`, this.findMethod(contractName, methodName).span);
    this.methodActive.add(key);
    try {
      const method = this.findMethod(contractName,methodName); const c = this.contract(contractName); const bindings = this.bound(contractName);
      const env: Env = new Map();
      for (const p of c.params) env.set(p.name,{ kind: 'constant', type: p.type, data: bindings.get(p.name)!.bytes });
      const stackParams = c.kind === 'token' ? [...method.params.slice(1),method.params[0]!] : method.params;
      for (const [index,p] of stackParams.entries()) {
        if (env.has(p.name)) this.fatal('E0205', `method parameter ${p.name} shadows constructor`, p.span);
        env.set(p.name,{ kind: 'argument', type: p.type, index });
      }
      const emitter = new Emitter(stackParams.length, (code, message, span, frames) => this.fatal(code, message, span, frames));
      const helperStack: string[] = [];
      let inferenceVisits = 0;
      const inferBlock = (body: HelperStmt[], scope: Env, active: string[], frames: Frame[], returning: boolean): Checked => {
        const introduced: string[] = [];
        try {
          for (const stmt of body) {
            if (stmt.kind === 'let') {
              if (scope.has(stmt.name)) return this.problem('E0208', `let ${stmt.name} shadows a binding`, stmt.nameSpan, frames);
              const t = infer(stmt.expr, scope, active, frames);
              if (t === 'Error') return 'Error';
              if (t !== stmt.type) return this.problem('E0414', `let ${stmt.name} expects ${stmt.type}, got ${t}`, stmt.expr.span, frames);
              scope.set(stmt.name, { kind: 'local', type: stmt.type, index: -1 });
              introduced.push(stmt.name);
            } else if (stmt.kind === 'require') {
              for (const part of conjuncts(stmt.expr)) {
                const t = infer(part, scope, active, frames);
                if (t === 'Error') return 'Error';
                if (t !== 'Bool') return this.problem('E0404', `require requires Bool, got ${t}`, part.span, frames);
              }
            } else if (stmt.kind === 'if') {
              const t = infer(stmt.expr, scope, active, frames);
              if (t === 'Error') return 'Error';
              if (t !== 'Bool') return this.problem('E0404', `if requires Bool, got ${t}`, stmt.expr.span, frames);
              if (inferBlock(stmt.then, scope, active, frames, false) === 'Error') return 'Error';
              if (inferBlock(stmt.otherwise, scope, active, frames, false) === 'Error') return 'Error';
            } else {
              if (!returning) return this.problem('E0123', 'return must be the final statement of the helper', stmt.span, frames);
              return infer(stmt.expr, scope, active, frames);
            }
          }
          if (returning) return this.problem('E0123', 'helper must end with return', body.at(-1)?.span, frames);
          return 'Bool';
        } finally { for (const name of introduced) scope.delete(name); }
      };
      const infer = (expr: Expr, scope: Env, active: string[] = [], frames: Frame[] = []): Checked => {
        if (++inferenceVisits > MAX_INFERENCE_VISITS) this.fatal('E0704', 'type inference visit budget exceeded', expr.span, frames);
        if (expr.kind === 'number') { const n = BigInt(expr.value!); if (n < INT_MIN || n >= INT_MAX) return this.problem('E0413', INT_RANGE, expr.span, frames); return 'Int'; }
        if (expr.kind === 'bool') return 'Bool';
        if (expr.kind === 'name') {
          if (expr.value === 'this.root') return c.kind === 'token' ? 'TokenId' : 'ContractRootHash';
          if (expr.value === 'this.coin.token_id') { if (c.kind === 'token') return this.problem('E0411', 'mint method has no coin', expr.span, frames); return 'TokenId'; }
          if (expr.value === 'this.coin.value') { if (c.kind === 'token') return this.problem('E0411', 'mint method has no coin', expr.span, frames); return 'Amount'; }
          const dot = expr.value!.split('.');
          if ((dot.length === 2 && (dot[1] === 'token_id' || dot[1] === 'value' || dot[1] === 'is_spend')) || (dot.length === 3 && dot[1] === 'coin' && ['token_id','value'].includes(dot[2]!))) {
            const v = scope.get(dot[0]!);
            if (!v || v.kind !== 'local' || (v.type !== 'InputIndex' && v.type !== 'OutputIndex')) return this.problem('E0305', `unbound record ${dot[0]}`, expr.span, frames, this.hint(dot[0]!, scope));
            if (dot.length === 3 && v.type !== 'InputIndex') return this.problem('E0412', 'coin field requires input', expr.span, frames);
            if (dot[1] === 'is_spend') { if (v.type !== 'InputIndex') return this.problem('E0412', 'is_spend requires input', expr.span, frames); return 'Bool'; }
            return dot.at(-1) === 'token_id' ? 'TokenId' : 'Amount';
          }
          const v = scope.get(expr.value!); if (!v) return this.problem('E0301', `unbound name ${expr.value}`, expr.span, frames, this.hint(expr.value!, scope));
          return v.kind === 'substitute' ? infer(v.expr, v.env, active, v.frames) : v.type;
        }
        if (expr.kind === 'unary') {
          if (expr.value === '-' && expr.right?.kind === 'number') { const n = -BigInt(expr.right.value!); if (n < INT_MIN || n >= INT_MAX) return this.problem('E0413', INT_RANGE, expr.span, frames); return 'Int'; }
          const t = infer(expr.right!, scope, active, frames);
          if (t === 'Error') return 'Error';
          if ((expr.value === '!' && t === 'Bool') || (expr.value === '-' && t === 'Int')) return t;
          return this.problem('E0402', `invalid unary ${expr.value} on ${t}`, expr.span, frames);
        }
        if (expr.kind === 'binary') {
          const a = infer(expr.left!, scope, active, frames), b = infer(expr.right!, scope, active, frames);
          if (a === 'Error' || b === 'Error') return 'Error';
          if (a !== b && !(['Int','Amount'].includes(a) && ['Int','Amount'].includes(b))) return this.problem('E0401', `binary type mismatch ${a}, ${b}`, expr.span, frames);
          if (expr.value === '==' || expr.value === '!=') return 'Bool';
          if (['+','-','*'].includes(expr.value!) && ['Int','Amount'].includes(a) && ['Int','Amount'].includes(b)) return a === 'Amount' || b === 'Amount' ? 'Amount' : 'Int';
          if (['<','>','<=','>='].includes(expr.value!) && ['Int','Amount'].includes(a) && ['Int','Amount'].includes(b)) return 'Bool';
          if (['&&','||'].includes(expr.value!) && a === 'Bool') return 'Bool';
          return this.problem('E0403', `invalid binary ${expr.value} on ${a}`, expr.span, frames);
        }
        if (expr.kind !== 'call') return this.problem('E9001', 'unknown expression', expr.span, frames);
        const name = expr.value!, args = expr.args ?? [];
        if (name === 'num_bytes') {
          if (args.length !== 1 || infer(args[0]!, scope, active, frames) !== 'Int') return this.problem('E0405', 'num_bytes expects Int', expr.span, frames);
          return 'Bytes(16)';
        }
        if (name === 'check_lock' || name === 'check_sequence') {
          if (args.length !== 2 || args.some(arg => infer(arg, scope, active, frames) !== 'Int')) return this.problem('E0405', `${name} expects Int kind and bound`, expr.span, frames);
          return 'Bool';
        }
        if (name.endsWith('.branch') || name.endsWith('.branch_count')) {
          const path = name.split('.'), current = path.slice(0,-1).join('.') === 'this.coin', receiver = scope.get(path[0]!);
          if (current ? c.kind === 'token' : !(receiver?.kind === 'local' && ['InputIndex','OutputIndex'].includes(receiver.type) && (path.length === 2 || path.length === 3 && path[1] === 'coin' && receiver.type === 'InputIndex'))) return this.problem('E0412', 'branch read requires a spend coin or enumerated input/output', expr.span, frames);
          const branch = name.endsWith('.branch');
          if (args.length !== (branch ? 1 : 0) || branch && infer(args[0]!, scope, active, frames) !== 'Int') return this.problem('E0405', 'branch index must be Int; branch_count takes no arguments', expr.span, frames);
          return branch ? 'Bytes32' : 'Int';
        }
        if (name === 'leaf_hash') { if (args.length !== 1 || args[0]!.kind !== 'name' || args[0]!.value!.split('.').length !== 2) return this.problem('E0502', 'leaf_hash requires Contract.method', expr.span, frames); return 'MethodLeafHash'; }
        if (name === 'contract_root' || name === 'merkle_root') { if (args.length !== 1 || args[0]!.kind !== 'name' || args[0]!.value!.includes('.')) return this.problem('E0502', `${name} requires tree name`, expr.span, frames); return this.contract(args[0]!.value!, args[0]!.span).kind === 'token' ? 'TokenId' : 'ContractRootHash'; }
        if (name.endsWith('.requires_branch') || name.endsWith('.exclusive_branch') || name.endsWith('.continues_branch')) {
          const parts = name.split('.'), receiver = scope.get(parts[0]!);
          const inputPredicate = name.endsWith('.requires_branch') && receiver?.type === 'InputIndex';
          if (inputPredicate ? !(parts.length === 2 || parts.length === 3 && parts[1] === 'coin') : parts.length !== 2 || receiver?.type !== 'OutputIndex') return this.problem('E0412', 'branch predicate requires an enumerated input/output receiver', expr.span, frames);
          if (args.length !== 1) return this.problem('E0412', 'requires_branch expects output and contract root', expr.span, frames);
          const arg = infer(args[0]!, scope, active, frames); if (arg === 'Error') return 'Error';
          if (arg !== 'ContractRootHash') return this.problem('E0412', 'requires_branch expects output and contract root', expr.span, frames);
          return 'Bool';
        }
        if (name === 'checksig') { if (args.length !== 2) return this.problem('E0502', 'checksig expects Signature, PublicKey', expr.span, frames); const a = infer(args[0]!, scope, active, frames), b = infer(args[1]!, scope, active, frames); if (a === 'Error' || b === 'Error') return 'Error'; if (a !== 'Signature' || b !== 'PublicKey') return this.problem('E0405', 'checksig expects Signature, PublicKey', expr.span, frames); return 'Bool'; }
        if (['sha256','hash256','blake3'].includes(name)) {
          if (args.length !== 1) return this.problem('E0502', `${name} expects one byte value`, expr.span, frames);
          const t = infer(args[0]!, scope, active, frames);
          if (t === 'Error') return 'Error';
          if (!['PublicKey','Signature','Bytes32','MethodLeafHash','ContractRootHash'].includes(t) && !t.startsWith('Bytes(')) return this.problem('E0405', `${name} expects bytes`, expr.span, frames);
          return 'Bytes32';
        }
        const helper = this.program.helpers.get(name); if (!helper) return this.problem('E0302', `unknown function ${name}`, expr.span, frames, this.hint(name, scope));
        if (helper.params.length !== args.length) return this.problem('E0501', `helper ${name} arity mismatch`, expr.span, frames);
        if (active.includes(name) || active.length >= 16) this.fatal('E0503', `recursive helper ${name}`, expr.span, frames);
        const inner: Env = new Map();
        const next = [...frames, { name: helper.name, at: expr.span }];
        for (let i = 0; i < args.length; i++) {
          const p = helper.params[i]!, actual = infer(args[i]!, scope, active, frames);
          if (actual === 'Error') return 'Error';
          if (actual !== p.type) return this.problem('E0406', `helper ${name}.${p.name} expects ${p.type}, got ${actual}`, args[i]!.span, frames);
          inner.set(p.name, { kind:'substitute', type:p.type, expr:args[i]!, env:scope, origin:expr.span, frames });
        }
        const result = inferBlock(helper.body, inner, [...active, name], next, true);
        if (result === 'Error') return 'Error';
        if (result !== helper.result) return this.problem('E0407', `helper ${name} returns ${result}, declared ${helper.result}`, helperReturn(helper.body)?.expr.span ?? helper.span, next);
        return result;
      };
      let emitBlock!: (body: HelperStmt[], scope: Env, origin: Span | undefined, frames: Frame[], returning: boolean) => Checked;
      const expression = (expr: Expr, scope: Env, origin?: Span, frames: Frame[] = []): Checked => {
        emitter.frames = frames;
        if (expr.kind === 'number') {
          const n = BigInt(expr.value!); if (n < INT_MIN || n >= INT_MAX) return this.problem('E0413', INT_RANGE, expr.span, frames);
          emitter.number(n, expr.span, origin); return 'Int';
        }
        if (expr.kind === 'bool') { emitter.number(expr.value === 'true' ? 1n : 0n, expr.span, origin); return 'Bool'; }
        if (expr.kind === 'name') {
          if (expr.value === 'this.root') { emitter.op('BRANCHROOT', expr.span, origin, 1); return c.kind === 'token' ? 'TokenId' : 'ContractRootHash'; }
          if (expr.value === 'this.coin.token_id' || expr.value === 'this.coin.value') {
            if (c.kind === 'token') return this.problem('E0411', 'mint method has no coin', expr.span, frames);
            emitter.op('INPUTINDEX', expr.span, origin, 1);
            emitter.op(expr.value.endsWith('token_id') ? 'UTXOTOKENID' : 'UTXOVALUE', expr.span, origin);
            return expr.value.endsWith('token_id') ? 'TokenId' : 'Amount';
          }
          const dot = expr.value!.split('.');
          if ((dot.length === 2 && ['token_id','value','is_spend'].includes(dot[1]!)) || (dot.length === 3 && dot[1] === 'coin' && ['token_id','value'].includes(dot[2]!))) {
            const v = scope.get(dot[0]!);
            if (!v || v.kind !== 'local' || (v.type !== 'InputIndex' && v.type !== 'OutputIndex')) return this.problem('E0305', `unbound record ${dot[0]}`, expr.span, frames, this.hint(dot[0]!, scope));
            if (dot.length === 3 && v.type !== 'InputIndex') return this.problem('E0412', 'coin field requires input', expr.span, frames);
            emitter.number(BigInt(emitter.height - 1 - v.index), expr.span, origin); emitter.op('PICK', expr.span, origin);
            if (dot[1] === 'is_spend') { if (v.type !== 'InputIndex') return this.problem('E0412', 'is_spend requires input', expr.span, frames); emitter.op('INPUTFLAGS', expr.span, origin); emitter.number(1n, expr.span, origin); emitter.op('NUMEQUAL', expr.span, origin, -1); return 'Bool'; }
            const field = dot.at(-1)!;
            const op = v.type === 'OutputIndex' ? (field === 'token_id' ? 'OUTPUTTOKENID' : 'OUTPUTVALUE') : (field === 'token_id' ? 'UTXOTOKENID' : 'UTXOVALUE');
            emitter.op(op, expr.span, origin); return field === 'token_id' ? 'TokenId' : 'Amount';
          }
          const v = scope.get(expr.value!); if (!v) return this.problem('E0301', `unbound name ${expr.value}`, expr.span, frames, this.hint(expr.value!, scope));
          if (v.kind === 'constant') emitter.push(v.data, expr.span, origin);
          else if (v.kind === 'argument' || v.kind === 'local') { emitter.number(BigInt(emitter.height - 1 - v.index), expr.span, origin); emitter.op('PICK', expr.span, origin); }
          else {
            const actual = expression(v.expr, v.env, v.origin, v.frames);
            if (actual === 'Error') return 'Error';
            if (actual !== v.type) return this.problem('E0406', `helper substitution expected ${v.type}, got ${actual}`, expr.span, frames);
            return actual;
          }
          return v.type;
        }
        if (expr.kind === 'unary') {
          if (expr.value === '-' && expr.right?.kind === 'number') {
            const n = -BigInt(expr.right.value!); if (n < INT_MIN || n >= INT_MAX) return this.problem('E0413', INT_RANGE, expr.span, frames);
            emitter.number(n, expr.span, origin); return 'Int';
          }
          const t = expression(expr.right!, scope, origin, frames);
          if (t === 'Error') return 'Error';
          if (expr.value === '!' && t === 'Bool') { emitter.op('NOT', expr.span, origin); return 'Bool'; }
          if (expr.value === '-' && t === 'Int') { emitter.op('NEGATE', expr.span, origin); return 'Int'; }
          return this.problem('E0402', `invalid unary ${expr.value} on ${t}`, expr.span, frames);
        }
        if (expr.kind === 'binary') {
          if (expr.value === '&&' || expr.value === '||') {
            const a = expression(expr.left!, scope, origin, frames);
            if (a === 'Error') return 'Error';
            if (a !== 'Bool') return this.problem('E0404', `${expr.value} requires Bool`, expr.left?.span ?? expr.span, frames);
            if (expr.value === '||') emitter.op('NOT', expr.span, origin);
            emitter.control('IF', expr.span); const before = emitter.height;
            const b = expression(expr.right!, scope, origin, frames);
            if (b === 'Error') return 'Error';
            if (b !== 'Bool') return this.problem('E0404', `${expr.value} requires Bool`, expr.right?.span ?? expr.span, frames);
            if (emitter.height !== before + 1) this.fatal('E9001', 'logical branch stack mismatch', expr.span, frames);
            emitter.control('ELSE', expr.span); emitter.height = before;
            emitter.number(expr.value === '&&' ? 0n : 1n, expr.span, origin);
            emitter.control('ENDIF', expr.span); return 'Bool';
          }
          const a = expression(expr.left!, scope, origin, frames), b = expression(expr.right!, scope, origin, frames);
          if (a === 'Error' || b === 'Error') return 'Error';
          if (expr.value === '==' || expr.value === '!=') {
            if (a !== b) return this.problem('E0401', `equality type mismatch ${a} and ${b}`, expr.span, frames);
            emitter.op('EQUAL', expr.span, origin, -1); if (expr.value === '!=') emitter.op('NOT', expr.span, origin); return 'Bool';
          }
          const cases: Record<string, [keyof typeof OPCODES, ValueType]> = { '+':['ADD', a], '-':['SUB', a], '*':['MUL', a], '<':['LESSTHAN', 'Bool'], '>':['GREATERTHAN', 'Bool'], '>=':['GREATERTHANOREQUAL', 'Bool'] };
          const rule = cases[expr.value!]; if (!rule || !['Int','Amount'].includes(a) || !['Int','Amount'].includes(b)) return this.problem('E0403', `invalid ${expr.value} operands ${a}, ${b}`, expr.span, frames);
          emitter.op(rule[0], expr.span, origin, -1); return ['+','-','*'].includes(expr.value!) && (a === 'Amount' || b === 'Amount') ? 'Amount' : rule[1];
        }
        if (expr.kind !== 'call') return this.problem('E9001', 'unknown expression', expr.span, frames);
        const args = expr.args ?? [];
        const name = expr.value!;
        if (name === 'num_bytes') {
          if (args.length !== 1) return this.problem('E0405', 'num_bytes expects Int', expr.span, frames);
          if (expression(args[0]!, scope, origin, frames) !== 'Int') return this.problem('E0405', 'num_bytes expects Int', expr.span, frames);
          // Numeric ADD validates an adversarial witness as canonical P03 N.
          emitter.number(0n, expr.span, origin); emitter.op('ADD', expr.span, origin, -1);
          return 'Bytes(16)';
        }
        if (name === 'check_lock' || name === 'check_sequence') {
          if (args.length !== 2) return this.problem('E0405', `${name} expects Int kind and bound`, expr.span, frames);
          const kind = expression(args[0]!, scope, origin, frames), bound = expression(args[1]!, scope, origin, frames);
          if (kind !== 'Int' || bound !== 'Int') return this.problem('E0405', `${name} expects Int kind and bound`, expr.span, frames);
          emitter.op(name === 'check_lock' ? 'CHECKLOCKTIMEVERIFY' : 'CHECKSEQUENCEVERIFY', expr.span, origin, -2);
          emitter.number(1n, expr.span, origin); return 'Bool';
        }
        if (name.endsWith('.branch') || name.endsWith('.branch_count')) {
          const path = name.split('.'), current = path.slice(0,-1).join('.') === 'this.coin', receiver = scope.get(path[0]!);
          if (current ? c.kind === 'token' : !(receiver?.kind === 'local' && ['InputIndex','OutputIndex'].includes(receiver.type) && (path.length === 2 || path.length === 3 && path[1] === 'coin' && receiver.type === 'InputIndex'))) return this.problem('E0412', 'branch read requires a spend coin or enumerated input/output', expr.span, frames);
          const branch = name.endsWith('.branch');
          if (args.length !== (branch ? 1 : 0)) return this.problem('E0405', 'branch expects one Int index; branch_count takes no arguments', expr.span, frames);
          if (current) emitter.op('INPUTINDEX', expr.span, origin, 1);
          else { const v = receiver!; if (v.kind !== 'local') return this.problem('E0412', 'branch read requires a local index', expr.span, frames); emitter.number(BigInt(emitter.height - 1 - v.index), expr.span, origin); emitter.op('PICK', expr.span, origin); }
          if (branch && expression(args[0]!, scope, origin, frames) !== 'Int') return this.problem('E0405', 'branch index must be Int', expr.span, frames);
          const output = !current && receiver!.type === 'OutputIndex';
          emitter.op(output ? (branch ? 'OUTPUTBRANCH' : 'OUTPUTBRANCHCOUNT') : (branch ? 'UTXOBRANCH' : 'UTXOBRANCHCOUNT'), expr.span, origin, branch ? -1 : 0);
          return branch ? 'Bytes32' : 'Int';
        }
        if (name === 'leaf_hash') {
          if (args.length !== 1 || args[0]!.kind !== 'name') return this.problem('E0502', 'leaf_hash requires Contract.method name', expr.span, frames);
          const path = args[0]!.value!.split('.'); if (path.length !== 2) return this.problem('E0502', 'leaf_hash requires Contract.method name', expr.span, frames);
          emitter.push(this.method(path[0]!, path[1]!).leaf, expr.span, origin); return 'MethodLeafHash';
        }
        if (name === 'contract_root' || name === 'merkle_root') {
          if (args.length !== 1 || args[0]!.kind !== 'name' || args[0]!.value!.includes('.')) return this.problem('E0502', 'contract_root requires Contract name', expr.span, frames);
          const other = this.contract(args[0]!.value!, args[0]!.span); emitter.push(this.root(other.name).root, expr.span, origin); return other.kind === 'token' ? 'TokenId' : 'ContractRootHash';
        }
        if (name.endsWith('.requires_branch') || name.endsWith('.exclusive_branch') || name.endsWith('.continues_branch')) {
          const parts = name.split('.'), v = scope.get(parts[0]!);
          const inputPredicate = name.endsWith('.requires_branch') && v?.type === 'InputIndex';
          if (inputPredicate ? !(parts.length === 2 || parts.length === 3 && parts[1] === 'coin') : parts.length !== 2 || v?.type !== 'OutputIndex') return this.problem('E0412', 'branch predicate requires an enumerated input/output receiver', expr.span, frames);
          if (!v || v.kind !== 'local' || args.length !== 1) return this.problem('E0412', 'requires_branch requires output index and one root', expr.span, frames);
          emitter.number(BigInt(emitter.height - 1 - v.index), expr.span, origin); emitter.op('PICK', expr.span, origin);
          const t = expression(args[0]!, scope, origin, frames);
          if (t === 'Error') return 'Error';
          if (t !== 'ContractRootHash') return this.problem('E0412', 'requires_branch requires ContractRootHash', args[0]!.span, frames);
          emitter.op(inputPredicate ? 'UTXOREQUIRESBRANCH' : name.endsWith('.exclusive_branch') ? 'OUTPUTEXCLUSIVEBRANCH' : name.endsWith('.continues_branch') ? 'OUTPUTCONTINUESBRANCH' : 'OUTPUTREQUIRESBRANCH', expr.span, origin, -1); return 'Bool';
        }
        if (name === 'checksig') {
          if (args.length !== 2) return this.problem('E0502', 'checksig needs signature and PublicKey', expr.span, frames);
          const a = expression(args[0]!, scope, origin, frames), b = expression(args[1]!, scope, origin, frames);
          if (a === 'Error' || b === 'Error') return 'Error';
          if (a !== 'Signature' || b !== 'PublicKey') return this.problem('E0405', 'checksig expects Signature, PublicKey', expr.span, frames);
          emitter.op('CHECKSIG', expr.span, origin, -1); return 'Bool';
        }
        const hashes: Record<string, keyof typeof OPCODES> = { sha256:'SHA256', hash256:'HASH256', blake3:'BLAKE3' };
        if (hashes[name]) {
          if (args.length !== 1) return this.problem('E0502', `${name} expects one byte value`, expr.span, frames);
          const t = expression(args[0]!, scope, origin, frames);
          if (t === 'Error') return 'Error';
          if (!['PublicKey','Signature','Bytes32','MethodLeafHash','ContractRootHash'].includes(t) && !t.startsWith('Bytes(')) return this.problem('E0405', `${name} expects byte value, got ${t}`, expr.span, frames);
          emitter.op(hashes[name], expr.span, origin); return 'Bytes32';
        }
        const helper = this.program.helpers.get(name); if (!helper) return this.problem('E0302', `unknown function ${name}`, expr.span, frames, this.hint(name, scope));
        if (helper.params.length !== args.length) return this.problem('E0501', `helper ${name} arity mismatch`, expr.span, frames);
        if (helperStack.includes(name)) this.fatal('E0503', `recursive helper ${name}`, expr.span, frames);
        if (++emitter.expansions > MAX_EXPANSIONS || helperStack.length >= 16) this.fatal('E0703', 'helper expansion budget exceeded', expr.span, frames);
        const inner: Env = new Map();
        // Each helper parameter is a hygienically scoped expression thunk. The
        // source argument is checked against the declared parameter type once.
        // `frames` stays the caller's chain; the body is checked under `next`.
        for (let i = 0; i < args.length; i++) {
          const p = helper.params[i]!;
          const actual = infer(args[i]!, scope, helperStack, frames);
          if (actual === 'Error') return 'Error';
          if (actual !== p.type) return this.problem('E0406', `helper ${name}.${p.name} expects ${p.type}, got ${actual}`, args[i]!.span, frames);
          inner.set(p.name, { kind: 'substitute', type: p.type, expr: args[i]!, env: scope, origin: expr.span, frames });
        }
        const next = [...frames, { name: helper.name, at: expr.span }];
        helperStack.push(name);
        try {
          const result = emitBlock(helper.body, inner, expr.span, next, true);
          if (result === 'Error') return 'Error';
          if (result !== helper.result) return this.problem('E0407', `helper ${name} returns ${result}, declared ${helper.result}`, helperReturn(helper.body)?.expr.span ?? helper.span, next);
          return result;
        } finally { helperStack.pop(); }
      };
      // Split only a require operand. Each conjunct is verified immediately, so
      // CHECKSIG/EQUAL sit next to VERIFY. `||` is left as a short-circuit.
      const emitRequire = (expr: Expr, scope: Env, origin: Span | undefined, frames: Frame[], span: Span): void => {
        for (const part of conjuncts(expr)) {
          const t = expression(part, scope, origin, frames);
          if (t === 'Error') continue;
          if (t !== 'Bool') {
            this.problem('E0404', `require requires Bool, got ${t}`, part.span, frames);
            emitter.op('DROP', part.span, origin, -1);
            continue;
          }
          emitter.op('VERIFY', span, origin, -1);
        }
      };
      emitBlock = (body, scope, origin, frames, returning) => {
        const introduced: string[] = [];
        const forget = (): void => { for (const name of introduced) scope.delete(name); introduced.length = 0; };
        const dropTop = (span: Span): void => {
          for (let n = introduced.length; n > 0; n--) emitter.op('DROP', span, origin, -1);
          forget();
        };
        // Locals sit under the return value. ROLL 1 brings each one to the top.
        const buryReturn = (span: Span): void => {
          for (let n = introduced.length; n > 0; n--) {
            emitter.number(1n, span, origin); emitter.op('ROLL', span, origin, -1); emitter.op('DROP', span, origin, -1);
          }
          forget();
        };
        try {
          for (const stmt of body) {
            if (stmt.kind === 'let') {
              if (scope.has(stmt.name)) { this.problem('E0208', `let ${stmt.name} shadows a binding`, stmt.nameSpan, frames); continue; }
              const t = expression(stmt.expr, scope, origin, frames);
              if (t === 'Error') continue;
              if (t !== stmt.type) {
                this.problem('E0414', `let ${stmt.name} expects ${stmt.type}, got ${t}`, stmt.expr.span, frames);
                emitter.op('DROP', stmt.span, origin, -1); continue;
              }
              scope.set(stmt.name, { kind: 'local', type: t, index: emitter.height - 1 });
              introduced.push(stmt.name);
            } else if (stmt.kind === 'require') emitRequire(stmt.expr, scope, origin, frames, stmt.span);
            else if (stmt.kind === 'if') {
              const t = expression(stmt.expr, scope, origin, frames);
              if (t === 'Error') continue;
              if (t !== 'Bool') { this.problem('E0404', `if requires Bool, got ${t}`, stmt.expr.span, frames); emitter.op('DROP', stmt.span, origin, -1); continue; }
              emitter.control('IF', stmt.span, origin);
              const before = emitter.height;
              if (emitBlock(stmt.then, scope, origin, frames, false) === 'Error') return 'Error';
              if (emitter.height !== before) this.fatal('E9001', 'then stack mismatch', stmt.span, frames);
              emitter.control('ELSE', stmt.span, origin);
              if (emitBlock(stmt.otherwise, scope, origin, frames, false) === 'Error') return 'Error';
              if (emitter.height !== before) this.fatal('E9001', 'else stack mismatch', stmt.span, frames);
              emitter.control('ENDIF', stmt.span, origin);
            } else {
              if (!returning) return this.problem('E0123', 'return must be the final statement of the helper', stmt.span, frames);
              const t = expression(stmt.expr, scope, origin, frames);
              if (t === 'Error') return 'Error';
              buryReturn(stmt.span);
              return t;
            }
          }
          if (returning) return this.problem('E0123', 'helper must end with return', body.at(-1)?.span ?? frames.at(-1)?.at, frames);
          dropTop(body.at(-1)?.span ?? frames.at(-1)?.at ?? { start: 0, end: 0 });
          return 'Bool';
        } finally { for (const name of introduced) scope.delete(name); }
      };
      const statements = (body: Stmt[], nested = false): void => {
        for (const stmt of body) {
          if (stmt.kind === 'for') {
            const name = stmt.variable!;
            if (env.has(name)) this.fatal('E0206', `loop variable ${name} shadows binding`, stmt.span);
            const before = emitter.height;
            if (stmt.collection === 'tx.inputs') emitter.op('ENUMERATE_INPUTS',stmt.span,undefined,1);
            else emitter.op('ENUMERATE_OUTPUTS',stmt.span,undefined,1);
            env.set(name,{kind:'local',type:stmt.collection === 'tx.inputs' ? 'InputIndex' : 'OutputIndex',index:before});
            statements(stmt.then!,true);
            if (emitter.height !== before + 1) this.fatal('E9001', 'loop body stack mismatch', stmt.span);
            emitter.op('DROP',stmt.span,undefined,-1);
            emitter.op('ENDENUMERATE',stmt.span);
            env.delete(name); continue;
          }
          if (stmt.kind === 'assign') {
            const name = stmt.variable!, existing = env.get(name);
            if (!existing && (nested || stmt.assignOp !== '=')) this.fatal('E0410', `local ${name} must be initialized at method top level`, stmt.span);
            if (existing && (existing.kind !== 'local' || existing.type === 'InputIndex' || existing.type === 'OutputIndex')) this.fatal('E0409', `cannot assign ${name}`, stmt.span);
            if (stmt.assignOp !== '=') {
              emitter.number(BigInt(emitter.height - 1 - existing!.index),stmt.span); emitter.op('PICK',stmt.span);
            }
            const t = expression(stmt.expr!,env);
            if (t === 'Error') continue;
            if (t !== 'Int' && t !== 'Amount') this.fatal('E0408', 'numeric local required', stmt.expr?.span ?? stmt.span);
            if (stmt.assignOp !== '=') emitter.op(stmt.assignOp === '+=' ? 'ADD':'SUB',stmt.span,undefined,-1);
            if (!existing) env.set(name,{kind:'local',type:t,index:emitter.height - 1});
            else {
              const oldHeight = emitter.height - 1;
              const depth = oldHeight - existing.index;
              emitter.number(BigInt(depth),stmt.span); emitter.op('ROLL',stmt.span,undefined,-1); emitter.op('DROP',stmt.span,undefined,-1);
              for (let i = 0; i < depth - 1; i++) { emitter.number(BigInt(depth - 1),stmt.span); emitter.op('ROLL',stmt.span,undefined,-1); }
              env.set(name,{...existing,type:t === 'Amount' ? 'Amount' : existing.type});
            }
            continue;
          }
          if (stmt.kind === 'require') { emitRequire(stmt.expr!, env, undefined, [], stmt.span); continue; }
          const t = expression(stmt.expr!,env);
          if (t === 'Error') continue;
          if (t !== 'Bool') { this.problem('E0404', `${stmt.kind} requires Bool, got ${t}`, stmt.expr?.span ?? stmt.span); emitter.op('DROP', stmt.span, undefined, -1); continue; }
          {
            emitter.control('IF',stmt.span);
            const before = emitter.height;
            statements(stmt.then!,true);
            if (emitter.height !== before) this.fatal('E9001', 'then stack mismatch', stmt.span);
            emitter.control('ELSE',stmt.span);
            statements(stmt.otherwise!,true);
            if (emitter.height !== before) this.fatal('E9001', 'else stack mismatch', stmt.span);
            emitter.control('ENDIF',stmt.span);
          }
        }
      };
      statements(method.body);
      this.diag.checkpoint();
      for (let i = emitter.height - stackParams.length; i > 0; i--) emitter.op('DROP',method.span,undefined,-1);
      for (let i = 0; i < method.params.length; i++) emitter.op('DROP',method.span,undefined,-1);
      emitter.number(1n,method.span);
      if (emitter.height !== 1) this.fatal('E9001', 'compiled method final stack mismatch', method.span);
      const finished = emitter.finish(this.options.optimize !== false); const script = finished.script;
      let loopMultiplier = 1, worstCaseSignatureChecks = 0;
      for (const entry of finished.map) {
        if (entry.op === 'ENUMERATE_INPUTS' || entry.op === 'ENUMERATE_OUTPUTS') loopMultiplier *= 65535;
        else if (entry.op === 'ENDENUMERATE') loopMultiplier /= 65535;
        else if (entry.op === 'CHECKSIG' || entry.op === 'CHECKSIGVERIFY') worstCaseSignatureChecks += loopMultiplier;
      }
      const compiled = { script, leaf: leafHash(script), map: finished.map,
        resources: { ...finished.resources,
          helperExpansions: emitter.expansions, dynamicSignatureChecks: worstCaseSignatureChecks } };
      this.methodMemo.set(key,compiled); return compiled;
    } finally { this.methodActive.delete(key); }
  }
  compile(): ContractArtifact {
    const c = this.contract(this.options.contract); const root = this.root(c.name); const bound = this.bound(c.name);
    const methods: MethodArtifact[] = c.methods.map(m => {
      const compiled = this.method(c.name,m.name);
      return { name: m.name, invocation:c.kind === 'token' ? 'mint' as const : 'spend' as const,
        ...(c.kind === 'token' ? { mintAmountParam:m.params[0]!.name } : {}),
        args: (c.kind === 'token' ? m.params.slice(1) : m.params).map(p => ({ name:p.name,type:p.type })), scriptHex: hex(compiled.script), leaf: hex(compiled.leaf),
        proof: root.proofs.get(m.name)!.map(hex), root: hex(root.root), sourceMap: compiled.map, staticResources: compiled.resources };
    });
    return { schema: 'lotus-v2/contract-artifact/2', target: 'P01-P02-P03-candidate-2026-10-14', contract: c.name, kind:c.kind,
      constructor: c.params.map(p => ({ name:p.name,type:p.type })), bindings: c.params.map(p => ({ name:p.name,...bound.get(p.name)!.binding })),
      methods, policy: { branches: [hex(root.root)], paths: [[0]], root: hex(root.root), treeRecipe: 'sorted-leaves-largest-power-split-v1' } };
  }
  /** Roots actually compiled for this program, including dependencies of the selected contract. */
  computedRoots(): { name: string; root: string; methods: { name: string; leaf: string }[] }[] {
    const out: { name: string; root: string; methods: { name: string; leaf: string }[] }[] = [];
    for (const [name, tree] of this.rootMemo) {
      const c = this.contract(name);
      out.push({ name, root: hex(tree.root), methods: c.methods.map(m => {
        const compiled = this.methodMemo.get(`${name}.${m.name}`);
        if (!compiled) this.fatal('E9001', `missing compiled method ${name}.${m.name}`, m.span);
        return { name: m.name, leaf: hex(compiled.leaf) };
      }) });
    }
    out.sort((a, b) => a.name < b.name ? -1 : a.name > b.name ? 1 : 0);
    return out;
  }
}

function requireOptions(options: CompileOptions, bag: DiagnosticBag): void {
  if (typeof options?.contract !== 'string' || !options.bindings || typeof options.bindings !== 'object') bag.raise('E0601', 'compile options require contract and bindings');
}
function openSource(source: string, file: string, sources = new SourceManager()): DiagnosticBag {
  if (!sources.get(file)) sources.add(file, source);
  return new DiagnosticBag(sources, file);
}
function singleModule(source: string, file: string, bag: DiagnosticBag): Program {
  const program = new Parser(lex(source, file, bag), bag).parse();
  if (program.imports.length) bag.raise('E0121', 'import requires a package build (compilePackage)', program.imports[0]!.span);
  bag.checkpoint();
  return program;
}
export function compileContract(source: string, options: CompileOptions, file = '<source>'): ContractArtifact {
  const bag = openSource(source, file); requireOptions(options, bag);
  return new Compiler(singleModule(source, file, bag), options, bag).compile();
}
export async function compileContractAsync(source: string, options: CompileOptions, onEvent?: (event: SchedulerEvent) => void, file = '<source>'): Promise<ContractArtifact> {
  const bag = openSource(source, file); requireOptions(options, bag);
  return new Compiler(singleModule(source, file, bag), options, bag).compileAsync(onEvent);
}
/** @internal Package linker entry: parse one module (declaration-only modules may omit contracts). */
export function parseModuleSource(source: string, requireContract: boolean, file = '<source>', sources?: SourceManager): Program {
  const bag = openSource(source, file, sources);
  const program = new Parser(lex(source, file, bag), bag).parse(requireContract);
  bag.checkpoint();
  return program;
}
/** @internal Package linker entry: compile an already linked program through the promise scheduler. */
export async function compileLinkedProgramAsync(program: Program, options: CompileOptions, onEvent?: (event: SchedulerEvent) => void, sources?: SourceManager): Promise<{ artifact: ContractArtifact; roots: { name: string; root: string; methods: { name: string; leaf: string }[] }[] }> {
  const bag = new DiagnosticBag(sources ?? new SourceManager(), '<source>');
  requireOptions(options, bag);
  const compiler = new Compiler(program, options, bag);
  const artifact = await compiler.compileAsync(onEvent);
  return { artifact, roots: compiler.computedRoots() };
}
export async function compileContractWithTrace(source: string, options: CompileOptions, file = '<source>'): Promise<{ artifact: ContractArtifact; trace: SchedulerEvent[] }> {
  const trace: SchedulerEvent[] = [];
  const artifact = await compileContractAsync(source, options, event => trace.push(event), file);
  return { artifact, trace };
}
export function methodLeafHash(artifact: ContractArtifact, method: string): { kind: 'MethodLeafHash'; hex: string } {
  const m = artifact.methods.find(x => x.name === method); if (!m) throw new Error(`unknown method ${method}`);
  return { kind: 'MethodLeafHash', hex: m.leaf };
}
export function contractRootHash(artifact: ContractArtifact): { kind: 'ContractRootHash'; hex: string } {
  return { kind: 'ContractRootHash', hex: artifact.policy.root };
}
