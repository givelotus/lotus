// Console command-line parser, modelled on bitcoin-qt's RPCParseCommandLine.
//
//   getblockhash 0
//   getblock(getbestblockhash())
//   getblock(getblockhash(0), 1)[tx][0]
//   sendmany "" '{"addr": "10.00"}'
//
// Arguments are separated by whitespace at the top level, and by commas inside
// parentheses. A call written as name(...) can appear as an argument; its
// result is passed as the argument value. [key] after a call selects an array
// index or object key from its result.
//
// Argument rule: a double-quoted argument is always a string. Any other
// argument (bare or single-quoted) is parsed as JSON when it is valid JSON
// (numbers, true/false/null, objects, arrays); otherwise it is a string.

import { parse as parseJson } from './json.js';

export class ConsoleSyntaxError extends Error {}

/**
 * @typedef {{type: 'lit', text: string, quote: string|null}} Lit
 * @typedef {{type: 'call', method: string, args: Array<Lit|Call>, path: string[]}} Call
 */

/**
 * @param {string} line
 * @returns {Call|null} null for an empty line
 */
export function parseCommandLine(line) {
  let i = 0;
  const s = line;
  const fail = (msg) => { throw new ConsoleSyntaxError(`${msg} (at column ${i + 1})`); };
  const skipWs = () => { while (i < s.length && /\s/.test(s[i])) i++; };
  const ident = () => {
    const m = /^[A-Za-z_][A-Za-z0-9_-]*/.exec(s.slice(i));
    if (!m) fail('expected a command name');
    i += m[0].length;
    return m[0];
  };
  const quoted = () => {
    const q = s[i++];
    let out = '';
    for (;;) {
      if (i >= s.length) fail('unterminated quote');
      const c = s[i];
      if (c === q) { i++; return { type: 'lit', text: out, quote: q }; }
      if (c === '\\' && q === '"' && i + 1 < s.length) { out += s[i + 1]; i += 2; continue; }
      out += c;
      i++;
    }
  };
  const bare = (stops) => {
    const start = i;
    let depth = 0;
    while (i < s.length) {
      const c = s[i];
      if (depth === 0 && stops.includes(c)) break;
      if (depth === 0 && /\s/.test(c) && stops.includes(' ')) break;
      if (c === '{' || c === '[') depth++;
      if (c === '}' || c === ']') depth--;
      if (c === '"') { // keep quoted JSON strings inside bare tokens intact
        i++;
        while (i < s.length && s[i] !== '"') i += s[i] === '\\' ? 2 : 1;
      }
      i++;
    }
    const text = s.slice(start, i).trim();
    if (text === '') fail('expected an argument');
    return { type: 'lit', text, quote: null };
  };
  const pathSuffix = () => {
    const path = [];
    while (s[i] === '[') {
      const end = s.indexOf(']', i);
      if (end < 0) fail('unterminated [');
      path.push(s.slice(i + 1, end).trim());
      i = end + 1;
    }
    return path;
  };
  const isNestedCall = () => /^[A-Za-z_][A-Za-z0-9_-]*\(/.test(s.slice(i));
  const argument = (stops) => {
    if (s[i] === '"' || s[i] === "'") return quoted();
    if (isNestedCall()) return call(true);
    return bare(stops);
  };
  const call = (nested) => {
    const method = ident();
    const args = [];
    if (s[i] === '(') {
      i++;
      skipWs();
      if (s[i] === ')') i++;
      else {
        for (;;) {
          skipWs();
          args.push(argument([',', ')']));
          skipWs();
          if (s[i] === ',') { i++; continue; }
          if (s[i] === ')') { i++; break; }
          fail('expected "," or ")"');
        }
      }
      return { type: 'call', method, args, path: pathSuffix() };
    }
    if (nested) fail('expected "("');
    for (;;) {
      skipWs();
      if (i >= s.length) break;
      args.push(argument([' ']));
    }
    return { type: 'call', method, args, path: [] };
  };

  skipWs();
  if (i >= s.length || s[i] === '#') return null;
  const result = call(false);
  skipWs();
  if (i < s.length) fail('unexpected text after command');
  return result;
}

/** Convert a literal argument to its RPC parameter value. */
export function literalValue(lit) {
  if (lit.quote === '"') return lit.text;
  try {
    return parseJson(lit.text);
  } catch {
    return lit.text;
  }
}

/**
 * Evaluate a parsed command, nested calls first.
 * @param {Call} node
 * @param {(method: string, params: any[]) => Promise<any>} callRpc
 */
export async function evaluate(node, callRpc) {
  const params = [];
  for (const a of node.args) params.push(a.type === 'call' ? await evaluate(a, callRpc) : literalValue(a));
  let result = await callRpc(node.method, params);
  for (const key of node.path) {
    if (result === null || typeof result !== 'object') throw new ConsoleSyntaxError(`cannot index ${typeof result} with [${key}]`);
    if (Array.isArray(result)) {
      if (!/^\d+$/.test(key) || Number(key) >= result.length) throw new ConsoleSyntaxError(`index [${key}] out of range`);
      result = result[Number(key)];
    } else {
      if (!Object.hasOwn(result, key)) throw new ConsoleSyntaxError(`no key [${key}] in result`);
      result = result[key];
    }
  }
  return result;
}

/** Commands bitcoin-qt keeps out of the console history. */
const SENSITIVE = /^\s*(walletpassphrase|walletpassphrasechange|encryptwallet|importprivkey|importmulti|importwallet|dumpprivkey|dumpwallet|sethdseed|signmessagewithprivkey|signrawtransactionwithkey|createwallet)\b|\b(walletpassphrase|walletpassphrasechange|encryptwallet|importprivkey|importmulti|sethdseed|signmessagewithprivkey|signrawtransactionwithkey|createwallet)\s*\(/;

/** True when a line must not be stored in history. */
export function isSensitive(line) {
  return SENSITIVE.test(line);
}
