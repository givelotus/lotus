// Boot: session → profile → router → poller.

import { html, render, useEffect, useState } from './vendor/htm-preact-standalone.mjs';
import { createApp } from './app.js';
import { parseRoute } from './router.js';
import { tokenFromHash } from './lib/session.js';
import { useStore } from './ui/components.js';
import { Sidebar, TopBar, StatusBar, Toasts, UpdateBanner } from './ui/layout.js';
import { LoginView } from './views/login.js';
import { OfflineView, WarmupView, BootView } from './views/offline.js';
import { OverviewView } from './views/overview.js';
import { SendView } from './views/send.js';
import { ReceiveView } from './views/receive.js';
import { TransactionsView } from './views/transactions.js';
import { PeersView } from './views/peers.js';
import { ConsoleView } from './views/console.js';
import { NodeView } from './views/nodeinfo.js';
import { WalletsView } from './views/wallets.js';

const app = createApp();

function useRoute() {
  const [route, setRoute] = useState(parseRoute(location.hash));
  useEffect(() => {
    const on = () => setRoute(parseRoute(location.hash));
    addEventListener('hashchange', on);
    return () => removeEventListener('hashchange', on);
  }, []);
  return route;
}

const VIEWS = {
  overview: OverviewView,
  send: SendView,
  receive: ReceiveView,
  transactions: TransactionsView,
  tx: TransactionsView,
  peers: PeersView,
  console: ConsoleView,
  node: NodeView,
  wallets: WalletsView,
  login: OverviewView,
};

function Root() {
  const state = useStore(app.store);
  const route = useRoute();
  useEffect(() => {
    // Follow wallet changes made through links (?w=...).
    if (state.phase === 'ready' && route.wallet !== null && route.wallet !== state.wallet && (state.wallets ?? []).includes(route.wallet)) {
      app.selectWallet(route.wallet);
    }
  }, [route.wallet, state.phase]);

  if (state.phase === 'boot') return html`<${BootView} />`;
  if (state.phase === 'login') return html`<${LoginView} app=${app} state=${state} />`;
  if (state.phase === 'offline') return html`<${OfflineView} app=${app} state=${state} />`;
  if (state.phase === 'warmup') return html`<${WarmupView} state=${state} />`;
  const View = VIEWS[route.view] ?? OverviewView;
  return html`
    <div class="shell">
      <${Sidebar} app=${app} state=${state} route=${route} />
      <div class="main-col">
        <${TopBar} app=${app} state=${state} />
        <${UpdateBanner} state=${state} />
        ${state.warmup ? html`<div class="banner info">${state.warmup}</div>` : null}
        <main class="content" key=${`${route.view === 'tx' ? 'transactions' : route.view}|${state.wallet}`}>
          <${View} app=${app} state=${state} route=${route} />
        </main>
        <${StatusBar} app=${app} state=${state} />
      </div>
      <${Toasts} state=${state} />
    </div>`;
}

render(html`<${Root} />`, document.getElementById('app'));
app.boot();

// A login link opened in an already-open tab only changes the hash.
addEventListener('hashchange', () => {
  if (tokenFromHash(location.hash)) app.boot();
});

// Installability and offline shell.
addEventListener('beforeinstallprompt', (e) => {
  e.preventDefault();
  app.store.set({ installPrompt: e });
});

if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/wallet/sw.js', { scope: '/wallet/' }).then((reg) => {
    const watch = (sw) => sw?.addEventListener('statechange', () => {
      if (sw.state === 'installed' && navigator.serviceWorker.controller) app.store.set({ swUpdate: true });
    });
    if (reg.waiting && navigator.serviceWorker.controller) app.store.set({ swUpdate: true });
    watch(reg.installing);
    reg.addEventListener('updatefound', () => watch(reg.installing));
  }).catch((e) => console.warn('service worker registration failed', e));
  let reloading = false;
  navigator.serviceWorker.addEventListener('controllerchange', () => {
    if (reloading || !app.store.get().swUpdate) return;
    reloading = true;
    location.reload();
  });
}

// Visible for debugging from the browser devtools only.
globalThis.nodePwa = app;
