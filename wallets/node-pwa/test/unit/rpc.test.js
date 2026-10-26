import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createRpc, RpcError, HttpError, NetworkError, describeError } from '../../src/lib/rpc.js';
import { Decimal } from '../../src/lib/json.js';

function mockFetch(handler) {
  const seen = [];
  const fetch = async (url, init) => {
    seen.push({ url, init, body: init.body ? JSON.parse(init.body) : null });
    const r = await handler(url, init, JSON.parse(init.body));
    return new Response(typeof r.body === 'string' ? r.body : JSON.stringify(r.body), { status: r.status ?? 200 });
  };
  return { fetch, seen };
}
const auth = (headers = {}) => ({ headers: () => headers, unauth: 0, onUnauthorized() { this.unauth++; } });

test('call posts JSON-RPC 1.0 to / or /wallet/<name> with auth headers', async () => {
  const m = mockFetch((url, init, body) => ({ body: `{"result":{"balance":50000000.00},"error":null,"id":${body.id}}` }));
  const a = auth({ 'X-CSRF-Token': 'abc' });
  const rpc = createRpc({ auth: a, fetch: m.fetch });
  const r = await rpc.call('getwalletinfo', [], { wallet: 'my wallet/1' });
  assert.ok(r.balance instanceof Decimal);
  assert.equal(r.balance.toString(), '50000000.00');
  await rpc.call('getblockcount');
  await rpc.call('getbalance', [], { wallet: '' });
  assert.equal(m.seen[0].url, '/wallet/my%20wallet%2F1');
  assert.equal(m.seen[1].url, '/');
  assert.equal(m.seen[2].url, '/wallet/');
  assert.equal(m.seen[0].init.headers['Content-Type'], 'application/json');
  assert.equal(m.seen[0].init.headers['X-CSRF-Token'], 'abc');
  assert.equal(m.seen[0].init.credentials, 'same-origin');
  assert.equal(m.seen[0].body.jsonrpc, '1.0');
  assert.equal(m.seen[0].body.method, 'getwalletinfo');
});

test('decimal parameters are sent as exact numbers', async () => {
  let raw;
  const rpc = createRpc({ auth: auth(), fetch: async (u, init) => { raw = init.body; return new Response('{"result":null,"error":null,"id":1}'); } });
  await rpc.call('settxfee', [new Decimal('0.10')]);
  assert.match(raw, /"params":\[0\.10\]/);
});

test('JSON-RPC errors (HTTP 500/404 bodies) become RpcError', async () => {
  const rpc = createRpc({ auth: auth(), fetch: async () => new Response('{"result":null,"error":{"code":-18,"message":"Requested wallet does not exist or is not loaded"},"id":1}', { status: 500 }) });
  await assert.rejects(rpc.call('getwalletinfo'), (e) => e instanceof RpcError && e.code === -18 && e.method === 'getwalletinfo');
  assert.match(describeError(new RpcError(-5, 'Invalid address', 'x')), /Invalid address \(code -5\)/);
});

test('warm-up -28 is reported', async () => {
  let warm = null;
  const rpc = createRpc({ auth: auth(), onWarmup: (m) => { warm = m; }, fetch: async () => new Response('{"result":null,"error":{"code":-28,"message":"Loading block index..."},"id":1}', { status: 500 }) });
  await assert.rejects(rpc.call('getblockcount'), (e) => e.code === -28);
  assert.equal(warm, 'Loading block index...');
});

test('401 tells the auth layer, 403 is not permitted, other HTTP errors keep status', async () => {
  const a = auth();
  let status = 401;
  const rpc = createRpc({ auth: a, fetch: async () => new Response('', { status }) });
  await assert.rejects(rpc.call('x'), (e) => e instanceof HttpError && e.status === 401);
  assert.equal(a.unauth, 1);
  status = 403;
  await assert.rejects(rpc.call('x'), (e) => e instanceof HttpError && e.status === 403 && /not permitted/.test(e.message));
  status = 405;
  await assert.rejects(rpc.call('x'), (e) => e instanceof HttpError && e.status === 405);
  assert.equal(a.unauth, 1);
});

test('network failure → NetworkError and callback; success → reachable', async () => {
  let net = 0, ok = 0, fail = true;
  const rpc = createRpc({
    auth: auth(), onNetworkError: () => net++, onReachable: () => ok++,
    fetch: async () => { if (fail) throw new TypeError('Failed to fetch'); return new Response('{"result":1,"error":null,"id":1}'); },
  });
  await assert.rejects(rpc.call('x'), NetworkError);
  assert.equal(net, 1);
  fail = false;
  assert.equal(await rpc.call('x'), 1);
  assert.equal(ok, 1);
});

test('timeout aborts the request', async () => {
  const rpc = createRpc({
    auth: auth(),
    fetch: (u, init) => new Promise((_, rej) => init.signal.addEventListener('abort', () => rej(init.signal.reason))),
  });
  await assert.rejects(rpc.call('waitfornewblock', [], { timeoutMs: 20 }), (e) => e instanceof NetworkError && /timed out/.test(e.message));
});

test('batch returns results in input order, matched by id, errors per call', async () => {
  const m = mockFetch((url, init, body) => ({
    body: body.slice().reverse().map((c) => c.method === 'bad'
      ? { result: null, error: { code: -32601, message: 'Method not found' }, id: c.id }
      : { result: c.method + ':' + c.params.join(','), error: null, id: c.id }),
  }));
  const rpc = createRpc({ auth: auth(), fetch: m.fetch });
  const out = await rpc.batch([['a', [1]], ['bad'], ['c', [2, 3]]], { wallet: 'w' });
  assert.equal(out[0], 'a:1');
  assert.ok(out[1] instanceof RpcError && out[1].code === -32601 && out[1].method === 'bad');
  assert.equal(out[2], 'c:2,3');
  assert.equal(m.seen[0].url, '/wallet/w');
  assert.equal(m.seen[0].body.length, 3);
  assert.deepEqual(await rpc.batch([]), []);
});

test('batch with a missing reply or a whole-batch error object', async () => {
  let reply = '[{"result":1,"error":null,"id":1}]';
  const rpc = createRpc({ auth: auth(), fetch: async () => new Response(reply) });
  const out = await rpc.batch([['a'], ['b']]);
  assert.equal(out[0], 1);
  assert.ok(out[1] instanceof RpcError && /missing/.test(out[1].message));
  reply = '{"result":null,"error":{"code":-32600,"message":"nope"},"id":null}';
  const out2 = await rpc.batch([['a'], ['b']]);
  assert.ok(out2.every((e) => e instanceof RpcError && e.code === -32600));
});
