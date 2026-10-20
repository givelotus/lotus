import { test } from 'node:test';
import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { createDevServer } from '../../tools/devserver.mjs';
import { compactTarget } from '../../src/lib/mining-work.js';
import { sha256d, v2BlockHash, setHeaderNonce, meetsTarget } from '../../src/lib/mining-hashes.js';

test('actual browser worker dispatches both shaders and CPU-validates winning nonces', { skip: process.env.MINING_GPU !== '1' }, async () => {
  const { chromium } = await import('@playwright/test');
  const { server } = createDevServer({ root: fileURLToPath(new URL('../../src/', import.meta.url)), rpcUrl: 'http://127.0.0.1:1', auth: 'proxy' });
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  try {
    const page = await browser.newPage();
    await page.route('**/wallet/test.html', (route) => route.fulfill({ contentType: 'text/html', body: '<!doctype html><div></div>' }));
    await page.goto(`http://127.0.0.1:${server.address().port}/wallet/test.html`);
    for (const algorithm of ['sha256d', 'lotus-v2-blockid']) {
      const native = algorithm === 'lotus-v2-blockid';
      const header = new Uint8Array(native ? 134 : 80);
      new DataView(header.buffer).setUint32(native ? 32 : 72, 0x207fffff, true);
      const target = compactTarget(0x207fffff);
      const chainid = native ? new Uint8Array(32).fill(0x17) : undefined;
      const descriptor = { version: 1, algorithm, headerbytes: header.length, nonceoffset: native ? 42 : 76, noncebytes: native ? 8 : 4,
        noncebyteorder: 'little', hashbyteorder: 'little', targetbyteorder: 'big', template_rpc: 'getrawunsolvedblock', submit_rpc: 'submitblock', ...(native ? { chainid: '17'.repeat(32) } : {}) };
      const result = await page.evaluate(async ({ descriptor, header, target, chainid }) => {
        return new Promise((resolve, reject) => {
          const worker = new Worker('/wallet/mining/worker.js', { type: 'module' });
          const timeout = setTimeout(() => { worker.terminate(); reject(new Error('GPU worker timed out')); }, 30000);
          worker.onerror = (e) => { clearTimeout(timeout); worker.terminate(); reject(new Error(e.message)); };
          worker.onmessage = ({ data }) => {
            if (data.type === 'progress') return;
            clearTimeout(timeout); worker.terminate();
            if (data.type === 'candidate') resolve(data); else reject(new Error(data.message ?? data.type));
          };
          worker.postMessage({ type: 'start', work: { descriptor, header: Uint8Array.from(header), target: Uint8Array.from(target), ...(chainid ? { chainid: Uint8Array.from(chainid) } : {}) } });
        });
      }, { descriptor, header: Array.from(header), target: Array.from(target), chainid: chainid && Array.from(chainid) });
      const solved = setHeaderNonce(header, BigInt(result.nonce));
      assert.ok(meetsTarget(native ? v2BlockHash(solved, chainid) : sha256d(solved), target));
      assert.equal(result.hashes, 1024);
    }
  } finally { await browser.close(); server.closeAllConnections(); await new Promise((resolve) => server.close(resolve)); }
});

test('native GPU worker honors pool prefix, low-word carry and final uint64 partial dispatch', { skip: process.env.MINING_GPU !== '1' }, async () => {
  const { chromium } = await import('@playwright/test');
  const { server } = createDevServer({ root: fileURLToPath(new URL('../../src/', import.meta.url)), rpcUrl: 'http://127.0.0.1:1', auth: 'proxy' });
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  try {
    const page = await browser.newPage();
    await page.route('**/wallet/test.html', (route) => route.fulfill({ contentType: 'text/html', body: '<!doctype html><div></div>' }));
    await page.goto(`http://127.0.0.1:${server.address().port}/wallet/test.html`);
    for (const [start, end] of [[0xabcdef00fffffffen, 0xabcdef0100000002n], [(1n << 64n) - 2n, 1n << 64n]]) {
      const header = new Uint8Array(134), chainid = new Uint8Array(32).fill(0x17);
      const descriptor = { version: 1, algorithm: 'lotus-v2-blockid', headerbytes: 134, nonceoffset: 42, noncebytes: 8, noncebyteorder: 'little', hashbyteorder: 'little', targetbyteorder: 'big', template_rpc: 'getrawunsolvedblock', submit_rpc: 'submitblock', chainid: '17'.repeat(32) };
      // Choose a target whose first winning lane occurs after the u32 carry,
      // or at uint64 max, so validation cannot pass on lane zero alone.
      let expected, target;
      for (let seed = 0; seed < 256; seed++) {
        header[70] = seed;
        const digests = Array.from({ length: Number(end - start) }, (_, i) => v2BlockHash(setHeaderNonce(header, start + BigInt(i)), chainid));
        let minimum = 0;
        for (let i = 1; i < digests.length; i++) if (meetsTarget(digests[i], digests[minimum])) minimum = i;
        if (minimum === digests.length - 1) { expected = start + BigInt(minimum); target = digests[minimum]; break; }
      }
      assert.ok(target);
      const result = await page.evaluate(async (input) => new Promise((resolve, reject) => {
        const worker = new Worker('/wallet/mining/worker.js', { type: 'module' });
        const timer = setTimeout(() => { worker.terminate(); reject(new Error('Pool GPU boundary test timed out')); }, 30000);
        worker.onerror = (e) => { clearTimeout(timer); worker.terminate(); reject(new Error(e.message)); };
        worker.onmessage = ({ data }) => {
          if (data.type === 'progress') return;
          clearTimeout(timer); worker.terminate();
          if (data.type === 'candidate') resolve(data); else reject(new Error(data.message ?? data.type));
        };
        worker.postMessage({ type: 'start', work: { descriptor: input.descriptor, header: Uint8Array.from(input.header), target: Uint8Array.from(input.target), chainid: Uint8Array.from(input.chainid), nonceStart: input.start, nonceEnd: input.end } });
      }), { descriptor, header: Array.from(header), target: Array.from(target), chainid: Array.from(chainid), start: start.toString(), end: end.toString() });
      assert.equal(result.nonce, expected.toString());
      assert.equal(result.hashes, Number(end - start));
      assert.ok(meetsTarget(v2BlockHash(setHeaderNonce(header, BigInt(result.nonce)), chainid), target));
    }
  } finally { await browser.close(); server.closeAllConnections(); await new Promise((resolve) => server.close(resolve)); }
});
