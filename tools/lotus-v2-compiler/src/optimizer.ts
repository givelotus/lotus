/** Bounded stack-identity rewrites over lowered P03 instructions. */
import type { Span } from './compiler.js';
import { sha256 } from '@noble/hashes/sha256';
import { blake3 } from '@noble/hashes/blake3';

export type SourceEntry = { source: Span; expandedFrom?: Span; optimizedFrom?: { op: string; source: Span; expandedFrom?: Span }[];
  byteStart: number; byteEnd: number; op: string };
export type Instruction = { wire: Uint8Array; map: SourceEntry; delta: number; foldable?: boolean };

function origin(entry: Instruction): { op: string; source: Span; expandedFrom?: Span }[] {
  return entry.map.optimizedFrom ?? [{ op: entry.map.op, source: entry.map.source,
    ...(entry.map.expandedFrom ? { expandedFrom: entry.map.expandedFrom } : {}) }];
}
function fuse(first: Instruction, second: Instruction, op: string, byte: number): Instruction {
  return { wire: Uint8Array.of(byte), delta: first.delta + second.delta,
    map: { ...second.map, op, optimizedFrom: [...origin(first), ...origin(second)] } };
}
const INT_MIN = -(1n << 127n), INT_MAX = (1n << 127n) - 1n;
function intBytes(value: bigint): Uint8Array {
  const out = new Uint8Array(16); let bits = value < 0n ? value + (1n << 128n) : value;
  for (let i = 0; i < 16; i++) { out[i] = Number(bits & 255n); bits >>= 8n; }
  return out;
}
function asInt(raw: Uint8Array): bigint | undefined {
  if (raw.length !== 16) return undefined;
  let value = 0n;
  for (let i = 15; i >= 0; i--) value = (value << 8n) | BigInt(raw[i]!);
  return raw[15]! & 0x80 ? value - (1n << 128n) : value;
}
function literal(entry: Instruction): Uint8Array | undefined {
  const op = entry.wire[0]!;
  if (entry.map.op === 'ZERO') return intBytes(0n);
  if (entry.map.op === 'NEGATIVE_ONE') return intBytes(-1n);
  if (entry.map.op.startsWith('N(') && op >= 0x4e && op <= 0x5d) return intBytes(BigInt(op - 0x4d));
  if (entry.map.op.startsWith('PUSH_') && op >= 1 && op <= 75 && entry.wire.length === op + 1) return entry.wire.slice(1);
  return undefined;
}
function push(raw: Uint8Array, source: readonly Instruction[], numeric: boolean): Instruction {
  const value = numeric ? asInt(raw) : undefined;
  let wire: Uint8Array, op: string;
  if (value === 0n) { wire = Uint8Array.of(0); op = 'ZERO'; }
  else if (value === -1n) { wire = Uint8Array.of(0x4d); op = 'NEGATIVE_ONE'; }
  else if (value !== undefined && value >= 1n && value <= 16n) {
    wire = Uint8Array.of(0x4d + Number(value)); op = `N(${value})`;
  } else {
    wire = Uint8Array.of(raw.length, ...raw); op = `PUSH_${raw.length}`;
  }
  const last = source.at(-1)!;
  return { wire, delta: 1, foldable: source.slice(0, -1).every(entry => entry.foldable),
    map: { ...last.map, op, optimizedFrom: source.flatMap(origin) } };
}
function sameBytes(a: Uint8Array, b: Uint8Array): boolean {
  return a.length === b.length && a.every((byte, index) => byte === b[index]);
}
function foldUnary(a: Instruction, b: Instruction): Instruction | undefined {
  const x = literal(a); if (!x) return undefined;
  const n = asInt(x);
  if (b.map.op === 'SHA256') return push(sha256(x), [a,b], false);
  if (b.map.op === 'HASH256') return push(sha256(sha256(x)), [a,b], false);
  if (b.map.op === 'BLAKE3') return push(blake3(x), [a,b], false);
  if (!a.foldable) return undefined;
  if (b.map.op === 'NEGATE' && n !== undefined && n !== INT_MIN) return push(intBytes(-n), [a,b], true);
  if (b.map.op === 'NOT' && (n === 0n || n === 1n)) return push(intBytes(1n - n), [a,b], true);
  return undefined;
}
function foldBinary(a: Instruction, b: Instruction, c: Instruction): Instruction | undefined {
  const x = literal(a), y = literal(b); if (!x || !y || !a.foldable || !b.foldable) return undefined;
  if (c.map.op === 'EQUAL') return push(intBytes(sameBytes(x,y) ? 1n : 0n), [a,b,c], true);
  const left = asInt(x), right = asInt(y);
  if (left === undefined || right === undefined) return undefined;
  let result: bigint | undefined;
  switch (c.map.op) {
    case 'ADD': result = left + right; break;
    case 'SUB': result = left - right; break;
    case 'MUL': result = left * right; break;
    case 'LESSTHAN': result = left < right ? 1n : 0n; break;
    case 'GREATERTHAN': result = left > right ? 1n : 0n; break;
    case 'BOOLAND': if ((left === 0n || left === 1n) && (right === 0n || right === 1n)) result = left & right; break;
    case 'BOOLOR': if ((left === 0n || left === 1n) && (right === 0n || right === 1n)) result = left | right; break;
  }
  if (result === undefined || result < INT_MIN || result > INT_MAX) return undefined;
  return push(intBytes(result), [a,b,c], true);
}
function verifiedLiteral(a: Instruction, b: Instruction | undefined, c: Instruction | undefined): 2 | 3 | undefined {
  const x = literal(a);
  if (!x || !a.foldable) return undefined;
  if (b?.map.op === 'VERIFY' && asInt(x) === 1n) return 2;
  if (!b || !c || c.map.op !== 'EQUALVERIFY' || !b.foldable) return undefined;
  const y = literal(b);
  return y && sameBytes(x,y) ? 3 : undefined;
}

/**
 * Each rewrite strictly reduces opcode count, so the fuel bound is also an
 * assertion against an accidentally nonterminating future rule. ZERO/PICK is
 * the symbolic stack identity `S x -> S x 0 -> S x x`; DUP has that exact
 * effect and the same error behavior for a valid x. No operation with a
 * potential runtime error is deleted or reordered.
 */
export function optimizeInstructions(original: readonly Instruction[], argumentCount: number): Instruction[] {
  let entries = [...original];
  // The compiler preserves original arguments below expression temporaries.
  // One depth-zero read in a straight-line single-argument method can consume
  // its original argument; the trailing compiler-inserted DROP then vanishes.
  const picks = entries.flatMap((entry, index) => entry.map.op === 'PICK' ? [index] : []);
  const pick = picks[0];
  if (argumentCount === 1 && picks.length === 1 && pick !== undefined && pick > 0 &&
      entries[pick - 1]!.map.op === 'ZERO' &&
      entries.every(entry => entry.map.op.startsWith('PUSH_') || entry.map.op.startsWith('N(') ||
        ['PUSHDATA','ZERO','NEGATIVE_ONE','PICK','DROP','VERIFY','CHECKSIG','SHA256','HASH256','BLAKE3',
          'EQUAL','NOT','NEGATE','ADD','SUB','MUL','BOOLAND','BOOLOR','LESSTHAN','GREATERTHAN'].includes(entry.map.op)) &&
      entries.at(-2)?.map.op === 'DROP' && entries.at(-1)?.map.op === 'N(1)') {
    entries = entries.filter((_, index) => index !== pick - 1 && index !== pick && index !== original.length - 2);
  }
  const fuel = original.length + 1;
  for (let pass = 0; pass < fuel; pass++) {
    let changed = false;
    const next: Instruction[] = [];
    for (let i = 0; i < entries.length; i++) {
      const a = entries[i]!, b = entries[i + 1];
      const c = entries[i + 2];
      const verified = verifiedLiteral(a,b,c);
      const foldedBinary = b && c ? foldBinary(a,b,c) : undefined;
      const foldedUnary = b ? foldUnary(a,b) : undefined;
      if (verified) { i += verified - 1; changed = true; }
      else if (foldedBinary) { next.push(foldedBinary); i += 2; changed = true; }
      else if (foldedUnary) { next.push(foldedUnary); i++; changed = true; }
      else if (b && a.map.op === 'ZERO' && b.map.op === 'PICK') {
        next.push(fuse(a, b, 'DUP', 0x7a)); i++; changed = true;
      } else if (b && a.map.op === 'CHECKSIG' && b.map.op === 'VERIFY') {
        next.push(fuse(a, b, 'CHECKSIGVERIFY', 0xbc)); i++; changed = true;
      } else if (b && a.map.op === 'EQUAL' && b.map.op === 'VERIFY') {
        next.push(fuse(a, b, 'EQUALVERIFY', 0x92)); i++; changed = true;
      } else next.push(a);
    }
    entries = next;
    if (!changed) return entries;
  }
  throw new Error('optimizer fuel exhausted');
}
