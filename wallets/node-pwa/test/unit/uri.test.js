import { test } from 'node:test';
import assert from 'node:assert/strict';
import { parseUri, buildUri } from '../../src/lib/uri.js';

const XPI = 'xpi1q80z6tf5zlwd794z4dpe28fehp3qdt2lg8q3jz3mzacmrqw20vseq37xlywnx';

test('cashaddr addresses keep their prefix', () => {
  const u = parseUri(' ecash:qq123?amount=10.5&label=Coffee%20shop&message=hi+there ');
  assert.equal(u.address, 'ecash:qq123');
  assert.equal(u.amount, '10.5');
  assert.equal(u.label, 'Coffee shop');
  assert.equal(u.message, 'hi there');
  assert.equal(parseUri('ecregtest:qqabc').address, 'ecregtest:qqabc');
  assert.equal(parseUri('qqabc').address, 'qqabc');
});

test('xpi: URIs strip the scheme, both cases', () => {
  assert.equal(parseUri(`xpi:${XPI}?amount=1`).address, XPI);
  assert.equal(parseUri(`XPI:${XPI.toUpperCase()}`).address, XPI.toUpperCase());
  assert.equal(parseUri(`web+xpi:${XPI}`).address, XPI);
  assert.equal(parseUri(`web+xpi:${XPI}`).scheme, 'xpi');
  assert.equal(parseUri('web+ecash:qqx').address, 'ecash:qqx');
  assert.equal(parseUri(XPI).address, XPI);
});

test('rejects bad parameters', () => {
  assert.throws(() => parseUri('ecash:qq?amount=1e5'), /decimal/);
  assert.throws(() => parseUri('ecash:qq?amount=-1'), /decimal/);
  assert.throws(() => parseUri('ecash:qq?amount=1&amount=2'), /duplicate/);
  assert.throws(() => parseUri('ecash:qq?req-foo=1'), /required/);
  assert.deepEqual(parseUri('ecash:qq?other=x').params, { other: 'x' });
});

test('build', () => {
  assert.equal(buildUri({ address: XPI }, 'xpi', { qr: true }), 'XPI:' + XPI.toUpperCase());
  assert.equal(buildUri({ address: XPI }, 'xpi'), 'xpi:' + XPI);
  assert.equal(buildUri({ address: XPI, amount: '1.50', label: 'a b' }, 'xpi', { qr: true }), `xpi:${XPI}?amount=1.50&label=a%20b`);
  assert.equal(buildUri({ address: 'ecash:qq1', amount: '2', message: '&=' }, 'cashaddr'), 'ecash:qq1?amount=2&message=%26%3D');
  assert.equal(buildUri({ address: 'ecash:qq1', label: '' }, 'cashaddr'), 'ecash:qq1');
  const round = parseUri(buildUri({ address: 'ecash:qq1', amount: '3.25', label: 'x&y', message: 'm' }, 'cashaddr'));
  assert.deepEqual([round.address, round.amount, round.label, round.message], ['ecash:qq1', '3.25', 'x&y', 'm']);
});
