/** Bounded stack-identity rewrites over lowered P03 instructions. */
import type { Span } from './compiler.js';

export type SourceEntry = { source: Span; expandedFrom?: Span; optimizedFrom?: { op: string; source: Span; expandedFrom?: Span }[];
  byteStart: number; byteEnd: number; op: string };
export type Instruction = { wire: Uint8Array; map: SourceEntry; delta: number };

function origin(entry: Instruction): { op: string; source: Span; expandedFrom?: Span }[] {
  return entry.map.optimizedFrom ?? [{ op: entry.map.op, source: entry.map.source,
    ...(entry.map.expandedFrom ? { expandedFrom: entry.map.expandedFrom } : {}) }];
}
function fuse(first: Instruction, second: Instruction, op: string, byte: number): Instruction {
  return { wire: Uint8Array.of(byte), delta: first.delta + second.delta,
    map: { ...second.map, op, optimizedFrom: [...origin(first), ...origin(second)] } };
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
      !entries.some(entry => ['IF','ELSE','ENDIF'].includes(entry.map.op)) &&
      entries.at(-2)?.map.op === 'DROP' && entries.at(-1)?.map.op === 'N(1)') {
    entries = entries.filter((_, index) => index !== pick - 1 && index !== pick && index !== original.length - 2);
  }
  const fuel = original.length + 1;
  for (let pass = 0; pass < fuel; pass++) {
    let changed = false;
    const next: Instruction[] = [];
    for (let i = 0; i < entries.length; i++) {
      const a = entries[i]!, b = entries[i + 1];
      if (b && a.map.op === 'ZERO' && b.map.op === 'PICK') {
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
