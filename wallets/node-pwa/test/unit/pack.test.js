import { test } from 'node:test';
import assert from 'node:assert/strict';
import { gunzipSync } from 'node:zlib';
import { createHash } from 'node:crypto';
import { mkdtempSync, writeFileSync, mkdirSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { buildBundle, deterministicGzip, tarHeader } from '../../tools/pack.mjs';

const SRC = fileURLToPath(new URL('../../src/', import.meta.url));
const COMMIT = 'a'.repeat(40);

/** Minimal ustar reader for checking our own output. */
function untar(buf) {
  const out = [];
  for (let off = 0; off + 512 <= buf.length;) {
    const h = buf.subarray(off, off + 512);
    if (h.every((b) => b === 0)) break;
    const str = (a, b) => h.subarray(a, b).toString('utf8').replace(/\0.*$/s, '');
    const size = parseInt(str(124, 136), 8);
    const prefix = str(345, 500);
    let sum = 0;
    for (let i = 0; i < 512; i++) sum += i >= 148 && i < 156 ? 32 : h[i];
    assert.equal(parseInt(str(148, 156), 8), sum, 'header checksum');
    out.push({
      name: (prefix ? prefix + '/' : '') + str(0, 100), type: str(156, 157), mode: str(100, 108), uid: str(108, 116),
      mtime: parseInt(str(136, 148), 8), magic: str(257, 263), data: buf.subarray(off + 512, off + 512 + size),
    });
    off += 512 + Math.ceil(size / 512) * 512;
  }
  return out;
}

test('bundle is deterministic and follows node-pwa-bundle/1', () => {
  const a = buildBundle({ srcDir: SRC, version: '1.2.3', sourceCommit: COMMIT });
  const b = buildBundle({ srcDir: SRC, version: '1.2.3', sourceCommit: COMMIT });
  assert.ok(a.tarball.equals(b.tarball), 'same input → same bytes');
  assert.equal(a.tarball[9], 0xff);
  const members = untar(gunzipSync(a.tarball));
  const names = members.map((m) => m.name);
  assert.deepEqual(names, [...names].sort((x, y) => Buffer.compare(Buffer.from(x), Buffer.from(y))));
  assert.ok(members.every((m) => m.name.startsWith('node-pwa/') && m.type === '0' && m.mode === '0000644' && m.uid === '0000000' && m.mtime === 0 && m.magic === 'ustar'));
  const bundle = JSON.parse(members.find((m) => m.name === 'node-pwa/BUNDLE.json').data);
  assert.equal(bundle.format, 1);
  assert.equal(bundle.name, 'node-pwa');
  assert.equal(bundle.version, '1.2.3');
  assert.equal(bundle.source_commit, COMMIT);
  assert.ok(bundle.files['index.html'] && bundle.files['main.js'] && bundle.files['icons/icon-512.png']);
  const byName = new Map(members.map((m) => [m.name.slice('node-pwa/'.length), m.data]));
  for (const [rel, info] of Object.entries(bundle.files)) {
    const data = byName.get(rel);
    assert.equal(createHash('sha256').update(data).digest('hex'), info.sha256, rel);
    assert.equal(data.length, info.size, rel);
    const gz = byName.get(rel + '.gz');
    if (/\.(html|js|mjs|css|json|webmanifest|svg|txt)$/.test(rel)) assert.ok(gunzipSync(gz).equals(data), `${rel}.gz`);
    else assert.equal(gz, undefined, rel);
  }
  const expected = new Set(['BUNDLE.json']);
  for (const rel of Object.keys(bundle.files)) { expected.add(rel); if (byName.has(rel + '.gz')) expected.add(rel + '.gz'); }
  assert.deepEqual(new Set(byName.keys()), expected, 'no other members');
  assert.match(byName.get('sw.js').toString(), /const VERSION = '1\.2\.3';/);
  assert.equal(byName.get('index.html').toString().includes('content="session"'), true);
});

test('version, commit and SOURCE_DATE_EPOCH are reflected; bad inputs refused', () => {
  const a = buildBundle({ srcDir: SRC, version: '1.2.3', sourceCommit: COMMIT, mtime: 1700000000 });
  assert.ok(untar(gunzipSync(a.tarball)).every((m) => m.mtime === 1700000000));
  assert.throws(() => buildBundle({ srcDir: SRC, version: '1.2', sourceCommit: COMMIT }), /X\.Y\.Z/);
  assert.throws(() => buildBundle({ srcDir: SRC, version: '1.2.3', sourceCommit: 'abc' }), /40/);
});

test('src may not contain generated files; dot-files are skipped', () => {
  const dir = mkdtempSync(join(tmpdir(), 'node-pwa-pack-'));
  try {
    writeFileSync(join(dir, 'sw.js'), "const VERSION = 'dev';\n");
    writeFileSync(join(dir, '.DS_Store'), 'x');
    const { bundle } = buildBundle({ srcDir: dir, version: '0.0.1', sourceCommit: COMMIT });
    assert.deepEqual(Object.keys(bundle.files), ['sw.js']);
    writeFileSync(join(dir, 'a.js.gz'), 'x');
    assert.throws(() => buildBundle({ srcDir: dir, version: '0.0.1', sourceCommit: COMMIT }), /must not contain/);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test('long paths use the ustar prefix field; gzip header is fixed', () => {
  const name = 'node-pwa/' + 'd'.repeat(60) + '/' + 'f'.repeat(60) + '.js';
  const h = tarHeader(name, 1, 0);
  assert.equal(h.subarray(345, 345 + 70).toString().replace(/\0.*$/s, ''), 'node-pwa/' + 'd'.repeat(60));
  const g = deterministicGzip(Buffer.from('hello'));
  assert.deepEqual([...g.subarray(4, 10)], [0, 0, 0, 0, 2, 0xff]);
});

test('service worker dev precache list covers every app file', () => {
  const sw = readFileSync(join(SRC, 'sw.js'), 'utf8');
  const list = JSON.parse(sw.match(/const PRECACHE = (\[[\s\S]*?\]);/)[1].replace(/'/g, '"').replace(/,\s*\]/, ']'));
  const { bundle } = buildBundle({ srcDir: SRC, version: '0.0.1', sourceCommit: COMMIT });
  const files = Object.keys(bundle.files).filter((f) => f !== 'sw.js' && f !== 'vendor/VENDOR.json');
  assert.deepEqual(new Set(list.filter((f) => f !== '')), new Set(files));
  assert.ok(list.includes(''));
});
