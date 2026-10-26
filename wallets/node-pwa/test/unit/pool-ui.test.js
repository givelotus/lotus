import { test } from 'node:test';
import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { createDevServer } from '../../tools/devserver.mjs';
import { chainDiscovery } from '../helpers/chain-discovery.mjs';
import { encodeTyped } from '../../src/lib/xpiaddr.js';
import { bytesToHex, setHeaderNonce } from '../../src/lib/mining-hashes.js';
import { compactTarget } from '../../src/lib/mining-work.js';

test('pool UI gates native wallets, reviews terms, starts explicitly and cancels on wallet change', { skip: process.env.MINING_UI !== '1' }, async () => {
  const { chromium } = await import('@playwright/test');
  const { server } = createDevServer({ root: fileURLToPath(new URL('../../src/', import.meta.url)), rpcUrl: 'http://127.0.0.1:1', auth: 'proxy' });
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  try {
    const page = await browser.newPage();
    await page.route('**/wallet/test.html', (route) => route.fulfill({ contentType: 'text/html', body: '<!doctype html><div id="root"></div>' }));
    await page.goto(`http://127.0.0.1:${server.address().port}/wallet/test.html`);
    const discovery = chainDiscovery({ native: true });
    const address = encodeTyped('rxpi', new Uint8Array(32).fill(3), 1);
    let header = new Uint8Array(134); new DataView(header.buffer).setUint32(32, 0x207fffff, true); header = setHeaderNonce(header, 1n << 40n);
    const job = { protocol: 'v2', worker_id: `${address}.browser`, job_id: '1', chain_id: discovery.chain.chainid, header_hex: bytesToHex(header), prev_block_hash: '00'.repeat(32), nonce_prefix: 1,
      share_target: 'bf' + 'ff'.repeat(31), network_target: bytesToHex(compactTarget(0x207fffff).reverse()), operator_fee_bps: 125, operator_address: address };
    await page.evaluate(async ({ discovery, address, job }) => {
      const { html, render } = await import('/wallet/vendor/htm-preact-standalone.mjs');
      const { MiningView } = await import('/wallet/views/mining.js');
      const { ChainConfig } = await import('/wallet/lib/chainconfig.js');
      Object.defineProperty(navigator, 'gpu', { value: {}, configurable: true });
      window.calls = []; window.fakeWorkers = [];
      window.Worker = class { constructor() { window.fakeWorkers.push(this); } postMessage(value) { this.work = value; } terminate() { this.terminated = true; } };
      let state = { profile: new ChainConfig(discovery), wallet: 'first', wallets: ['first', 'second'] };
      const app = { refresh() {}, selectWallet(wallet) { state = { ...state, wallet }; draw(); },
        rpc: { async call(method, params = [], options) {
          calls.push({ method, params, wallet: options?.wallet });
          if (method === 'getpoolinfo') return { enabled: true, payout_ready: true, pool_address: address, operator_fee_bps: 125, operator_address: address, pplns_window_max: 1000 };
          if (method === 'getnewaddress') return address;
          if (method === 'getaddressinfo') return { native: true, type: 1, ismine: true, spendable: false };
          if (method === 'getminingjob') return job;
          if (method === 'getpoolworker') return { accepted_shares: 0, rejected_shares: 0 };
          throw new Error(method);
        } }, walletCall(method, params) { return this.rpc.call(method, params, { wallet: state.wallet }); } };
      const draw = () => render(html`<${MiningView} app=${app} state=${state} />`, document.querySelector('#root'));
      window.selectProofWallet = app.selectWallet;
      window.enableNative = () => { discovery.wallet = { native_receiving: { available: true, address_type: 'native', format: 'xpiaddr', template: 'keyhash' } }; state = { ...state, profile: new ChainConfig(discovery) }; draw(); };
      draw();
    }, { discovery, address, job });
    await page.getByLabel('Mining mode').selectOption('pool');
    assert.equal(await page.getByRole('button', { name: 'Create native payout address', exact: true }).isEnabled(), false);
    await page.evaluate(() => window.enableNative());
    await page.getByRole('button', { name: 'Create native payout address', exact: true }).click();
    await page.waitForFunction(() => document.querySelector('#pool-address')?.value.startsWith('rxpi1'));
    assert.equal(await page.getByRole('button', { name: 'Start GPU mining', exact: true }).isEnabled(), false);
    await page.getByRole('button', { name: 'Review pool terms', exact: true }).click();
    await page.getByText('1.25% of miner rewards', { exact: true }).waitFor();
    assert.equal(await page.evaluate(() => calls.filter((c) => c.method === 'getminingjob').length), 0);
    await page.getByRole('button', { name: 'Start GPU mining', exact: true }).click();
    await page.waitForFunction(() => window.fakeWorkers.length === 1);
    const proof = await page.evaluate(() => ({ calls, work: fakeWorkers[0].work }));
    assert.ok(proof.calls.some((c) => c.method === 'getnewaddress' && c.params[1] === 'native' && c.wallet === 'first'));
    assert.equal(proof.work.work.nonceStart, (1n << 40n).toString());
    await page.evaluate(() => window.selectProofWallet('second'));
    await page.waitForFunction(() => window.fakeWorkers[0].terminated === true);
    assert.equal(await page.getByRole('button', { name: 'Stop mining', exact: true }).isEnabled(), false);
    assert.equal(await page.evaluate(() => calls.filter((c) => c.method === 'submitminingshare').length), 0);
  } finally { await browser.close(); server.closeAllConnections(); await new Promise((resolve) => server.close(resolve)); }
});
