// Exact fixed-point amounts as BigInt base units.
//
// The number of decimals comes from getcurrencyinfo; nothing is hard-coded.
// Amounts are never rounded: input with more fractional digits than the
// currency has is refused, and RPC values are converted from their exact text.

import { Decimal } from './json.js';

export class AmountError extends Error {}

/**
 * Parse a user-entered amount ("1,234.5" style grouping is not accepted;
 * a plain decimal string with "." is).
 * @param {string} text
 * @param {number} decimals
 * @param {{allowNegative?: boolean}} [opts]
 * @returns {bigint} base units
 */
export function parseAmount(text, decimals, opts = {}) {
  if (typeof text !== 'string') throw new AmountError('amount must be text');
  const s = text.trim();
  if (s === '') throw new AmountError('enter an amount');
  const m = /^(-?)(\d*)(?:\.(\d*))?$/.exec(s);
  if (!m || (m[2] === '' && (m[3] === undefined || m[3] === ''))) throw new AmountError('not a number');
  const [, sign, whole, frac = ''] = m;
  if (sign && !opts.allowNegative) throw new AmountError('amount must not be negative');
  if (frac.length > decimals) {
    throw new AmountError(decimals === 0
      ? 'this currency has no fractional units'
      : `at most ${decimals} decimal place${decimals === 1 ? '' : 's'}`);
  }
  const units = BigInt(whole || '0') * 10n ** BigInt(decimals) + BigInt((frac + '0'.repeat(decimals)).slice(0, decimals) || '0');
  return sign ? -units : units;
}

/**
 * Format base units as a decimal string with exactly `decimals` digits.
 * @param {bigint} units
 * @param {number} decimals
 * @param {{group?: boolean, sign?: boolean}} [opts]
 */
export function formatAmount(units, decimals, opts = {}) {
  const neg = units < 0n;
  const abs = neg ? -units : units;
  const scale = 10n ** BigInt(decimals);
  let whole = (abs / scale).toString();
  if (opts.group) whole = whole.replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
  const frac = decimals > 0 ? '.' + (abs % scale).toString().padStart(decimals, '0') : '';
  const sign = neg ? '-' : opts.sign && abs > 0n ? '+' : '';
  return sign + whole + frac;
}

/**
 * Convert an RPC amount (Number, Decimal from json.js, or string) to base units.
 * Throws if the value has more precision than the currency.
 * @param {number|Decimal|string|null|undefined} value
 * @param {number} decimals
 * @returns {bigint}
 */
export function fromRpc(value, decimals) {
  if (value === null || value === undefined) return 0n;
  let text;
  if (value instanceof Decimal) text = value.text;
  else if (typeof value === 'number') {
    if (!Number.isFinite(value)) throw new AmountError('amount is not finite');
    text = Number.isInteger(value) ? value.toFixed(0) : String(value);
  } else text = String(value);
  if (/[eE]/.test(text)) text = expandExponent(text);
  // RPC values may carry trailing zeros beyond `decimals` (e.g. "1.000000").
  const m = /^(-?\d+)\.(\d+)$/.exec(text);
  if (m && m[2].length > decimals) {
    const extra = m[2].slice(decimals);
    if (/[^0]/.test(extra)) throw new AmountError(`RPC amount ${text} has more than ${decimals} decimals`);
    text = decimals ? `${m[1]}.${m[2].slice(0, decimals)}` : m[1];
  }
  return parseAmount(text, decimals, { allowNegative: true });
}

/** Base units → exact decimal string accepted by AmountFromValue. */
export function toRpc(units, decimals) {
  return formatAmount(units, decimals);
}

function expandExponent(text) {
  const m = /^(-?)(\d+)(?:\.(\d+))?[eE]([+-]?\d+)$/.exec(text);
  if (!m) throw new AmountError(`bad amount ${text}`);
  const [, sign, intPart, fracPart = '', expText] = m;
  const exp = Number(expText);
  let digits = intPart + fracPart;
  let point = intPart.length + exp;
  if (point <= 0) { digits = '0'.repeat(1 - point) + digits; point = 1; }
  if (point > digits.length) digits += '0'.repeat(point - digits.length);
  const whole = digits.slice(0, point).replace(/^0+(?=\d)/, '');
  const frac = digits.slice(point);
  return sign + whole + (frac ? '.' + frac : '');
}
