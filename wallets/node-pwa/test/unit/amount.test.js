import { test } from 'node:test';
import assert from 'node:assert/strict';
import { parseAmount, formatAmount, fromRpc, toRpc, AmountError } from '../../src/lib/amount.js';
import { parse, Decimal } from '../../src/lib/json.js';

test('parse and format round trip for several decimal counts', () => {
  for (const [d, text, units] of [[2, '1.5', 150n], [2, '0.01', 1n], [6, '123.000001', 123000001n], [0, '42', 42n], [8, '.5', 50000000n], [2, '7.', 700n]]) {
    assert.equal(parseAmount(text, d), units, text);
  }
  assert.equal(formatAmount(150n, 2), '1.50');
  assert.equal(formatAmount(-1n, 2), '-0.01');
  assert.equal(formatAmount(5n, 0), '5');
  assert.equal(formatAmount(123456789n, 2, { group: true }), '1 234 567.89');
  assert.equal(formatAmount(1n, 2, { sign: true }), '+0.01');
  assert.equal(toRpc(100000000000000n, 2), '1000000000000.00');
});

test('refuses more than `decimals` digits instead of rounding', () => {
  assert.throws(() => parseAmount('1.001', 2), AmountError);
  assert.throws(() => parseAmount('1.5', 0), /no fractional/);
  assert.throws(() => parseAmount('-1', 2), /negative/);
  for (const bad of ['', ' ', '.', 'abc', '1,5', '1e3', '0x10', '1..2', '+1']) assert.throws(() => parseAmount(bad, 2), AmountError, bad);
});

test('large values are exact', () => {
  const units = parseAmount('92233720368547758.07', 2);
  assert.equal(units, 9223372036854775807n);
  assert.equal(formatAmount(units, 2), '92233720368547758.07');
});

test('fromRpc converts Decimal, Number and string exactly', () => {
  const v = parse('{"a":50000000.00,"b":-2.25,"c":5000000000,"d":1e-2,"e":1.10000000}');
  assert.equal(fromRpc(v.a, 2), 5000000000n);
  assert.equal(fromRpc(v.b, 2), -225n);
  assert.equal(fromRpc(v.c, 2), 500000000000n);
  assert.equal(fromRpc(v.d, 2), 1n);
  assert.equal(fromRpc(v.e, 2), 110n);
  assert.equal(fromRpc(0.3, 2), 30n);
  assert.equal(fromRpc('12.34', 2), 1234n);
  assert.equal(fromRpc(undefined, 2), 0n);
  assert.throws(() => fromRpc(new Decimal('0.001'), 2), AmountError);
});
