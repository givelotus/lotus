// Lotus V2 "xpiaddr" encoder/decoder (version 0: one 32-byte branch root).
//
//   <hrp> "1" <version symbol> <52 payload symbols> <8 checksum symbols>
//
// The checksum is cashaddr's 40-bit BCH PolyMod over the 61 body symbols; the
// network enters only through the per-hrp constant K. Port of the reference
// xpiaddr_v2.py; decode() raises XpiAddrError with the reference's exact
// reason strings. Only all-lowercase or all-uppercase input is accepted.

export const CHARSET = 'qpzry9x8gf2tvdw0s3jn54khce6mua7l';
const REV = new Map([...CHARSET].map((c, i) => [c, i]));
const GEN = [0x98f2bc8e61n, 0x79b76d99e2n, 0xf33e5fb3c4n, 0xae2eabe2a8n, 0x1e4f43e470n];

export const K = Object.freeze({
  xpi: 0xb70061479en,
  txpi: 0xadda0f1635n,
  rxpi: 0x8172b45d63n,
});

/** Chain name from getblockchaininfo → address hrp. */
export const HRP_FOR_CHAIN = Object.freeze({ main: 'xpi', test: 'txpi', regtest: 'rxpi' });

const VERSION_ROOT = 0;
const BODY_LEN = 61;
const PAYLOAD_LEN = 52;

export class XpiAddrError extends Error {
  /** @param {string} reason */
  constructor(reason) {
    super(reason);
    this.reason = reason;
  }
}

/** @param {number[]} symbols */
export function polymod(symbols) {
  let c = 1n;
  for (const d of symbols) {
    const c0 = c >> 35n;
    c = ((c & 0x07ffffffffn) << 5n) ^ BigInt(d);
    for (let i = 0; i < 5; i++) if ((c0 >> BigInt(i)) & 1n) c ^= GEN[i];
  }
  return c;
}

function rootToSymbols(root) {
  let acc = 0n;
  for (const b of root) acc = (acc << 8n) | BigInt(b);
  acc <<= 4n;
  const out = [];
  for (let i = 0; i < PAYLOAD_LEN; i++) out.push(Number((acc >> BigInt(5 * (51 - i))) & 31n));
  return out;
}

function symbolsToRoot(symbols) {
  let acc = 0n;
  for (const s of symbols) acc = (acc << 5n) | BigInt(s);
  if (acc & 0xfn) throw new XpiAddrError('nonzero padding');
  acc >>= 4n;
  const root = new Uint8Array(32);
  for (let i = 31; i >= 0; i--) { root[i] = Number(acc & 0xffn); acc >>= 8n; }
  return root;
}

/**
 * @param {string} hrp
 * @param {Uint8Array|number[]} root 32 bytes
 * @returns {string} lowercase address
 */
export function encode(hrp, root) {
  if (!Object.hasOwn(K, hrp)) throw new XpiAddrError('unknown prefix');
  if (root.length !== 32) throw new XpiAddrError('root must be 32 bytes');
  const data = [VERSION_ROOT, ...rootToSymbols(root)];
  const mod = polymod([...data, 0, 0, 0, 0, 0, 0, 0, 0]) ^ K[hrp];
  const checksum = [];
  for (let i = 0; i < 8; i++) checksum.push(Number((mod >> BigInt(5 * (7 - i))) & 31n));
  return hrp + '1' + [...data, ...checksum].map((s) => CHARSET[s]).join('');
}

/**
 * Decode an address. Callers trim whitespace and strip URI framing first.
 * @param {string} addr
 * @param {string} [expectedHrp]
 * @returns {{hrp: string, root: Uint8Array}}
 */
export function decode(addr, expectedHrp) {
  if (addr !== addr.toLowerCase() && addr !== addr.toUpperCase()) throw new XpiAddrError('mixed case');
  const a = addr.toLowerCase();
  const sep = a.lastIndexOf('1');
  const hrp = sep < 0 ? '' : a.slice(0, sep);
  const body = sep < 0 ? '' : a.slice(sep + 1);
  if (sep < 0 || !Object.hasOwn(K, hrp)) throw new XpiAddrError('unknown prefix');
  if (expectedHrp !== undefined && hrp !== expectedHrp) throw new XpiAddrError('wrong network');
  if (body.length !== BODY_LEN) throw new XpiAddrError('bad length');
  const symbols = [];
  for (const c of body) {
    const v = REV.get(c);
    if (v === undefined) throw new XpiAddrError('bad character');
    symbols.push(v);
  }
  if (polymod(symbols) !== K[hrp]) throw new XpiAddrError('bad checksum');
  if (symbols[0] !== VERSION_ROOT) throw new XpiAddrError('unknown version');
  return { hrp, root: symbolsToRoot(symbols.slice(1, 1 + PAYLOAD_LEN)) };
}

/** True when the string looks like it is meant to be an xpiaddr (for UI hints). */
export function looksLikeXpi(addr) {
  return /^(r|t)?xpi1/i.test(addr.trim());
}
