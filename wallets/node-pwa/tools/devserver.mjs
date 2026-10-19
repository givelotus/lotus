#!/usr/bin/env node
// Development server for the node PWA (Node stdlib only).
//
// Serves an app directory (src/, or an extracted release bundle) under
// /wallet/ with the daemon design's headers, and forwards JSON-RPC POSTs on
// "/" and "/wallet/<name>" to a node, adding Basic auth from the node's
// cookie file (re-read on every request, so node restarts are fine) or from
// --rpcuser/--rpcpassword.
//
// --auth proxy   (default) the app sends no credentials; index.html is served
//                with <meta name="node-pwa-auth" content="proxy">.
// --auth session emulates the daemon's planned browser sessions: one-time
//                login tokens, /auth/session, /auth/logout, an HttpOnly
//                cookie, X-CSRF-Token and the Origin/Host policy. This lets
//                the app's session path run before any node serves it.
//
//   node tools/devserver.mjs --datadir ~/regtest-data --chain regtest --rpcport 18604
//
// Bind it to loopback only: anyone who can reach it gets the node's RPC.

import { createServer } from 'node:http';
import { readFile, stat, realpath } from 'node:fs/promises';
import { createHash, randomBytes, timingSafeEqual } from 'node:crypto';
import { join, resolve, sep, extname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { parseArgs } from 'node:util';

export const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json',
  '.webmanifest': 'application/manifest+json',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.ico': 'image/x-icon',
  '.woff2': 'font/woff2',
  '.wasm': 'application/wasm',
  '.txt': 'text/plain; charset=utf-8',
};

export const SECURITY_HEADERS = {
  'Content-Security-Policy': "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data: blob:; " +
    "connect-src 'self'; manifest-src 'self'; worker-src 'self'; font-src 'self'; media-src 'self'; " +
    "form-action 'none'; frame-ancestors 'none'; base-uri 'none'",
  'X-Content-Type-Options': 'nosniff',
  'Referrer-Policy': 'no-referrer',
  'X-Frame-Options': 'DENY',
  'Cross-Origin-Opener-Policy': 'same-origin',
  'Cross-Origin-Resource-Policy': 'same-origin',
  'Permissions-Policy': 'camera=(self), microphone=(), geolocation=(), usb=(), hid=()',
};

/**
 * The design's path rules for GET /wallet/<path>: strip the query, decode
 * once, reject empty/dot segments, backslash, NUL, leading "/", over 256
 * characters and dot-files. Empty maps to index.html. Returns null if rejected.
 */
export function normalizeAssetPath(rawPath) {
  let p = rawPath.split('?')[0];
  try {
    p = decodeURIComponent(p);
  } catch {
    return null;
  }
  if (p === '') return 'index.html';
  if (p.length > 256 || p.startsWith('/') || p.includes('\\') || p.includes('\0')) return null;
  const segs = p.split('/');
  if (segs.some((s) => s === '' || s === '.' || s === '..' || s.startsWith('.'))) return null;
  return p;
}

/** Host header allowed: loopback literal or localhost with any port. */
export function hostAllowed(host) {
  if (!host) return false;
  const h = host.toLowerCase();
  const m = /^(\[[0-9a-f:.]+\]|[^:]+)(?::(\d+))?$/.exec(h);
  if (!m) return false;
  const name = m[1];
  return name === 'localhost' || name === '[::1]' || /^127\.\d{1,3}\.\d{1,3}\.\d{1,3}$/.test(name);
}

/** Origin must equal scheme://Host after lower-casing and dropping a default port. */
export function originMatches(origin, host, scheme = 'http') {
  if (!origin || !host) return false;
  const norm = (s, sch) => {
    const v = s.toLowerCase();
    return sch === 'http' ? v.replace(/:80$/, '') : v.replace(/:443$/, '');
  };
  return norm(origin, scheme) === `${scheme}://${norm(host, scheme)}`;
}

export function parseCookies(header) {
  const out = {};
  for (const part of (header ?? '').split(';')) {
    const eq = part.indexOf('=');
    if (eq < 0) continue;
    const k = part.slice(0, eq).trim();
    if (k && !Object.hasOwn(out, k)) out[k] = part.slice(eq + 1).trim();
  }
  return out;
}

const sha256 = (s) => createHash('sha256').update(s).digest();
const sameBytes = (a, b) => a.length === b.length && timingSafeEqual(a, b);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

/** In-memory token and session stores, as specified for the daemon. */
export function createSessionStore({ now = () => Date.now() } = {}) {
  const tokens = []; // {hash, expires, user}
  const sessions = new Map(); // hex(sha256(id)) → {user, csrf, created, lastUsed}
  const IDLE = 7 * 86400e3;
  const ABSOLUTE = 30 * 86400e3;
  return {
    mintToken(user) {
      const token = randomBytes(32).toString('hex');
      tokens.push({ hash: sha256(token), expires: now() + 120e3, user });
      while (tokens.length > 16) tokens.shift();
      return token;
    },
    consumeToken(token) {
      if (!/^[0-9a-f]{64}$/.test(token ?? '')) return null;
      const h = sha256(token);
      let found = -1;
      tokens.forEach((t, i) => { if (sameBytes(t.hash, h)) found = i; });
      if (found < 0) return null;
      const [t] = tokens.splice(found, 1);
      return t.expires > now() ? t.user : null;
    },
    create(user) {
      const id = randomBytes(32).toString('hex');
      const csrf = randomBytes(32).toString('hex');
      sessions.set(sha256(id).toString('hex'), { user, csrf, created: now(), lastUsed: now() });
      while (sessions.size > 64) {
        let oldest = null;
        for (const [k, s] of sessions) if (!oldest || s.lastUsed < sessions.get(oldest).lastUsed) oldest = k;
        sessions.delete(oldest);
      }
      return { id, csrf, expires: Math.floor((now() + ABSOLUTE) / 1000) };
    },
    lookup(id) {
      if (!/^[0-9a-f]{64}$/.test(id ?? '')) return null;
      const k = sha256(id).toString('hex');
      const s = sessions.get(k);
      if (!s) return null;
      if (now() - s.lastUsed > IDLE || now() - s.created > ABSOLUTE) { sessions.delete(k); return null; }
      s.lastUsed = now();
      return { ...s, key: k, expires: Math.floor((s.created + ABSOLUTE) / 1000) };
    },
    remove(key) { sessions.delete(key); },
  };
}

/**
 * @param {{root: string, rpcUrl: string, auth?: 'proxy'|'session', cookieFile?: string,
 *          rpcUser?: string, rpcPassword?: string, log?: (msg: string) => void}} opts
 */
export function createDevServer(opts) {
  const authMode = opts.auth ?? 'proxy';
  const root = resolve(opts.root);
  const rpcPort = new URL(opts.rpcUrl).port || '80';
  const cookieName = `nodewallet_${rpcPort}`;
  const store = createSessionStore();
  const log = opts.log ?? (() => {});

  async function nodeCredentials() {
    if (opts.rpcUser !== undefined) return `${opts.rpcUser}:${opts.rpcPassword ?? ''}`;
    return (await readFile(opts.cookieFile, 'utf8')).trim();
  }

  async function forward(path, body, credentials, signal) {
    const auth = 'Basic ' + Buffer.from(credentials ?? (await nodeCredentials())).toString('base64');
    const resp = await fetch(new URL(path, opts.rpcUrl), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: auth },
      body,
      signal,
    });
    return { status: resp.status, body: Buffer.from(await resp.arrayBuffer()) };
  }

  const reply = (res, status, headers, body = '') => {
    res.writeHead(status, headers);
    res.end(body);
  };
  const json = (res, status, obj, extra = {}) =>
    reply(res, status, { 'Content-Type': 'application/json', 'Cache-Control': 'no-store', ...extra }, JSON.stringify(obj));

  async function readBody(req, limit) {
    const chunks = [];
    let n = 0;
    for await (const c of req) {
      n += c.length;
      if (n > limit) throw Object.assign(new Error('body too large'), { status: 413 });
      chunks.push(c);
    }
    return Buffer.concat(chunks);
  }

  /** The design's origin policy; for GET, Origin may be absent. */
  function originOk(req, requireOrigin) {
    if (!hostAllowed(req.headers.host)) return false;
    const origin = req.headers.origin;
    if (!origin) return !requireOrigin;
    return originMatches(origin, req.headers.host, 'http');
  }

  function sessionFor(req) {
    return store.lookup(parseCookies(req.headers.cookie)[cookieName]);
  }

  function setCookie(id) {
    return `${cookieName}=${id}; Path=/; HttpOnly; SameSite=Strict; Max-Age=2592000`;
  }

  async function serveAsset(req, res, rel) {
    const p = normalizeAssetPath(rel);
    const type = p && MIME[extname(p).toLowerCase()];
    if (!p || !type) return reply(res, 404, { ...SECURITY_HEADERS, 'Content-Type': 'text/plain; charset=utf-8' }, 'not found');
    try {
      const full = await realpath(join(root, p));
      const rootReal = await realpath(root);
      if (!full.startsWith(rootReal + sep)) throw new Error('outside root');
      const st = await stat(full);
      if (!st.isFile() || st.size > 16 * 1024 * 1024) throw new Error('not a file');
      let body = await readFile(full);
      if (p === 'index.html' && authMode === 'proxy') {
        body = Buffer.from(body.toString('utf8').replace('<meta name="node-pwa-auth" content="session">', '<meta name="node-pwa-auth" content="proxy">'));
      }
      reply(res, 200, { ...SECURITY_HEADERS, 'Content-Type': type, 'Cache-Control': 'no-store' }, req.method === 'HEAD' ? '' : body);
    } catch {
      reply(res, 404, { ...SECURITY_HEADERS, 'Content-Type': 'text/plain; charset=utf-8' }, 'not found');
    }
  }

  async function handleAuth(req, res, url) {
    if (url.pathname === '/auth/session' && req.method === 'GET') {
      if (!originOk(req, false)) return json(res, 403, { error: 'origin not allowed' });
      const s = sessionFor(req);
      if (!s) return json(res, 401, { error: 'login required' });
      return json(res, 200, { csrf: s.csrf, user: s.user, expires: s.expires, pwa_version: 'dev' });
    }
    if (url.pathname === '/auth/session' && req.method === 'POST') {
      if (!originOk(req, true)) return json(res, 403, { error: 'origin not allowed' });
      if (!/^application\/json\b/i.test(req.headers['content-type'] ?? '')) return json(res, 415, { error: 'JSON required' });
      if (!isLoopback(req.socket.remoteAddress)) return json(res, 403, { error: 'wallet sessions need HTTPS or a loopback connection' });
      let body;
      try {
        body = JSON.parse((await readBody(req, 4096)).toString('utf8'));
      } catch (e) {
        return json(res, e.status ?? 400, { error: 'bad request' });
      }
      let user = null;
      if (typeof body.token === 'string') {
        user = store.consumeToken(body.token);
      } else if (typeof body.user === 'string' && typeof body.password === 'string') {
        // Let the node judge the credentials, exactly as RPCAuthorized would.
        try {
          const r = await forward('/', '{"jsonrpc":"1.0","id":0,"method":"uptime","params":[]}', `${body.user}:${body.password}`);
          if (r.status !== 401 && r.status !== 403) user = body.user;
        } catch {
          return json(res, 502, { error: 'node unreachable' });
        }
      }
      if (!user) {
        await sleep(250);
        log('auth: login failed');
        return json(res, 401, { error: 'login failed' });
      }
      const s = store.create(user);
      log(`auth: session created for ${user}`);
      return json(res, 200, { csrf: s.csrf, user, expires: s.expires }, { 'Set-Cookie': setCookie(s.id) });
    }
    if (url.pathname === '/auth/logout' && req.method === 'POST') {
      const s = sessionFor(req);
      if (!originOk(req, true) || !s || !csrfOk(req, s)) return json(res, 401, { error: 'login required' });
      store.remove(s.key);
      return reply(res, 204, { 'Set-Cookie': `${cookieName}=; Max-Age=0; Path=/`, 'Cache-Control': 'no-store' });
    }
    return json(res, 405, { error: 'method not allowed' });
  }

  function csrfOk(req, s) {
    const h = req.headers['x-csrf-token'];
    return typeof h === 'string' && sameBytes(Buffer.from(h), Buffer.from(s.csrf));
  }

  async function handleRpc(req, res, url) {
    let credentials = null;
    if (authMode === 'session' && !req.headers.authorization) {
      const s = sessionFor(req);
      const ok = s && originOk(req, true) && csrfOk(req, s) && /^application\/json\b/i.test(req.headers['content-type'] ?? '');
      if (!ok) {
        await sleep(250);
        return reply(res, 401, { 'Content-Type': 'text/plain; charset=utf-8' }, '');
      }
    } else if (authMode === 'session') {
      // Non-browser clients with their own Basic auth pass straight through.
      credentials = Buffer.from(req.headers.authorization.replace(/^Basic\s+/i, ''), 'base64').toString('utf8');
    }
    let body;
    try {
      body = await readBody(req, 32 * 1024 * 1024);
    } catch (e) {
      return reply(res, e.status ?? 400, {}, '');
    }
    // Drop the upstream request when the browser goes away.
    const ctl = new AbortController();
    res.on('close', () => { if (!res.writableFinished) ctl.abort(); });
    try {
      const r = await forward(url.pathname, body, credentials, ctl.signal);
      return reply(res, r.status, { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' }, r.body);
    } catch (e) {
      if (ctl.signal.aborted) return undefined;
      log(`rpc: node unreachable (${e.cause?.code ?? e.message})`);
      return reply(res, 502, { 'Content-Type': 'text/plain; charset=utf-8' }, 'node unreachable');
    }
  }

  const server = createServer(async (req, res) => {
    try {
      const url = new URL(req.url, 'http://dev.invalid');
      if (url.pathname.startsWith('/auth/')) {
        if (authMode !== 'session') return json(res, 404, { error: 'not found' });
        return await handleAuth(req, res, url);
      }
      if (req.method === 'POST' && (url.pathname === '/' || url.pathname.startsWith('/wallet/'))) return await handleRpc(req, res, url);
      if (req.method === 'GET' && url.pathname === '/wallet') return reply(res, 308, { Location: '/wallet/' });
      if (req.method === 'GET' && url.pathname.startsWith('/wallet/')) {
        // Use the raw path so percent-encoded traversal reaches the checks undecoded.
        const raw = req.url.split('?')[0].slice('/wallet/'.length);
        return await serveAsset(req, res, raw);
      }
      if (req.method === 'GET' && url.pathname === '/') return reply(res, 302, { Location: '/wallet/' });
      if (url.pathname.startsWith('/wallet/') || url.pathname === '/') return reply(res, 405, {}, '');
      return reply(res, 404, {}, 'not found');
    } catch (e) {
      log(`error: ${e.message}`);
      if (!res.headersSent) reply(res, 500, {}, '');
    }
  });

  return {
    server,
    cookieName,
    /** One-time login token (session mode), as getwalletpwaurl would mint. */
    mintToken: (user = '__cookie__') => store.mintToken(user),
  };
}

function isLoopback(addr) {
  return addr === '::1' || /^(::ffff:)?127\./.test(addr ?? '');
}

function cookiePath(datadir, chain) {
  const sub = { main: '', test: 'testnet3', regtest: 'regtest' }[chain];
  if (sub === undefined) throw new Error(`unknown chain ${chain}`);
  return join(datadir, sub, '.cookie');
}

async function main() {
  const { values } = parseArgs({
    options: {
      root: { type: 'string', default: fileURLToPath(new URL('../src', import.meta.url)) },
      host: { type: 'string', default: '127.0.0.1' },
      port: { type: 'string', default: '18680' },
      rpcport: { type: 'string', default: '18604' },
      rpchost: { type: 'string', default: '127.0.0.1' },
      datadir: { type: 'string' },
      chain: { type: 'string', default: 'regtest' },
      cookie: { type: 'string' },
      rpcuser: { type: 'string' },
      rpcpassword: { type: 'string' },
      auth: { type: 'string', default: 'proxy' },
      help: { type: 'boolean', short: 'h' },
    },
  });
  if (values.help || (!values.datadir && !values.cookie && values.rpcuser === undefined)) {
    console.log(`usage: node tools/devserver.mjs (--datadir DIR [--chain regtest|test|main] | --cookie FILE | --rpcuser U --rpcpassword P)
         [--rpcport 18604] [--rpchost 127.0.0.1] [--port 18680] [--host 127.0.0.1] [--root src] [--auth proxy|session]`);
    process.exit(values.help ? 0 : 2);
  }
  if (!['proxy', 'session'].includes(values.auth)) throw new Error('--auth must be proxy or session');
  const dev = createDevServer({
    root: values.root,
    rpcUrl: `http://${values.rpchost.includes(':') ? `[${values.rpchost}]` : values.rpchost}:${values.rpcport}/`,
    auth: values.auth,
    cookieFile: values.cookie ?? (values.datadir ? cookiePath(values.datadir, values.chain) : undefined),
    rpcUser: values.rpcuser,
    rpcPassword: values.rpcpassword,
    log: (m) => console.error(m),
  });
  dev.server.listen(Number(values.port), values.host, () => {
    const base = `http://${values.host.includes(':') ? `[${values.host}]` : values.host}:${values.port}/wallet/`;
    const printUrl = () => console.log(`Wallet: ${values.auth === 'session' ? `${base}#/login/${dev.mintToken()}` : base}`);
    printUrl();
    if (values.auth === 'session' && process.stdin.isTTY) {
      console.error('Press Enter for a new one-time login link (links expire after 120 s).');
      process.stdin.on('data', printUrl);
    }
  });
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().catch((e) => { console.error(e.message); process.exit(1); });
}
