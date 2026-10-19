// End-to-end smoke test: a real regtest lotusd, the dev server, and headless
// Chrome. Skips (with a message) unless LOTUSD points at a lotusd binary.
// Amounts stay small so it also runs on chains with a low regtest subsidy.

import { test, expect } from '@playwright/test';
import { execFileSync } from 'node:child_process';
import { mkdtempSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { startNode, freePort } from './regtest.mjs';
import { createDevServer } from '../../tools/devserver.mjs';
import { buildBundle } from '../../tools/pack.mjs';

const LOTUSD = process.env.LOTUSD;
const SRC = fileURLToPath(new URL('../../src/', import.meta.url));

test.describe.configure({ mode: 'serial' });
test.skip(!LOTUSD, 'set LOTUSD=/path/to/lotusd to run the smoke test');

let node;
const servers = [];

async function serve({ auth = 'proxy', root = SRC, port } = {}) {
  const dev = createDevServer({ root, rpcUrl: node.rpcUrl, auth, cookieFile: node.cookieFile });
  const p = port ?? (await freePort());
  await new Promise((r) => dev.server.listen(p, '127.0.0.1', r));
  const close = () => new Promise((r) => { dev.server.closeAllConnections(); dev.server.close(r); });
  const s = { dev, port: p, base: `http://127.0.0.1:${p}/wallet/`, close };
  servers.push(s);
  return s;
}

function trackErrors(page) {
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  page.on('console', (m) => { if (m.type() === 'error' && !/Failed to load resource|ERR_CONNECTION_REFUSED|net::ERR/.test(m.text())) errors.push(m.text()); });
  return errors;
}

async function go(page, base, view, wallet) {
  await page.goto(`${base}#/${view}${wallet !== undefined ? `?w=${encodeURIComponent(wallet)}` : ''}`);
}

async function consoleRun(page, line) {
  const input = page.getByTestId('console-input');
  await expect(input).toBeEnabled();
  await input.fill(line);
  await input.press('Enter');
  await expect(input).toBeEnabled({ timeout: 60000 });
}

async function newAddress(page, label) {
  await page.getByRole('link', { name: 'Receive', exact: true }).click();
  await page.getByLabel('Label', { exact: true }).fill(label);
  await page.getByRole('button', { name: 'Create payment request' }).click();
  const addr = (await page.getByTestId('request-address').textContent()).trim();
  await expect(page.locator('svg.qr')).toBeVisible();
  await page.getByRole('button', { name: 'Close' }).click();
  return addr;
}

async function send(page, address, amount, { subtractFee = false, passphrase } = {}) {
  await page.getByRole('link', { name: 'Send', exact: true }).click();
  await page.getByLabel('Pay to').fill(address);
  await expect(page.locator('.address-status')).toHaveText('✓ valid');
  await page.getByLabel(/^Amount/).fill(amount);
  if (subtractFee) await page.getByLabel('Subtract fee from amount').check();
  await page.getByRole('button', { name: 'Review' }).click();
  await expect(page.getByRole('dialog', { name: 'Confirm payment' })).toBeVisible();
  // The preview uses walletcreatefundedpsbt; nodes without it show the fallback text.
  await expect(page.getByTestId('fee-preview')).toContainText(/\d|calculated when sent/);
  if (passphrase !== undefined) await page.getByLabel('Wallet passphrase').fill(passphrase);
  await page.getByTestId('confirm-send').click();
  const txid = (await page.getByTestId('sent-txid').textContent()).trim();
  expect(txid).toMatch(/^[0-9a-f]{64}$/);
  return txid;
}

test.beforeAll(async () => {
  node = await startNode(LOTUSD);
});

test.afterAll(async () => {
  for (const s of servers) await s.close().catch(() => {});
  await node?.stop();
  if (node && !process.env.NODE_PWA_SMOKE_KEEP) rmSync(node.datadir, { recursive: true, force: true });
});

test('dev proxy: create a wallet, mine, receive, send, inspect, peers, console', async ({ page }) => {
  const errors = trackErrors(page);
  const { base } = await serve();
  await page.goto(base);

  // 1. Empty-wallet prompt, then create w1 through the UI.
  await expect(page.getByTestId('no-wallet')).toBeVisible();
  await page.getByRole('link', { name: 'Create or open a wallet' }).click();
  await page.getByLabel('Wallet name').fill('w1');
  await page.getByRole('button', { name: 'Create wallet' }).click();
  await expect(page.getByTestId('wallet-picker')).toHaveText(/w1/);
  await expect(page).toHaveURL(/\?w=w1$/);

  // 2. Mine to an address from the Receive view, through the console.
  const mining = await newAddress(page, 'mining');
  await page.getByRole('link', { name: 'Console', exact: true }).click();
  await consoleRun(page, `generatetoaddress 101 ${mining}`);
  await expect(page.getByTestId('console-output')).toContainText(/"[0-9a-f]{64}"\s*\]/);
  await consoleRun(page, 'help getblockcount');
  await expect(page.getByTestId('console-output')).toContainText('getblockcount');
  await consoleRun(page, 'getblock(getbestblockhash())[height]');
  await expect(page.locator('.console-out pre.result').last()).toHaveText('101');
  const input = page.getByTestId('console-input');
  await input.press('ArrowUp');
  await expect(input).toHaveValue('getblock(getbestblockhash())[height]');
  await input.press('ArrowUp');
  await expect(input).toHaveValue('help getblockcount');

  // 3. Mature balance on the overview.
  await page.getByRole('link', { name: 'Overview', exact: true }).click();
  await expect(page.getByTestId('balance-available')).toContainText(/[1-9]/);

  // 4. Send to a second new address with "subtract fee"; see it in the list and details.
  const dest = await newAddress(page, 'dest');
  const txid = await send(page, dest, '100.00', { subtractFee: true });
  await page.getByRole('link', { name: 'Transactions', exact: true }).click();
  await expect(page.getByTestId('tx-table')).toContainText('dest');
  await page.getByTestId('tx-table').getByRole('row').filter({ hasText: 'sent' }).first().click();
  await expect(page.getByTestId('tx-detail')).toContainText(txid);
  await expect(page.getByTestId('tx-detail')).toContainText('unconfirmed');
  await page.getByRole('button', { name: 'Close' }).click();
  const tx = await node.rpc('gettransaction', [txid], 'w1');
  expect(tx.details.some((d) => d.address === dest)).toBe(true);

  // 5. A payment URI pasted into the address field fills amount and label.
  await page.getByRole('link', { name: 'Send', exact: true }).click();
  await page.getByLabel('Pay to').fill(`${dest}?amount=12.5&label=Shop`);
  await expect(page.getByLabel('Pay to')).toHaveValue(dest);
  await expect(page.getByLabel(/^Amount/)).toHaveValue('12.5');
  await expect(page.getByLabel('Label', { exact: true })).toHaveValue('Shop');
  await page.getByLabel(/^Amount/).fill('1.0000000001');
  await page.getByRole('button', { name: 'Review' }).click();
  await expect(page.locator('.field-error')).toContainText(/at most \d+ decimal places/);

  // 6. Peers: empty tables; the status-bar switch toggles network activity.
  await page.getByRole('link', { name: 'Peers', exact: true }).click();
  await expect(page.getByTestId('no-peers')).toBeVisible();
  await expect(page.getByTestId('no-bans')).toBeVisible();
  await page.getByTestId('network-toggle').click();
  await expect(page.getByTestId('network-toggle')).toHaveText('Network off');
  expect((await node.rpc('getnetworkinfo')).networkactive).toBe(false);
  await page.getByTestId('network-toggle').click();
  await expect(page.getByTestId('network-toggle')).toHaveText('Network on');
  // No peers exist on an isolated node, so bans are added over RPC and removed in the UI.
  await node.rpc('setban', ['203.0.113.9', 'add', 3600]);
  await node.rpc('setban', ['198.51.100.0/24', 'add', 3600]);
  await expect(page.getByTestId('ban-table')).toContainText('203.0.113.9');
  await page.getByTestId('ban-table').getByRole('row').filter({ hasText: '203.0.113.9' }).getByRole('button', { name: 'Unban' }).click();
  await expect(page.getByTestId('ban-table')).not.toContainText('203.0.113.9');
  await page.getByRole('button', { name: 'Clear all' }).click();
  await expect(page.getByTestId('no-bans')).toBeVisible();
  expect(await node.rpc('listbanned')).toEqual([]);

  // 7. Node view renders chain data.
  await page.getByRole('link', { name: 'Node', exact: true }).click();
  await expect(page.locator('.node')).toContainText('regtest');

  expect(errors).toEqual([]);
});

test('dev proxy: encrypted wallet asks for the passphrase and locks again', async ({ page }) => {
  const errors = trackErrors(page);
  const { base } = await serve();
  await go(page, base, 'wallets', 'w1');
  await page.getByLabel('Wallet name').fill('w2');
  await page.getByLabel(/^Passphrase/).fill('correct horse');
  await page.getByLabel('Repeat passphrase').fill('correct horse');
  await page.getByRole('button', { name: 'Create wallet' }).click();
  await expect(page).toHaveURL(/\?w=w2$/);
  await expect(page.locator('.topbar')).toContainText('Locked');
  const w2addr = await newAddress(page, 'from w1');

  // Fund w2 from w1 and confirm it.
  await page.getByTestId('wallet-picker').selectOption({ label: 'w1' });
  await expect(page).toHaveURL(/\?w=w1$/);
  await send(page, w2addr, '50.00');
  await node.rpc('generatetoaddress', [1, w2addr]);

  // Spend from w2: wrong passphrase first, then the right one.
  await page.getByTestId('wallet-picker').selectOption({ label: 'w2' });
  await page.getByRole('link', { name: 'Send', exact: true }).click();
  await page.getByLabel('Pay to').fill(w2addr);
  await expect(page.locator('.address-status')).toHaveText('✓ valid');
  await page.getByLabel(/^Amount/).fill('10.00');
  await page.getByRole('button', { name: 'Review' }).click();
  await page.getByLabel('Wallet passphrase').fill('wrong');
  await page.getByTestId('confirm-send').click();
  await expect(page.getByRole('dialog')).toContainText('passphrase is incorrect');
  await page.getByLabel('Wallet passphrase').fill('correct horse');
  await page.getByTestId('confirm-send').click();
  await expect(page.getByTestId('sent-txid')).toHaveText(/^[0-9a-f]{64}$/);
  expect(Number((await node.rpc('getwalletinfo', [], 'w2')).unlocked_until)).toBe(0);
  expect(errors).toEqual([]);
});

test('session mode: login link, cookie session, logout, password login, offline shell', async ({ page }) => {
  const errors = trackErrors(page);
  const s = await serve({ auth: 'session' });
  const token = s.dev.mintToken();
  await page.goto(`${s.base}#/login/${token}`);
  await expect(page.getByTestId('wallet-picker')).toBeVisible();
  expect(page.url()).not.toContain(token);
  await expect(page.locator('.topbar')).toContainText('Log out');

  // The session survives a reload (the CSRF token is fetched again).
  await page.reload();
  await expect(page.getByTestId('balance-available')).toBeVisible();

  // The link worked once only.
  await page.getByRole('button', { name: 'Log out' }).click();
  await page.goto(`${s.base}#/login/${token}`);
  await expect(page.getByRole('alert')).toContainText('Login link not accepted');

  // Password login with the pasted cookie line.
  const cookieLine = (await import('node:fs')).readFileSync(node.cookieFile, 'utf8').trim();
  await page.getByLabel('Password or cookie line').fill('nope:nope');
  await page.getByRole('button', { name: 'Log in' }).click();
  await expect(page.getByRole('alert')).toContainText('login failed');
  await page.getByLabel('Password or cookie line').fill(cookieLine);
  await page.getByRole('button', { name: 'Log in' }).click();
  await expect(page.getByTestId('wallet-picker')).toBeVisible();

  // Offline: with the server gone, a reload is served by the service worker.
  await page.evaluate(() => navigator.serviceWorker.ready);
  await page.reload();
  await page.evaluate(() => navigator.serviceWorker.ready);
  await expect.poll(() => page.evaluate(() => !!navigator.serviceWorker.controller)).toBe(true);
  await s.close();
  await page.reload();
  await expect(page.getByTestId('offline')).toBeVisible();

  // Restart on the same port: it reconnects by itself and asks for a new login.
  await serve({ auth: 'session', port: s.port });
  await expect(page.getByRole('button', { name: 'Log in' })).toBeVisible({ timeout: 45000 });
  expect(errors).toEqual([]);
});

test('packed release bundle serves and caches under its version', async ({ page }) => {
  const errors = trackErrors(page);
  const dir = mkdtempSync(join(process.env.NODE_PWA_SMOKE_TMP ?? tmpdir(), 'node-pwa-bundle-'));
  try {
    const { tarball } = buildBundle({ srcDir: SRC, version: '0.1.0', sourceCommit: 'b'.repeat(40) });
    writeFileSync(join(dir, 'bundle.tar.gz'), tarball);
    execFileSync('tar', ['-xzf', join(dir, 'bundle.tar.gz'), '-C', dir]);
    const { base } = await serve({ root: join(dir, 'node-pwa') });
    await go(page, base, 'overview', 'w1');
    await expect(page.getByTestId('balance-available')).toContainText(/[1-9]/);
    await page.evaluate(() => navigator.serviceWorker.ready);
    await expect.poll(() => page.evaluate(() => caches.keys())).toContain('node-pwa-0.1.0');
    await expect.poll(() => page.evaluate(async () => (await (await caches.open('node-pwa-0.1.0')).keys()).length)).toBeGreaterThan(30);
    expect(errors).toEqual([]);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});
