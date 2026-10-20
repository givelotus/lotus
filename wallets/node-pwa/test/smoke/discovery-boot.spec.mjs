// Actual app boot with one authoritative discovery RPC; no daemon needed.
import { test, expect } from '@playwright/test';
import { fileURLToPath } from 'node:url';
import { createDevServer } from '../../tools/devserver.mjs';
import { chainDiscovery } from '../helpers/chain-discovery.mjs';
let server;
let base;
test.beforeAll(async () => {
  ({ server } = createDevServer({ root: fileURLToPath(new URL('../../src/', import.meta.url)), rpcUrl: 'http://127.0.0.1:1', auth: 'proxy' }));
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  base = `http://127.0.0.1:${server.address().port}/wallet/`;
});
test.afterAll(async () => { server.closeAllConnections(); await new Promise((resolve) => server.close(resolve)); });
async function mockNode(page, state) {
  const calls = [];
  await page.route('**/*', async (route) => {
    const request = route.request();
    if (request.method() !== 'POST') return route.continue();
    const payload = request.postDataJSON();
    const reply = ({ method, id }) => {
      calls.push(method);
      let result;
      let error = null;
      if (method === 'getchainconfig') {
        if (state.missing) error = { code: -32601, message: 'Method not found' };
        else result = state.discovery;
      } else if (method === 'listwallets') result = [];
      else if (method === 'getblockchaininfo') result = { chain: state.discovery.chain.network, blocks: 0, headers: 0, bestblockhash: 'ab'.repeat(32), verificationprogress: 1, initialblockdownload: false };
      else if (method === 'getnetworkinfo') result = { networkactive: true, connections: 0, subversion: '/Node:1.0/', version: 1 };
      else error = { code: -32601, message: 'Mock method not implemented' };
      return { result: result ?? null, error, id };
    };
    await route.fulfill({ contentType: 'application/json', body: JSON.stringify(Array.isArray(payload) ? payload.map(reply) : reply(payload)) });
  });
  return calls;
}
test('full UI boot discovers identity/capabilities once without currency/header/address probes', async ({ page }) => {
  const calls = await mockNode(page, { discovery: chainDiscovery({ native: true }) });
  await page.goto(base);
  await expect(page.getByTestId('no-wallet')).toBeVisible();
  await page.evaluate(() => window.nodePwa.poller.stop());
  expect(calls.filter((m) => m === 'getchainconfig')).toHaveLength(1);
  for (const method of ['getcurrencyinfo', 'getmininginfo', 'getblockhash', 'getblockheader', 'validateaddress']) expect(calls).not.toContain(method);
  expect(await page.evaluate(async () => {
    const current = nodePwa.store.get().profile;
    return current === await nodePwa.chainAdaptor.discover() && Object.isFrozen(current) && current.currency.rpcDecimals === 6;
  })).toBe(true);
});
test('missing or unsupported discovery is explicit, with no fallback or automatic retry', async ({ page }) => {
  const state = { discovery: chainDiscovery(), missing: true };
  const calls = await mockNode(page, state);
  await page.goto(base);
  await expect(page.getByTestId('unsupported-node')).toContainText('does not support getchainconfig');
  expect(calls).toEqual(['getchainconfig']);
  state.missing = false; state.discovery.version = 99;
  await page.getByRole('button', { name: 'Retry discovery', exact: true }).click();
  await expect(page.getByTestId('unsupported-node')).toContainText('schema version');
  expect(calls).toEqual(['getchainconfig', 'getchainconfig']);
});
test('reconnect replaces the connection singleton and clears stale wallet state when genesis changes', async ({ page }) => {
  const state = { discovery: chainDiscovery() };
  const calls = await mockNode(page, state);
  await page.goto(base);
  await expect(page.getByTestId('no-wallet')).toBeVisible();
  await page.evaluate(() => {
    nodePwa.poller.stop(); window.oldConfig = nodePwa.store.get().profile;
    nodePwa.store.set({ balances: { stale: true }, walletInfo: { stale: true }, txs: [{ stale: true }] });
  });
  state.discovery = chainDiscovery({ genesis: 'cd'.repeat(32) });
  await page.evaluate(() => nodePwa.retryNow());
  await expect.poll(() => page.evaluate(() => nodePwa.store.get().profile?.network.genesis)).toBe('cd'.repeat(32));
  await page.evaluate(() => nodePwa.poller.stop());
  expect(await page.evaluate(() => {
    const s = nodePwa.store.get();
    return s.profile !== window.oldConfig && s.balances === null && s.walletInfo === null && s.txs === null && s.wallet === null;
  })).toBe(true);
  expect(calls.filter((m) => m === 'getchainconfig')).toHaveLength(2);
});
