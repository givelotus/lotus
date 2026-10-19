#!/usr/bin/env node
// Deterministic release bundle (format "node-pwa-bundle/1"), Node stdlib only.
//
//   npm run pack            → dist/node-pwa-<version>.tar.gz and .sha256
//
// The tarball's members all sit under node-pwa/: every file of src/, a
// generated BUNDLE.json listing each file's sha256 and size, and a .gz
// sibling for every listed compressible file. Members are sorted, regular
// files only (no directory entries), ustar headers with mode 0644, uid/gid 0,
// mtime SOURCE_DATE_EPOCH (default 0). Every gzip stream has mtime 0 and OS
// byte 255, so the output depends only on the inputs and the zlib deflate
// implementation (pin the Node version in CI to compare across machines).

import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { gzipSync } from 'node:zlib';
import { execFileSync } from 'node:child_process';
import { relative, join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { parseArgs } from 'node:util';
import { walk } from './lint.mjs';

export const COMPRESSIBLE = ['.html', '.js', '.mjs', '.css', '.json', '.webmanifest', '.svg', '.txt'];
const sha256 = (b) => createHash('sha256').update(b).digest('hex');
const byteOrder = (a, b) => Buffer.compare(Buffer.from(a), Buffer.from(b));

/** gzip with a fixed header: mtime 0 (Node's default) and OS "unknown". */
export function deterministicGzip(buf) {
  const gz = gzipSync(buf, { level: 9 });
  gz[4] = gz[5] = gz[6] = gz[7] = 0;
  gz[9] = 0xff;
  return gz;
}

function octal(n, width) {
  return n.toString(8).padStart(width - 1, '0') + '\0';
}

/** One ustar header block for a regular file. */
export function tarHeader(name, size, mtime) {
  const h = Buffer.alloc(512);
  let prefix = '';
  let base = name;
  if (Buffer.byteLength(name) > 100) {
    const cut = name.lastIndexOf('/', 155);
    if (cut <= 0 || Buffer.byteLength(name.slice(cut + 1)) > 100) throw new Error(`path too long for ustar: ${name}`);
    prefix = name.slice(0, cut);
    base = name.slice(cut + 1);
  }
  h.write(base, 0, 100, 'utf8');
  h.write(octal(0o644, 8), 100, 'ascii');
  h.write(octal(0, 8), 108, 'ascii');
  h.write(octal(0, 8), 116, 'ascii');
  h.write(octal(size, 12), 124, 'ascii');
  h.write(octal(mtime, 12), 136, 'ascii');
  h.write('        ', 148, 'ascii');
  h.write('0', 156, 'ascii');
  h.write('ustar\0', 257, 'ascii');
  h.write('00', 263, 'ascii');
  h.write(prefix, 345, 155, 'utf8');
  let sum = 0;
  for (const b of h) sum += b;
  h.write(octal(sum, 7) + ' ', 148, 'ascii');
  return h;
}

/** @param {Array<[string, Buffer]>} members already sorted */
export function tar(members, mtime) {
  const parts = [];
  for (const [name, data] of members) {
    parts.push(tarHeader(name, data.length, mtime), data);
    const pad = (512 - (data.length % 512)) % 512;
    if (pad) parts.push(Buffer.alloc(pad));
  }
  parts.push(Buffer.alloc(1024));
  const total = parts.reduce((n, b) => n + b.length, 0);
  const rec = 10240;
  if (total % rec) parts.push(Buffer.alloc(rec - (total % rec)));
  return Buffer.concat(parts);
}

/**
 * @param {{srcDir: string, version: string, sourceCommit: string, mtime?: number}} o
 * @returns {{tarball: Buffer, bundle: object}}
 */
export function buildBundle({ srcDir, version, sourceCommit, mtime = 0 }) {
  if (!/^\d+\.\d+\.\d+$/.test(version)) throw new Error(`version must be X.Y.Z, got ${version}`);
  if (!/^[0-9a-f]{40}$/.test(sourceCommit)) throw new Error('source commit must be 40 lowercase hex');
  const files = new Map();
  for (const full of walk(srcDir)) {
    const rel = relative(srcDir, full).split('\\').join('/');
    if (rel.split('/').some((s) => s.startsWith('.'))) continue; // e.g. .DS_Store
    let data = readFileSync(full);
    if (rel === 'sw.js') {
      const text = data.toString('utf8');
      const marker = "const VERSION = 'dev';";
      if (text.split(marker).length !== 2) throw new Error('sw.js must contain exactly one VERSION marker');
      data = Buffer.from(text.replace(marker, `const VERSION = '${version}';`));
    }
    if (rel === 'BUNDLE.json' || rel.endsWith('.gz')) throw new Error(`src/ must not contain ${rel}`);
    files.set(rel, data);
  }
  const listed = [...files.keys()].sort(byteOrder);
  const bundle = {
    format: 1,
    name: 'node-pwa',
    version,
    source_commit: sourceCommit,
    files: Object.fromEntries(listed.map((rel) => [rel, { sha256: sha256(files.get(rel)), size: files.get(rel).length }])),
  };
  const members = new Map();
  members.set('BUNDLE.json', Buffer.from(JSON.stringify(bundle, null, 1) + '\n'));
  for (const rel of listed) {
    members.set(rel, files.get(rel));
    if (COMPRESSIBLE.some((ext) => rel.endsWith(ext))) members.set(`${rel}.gz`, deterministicGzip(files.get(rel)));
  }
  const sorted = [...members.keys()].sort(byteOrder);
  const tarball = deterministicGzip(tar(sorted.map((rel) => [`node-pwa/${rel}`, members.get(rel)]), mtime));
  return { tarball, bundle };
}

function main() {
  const here = dirname(fileURLToPath(import.meta.url));
  const pkgDir = join(here, '..');
  const { values } = parseArgs({
    options: {
      out: { type: 'string', default: join(pkgDir, 'dist') },
      'source-commit': { type: 'string' },
      'allow-dirty': { type: 'boolean', default: false },
    },
  });
  const pkg = JSON.parse(readFileSync(join(pkgDir, 'package.json'), 'utf8'));
  let commit = values['source-commit'];
  if (!commit) {
    commit = execFileSync('git', ['rev-parse', 'HEAD'], { cwd: pkgDir, encoding: 'utf8' }).trim();
    const dirty = execFileSync('git', ['status', '--porcelain', '--', 'src', 'package.json'], { cwd: pkgDir, encoding: 'utf8' }).trim();
    if (dirty && !values['allow-dirty']) {
      console.error(`src/ has uncommitted changes; commit them or pass --allow-dirty:\n${dirty}`);
      process.exit(1);
    }
    if (dirty) console.error('warning: packing uncommitted changes; source_commit does not describe them');
  }
  const mtime = Number(process.env.SOURCE_DATE_EPOCH ?? 0);
  if (!Number.isSafeInteger(mtime) || mtime < 0) throw new Error('SOURCE_DATE_EPOCH must be a non-negative integer');
  const { tarball, bundle } = buildBundle({ srcDir: join(pkgDir, 'src'), version: pkg.version, sourceCommit: commit, mtime });
  mkdirSync(values.out, { recursive: true });
  const name = `node-pwa-${pkg.version}.tar.gz`;
  const hash = sha256(tarball);
  writeFileSync(join(values.out, name), tarball);
  writeFileSync(join(values.out, `${name}.sha256`), `${hash}  ${name}\n`);
  console.log(`${join(values.out, name)}`);
  console.log(`sha256 ${hash}`);
  console.log(`${Object.keys(bundle.files).length} files, version ${bundle.version}, source ${bundle.source_commit}`);
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) main();
