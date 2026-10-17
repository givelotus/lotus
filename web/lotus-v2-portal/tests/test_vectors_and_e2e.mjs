/**
 * End-to-End & Bit-for-Bit P04 Test Vector Suite (`web/lotus-v2-portal/tests/test_vectors_and_e2e.mjs`)
 *
 * Verifies:
 * 1. Bit-for-bit parity between `miner-worker.js` / `miner-webgpu.js` (word-packed & byte-level
 *    2-stage Tagged BLAKE3) and all P04 test vectors from `miner/V2-MINING.md`, `v2_header.rs`,
 *    `v2_gpu.rs`, and `v2_job.rs` (including `0x08090a0b0c0d0e0f`, `0x08090a0b0c0d0e10`,
 *    `u64::MAX`, u32 carry boundaries, and the `native-037-template` C++ block fixture).
 * 2. WGSL compute shader structure (`@compute @workgroup_size(256)`, `b3_g`, `b3_compress`,
 *    `atomicAdd(&hits.count, 1u)`, and 2-stage `WorkHash` -> `BlockID` pipeline).
 * 3. Live End-to-End flow against `server.py` on a high port (>= 37000):
 *    `GET /pool/jobs` (SSE) -> JS/WGSL share mining -> `POST /pool/submit` -> share acceptance ->
 *    $10/mo newsletter subscription unlock -> `GET /api/newsletter/articles` premium unlock ->
 *    PPLNS stats & block discovery update!
 */

import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { createRequire } from 'node:module';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const __dirname = path.dirname(fileURLToPath(import.meta.url));

const Core = require('../public/miner-worker.js');
const WebGPUMod = require('../public/miner-webgpu.js');

const P04_HEADER_HEX =
  '202122232425262728292a2b2c2d2e2f303132333435363738393a3b3c3d3e3f' +
  'ffff001d0605040302010f0e0d0c0b0a0908020000008877665544332211' +
  '00ffeeddccbbaa99404142434445464748494a4b4c4d4e4f505152535455565758595a5b5c5d5e5f' +
  '606162636465666768696a6b6c6d6e6f707172737475767778797a7b7c7d7e7f';

const P04_CHAIN_ID_HEX =
  '000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f';

const NATIVE_037_TEMPLATE = {
  protocol: 'v2',
  job_id: 'native-037-template',
  chain_id: P04_CHAIN_ID_HEX,
  header:
    '2ba3f975fbc1840b9cb4acc6aa84a88539010eb2132cb06a43168b1cb6b66ae5ffff002178f1536500000000000000000000020000009001000000000000050000000000000033333333333333333333333333333333333333333333333333333333333333334444444444444444444444444444444444444444444444444444444444444444',
  target: '000000000000000000000000000000000000000000000000000000000000ffff',
};

function testP04VectorsAndWordBatchParity() {
  console.log('1. Verifying bit-for-bit parity with P04 & lotus_v2.cl test vectors...');
  const header = Core.hexToBytes(P04_HEADER_HEX);
  const chainId = Core.hexToBytes(P04_CHAIN_ID_HEX);
  const allFfTarget = new Uint8Array(32).fill(0xff);

  // Vector 1: Nonce 0x08090a0b0c0d0e0f
  const v1 = Core.hashes(header, chainId);
  assert.equal(
    Core.bytesToHex(v1.bodyHash),
    '1704e11edcbc47eb829d210ac1affb606dd4021c82305e07a028962456efec3d',
    'P04 BodyHash mismatch'
  );
  assert.equal(
    Core.bytesToHex(v1.workHash),
    '56c49269bcb4709b42d48312a382badc0906162e5bd6e49aac48a7096288ffd1',
    'P04 WorkHash[0] mismatch'
  );
  assert.equal(
    Core.bytesToHex(v1.blockId),
    'fbe9243579627fc3a41043c80395d33a8a01b91a9b86b6c6e629530595c83370',
    'P04 BlockID[0] mismatch'
  );

  // Vector 2: Nonce 0x08090a0b0c0d0e10 (start + 1)
  const header2 = Core.writeNonceLE(header, 0x08090a0b0c0d0e10n);
  const v2 = Core.hashes(header2, chainId);
  assert.equal(Core.bytesToHex(v2.bodyHash), Core.bytesToHex(v1.bodyHash));
  assert.equal(
    Core.bytesToHex(v2.workHash),
    '3df1f29ca207e25132c7b3fdddfae0163b16d0c6bf7488e2810858e84f0673e5',
    'P04 WorkHash[1] mismatch'
  );
  assert.equal(
    Core.bytesToHex(v2.blockId),
    '8a967f4522d06f683830cf003b9f456001e045f617bf4d4336754a91c75f5824',
    'P04 BlockID[1] mismatch'
  );

  // Verify pre-packed u32 word batch evaluator matches both vectors and u64::MAX
  const prepared = Core.prepareTemplates(header, chainId, allFfTarget);
  const batch = Core.hashNoncesWordBatch(
    prepared.workWords,
    prepared.idPrefixWords,
    prepared.targetWords,
    0x08090a0b0c0d0e0fn,
    2,
    true
  );
  assert.equal(batch.matches.length, 2);
  assert.equal(
    Core.bytesToHex(batch.matches[0].blockId),
    'fbe9243579627fc3a41043c80395d33a8a01b91a9b86b6c6e629530595c83370'
  );
  assert.equal(
    Core.bytesToHex(batch.matches[1].blockId),
    '8a967f4522d06f683830cf003b9f456001e045f617bf4d4336754a91c75f5824'
  );

  // Vector 3: u64::MAX (0xffffffffffffffff)
  const maxBatch = Core.hashNoncesWordBatch(
    prepared.workWords,
    prepared.idPrefixWords,
    prepared.targetWords,
    0xffffffffffffffffn,
    1,
    true
  );
  assert.equal(
    Core.bytesToHex(maxBatch.matches[0].blockId),
    'ce606e015b769cf60502917d0bac3597048e25668c7df323f817b53969aab371',
    'P04 u64::MAX BlockID mismatch'
  );

  // Vector 4: u32 carry window (0xffffffff - 1 .. +4)
  const carryStart = 0xffffffffn - 1n;
  const carryBatch = Core.hashNoncesWordBatch(
    prepared.workWords,
    prepared.idPrefixWords,
    prepared.targetWords,
    carryStart,
    4,
    true
  );
  for (let i = 0; i < 4; i++) {
    const n = carryStart + BigInt(i);
    const h = Core.writeNonceLE(header, n);
    const expected = Core.hashes(h, chainId).blockId;
    assert.equal(
      Core.bytesToHex(carryBatch.allResults[i].blockId),
      Core.bytesToHex(expected),
      `u32 carry mismatch at offset ${i}`
    );
  }

  // Vector 5: C++ native-037-template fixture
  const tplHeader = Core.hexToBytes(NATIVE_037_TEMPLATE.header);
  const tplTarget = Core.hexToBytes(NATIVE_037_TEMPLATE.target);
  const tplHashes = Core.hashes(tplHeader, chainId);
  assert.equal(
    Core.bytesToHex(tplHashes.bodyHash),
    'e6488811010b45ed6ce854cdc9758edb80b552d23e75948e7ccc1fe0f5145bea'
  );
  assert.equal(
    Core.bytesToHex(tplHashes.workHash),
    '67609329f280d16be8df0d4c20d8e2ffd6fadca4b69750f93bd432d492e1587c'
  );
  assert.equal(
    Core.bytesToHex(tplHashes.blockId),
    'd9ba1f949132940f2a3e4c1cf5c15dd8ecdb7718055f686ac5e3d3b2c5824d2a'
  );

  const tplPrep = Core.prepareTemplates(tplHeader, chainId, tplTarget);
  const tplSearch = Core.hashNoncesWordBatch(
    tplPrep.workWords,
    tplPrep.idPrefixWords,
    tplPrep.targetWords,
    0n,
    8,
    false
  );
  assert.ok(tplSearch.matches.length >= 1, 'native-037-template must find a match in 0..8');
  assert.ok(Core.meetsTarget(tplSearch.matches[0].blockId, tplTarget));

  console.log('   ✓ All P04 & native-037 vectors match bit-for-bit!');
}

function testWgslShaderStructure() {
  console.log('2. Verifying WGSL Compute Shader in miner-webgpu.js...');
  const wgsl = WebGPUMod.LOTUS_V2_WGSL;
  assert.ok(wgsl.includes('@compute @workgroup_size(256)'), 'Missing @compute @workgroup_size(256)');
  assert.ok(wgsl.includes('fn b3_g('), 'Missing b3_g in WGSL');
  assert.ok(wgsl.includes('fn b3_compress('), 'Missing b3_compress in WGSL');
  assert.ok(wgsl.includes('fn find_nonce_matches('), 'Missing find_nonce_matches entry point');
  assert.ok(wgsl.includes('atomicAdd(&hits.count, 1u)'), 'Missing atomicAdd(&hits.count, 1u)');
  assert.equal(WebGPUMod.WORKGROUP_SIZE, 256);
  assert.equal(WebGPUMod.TARGET_DISPATCH_MS, 3.0);
  console.log('   ✓ WGSL shader structure & constants verified!');
}

function parseSseFrames(rawText) {
  const frames = [];
  const chunks = rawText.replace(/\r\n/g, '\n').split('\n\n');
  for (const chunk of chunks) {
    let event = 'message';
    const dataLines = [];
    for (const line of chunk.split('\n')) {
      if (line.startsWith('event:')) event = line.slice(6).trim();
      else if (line.startsWith('data:')) dataLines.push(line.slice(5).trim());
    }
    if (dataLines.length > 0) {
      frames.push({ event, data: JSON.parse(dataLines.join('\n')) });
    }
  }
  return frames;
}

async function testEndToEndPoolAndNewsletter() {
  const port = 37215; // High port >= 37000, strictly avoids 10604, 10605, 8331
  const baseUrl = `http://127.0.0.1:${port}`;
  const serverScript = path.resolve(__dirname, '../server.py');

  console.log(`3. Starting server.py on port ${port} for End-to-End verification...`);
  const proc = spawn('python3', [serverScript, '--port', String(port)], {
    env: { ...process.env, LOTUS_PORTAL_QUIET: '1' },
    stdio: ['ignore', 'pipe', 'pipe'],
  });

  try {
    // Wait for server to listen
    let ready = false;
    for (let i = 0; i < 30; i++) {
      try {
        const r = await fetch(`${baseUrl}/api/pool/stats`);
        if (r.ok) {
          ready = true;
          break;
        }
      } catch (_) {}
      await new Promise((res) => setTimeout(res, 100));
    }
    assert.ok(ready, 'server.py did not become ready in time');

    const subscriber = 'e2e-miner@lotus.org';
    const worker = `sub:${subscriber}`;

    // Step A: Verify newsletter is initially locked for subscriber
    let artResp = await (
      await fetch(`${baseUrl}/api/newsletter/articles?subscriber=${encodeURIComponent(subscriber)}`)
    ).json();
    assert.equal(artResp.subscription.unlocked, false);
    assert.ok(artResp.articles[0].premium_content[0].includes('Subscriber-only section'));

    // Step B: Connect to GET /pool/jobs?worker=sub:e2e-miner@lotus.org&once=1 and parse SSE job event
    const sseResp = await fetch(`${baseUrl}/pool/jobs?worker=${encodeURIComponent(worker)}&once=1`);
    assert.equal(sseResp.status, 200);
    assert.ok(sseResp.headers.get('content-type').includes('text/event-stream'));
    const sseText = await sseResp.text();
    const events = parseSseFrames(sseText);
    assert.equal(events.length, 1);
    assert.equal(events[0].event, 'job');

    const job = events[0].data;
    assert.equal(job.protocol, 'v2');
    assert.equal(job.header.length, 268);
    assert.equal(job.chain_id.length, 64);
    assert.equal(job.target.length, 64);

    // Step C: Mine 4 valid shares using `LotusV2MinerCore.hashNoncesWordBatch` and submit to POST /pool/submit
    const header = Core.hexToBytes(job.header);
    const chainId = Core.hexToBytes(job.chain_id);
    const target = Core.hexToBytes(job.target);
    const prepared = Core.prepareTemplates(header, chainId, target);

    let searchNonce = 0n;
    let sharesAccepted = 0;
    let lastSubmitData = null;

    while (sharesAccepted < 4 && searchNonce < 200000n) {
      const { matches } = Core.hashNoncesWordBatch(
        prepared.workWords,
        prepared.idPrefixWords,
        prepared.targetWords,
        searchNonce,
        2048,
        false
      );
      searchNonce += 2048n;

      for (const hit of matches) {
        const solvedHeader = Core.writeNonceLE(header, hit.nonce);
        const submitRes = await fetch(`${baseUrl}/pool/submit`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            protocol: 'v2',
            job_id: job.job_id,
            worker,
            nonce: Number(hit.nonce),
            nonce_hex: hit.nonce.toString(16).padStart(16, '0'),
            header: Core.bytesToHex(solvedHeader),
            block_id: Core.bytesToHex(hit.blockId),
          }),
        });
        assert.equal(submitRes.status, 200);
        lastSubmitData = await submitRes.json();
        assert.equal(lastSubmitData.accepted, true);
        assert.equal(lastSubmitData.subscription_unlocked, true);
        sharesAccepted = lastSubmitData.shares_accepted;
        if (sharesAccepted >= 4) break;
      }
    }

    assert.equal(sharesAccepted, 4, 'Should have mined and accepted 4 shares');
    assert.equal(lastSubmitData.subscription.usd_credited, 10.0);
    assert.equal(lastSubmitData.subscription.progress_pct, 100.0);
    assert.equal(lastSubmitData.subscription.unlock_method, 'mined-full-month');

    // Step D: Verify newsletter articles are now unlocked with full technical sections
    artResp = await (
      await fetch(`${baseUrl}/api/newsletter/articles?subscriber=${encodeURIComponent(subscriber)}`)
    ).json();
    assert.equal(artResp.subscription.unlocked, true);
    assert.equal(artResp.articles.length, 3);
    assert.ok(
      artResp.articles[0].premium_content[0].includes('Domain-Separated Tagged BLAKE3 Nodes'),
      'Premium article content should be unlocked after mining shares'
    );

    // Step E: Verify Pool Stats & PPLNS Split updated
    const statsResp = await (
      await fetch(`${baseUrl}/api/pool/stats?worker=${encodeURIComponent(worker)}`)
    ).json();
    assert.equal(statsResp.worker_stats.shares_accepted, 4);
    assert.ok(statsResp.worker_stats.pplns_xpi_earned >= 13.0);
    assert.equal(statsResp.reward_split.miner_pct, 50);
    assert.equal(statsResp.reward_split.staker_pct, 25);
    assert.equal(statsResp.reward_split.treasury_pct, 25);
    assert.ok(statsResp.recent_blocks.length >= 3, 'New block should be recorded in recent_blocks');

    // Step F: Verify Covenant & Card Unlock Endpoints
    const covResp = await (
      await fetch(`${baseUrl}/api/newsletter/unlock-covenant`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ subscriber: 'covenant-user@lotus.org' }),
      })
    ).json();
    assert.equal(covResp.ok, true);
    assert.equal(covResp.subscription.unlocked, true);
    assert.equal(covResp.subscription.unlock_method, 'lotus-v2-covenant');

    const cardResp = await (
      await fetch(`${baseUrl}/api/newsletter/unlock-card`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ subscriber: 'card-user@lotus.org', plan: 'monthly-10-usd' }),
      })
    ).json();
    assert.equal(cardResp.ok, true);
    assert.equal(cardResp.subscription.unlocked, true);
    assert.equal(cardResp.subscription.unlock_method, 'fiat-card-10-usd');

    console.log('   ✓ End-to-End SSE -> Share Mining -> Submit -> Newsletter Unlock -> PPLNS verified!');
  } finally {
    proc.kill('SIGTERM');
  }
}

async function main() {
  testP04VectorsAndWordBatchParity();
  testWgslShaderStructure();
  await testEndToEndPoolAndNewsletter();
  console.log('\nALL LOTUS V2 PORTAL & WEB MINER TESTS PASSED!');
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
