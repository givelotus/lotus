/** Bounded symbolic stack rewrites over lowered P03 instructions. */
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

type Cell = { id: string; start: number; removable: boolean };
type State = { stack: Cell[]; facts: Map<string, 0 | 1> };
// New emitted instructions need an explicit symbolic stack model before this
// pass may reason across them. A net stack delta alone is insufficient.
const symbolicOps = new Set([
  'PUSHDATA','IF','ELSE','ENDIF','ENUMERATE_INPUTS','ENUMERATE_OUTPUTS','ENDENUMERATE',
  'PICK','DUP','DROP','VERIFY','SWAP','ROLL','EQUAL','EQUALVERIFY','NUMEQUAL',
  'ADD','SUB','MUL','BOOLAND','BOOLOR','LESSTHAN','GREATERTHAN','GREATERTHANOREQUAL',
  'CHECKSIG','CHECKSIGVERIFY','OUTPUTREQUIRESBRANCH','NOT','NEGATE','SHA256','HASH256',
  'BLAKE3','INPUTFLAGS','UTXOVALUE','UTXOTOKENID','OUTPUTVALUE','OUTPUTTOKENID',
  'BRANCHROOT','INPUTINDEX',
]);
const unknown = (id: string): Cell => ({ id, start: -1, removable: false });
const copyState = (state: State): State => ({ stack: state.stack.map(cell => ({ ...cell })), facts: new Map(state.facts) });
const numericLiteral = (entry: Instruction): bigint | undefined => {
  const bytes = literal(entry);
  return bytes && entry.foldable ? asInt(bytes) : undefined;
};
function matchingEnd(entries: readonly Instruction[], start: number, open: string, close: string): number {
  let depth = 0;
  for (let i = start; i < entries.length; i++) {
    if (entries[i]!.map.op === open || (close === 'ENDENUMERATE' &&
        ['ENUMERATE_INPUTS','ENUMERATE_OUTPUTS'].includes(entries[i]!.map.op))) depth++;
    else if (entries[i]!.map.op === close && --depth === 0) return i;
  }
  return -1;
}
function matchingElse(entries: readonly Instruction[], start: number, end: number): number {
  let depth = 0;
  for (let i = start + 1; i < end; i++) {
    const op = entries[i]!.map.op;
    if (op === 'IF') depth++;
    else if (op === 'ENDIF') depth--;
    else if (op === 'ELSE' && depth === 0) return i;
  }
  throw new Error('IF without ELSE in optimizer');
}

/** Recurse through branches and enumerations; only erase a producer when its
 * entire suffix is a pure stack read. An opaque constructor push has no
 * reusable identity, even when its bytes happen to match another push. */
function symbolicRegion(entries: readonly Instruction[], state: State, budget: { left: number; next: number }): Instruction[] {
  if (--budget.left < 0) throw new Error('symbolic optimizer budget exceeded');
  const fresh = (kind: string): Cell => unknown(`${kind}:${budget.next++}`);
  const out: Instruction[] = [];
  for (let i = 0; i < entries.length; i++) {
    const entry = entries[i]!, op = entry.map.op;
    if (op === 'IF') {
      const end = matchingEnd(entries, i, 'IF', 'ENDIF');
      const middle = matchingElse(entries, i, end);
      const condition = state.stack.pop() ?? fresh('underflow');
      const thenState = copyState(state), elseState = copyState(state);
      thenState.stack = thenState.stack.map(cell => unknown(cell.id));
      elseState.stack = elseState.stack.map(cell => unknown(cell.id));
      // IF itself validates a canonical Boolean before either arm executes.
      thenState.facts.set(condition.id, 1); elseState.facts.set(condition.id, 0);
      const thenEntries = symbolicRegion(entries.slice(i + 1, middle), thenState, budget);
      const elseEntries = symbolicRegion(entries.slice(middle + 1, end), elseState, budget);
      out.push(entry, ...thenEntries, entries[middle]!, ...elseEntries, entries[end]!);
      if (thenState.stack.length !== elseState.stack.length) throw new Error('optimizer branch stack mismatch');
      state.stack = thenState.stack.map((cell, n) =>
        cell.id === elseState.stack[n]!.id ? unknown(cell.id) : fresh('merge'));
      state.facts = new Map([...state.facts].filter(([id, fact]) =>
        thenState.facts.get(id) === fact && elseState.facts.get(id) === fact));
      i = end; continue;
    }
    if (op === 'ENUMERATE_INPUTS' || op === 'ENUMERATE_OUTPUTS') {
      const end = matchingEnd(entries, i, op, 'ENDENUMERATE');
      if (end < 0) { out.push(entry); state.stack = state.stack.map(() => fresh('control')); continue; }
      const bodyState = copyState(state);
      // A local initialized from an argument shares its identity until the
      // body mutates it. Repeated iterations must start with fresh identities
      // for every slot, while repeated reads of one slot within an iteration
      // can still be simplified.
      bodyState.stack = bodyState.stack.map(() => fresh('loopInput'));
      bodyState.facts.clear();
      bodyState.stack.push(fresh('iterator'));
      const body = symbolicRegion(entries.slice(i + 1, end), bodyState, budget);
      out.push(entry, ...body, entries[end]!);
      state.stack = state.stack.map(() => fresh('loopResult'));
      state.facts.clear(); i = end; continue;
    }
    if (op === 'ELSE' || op === 'ENDIF' || op === 'ENDENUMERATE') throw new Error(`unexpected ${op} in optimizer`);
    const top = state.stack.at(-1);
    const canErase = (cell: Cell | undefined): cell is Cell =>
      !!cell && cell.removable && cell.start >= 0 && cell.start < out.length;
    const pureRead = (cell: Cell): boolean => out.slice(cell.start).every(x =>
      ['ZERO','NEGATIVE_ONE','PICK','DUP'].includes(x.map.op) || x.map.op.startsWith('N('));
    if (op === 'PICK') {
      const depth = state.stack.pop();
      const n = out.at(-1) ? numericLiteral(out.at(-1)!) : undefined;
      const source = n !== undefined && n >= 0n && n < BigInt(state.stack.length)
        ? state.stack[state.stack.length - 1 - Number(n)] : undefined;
      const start = depth?.removable && depth.start === out.length - 1 ? depth.start : out.length;
      state.stack.push(source ? { id: source.id, start, removable: !!depth?.removable && depth.start === out.length - 1 } : fresh('pick'));
      out.push(entry); continue;
    }
    if (op === 'DUP') {
      state.stack.push(top ? { id: top.id, start: out.length, removable: true } : fresh('dup'));
      out.push(entry); continue;
    }
    if (op === 'VERIFY' && canErase(top) && pureRead(top) && state.facts.get(top.id) === 1) {
      out.splice(top.start); state.stack.pop(); continue;
    }
    if ((op === 'EQUAL' || op === 'EQUALVERIFY') && state.stack.length >= 2) {
      const right = state.stack.at(-1)!, left = state.stack.at(-2)!;
      if (left.id === right.id && canErase(left) && canErase(right) &&
          left.start < right.start && right.start < out.length &&
          out.slice(left.start, right.start).every(x => ['ZERO','NEGATIVE_ONE','PICK','DUP'].includes(x.map.op) || x.map.op.startsWith('N(')) &&
          out.slice(right.start).every(x => ['ZERO','NEGATIVE_ONE','PICK','DUP'].includes(x.map.op) || x.map.op.startsWith('N('))) {
        const sources = [...out.splice(left.start), entry];
        state.stack.splice(-2, 2);
        if (op === 'EQUAL') {
          const replacement = push(intBytes(1n), sources, true);
          state.stack.push({ id: 'const:1', start: out.length, removable: true });
          state.facts.set('const:1', 1);
          out.push(replacement);
        }
        continue;
      }
    }
    if (op === 'NOT' && canErase(top) && pureRead(top)) {
      const fact = state.facts.get(top.id);
      if (fact !== undefined) {
        const sources = [...out.splice(top.start), entry];
        state.stack.pop();
        const value = 1 - fact as 0 | 1;
        state.stack.push({ id: `const:${value}`, start: out.length, removable: true });
        out.push(push(intBytes(BigInt(value)), sources, true)); continue;
      }
    }
    if (literal(entry)) {
      const n = numericLiteral(entry);
      const id = entry.foldable && n !== undefined ? `const:${n}` : `literal:${budget.next++}`;
      state.stack.push({ id, start: out.length, removable: !!entry.foldable });
      if (n === 0n || n === 1n) state.facts.set(id, Number(n) as 0 | 1);
    } else if (op === 'DROP') state.stack.pop();
    else if (op === 'VERIFY') {
      const verified = state.stack.pop();
      if (verified) state.facts.set(verified.id, 1);
    }
    else if (op === 'SWAP') {
      const a = state.stack.pop() ?? fresh('swap'), b = state.stack.pop() ?? fresh('swap');
      state.stack.push(a,b);
    } else if (op === 'ROLL') {
      const depth = state.stack.pop();
      const n = depth?.id.startsWith('const:') ? Number(depth.id.slice(6)) : -1;
      if (Number.isSafeInteger(n) && n >= 0 && n < state.stack.length)
        state.stack.push(state.stack.splice(state.stack.length - 1 - n, 1)[0]!);
      else state.stack = state.stack.map(() => fresh('roll'));
    } else {
      const binary = ['EQUAL','NUMEQUAL','ADD','SUB','MUL','BOOLAND','BOOLOR','LESSTHAN',
        'GREATERTHAN','GREATERTHANOREQUAL','CHECKSIG','OUTPUTREQUIRESBRANCH'];
      const unary = ['NOT','NEGATE','SHA256','HASH256','BLAKE3','INPUTFLAGS','UTXOVALUE',
        'UTXOTOKENID','OUTPUTVALUE','OUTPUTTOKENID'];
      const sources = binary.includes(op) || ['EQUALVERIFY','CHECKSIGVERIFY'].includes(op) ? 2 : unary.includes(op) ? 1 : 0;
      if (sources || entry.delta === 1) {
        for (let j = 0; j < sources; j++) state.stack.pop();
        if (!['CHECKSIGVERIFY','EQUALVERIFY'].includes(op)) state.stack.push(fresh('result'));
      } else state.stack = state.stack.map(() => fresh('unknownOp'));
    }
    out.push(entry);
  }
  return out;
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
    if (!changed) {
      if (entries.some(entry => !literal(entry) && !symbolicOps.has(entry.map.op))) return entries;
      // Keep the symbolic pass bounded even for deeply nested source programs.
      const budget = { left: Math.min(16384, entries.length * 2 + 1), next: 0 };
      const symbolic = symbolicRegion(entries, {
        stack: Array.from({ length: argumentCount }, (_, n) => unknown(`arg:${n}`)),
        facts: new Map(),
      }, budget);
      if (symbolic.length === entries.length) return entries;
      entries = symbolic;
    }
  }
  throw new Error('optimizer fuel exhausted');
}
