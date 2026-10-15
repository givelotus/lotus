/**
 * Strict parser for the tiny TOML subset used by `lotus.toml` (CABI-07).
 *
 * Accepted (every accepted file is also valid TOML 1.0):
 * - UTF-8 text without BOM, LF or CRLF line endings, no tab characters or control bytes;
 * - blank lines and full-line or trailing `#` comments;
 * - `[table]` headers with a bare key (no dotted, quoted, array or inline tables);
 * - `key = "string"` and `key = ["a", "b"]` (single line, optional trailing comma);
 * - bare keys `[A-Za-z0-9_-]+`; basic strings without escapes, quotes or control characters.
 *
 * Everything else (integers, booleans, escapes, multi-line values, dotted keys,
 * duplicate keys/tables, keys before the first table) is rejected rather than
 * approximated, so two parsers cannot disagree about an accepted manifest.
 */
export type TomlValue = string | string[];
export type TomlDocument = Map<string, Map<string, TomlValue>>;

const KEY = /^[A-Za-z0-9_-]+$/;
const STRING = /^"([^"\\\x00-\x1f\x7f]*)"/;

export function parseTomlSubset(text: string, file: string): TomlDocument {
  if (text.startsWith('\uFEFF')) throw new Error(`${file}: byte-order mark is not allowed`);
  const doc: TomlDocument = new Map();
  let table: Map<string, TomlValue> | undefined;
  const lines = text.split('\n');
  lines.forEach((raw, index) => {
    const lineNo = index + 1;
    const fail = (message: string): never => { throw new Error(`${file}:${lineNo}: ${message}`); };
    const line = raw.endsWith('\r') ? raw.slice(0, -1) : raw;
    if (/[\x00-\x08\x0a-\x1f\x7f\t]/.test(line)) fail('control or tab character');
    let rest = line.trim();
    if (rest === '' || rest.startsWith('#')) return;
    const header = /^\[([A-Za-z0-9_-]+)\]\s*(#.*)?$/.exec(rest);
    if (header) {
      const name = header[1]!;
      if (doc.has(name)) fail(`duplicate table [${name}]`);
      table = new Map(); doc.set(name, table); return;
    }
    const eq = rest.indexOf('=');
    if (eq < 0) fail('expected key = value');
    const key = rest.slice(0, eq).trim();
    if (!KEY.test(key)) fail(`unsupported key ${JSON.stringify(key)} (bare keys only)`);
    if (!table) fail('key outside of a table');
    if (table!.has(key)) fail(`duplicate key ${key}`);
    rest = rest.slice(eq + 1).trim();
    let value: TomlValue;
    if (rest.startsWith('"')) {
      const m = STRING.exec(rest); if (!m) fail('unsupported string (escapes, quotes and control characters are not allowed)');
      value = m![1]!; rest = rest.slice(m![0].length);
    } else if (rest.startsWith('[')) {
      rest = rest.slice(1).trim(); const items: string[] = [];
      while (!rest.startsWith(']')) {
        const m = STRING.exec(rest); if (!m) fail('array items must be basic strings on one line');
        items.push(m![1]!); rest = rest.slice(m![0].length).trim();
        if (rest.startsWith(',')) rest = rest.slice(1).trim();
        else if (!rest.startsWith(']')) fail('expected , or ] in array');
      }
      value = items; rest = rest.slice(1);
    } else return fail('unsupported value (only strings and string arrays)');
    rest = rest.trim();
    if (rest !== '' && !rest.startsWith('#')) fail('unexpected text after value');
    table!.set(key, value!);
  });
  return doc;
}
