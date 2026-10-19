import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';

const dir = new URL('../../src/vendor/', import.meta.url);

test('vendored files match the hashes recorded in VENDOR.json', () => {
  const manifest = JSON.parse(readFileSync(new URL('VENDOR.json', dir), 'utf8'));
  assert.ok(Object.keys(manifest).length >= 2);
  for (const [name, info] of Object.entries(manifest)) {
    const h = createHash('sha256').update(readFileSync(new URL(name, dir))).digest('hex');
    assert.equal(h, info.sha256, name);
    assert.ok(info.license && info.upstream && info.version, name);
  }
});

test('vendored modules load and work', async () => {
  const { QrCode } = await import('../../src/vendor/qrcodegen.mjs');
  const qr = QrCode.encodeText('ECREGTEST:QQ', QrCode.Ecc.MEDIUM);
  assert.ok(qr.size >= 21);
  const preact = await import('../../src/vendor/htm-preact-standalone.mjs');
  assert.equal(typeof preact.html, 'function');
  assert.equal(typeof preact.useState, 'function');
});
