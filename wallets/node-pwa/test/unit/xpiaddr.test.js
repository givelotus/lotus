import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { encode, decode, K, XpiAddrError } from '../../src/lib/xpiaddr.js';

const vectors = JSON.parse(readFileSync(new URL('../fixtures/xpiaddr_v2_vectors.json', import.meta.url), 'utf8'));
const hex = (u8) => Buffer.from(u8).toString('hex');

test('constants match the vector file', () => {
  for (const [hrp, k] of Object.entries(vectors.constants)) assert.equal(K[hrp], BigInt(k));
});

test('every valid vector decodes and re-encodes', () => {
  assert.ok(vectors.valid.length >= 13);
  for (const v of vectors.valid) {
    const d = decode(v.address);
    assert.equal(d.hrp, v.hrp, v.note);
    assert.equal(hex(d.root), v.root, v.note);
    assert.deepEqual(decode(v.address, v.hrp).hrp, v.hrp);
    assert.equal(encode(v.hrp, Buffer.from(v.root, 'hex')), v.address.toLowerCase(), v.note);
    assert.equal(v.address.length, v.hrp === 'xpi' ? 65 : 66);
  }
});

test('every invalid vector fails with the exact reason', () => {
  assert.ok(vectors.invalid.length >= 30);
  for (const v of vectors.invalid) {
    assert.throws(() => decode(v.address), (e) => e instanceof XpiAddrError && e.reason === v.reason, `${v.note}: expected ${v.reason}`);
  }
});

test('wrong network is reported when the hrp differs from the chain', () => {
  const testnet = vectors.valid.find((v) => v.hrp === 'txpi').address;
  assert.throws(() => decode(testnet, 'xpi'), (e) => e.reason === 'wrong network');
});

test('encode rejects bad input', () => {
  assert.throws(() => encode('btc', new Uint8Array(32)), /unknown prefix/);
  assert.throws(() => encode('xpi', new Uint8Array(31)), /32 bytes/);
});
