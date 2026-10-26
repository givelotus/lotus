import { readFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';

const executable = process.argv[2];
if (!executable) throw new Error('usage: node test/run-native-generic-fixture.mjs NATIVE_CHECK_EXECUTABLE');
const f = JSON.parse(readFileSync(new URL('../fixtures/generic-payment-v2.json', import.meta.url)));
const run = spawnSync(executable, [f.valid.wire, f.context.coinWire, f.context.chainId, f.publicTestKey,
  f.valid.txid, f.valid.txhash, f.valid.message, 'valid'], { encoding: 'utf8' });
if (run.status !== 0) throw new Error(run.stderr);
console.log('generic Payment: native proof/framing/identities/signature checks passed');
