// Opt-in, isolated accepted-block proof, never a production/user node.
// NODE_PWA_MINING_BINARY=/path/to/lotusd NODE_PWA_MINING_OUT=/persistent/dir
// NODE_PWA_MINING_RPC_PORT=59004 NODE_PWA_MINING_P2P_PORT=59005 node test/smoke/mining-node-proof.mjs
import { chromium } from '@playwright/test';
import { createHash } from 'node:crypto';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { startNode } from './regtest.mjs';
import { createDevServer } from '../../tools/devserver.mjs';
import { ChainConfig } from '../../src/lib/chainconfig.js';
import { v2BlockHash, sha256d, hexToBytes, bytesToHex } from '../../src/lib/mining-hashes.js';
const binary = process.env.NODE_PWA_MINING_BINARY;
const out = process.env.NODE_PWA_MINING_OUT;
if (!binary || !out) throw new Error('Explicit binary and persistent evidence directory required.');
mkdirSync(out, { recursive: true });
const digest = createHash('sha256').update(readFileSync(binary)).digest('hex');
let node, browser, server;
const receipt = { binary, binary_sha256: digest, started: new Date().toISOString(), status: 'running' };
try {
  node = await startNode(binary, { datadirBase: out, rpcPort: Number(process.env.NODE_PWA_MINING_RPC_PORT ?? 59004), p2pPort: Number(process.env.NODE_PWA_MINING_P2P_PORT ?? 59005) });
  receipt.datadir = node.datadir; receipt.rpc_port = node.rpcPort;
  await node.rpc('createwallet', ['gpu-proof']);
  const address = await node.rpc('getnewaddress', ['GPU proof'], 'gpu-proof');
  const chain = await node.rpc('getblockchaininfo');
  if (chain.chain !== 'regtest' || chain.blocks !== 0) throw new Error('Fresh isolated regtest required.');
  let descriptor;
  try {
    const discovery = await node.rpc('getchainconfig');
    const config = new ChainConfig(discovery);
    descriptor = config.mining.descriptor;
    receipt.discovery = discovery;
    receipt.descriptor_provenance = 'One getchainconfig RPC and validated immutable ChainConfig';
  } catch (error) {
    if (process.env.NODE_PWA_MINING_ALLOW_REFERENCE !== '1') throw error;
    receipt.discovery_error = error.message;
  }
  if (!descriptor) {
    // Legacy reference-only proof: never enables old-node GPU in the public UI.
    const genesis = await node.rpc('getblockheader', [chain.bestblockhash, false]);
    let algorithm, headerbytes, nonceoffset, noncebytes, chainid;
    if (genesis.length === 160 && bytesToHex(sha256d(hexToBytes(genesis)).reverse()) === chain.bestblockhash) {
      algorithm = 'sha256d'; headerbytes = 80; nonceoffset = 76; noncebytes = 4;
    } else if (genesis.length === 268 && bytesToHex(v2BlockHash(hexToBytes(genesis), new Uint8Array(32)).reverse()) === chain.bestblockhash) {
      algorithm = 'lotus-v2-blockid'; headerbytes = 134; nonceoffset = 42; noncebytes = 8; chainid = '00'.repeat(32);
    } else throw new Error('Audited regtest proof-of-work identity did not match actual node genesis.');
    descriptor = { version: 1, algorithm, headerbytes, nonceoffset, noncebytes, noncebyteorder: 'little', hashbyteorder: 'little', targetbyteorder: 'big', ...(chainid ? { chainid } : {}), template_rpc: 'getrawunsolvedblock', submit_rpc: 'submitblock' };
    receipt.descriptor_provenance = 'Reference artifact only: audited SHA256D/V2-zero-chain-id regtest descriptor independently verified against actual genesis. Public UI requires getchainconfig; no new descriptor RPC, combined stack, or clean new-build validation.';
  }
  receipt.descriptor = descriptor;
  ({ server } = createDevServer({ root: fileURLToPath(new URL('../../src/', import.meta.url)), rpcUrl: node.rpcUrl, cookieFile: node.cookieFile, auth: 'proxy' }));
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  browser = await chromium.launch({ channel: 'chrome', headless: true });
  const page = await browser.newPage();
  await page.route('**/wallet/test.html', (route) => route.fulfill({ contentType: 'text/html', body: '<!doctype html><div></div>' }));
  await page.goto(`http://127.0.0.1:${server.address().port}/wallet/test.html`);
  receipt.browser = await browser.version();
  const uiOnly = process.env.NODE_PWA_MINING_UI_ONLY === '1';
  if (!uiOnly) receipt.mining = await page.evaluate(async ({ descriptor, address }) => {
    const { BrowserMiner } = await import('/wallet/lib/browser-miner.js');
    return new Promise((resolve, reject) => {
      let hashes = 0;
      const timer = setTimeout(() => { miner.stop(); reject(new Error('Mining proof timed out')); }, 30000);
      const rpc = { async call(method, params, opts) {
        const response = await fetch('/', { method: 'POST', headers: { 'Content-Type': 'application/json' }, signal: opts?.signal, body: JSON.stringify({ jsonrpc: '1.0', id: 1, method, params }) });
        const value = await response.json(); if (value.error) throw new Error(value.error.message); return value.result;
      } };
      const miner = new BrowserMiner({ rpc, onState(state) { hashes = state.hashes ?? hashes; if (!state.running && state.status !== 'Stopped') { clearTimeout(timer); reject(new Error(state.status)); } },
        onBlock() { clearTimeout(timer); miner.stop(); resolve({ accepted: true, computed_gpu_hashes: hashes }); } });
      miner.start(address, descriptor);
    });
  }, { descriptor, address });
  const after = await node.rpc('getblockchaininfo');
  if (after.blocks !== (uiOnly ? 0 : 1)) throw new Error(`Unexpected proof height ${after.blocks}`);
  if (!uiOnly) {
    receipt.accepted_height = after.blocks; receipt.accepted_blockhash = after.bestblockhash;
    receipt.header = await node.rpc('getblockheader', [after.bestblockhash, false]);
  }
  if (uiOnly) {
    const methods = [];
    page.on('request', (request) => {
      if (request.method() !== 'POST') return;
      try { const body = request.postDataJSON(); for (const call of Array.isArray(body) ? body : [body]) methods.push(call.method); } catch {}
    });
    await page.goto(`http://127.0.0.1:${server.address().port}/wallet/#/mining?w=gpu-proof`);
    await page.getByLabel('Payout address', { exact: true }).waitFor();
    await page.getByLabel('Payout address', { exact: true }).fill(address);
    if (!await page.getByRole('button', { name: 'Start GPU mining', exact: true }).isEnabled()) throw new Error('Public GPU Start control was not enabled by discovery.');
    const actual = await page.evaluate(async () => {
      nodePwa.poller.stop();
      const config = nodePwa.store.get().profile;
      return { identity: config.chainIdentifier, ticker: config.currency.ticker, singleton: config === await nodePwa.chainAdaptor.discover(), immutable: Object.isFrozen(config) };
    });
    const discoveryCalls = methods.filter((method) => method === 'getchainconfig').length;
    const probes = methods.filter((method) => ['getcurrencyinfo', 'getmininginfo', 'getblockheader', 'validateaddress'].includes(method));
    if (discoveryCalls !== 1 || probes.length || !actual.singleton || !actual.immutable) throw new Error('Public UI did not use one authoritative immutable discovery.');
    receipt.public_ui = { ...actual, discovery_calls: discoveryCalls, legacy_probes: probes, gpu_start_enabled: true, mining_started: false };
  }
  receipt.status = 'ok';
} catch (error) { receipt.status = 'failed'; receipt.error = error.stack; process.exitCode = 1; }
finally {
  await browser?.close();
  if (server) { server.closeAllConnections(); await new Promise((resolve) => server.close(resolve)); }
  await node?.stop();
  receipt.finished = new Date().toISOString();
  writeFileSync(join(out, 'receipt.json'), JSON.stringify(receipt, null, 2) + '\n');
  console.log(JSON.stringify(receipt, null, 2));
}
