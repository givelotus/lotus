// Component-level browser checks with mocked RPCs; no daemon or wallet data.
import { test, expect } from '@playwright/test';
import { fileURLToPath } from 'node:url';
import { createDevServer } from '../../tools/devserver.mjs';

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
  await page.evaluate(async ({ kind, config }) => {
    const { html, render } = await import('/wallet/vendor/htm-preact-standalone.mjs');
    const { WalletsView } = await import('/wallet/views/wallets.js');
    const { StatusBar } = await import('/wallet/ui/layout.js');
    const { ReceiveView } = await import('/wallet/views/receive.js');
    const { MessagesView } = await import('/wallet/views/messages.js');
    window.calls = [];
    window.selected = null;
    window.refreshed = 0;
    const state = { wallets: config.loaded ?? [], wallet: kind === 'receive' || (kind === 'messages' && !config.noWallet) ? '' : null, net: { networkactive: true }, profile: { ticker: 'XEC', decimals: 2, addressFormat: 'cashaddr' } };
    const draw = () => render(html`<${kind === 'wallets' ? WalletsView : kind === 'receive' ? ReceiveView : kind === 'messages' ? MessagesView : StatusBar} app=${app} state=${state} />`, document.getElementById('root'));
    const app = {
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
        if (method === 'getwalletinfo') return config.locked ? { unlocked_until: 0 } : {};
        if (method === 'signmessage') return 'compact-signature==';
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
    draw();
  }, { kind, config });
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
  await expect(page.getByTestId('signed-message')).toContainText('compact-signature==');
  await expect(page.getByRole('button', { name: 'Copy signature', exact: true })).toBeVisible();
  expect(await page.evaluate(() => window.calls)).toEqual([
    { method: 'getwalletinfo', params: [], wallet: '' },
    { method: 'signmessage', params: ['ecregtest:qkey', message], wallet: '' },
  ]);
});

test('locked wallet unlocks only for signing, relocks, and clears passphrase', async ({ page }) => {
  await mount(page, 'messages', { locked: true });
  await page.getByLabel('Signing address', { exact: true }).fill('ecregtest:qkey');
  await page.getByRole('button', { name: 'Sign message', exact: true }).click();
  await page.getByLabel('Wallet passphrase', { exact: true }).fill('temporary-secret');
  await page.getByRole('button', { name: 'Unlock and sign', exact: true }).click();
  await expect(page.getByTestId('signed-message')).toBeVisible();
  expect(await page.evaluate(() => window.calls.map((c) => c.method))).toEqual(['getwalletinfo', 'walletpassphrase', 'signmessage', 'walletlock']);
  expect(await page.evaluate(() => window.calls.every((c) => c.wallet === ''))).toBe(true);
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
  await expect(page.getByRole('button', { name: 'Sign message', exact: true })).toBeDisabled();
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
  await page.getByLabel('Verification address', { exact: true }).fill('ecregtest:qkey');
  await page.getByLabel('Signature to verify', { exact: true }).fill('wrong-signature==');
  await page.getByRole('button', { name: 'Verify message', exact: true }).click();
  await expect(page.getByRole('status')).toContainText('Signature does not match');
});
