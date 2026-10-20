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

test('typed native keyhash addresses match independent backend oracle on all networks', async () => {
  const { encodeTyped, decodeTyped } = await import('../../src/lib/xpiaddr.js');
  const typed = JSON.parse(readFileSync(new URL('../fixtures/xpiaddr_type1_vectors.json', import.meta.url), 'utf8'));
  assert.equal(typed.vectors.length, 9);
  for (const v of typed.vectors) {
    const value = decodeTyped(v.address, v.hrp);
    assert.equal(value.type, 1); assert.equal(hex(value.payload), v.payload);
    assert.equal(encodeTyped(v.hrp, Buffer.from(v.payload, 'hex'), 1), v.address);
    assert.equal(decodeTyped(v.address.toUpperCase()).type, 1);
    assert.throws(() => decode(v.address), /unknown version/); // key hash is not an explicit branch root
    const broken = v.address.slice(0, -1) + (v.address.endsWith('q') ? 'p' : 'q');
    assert.throws(() => decodeTyped(broken), /bad checksum/);
  }
  assert.equal(typed.vectors.at(-1).address, 'rxpi1pl8e2pv6n7jp0g9fgrk36qzff6z98mxnynqz57hhkvga4tq8xqlmsq2859j5u');
  for (const v of vectors.valid) { const value = decodeTyped(v.address); assert.equal(value.type, 0); assert.equal(hex(value.payload), v.root); }
  const future = vectors.invalid.find((v) => v.note === 'version 31 with a correct checksum');
  assert.throws(() => decodeTyped(future.address), /unknown version/);
  assert.throws(() => encodeTyped('rxpi', new Uint8Array(32), 2), /unknown version/);
});
