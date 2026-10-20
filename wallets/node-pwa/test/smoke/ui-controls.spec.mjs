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
    window.calls = [];
    window.selected = null;
    window.refreshed = 0;
    const state = { wallets: config.loaded ?? [], wallet: kind === 'receive' ? '' : null, net: { networkactive: true }, profile: { ticker: 'XEC', decimals: 2, addressFormat: 'cashaddr' } };
    const draw = () => render(html`<${kind === 'wallets' ? WalletsView : kind === 'receive' ? ReceiveView : StatusBar} app=${app} state=${state} />`, document.getElementById('root'));
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
      rpc: { async call(method, params) {
        window.calls.push({ method, params });
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
