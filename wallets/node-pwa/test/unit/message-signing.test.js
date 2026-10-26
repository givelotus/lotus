import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { ChainAdaptor } from '../../src/lib/chain-adaptor.js';
import { DaemonWalletMessageProvider, legacyMessageDigest, LEGACY_MESSAGE_SCHEME } from '../../src/lib/message-signing.js';
import { chainDiscovery } from '../helpers/chain-discovery.mjs';
function legacyOracle(message) {
  const domain = Buffer.from('eCash Signed Message:\n'); const text = Buffer.from(message);
  let size;
  if (text.length < 253) size = Buffer.from([text.length]);
  else { size = Buffer.alloc(3); size[0] = 253; size.writeUInt16LE(text.length, 1); }
  const preimage = Buffer.concat([Buffer.from([domain.length]), domain, size, text]);
  return createHash('sha256').update(createHash('sha256').update(preimage).digest()).digest();
}
const signature = Buffer.from([31, ...new Uint8Array(64).fill(1)]).toString('base64');
test('legacy digest preserves Qt eCash domain and exact UTF8/whitespace/CompactSize encoding', () => {
  for (const message of ['', '  Hello\n世界 \n', 'a'.repeat(252), 'a'.repeat(253), 'a'.repeat(300)]) assert.deepEqual(Buffer.from(legacyMessageDigest(message)), legacyOracle(message));
  assert.equal(LEGACY_MESSAGE_SCHEME.domain, 'eCash Signed Message:\n');
});
test('adapter chooses unchanged legacy scheme, wallet provider retains custody, verifier is node-wide', async () => {
  const calls = [];
  const rpc = { async call(method, params, options) { calls.push({ method, params, options }); if (method === 'getchainconfig') return chainDiscovery(); if (method === 'signmessage') return signature; if (method === 'verifymessage') return true; } };
  const adaptor = new ChainAdaptor({ rpc }); const provider = new DaemonWalletMessageProvider({ rpc, wallet: '' });
  const message = '  exact\nmessage \n';
  assert.equal(await adaptor.signMessage({ address: 'ecregtest:qkey', message, walletProvider: provider }), signature);
  assert.deepEqual(calls.map((c) => c.method), ['getchainconfig', 'signmessage', 'verifymessage']);
  assert.deepEqual(calls[1], { method: 'signmessage', params: ['ecregtest:qkey', message], options: { wallet: '' } });
  assert.equal(calls[2].options, undefined);
});
test('native message signing remains unsupported and never calls a wallet provider', async () => {
  let signs = 0;
  const adaptor = new ChainAdaptor({ rpc: { async call() { return chainDiscovery({ native: true }); } } });
  const caps = await adaptor.messageSigningCapabilities(); assert.equal(caps.native.supported, false);
  assert.equal(adaptor.config.features.nativeMessageSigning, false);
  await assert.rejects(adaptor.signMessage({ address: 'not-an-implemented-native-address', message: 'x', addressKind: 'native-keyhash', walletProvider: { signMessage() { signs++; } } }), /not implemented/);
  assert.equal(signs, 0);
});
test('legacy verification retains false and node errors, and never changes signature/message bytes', async () => {
  const calls = [];
  const adaptor = new ChainAdaptor({ rpc: { async call(method, params) { if (method === 'getchainconfig') return chainDiscovery(); calls.push(params); if (params[1] === 'bad') throw new Error('Malformed base64 encoding'); return false; } } });
  assert.equal(await adaptor.verifyMessage({ address: 'address', signature: ' unchanged ', message: ' \n' }), false);
  assert.deepEqual(calls[0], ['address', ' unchanged ', ' \n']);
  await assert.rejects(adaptor.verifyMessage({ address: 'address', signature: 'bad', message: '' }), /Malformed base64 encoding/);
});

test('connection invalidation prevents a stale provider result from being returned', async () => {
  let finish;
  const adaptor = new ChainAdaptor({ rpc: { async call() { return chainDiscovery(); } } });
  await adaptor.discover();
  const operation = adaptor.signMessage({ address: 'address', message: '', walletProvider: { signMessage() { return new Promise((resolve) => { finish = resolve; }); } } });
  // Let the capability lookup reach the provider without using wall-clock waits.
  for (let i = 0; i < 5 && !finish; ++i) await Promise.resolve();
  assert.ok(finish); adaptor.invalidate(); finish(signature);
  await assert.rejects(operation, /invalidated by a connection change/);
});
