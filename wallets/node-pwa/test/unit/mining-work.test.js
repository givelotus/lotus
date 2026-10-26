import { test } from 'node:test';
import assert from 'node:assert/strict';
import { compactTarget, decodeMiningWork, validateCandidate } from '../../src/lib/mining-work.js';
import { bytesToHex, meetsTarget, setHeaderNonce, sha256d } from '../../src/lib/mining-hashes.js';
import { BrowserMiner } from '../../src/lib/browser-miner.js';
const descriptor = { version: 1, algorithm: 'sha256d', headerbytes: 80, nonceoffset: 76, noncebytes: 4, noncebyteorder: 'little', hashbyteorder: 'little', targetbyteorder: 'big', template_rpc: 'getrawunsolvedblock', submit_rpc: 'submitblock' };
const parent = 'ab'.repeat(32);
function fixture() {
  const header = new Uint8Array(80); header.fill(0xab, 4, 36);
  new DataView(header.buffer).setUint32(72, 0x207fffff, true);
  return { blockhex: bytesToHex(header) + '01ffdeadbeef', target: bytesToHex(compactTarget(0x207fffff).slice().reverse()) };
}
function solution(work) {
  for (let n = 0n; n < 1000n; ++n) if (meetsTarget(sha256d(setHeaderNonce(work.header, n)), work.target)) return n;
  throw new Error('test solution not found');
}
test('work target and parent must match the exact node candidate; only nonce changes', () => {
  const raw = fixture(); const work = decodeMiningWork(raw, descriptor, parent);
  const out = validateCandidate(work, solution(work));
  assert.equal(out.blockhex.slice(160), raw.blockhex.slice(160));
  assert.equal(out.blockhex.slice(0, 152), raw.blockhex.slice(0, 152));
  assert.throws(() => decodeMiningWork(raw, descriptor, 'cc'.repeat(32)), /changed parent/);
  assert.throws(() => decodeMiningWork({ ...raw, target: 'ff'.repeat(32) }, descriptor, parent), /differs/);
  assert.throws(() => validateCandidate(work, 1n << 32n), /invalid nonce/);
  assert.throws(() => compactTarget(0), /Invalid/);
  assert.throws(() => compactTarget(0x2300ffff), /out of range/);
});
function fake({ changed = false, reject = null } = {}) {
  const calls = []; const workers = []; const states = [];
  let accepted = 0;
  const miner = new BrowserMiner({
    rpc: { async call(method, params) {
      calls.push({ method, params });
      if (method === 'getbestblockhash') return changed && calls.filter((c) => c.method === method).length > 1 ? 'cc'.repeat(32) : parent;
      if (method === 'getrawunsolvedblock') return fixture();
      if (method === 'submitblock') return reject;
    } },
    createWorker() { const worker = { terminate() { this.terminated = true; }, postMessage(message) { this.work = message.work; } }; workers.push(worker); return worker; },
    onState(s) { states.push(s); }, onBlock() { accepted++; },
  });
  return { miner, calls, workers, states, get accepted() { return accepted; } };
}
test('mining never starts implicitly and Stop ignores late worker candidates', async () => {
  const f = fake(); assert.equal(f.workers.length, 0);
  await f.miner.start('address', descriptor); const worker = f.workers[0];
  const work = decodeMiningWork(fixture(), descriptor, parent);
  f.miner.stop();
  await worker.onmessage({ data: { type: 'candidate', nonce: solution(work).toString(), hashes: 1024 } });
  assert.equal(f.calls.filter((c) => c.method === 'submitblock').length, 0);
  assert.ok(worker.terminated);
});
test('CPU-verified current candidate submits unchanged block body; rejection stops', async () => {
  const f = fake({ reject: 'bad-candidate' }); await f.miner.start('address', descriptor);
  const work = decodeMiningWork(fixture(), descriptor, parent);
  await f.workers[0].onmessage({ data: { type: 'candidate', nonce: solution(work).toString(), hashes: 1024 } });
  const submitted = f.calls.find((c) => c.method === 'submitblock').params[0];
  assert.equal(submitted.slice(160), fixture().blockhex.slice(160));
  assert.equal(f.accepted, 0);
  assert.match(f.states.at(-1).status, /Node rejected/);
  assert.equal(f.states.at(-1).running, false);
});
test('stale tip prevents candidate submission and malformed GPU output stops', async () => {
  const f = fake({ changed: true }); await f.miner.start('address', descriptor);
  const work = decodeMiningWork(fixture(), descriptor, parent);
  await f.workers[0].onmessage({ data: { type: 'candidate', nonce: solution(work).toString(), hashes: 1024 } });
  assert.equal(f.calls.filter((c) => c.method === 'submitblock').length, 0);
  f.miner.stop();
  const g = fake(); await g.miner.start('address', descriptor);
  await g.workers[0].onmessage({ data: { type: 'candidate', nonce: '-1', hashes: 1024 } });
  assert.match(g.states.at(-1).status, /invalid nonce/);
  assert.equal(g.calls.filter((c) => c.method === 'submitblock').length, 0);
});
