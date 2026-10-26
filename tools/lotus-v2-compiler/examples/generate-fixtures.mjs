import { writeFileSync } from 'node:fs';
import { schnorr } from '@noble/curves/secp256k1';
import { compilePayment, PAYMENT_SOURCE } from '../dist/compiler.js';
import { buildPaymentFixture } from '../dist/fixtures.js';

const scenarios = [
  { name: 'key3-one-output', key: 3, coinValue: 2000n, values: [1000n], txidByte: '11', lock: 0n },
  { name: 'key4-two-outputs', key: 4, coinValue: 300000n, values: [60000n, 239000n], txidByte: '22', lock: 1n },
];
for (const s of scenarios) {
  const secret = Buffer.alloc(32); secret[31] = s.key;
  const owner = Buffer.from(schnorr.getPublicKey(secret)).toString('hex');
  const branch = compilePayment(PAYMENT_SOURCE, owner).policy.leaf;
  const policy = { flags: 0, branches: [branch], paths: [[0]] };
  const fixture = buildPaymentFixture({ source: PAYMENT_SOURCE, owner, testSecret: secret.toString('hex'),
    chainId: Buffer.from(Array.from({ length: 32 }, (_, i) => i)).toString('hex'),
    outpoint: { txid: s.txidByte.repeat(32), index: 0 }, sequence: 0xffffffff, lock: s.lock,
    coin: { ...policy, value: s.coinValue }, outputs: s.values.map(value => ({ ...policy, value })),
    profile: 'payment-fixture-p01-v1', signingMode: 0 });
  writeFileSync(new URL(`../fixtures/${s.name}.json`, import.meta.url), JSON.stringify(fixture, null, 2) + '\n');
}
