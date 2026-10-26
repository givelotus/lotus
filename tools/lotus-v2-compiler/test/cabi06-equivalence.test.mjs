import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { compileContract } from '../dist/generic.js';

const corpus = JSON.parse(readFileSync(new URL('../fixtures/optimizer-equivalence/corpus.json', import.meta.url)));
const signature = 'e907831f80848d1069a5371b402410364bdf1c5f8307b0084c55f1ce2dca8215' +
  '25f66a4a85ea8b71e482a74f382d2ce5ebeee8fdb2172f477df4900d310536c0';
function encode(value) {
  if (value.startsWith('raw:')) return value.slice(4);
  if (value === 'signature') return signature;
  if (value === 'bad-signature') return '00' + signature.slice(2);
  const n = value === 'max' ? (1n << 127n)-1n : value === 'min' ? -(1n << 127n) : BigInt(value);
  let x = BigInt.asUintN(128, n), hex = '';
  for (let i=0; i<16; i++, x >>= 8n) hex += Number(x & 255n).toString(16).padStart(2,'0');
  return hex;
}
test('CABI06 corpus preserves VM semantics and retains exact-profile cost boundary disagreements', () => {
  const cases = corpus.cases.map(c => {
    const options = { contract:'C', bindings:c.bindings ?? {} };
    const before = compileContract(c.source, {...options, optimize:false}).methods[0].scriptHex;
    const after = compileContract(c.source, options).methods[0].scriptHex;
    return {...c, args:c.args.map(args => args.map(encode)), before, after};
  });
  const python = process.env.LOTUS_V2_PYTHON ?? 'python3';
  const reference = new URL('../../lotus-v2-reference/', import.meta.url).pathname;
  const run = spawnSync(python, [new URL('./cabi06-reference.py', import.meta.url).pathname], {
    encoding:'utf8', timeout:30000, maxBuffer:4*1024*1024,
    env:{...process.env, PYTHONPATH:reference}, input:JSON.stringify({...corpus, cases}),
  });
  assert.equal(run.status, 0, run.stderr || run.stdout);
  const observations = JSON.parse(run.stdout);
  assert.equal(observations.length, 24);
  assert.ok(observations.some(o => o.before.root !== o.after.root));
  assert.ok(observations.some(o => o.before.accounting !== o.after.accounting));
  assert.ok(observations.some(o => o.boundaries.some(([a,b]) => a.status !== b.status)),
    'resource boundary acceptance differs: retain this CABI06 obligation');
  assert.ok(cases.find(c => c.name === 'checksigverify').after.includes('bc'));
  for (const o of observations) {
    assert.equal(o.before.accounting, o.before.enforcement);
    assert.equal(o.after.accounting, o.after.enforcement);
  }
  const retained = JSON.parse(readFileSync(new URL('../fixtures/optimizer-equivalence/observations.json', import.meta.url)));
  assert.deepEqual({schema:corpus.schema, cases, observations}, retained,
    'retained discrepancies changed; investigate rather than regenerate');
});
