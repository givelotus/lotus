// Regression: boot may finish before useEffect subscribes to the store.
import { test, expect } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { createDevServer } from '../../tools/devserver.mjs';
test('store updates between first render and effect subscription remain observable', async ({ page }) => {
  const { server } = createDevServer({ root: fileURLToPath(new URL('../../src/', import.meta.url)), rpcUrl: 'http://127.0.0.1:1', auth: 'proxy' });
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  try {
    await page.route('**/wallet/test.html', (route) => route.fulfill({ contentType: 'text/html', body: '<!doctype html><div id="root"></div>' }));
    if (process.env.PWA_COMPONENTS_BEFORE) await page.route('**/wallet/ui/components.js', (route) => route.fulfill({ contentType: 'text/javascript', body: readFileSync(process.env.PWA_COMPONENTS_BEFORE, 'utf8') }));
    await page.goto(`http://127.0.0.1:${server.address().port}/wallet/test.html`);
    await page.evaluate(async () => {
      const { html, render } = await import('/wallet/vendor/htm-preact-standalone.mjs');
      const { useStore } = await import('/wallet/ui/components.js');
      const { createStore } = await import('/wallet/lib/store.js');
      const store = createStore({ value: 'Connecting' });
      const View = () => html`<p role="status">${useStore(store).value}</p>`;
      render(html`<${View} />`, document.getElementById('root'));
      store.set({ value: 'Finished before subscription' });
    });
    await expect(page.getByRole('status')).toHaveText('Finished before subscription', { timeout: 1000 });
  } finally { server.closeAllConnections(); await new Promise((resolve) => server.close(resolve)); }
});
