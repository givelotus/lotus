import { test } from 'node:test';
import assert from 'node:assert/strict';
import { resolveChainConfig, validateMiningDescriptor } from '../../src/lib/chainconfig.js';
const pow = { version: 1, algorithm: 'sha256d', headerbytes: 80, nonceoffset: 76, noncebytes: 4,
  noncebyteorder: 'little', hashbyteorder: 'little', targetbyteorder: 'big', template_rpc: 'getrawunsolvedblock', submit_rpc: 'submitblock' };
const base = { chain: 'regtest', profile: 'ecash', currency: { ticker: 'XEC', decimals: 2, satoshisperunit: 100 }, addressFormat: 'cashaddr', hrp: null, client: 'node', version: 1 };
test('ChainConfig is immutable and older nodes keep wallet/regtest capabilities without GPU guesses', () => {
  const cfg = resolveChainConfig(base);
  assert.ok(Object.isFrozen(cfg)); assert.ok(Object.isFrozen(cfg.currency));
  assert.equal(cfg.currency.atomicUnitsPerCoin, '100');
  assert.equal(cfg.rpc.testBlockGeneration, true);
  assert.equal(cfg.mining.supported, false);
  assert.equal(resolveChainConfig({ ...base, chain: 'main' }).rpc.testBlockGeneration, false);
});
test('mining algorithms require exact node descriptor independent of ticker', () => {
  assert.equal(resolveChainConfig({ ...base, currency: { ticker: 'anything', decimals: 2 }, miningInfo: { pow } }).mining.descriptor.algorithm, 'sha256d');
  assert.throws(() => validateMiningDescriptor({ ...pow, algorithm: 'sha256' }), /unsupported proof/);
  assert.throws(() => validateMiningDescriptor({ ...pow, nonceoffset: 42 }), /layout/);
  assert.throws(() => validateMiningDescriptor({ ...pow, hashbyteorder: 'big' }), /byte order/);
  assert.throws(() => validateMiningDescriptor({ ...pow, template_rpc: 'evalcode' }), /RPC contract/);
  assert.throws(() => validateMiningDescriptor({ ...pow, algorithm: 'lotus-v2-blockid', headerbytes: 134, nonceoffset: 42, noncebytes: 8 }), /chain identifier/);
  assert.equal(validateMiningDescriptor({ ...pow, algorithm: 'lotus-v2-blockid', headerbytes: 134, nonceoffset: 42, noncebytes: 8, chainid: 'ab'.repeat(32) }).chainid, 'ab'.repeat(32));
});
test('currency unit mismatches fail without silently rescaling values', () => {
  assert.throws(() => resolveChainConfig({ ...base, currency: { ticker: 'XPI', decimals: 8, satoshisperunit: 100 } }), /disagree/);
});
