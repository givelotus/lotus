import { test } from 'node:test';
import assert from 'node:assert/strict';
import { validateMiningDescriptor } from '../../src/lib/chainconfig.js';
import { chainDiscovery } from '../helpers/chain-discovery.mjs';

test('mining algorithm descriptor uses exact compiled layout and cannot inject an RPC or scheme', () => {
  const pow = chainDiscovery().mining.pow;
  assert.equal(validateMiningDescriptor(pow).algorithm, 'sha256d');
  assert.throws(() => validateMiningDescriptor({ ...pow, algorithm: 'constructor' }), /unsupported proof/);
  assert.throws(() => validateMiningDescriptor({ ...pow, algorithm: 'sha256' }), /unsupported proof/);
  assert.throws(() => validateMiningDescriptor({ ...pow, nonceoffset: 42 }), /layout/);
  assert.throws(() => validateMiningDescriptor({ ...pow, hashbyteorder: 'big' }), /byte order/);
  assert.throws(() => validateMiningDescriptor({ ...pow, template_rpc: 'evalcode' }), /RPC contract/);
  assert.throws(() => validateMiningDescriptor({ ...pow, algorithm: 'lotus-v2-blockid', headerbytes: 134, nonceoffset: 42, noncebytes: 8 }), /chain identifier/);
});

test('native wallet receiving is explicit, validated and immutable', async () => {
  const { ChainConfig } = await import('../../src/lib/chainconfig.js');
  const { chainDiscovery } = await import('../helpers/chain-discovery.mjs');
  const raw = chainDiscovery({ native: true });
  assert.equal(new ChainConfig(raw).wallet.nativeReceiving, false);
  raw.wallet = { native_receiving: { available: true, address_type: 'native', format: 'xpiaddr', template: 'keyhash' } };
  const config = new ChainConfig(raw);
  assert.equal(config.wallet.nativeReceiving, true); assert.ok(Object.isFrozen(config.wallet));
  raw.wallet.native_receiving.template = 'arbitrary';
  assert.throws(() => new ChainConfig(raw), /Unsupported native wallet receiving/);
  const legacy = chainDiscovery(); legacy.wallet = { native_receiving: { available: true, address_type: 'native', format: 'xpiaddr', template: 'keyhash' } };
  assert.throws(() => new ChainConfig(legacy), /Unsupported native wallet receiving/);
});

test('native payout codec requires the explicit discovered prefix on every supported network', async () => {
  const { ChainConfig } = await import('../../src/lib/chainconfig.js');
  const { chainDiscovery } = await import('../helpers/chain-discovery.mjs');
  for (const [network, hrp] of [['main', 'xpi'], ['test', 'txpi'], ['regtest', 'rxpi']]) {
    const raw = chainDiscovery({ native: true, network });
    const config = new ChainConfig(raw);
    assert.equal(config.address.nativeHrp, hrp);
    assert.equal(config.wallet.nativeReceiving, false); // manual native payout remains available without wallet support
    assert.equal(config.address.format, 'cashaddr');
    assert.ok(config.address.acceptedFormats.includes('xpiaddr'));
    delete raw.address.nativehrp;
    assert.throws(() => new ChainConfig(raw), /codec and prefix disagree/);
    raw.address.acceptedformats = ['cashaddr', 'base58check'];
    assert.equal(new ChainConfig(raw).address.nativeHrp, null); // no inferred native prefix
    raw.wallet = { native_receiving: { available: true, address_type: 'native', format: 'xpiaddr', template: 'keyhash' } };
    assert.throws(() => new ChainConfig(raw), /Unsupported native wallet receiving/);
  }
  const wrong = chainDiscovery({ native: true }); wrong.address.nativehrp = 'xpi';
  assert.throws(() => new ChainConfig(wrong), /disagrees with network/);
  const legacy = chainDiscovery(); legacy.address.acceptedformats.push('xpiaddr'); legacy.address.nativehrp = 'rxpi';
  assert.throws(() => new ChainConfig(legacy), /Unsupported address codec/);
});
