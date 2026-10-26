import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, writeFileSync, unlinkSync, mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';
import { spawnSync } from 'node:child_process';
import ts from 'typescript';
import { buildPaymentFixture } from '../dist/fixtures.js';
import { generatePython, generateTypeScript } from '../dist/bindings.js';
import { hex, unhex } from '../dist/compiler.js';

const cases = ['key3-one-output', 'key4-two-outputs'];
function fixture(name) { return JSON.parse(readFileSync(new URL(`../fixtures/${name}.json`, import.meta.url))); }
function contextFromJson(f) {
  const output = o => ({ value: BigInt(o.valueAtoms), flags: 0, branches: o.branches, paths: o.paths });
  return { profile: f.context.profile, chainId: f.context.chainId, prevTxid: f.context.outpoint.txid,
    prevIndex: f.context.outpoint.index, sequence: f.context.sequence, lock: BigInt(f.context.lock), coin: output(f.context.coin), outputs: f.context.outputs.map(output) };
}

test('two policies and distinct output counts reproduce offline fixtures', () => {
  const [a, b] = cases.map(fixture);
  assert.notEqual(a.artifact.policy.leaf, b.artifact.policy.leaf);
  assert.equal(a.context.outputs.length, 1);
  assert.equal(b.context.outputs.length, 2);
  for (const [idx, f] of [a, b].entries()) {
    const secret = '00'.repeat(31) + (idx + 3).toString(16).padStart(2, '0');
    const result = buildPaymentFixture({ source: f.source, owner: f.artifact.scriptHex.slice(2, 66), testSecret: secret,
      chainId: f.context.chainId, outpoint: f.context.outpoint, sequence: f.context.sequence, lock: BigInt(f.context.lock),
      coin: contextFromJson(f).coin, outputs: contextFromJson(f).outputs, profile: f.context.profile, signingMode: 0 });
    assert.deepEqual(result, f);
    assert.deepEqual(f.mutations.map(m => m.name), ['changed-output-value', 'changed-chain-id', 'changed-owner']);
    assert(f.mutations.every(m => m.expectedReason === 'signature verification failed'));
  }
  const independent = JSON.parse(readFileSync(new URL('../fixtures/reference-signed-payment-v1.json', import.meta.url)));
  assert.equal(a.valid.wire, independent.wire);
  assert.equal(a.valid.txid, independent.txid);
});

test('generated TypeScript binding executes signed call and matches witness bytes', async () => {
  const f = fixture(cases[1]);
  const generated = new URL('./GeneratedPayment.mjs', import.meta.url);
  const js = ts.transpileModule(generateTypeScript(f.artifact), { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext } }).outputText;
  writeFileSync(generated, js);
  try {
    const module = await import(`${pathToFileURL(generated.pathname)}?run=${Date.now()}`);
    const client = new module.Payment(f.artifact);
    const plan = client.prepareSpend(contextFromJson(f));
    const result = client.finalizeSpend(plan, unhex(f.valid.signature));
    assert.equal(hex(result.wire), f.valid.wire);
    assert.equal(result.txid, f.valid.txid);
  } finally { unlinkSync(generated); }
});

test('generated Python binding executes call through documented runtime and matches witness bytes', () => {
  const f = fixture(cases[1]);
  const dir = mkdtempSync(join(tmpdir(), 'lotus-payment-python-'));
  try {
    const generated = join(dir, 'Payment.py');
    const json = join(dir, 'fixture.json');
    writeFileSync(generated, generatePython(f.artifact));
    writeFileSync(json, JSON.stringify(f));
    const run = spawnSync('python3', [new URL('./python-binding-run.py', import.meta.url).pathname, generated, json], { encoding: 'utf8' });
    assert.equal(run.status, 0, run.stderr);
    assert.match(run.stdout, /witness bytes match/);
  } finally { rmSync(dir, { recursive: true, force: true }); }
});

test('offline JSON CLI accepts explicit profile/coins and emits stable fixture', () => {
  const f = fixture(cases[1]);
  const dir = mkdtempSync(join(tmpdir(), 'lotus-payment-cli-'));
  try {
    const input = join(dir, 'input.json'); const output = join(dir, 'output.json');
    writeFileSync(input, JSON.stringify({ schema: 'lotus-v2/payment-fixture-input/1', source: f.source,
      owner: f.artifact.scriptHex.slice(2, 66), testSecret: '00'.repeat(31) + '04', chainId: f.context.chainId,
      outpoint: f.context.outpoint, sequence: f.context.sequence, lock: f.context.lock,
      coin: f.context.coin, outputs: f.context.outputs, profile: f.context.profile, signingMode: 0 }));
    const run = spawnSync('node', ['dist/fixture-cli.js', input, output], { cwd: new URL('..', import.meta.url).pathname, encoding: 'utf8' });
    assert.equal(run.status, 0, run.stderr);
    assert.deepEqual(JSON.parse(readFileSync(output)), f);
  } finally { rmSync(dir, { recursive: true, force: true }); }
});

test('fixture builder rejects implicit key, partial mode and malformed locks', () => {
  const f = fixture(cases[0]);
  const base = { source: f.source, owner: f.artifact.scriptHex.slice(2, 66), testSecret: '00'.repeat(31) + '03',
    chainId: f.context.chainId, outpoint: f.context.outpoint, sequence: f.context.sequence, lock: 0n,
    coin: contextFromJson(f).coin, outputs: contextFromJson(f).outputs, profile: f.context.profile, signingMode: 0 };
  assert.throws(() => buildPaymentFixture({ ...base, signingMode: 1 }), /FULL signing mode 0 only/);
  assert.throws(() => buildPaymentFixture({ ...base, testSecret: '00'.repeat(31) + '04' }), /owner does not match/);
  assert.throws(() => buildPaymentFixture({ ...base, lock: 3n }), /invalid P01 lock/);
  assert.throws(() => buildPaymentFixture({ ...base, sequence: 0x80000000 }), /invalid P01 sequence/);
});
