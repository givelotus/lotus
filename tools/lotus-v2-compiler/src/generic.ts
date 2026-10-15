/** Bounded, typed P03 contract frontend. No VM or consensus-validation code. */
import { bytes, concat, cs, hex, tagged, unhex, uint, type Span } from './compiler.js';
import { schnorr } from '@noble/curves/secp256k1';
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
/** `private` (default, module only), `package` (same package) or `export` (other packages via exported modules). */
export type Visibility = 'private' | 'package' | 'export';
export type Helper = { name: string; params: Param[]; result: ValueType; body: Expr; span: Span; visibility: Visibility };
export type Method = { name: string; params: Param[]; body: Stmt[]; span: Span };
export type Contract = { name: string; kind: 'contract' | 'token'; params: Param[]; methods: Method[]; span: Span };
/** `import TARGET::path::{a, b as c};` or `import TARGET::path as alias;` where TARGET is a dependency alias or `package`. */
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
  build?: import('./packages.js').BuildGraph };
export type CompileOptions = { contract: string; bindings: Record<string, Record<string, BoundValue>>; optimize?: boolean };

const MAX_SOURCE = 65536, MAX_SCRIPT = 8192, MAX_OPS = 4096, MAX_EXPANSIONS = 256, MAX_METHODS = 16;
const MAX_INFERENCE_VISITS = 8192;
const MAX_DEPENDENCY_VISITS = 8192;
function symbol(name: string): void { assertPortableName(name); }
function utf8Offset(source: string, utf16: number): number { return new TextEncoder().encode(source.slice(0, utf16)).length; }
function lex(source: string): Token[] {
  if (new TextEncoder().encode(source).length > MAX_SOURCE) throw new Error('source exceeds 65536 UTF-8 bytes');
  const re = /\s+|\/\/[^\n]*|\/\*[\s\S]*?\*\/|==|!=|>=|<=|\+=|-=|&&|\|\||::|[A-Za-z_][A-Za-z_0-9]*|[0-9]+|[<>{}():;,.!+*\-=]/gy;
  const out: Token[] = []; let pos = 0;
  while (pos < source.length) {
    re.lastIndex = pos; const m = re.exec(source);
    if (!m) throw new Error(`unsupported character at UTF-8 byte ${utf8Offset(source, pos)}`);
    if (!/^\s|^\//.test(m[0])) out.push({ text: m[0], span: { start: utf8Offset(source, pos), end: utf8Offset(source, re.lastIndex) } });
    pos = re.lastIndex;
  }
  out.push({ text: '<eof>', span: { start: utf8Offset(source, pos), end: utf8Offset(source, pos) } });
  return out;
}
class Parser {
  private i = 0;
  constructor(private readonly tokens: Token[]) {}
  private peek(): Token { return this.tokens[this.i]!; }
  private take(expected?: string): Token { const t = this.peek(); if (expected && t.text !== expected) throw new Error(`expected ${expected} at UTF-8 byte ${t.span.start}`); this.i++; return t; }
  private ident(): Token { const t = this.take(); if (!/^[A-Za-z_][A-Za-z_0-9]*$/.test(t.text)) throw new Error(`expected identifier at UTF-8 byte ${t.span.start}`); return t; }
  private type(): ValueType {
    const t = this.ident();
    if (t.text === 'Bytes') { this.take('('); const n = this.take(); this.take(')'); if (!/^[0-9]+$/.test(n.text) || Number(n.text) < 1 || Number(n.text) > 8192) throw new Error(`Bytes bound 1..8192 at UTF-8 byte ${n.span.start}`); return `Bytes(${Number(n.text)})`; }
    if (['PublicKey','Signature','Bytes32','Int','Amount','TokenId','Bool','MethodLeafHash','ContractRootHash'].includes(t.text)) return t.text as ValueType;
    throw new Error(`unsupported type ${t.text} at UTF-8 byte ${t.span.start}`);
  }
  private params(close: string): Param[] {
    const out: Param[] = [];
    if (this.peek().text !== close) while (true) {
      const name = this.ident(); this.take(':'); const type = this.type();
      symbol(name.text);
      if (out.some(x => x.name === name.text)) throw new Error(`duplicate parameter ${name.text}`);
      out.push({ name: name.text, type, span: name.span });
      if (this.peek().text !== ',') break; this.take(',');
    }
    this.take(close); return out;
  }
  private expression(min = 0, depth = 0): Expr {
    if (depth > 64) throw new Error('expression depth exceeded');
    let left: Expr;
    const start = this.peek();
    if (start.text === '!' || start.text === '-') { this.take(); const inner = this.expression(7,depth + 1); left = { kind: 'unary', value: start.text, right: inner, span: { start: start.span.start, end: inner.span.end } }; }
    else if (start.text === '(') { this.take(); left = this.expression(0,depth + 1); this.take(')'); }
    else if (/^[0-9]+$/.test(start.text)) { this.take(); left = { kind: 'number', value: start.text, span: start.span }; }
    else if (start.text === 'true' || start.text === 'false') { this.take(); left = { kind: 'bool', value: start.text, span: start.span }; }
    else {
      const name = this.ident(); let value = name.text;
      if (this.peek().text === '::') {
        // Module-alias call `alias::helper(...)`; only meaningful in package builds.
        this.take('::'); value += '::' + this.ident().text;
        if (this.peek().text !== '(') throw new Error(`qualified name ${value} must be called at UTF-8 byte ${name.span.start}`);
      }
      while (this.peek().text === '.') { this.take('.'); value += '.' + this.ident().text; }
      if (this.peek().text === '(') {
        this.take('('); const args: Expr[] = [];
        if (this.peek().text !== ')') while (true) { args.push(this.expression(0,depth + 1)); if (this.peek().text !== ',') break; this.take(','); }
        const end = this.take(')'); left = { kind: 'call', value, args, span: { start: name.span.start, end: end.span.end } };
      } else left = { kind: 'name', value, span: { start: name.span.start, end: this.tokens[this.i - 1]!.span.end } };
    }
    const precedence: Record<string, number> = { '||': 1, '&&': 2, '==': 3, '!=': 3, '<': 4, '>': 4, '<=':4, '>=':4, '+': 5, '-': 5, '*': 6 };
    while ((precedence[this.peek().text] ?? 0) >= min && precedence[this.peek().text]) {
      const op = this.take(); const right = this.expression(precedence[op.text]! + 1,depth + 1);
      left = { kind: 'binary', value: op.text, left, right, span: { start: left.span.start, end: right.span.end } };
    }
    return left;
  }
  private statements(depth = 0, loops = 0): Stmt[] {
    if (depth > 16) throw new Error('control nesting depth exceeded');
    this.take('{'); const out: Stmt[] = [];
    while (this.peek().text !== '}') {
      const start = this.take();
      if (start.text === 'require') { this.take('('); const expr = this.expression(); this.take(')'); const end = this.take(';'); out.push({ kind: 'require', expr, span: { start: start.span.start, end: end.span.end } }); }
      else if (start.text === 'if') { const expr = this.expression(); const then = this.statements(depth + 1,loops); const otherwise = this.peek().text === 'else' ? (this.take('else'), this.statements(depth + 1,loops)) : []; out.push({ kind: 'if', expr, then, otherwise, span: { start: start.span.start, end: this.tokens[this.i - 1]!.span.end } }); }
      else if (start.text === 'for') { if (loops >= 2) throw new Error('loop nesting exceeds two'); const variable = this.ident(); this.take('in'); const collection = this.ident().text + '.' + (this.take('.'), this.ident().text); if (collection !== 'tx.inputs' && collection !== 'tx.outputs') throw new Error(`unsupported collection ${collection}`); const then = this.statements(depth + 1,loops + 1); out.push({ kind: 'for', variable: variable.text, collection, then, span: { start: start.span.start, end: this.tokens[this.i - 1]!.span.end } }); }
      else if (/^[A-Za-z_][A-Za-z_0-9]*$/.test(start.text)) { const op = this.take(); if (!['=','+=','-='].includes(op.text)) throw new Error(`unsupported assignment ${op.text}`); const expr = this.expression(); const end = this.take(';'); out.push({ kind:'assign', variable:start.text, assignOp:op.text as '='|'+='|'-=', expr, span:{start:start.span.start,end:end.span.end} }); }
      else throw new Error(`unsupported statement ${start.text} at UTF-8 byte ${start.span.start}`);
      if (out.length > 256) throw new Error('statement budget exceeded');
    }
    this.take('}'); return out;
  }
  private importDecl(start: Token): ImportDecl {
    const target = this.take();
    if (target.text !== 'package' && !/^[A-Za-z_][A-Za-z_0-9]*$/.test(target.text)) throw new Error(`expected dependency alias or package at UTF-8 byte ${target.span.start}`);
    if (target.text !== 'package') symbol(target.text);
    const path: string[] = []; let items: ImportDecl['items']; let pathEnd = target.span.end;
    while (this.peek().text === '::') {
      this.take('::');
      if (this.peek().text === '{') {
        this.take('{'); items = [];
        while (this.peek().text !== '}') {
          const name = this.ident(); symbol(name.text); let local = name;
          if (this.peek().text === 'as') { this.take('as'); local = this.ident(); symbol(local.text); }
          items.push({ name: name.text, local: local.text, span: { start: name.span.start, end: local.span.end } });
          if (this.peek().text !== ',') break; this.take(',');
        }
        this.take('}');
        if (!items.length) throw new Error(`empty import list at UTF-8 byte ${start.span.start}`);
        break;
      }
      const segment = this.ident(); path.push(segment.text); pathEnd = segment.span.end;
    }
    if (!path.length) throw new Error(`import requires a module path at UTF-8 byte ${start.span.start}`);
    let moduleAlias: ImportDecl['moduleAlias'];
    if (!items) {
      if (this.peek().text !== 'as') throw new Error(`import requires ::{names} or 'as alias' at UTF-8 byte ${this.peek().span.start}`);
      this.take('as'); const alias = this.ident(); symbol(alias.text); moduleAlias = { name: alias.text, span: alias.span };
    }
    const end = this.take(';');
    return { target: target.text, targetSpan: target.span, path, pathSpan: { start: target.span.start, end: pathEnd },
      span: { start: start.span.start, end: end.span.end }, ...(items ? { items } : {}), ...(moduleAlias ? { moduleAlias } : {}) };
  }
  parse(requireContract = true): Program {
    const helpers = new Map<string, Helper>(); const contracts = new Map<string, Contract>(); const imports: ImportDecl[] = [];
    while (this.peek().text !== '<eof>') {
      let start = this.take();
      if (start.text === 'import') {
        if (helpers.size || contracts.size) throw new Error(`import must precede declarations at UTF-8 byte ${start.span.start}`);
        imports.push(this.importDecl(start)); continue;
      }
      let visibility: Visibility = 'private';
      if (start.text === 'export' || start.text === 'package') {
        visibility = start.text;
        if (this.peek().text !== 'function') throw new Error(`${start.text} applies only to helper functions at UTF-8 byte ${start.span.start}`);
        const modifier = start; start = this.take(); start = { text: start.text, span: { start: modifier.span.start, end: start.span.end } };
      }
      if (start.text === 'function') {
        const name = this.ident(); this.take('('); const params = this.params(')'); this.take(':'); const result = this.type(); this.take('{'); this.take('return'); const body = this.expression(); this.take(';'); const end = this.take('}');
        symbol(name.text);
        if (helpers.has(name.text)) throw new Error(`duplicate helper ${name.text}`);
        helpers.set(name.text, { name: name.text, params, result, body, span: { start: start.span.start, end: end.span.end }, visibility });
      } else if (start.text === 'contract' || start.text === 'token') {
        const name = this.ident(); symbol(name.text); const params = this.peek().text === '<' ? (this.take('<'), this.params('>')) : [];
        this.take('{'); const methods: Method[] = [];
        while (this.peek().text !== '}') {
          this.take('function'); const method = this.ident(); symbol(method.text); this.take('('); const args = this.params(')'); const body = this.statements();
          if (!body.length || methods.some(x => x.name.toLowerCase() === method.text.toLowerCase())) throw new Error(`empty or duplicate method ${method.text}`);
          if (start.text === 'token' && (args[0]?.type !== 'Amount')) throw new Error(`token method ${method.text} first parameter must be Amount`);
          methods.push({ name: method.text, params: args, body, span: { start: method.span.start, end: this.tokens[this.i - 1]!.span.end } });
          if (methods.length > MAX_METHODS) throw new Error('more than 16 methods');
        }
        const end = this.take('}'); if (!methods.length || contracts.has(name.text)) throw new Error(`empty or duplicate contract ${name.text}`);
        contracts.set(name.text, { name: name.text, kind:start.text as 'contract'|'token', params, methods, span: { start: start.span.start, end: end.span.end } });
      } else throw new Error(`expected contract or helper at UTF-8 byte ${start.span.start}`);
    }
    if (requireContract && !contracts.size) throw new Error('source has no contract');
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
  { kind: 'substitute'; type: ValueType; expr: Expr; env: Env; origin: Span };
type Env = Map<string, EVar>;
type Compiled = { script: Uint8Array; leaf: Uint8Array; map: MethodArtifact['sourceMap']; resources: MethodArtifact['staticResources'] };
const OPCODES = { VERIFY: 0x65, IF: 0x61, ELSE: 0x63, ENDIF: 0x64, ENUMERATE_INPUTS:0x67, ENUMERATE_OUTPUTS:0x68, ENDENUMERATE:0x6a, DROP: 0x79, PICK: 0x7d, ROLL:0x7e,
  SWAP:0x80, BRANCHROOT:0xf2, INPUTINDEX:0xd0, INPUTFLAGS:0xd1, UTXOVALUE:0xd6, UTXOTOKENID:0xd7, OUTPUTVALUE:0xe1, OUTPUTTOKENID:0xe2, OUTPUTREQUIRESBRANCH:0xe8, NUMEQUAL:0xa6, GREATERTHANOREQUAL:0xac,
  EQUAL: 0x91, NOT: 0x9c, ADD: 0x9e, SUB: 0x9f, MUL: 0xa0, BOOLAND: 0xa4, BOOLOR: 0xa5,
  LESSTHAN: 0xa9, GREATERTHAN: 0xaa, SHA256: 0xb8, HASH256: 0xb9, BLAKE3: 0xba, CHECKSIG: 0xbb, CHECKSIGVERIFY: 0xbc, NEGATE: 0x9a } as const;
class Emitter {
  private instructions: Instruction[] = [];
  private length = 0;
  readonly map: MethodArtifact['sourceMap'] = [];
  height: number; maxHeight: number; opcodes = 0; signatureChecks = 0; expansions = 0;
  constructor(readonly args: number) { this.height = args; this.maxHeight = args; }
  private append(data: Uint8Array, op: string, span: Span, origin?: Span, delta = 0, foldable = false): void {
    if (this.length + data.length > MAX_SCRIPT) throw new Error('MAX_SCRIPT_BYTES exceeded');
    if (++this.opcodes > MAX_OPS) throw new Error('opcode budget exceeded');
    this.map.push({ source: span, ...(origin ? { expandedFrom: origin } : {}), byteStart: this.length, byteEnd: this.length + data.length, op });
    this.instructions.push({ wire: data, map: this.map.at(-1)!, delta, foldable }); this.length += data.length; this.height += delta;
    if (this.height < 0) throw new Error('compiler stack underflow');
    this.maxHeight = Math.max(this.maxHeight, this.height);
  }
  push(data: Uint8Array, span: Span, origin?: Span, foldable = false): void {
    if (data.length > 8192) throw new Error('MAX_ELEMENT_BYTES exceeded');
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
  control(name: 'IF'|'ELSE'|'ENDIF', span: Span): void { this.op(name, span, undefined, name === 'IF' ? -1 : 0); }
  finish(optimize: boolean): { script: Uint8Array; map: MethodArtifact['sourceMap']; resources: Pick<MethodArtifact['staticResources'], 'scriptBytes'|'opcodes'|'maxStackItems'> } {
    const entries = optimize ? optimizeInstructions(this.instructions, this.args) : this.instructions;
    const structured = entries.some(entry => ['IF','ELSE','ENDIF','ENUMERATE_INPUTS','ENUMERATE_OUTPUTS','ENDENUMERATE'].includes(entry.map.op));
    const map: MethodArtifact['sourceMap'] = [];
    let offset = 0, height = this.args, maxStackItems = height;
    for (const entry of entries) {
      map.push({ ...entry.map, byteStart: offset, byteEnd: offset + entry.wire.length });
      offset += entry.wire.length;
      if (!structured) { height += entry.delta; if (height < 0) throw new Error('optimized compiler stack underflow'); maxStackItems = Math.max(maxStackItems, height); }
    }
    if (structured) { height = this.height; maxStackItems = this.maxHeight; }
    if (height !== 1) throw new Error('optimized method final stack mismatch');
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
  constructor(private readonly program: Program, private readonly options: CompileOptions) {}
  private contract(name: string): Contract { const c = this.program.contracts.get(name); if (!c) throw new Error(`unknown contract ${name}`); return c; }
  private bound(name: string): Map<string, { bytes: Uint8Array; binding: Binding }> {
    const old = this.bindingMemo.get(name); if (old) return old;
    const c = this.contract(name); const input = this.options.bindings[name] ?? (c.params.length === 0 ? {} : undefined);
    if (!input || Object.keys(input).length !== c.params.length) throw new Error(`constructor arity mismatch for ${name}`);
    const out = new Map<string, { bytes: Uint8Array; binding: Binding }>();
    for (const p of c.params) {
      if (!Object.hasOwn(input,p.name)) throw new Error(`missing constructor binding ${name}.${p.name}`);
      out.set(p.name,literal(input[p.name]!,p.type));
    }
    this.bindingMemo.set(name,out); return out;
  }
  private findMethod(contract: string, method: string): Method { const m = this.contract(contract).methods.find(x => x.name === method); if (!m) throw new Error(`unknown method ${contract}.${method}`); return m; }
  private dependencies(method: Method): string[] {
    const found = new Set<string>();
    const scan = (expr: Expr, target: Set<string>, helpers: string[]): void => {
      if (++this.dependencyVisits > MAX_DEPENDENCY_VISITS) throw new Error('dependency scan visit budget exceeded');
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
              if (helpers.length >= 16) throw new Error('helper dependency depth exceeded');
              const inner = new Set<string>();
              scan(helper.body, inner, [...helpers, helper.name]);
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
        scheduler.register(name, () => this.dependencies(method), () => execute(name, () => { this.method(contract.name, method.name); }), method.span);
      }
      const name = `root:${contract.name}`;
      scheduler.register(name, contract.methods.map(method => `leaf:${contract.name}.${method.name}`), () => execute(name, () => { this.root(contract.name); }), contract.span);
    }
    await scheduler.run(`root:${this.options.contract}`);
    this.enforceScheduledJobs = false;
    return this.compile();
  }
  private root(name: string): Tree {
    const old = this.rootMemo.get(name); if (old) return old;
    if (this.enforceScheduledJobs && this.scheduledJob !== `root:${name}`) throw new Error(`unscheduled root dependency ${name}`);
    if (this.rootActive.has(name)) throw new Error(`contract-root dependency cycle at ${name}`);
    this.rootActive.add(name);
    try {
      this.bound(name);
      const leaves = this.contract(name).methods.map(m => ({ name: m.name, hash: this.method(name,m.name).leaf }));
      const result = tree(leaves); this.rootMemo.set(name,result); return result;
    } finally { this.rootActive.delete(name); }
  }
  private method(contractName: string, methodName: string): Compiled {
    const key = `${contractName}.${methodName}`; const old = this.methodMemo.get(key); if (old) return old;
    if (this.enforceScheduledJobs && this.scheduledJob !== `leaf:${key}`) throw new Error(`unscheduled leaf dependency ${key}`);
    if (this.methodActive.has(key)) throw new Error(`method-leaf dependency cycle at ${key}`);
    this.methodActive.add(key);
    try {
      const method = this.findMethod(contractName,methodName); const c = this.contract(contractName); const bindings = this.bound(contractName);
      const env: Env = new Map();
      for (const p of c.params) env.set(p.name,{ kind: 'constant', type: p.type, data: bindings.get(p.name)!.bytes });
      const stackParams = c.kind === 'token' ? [...method.params.slice(1),method.params[0]!] : method.params;
      for (const [index,p] of stackParams.entries()) {
        if (env.has(p.name)) throw new Error(`method parameter ${p.name} shadows constructor`);
        env.set(p.name,{ kind: 'argument', type: p.type, index });
      }
      const emitter = new Emitter(stackParams.length);
      const helperStack: string[] = [];
      let inferenceVisits = 0;
      const infer = (expr: Expr, scope: Env, active: string[] = []): ValueType => {
        if (++inferenceVisits > MAX_INFERENCE_VISITS) throw new Error('type inference visit budget exceeded');
        if (expr.kind === 'number') { encodedInt(BigInt(expr.value!)); return 'Int'; }
        if (expr.kind === 'bool') return 'Bool';
        if (expr.kind === 'name') {
          if (expr.value === 'this.root') return c.kind === 'token' ? 'TokenId' : 'ContractRootHash';
          if (expr.value === 'this.coin.token_id') { if (c.kind === 'token') throw new Error('mint method has no coin'); return 'TokenId'; }
          if (expr.value === 'this.coin.value') { if (c.kind === 'token') throw new Error('mint method has no coin'); return 'Amount'; }
          const dot = expr.value!.split('.');
          if ((dot.length === 2 && (dot[1] === 'token_id' || dot[1] === 'value' || dot[1] === 'is_spend')) || (dot.length === 3 && dot[1] === 'coin' && ['token_id','value'].includes(dot[2]!))) {
            const v = scope.get(dot[0]!);
            if (!v || v.kind !== 'local' || (v.type !== 'InputIndex' && v.type !== 'OutputIndex')) throw new Error(`unbound record ${dot[0]}`);
            if (dot.length === 3 && v.type !== 'InputIndex') throw new Error('coin field requires input');
            if (dot[1] === 'is_spend') { if (v.type !== 'InputIndex') throw new Error('is_spend requires input'); return 'Bool'; }
            return dot.at(-1) === 'token_id' ? 'TokenId' : 'Amount';
          }
          const v = scope.get(expr.value!); if (!v) throw new Error(`unbound name ${expr.value}`);
          return v.kind === 'substitute' ? infer(v.expr,v.env,active) : v.type;
        }
        if (expr.kind === 'unary') {
          if (expr.value === '-' && expr.right?.kind === 'number') { encodedInt(-BigInt(expr.right.value!)); return 'Int'; }
          const t = infer(expr.right!,scope,active);
          if ((expr.value === '!' && t === 'Bool') || (expr.value === '-' && t === 'Int')) return t;
          throw new Error(`invalid unary ${expr.value} on ${t}`);
        }
        if (expr.kind === 'binary') {
          const a = infer(expr.left!,scope,active), b = infer(expr.right!,scope,active);
          if (a !== b && !(['Int','Amount'].includes(a) && ['Int','Amount'].includes(b))) throw new Error(`binary type mismatch ${a}, ${b}`);
          if (expr.value === '==' || expr.value === '!=') return 'Bool';
          if (['+','-','*'].includes(expr.value!) && ['Int','Amount'].includes(a) && ['Int','Amount'].includes(b)) return a === 'Amount' || b === 'Amount' ? 'Amount' : 'Int';
          if (['<','>','<=','>='].includes(expr.value!) && ['Int','Amount'].includes(a) && ['Int','Amount'].includes(b)) return 'Bool';
          if (['&&','||'].includes(expr.value!) && a === 'Bool') return 'Bool';
          throw new Error(`invalid binary ${expr.value} on ${a}`);
        }
        if (expr.kind !== 'call') throw new Error('unknown expression');
        const name = expr.value!, args = expr.args ?? [];
        if (name === 'leaf_hash') { if (args.length !== 1 || args[0]!.kind !== 'name' || args[0]!.value!.split('.').length !== 2) throw new Error('leaf_hash requires Contract.method'); return 'MethodLeafHash'; }
        if (name === 'contract_root' || name === 'merkle_root') { if (args.length !== 1 || args[0]!.kind !== 'name' || args[0]!.value!.includes('.')) throw new Error(`${name} requires tree name`); return this.contract(args[0]!.value!).kind === 'token' ? 'TokenId' : 'ContractRootHash'; }
        if (name.endsWith('.requires_branch')) { if (args.length !== 1 || infer(args[0]!,scope,active) !== 'ContractRootHash' || scope.get(name.split('.')[0]!)?.type !== 'OutputIndex') throw new Error('requires_branch expects output and contract root'); return 'Bool'; }
        if (name === 'checksig') { if (args.length !== 2 || infer(args[0]!,scope,active) !== 'Signature' || infer(args[1]!,scope,active) !== 'PublicKey') throw new Error('checksig expects Signature, PublicKey'); return 'Bool'; }
        if (['sha256','hash256','blake3'].includes(name)) {
          if (args.length !== 1) throw new Error(`${name} expects one byte value`);
          const t = infer(args[0]!,scope,active);
          if (!['PublicKey','Signature','Bytes32','MethodLeafHash','ContractRootHash'].includes(t) && !t.startsWith('Bytes(')) throw new Error(`${name} expects bytes`);
          return 'Bytes32';
        }
        const helper = this.program.helpers.get(name); if (!helper) throw new Error(`unknown function ${name}`);
        if (helper.params.length !== args.length) throw new Error(`helper ${name} arity mismatch`);
        if (active.includes(name) || active.length >= 16) throw new Error(`recursive helper ${name}`);
        const inner: Env = new Map();
        for (let i = 0; i < args.length; i++) {
          const p = helper.params[i]!, actual = infer(args[i]!,scope,active);
          if (actual !== p.type) throw new Error(`helper ${name}.${p.name} expects ${p.type}, got ${actual}`);
          inner.set(p.name,{ kind:'substitute', type:p.type, expr:args[i]!, env:scope, origin:expr.span });
        }
        const result = infer(helper.body,inner,[...active,name]);
        if (result !== helper.result) throw new Error(`helper ${name} returns ${result}, declared ${helper.result}`);
        return result;
      };
      const expression = (expr: Expr, scope: Env, origin?: Span): ValueType => {
        if (expr.kind === 'number') { emitter.number(BigInt(expr.value!),expr.span,origin); return 'Int'; }
        if (expr.kind === 'bool') { emitter.number(expr.value === 'true' ? 1n : 0n,expr.span,origin); return 'Bool'; }
        if (expr.kind === 'name') {
          if (expr.value === 'this.root') { emitter.op('BRANCHROOT',expr.span,origin,1); return c.kind === 'token' ? 'TokenId' : 'ContractRootHash'; }
          if (expr.value === 'this.coin.token_id' || expr.value === 'this.coin.value') {
            if (c.kind === 'token') throw new Error('mint method has no coin');
            emitter.op('INPUTINDEX',expr.span,origin,1);
            emitter.op(expr.value.endsWith('token_id') ? 'UTXOTOKENID' : 'UTXOVALUE',expr.span,origin);
            return expr.value.endsWith('token_id') ? 'TokenId' : 'Amount';
          }
          const dot = expr.value!.split('.');
          if ((dot.length === 2 && ['token_id','value','is_spend'].includes(dot[1]!)) || (dot.length === 3 && dot[1] === 'coin' && ['token_id','value'].includes(dot[2]!))) {
            const v = scope.get(dot[0]!);
            if (!v || v.kind !== 'local' || (v.type !== 'InputIndex' && v.type !== 'OutputIndex')) throw new Error(`unbound record ${dot[0]}`);
            if (dot.length === 3 && v.type !== 'InputIndex') throw new Error('coin field requires input');
            emitter.number(BigInt(emitter.height - 1 - v.index),expr.span,origin); emitter.op('PICK',expr.span,origin);
            if (dot[1] === 'is_spend') { if (v.type !== 'InputIndex') throw new Error('is_spend requires input'); emitter.op('INPUTFLAGS',expr.span,origin); emitter.number(1n,expr.span,origin); emitter.op('NUMEQUAL',expr.span,origin,-1); return 'Bool'; }
            const field = dot.at(-1)!;
            const op = v.type === 'OutputIndex' ? (field === 'token_id' ? 'OUTPUTTOKENID' : 'OUTPUTVALUE') : (field === 'token_id' ? 'UTXOTOKENID' : 'UTXOVALUE');
            emitter.op(op,expr.span,origin); return field === 'token_id' ? 'TokenId' : 'Amount';
          }
          const v = scope.get(expr.value!); if (!v) throw new Error(`unbound name ${expr.value} at UTF-8 byte ${expr.span.start}`);
          if (v.kind === 'constant') emitter.push(v.data,expr.span,origin);
          else if (v.kind === 'argument' || v.kind === 'local') { emitter.number(BigInt(emitter.height - 1 - v.index),expr.span,origin); emitter.op('PICK',expr.span,origin); }
          else { const actual = expression(v.expr,v.env,v.origin); if (actual !== v.type) throw new Error(`helper substitution expected ${v.type}, got ${actual}`); return actual; }
          return v.type;
        }
        if (expr.kind === 'unary') {
          if (expr.value === '-' && expr.right?.kind === 'number') { emitter.number(-BigInt(expr.right.value!),expr.span,origin); return 'Int'; }
          const t = expression(expr.right!,scope,origin);
          if (expr.value === '!' && t === 'Bool') { emitter.op('NOT',expr.span,origin); return 'Bool'; }
          if (expr.value === '-' && t === 'Int') { emitter.op('NEGATE',expr.span,origin); return 'Int'; }
          throw new Error(`invalid unary ${expr.value} on ${t}`);
        }
        if (expr.kind === 'binary') {
          if (expr.value === '&&' || expr.value === '||') {
            const a = expression(expr.left!,scope,origin); if (a !== 'Bool') throw new Error(`${expr.value} requires Bool`);
            if (expr.value === '||') emitter.op('NOT',expr.span,origin);
            emitter.control('IF',expr.span); const before = emitter.height;
            const b = expression(expr.right!,scope,origin); if (b !== 'Bool') throw new Error(`${expr.value} requires Bool`);
            if (emitter.height !== before + 1) throw new Error('logical branch stack mismatch');
            emitter.control('ELSE',expr.span); emitter.height = before;
            emitter.number(expr.value === '&&' ? 0n : 1n,expr.span,origin);
            emitter.control('ENDIF',expr.span); return 'Bool';
          }
          const a = expression(expr.left!,scope,origin), b = expression(expr.right!,scope,origin);
          if (expr.value === '==' || expr.value === '!=') {
            if (a !== b) throw new Error(`equality type mismatch ${a} and ${b}`);
            emitter.op('EQUAL',expr.span,origin,-1); if (expr.value === '!=') emitter.op('NOT',expr.span,origin); return 'Bool';
          }
          const cases: Record<string,[keyof typeof OPCODES,ValueType]> = { '+':['ADD',a], '-':['SUB',a], '*':['MUL',a], '<':['LESSTHAN','Bool'], '>':['GREATERTHAN','Bool'], '>=':['GREATERTHANOREQUAL','Bool'] };
          const rule = cases[expr.value!]; if (!rule || !['Int','Amount'].includes(a) || !['Int','Amount'].includes(b)) throw new Error(`invalid ${expr.value} operands ${a}, ${b}`);
          emitter.op(rule[0],expr.span,origin,-1); return ['+','-','*'].includes(expr.value!) && (a === 'Amount' || b === 'Amount') ? 'Amount' : rule[1];
        }
        if (expr.kind !== 'call') throw new Error('unknown expression');
        const args = expr.args ?? [];
        const name = expr.value!;
        if (name === 'leaf_hash') {
          if (args.length !== 1 || args[0]!.kind !== 'name') throw new Error('leaf_hash requires Contract.method name');
          const path = args[0]!.value!.split('.'); if (path.length !== 2) throw new Error('leaf_hash requires Contract.method name');
          emitter.push(this.method(path[0]!,path[1]!).leaf,expr.span,origin); return 'MethodLeafHash';
        }
        if (name === 'contract_root' || name === 'merkle_root') {
          if (args.length !== 1 || args[0]!.kind !== 'name' || args[0]!.value!.includes('.')) throw new Error('contract_root requires Contract name');
          const other = this.contract(args[0]!.value!); emitter.push(this.root(other.name).root,expr.span,origin); return other.kind === 'token' ? 'TokenId' : 'ContractRootHash';
        }
        if (name.endsWith('.requires_branch')) {
          const v = scope.get(name.split('.')[0]!); if (!v || v.kind !== 'local' || v.type !== 'OutputIndex' || args.length !== 1) throw new Error('requires_branch requires output index and one root');
          emitter.number(BigInt(emitter.height - 1 - v.index),expr.span,origin); emitter.op('PICK',expr.span,origin);
          const t = expression(args[0]!,scope,origin); if (t !== 'ContractRootHash') throw new Error('requires_branch requires ContractRootHash');
          emitter.op('OUTPUTREQUIRESBRANCH',expr.span,origin,-1); return 'Bool';
        }
        if (name === 'checksig') {
          if (args.length !== 2) throw new Error('checksig needs signature and PublicKey');
          const a = expression(args[0]!,scope,origin), b = expression(args[1]!,scope,origin);
          if (a !== 'Signature' || b !== 'PublicKey') throw new Error('checksig expects Signature, PublicKey');
          emitter.op('CHECKSIG',expr.span,origin,-1); return 'Bool';
        }
        const hashes: Record<string,keyof typeof OPCODES> = { sha256:'SHA256', hash256:'HASH256', blake3:'BLAKE3' };
        if (hashes[name]) {
          if (args.length !== 1) throw new Error(`${name} expects one byte value`);
          const t = expression(args[0]!,scope,origin);
          if (!['PublicKey','Signature','Bytes32','MethodLeafHash','ContractRootHash'].includes(t) && !t.startsWith('Bytes(')) throw new Error(`${name} expects byte value, got ${t}`);
          emitter.op(hashes[name],expr.span,origin); return 'Bytes32';
        }
        const helper = this.program.helpers.get(name); if (!helper) throw new Error(`unknown function ${name}`);
        if (helper.params.length !== args.length) throw new Error(`helper ${name} arity mismatch`);
        if (helperStack.includes(name)) throw new Error(`recursive helper ${name}`);
        if (++emitter.expansions > MAX_EXPANSIONS || helperStack.length >= 16) throw new Error('helper expansion budget exceeded');
        const inner: Env = new Map();
        // Each helper parameter is a hygienically scoped expression thunk. The
        // source argument is checked against the declared parameter type once.
        for (let i = 0; i < args.length; i++) {
          const p = helper.params[i]!;
          const actual = infer(args[i]!,scope,helperStack);
          if (actual !== p.type) throw new Error(`helper ${name}.${p.name} expects ${p.type}, got ${actual}`);
          inner.set(p.name,{ kind: 'substitute', type: p.type, expr: args[i]!, env: scope, origin: expr.span });
        }
        helperStack.push(name);
        try { const result = expression(helper.body,inner,expr.span); if (result !== helper.result) throw new Error(`helper ${name} returns ${result}, declared ${helper.result}`); return result; }
        finally { helperStack.pop(); }
      };
      const statements = (body: Stmt[], nested = false): void => {
        for (const stmt of body) {
          if (stmt.kind === 'for') {
            const name = stmt.variable!;
            if (env.has(name)) throw new Error(`loop variable ${name} shadows binding`);
            const before = emitter.height;
            if (stmt.collection === 'tx.inputs') emitter.op('ENUMERATE_INPUTS',stmt.span,undefined,1);
            else emitter.op('ENUMERATE_OUTPUTS',stmt.span,undefined,1);
            env.set(name,{kind:'local',type:stmt.collection === 'tx.inputs' ? 'InputIndex' : 'OutputIndex',index:before});
            statements(stmt.then!,true);
            if (emitter.height !== before + 1) throw new Error('loop body stack mismatch');
            emitter.op('DROP',stmt.span,undefined,-1);
            emitter.op('ENDENUMERATE',stmt.span);
            env.delete(name); continue;
          }
          if (stmt.kind === 'assign') {
            const name = stmt.variable!, existing = env.get(name);
            if (!existing && (nested || stmt.assignOp !== '=')) throw new Error(`local ${name} must be initialized at method top level`);
            if (existing && (existing.kind !== 'local' || existing.type === 'InputIndex' || existing.type === 'OutputIndex')) throw new Error(`cannot assign ${name}`);
            if (stmt.assignOp !== '=') {
              emitter.number(BigInt(emitter.height - 1 - existing!.index),stmt.span); emitter.op('PICK',stmt.span);
            }
            const t = expression(stmt.expr!,env);
            if (t !== 'Int' && t !== 'Amount') throw new Error('numeric local required');
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
          const t = expression(stmt.expr!,env);
          if (t !== 'Bool') throw new Error(`${stmt.kind} requires Bool, got ${t}`);
          if (stmt.kind === 'require') emitter.op('VERIFY',stmt.span,undefined,-1);
          else {
            emitter.control('IF',stmt.span);
            const before = emitter.height;
            statements(stmt.then!,true);
            if (emitter.height !== before) throw new Error('then stack mismatch');
            emitter.control('ELSE',stmt.span);
            statements(stmt.otherwise!,true);
            if (emitter.height !== before) throw new Error('else stack mismatch');
            emitter.control('ENDIF',stmt.span);
          }
        }
      };
      statements(method.body);
      for (let i = emitter.height - stackParams.length; i > 0; i--) emitter.op('DROP',method.span,undefined,-1);
      for (let i = 0; i < method.params.length; i++) emitter.op('DROP',method.span,undefined,-1);
      emitter.number(1n,method.span);
      if (emitter.height !== 1) throw new Error('compiled method final stack mismatch');
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
}

function singleModule(source: string): Program {
  const program = new Parser(lex(source)).parse();
  if (program.imports.length) throw new Error(`import at UTF-8 byte ${program.imports[0]!.span.start} requires a package build (compilePackage)`);
  return program;
}
export function compileContract(source: string, options: CompileOptions): ContractArtifact {
  if (typeof options?.contract !== 'string' || !options.bindings || typeof options.bindings !== 'object') throw new Error('compile options require contract and bindings');
  return new Compiler(singleModule(source), options).compile();
}
export async function compileContractAsync(source: string, options: CompileOptions, onEvent?: (event: SchedulerEvent) => void): Promise<ContractArtifact> {
  if (typeof options?.contract !== 'string' || !options.bindings || typeof options.bindings !== 'object') throw new Error('compile options require contract and bindings');
  return new Compiler(singleModule(source), options).compileAsync(onEvent);
}
/** @internal Package linker entry: parse one module (declaration-only modules may omit contracts). */
export function parseModuleSource(source: string, requireContract: boolean): Program {
  return new Parser(lex(source)).parse(requireContract);
}
/** @internal Package linker entry: compile an already linked program through the promise scheduler. */
export async function compileLinkedProgramAsync(program: Program, options: CompileOptions, onEvent?: (event: SchedulerEvent) => void): Promise<ContractArtifact> {
  if (typeof options?.contract !== 'string' || !options.bindings || typeof options.bindings !== 'object') throw new Error('compile options require contract and bindings');
  return new Compiler(program, options).compileAsync(onEvent);
}
export async function compileContractWithTrace(source: string, options: CompileOptions): Promise<{ artifact: ContractArtifact; trace: SchedulerEvent[] }> {
  const trace: SchedulerEvent[] = [];
  const artifact = await compileContractAsync(source, options, event => trace.push(event));
  return { artifact, trace };
}
export function methodLeafHash(artifact: ContractArtifact, method: string): { kind: 'MethodLeafHash'; hex: string } {
  const m = artifact.methods.find(x => x.name === method); if (!m) throw new Error(`unknown method ${method}`);
  return { kind: 'MethodLeafHash', hex: m.leaf };
}
export function contractRootHash(artifact: ContractArtifact): { kind: 'ContractRootHash'; hex: string } {
  return { kind: 'ContractRootHash', hex: artifact.policy.root };
}
