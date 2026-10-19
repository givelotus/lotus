// App controller: session → profile → wallet selection → poller.
//
// Views read state from app.store and call app.rpc / app.walletCall. All node
// state is refreshed by one batched tick (see lib/poller.js).

import { createRpc, RpcError, HttpError, NetworkError, RPC_IN_WARMUP, RPC_WALLET_NOT_FOUND, RPC_WALLET_NOT_SPECIFIED } from './lib/rpc.js';
import { createProxyAuth, createSessionAuth, authModeFromDocument, tokenFromHash } from './lib/session.js';
import { createPoller } from './lib/poller.js';
import { detectProfile } from './lib/profile.js';
import { createStore } from './lib/store.js';
import { load, save } from './lib/storage.js';
import { parseRoute, routeHash } from './router.js';

/**
 * @typedef {{
 *   phase: 'boot'|'login'|'warmup'|'offline'|'ready',
 *   session: any, profile: import('./lib/profile.js').Profile|null,
 *   wallets: string[]|null, wallet: string|null,
 *   chain: any, net: any, balances: any, walletInfo: any, txs: any[]|null,
 *   warmup: string, offlineSince: number|null, retryInMs: number,
 *   loginError: string, toasts: Array<{id: number, text: string, kind: string}>,
 *   swUpdate: boolean, installPrompt: any, lastTick: number,
 * }} AppState
 */

export function createApp({ fetch, location = globalThis.location, history = globalThis.history } = {}) {
  const mode = authModeFromDocument();
  const auth = mode === 'proxy' ? createProxyAuth() : createSessionAuth({ fetch });

  /** @type {ReturnType<typeof createStore<AppState>>} */
  const store = createStore({
    phase: 'boot', session: null, profile: null, wallets: null, wallet: null,
    chain: null, net: null, balances: null, walletInfo: null, txs: null,
    warmup: '', offlineSince: null, retryInMs: 0, loginError: '', toasts: [],
    swUpdate: false, installPrompt: null, lastTick: 0,
  });

  let reconnectTimer = null;
  let reconnectDelay = 0;
  let lastTxKey = '';

  const rpc = createRpc({
    auth,
    fetch,
    onNetworkError: () => {
      if (store.get().phase === 'ready') goOffline();
    },
    onWarmup: (msg) => store.set({ warmup: msg }),
  });

  auth.setUnauthorizedHandler(() => {
    poller.stop();
    if (store.get().phase !== 'login') {
      store.set({ phase: 'login', session: null, loginError: 'Your session ended. Please log in again.' });
    }
  });

  const poller = createPoller({
    tick,
    // 10 s rather than longer: an abandoned call (closed or reloaded tab)
    // keeps one of the node's RPC worker threads (-rpcthreads, default 4)
    // busy until it times out.
    waitForBlock: async (_last, signal) => {
      const r = await rpc.call('waitfornewblock', [10000], { timeoutMs: 20000, signal });
      return r?.hash ?? null;
    },
  });

  // ---- wallet-aware calls ------------------------------------------------

  /** Call a wallet RPC on the selected wallet. */
  function walletCall(method, params = [], opts = {}) {
    const w = store.get().wallet;
    return rpc.call(method, params, { ...opts, wallet: w });
  }

  // ---- refresh -----------------------------------------------------------

  async function tick() {
    const s = store.get();
    if (s.phase !== 'ready') return;
    const w = s.wallet;
    const calls = [['getblockchaininfo'], ['getnetworkinfo'], ['listwallets']];
    if (w !== null) calls.push(['getbalances'], ['getwalletinfo']);
    const out = await rpc.batch(calls, { wallet: w });
    const [chain, net, wallets, balances, walletInfo] = out;
    if (chain instanceof RpcError && chain.code === RPC_IN_WARMUP) {
      store.set({ warmup: chain.message });
      return;
    }
    const patch = { lastTick: Date.now(), warmup: '' };
    if (!(chain instanceof RpcError)) { patch.chain = chain; poller.setBestHash(chain.bestblockhash); }
    if (!(net instanceof RpcError)) patch.net = net;
    if (!(wallets instanceof RpcError)) patch.wallets = wallets;
    if (w !== null) {
      if (balances instanceof RpcError && (balances.code === RPC_WALLET_NOT_FOUND || balances.code === RPC_WALLET_NOT_SPECIFIED)) {
        // The wallet was unloaded elsewhere (console, lotus-cli).
        patch.wallet = null;
        patch.balances = patch.walletInfo = null;
        patch.txs = null;
      } else {
        if (!(balances instanceof RpcError)) patch.balances = balances;
        if (!(walletInfo instanceof RpcError)) patch.walletInfo = walletInfo;
      }
    } else if (!(wallets instanceof RpcError) && wallets.length > 0) {
      patch.wallet = pickWallet(wallets);
    }
    store.set(patch);
    if (patch.wallet !== undefined && patch.wallet !== w) {
      syncWalletToHash();
      poller.poke();
      return;
    }
    // listtransactions only when something that affects it changed.
    if (w !== null && patch.walletInfo) {
      const key = `${w}|${patch.walletInfo.txcount}|${patch.chain?.bestblockhash}`;
      const hasUnconfirmed = (store.get().txs ?? []).some((t) => (t.confirmations ?? 0) < 1);
      if (key !== lastTxKey || hasUnconfirmed) {
        const txs = await rpc.call('listtransactions', ['*', 50, 0, true], { wallet: w });
        lastTxKey = key;
        if (store.get().wallet === w) store.set({ txs: txs.slice().reverse() });
      }
    }
  }

  function pickWallet(wallets) {
    const route = parseRoute(location.hash);
    if (route.wallet !== null && wallets.includes(route.wallet)) return route.wallet;
    const remembered = load('wallet', null);
    if (remembered !== null && wallets.includes(remembered)) return remembered;
    return wallets.length > 0 ? wallets[0] : null;
  }

  function selectWallet(name) {
    lastTxKey = '';
    store.set({ wallet: name, balances: null, walletInfo: null, txs: null });
    if (name !== null) save('wallet', name);
    syncWalletToHash();
    poller.poke();
  }

  function syncWalletToHash() {
    const route = parseRoute(location.hash);
    const w = store.get().wallet;
    if (route.wallet === w) return;
    history.replaceState(null, '', routeHash(route.view, route.arg, w));
    globalThis.dispatchEvent?.(new HashChangeEvent('hashchange'));
  }

  // ---- lifecycle ----------------------------------------------------------

  async function boot() {
    clearTimeout(reconnectTimer);
    try {
      let session = await auth.status();
      const token = tokenFromHash(location.hash);
      if (token) {
        // Clear the token from the address bar before anything else, used or not.
        history.replaceState(null, '', '#/overview');
        if (!session) {
          try {
            session = await auth.loginToken(token);
          } catch (e) {
            store.set({ phase: 'login', loginError: `Login link not accepted: ${e.message}. Links work once and expire after two minutes.` });
            return;
          }
        }
      }
      if (!session) {
        store.set({ phase: 'login', session: null });
        return;
      }
      store.set({ session, loginError: '' });
      await afterLogin();
    } catch (e) {
      if (e instanceof NetworkError || e instanceof TypeError) goOffline();
      else if (e instanceof HttpError && e.status === 401) { /* handled by the unauthorized handler */ }
      else { goOffline(String(e?.message ?? e)); }
    }
  }

  async function afterLogin() {
    for (;;) {
      try {
        const profile = await detectProfile(rpc);
        const wallets = await rpc.call('listwallets');
        store.set({ profile, wallets, wallet: pickWallet(wallets), phase: 'ready', warmup: '', offlineSince: null });
        reconnectDelay = 0;
        if (globalThis.document) document.title = `${profile.client} · ${profile.chain}`;
        syncWalletToHash();
        poller.start();
        poller.poke();
        return;
      } catch (e) {
        if (e instanceof RpcError && e.code === RPC_IN_WARMUP) {
          store.set({ phase: 'warmup', warmup: e.message });
          await new Promise((r) => setTimeout(r, 1000));
          continue;
        }
        throw e;
      }
    }
  }

  function goOffline() {
    poller.stop();
    const s = store.get();
    reconnectDelay = reconnectDelay ? Math.min(reconnectDelay * 2, 30000) : 1000;
    store.set({ phase: 'offline', offlineSince: s.offlineSince ?? Date.now(), retryInMs: reconnectDelay });
    clearTimeout(reconnectTimer);
    reconnectTimer = setTimeout(boot, reconnectDelay);
  }

  async function loginPassword(user, password) {
    try {
      const session = await auth.loginPassword(user, password);
      store.set({ session, loginError: '' });
      await afterLogin();
    } catch (e) {
      store.set({ loginError: e.message });
    }
  }

  async function logout() {
    poller.stop();
    await auth.logout().catch(() => {});
    store.set({ phase: 'login', session: null, loginError: '', wallet: null, balances: null, walletInfo: null, txs: null });
  }

  // ---- toasts ---------------------------------------------------------------

  let toastId = 0;
  function toast(text, kind = 'info', ms = 4000) {
    const id = ++toastId;
    store.set((s) => ({ toasts: [...s.toasts, { id, text, kind }] }));
    setTimeout(() => store.set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })), ms);
  }

  // Refresh right away when the tab becomes visible again.
  globalThis.document?.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') poller.poke();
  });

  return {
    mode, auth, rpc, store, poller, walletCall, selectWallet, boot, loginPassword, logout, toast,
    retryNow: () => { reconnectDelay = 0; boot(); },
    refresh: () => poller.poke(),
  };
}
