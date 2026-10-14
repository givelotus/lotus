/** Bounded, typed P03 contract frontend. No VM or consensus-validation code. */
import { bytes, concat, cs, hex, tagged, unhex, uint, type Span } from './compiler.js';
import { schnorr } from '@noble/curves/secp256k1';

export type ValueType = 'PublicKey' | 'Signature' | 'Bytes32' | `Bytes(${number})` | 'Int' | 'Bool' | 'MethodLeafHash' | 'ContractRootHash';
export type BoundValue = string | boolean | bigint;
type Token = { text: string; span: Span };
type Param = { name: string; type: ValueType; span: Span };
type Expr = { kind: 'name' | 'number' | 'bool' | 'call' | 'binary' | 'unary'; span: Span; value?: string; args?: Expr[]; left?: Expr; right?: Expr };
type Stmt = { kind: 'require' | 'if'; span: Span; expr: Expr; then?: Stmt[]; otherwise?: Stmt[] };
type Helper = { name: string; params: Param[]; result: ValueType; body: Expr; span: Span };
type Method = { name: string; params: Param[]; body: Stmt[]; span: Span };
type Contract = { name: string; params: Param[]; methods: Method[]; span: Span };
type Program = { helpers: Map<string, Helper>; contracts: Map<string, Contract> };
type Binding = { type: ValueType; value: string | boolean };
export type MethodArtifact = { name: string; args: { name: string; type: ValueType }[]; scriptHex: string; leaf: string; proof: string[]; root: string;
  sourceMap: { source: Span; expandedFrom?: Span; byteStart: number; byteEnd: number; op: string }[];
  staticResources: { scriptBytes: number; opcodes: number; maxStackItems: number; helperExpansions: number; dynamicSignatureChecks: number } };
export type ContractArtifact = { schema: 'lotus-v2/contract-artifact/2'; target: 'P01-P02-P03-candidate-2026-10-14'; contract: string;
  constructor: { name: string; type: ValueType }[]; bindings: { name: string; type: ValueType; value: string | boolean }[];
  methods: MethodArtifact[]; policy: { branches: [string]; paths: [[0]]; root: string; treeRecipe: 'sorted-leaves-largest-power-split-v1' } };
export type CompileOptions = { contract: string; bindings: Record<string, Record<string, BoundValue>> };

const MAX_SOURCE = 65536, MAX_SCRIPT = 8192, MAX_OPS = 4096, MAX_EXPANSIONS = 256, MAX_METHODS = 16;
const RESERVED = new Set('as async await break case catch class const continue debugger default delete do else enum export extends false finally for from function if import in instanceof interface let new null of package private protected public return static super switch this throw true try type typeof var void while with yield and def elif except lambda nonlocal not or pass raise global is None self constructor'.split(' '));
function symbol(name: string): void { if (RESERVED.has(name)) throw new Error(`reserved name ${name}`); }
function utf8Offset(source: string, utf16: number): number { return new TextEncoder().encode(source.slice(0, utf16)).length; }
function lex(source: string): Token[] {
  if (new TextEncoder().encode(source).length > MAX_SOURCE) throw new Error('source exceeds 65536 UTF-8 bytes');
  const re = /\s+|\/\/[^\n]*|\/\*[\s\S]*?\*\/|==|!=|&&|\|\||[A-Za-z_][A-Za-z_0-9]*|[0-9]+|[<>{}():;,.!+*\-]/gy;
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
    if (['PublicKey','Signature','Bytes32','Int','Bool','MethodLeafHash','ContractRootHash'].includes(t.text)) return t.text as ValueType;
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
      while (this.peek().text === '.') { this.take('.'); value += '.' + this.ident().text; }
      if (this.peek().text === '(') {
        this.take('('); const args: Expr[] = [];
        if (this.peek().text !== ')') while (true) { args.push(this.expression(0,depth + 1)); if (this.peek().text !== ',') break; this.take(','); }
        const end = this.take(')'); left = { kind: 'call', value, args, span: { start: name.span.start, end: end.span.end } };
      } else left = { kind: 'name', value, span: { start: name.span.start, end: this.tokens[this.i - 1]!.span.end } };
    }
    const precedence: Record<string, number> = { '||': 1, '&&': 2, '==': 3, '!=': 3, '<': 4, '>': 4, '+': 5, '-': 5, '*': 6 };
    while ((precedence[this.peek().text] ?? 0) >= min && precedence[this.peek().text]) {
      const op = this.take(); const right = this.expression(precedence[op.text]! + 1,depth + 1);
      left = { kind: 'binary', value: op.text, left, right, span: { start: left.span.start, end: right.span.end } };
    }
    return left;
  }
  private statements(depth = 0): Stmt[] {
    if (depth > 16) throw new Error('control nesting depth exceeded');
    this.take('{'); const out: Stmt[] = [];
    while (this.peek().text !== '}') {
      const start = this.take();
      if (start.text === 'require') { this.take('('); const expr = this.expression(); this.take(')'); const end = this.take(';'); out.push({ kind: 'require', expr, span: { start: start.span.start, end: end.span.end } }); }
      else if (start.text === 'if') { this.take('('); const expr = this.expression(); this.take(')'); const then = this.statements(depth + 1); this.take('else'); const otherwise = this.statements(depth + 1); out.push({ kind: 'if', expr, then, otherwise, span: { start: start.span.start, end: this.tokens[this.i - 1]!.span.end } }); }
      else throw new Error(`unsupported statement ${start.text} at UTF-8 byte ${start.span.start}`);
      if (out.length > 256) throw new Error('statement budget exceeded');
    }
    this.take('}'); return out;
  }
  parse(): Program {
    const helpers = new Map<string, Helper>(); const contracts = new Map<string, Contract>();
    while (this.peek().text !== '<eof>') {
      const start = this.take();
      if (start.text === 'function') {
        const name = this.ident(); this.take('('); const params = this.params(')'); this.take(':'); const result = this.type(); this.take('{'); this.take('return'); const body = this.expression(); this.take(';'); const end = this.take('}');
        symbol(name.text);
        if (helpers.has(name.text)) throw new Error(`duplicate helper ${name.text}`);
        helpers.set(name.text, { name: name.text, params, result, body, span: { start: start.span.start, end: end.span.end } });
      } else if (start.text === 'contract') {
        const name = this.ident(); symbol(name.text); const params = this.peek().text === '<' ? (this.take('<'), this.params('>')) : [];
        this.take('{'); const methods: Method[] = [];
        while (this.peek().text !== '}') {
          this.take('function'); const method = this.ident(); symbol(method.text); this.take('('); const args = this.params(')'); const body = this.statements();
          if (!body.length || methods.some(x => x.name === method.text)) throw new Error(`empty or duplicate method ${method.text}`);
          methods.push({ name: method.text, params: args, body, span: { start: method.span.start, end: this.tokens[this.i - 1]!.span.end } });
          if (methods.length > MAX_METHODS) throw new Error('more than 16 methods');
        }
        const end = this.take('}'); if (!methods.length || contracts.has(name.text)) throw new Error(`empty or duplicate contract ${name.text}`);
        contracts.set(name.text, { name: name.text, params, methods, span: { start: start.span.start, end: end.span.end } });
      } else throw new Error(`expected contract or helper at UTF-8 byte ${start.span.start}`);
    }
    if (!contracts.size) throw new Error('source has no contract');
    return { helpers, contracts };
  }
}

function encodedInt(value: bigint): Uint8Array {
  if (value < -(1n << 127n) || value >= (1n << 127n)) throw new Error('Int exceeds signed 128-bit range');
  return uint(value < 0n ? (1n << 128n) + value : value, 16);
}
function literal(value: BoundValue, type: ValueType): { bytes: Uint8Array; binding: Binding } {
  if (type === 'Int') {
    const text = typeof value === 'bigint' ? value.toString() : value;
    if (typeof text !== 'string' || !/^(0|-?[1-9][0-9]*)$/.test(text)) throw new Error('Int binding requires canonical decimal string or bigint');
    const n = BigInt(text); return { bytes: encodedInt(n), binding: { type, value: n.toString() } };
  }
  if (type === 'Bool') { if (typeof value !== 'boolean') throw new Error('Bool binding requires boolean'); return { bytes: encodedInt(value ? 1n : 0n), binding: { type, value } }; }
  if (typeof value !== 'string') throw new Error(`${type} binding requires lowercase hex`);
  const x = unhex(value);
  const exact32 = ['PublicKey','Bytes32','MethodLeafHash','ContractRootHash'].includes(type);
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

type EVar = { kind: 'argument'; type: ValueType; index: number } |
  { kind: 'constant'; type: ValueType; data: Uint8Array } |
  { kind: 'substitute'; type: ValueType; expr: Expr; env: Env; origin: Span };
type Env = Map<string, EVar>;
type Compiled = { script: Uint8Array; leaf: Uint8Array; map: MethodArtifact['sourceMap']; resources: MethodArtifact['staticResources'] };
const OPCODES = { VERIFY: 0x65, IF: 0x61, ELSE: 0x63, ENDIF: 0x64, DROP: 0x79, PICK: 0x7d,
  EQUAL: 0x91, NOT: 0x9c, ADD: 0x9e, SUB: 0x9f, MUL: 0xa0, BOOLAND: 0xa4, BOOLOR: 0xa5,
  LESSTHAN: 0xa9, GREATERTHAN: 0xaa, SHA256: 0xb8, HASH256: 0xb9, BLAKE3: 0xba, CHECKSIG: 0xbb, NEGATE: 0x9a } as const;
class Emitter {
  private chunks: Uint8Array[] = [];
  private length = 0;
  readonly map: MethodArtifact['sourceMap'] = [];
  height: number; maxHeight: number; opcodes = 0; signatureChecks = 0; expansions = 0;
  constructor(readonly args: number) { this.height = args; this.maxHeight = args; }
  private append(data: Uint8Array, op: string, span: Span, origin?: Span, delta = 0): void {
    if (this.length + data.length > MAX_SCRIPT) throw new Error('MAX_SCRIPT_BYTES exceeded');
    if (++this.opcodes > MAX_OPS) throw new Error('opcode budget exceeded');
    this.map.push({ source: span, ...(origin ? { expandedFrom: origin } : {}), byteStart: this.length, byteEnd: this.length + data.length, op });
    this.chunks.push(data); this.length += data.length; this.height += delta;
    if (this.height < 0) throw new Error('compiler stack underflow');
    this.maxHeight = Math.max(this.maxHeight, this.height);
  }
  push(data: Uint8Array, span: Span, origin?: Span): void {
    if (data.length > 8192) throw new Error('MAX_ELEMENT_BYTES exceeded');
    const wire = data.length > 0 && data.length <= 75 ? concat(Uint8Array.of(data.length), data) : concat(Uint8Array.of(0x4c), bytes(data));
    this.append(wire, data.length <= 75 && data.length > 0 ? `PUSH_${data.length}` : 'PUSHDATA', span, origin, 1);
  }
  number(n: bigint, span: Span, origin?: Span): void {
    if (n === 0n) this.append(Uint8Array.of(0), 'ZERO', span, origin, 1);
    else if (n === -1n) this.append(Uint8Array.of(0x4d), 'NEGATIVE_ONE', span, origin, 1);
    else if (n >= 1n && n <= 16n) this.append(Uint8Array.of(0x4d + Number(n)), `N(${n})`, span, origin, 1);
    else this.push(encodedInt(n), span, origin);
  }
  op(name: keyof typeof OPCODES, span: Span, origin?: Span, delta = 0): void { this.append(Uint8Array.of(OPCODES[name]), name, span, origin, delta); if (name === 'CHECKSIG') this.signatureChecks++; }
  control(name: 'IF'|'ELSE'|'ENDIF', span: Span): void { this.op(name, span, undefined, name === 'IF' ? -1 : 0); }
  done(): Uint8Array { return concat(...this.chunks); }
  get bytes(): number { return this.length; }
}

class Compiler {
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
  private root(name: string): Tree {
    const old = this.rootMemo.get(name); if (old) return old;
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
    if (this.methodActive.has(key)) throw new Error(`method-leaf dependency cycle at ${key}`);
    this.methodActive.add(key);
    try {
      const method = this.findMethod(contractName,methodName); const c = this.contract(contractName); const bindings = this.bound(contractName);
      const env: Env = new Map();
      for (const p of c.params) env.set(p.name,{ kind: 'constant', type: p.type, data: bindings.get(p.name)!.bytes });
      for (const [index,p] of method.params.entries()) {
        if (env.has(p.name)) throw new Error(`method parameter ${p.name} shadows constructor`);
        env.set(p.name,{ kind: 'argument', type: p.type, index });
      }
      const emitter = new Emitter(method.params.length);
      const helperStack: string[] = [];
      const infer = (expr: Expr, scope: Env, active: string[] = []): ValueType => {
        if (expr.kind === 'number') { encodedInt(BigInt(expr.value!)); return 'Int'; }
        if (expr.kind === 'bool') return 'Bool';
        if (expr.kind === 'name') {
          const v = scope.get(expr.value!); if (!v) throw new Error(`unbound name ${expr.value}`);
          return v.kind === 'substitute' ? infer(v.expr,v.env,active) : v.type;
        }
        if (expr.kind === 'unary') {
          const t = infer(expr.right!,scope,active);
          if ((expr.value === '!' && t === 'Bool') || (expr.value === '-' && t === 'Int')) return t;
          throw new Error(`invalid unary ${expr.value} on ${t}`);
        }
        if (expr.kind === 'binary') {
          const a = infer(expr.left!,scope,active), b = infer(expr.right!,scope,active);
          if (a !== b) throw new Error(`binary type mismatch ${a}, ${b}`);
          if (expr.value === '==' || expr.value === '!=') return 'Bool';
          if (['+','-','*'].includes(expr.value!) && a === 'Int') return 'Int';
          if (['<','>'].includes(expr.value!) && a === 'Int') return 'Bool';
          if (['&&','||'].includes(expr.value!) && a === 'Bool') return 'Bool';
          throw new Error(`invalid binary ${expr.value} on ${a}`);
        }
        if (expr.kind !== 'call') throw new Error('unknown expression');
        const name = expr.value!, args = expr.args ?? [];
        if (name === 'leaf_hash') { if (args.length !== 1 || args[0]!.kind !== 'name' || args[0]!.value!.split('.').length !== 2) throw new Error('leaf_hash requires Contract.method'); return 'MethodLeafHash'; }
        if (name === 'contract_root') { if (args.length !== 1 || args[0]!.kind !== 'name' || args[0]!.value!.includes('.')) throw new Error('contract_root requires Contract'); return 'ContractRootHash'; }
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
          const v = scope.get(expr.value!); if (!v) throw new Error(`unbound name ${expr.value} at UTF-8 byte ${expr.span.start}`);
          if (v.kind === 'constant') emitter.push(v.data,expr.span,origin);
          else if (v.kind === 'argument') { emitter.number(BigInt(emitter.height - 1 - v.index),expr.span,origin); emitter.op('PICK',expr.span,origin); }
          else { const actual = expression(v.expr,v.env,v.origin); if (actual !== v.type) throw new Error(`helper substitution expected ${v.type}, got ${actual}`); return actual; }
          return v.type;
        }
        if (expr.kind === 'unary') {
          const t = expression(expr.right!,scope,origin);
          if (expr.value === '!' && t === 'Bool') { emitter.op('NOT',expr.span,origin); return 'Bool'; }
          if (expr.value === '-' && t === 'Int') { emitter.op('NEGATE',expr.span,origin); return 'Int'; }
          throw new Error(`invalid unary ${expr.value} on ${t}`);
        }
        if (expr.kind === 'binary') {
          const a = expression(expr.left!,scope,origin), b = expression(expr.right!,scope,origin);
          if (expr.value === '==' || expr.value === '!=') {
            if (a !== b) throw new Error(`equality type mismatch ${a} and ${b}`);
            emitter.op('EQUAL',expr.span,origin,-1); if (expr.value === '!=') emitter.op('NOT',expr.span,origin); return 'Bool';
          }
          const cases: Record<string,[ValueType,keyof typeof OPCODES,ValueType]> = { '+':['Int','ADD','Int'], '-':['Int','SUB','Int'], '*':['Int','MUL','Int'], '<':['Int','LESSTHAN','Bool'], '>':['Int','GREATERTHAN','Bool'], '&&':['Bool','BOOLAND','Bool'], '||':['Bool','BOOLOR','Bool'] };
          const rule = cases[expr.value!]; if (!rule || a !== rule[0] || b !== rule[0]) throw new Error(`invalid ${expr.value} operands ${a}, ${b}`);
          emitter.op(rule[1],expr.span,origin,-1); return rule[2];
        }
        if (expr.kind !== 'call') throw new Error('unknown expression');
        const args = expr.args ?? [];
        const name = expr.value!;
        if (name === 'leaf_hash') {
          if (args.length !== 1 || args[0]!.kind !== 'name') throw new Error('leaf_hash requires Contract.method name');
          const path = args[0]!.value!.split('.'); if (path.length !== 2) throw new Error('leaf_hash requires Contract.method name');
          emitter.push(this.method(path[0]!,path[1]!).leaf,expr.span,origin); return 'MethodLeafHash';
        }
        if (name === 'contract_root') {
          if (args.length !== 1 || args[0]!.kind !== 'name' || args[0]!.value!.includes('.')) throw new Error('contract_root requires Contract name');
          emitter.push(this.root(args[0]!.value!).root,expr.span,origin); return 'ContractRootHash';
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
      const statements = (body: Stmt[]): void => {
        if (!body.length) throw new Error('empty authorization block');
        for (const stmt of body) {
          const t = expression(stmt.expr,env);
          if (t !== 'Bool') throw new Error(`${stmt.kind} requires Bool, got ${t}`);
          if (stmt.kind === 'require') emitter.op('VERIFY',stmt.span,undefined,-1);
          else {
            emitter.control('IF',stmt.span);
            const before = emitter.height;
            statements(stmt.then!);
            if (emitter.height !== before) throw new Error('then stack mismatch');
            emitter.control('ELSE',stmt.span);
            statements(stmt.otherwise!);
            if (emitter.height !== before) throw new Error('else stack mismatch');
            emitter.control('ENDIF',stmt.span);
          }
        }
      };
      statements(method.body);
      for (let i = 0; i < method.params.length; i++) emitter.op('DROP',method.span,undefined,-1);
      emitter.number(1n,method.span);
      if (emitter.height !== 1) throw new Error('compiled method final stack mismatch');
      const script = emitter.done(); const compiled = { script, leaf: leafHash(script), map: emitter.map,
        resources: { scriptBytes: emitter.bytes, opcodes: emitter.opcodes, maxStackItems: emitter.maxHeight,
          helperExpansions: emitter.expansions, dynamicSignatureChecks: emitter.signatureChecks } };
      this.methodMemo.set(key,compiled); return compiled;
    } finally { this.methodActive.delete(key); }
  }
  compile(): ContractArtifact {
    const c = this.contract(this.options.contract); const root = this.root(c.name); const bound = this.bound(c.name);
    const methods: MethodArtifact[] = c.methods.map(m => {
      const compiled = this.method(c.name,m.name);
      return { name: m.name, args: m.params.map(p => ({ name:p.name,type:p.type })), scriptHex: hex(compiled.script), leaf: hex(compiled.leaf),
        proof: root.proofs.get(m.name)!.map(hex), root: hex(root.root), sourceMap: compiled.map, staticResources: compiled.resources };
    });
    return { schema: 'lotus-v2/contract-artifact/2', target: 'P01-P02-P03-candidate-2026-10-14', contract: c.name,
      constructor: c.params.map(p => ({ name:p.name,type:p.type })), bindings: c.params.map(p => ({ name:p.name,...bound.get(p.name)!.binding })),
      methods, policy: { branches: [hex(root.root)], paths: [[0]], root: hex(root.root), treeRecipe: 'sorted-leaves-largest-power-split-v1' } };
  }
}

export function compileContract(source: string, options: CompileOptions): ContractArtifact {
  if (typeof options?.contract !== 'string' || !options.bindings || typeof options.bindings !== 'object') throw new Error('compile options require contract and bindings');
  return new Compiler(new Parser(lex(source)).parse(), options).compile();
}
export function methodLeafHash(artifact: ContractArtifact, method: string): { kind: 'MethodLeafHash'; hex: string } {
  const m = artifact.methods.find(x => x.name === method); if (!m) throw new Error(`unknown method ${method}`);
  return { kind: 'MethodLeafHash', hex: m.leaf };
}
export function contractRootHash(artifact: ContractArtifact): { kind: 'ContractRootHash'; hex: string } {
  return { kind: 'ContractRootHash', hex: artifact.policy.root };
}
