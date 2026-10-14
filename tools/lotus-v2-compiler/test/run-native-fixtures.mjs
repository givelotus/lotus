import { readFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';

const executable = process.argv[2];
if (!executable) throw new Error('usage: node test/run-native-fixtures.mjs NATIVE_CHECK_EXECUTABLE');
for (const name of ['key3-one-output', 'key4-two-outputs']) {
  const f = JSON.parse(readFileSync(new URL(`../fixtures/${name}.json`, import.meta.url)));
  function check(wire, coinWire, chainId, owner, txid, txhash, message, expected) {
    const run = spawnSync(executable, [wire, coinWire, chainId, owner, txid, txhash, message, expected], { encoding: 'utf8' });
    if (run.status !== 0) throw new Error(`${name}/${expected}: ${run.stderr}`);
  }
  check(f.valid.wire, f.context.coinWire, f.context.chainId, f.artifact.scriptHex.slice(2, 66),
    f.valid.txid, f.valid.txhash, f.valid.message, 'valid');
  for (const m of f.mutations) check(m.wire, m.context.coinWire, m.context.chainId, m.context.owner, '-', '-', '-', 'invalid');
  console.log(`${name}: native framing/identity/signature checks passed (valid + 3 mutations)`);
}
