// Component-level browser checks with mocked RPCs; no daemon or wallet data.
import { test, expect } from '@playwright/test';
import { fileURLToPath } from 'node:url';
import { createDevServer } from '../../tools/devserver.mjs';
import { chainDiscovery } from '../helpers/chain-discovery.mjs';
const COMPACT_SIGNATURE = Buffer.from([31, ...new Uint8Array(64).fill(1)]).toString('base64');

let server;
let base;
test.beforeAll(async () => {
  ({ server } = createDevServer({ root: fileURLToPath(new URL('../../src/', import.meta.url)), rpcUrl: 'http://127.0.0.1:1', auth: 'proxy' }));
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  base = `http://127.0.0.1:${server.address().port}/wallet/`;
});
test.afterAll(async () => {
  server.closeAllConnections();
  await new Promise((resolve) => server.close(resolve));
});

async function mount(page, kind, config = {}) {
  await page.route('**/wallet/test.html', (route) => route.fulfill({ contentType: 'text/html', body: '<!doctype html><div id="root"></div>' }));
  await page.goto(`${base}test.html`);
  if (config.shell) await page.addStyleTag({ url: `${base}app.css` });
  await page.evaluate(async ({ kind, config, discovery, compactSignature }) => {
    const { html, render } = await import('/wallet/vendor/htm-preact-standalone.mjs');
    const { ChainAdaptor } = await import('/wallet/lib/chain-adaptor.js');
    const { ChainConfig } = await import('/wallet/lib/chainconfig.js');
    const { WalletsView } = await import('/wallet/views/wallets.js');
    const { StatusBar, Sidebar, TopBar } = await import('/wallet/ui/layout.js');
    const { ReceiveView } = await import('/wallet/views/receive.js');
    const { MessagesView } = await import('/wallet/views/messages.js');
    const { MiningView } = await import('/wallet/views/mining.js');
    window.calls = [];
    window.workerStarts = 0; window.workerStops = 0;
    if (config.fakeWorker) {
      Object.defineProperty(navigator, 'gpu', { configurable: true, value: {} });
      window.Worker = class {
        constructor() { window.workerStarts++; }
        postMessage() {}
        terminate() { window.workerStops++; }
      };
    }
    window.selected = null;
    window.refreshed = 0;
    const discovered = new ChainConfig(discovery);
    const profile = config.disableGpu ? { ...discovered, mining: { supported: false, reason: 'GPU mining is unavailable for this configuration.' } }
      : config.pow ? { ...discovered, mining: { supported: true, descriptor: config.pow } } : discovered;
    const state = { wallets: config.loaded ?? [], wallet: kind === 'receive' || kind === 'mining' || (kind === 'messages' && !config.noWallet) ? '' : null, net: { networkactive: true }, profile };
    const draw = () => {
      const View = kind === 'wallets' ? WalletsView : kind === 'receive' ? ReceiveView : kind === 'messages' ? MessagesView : kind === 'mining' ? MiningView : StatusBar;
      const body = html`<${View} app=${app} state=${state} />${config.long ? Array.from({ length: 40 }, (_, i) => html`<section class="card"><h2>More wallet content ${i}</h2><p>Scrollable content with accessible controls.</p><button type="button" id=${`content-${i}`}>Content action ${i}</button></section>`) : null}`;
      render(config.shell ? html`<div class="shell"><${Sidebar} app=${app} state=${state} route=${{ view: kind }} /><div class="main-col"><${TopBar} app=${app} state=${state} /><main class="content" tabindex="0" aria-label="Wallet content">${body}</main><${StatusBar} app=${app} state=${state} /></div></div>` : body, document.getElementById('root'));
    };
    const app = {
      auth: { canLogout: false },
      async walletCall(method, params) {
        window.calls.push({ method, params, wallet: state.wallet });
        if (method === 'getnewaddress') {
          window.generatedLabel = params[0];
          return 'ecregtest:qqtestaddress';
        }
        if (method === 'listreceivedbyaddress') return window.generatedLabel === undefined ? [] : [{ address: 'ecregtest:qqtestaddress', label: window.generatedLabel, amount: 0, confirmations: 0 }];
      },
      selectWallet(name) { window.selected = name; },
      refresh() { window.refreshed++; draw(); },
      toast(message, kind) { window.toast = { message, kind }; },
      rpc: { async call(method, params, opts) {
        window.calls.push({ method, params, ...(opts ? { wallet: opts.wallet } : {}) });
        if (config.fail && method === config.fail) throw new Error(config.failureMessage ?? 'RPC denied');
        if (method === 'getrawunsolvedblock') return config.rawTemplate;
        if (method === 'getbestblockhash') return 'ab'.repeat(32);
        if (method === 'getblockchaininfo') return { chain: config.actualChain ?? config.chain ?? 'regtest' };
        if (method === 'generatetoaddress') return Array.from({ length: params[0] }, () => 'ab'.repeat(32));
        if (method === 'getwalletinfo') return config.locked ? { unlocked_until: 0 } : {};
        if (method === 'signmessage') return compactSignature;
        if (method === 'verifymessage') return config.verify !== false;
        if (method === 'listwalletdir') {
          const disk = config.appearsAfterCheck && window.calls.filter((c) => c.method === method).length > 1 ? [''] : (config.disk ?? []);
          return { wallets: disk.map((name) => ({ name })) };
        }
        if (method === 'listwallets') return state.wallets;
        if (config.fail && method === config.fail) throw new Error('RPC denied');
        if (method === 'createwallet' || method === 'loadwallet') {
          state.wallets = [...state.wallets, params[0]];
          return { name: params[0] };
        }
        if (method === 'setnetworkactive') state.net = { ...state.net, networkactive: params[0] };
      } },
    };
    app.chainAdaptor = new ChainAdaptor({ rpc: app.rpc });
    app.chainAdaptor.config = new ChainConfig(discovery);
    app.chainAdaptor.promise = Promise.resolve(app.chainAdaptor.config);
    draw();
  }, { kind, config, discovery: chainDiscovery({ network: config.chain ?? 'regtest' }), compactSignature: COMPACT_SIGNATURE });
}

test('create default wallet passes empty name and selects it', async ({ page }) => {
  await mount(page, 'wallets');
  await page.getByRole('button', { name: 'Create default wallet', exact: true }).click();
  await expect.poll(() => page.evaluate(() => window.selected)).toBe('');
  expect(await page.evaluate(() => window.calls.find((c) => c.method === 'createwallet').params)).toEqual(['']);
  expect(await page.evaluate(() => window.refreshed)).toBe(1);
  await expect(page.getByRole('button', { name: 'Create default wallet', exact: true })).toHaveCount(0);
});

test('default created by another tab is opened without recreating', async ({ page }) => {
  await mount(page, 'wallets', { appearsAfterCheck: true });
  await page.getByRole('button', { name: 'Create default wallet', exact: true }).click();
  await expect.poll(() => page.evaluate(() => window.selected)).toBe('');
  expect(await page.evaluate(() => window.calls.filter((c) => c.method === 'createwallet'))).toEqual([]);
  expect(await page.evaluate(() => window.calls.find((c) => c.method === 'loadwallet').params)).toEqual(['']);
});

test('existing default offers open instead of duplicate creation', async ({ page }) => {
  await mount(page, 'wallets', { disk: [''] });
  await expect(page.getByRole('button', { name: 'Open', exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Create default wallet', exact: true })).toHaveCount(0);
  await page.getByRole('button', { name: 'Open', exact: true }).click();
  await expect.poll(() => page.evaluate(() => window.selected)).toBe('');
});

test('failed creation reports error without selecting a wallet', async ({ page }) => {
  await mount(page, 'wallets', { fail: 'createwallet' });
  await page.getByRole('button', { name: 'Create default wallet', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('RPC denied');
  expect(await page.evaluate(() => window.selected)).toBe(null);
  await expect(page.getByRole('button', { name: 'Create default wallet', exact: true })).toBeEnabled();
});

test('network action toggles node P2P in both directions', async ({ page }) => {
  await mount(page, 'network');
  await page.getByRole('button', { name: 'Disable peer networking', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Enable peer networking', exact: true })).toBeVisible();
  await expect(page.locator('#peer-network-help')).toContainText('disabled');
  await page.getByRole('button', { name: 'Enable peer networking', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Disable peer networking', exact: true })).toBeVisible();
  expect(await page.evaluate(() => window.calls.filter((c) => c.method === 'setnetworkactive').map((c) => c.params))).toEqual([[false], [true]]);
});


test('receiving address needs no request fields and is saved in the unnamed wallet', async ({ page }) => {
  await mount(page, 'receive');
  await page.getByRole('button', { name: 'Create receiving address', exact: true }).click();
  await expect(page.getByRole('dialog', { name: 'Receiving address', exact: true })).toBeVisible();
  await expect(page.getByTestId('request-address')).toHaveText('ecregtest:qqtestaddress');
  await expect(page.getByRole('button', { name: 'Copy address', exact: true })).toBeVisible();
  await expect(page.locator('svg.qr')).toBeVisible();
  expect(await page.evaluate(() => window.calls.filter((c) => c.method === 'getnewaddress'))).toEqual([{ method: 'getnewaddress', params: [''], wallet: '' }]);
  await page.getByRole('button', { name: 'Close', exact: true }).click();
  await expect(page.getByRole('table')).toContainText('ecregtest:qqtestaddress');
  await expect(page.locator('.receive')).toContainText('Addresses and labels are saved in the node');
  await expect(page.getByRole('heading', { name: 'Requested payments' }).locator('..')).toContainText('No requests yet');
});

test('payment request keeps its amount, message, browser history and durable address', async ({ page }) => {
  await mount(page, 'receive');
  await page.getByLabel('Label (optional)', { exact: true }).fill('Coffee');
  await page.getByLabel('Amount (XEC, optional)', { exact: true }).fill('2.50');
  await page.getByLabel('Message (optional)', { exact: true }).fill('Thanks');
  await page.getByRole('button', { name: 'Create payment request', exact: true }).click();
  await expect(page.getByRole('dialog', { name: 'Payment request', exact: true })).toBeVisible();
  await expect(page.getByRole('dialog')).toContainText('2.50');
  await expect(page.getByRole('dialog')).toContainText('Thanks');
  expect(await page.evaluate(() => window.calls.filter((c) => c.method === 'getnewaddress'))).toEqual([{ method: 'getnewaddress', params: ['Coffee'], wallet: '' }]);
  await page.getByRole('button', { name: 'Close', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Requested payments' }).locator('..')).toContainText('Coffee');
  await expect(page.getByRole('heading', { name: 'Received by address' }).locator('..')).toContainText('ecregtest:qqtestaddress');
});


test('signing preserves whitespace on the selected unnamed wallet without exporting keys', async ({ page }) => {
  await mount(page, 'messages');
  await page.getByLabel('Signing address', { exact: true }).fill(' ecregtest:qkey ');
  const message = '  line one\nline two \n';
  await page.getByLabel('Message to sign', { exact: true }).fill(message);
  await page.getByRole('button', { name: 'Sign message', exact: true }).click();
  await expect(page.getByTestId('signed-message')).toContainText(COMPACT_SIGNATURE);
  await expect(page.getByRole('button', { name: 'Copy signature', exact: true })).toBeVisible();
  expect(await page.evaluate(() => window.calls)).toEqual([
    { method: 'getwalletinfo', params: [], wallet: '' },
    { method: 'signmessage', params: ['ecregtest:qkey', message], wallet: '' },
    { method: 'verifymessage', params: ['ecregtest:qkey', COMPACT_SIGNATURE, message] },
  ]);
});

test('locked wallet unlocks only for signing, relocks, and clears passphrase', async ({ page }) => {
  await mount(page, 'messages', { locked: true });
  await page.getByLabel('Signing address', { exact: true }).fill('ecregtest:qkey');
  await page.getByRole('button', { name: 'Sign message', exact: true }).click();
  await page.getByLabel('Wallet passphrase', { exact: true }).fill('temporary-secret');
  await page.getByRole('button', { name: 'Unlock and sign', exact: true }).click();
  await expect(page.getByTestId('signed-message')).toBeVisible();
  expect(await page.evaluate(() => window.calls.map((c) => c.method))).toEqual(['getwalletinfo', 'walletpassphrase', 'signmessage', 'verifymessage', 'walletlock']);
  expect(await page.evaluate(() => window.calls.filter((c) => c.method !== 'verifymessage').every((c) => c.wallet === ''))).toBe(true);
  expect(await page.evaluate(() => Object.values(localStorage).some((v) => v.includes('temporary-secret')))).toBe(false);
  await expect(page.getByLabel('Wallet passphrase', { exact: true })).toHaveCount(0);
});

test('unsupported signing address is reported and temporarily unlocked wallet still relocks', async ({ page }) => {
  await mount(page, 'messages', { locked: true, fail: 'signmessage', failureMessage: 'Address does not refer to key' });
  await page.getByLabel('Signing address', { exact: true }).fill('xpi-native');
  await page.getByRole('button', { name: 'Sign message', exact: true }).click();
  await page.getByLabel('Wallet passphrase', { exact: true }).fill('temporary-secret');
  await page.getByRole('button', { name: 'Unlock and sign', exact: true }).click();
  await expect(page.getByRole('dialog').getByRole('alert')).toContainText('Address does not refer to key');
  await expect(page.getByLabel('Wallet passphrase', { exact: true })).toHaveValue('');
  expect(await page.evaluate(() => window.calls.map((c) => c.method))).toEqual(['getwalletinfo', 'walletpassphrase', 'signmessage', 'walletlock']);
});

test('relock failure is visible even after successful signing', async ({ page }) => {
  await mount(page, 'messages', { locked: true, fail: 'walletlock' });
  await page.getByLabel('Signing address', { exact: true }).fill('ecregtest:qkey');
  await page.getByRole('button', { name: 'Sign message', exact: true }).click();
  await page.getByLabel('Wallet passphrase', { exact: true }).fill('temporary-secret');
  await page.getByRole('button', { name: 'Unlock and sign', exact: true }).click();
  await expect(page.getByTestId('signed-message')).toBeVisible();
  await expect(page.getByRole('alert')).toContainText('Could not relock the wallet');
});

test('verification works without any wallet and sends the exact message', async ({ page }) => {
  await mount(page, 'messages', { noWallet: true });
  await expect(page.getByRole('tab', { name: 'Verify message', exact: true })).toHaveAttribute('aria-selected', 'true');
  await page.getByRole('tab', { name: 'Sign message', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Sign message', exact: true })).toBeDisabled();
  await page.getByRole('tab', { name: 'Verify message', exact: true }).click();
  await page.getByLabel('Verification address', { exact: true }).fill('ecregtest:qkey');
  await page.getByLabel('Signature to verify', { exact: true }).fill('compact-signature==');
  const message = ' \n exact text \n';
  await page.getByLabel('Message to verify', { exact: true }).fill(message);
  await page.getByRole('button', { name: 'Verify message', exact: true }).click();
  await expect(page.getByRole('status')).toContainText('Valid signature');
  expect(await page.evaluate(() => window.calls)).toEqual([{ method: 'verifymessage', params: ['ecregtest:qkey', 'compact-signature==', message] }]);
  await page.getByLabel('Message to verify', { exact: true }).fill('changed');
  await expect(page.getByRole('status')).toHaveCount(0);
});

test('verification rejects mismatches clearly', async ({ page }) => {
  await mount(page, 'messages', { verify: false });
  await page.getByRole('tab', { name: 'Verify message', exact: true }).click();
  await page.getByLabel('Verification address', { exact: true }).fill('ecregtest:qkey');
  await page.getByLabel('Signature to verify', { exact: true }).fill('wrong-signature==');
  await page.getByRole('button', { name: 'Verify message', exact: true }).click();
  await expect(page.getByRole('status')).toContainText('Signature does not match');
});


for (const size of [{ width: 1280, height: 720 }, { width: 1440, height: 900 }]) {
  test(`desktop shell keeps navigation and status visible while content scrolls at ${size.width}`, async ({ page }) => {
    await page.setViewportSize(size);
    await mount(page, 'wallets', { shell: true, long: true });
    await expect(page.getByRole('button', { name: 'Create default wallet', exact: true })).toBeEnabled();
    const before = await page.locator('.sidebar').boundingBox();
    await page.locator('#content-39').scrollIntoViewIfNeeded();
    const after = await page.locator('.sidebar').boundingBox();
    expect(after.y).toBe(before.y);
    await expect(page.getByRole('link', { name: 'Overview', exact: true })).toBeInViewport();
    await expect(page.locator('.topbar')).toBeInViewport();
    await expect(page.locator('.statusbar')).toBeInViewport();
    await expect(page.locator('#content-39')).toBeInViewport();
    expect(await page.locator('.content').evaluate((e) => e.scrollTop)).toBeGreaterThan(0);
    expect(await page.evaluate(() => document.documentElement.scrollHeight)).toBe(size.height);
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(size.width);
    // Keyboard users can focus the scroll area and reach its last control.
    await page.locator('.content').focus();
    await page.keyboard.press('Control+End');
    await expect(page.locator('#content-39')).toBeInViewport();
  });
}

test('wallet management and both creation actions fit a laptop viewport', async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 1280, height: 720 });
  await mount(page, 'wallets', { shell: true });
  await expect(page.getByRole('button', { name: 'Create default wallet', exact: true })).toBeEnabled();
  await expect(page.getByRole('button', { name: 'Create wallet', exact: true })).toBeInViewport();
  await expect(page.getByLabel('Wallet name', { exact: true })).toBeInViewport();
  await expect(page.getByRole('heading', { name: 'Open wallets', exact: true })).toBeInViewport();
  await page.screenshot({ path: testInfo.outputPath('wallets-laptop.png'), fullPage: true });
});

test('mobile layout stacks wallet controls and keeps final controls reachable without page overflow', async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await mount(page, 'wallets', { shell: true, long: true });
  await expect(page.getByRole('button', { name: 'Create default wallet', exact: true })).toBeEnabled();
  await page.locator('#content-39').scrollIntoViewIfNeeded();
  await expect(page.locator('#content-39')).toBeInViewport();
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(390);
  await page.getByRole('link', { name: 'Node', exact: true }).focus();
  await expect(page.getByRole('link', { name: 'Node', exact: true })).toBeInViewport();
  expect(await page.getByRole('link', { name: 'Node', exact: true }).evaluate((e) => e.getBoundingClientRect().height)).toBeGreaterThanOrEqual(44);
  await page.screenshot({ path: testInfo.outputPath('wallets-mobile.png'), fullPage: false });
});


test('message tabs preserve both forms and support arrow Home and End navigation', async ({ page }) => {
  await mount(page, 'messages');
  await page.getByLabel('Signing address', { exact: true }).fill('ecregtest:qkey');
  await page.getByLabel('Message to sign', { exact: true }).fill('sign text');
  await page.getByRole('tab', { name: 'Verify message', exact: true }).click();
  await expect(page.getByRole('tabpanel')).toHaveCount(1);
  await page.getByLabel('Message to verify', { exact: true }).fill('verify text');
  await page.getByRole('tab', { name: 'Verify message', exact: true }).focus();
  await page.keyboard.press('ArrowLeft');
  await expect(page.getByRole('tab', { name: 'Sign message', exact: true })).toBeFocused();
  await expect(page.getByLabel('Message to sign', { exact: true })).toHaveValue('sign text');
  await expect(page.getByLabel('Signing address', { exact: true })).toHaveValue('ecregtest:qkey');
  await page.keyboard.press('End');
  await expect(page.getByRole('tab', { name: 'Verify message', exact: true })).toBeFocused();
  await expect(page.getByLabel('Message to verify', { exact: true })).toHaveValue('verify text');
  await page.keyboard.press('Home');
  await expect(page.getByRole('tab', { name: 'Sign message', exact: true })).toBeFocused();
  await page.keyboard.press('ArrowRight');
  await expect(page.getByRole('tab', { name: 'Verify message', exact: true })).toHaveAttribute('aria-selected', 'true');
});


test('mining is opt-in and unavailable GPU does not fake counts or disable explicit regtest controls', async ({ page }) => {
  await mount(page, 'mining', { disableGpu: true });
  expect(await page.evaluate(() => window.calls)).toEqual([]);
  await expect(page.getByRole('button', { name: 'Start GPU mining', exact: true })).toBeDisabled();
  await expect(page.getByRole('button', { name: 'Mine 1 test block', exact: true })).toBeDisabled();
  await page.getByRole('button', { name: 'Create payout address', exact: true }).click();
  await expect(page.getByLabel('Payout address', { exact: true })).toHaveValue('ecregtest:qqtestaddress');
  await page.getByRole('button', { name: 'Mine 1 test block', exact: true }).click();
  await expect(page.getByRole('status').filter({ hasText: 'Generated 1 test block.' })).toBeVisible();
  await page.getByRole('button', { name: 'Mine 101 test blocks', exact: true }).click();
  await expect(page.getByRole('status').filter({ hasText: 'Generated 101 test blocks.' })).toBeVisible();
  expect(await page.evaluate(() => window.calls.filter((c) => c.method === 'generatetoaddress').map((c) => c.params))).toEqual([[1, 'ecregtest:qqtestaddress'], [101, 'ecregtest:qqtestaddress']]);
  expect(await page.evaluate(() => window.calls.filter((c) => c.method === 'getnewaddress')[0].wallet)).toBe('');
  await expect(page.locator('.mining')).toContainText('not browser GPU hashing');
});

test('instant mining is absent on mainnet and stale regtest state cannot trigger mainnet generation', async ({ page }) => {
  await mount(page, 'mining', { chain: 'main' });
  await expect(page.getByRole('button', { name: 'Mine 1 test block', exact: true })).toHaveCount(0);
  await mount(page, 'mining', { actualChain: 'main' });
  await page.getByLabel('Payout address', { exact: true }).fill('address');
  await page.getByRole('button', { name: 'Mine 1 test block', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('only on regtest');
  expect(await page.evaluate(() => window.calls.some((c) => c.method === 'generatetoaddress'))).toBe(false);
});


test('GPU mining starts only on click and hiding the tab stops it without auto-resume', async ({ page }) => {
  const header = new Uint8Array(80); header.fill(0xab, 4, 36); new DataView(header.buffer).setUint32(72, 0x207fffff, true);
  const pow = { version: 1, algorithm: 'sha256d', headerbytes: 80, nonceoffset: 76, noncebytes: 4, noncebyteorder: 'little', hashbyteorder: 'little', targetbyteorder: 'big', template_rpc: 'getrawunsolvedblock', submit_rpc: 'submitblock' };
  const rawTemplate = { blockhex: Buffer.from(header).toString('hex') + '0100', target: '7fffff' + '00'.repeat(29) };
  await mount(page, 'mining', { fakeWorker: true, pow, rawTemplate });
  await page.getByLabel('Payout address', { exact: true }).fill('payout');
  expect(await page.evaluate(() => window.workerStarts)).toBe(0);
  await page.getByRole('button', { name: 'Start GPU mining', exact: true }).click();
  await expect.poll(() => page.evaluate(() => window.workerStarts)).toBe(1);
  await page.evaluate(() => { Object.defineProperty(document, 'hidden', { configurable: true, value: true }); document.dispatchEvent(new Event('visibilitychange')); });
  await expect(page.getByRole('button', { name: 'Stop mining', exact: true })).toBeDisabled();
  await expect(page.getByRole('status').filter({ hasText: 'Paused because this tab is hidden' })).toBeVisible();
  await page.evaluate(() => { Object.defineProperty(document, 'hidden', { configurable: true, value: false }); document.dispatchEvent(new Event('visibilitychange')); });
  expect(await page.evaluate(() => window.workerStarts)).toBe(1);
  expect(await page.evaluate(() => window.workerStops)).toBe(1);
  await expect(page.getByRole('button', { name: 'Start GPU mining', exact: true })).toBeEnabled();
});
