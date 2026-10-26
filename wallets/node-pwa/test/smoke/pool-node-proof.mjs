// Opt-in proof against a newly created isolated regtest node only.
// NODE_PWA_POOL_BINARY=/absolute/lotusd NODE_PWA_POOL_OUT=/persistent/evidence node test/smoke/pool-node-proof.mjs
import { execFileSync } from 'node:child_process';
import { ChainConfig } from '../../src/lib/chainconfig.js';
import { chromium } from '@playwright/test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { startNode } from './regtest.mjs';
import { createDevServer } from '../../tools/devserver.mjs';
import { encode } from '../../src/lib/xpiaddr.js';
const binary = process.env.NODE_PWA_POOL_BINARY, out = process.env.NODE_PWA_POOL_OUT;
if (!binary || !out) throw new Error('Explicit integration binary and persistent evidence directory required.');
mkdirSync(out, { recursive: true });
const operator = encode('rxpi', new Uint8Array(32).fill(1));
const frontendRoot = fileURLToPath(new URL('../../../../', import.meta.url));
const frontendCommit = execFileSync('git', ['rev-parse', 'HEAD'], { cwd: frontendRoot, encoding: 'utf8' }).trim();
const receipt = { frontend_commit: frontendCommit, started: new Date().toISOString(), binary, binary_sha256: createHash('sha256').update(readFileSync(binary)).digest('hex'), status: 'running' };
let node, server, browser, page;
const calls = [], jobs = [], shares = [];
try {
  node = await startNode(binary, { datadirBase: out, extraArgs: [`-pooladdress=${operator}`, '-poolfeepercent=1.25', '-gbtwithoutpeers=1'] });
  receipt.datadir = node.datadir; receipt.rpc_port = node.rpcPort; receipt.p2p_port = node.p2pPort;
  receipt.node_args = [`-pooladdress=${operator}`, '-poolfeepercent=1.25', '-gbtwithoutpeers=1'];
  receipt.backend_discovery = await node.rpc('getchainconfig');
  const actualConfig = new ChainConfig(receipt.backend_discovery);
  assert.equal(actualConfig.network.kind, 'lotus-v2'); assert.equal(actualConfig.address.nativeHrp, 'rxpi'); assert.equal(actualConfig.wallet.nativeReceiving, true);
  receipt.pool_before_start = await node.rpc('getpoolinfo');
  assert.equal(receipt.pool_before_start.operator_fee_bps, 125); assert.equal(receipt.pool_before_start.payout_ready, true);
  const initial = await node.rpc('getblockchaininfo'); assert.equal(initial.chain, 'regtest'); assert.equal(initial.blocks, 0);
  await node.rpc('createwallet', ['pool-proof']);
  ({ server } = createDevServer({ root: fileURLToPath(new URL('../../src/', import.meta.url)), rpcUrl: node.rpcUrl, cookieFile: node.cookieFile, auth: 'proxy' }));
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  browser = await chromium.launch({ channel: 'chrome', headless: true }); receipt.browser = await browser.version();
  page = await browser.newPage();
  page.on('response', async (response) => {
    try {
      const request = response.request(); if (request.method() !== 'POST') return;
      const body = request.postDataJSON(); if (Array.isArray(body)) { calls.push(...body.map((v) => v.method)); return; }
      calls.push(body.method);
      const result = (await response.json()).result;
      if (body.method === 'getminingjob' && result) jobs.push(result);
      if (body.method === 'submitminingshare' && result) shares.push({ params: body.params, result });
    } catch {}
  });
  await page.goto(`http://127.0.0.1:${server.address().port}/wallet/#/mining?w=pool-proof`);
  await page.getByLabel('Mining mode').selectOption('pool');
  await page.getByRole('button', { name: 'Create native payout address', exact: true }).click();
  await page.waitForFunction(() => document.querySelector('#pool-address')?.value.startsWith('rxpi1'));
  const payout = await page.getByLabel('Native payout address', { exact: true }).inputValue();
  receipt.payout = payout; receipt.ownership = await node.rpc('getaddressinfo', [payout], 'pool-proof');
  assert.equal(receipt.ownership.ismine, true); assert.equal(receipt.ownership.native, true); assert.equal(receipt.ownership.type, 1);
  await page.getByLabel('Worker name', { exact: true }).fill('proof');
  await page.getByRole('button', { name: 'Review pool terms', exact: true }).click();
  await page.getByText('1.25% of miner rewards', { exact: true }).waitFor();
  assert.equal(calls.filter((m) => m === 'getminingjob').length, 0);
  assert.equal(calls.filter((m) => m === 'submitminingshare').length, 0);
  await page.getByRole('button', { name: 'Start GPU mining', exact: true }).click();
  // Start first awaits selected-wallet ownership. Wait for its explicit running
  // state before interpreting a disabled Stop button as a mining failure.
  await page.waitForFunction(() => Array.from(document.querySelectorAll('button')).some((button) => button.textContent === 'Stop mining' && !button.disabled), null, { timeout: 5000 });
  // Polling the private test node is independent evidence of accepted GPU work.
  const deadline = Date.now() + 30000;
  let info;
  while (Date.now() < deadline) {
    info = await node.rpc('getpoolinfo'); if (info.blocks_found > 0) break;
    if (!await page.getByRole('button', { name: 'Stop mining', exact: true }).isEnabled()) throw new Error(`Mining stopped before a block: ${await page.locator('.mining [role="status"]').textContent()}`);
    await new Promise((resolve) => setTimeout(resolve, 50));
  }
  await page.getByRole('button', { name: 'Stop mining', exact: true }).click();
  assert.ok(info.blocks_found > 0, 'Browser must produce a node-accepted pool block');
  const id = `${payout}.proof`; const stats = await node.rpc('getpoolworker', [id]); assert.ok(stats.accepted_shares > 0);
  const accepted = shares.find((s) => s.result.accepted && s.result.block_found); assert.ok(accepted);
  const job = jobs.find((j) => j.job_id === accepted.params[0]); assert.ok(job);
  const decoded = await node.rpc('decoderawtransaction', [job.coinbase_tx_hex]);
  const block = await node.rpc('getblock', [accepted.result.block_hash]);
  assert.equal(block.tx[0], decoded.txid);
  const total = job.coinbase_outputs.reduce((sum, output) => sum + BigInt(output.value_sats), 0n);
  assert.equal(BigInt(job.operator_commission_sats), total * 125n / 10000n);
  assert.equal(BigInt(job.worker_reward_sats), total - BigInt(job.operator_commission_sats));
  assert.equal(job.operator_address, operator); assert.equal(job.worker_id, id);
  const discovery = await page.evaluate(() => {
    nodePwa.poller.stop(); const c = nodePwa.store.get().profile;
    return { identity: c.chainIdentifier, native_receiving: c.wallet.nativeReceiving, native_hrp: c.address.nativeHrp, ticker: c.ticker, immutable: Object.isFrozen(c) };
  });
  receipt.discovery = discovery; receipt.discovery_calls = calls.filter((m) => m === 'getchainconfig').length;
  assert.equal(receipt.discovery_calls, 1); assert.equal(discovery.native_receiving, true);
  receipt.worker = stats; receipt.pool = info; receipt.accepted_share = accepted; receipt.accepted_job = job;
  receipt.accepted_height = block.height; receipt.accepted_block = accepted.result.block_hash;
  receipt.no_implicit_start = true; receipt.explicit_stop = true; receipt.status = 'ok';
} catch (error) { receipt.status = 'failed'; receipt.error = error.stack; process.exitCode = 1; }
finally {
  receipt.observed_calls = calls; receipt.observed_jobs = jobs.length; receipt.observed_shares = shares;
  if (page) { try { receipt.final_ui_status = await page.locator('.mining [role="status"]').textContent(); } catch {} }
  await browser?.close();
  if (server) { server.closeAllConnections(); await new Promise((resolve) => server.close(resolve)); }
  await node?.stop(); receipt.finished = new Date().toISOString();
  writeFileSync(join(out, 'receipt.json'), JSON.stringify(receipt, null, 2) + '\n');
  console.log(JSON.stringify(receipt, null, 2));
}
