import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, writeFileSync, unlinkSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { pathToFileURL } from 'node:url';
import ts from 'typescript';
import { generateContractTypeScript, generateContractPython } from '../dist/bindings.js';
import { hex, unhex } from '../dist/compiler.js';

const fixtureUrl = new URL('../fixtures/generic-payment-v2.json', import.meta.url);
const fixture = JSON.parse(readFileSync(fixtureUrl));
function contextFromFixture() {
  const output = value => ({ value: BigInt(value.valueAtoms), branches: value.branches, paths: value.paths });
  return { profile: fixture.context.profile, chainId: fixture.context.chainId,
    prevTxid: fixture.context.prevTxid, prevIndex: fixture.context.prevIndex, sequence: fixture.context.sequence,
    coin: output(fixture.context.coin), outputs: fixture.context.outputs.map(output) };
}

test('generated TypeScript wrapper prepares and finalizes signed schema 2 Payment', async () => {
  const path = new URL('./GeneratedContractPayment.mjs', import.meta.url);
  const source = generateContractTypeScript(fixture.artifact);
  const javascript = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext } }).outputText;
  writeFileSync(path, javascript);
  try {
    const { Payment } = await import(`${pathToFileURL(path.pathname)}?run=${Date.now()}`);
    const client = new Payment(fixture.artifact);
    const plan = client.prepareSpend(contextFromFixture(), { signature: null });
    assert.equal(plan.requests.length, 1);
    assert.equal(plan.requests[0].digest, fixture.valid.message);
    assert.equal(plan.requests[0].leaf, fixture.valid.leaf);
    assert.equal(plan.requests[0].feeAtoms.toString(), fixture.valid.feeAtoms);
    const result = client.finalizeSpend(plan, { signature: unhex(fixture.valid.signature) });
    assert.equal(hex(result.wire), fixture.valid.wire);
    assert.equal(result.txid, fixture.valid.txid);
    assert.equal(result.txhash, fixture.valid.txhash);
    assert.throws(() => client.finalizeSpend({ ...plan, methodName: 'other' }, { signature: unhex(fixture.valid.signature) }), /method plan mismatch/);
  } finally { unlinkSync(path); }
});

test('generated Python wrapper prepares and finalizes the same signed call', t => {
  const python = process.env.LOTUS_V2_PYTHON ?? 'python3';
  const probe = spawnSync(python, ['-c', 'import blake3'], { encoding: 'utf8' });
  if (probe.status !== 0) { t.skip('install python/requirements.txt and set LOTUS_V2_PYTHON'); return; }
  const path = new URL('./GeneratedContractPayment.py', import.meta.url);
  writeFileSync(path, generateContractPython(fixture.artifact));
  try {
    const run = spawnSync(python, ['test/python-generated-call-run.py', path.pathname, fixtureUrl.pathname], { encoding: 'utf8',
      env: { ...process.env, PYTHONPATH: new URL('../python/', import.meta.url).pathname } });
    assert.equal(run.status, 0, run.stderr);
    const actual = JSON.parse(run.stdout);
    assert.deepEqual(actual, { wire: fixture.valid.wire, txid: fixture.valid.txid, txhash: fixture.valid.txhash,
      digest: fixture.valid.message, leaf: fixture.valid.leaf, feeAtoms: fixture.valid.feeAtoms });
  } finally { unlinkSync(path); }
});
