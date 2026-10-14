import { blake3 } from '@noble/hashes/blake3';
import { schnorr } from '@noble/curves/secp256k1';
import { assertPortableName } from './names.js';

export type Span = { start: number; end: number };
type Token = { text: string; span: Span };
export type PaymentAst = { kind: 'Payment'; name: string; ownerName: string; signatureName: string; span: Span; ownerSpan: Span; checkSpan: Span };
export type PaymentIr = { kind: 'checksig'; signature: 'Signature'; publicKey: 'PublicKey'; stackBefore: ['Signature']; stackAfter: ['Boolean']; span: Span };
export type PaymentArtifact = {
  schema: 'lotus-v2/payment-artifact/1'; target: 'P01-P02-P03-candidate-2026-10-14';
  contract: string; constructor: { name: string; type: 'PublicKey'; bytes: 32 }[];
  methods: { name: 'spend'; args: { name: string; type: 'Signature'; bytes: [64, 64] }[]; path: [0] }[];
  scriptHex: string; policy: { branches: [string]; paths: [[0]]; leaf: string };
  sourceMap: { source: Span; byteStart: number; byteEnd: number; op: string }[];
  staticResources: { scriptBytes: number; opcodes: 2; maxStackItems: 2; dynamicSignatureCheck: true };
};

export function hex(bytes: Uint8Array): string { return Buffer.from(bytes).toString('hex'); }
export function unhex(value: string, length?: number): Uint8Array {
  if (!/^(?:[0-9a-f]{2})*$/.test(value) || (length !== undefined && value.length !== length * 2)) throw new Error(`expected lowercase hex${length === undefined ? '' : ` of ${length} bytes`}`);
  return Uint8Array.from(Buffer.from(value, 'hex'));
}
export function concat(...parts: Uint8Array[]): Uint8Array { return Uint8Array.from(Buffer.concat(parts)); }
export function cs(n: number): Uint8Array {
  if (!Number.isSafeInteger(n) || n < 0) throw new Error('invalid CompactSize');
  if (n < 253) return Uint8Array.of(n);
  if (n <= 0xffff) return Uint8Array.of(253, n & 255, n >> 8);
  if (n <= 0xffffffff) return concat(Uint8Array.of(254), uint(BigInt(n), 4));
  return concat(Uint8Array.of(255), uint(BigInt(n), 8));
}
export function uint(n: bigint, bytes: number): Uint8Array {
  if (typeof n !== 'bigint' || n < 0n || n >= (1n << BigInt(bytes * 8))) throw new Error(`u${bytes * 8} range`);
  const result = new Uint8Array(bytes);
  for (let i = 0; i < bytes; i++) { result[i] = Number(n & 255n); n >>= 8n; }
  return result;
}
export function bytes(x: Uint8Array): Uint8Array { return concat(cs(x.length), x); }
export function tagged(name: string, payload: Uint8Array): Uint8Array { return blake3(concat(new TextEncoder().encode(`Lotus/v2/${name}\0`), payload)); }

function tokenize(source: string): Token[] {
  const out: Token[] = [];
  const re = /\s+|\/\/[^\n]*|\/\*[\s\S]*?\*\/|[A-Za-z_][A-Za-z_0-9]*|[<>{}():;,]/gy;
  let i = 0;
  while (i < source.length) {
    re.lastIndex = i; const m = re.exec(source);
    if (!m) throw new Error(`unsupported character at offset ${i}`);
    if (!/^\s|^\//.test(m[0])) out.push({ text: m[0], span: { start: i, end: re.lastIndex } });
    i = re.lastIndex;
  }
  return out;
}
export function parsePayment(source: string): PaymentAst {
  const t = tokenize(source); let i = 0;
  function take(expected?: string): Token {
    const x = t[i++]; if (!x || (expected !== undefined && x.text !== expected)) throw new Error(`expected ${expected ?? 'identifier'} at offset ${x?.span.start ?? source.length}`);
    return x;
  }
  function ident(): Token { const x = take(); if (!/^[A-Za-z_][A-Za-z_0-9]*$/.test(x.text)) throw new Error(`expected identifier at offset ${x.span.start}`); return x; }
  const start = take('contract').span.start; const name = ident(); take('<'); const owner = ident(); take(':'); take('PublicKey'); take('>'); take('{');
  take('function'); take('spend'); take('('); const signature = ident(); take(':'); take('Signature'); take(')'); take('{');
  const checkStart = take('require').span.start; take('('); take('checksig'); take('('); const sigUse = ident(); take(','); const ownerUse = ident(); take(')'); take(')'); take(';');
  take('}'); const end = take('}').span.end;
  if (i !== t.length) throw new Error(`unsupported syntax at offset ${t[i]!.span.start}`);
  if (sigUse.text !== signature.text || ownerUse.text !== owner.text) throw new Error(`typed name mismatch at offset ${sigUse.span.start}`);
  for (const value of [name.text,owner.text,signature.text]) assertPortableName(value);
  if (owner.text === signature.text) throw new Error('method parameter shadows constructor');
  return { kind: 'Payment', name: name.text, ownerName: owner.text, signatureName: signature.text, span: { start, end }, ownerSpan: ownerUse.span, checkSpan: { start: checkStart, end: t[i - 3]!.span.end } };
}
export function lowerPayment(ast: PaymentAst): PaymentIr { return { kind: 'checksig', signature: 'Signature', publicKey: 'PublicKey', stackBefore: ['Signature'], stackAfter: ['Boolean'], span: ast.checkSpan }; }
export function compilePayment(source: string, ownerHex: string): PaymentArtifact {
  const ast = parsePayment(source); lowerPayment(ast); const owner = unhex(ownerHex, 32);
  try { schnorr.utils.lift_x(BigInt(`0x${ownerHex}`)); } catch { throw new Error('PublicKey is not a BIP340 x-only curve point'); }
  // P03 PUSH_32 (0x20), then CHECKSIG (0xbb). P02 one-leaf branch root.
  const script = concat(Uint8Array.of(0x20), owner, Uint8Array.of(0xbb));
  const leaf = tagged('branch', concat(Uint8Array.of(0), bytes(script)));
  return {
    schema: 'lotus-v2/payment-artifact/1', target: 'P01-P02-P03-candidate-2026-10-14', contract: ast.name,
    constructor: [{ name: ast.ownerName, type: 'PublicKey', bytes: 32 }],
    methods: [{ name: 'spend', args: [{ name: ast.signatureName, type: 'Signature', bytes: [64, 64] }], path: [0] }],
    scriptHex: hex(script), policy: { branches: [hex(leaf)], paths: [[0]], leaf: hex(leaf) },
    sourceMap: [ { source: ast.ownerSpan, byteStart: 0, byteEnd: 33, op: 'PUSH_32' }, { source: ast.checkSpan, byteStart: 33, byteEnd: 34, op: 'CHECKSIG' } ],
    staticResources: { scriptBytes: 34, opcodes: 2, maxStackItems: 2, dynamicSignatureCheck: true },
  };
}

export const PAYMENT_SOURCE = `contract Payment<owner: PublicKey> { function spend(signature: Signature) { require(checksig(signature, owner)); } }`;
