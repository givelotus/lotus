import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createSessionAuth, createProxyAuth, tokenFromHash, authModeFromDocument, LoginError } from '../../src/lib/session.js';

function fakeServer() {
  const log = [];
  let session = null;
  const fetch = async (url, init = {}) => {
    const method = init.method ?? 'GET';
    const body = init.body ? JSON.parse(init.body) : null;
    log.push({ url, method, body, headers: init.headers ?? {} });
    const json = (status, obj) => new Response(obj === undefined ? null : JSON.stringify(obj), { status });
    if (url === '/auth/session' && method === 'GET') return session ? json(200, { csrf: session, user: '__cookie__', expires: 9 }) : json(401, { error: 'login required' });
    if (url === '/auth/session' && method === 'POST') {
      if (body.token === 'a'.repeat(64) || (body.user === '__cookie__' && body.password === 'deadbeef')) {
        session = 'c'.repeat(64);
        return json(200, { csrf: session, user: body.user ?? '__cookie__', expires: 9 });
      }
      return json(401, { error: 'login failed' });
    }
    if (url === '/auth/logout') { session = null; return new Response(null, { status: 204 }); }
    return json(404, {});
  };
  return { fetch, log };
}

test('status is null before login and carries csrf after', async () => {
  const s = fakeServer();
  const auth = createSessionAuth({ fetch: s.fetch });
  assert.equal(await auth.status(), null);
  assert.deepEqual(auth.headers(), {});
  const info = await auth.loginToken('a'.repeat(64));
  assert.equal(info.user, '__cookie__');
  assert.deepEqual(auth.headers(), { 'X-CSRF-Token': 'c'.repeat(64) });
  const auth2 = createSessionAuth({ fetch: s.fetch });
  assert.equal((await auth2.status()).user, '__cookie__');
  assert.deepEqual(auth2.headers(), { 'X-CSRF-Token': 'c'.repeat(64) });
});

test('password login splits a pasted cookie line at the first colon', async () => {
  const s = fakeServer();
  const auth = createSessionAuth({ fetch: s.fetch });
  await auth.loginPassword('', '__cookie__:deadbeef');
  assert.deepEqual(s.log.at(-1).body, { user: '__cookie__', password: 'deadbeef' });
  await assert.rejects(auth.loginPassword('alice', 'wrong'), (e) => e instanceof LoginError && e.status === 401 && e.message === 'login failed');
});

test('logout sends the CSRF header and forgets it; unauthorized clears it', async () => {
  const s = fakeServer();
  const auth = createSessionAuth({ fetch: s.fetch });
  await auth.loginToken('a'.repeat(64));
  await auth.logout();
  assert.equal(s.log.at(-1).headers['X-CSRF-Token'], 'c'.repeat(64));
  assert.deepEqual(auth.headers(), {});
  let called = 0;
  auth.setUnauthorizedHandler(() => called++);
  await auth.loginToken('a'.repeat(64));
  auth.onUnauthorized();
  assert.equal(called, 1);
  assert.deepEqual(auth.headers(), {});
});

test('proxy auth sends nothing and needs no login', async () => {
  const auth = createProxyAuth();
  assert.deepEqual(auth.headers(), {});
  assert.equal(auth.mode, 'proxy');
  assert.ok(await auth.status());
});

test('token from hash and auth mode from the document', () => {
  const t = 'Ab'.repeat(32);
  assert.equal(tokenFromHash(`#/login/${t}`), t.toLowerCase());
  assert.equal(tokenFromHash('#/login/abc'), null);
  assert.equal(tokenFromHash('#/overview'), null);
  const doc = (content) => ({ querySelector: () => (content === null ? null : { getAttribute: () => content }) });
  assert.equal(authModeFromDocument(doc('proxy')), 'proxy');
  assert.equal(authModeFromDocument(doc('session')), 'session');
  assert.equal(authModeFromDocument(doc('weird')), 'session');
  assert.equal(authModeFromDocument(doc(null)), 'session');
});
