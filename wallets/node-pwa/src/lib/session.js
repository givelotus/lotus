// Browser authentication.
//
// Two modes, selected by <meta name="node-pwa-auth" content="..."> in
// index.html:
//
//   "session" (default; the daemon's design): the node serves the app and
//     /auth/session. Login with a one-time token from the URL fragment or with
//     RPC credentials sets an HttpOnly cookie; every RPC carries X-CSRF-Token.
//     The CSRF token lives only in memory and is re-fetched on every load.
//
//   "proxy" (development): tools/devserver.mjs forwards RPC POSTs to a node
//     with Basic auth it reads from the node's cookie file. The app sends no
//     credentials and there is nothing to log in to.
//
// Both expose the same interface, used by rpc.js (headers, onUnauthorized)
// and by the app shell (status, login*, logout).

export class LoginError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

/** @returns {'session'|'proxy'} */
export function authModeFromDocument(doc = globalThis.document) {
  const v = doc?.querySelector?.('meta[name="node-pwa-auth"]')?.getAttribute('content');
  return v === 'proxy' ? 'proxy' : 'session';
}

/**
 * @typedef {{user: string, expires?: number, pwa_version?: string}} SessionInfo
 * @typedef {{mode: string, headers(): Record<string,string>, onUnauthorized(): void,
 *   status(): Promise<SessionInfo|null>, loginToken(token: string): Promise<SessionInfo>,
 *   loginPassword(user: string, password: string): Promise<SessionInfo>, logout(): Promise<void>,
 *   canLogout: boolean, setUnauthorizedHandler(fn: () => void): void}} Auth
 */

/** @returns {Auth} */
export function createProxyAuth() {
  let onUnauth = () => {};
  return {
    mode: 'proxy',
    canLogout: false,
    headers: () => ({}),
    onUnauthorized: () => onUnauth(),
    setUnauthorizedHandler(fn) { onUnauth = fn; },
    async status() { return { user: 'dev proxy' }; },
    async loginToken() { throw new LoginError(400, 'the dev proxy has no login'); },
    async loginPassword() { throw new LoginError(400, 'the dev proxy has no login'); },
    async logout() {},
  };
}

/**
 * @param {{fetch?: typeof fetch, base?: string}} [cfg]
 * @returns {Auth}
 */
export function createSessionAuth(cfg = {}) {
  const doFetch = cfg.fetch ?? globalThis.fetch.bind(globalThis);
  const base = cfg.base ?? '';
  let csrf = null;
  let onUnauth = () => {};

  async function jsonOrNull(resp) {
    try { return await resp.json(); } catch { return null; }
  }

  async function login(body) {
    const resp = await doFetch(`${base}/auth/session`, {
      method: 'POST',
      credentials: 'same-origin',
      cache: 'no-store',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const json = await jsonOrNull(resp);
    if (!resp.ok || !json?.csrf) {
      throw new LoginError(resp.status, json?.error ?? (resp.status === 401 ? 'login failed' : `HTTP ${resp.status}`));
    }
    csrf = json.csrf;
    return { user: json.user, expires: json.expires, pwa_version: json.pwa_version };
  }

  return {
    mode: 'session',
    canLogout: true,
    headers: () => (csrf ? { 'X-CSRF-Token': csrf } : {}),
    onUnauthorized() { csrf = null; onUnauth(); },
    setUnauthorizedHandler(fn) { onUnauth = fn; },

    /** Session status; null when not logged in. Throws on network failure. */
    async status() {
      const resp = await doFetch(`${base}/auth/session`, { credentials: 'same-origin', cache: 'no-store' });
      if (resp.status === 401) { csrf = null; return null; }
      const json = await jsonOrNull(resp);
      if (!resp.ok || !json?.csrf) throw new LoginError(resp.status, json?.error ?? `HTTP ${resp.status}`);
      csrf = json.csrf;
      return { user: json.user, expires: json.expires, pwa_version: json.pwa_version };
    },

    loginToken(token) { return login({ token }); },

    /** Accepts rpcuser/rpcpassword, or a pasted cookie line "__cookie__:<hex>" as the password. */
    loginPassword(user, password) {
      if (!user && password.includes(':')) {
        const k = password.indexOf(':');
        return login({ user: password.slice(0, k), password: password.slice(k + 1) });
      }
      return login({ user, password });
    },

    async logout() {
      try {
        await doFetch(`${base}/auth/logout`, {
          method: 'POST',
          credentials: 'same-origin',
          headers: { 'Content-Type': 'application/json', ...(csrf ? { 'X-CSRF-Token': csrf } : {}) },
          body: '{}',
        });
      } finally {
        csrf = null;
      }
    },
  };
}

/** Extract a login token from a location hash like "#/login/<64 hex>". */
export function tokenFromHash(hash) {
  const m = /^#\/login\/([0-9a-fA-F]{64})(?:[?/].*)?$/.exec(hash ?? '');
  return m ? m[1].toLowerCase() : null;
}
