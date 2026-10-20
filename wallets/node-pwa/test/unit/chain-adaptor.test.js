import { test } from 'node:test';
import assert from 'node:assert/strict';
import { ChainAdaptor, UnsupportedDiscoveryError } from '../../src/lib/chain-adaptor.js';
import { ChainConfig } from '../../src/lib/chainconfig.js';
import { RpcError } from '../../src/lib/rpc.js';
import { chainDiscovery } from '../helpers/chain-discovery.mjs';

test('one authoritative call creates one immutable config per connection even with concurrent consumers', async () => {
  const calls = [];
  const adaptor = new ChainAdaptor({ rpc: { async call(method) { calls.push(method); return chainDiscovery({ native: true }); } } });
  const [a, b] = await Promise.all([adaptor.discover(), adaptor.discover()]);
  assert.strictEqual(a, b); assert.strictEqual(await adaptor.discover(), a);
  assert.deepEqual(calls, ['getchainconfig']);
  assert.equal(a.network.kind, 'lotus-v2'); assert.equal(a.currency.rpcDecimals, 6); assert.equal(a.currency.displayDecimals, 2);
  assert.equal(a.addressFormat, 'cashaddr');
  assert.ok(Object.isFrozen(a.address.acceptedFormats)); assert.ok(Object.isFrozen(a.network));
});
test('separate sessions never share config; reconnect verifies identity and genesis', async () => {
  let raw = chainDiscovery(); let changes = 0;
  const rpc = { async call() { return raw; } };
  const a = new ChainAdaptor({ rpc, onIdentityChange() { changes++; } });
  const first = await a.discover();
  const b = new ChainAdaptor({ rpc }); assert.notStrictEqual(await b.discover(), first);
  a.invalidate(); assert.notStrictEqual(await a.discover(), first); assert.equal(changes, 0);
  raw = chainDiscovery({ genesis: 'cd'.repeat(32) });
  a.invalidate(); const changed = await a.discover();
  assert.equal(changes, 1); assert.equal(changed.network.genesis, 'cd'.repeat(32));
});
test('in-flight old discovery cannot resurrect an invalidated connection', async () => {
  let finish;
  const adaptor = new ChainAdaptor({ rpc: { call() { return new Promise((resolve) => { finish = resolve; }); } } });
  const pending = adaptor.discover(); adaptor.invalidate(); finish(chainDiscovery());
  await assert.rejects(pending, /invalidated/); assert.equal(adaptor.config, null);
});
test('unsupported discovery is explicit and does not call fallback RPCs', async () => {
  const calls = [];
  const adaptor = new ChainAdaptor({ rpc: { async call(method) { calls.push(method); throw new RpcError(-32601, 'Method not found', method); } } });
  await assert.rejects(adaptor.discover(), UnsupportedDiscoveryError);
  assert.deepEqual(calls, ['getchainconfig']);
});
test('malformed chain facts fail before consumers can select algorithms or amounts', () => {
  let raw = chainDiscovery({ native: true }); raw.chain.identifier = 'xpi-mainnet';
  assert.throws(() => new ChainConfig(raw), /identifier disagrees/);
  raw = chainDiscovery({ native: true }); raw.mining.pow.chainid = '11'.repeat(32);
  assert.throws(() => new ChainConfig(raw), /disagrees with chain identity/);
  raw = chainDiscovery(); raw.currency.atomsperunit = '1000000';
  assert.throws(() => new ChainConfig(raw), /precision disagree/);
  raw = chainDiscovery(); raw.address.format = 'xpi';
  assert.throws(() => new ChainConfig(raw), /address codec/);
  raw = chainDiscovery({ network: 'main' }); raw.mining.testgeneration = true;
  assert.throws(() => new ChainConfig(raw), /outside regtest/);
  assert.equal(new ChainConfig(chainDiscovery({ cashaddr: false })).addressFormat, 'base58check');
});
