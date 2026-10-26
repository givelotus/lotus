import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { createServer, request } from 'node:http';
import { mkdtempSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createDevServer, normalizeAssetPath, hostAllowed, originMatches, parseCookies, createSessionStore } from '../../tools/devserver.mjs';

const SRC = fileURLToPath(new URL('../../src/', import.meta.url));

test('asset path rules', () => {
  assert.equal(normalizeAssetPath(''), 'index.html');
  assert.equal(normalizeAssetPath('lib/rpc.js?x=1'), 'lib/rpc.js');
  assert.equal(normalizeAssetPath('a%20b.js'), 'a b.js');
  for (const bad of ['..', '../x', 'a/../b', '%2e%2e/x', '%2E%2E%2Fx', 'a//b', '/etc/passwd', '%2fetc', 'a\\b', 'a%5cb', 'a%00b', '.git/config', 'x/.env', './a', 'x'.repeat(257), '%zz']) {
    assert.equal(normalizeAssetPath(bad), null, bad);
  }
});

test('Host and Origin policy', () => {
  for (const ok of ['127.0.0.1:18680', '127.1.2.3', 'localhost:9', 'LOCALHOST', '[::1]:18680']) assert.ok(hostAllowed(ok), ok);
  for (const bad of ['evil.example:18680', '192.168.1.2:18680', '', undefined, '127.0.0.1.evil.example', '[::2]:1']) assert.ok(!hostAllowed(bad), String(bad));
  assert.ok(originMatches('http://127.0.0.1:18680', '127.0.0.1:18680'));
  assert.ok(originMatches('http://localhost', 'localhost:80'));
  assert.ok(!originMatches('http://127.0.0.1:3000', '127.0.0.1:18680'), 'same site, other port');
  assert.ok(!originMatches('https://127.0.0.1:18680', '127.0.0.1:18680'), 'scheme mismatch');
  assert.ok(!originMatches(undefined, '127.0.0.1:18680'));
});

test('cookie parsing', () => {
  assert.deepEqual(parseCookies('a=1; nodewallet_18604=abc; b=2=3'), { a: '1', nodewallet_18604: 'abc', b: '2=3' });
  assert.deepEqual(parseCookies(undefined), {});
});

test('tokens are single use, expire, and at most 16 are kept; sessions expire', () => {
  let now = 1e12;
  const s = createSessionStore({ now: () => now });
  const t = s.mintToken('__cookie__');
  assert.equal(s.consumeToken(t), '__cookie__');
  assert.equal(s.consumeToken(t), null);
  const t2 = s.mintToken('u');
  now += 121e3;
  assert.equal(s.consumeToken(t2), null);
  const many = Array.from({ length: 17 }, () => s.mintToken('u'));
  assert.equal(s.consumeToken(many[0]), null, 'oldest evicted');
  assert.equal(s.consumeToken(many[16]), 'u');
  const sess = s.create('u');
  assert.equal(s.lookup(sess.id).user, 'u');
  now += 8 * 86400e3;
  assert.equal(s.lookup(sess.id), null, 'idle timeout');
  assert.equal(s.lookup('zz'), null);
});

// ---- HTTP behaviour against a fake node --------------------------------

let node, nodeUrl, dir, cookieFile;
const seen = [];

before(async () => {
  dir = mkdtempSync(join(tmpdir(), 'node-pwa-dev-'));
  cookieFile = join(dir, '.cookie');
  writeFileSync(cookieFile, '__cookie__:s3cret\n');
  node = createServer(async (req, res) => {
    let body = '';
    for await (const c of req) body += c;
    seen.push({ url: req.url, auth: req.headers.authorization, body });
    const creds = Buffer.from((req.headers.authorization ?? '').replace('Basic ', ''), 'base64').toString();
    if (creds !== '__cookie__:s3cret' && creds !== 'alice:pw') { res.writeHead(401); res.end(); return; }
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ result: { url: req.url, method: JSON.parse(body).method }, error: null, id: 1 }));
  });
  await new Promise((r) => node.listen(0, '127.0.0.1', r));
  nodeUrl = `http://127.0.0.1:${node.address().port}/`;
});
after(() => { node.close(); rmSync(dir, { recursive: true, force: true }); });

async function start(auth) {
  const dev = createDevServer({ root: SRC, rpcUrl: nodeUrl, auth, cookieFile });
  await new Promise((r) => dev.server.listen(0, '127.0.0.1', r));
  const base = `http://127.0.0.1:${dev.server.address().port}`;
  return { dev, base, close: () => new Promise((r) => { dev.server.closeAllConnections(); dev.server.close(r); }) };
}

test('proxy mode: static files with headers, RPC forwarded with cookie credentials', async () => {
  const { base, close } = await start('proxy');
  try {
    let r = await fetch(`${base}/wallet`, { redirect: 'manual' });
    assert.equal(r.status, 308);
    assert.equal(r.headers.get('location'), '/wallet/');
    r = await fetch(`${base}/wallet/`);
    assert.equal(r.status, 200);
    assert.match(r.headers.get('content-security-policy'), /script-src 'self'/);
    assert.equal(r.headers.get('cache-control'), 'no-store');
    assert.equal(r.headers.get('x-frame-options'), 'DENY');
    assert.match(await r.text(), /content="proxy"/);
    r = await fetch(`${base}/wallet/lib/rpc.js`);
    assert.equal(r.headers.get('content-type'), 'text/javascript; charset=utf-8');
    for (const bad of ['/wallet/%2e%2e/package.json', '/wallet/vendor/../../package.json', '/wallet/nope.js', '/wallet/README']) {
      assert.equal((await fetch(`${base}${bad}`)).status, 404, bad);
    }
    r = await fetch(`${base}/wallet/w%201`, { method: 'POST', body: '{"method":"getbalance","params":[]}' });
    assert.deepEqual((await r.json()).result, { url: '/wallet/w%201', method: 'getbalance' });
    assert.equal(seen.at(-1).auth, 'Basic ' + Buffer.from('__cookie__:s3cret').toString('base64'));
    assert.equal((await fetch(`${base}/auth/session`)).status, 404);
    assert.equal((await fetch(`${base}/wallet/`, { method: 'PUT' })).status, 405);
  } finally {
    await close();
  }
});

test('proxy mode: node down → 502', async () => {
  const dev = createDevServer({ root: SRC, rpcUrl: 'http://127.0.0.1:1/', cookieFile });
  await new Promise((r) => dev.server.listen(0, '127.0.0.1', r));
  try {
    const r = await fetch(`http://127.0.0.1:${dev.server.address().port}/`, { method: 'POST', body: '{}' });
    assert.equal(r.status, 502);
  } finally {
    dev.server.close();
  }
});

test('session mode: token login, CSRF and Origin checks, logout', async () => {
  const { dev, base, close } = await start('session');
  const host = new URL(base).host;
  const origin = base;
  try {
    assert.match(await (await fetch(`${base}/wallet/`)).text(), /content="session"/);
    assert.equal((await fetch(`${base}/auth/session`)).status, 401);
    // RPC without a session is refused.
    assert.equal((await fetch(`${base}/`, { method: 'POST', headers: { 'Content-Type': 'application/json', Origin: origin }, body: '{}' })).status, 401);
    const post = (body, headers = {}) => fetch(`${base}/auth/session`, { method: 'POST', headers: { 'Content-Type': 'application/json', Origin: origin, ...headers }, body: JSON.stringify(body) });
    assert.equal((await post({ token: 'f'.repeat(64) })).status, 401);
    const token = dev.mintToken();
    assert.equal((await post({ token }, { Origin: 'http://evil.example' })).status, 403);
    let r = await post({ token });
    assert.equal(r.status, 200);
    const setCookie = r.headers.get('set-cookie');
    assert.match(setCookie, new RegExp(`^${dev.cookieName}=[0-9a-f]{64}; Path=/; HttpOnly; SameSite=Strict; Max-Age=2592000$`));
    const { csrf, user } = await r.json();
    assert.equal(user, '__cookie__');
    assert.equal((await post({ token })).status, 401, 'token is single use');
    const cookie = setCookie.split(';')[0];
    r = await fetch(`${base}/auth/session`, { headers: { Cookie: cookie } });
    assert.equal((await r.json()).csrf, csrf);
    // fetch() cannot set Host (a forbidden header), so use node:http for the rebinding case.
    const rebinding = await new Promise((resolve, reject) => {
      const u = new URL(`${base}/auth/session`);
      request({ host: u.hostname, port: u.port, path: u.pathname, headers: { Cookie: cookie, Host: 'evil.example:18680' } }, (res) => { res.resume(); resolve(res.statusCode); }).on('error', reject).end();
    });
    assert.equal(rebinding, 403);
    const rpc = (headers) => fetch(`${base}/`, { method: 'POST', headers: { 'Content-Type': 'application/json', Cookie: cookie, Origin: origin, 'X-CSRF-Token': csrf, ...headers }, body: '{"method":"getblockcount"}' });
    assert.equal((await rpc({})).status, 200);
    assert.equal((await rpc({ 'X-CSRF-Token': 'x' })).status, 401);
    assert.equal((await rpc({ Origin: 'http://127.0.0.1:1' })).status, 401);
    assert.equal((await rpc({ Origin: '' })).status, 401);
    assert.equal((await rpc({ 'Content-Type': 'text/plain' })).status, 401);
    // Password login, with the node judging the credentials.
    assert.equal((await post({ user: 'alice', password: 'wrong' })).status, 401);
    assert.equal((await post({ user: 'alice', password: 'pw' })).status, 200);
    // Logout requires CSRF, then the session is gone.
    assert.equal((await fetch(`${base}/auth/logout`, { method: 'POST', headers: { Cookie: cookie, Origin: origin } })).status, 401);
    r = await fetch(`${base}/auth/logout`, { method: 'POST', headers: { Cookie: cookie, Origin: origin, 'X-CSRF-Token': csrf } });
    assert.equal(r.status, 204);
    assert.equal((await rpc({})).status, 401);
    assert.equal(host.startsWith('127.0.0.1:'), true);
  } finally {
    await close();
  }
});
