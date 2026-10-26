// BIP21-style payment URIs for cashaddr ("ecash:", "ecregtest:", ...) and
// xpiaddr ("xpi:").
//
// A cashaddr address already carries its prefix, so its URI is the address
// itself followed by an optional query. An xpiaddr has no ":" and is framed as
// "xpi:<address>". QR codes use the uppercase "XPI:<ADDRESS>" form when there
// are no parameters (alphanumeric QR mode is denser).

const KNOWN_KEYS = new Set(['amount', 'label', 'message']);

/**
 * @typedef {{address: string, amount?: string, label?: string, message?: string,
 *            params: Record<string, string>, scheme: string}} PaymentUri
 */

/**
 * Parse a pasted address or payment URI. Never validates the address itself;
 * the node does that.
 * @param {string} input
 * @returns {PaymentUri}
 */
export function parseUri(input) {
  let s = String(input).trim();
  const q = s.indexOf('?');
  const query = q >= 0 ? s.slice(q + 1) : '';
  s = q >= 0 ? s.slice(0, q) : s;
  let scheme = '';
  let address = s;
  const colon = s.indexOf(':');
  if (colon >= 0) {
    scheme = s.slice(0, colon).toLowerCase();
    if (scheme === 'xpi' || scheme === 'web+xpi') {
      address = s.slice(colon + 1).replace(/^\/\//, '');
    } else if (scheme === 'web+ecash') {
      address = 'ecash:' + s.slice(colon + 1).replace(/^\/\//, '');
      scheme = 'ecash';
    }
  }
  if (scheme === 'web+xpi') scheme = 'xpi';
  /** @type {PaymentUri} */
  const out = { scheme, address, params: {} };
  if (query) {
    for (const part of query.split('&')) {
      if (!part) continue;
      const eq = part.indexOf('=');
      const key = decodeComponent(eq >= 0 ? part.slice(0, eq) : part);
      const value = decodeComponent(eq >= 0 ? part.slice(eq + 1) : '');
      if (Object.hasOwn(out.params, key)) throw new Error(`duplicate URI parameter "${key}"`);
      if (key.startsWith('req-')) throw new Error(`unsupported required URI parameter "${key}"`);
      out.params[key] = value;
      if (KNOWN_KEYS.has(key)) out[key] = value;
    }
  }
  if (out.amount !== undefined && !/^\d*\.?\d+$|^\d+\.$/.test(out.amount)) {
    throw new Error('URI amount is not a decimal number');
  }
  return out;
}

function decodeComponent(s) {
  return decodeURIComponent(s.replace(/\+/g, ' '));
}

/**
 * @param {{address: string, amount?: string, label?: string, message?: string}} req
 * @param {'xpi'|'cashaddr'} format
 * @param {{qr?: boolean}} [opts] qr: prefer the uppercase form when possible
 */
export function buildUri(req, format, opts = {}) {
  const params = [];
  for (const key of ['amount', 'label', 'message']) {
    const v = req[key];
    if (v !== undefined && v !== null && v !== '') params.push(`${key}=${encodeURIComponent(v)}`);
  }
  const query = params.length ? '?' + params.join('&') : '';
  if (format === 'xpi') {
    if (!query && opts.qr) return 'XPI:' + req.address.toUpperCase();
    return 'xpi:' + req.address.toLowerCase() + query;
  }
  return req.address + query;
}
