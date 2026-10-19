// Hash routing: #/<view>[/<arg>][?w=<wallet>]. The selected wallet travels in
// the hash so links and reloads keep it; "w=" (empty) is the default wallet.

export const VIEWS = ['overview', 'send', 'receive', 'transactions', 'tx', 'peers', 'console', 'node', 'wallets', 'login'];

/** @returns {{view: string, arg: string|null, wallet: string|null, params: URLSearchParams}} */
export function parseRoute(hash) {
  const h = (hash ?? '').replace(/^#/, '');
  const q = h.indexOf('?');
  const path = q >= 0 ? h.slice(0, q) : h;
  const params = new URLSearchParams(q >= 0 ? h.slice(q + 1) : '');
  const parts = path.split('/').filter(Boolean);
  const view = VIEWS.includes(parts[0]) ? parts[0] : 'overview';
  let arg = null;
  if (parts.length > 1) {
    try { arg = decodeURIComponent(parts.slice(1).join('/')); } catch { arg = null; }
  }
  return { view, arg, wallet: params.has('w') ? params.get('w') : null, params };
}

export function routeHash(view, arg = null, wallet = null) {
  let h = `#/${view}`;
  if (arg !== null && arg !== undefined) h += '/' + encodeURIComponent(arg);
  if (wallet !== null && wallet !== undefined) h += '?w=' + encodeURIComponent(wallet);
  return h;
}
