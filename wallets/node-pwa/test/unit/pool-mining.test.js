import { test } from 'node:test';
import assert from 'node:assert/strict';
import { poolTerms, poolWorkerId, decodePoolJob, validatePoolCandidate } from '../../src/lib/pool-mining.js';
import { BrowserPoolMiner } from '../../src/lib/browser-pool-miner.js';
import { encode } from '../../src/lib/xpiaddr.js';
import { bytesToHex, setHeaderNonce } from '../../src/lib/mining-hashes.js';
import { compactTarget } from '../../src/lib/mining-work.js';
const descriptor = { version: 1, algorithm: 'lotus-v2-blockid', headerbytes: 134, nonceoffset: 42, noncebytes: 8, noncebyteorder: 'little', hashbyteorder: 'little', targetbyteorder: 'big', template_rpc: 'getrawunsolvedblock', submit_rpc: 'submitblock', chainid: '17'.repeat(32) };
const address = encode('rxpi', new Uint8Array(32).fill(3));
const workerId = `${address}.browser`;
const info = { enabled: true, payout_ready: true, pool_address: address, operator_fee_bps: 125, operator_address: address, pplns_window_max: 1000 };
const terms = poolTerms(info);
function fixture({ prefix = 0xffffff, target = 'bf' + 'ff'.repeat(31) } = {}) {
  let header = new Uint8Array(134);
  new DataView(header.buffer).setUint32(32, 0x207fffff, true);
  header = setHeaderNonce(header, BigInt(prefix) << 40n);
  return { protocol: 'v2', worker_id: workerId, job_id: '18446744073709551615', chain_id: descriptor.chainid,
    header_hex: bytesToHex(header), prev_block_hash: '00'.repeat(32), nonce_prefix: prefix,
    share_target: target, network_target: bytesToHex(compactTarget(0x207fffff).reverse()), operator_fee_bps: 125, operator_address: address };
}
function solve(work) {
  for (let nonce = work.nonceStart; nonce < work.nonceStart + 100n; nonce++) {
    try { validatePoolCandidate(work, nonce); return nonce; } catch {}
  }
  throw new Error('No test nonce found');
}
test('native worker destination validates network and excludes symbolic fallback', () => {
  assert.equal(poolWorkerId(address, 'browser', { network: { kind: 'lotus-v2', chain: 'regtest' }, address: { nativeHrp: 'rxpi', acceptedFormats: ['xpiaddr'] } }), workerId);
  assert.throws(() => poolWorkerId(address, 'browser', { network: { kind: 'lotus-v2', chain: 'main' }, address: { nativeHrp: 'xpi', acceptedFormats: ['xpiaddr'] } }), /wrong network/);
  assert.throws(() => poolWorkerId(address, 'sub:operator', { network: { kind: 'lotus-v2', chain: 'regtest' }, address: { nativeHrp: 'rxpi', acceptedFormats: ['xpiaddr'] } }), /Worker name/);
  assert.throws(() => poolWorkerId('alice', 'browser', { network: { kind: 'lotus-v2', chain: 'regtest' }, address: { nativeHrp: 'rxpi', acceptedFormats: ['xpiaddr'] } }));
});
test('native jobs validate layout, chain, terms, target, identity and unsigned nonce bounds', () => {
  const raw = fixture(); const work = decodePoolJob(raw, descriptor, workerId, terms);
  assert.equal(work.nonceStart, 0xffffff0000000000n); assert.equal(work.nonceEnd, 1n << 64n);
  assert.doesNotThrow(() => validatePoolCandidate(work, solve(work)));
  assert.throws(() => validatePoolCandidate(work, work.nonceStart - 1n), /range/);
  assert.throws(() => validatePoolCandidate(work, work.nonceEnd), /range/);
  for (const patch of [{ protocol: 'ecash' }, { chain_id: '99'.repeat(32) }, { worker_id: 'alice' }, { job_id: '18446744073709551616' }, { nonce_prefix: 0 }, { nonce_prefix: 0x1000000 }, { network_target: 'ff'.repeat(32) }, { operator_fee_bps: 126 }, { header_hex: raw.header_hex.slice(2) }]) assert.throws(() => decodePoolJob({ ...raw, ...patch }, descriptor, workerId, terms));
  assert.throws(() => poolTerms({ ...info, operator_fee_bps: 10001 }));
  assert.throws(() => poolTerms({ ...info, payout_ready: false }));
});
function fake({ reject = false, changedTerms = false } = {}) {
  const calls = [], workers = [], states = []; let job = 0;
  const miner = new BrowserPoolMiner({ rpc: { async call(method, params) {
    calls.push({ method, params });
    if (method === 'getpoolinfo') return changedTerms ? { ...info, operator_fee_bps: 200 } : info;
    if (method === 'getpoolworker') return { estimated_hashrate: 123, pplns_weight: 0.5 };
    if (method === 'getminingjob') return { ...fixture({ target: job++ ? '7f' + 'ff'.repeat(31) : undefined }), job_id: String(job) };
    if (method === 'submitminingshare') return { accepted: !reject, block_found: false, accepted_shares: reject ? 0 : 1, rejected_shares: reject ? 1 : 0, reason: reject ? 'nonce-prefix-mismatch' : 'accepted', share_target: '7f' + 'ff'.repeat(31) };
    throw new Error(method);
  } }, createWorker() { const worker = { terminate() { this.terminated = true; }, postMessage(message) { this.work = message.work; } }; workers.push(worker); return worker; }, onState(patch) { states.push(patch); } });
  return { calls, workers, states, miner };
}
test('reviewed terms precede registration; changed commission never dispatches GPU', async () => {
  const f = fake({ changedTerms: true }); assert.equal(f.calls.length, 0);
  await f.miner.start(workerId, descriptor, terms);
  assert.equal(f.workers.length, 0); assert.equal(f.states.at(-1).running, false);
  assert.match(f.states.at(-1).status, /commission changed/);
});
test('share submits exact uint64 string, new job applies VarDiff and advances nonce cursor', async () => {
  const f = fake(); await f.miner.start(workerId, descriptor, terms);
  try {
    const work = decodePoolJob(fixture(), descriptor, workerId, terms); const nonce = solve(work);
    await f.workers[0].onmessage({ data: { type: 'candidate', nonce: nonce.toString(), hashes: 1024 } });
    const submission = f.calls.find((c) => c.method === 'submitminingshare');
    assert.equal(submission.params[2], nonce.toString()); assert.equal(typeof submission.params[2], 'string');
    assert.equal(f.workers[1].work.nonceStart, (work.nonceStart + 1024n).toString());
    assert.equal(bytesToHex(f.workers[1].work.target), 'ff'.repeat(31) + '7f');
    assert.ok(f.states.some((s) => s.acceptedShares === 1));
  } finally { f.miner.stop(); }
});
test('stop ignores late shares; invalid candidates never reach RPC', async () => {
  const f = fake(); await f.miner.start(workerId, descriptor, terms);
  const worker = f.workers[0]; f.miner.stop();
  await worker.onmessage({ data: { type: 'candidate', nonce: '1', hashes: 1024 } });
  assert.ok(worker.terminated); assert.equal(f.calls.filter((c) => c.method === 'submitminingshare').length, 0);
  const g = fake(); await g.miner.start(workerId, descriptor, terms);
  await g.workers[0].onmessage({ data: { type: 'candidate', nonce: '1', hashes: 1024 } });
  assert.match(g.states.at(-1).status, /range/); assert.equal(g.calls.filter((c) => c.method === 'submitminingshare').length, 0);
});
test('protocol errors stop without retry mining', async () => {
  const f = fake({ reject: true }); await f.miner.start(workerId, descriptor, terms);
  const work = decodePoolJob(fixture(), descriptor, workerId, terms);
  await f.workers[0].onmessage({ data: { type: 'candidate', nonce: solve(work).toString(), hashes: 1024 } });
  assert.equal(f.workers.length, 1); assert.equal(f.states.at(-1).running, false);
  assert.match(f.states.at(-1).status, /nonce-prefix-mismatch/);
});

test('explicit restart does not replay a completed nonce batch for the same worker', async () => {
  const f = fake(); await f.miner.start(workerId, descriptor, terms);
  const first = BigInt(f.workers[0].work.nonceStart);
  await f.workers[0].onmessage({ data: { type: 'progress', hashes: 1024 } });
  f.miner.stop(); await f.miner.start(workerId, descriptor, terms);
  try { assert.equal(f.workers[1].work.nonceStart, (first + 1024n).toString()); }
  finally { f.miner.stop(); }
});

test('pool payout accepts genuine type1 backend keyhash addresses without treating payload as a branch root', () => {
  const native = 'rxpi1pl8e2pv6n7jp0g9fgrk36qzff6z98mxnynqz57hhkvga4tq8xqlmsq2859j5u';
  assert.equal(poolWorkerId(native, 'wallet', { network: { kind: 'lotus-v2' }, address: { nativeHrp: 'rxpi', acceptedFormats: ['xpiaddr'] } }), `${native}.wallet`);
});
