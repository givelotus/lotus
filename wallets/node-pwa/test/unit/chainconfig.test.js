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
