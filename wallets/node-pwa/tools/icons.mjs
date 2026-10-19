#!/usr/bin/env node
// Regenerates src/icons/*.png from the same simple geometry as icon.svg
// (Node stdlib only: a tiny rasterizer and PNG writer). Run after changing
// the icon; the PNGs are committed.

import { writeFileSync } from 'node:fs';
import { deflateSync } from 'node:zlib';

const GREEN = [0x1f, 0x6f, 0x5c];
const WHITE = [0xff, 0xff, 0xff];

/** Coverage of the icon at point (x, y) in the 64-unit design space. */
function sample(x, y, maskable) {
  // Background: rounded square (or full bleed for maskable).
  const bg = maskable ? true : roundedRect(x, y, 0, 0, 64, 64, 14);
  if (!bg) return null;
  // Maskable icons keep content inside the 80% safe zone: scale around the centre.
  const s = maskable ? 1 / 0.75 : 1;
  const ux = (x - 32) * s + 32;
  const uy = (y - 32) * s + 32;
  const outer = roundedRect(ux, uy, 12, 18, 40, 30, 7);
  const inner = roundedRect(ux, uy, 16, 22, 32, 22, 3);
  const band = ux >= 14 && ux <= 50 && uy >= 25 && uy <= 29;
  const dot = (ux - 41) ** 2 + (uy - 37) ** 2 <= 9;
  return (outer && !inner) || (band && outer) || dot ? WHITE : GREEN;
}

function roundedRect(x, y, rx, ry, w, h, r) {
  if (x < rx || y < ry || x > rx + w || y > ry + h) return false;
  const cx = Math.min(Math.max(x, rx + r), rx + w - r);
  const cy = Math.min(Math.max(y, ry + r), ry + h - r);
  return (x - cx) ** 2 + (y - cy) ** 2 <= r * r;
}

function render(size, maskable) {
  const ss = 4;
  const rows = [];
  for (let py = 0; py < size; py++) {
    const row = Buffer.alloc(1 + size * 4);
    for (let px = 0; px < size; px++) {
      let r = 0, g = 0, b = 0, a = 0;
      for (let sy = 0; sy < ss; sy++) {
        for (let sx = 0; sx < ss; sx++) {
          const c = sample(((px + (sx + 0.5) / ss) * 64) / size, ((py + (sy + 0.5) / ss) * 64) / size, maskable);
          if (c) { r += c[0]; g += c[1]; b += c[2]; a += 255; }
        }
      }
      const n = ss * ss;
      const cov = a / 255;
      row.set(cov ? [Math.round(r / cov), Math.round(g / cov), Math.round(b / cov), Math.round(a / n)] : [0, 0, 0, 0], 1 + px * 4);
    }
    rows.push(row);
  }
  return png(size, size, Buffer.concat(rows));
}

function png(w, h, raw) {
  const crcTable = Array.from({ length: 256 }, (_, n) => {
    let c = n;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    return c >>> 0;
  });
  const crc = (buf) => {
    let c = 0xffffffff;
    for (const b of buf) c = crcTable[(c ^ b) & 0xff] ^ (c >>> 8);
    return (c ^ 0xffffffff) >>> 0;
  };
  const chunk = (type, data) => {
    const len = Buffer.alloc(4);
    len.writeUInt32BE(data.length);
    const td = Buffer.concat([Buffer.from(type, 'ascii'), data]);
    const c = Buffer.alloc(4);
    c.writeUInt32BE(crc(td));
    return Buffer.concat([len, td, c]);
  };
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(w, 0);
  ihdr.writeUInt32BE(h, 4);
  ihdr.set([8, 6, 0, 0, 0], 8); // 8-bit RGBA
  return Buffer.concat([
    Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
    chunk('IHDR', ihdr),
    chunk('IDAT', deflateSync(raw, { level: 9 })),
    chunk('IEND', Buffer.alloc(0)),
  ]);
}

const dir = new URL('../src/icons/', import.meta.url);
writeFileSync(new URL('icon-192.png', dir), render(192, false));
writeFileSync(new URL('icon-512.png', dir), render(512, false));
writeFileSync(new URL('maskable-512.png', dir), render(512, true));
console.log('wrote icon-192.png, icon-512.png, maskable-512.png');
