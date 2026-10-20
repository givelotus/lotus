// App frame: sidebar navigation, top bar, status bar, toasts.

import { html, useState } from '../vendor/htm-preact-standalone.mjs';
import { routeHash } from '../router.js';
import { walletLabel } from './components.js';
import { describeError } from '../lib/rpc.js';

const NAV = [
  ['overview', 'Overview'],
  ['send', 'Send'],
  ['receive', 'Receive'],
  ['transactions', 'Transactions'],
  ['wallets', 'Wallets'],
  ['peers', 'Peers'],
  ['messages', 'Sign / verify message'],
  ['mining', 'Mining'],
  ['console', 'Console'],
  ['node', 'Node'],
];

export function Sidebar({ app, state, route }) {
  const install = async () => {
    const p = state.installPrompt;
    if (!p) return;
    p.prompt();
    await p.userChoice.catch(() => null);
    app.store.set({ installPrompt: null });
  };
  return html`
    <nav class="sidebar" aria-label="Main">
      <div class="brand">${state.profile?.client ?? 'Node'} <span class="muted">Wallet</span></div>
      <ul>
        ${NAV.map(([view, label]) => html`
          <li><a href=${routeHash(view, null, state.wallet)} class=${route.view === view || (view === 'transactions' && route.view === 'tx') ? 'active' : ''}
                 aria-current=${route.view === view ? 'page' : undefined}>${label}</a></li>`)}
      </ul>
      ${state.installPrompt ? html`<button class="secondary install" onClick=${install}>Install app</button>` : null}
    </nav>`;
}

export function TopBar({ app, state }) {
  const wi = state.walletInfo;
  const wallets = state.wallets ?? [];
  let lock = null;
  if (wi) {
    if (wi.unlocked_until === undefined) lock = html`<span class="badge" title="The wallet is not encrypted">Not encrypted</span>`;
    else if (Number(wi.unlocked_until) === 0) lock = html`<span class="badge warn" title="Encrypted and locked">Locked</span>`;
    else lock = html`<span class="badge ok" title="Encrypted, unlocked for now">Unlocked</span>`;
  }
  // Option values are indexes: wallet names can be any string, including "".
  const onSelect = (e) => {
    const i = Number(e.currentTarget.value);
    app.selectWallet(i >= 0 ? wallets[i] : null);
  };
  const selected = state.wallet === null ? -1 : wallets.indexOf(state.wallet);
  const chain = state.profile?.chain;
  return html`
    <header class="topbar">
      <label class="wallet-picker">
        <span class="sr-only">Wallet</span>
        <select aria-label="Wallet" onChange=${onSelect} value=${String(selected)} data-testid="wallet-picker">
          ${selected < 0 ? html`<option value="-1">No wallet loaded</option>` : null}
          ${wallets.map((w, i) => html`<option value=${String(i)}>${walletLabel(w)}</option>`)}
        </select>
      </label>
      ${lock}
      ${wi?.hdseedid || wi?.descriptors ? html`<span class="badge" title="HD key generation is enabled">HD</span>` : null}
      ${wi && wi.private_keys_enabled === false ? html`<span class="badge" title="This wallet has no private keys">Watch-only</span>` : null}
      <span class="spacer"></span>
      ${chain ? html`<span class=${`badge net ${chain === 'main' ? 'main' : 'test'}`} title="Network">${chain === 'main' ? 'mainnet' : chain}</span>` : null}
      ${app.auth.canLogout ? html`<button class="secondary small" onClick=${() => app.logout()}>Log out</button>` : html`<span class="badge" title="Development mode: the dev proxy adds RPC credentials">dev proxy</span>`}
    </header>`;
}

export function StatusBar({ app, state }) {
  const [busy, setBusy] = useState(false);
  const c = state.chain;
  const n = state.net;
  const syncing = c && (c.initialblockdownload || c.blocks < c.headers);
  const pct = c ? Math.floor(Number(c.verificationprogress) * 1000) / 10 : 0;
  const toggle = async () => {
    setBusy(true);
    try {
      await app.rpc.call('setnetworkactive', [!n.networkactive]);
      app.refresh();
    } catch (e) {
      app.toast(describeError(e), 'error');
    } finally {
      setBusy(false);
    }
  };
  return html`
    <footer class="statusbar" aria-label="Node status">
      <span class="sync">
        ${c ? (syncing
          ? html`<progress max="100" value=${pct} aria-label="Sync progress"></progress> Syncing ${pct}% · block ${c.blocks} of ${c.headers}`
          : html`<span class="dot ok"></span> Synced · block ${c.blocks}`) : '…'}
      </span>
      <span class="peers">
        ${n ? `${n.connections ?? 0} connection${n.connections === 1 ? '' : 's'} (${n.connections_in ?? 0} in, ${n.connections_out ?? 0} out)` : ''}
      </span>
      ${n ? html`<button class=${`small ${n.networkactive ? 'secondary' : 'warn'}`} disabled=${busy} onClick=${toggle}
                  title="Controls this node's peer connections; does not change your Wi-Fi or internet connection."
                  aria-describedby="peer-network-help" data-testid="network-toggle">
          ${n.networkactive ? 'Disable peer networking' : 'Enable peer networking'}</button>` : null}
      ${n ? html`<span id="peer-network-help" class="muted">Peer networking ${n.networkactive ? 'enabled' : 'disabled'} · node connections only</span>` : null}
      <span class="spacer"></span>
      <span class="version muted">${n ? n.subversion : ''}</span>
    </footer>`;
}

export function Toasts({ state }) {
  return html`
    <div class="toasts" aria-live="polite">
      ${state.toasts.map((t) => html`<div class=${`toast ${t.kind}`} key=${t.id}>${t.text}</div>`)}
    </div>`;
}

export function UpdateBanner({ state }) {
  if (!state.swUpdate) return null;
  const reload = () => {
    navigator.serviceWorker?.getRegistration('/wallet/').then((reg) => {
      reg?.waiting?.postMessage('skipWaiting');
    });
  };
  return html`<div class="banner info">Update available. <button class="small" onClick=${reload}>Reload</button></div>`;
}
