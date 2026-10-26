// Lossless JSON for RPC replies.
//
// JSON.parse turns every number into a double, which silently rounds large
// amounts and integers beyond 2^53. parse() keeps integers that fit exactly as
// Number and returns every other number as a Decimal holding the exact source
// text. stringify() writes Decimals back unchanged, so a value can round-trip.

/** An exact decimal number kept as its JSON source text. */
export class Decimal {
  /** @param {string} text a JSON number literal */
  constructor(text) {
    if (!NUMBER_RE.test(text)) throw new TypeError(`not a JSON number: ${text}`);
    this.text = text;
  }
  toString() { return this.text; }
  valueOf() { return Number(this.text); }
  toJSON() { return this.text; }
}

const NUMBER_RE = /^-?(0|[1-9]\d*)(\.\d+)?([eE][+-]?\d+)?$/;

export class JsonSyntaxError extends SyntaxError {}

/**
 * Parse JSON text, keeping non-safe and fractional numbers exact.
 * @param {string} text
 * @returns {any}
 */
export function parse(text) {
  let i = 0;
  const fail = (what) => {
    throw new JsonSyntaxError(`${what} at position ${i}`);
  };
  const ws = () => {
    while (i < text.length) {
      const c = text.charCodeAt(i);
      if (c === 0x20 || c === 0x0a || c === 0x0d || c === 0x09) i++;
      else break;
    }
  };
  const value = (depth) => {
    if (depth > 512) fail('nesting too deep');
    ws();
    const c = text[i];
    if (c === '{') {
      i++;
      const obj = {};
      ws();
      if (text[i] === '}') { i++; return obj; }
      for (;;) {
        ws();
        if (text[i] !== '"') fail('expected string key');
        const key = string();
        ws();
        if (text[i] !== ':') fail('expected ":"');
        i++;
        const v = value(depth + 1);
        Object.defineProperty(obj, key, { value: v, enumerable: true, writable: true, configurable: true });
        ws();
        if (text[i] === ',') { i++; continue; }
        if (text[i] === '}') { i++; return obj; }
        fail('expected "," or "}"');
      }
    }
    if (c === '[') {
      i++;
      const arr = [];
      ws();
      if (text[i] === ']') { i++; return arr; }
      for (;;) {
        arr.push(value(depth + 1));
        ws();
        if (text[i] === ',') { i++; continue; }
        if (text[i] === ']') { i++; return arr; }
        fail('expected "," or "]"');
      }
    }
    if (c === '"') return string();
    if (text.startsWith('true', i)) { i += 4; return true; }
    if (text.startsWith('false', i)) { i += 5; return false; }
    if (text.startsWith('null', i)) { i += 4; return null; }
    const m = /^-?(0|[1-9]\d*)(\.\d+)?([eE][+-]?\d+)?/.exec(text.slice(i, i + 400));
    if (!m) fail('unexpected token');
    i += m[0].length;
    if (!m[2] && !m[3]) {
      const n = Number(m[0]);
      if (Number.isSafeInteger(n)) return n;
    }
    return new Decimal(m[0]);
  };
  const string = () => {
    i++; // opening quote
    let out = '';
    let start = i;
    for (;;) {
      if (i >= text.length) fail('unterminated string');
      const c = text.charCodeAt(i);
      if (c === 0x22) {
        out += text.slice(start, i);
        i++;
        return out;
      }
      if (c < 0x20) fail('control character in string');
      if (c === 0x5c) {
        out += text.slice(start, i);
        const e = text[i + 1];
        const simple = { '"': '"', '\\': '\\', '/': '/', b: '\b', f: '\f', n: '\n', r: '\r', t: '\t' };
        if (e in simple) { out += simple[e]; i += 2; }
        else if (e === 'u') {
          const hex = text.slice(i + 2, i + 6);
          if (!/^[0-9a-fA-F]{4}$/.test(hex)) fail('bad \\u escape');
          out += String.fromCharCode(parseInt(hex, 16));
          i += 6;
        } else fail('bad escape');
        start = i;
        continue;
      }
      i++;
    }
  };
  const v = value(0);
  ws();
  if (i !== text.length) fail('trailing characters');
  return v;
}

/**
 * JSON.stringify that writes Decimal values as bare numbers.
 * @param {any} value
 * @param {number} [indent]
 * @returns {string}
 */
export function stringify(value, indent = 0) {
  const pad = (n) => (indent ? '\n' + ' '.repeat(indent * n) : '');
  const sep = indent ? ': ' : ':';
  const write = (v, level) => {
    if (v instanceof Decimal) return v.text;
    if (v === null || v === undefined) return 'null';
    if (typeof v === 'bigint') return v.toString();
    if (typeof v === 'number') return Number.isFinite(v) ? String(v) : 'null';
    if (typeof v === 'string' || typeof v === 'boolean') return JSON.stringify(v);
    if (Array.isArray(v)) {
      if (v.length === 0) return '[]';
      return '[' + v.map((x) => pad(level + 1) + write(x, level + 1)).join(',') + pad(level) + ']';
    }
    if (typeof v === 'object') {
      const keys = Object.keys(v).filter((k) => v[k] !== undefined);
      if (keys.length === 0) return '{}';
      return '{' + keys.map((k) => pad(level + 1) + JSON.stringify(k) + sep + write(v[k], level + 1)).join(',') + pad(level) + '}';
    }
    return 'null';
  };
  return write(value, 0);
}
