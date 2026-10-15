import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, writeFileSync, rmSync, readFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { compilePackage, updateLock } from '../dist/packages.js';
import { compileContract } from '../dist/generic.js';

const A = '79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798';
const B = 'c6047f9441ed7d6d3045406e95c07cd85c778e4b8cef3ca7abac09b95c709ee5';
function project(main = 'import lib::wallet::{Wallet, Hold}; contract Main { entry spend() { require(contract_root(alice) != contract_root(bob)); } }', library = `export contract Wallet<owner: PublicKey> { entry spend(sig: Signature) { require(checksig(sig, owner)); } }
export contract Hold<digest: Bytes32> { entry spend(preimage: Bytes32) { require(sha256(preimage) == digest); } }`) {
  const dir = mkdtempSync(join(tmpdir(), 'lotus-lc04-'));
  mkdirSync(join(dir, 'src')); mkdirSync(join(dir, 'lib', 'src'), { recursive: true });
  writeFileSync(join(dir, 'lotus.toml'), '[package]\nname="app"\nversion="1.0.0"\nkind="contract"\nsource="src"\nmodules=["main"]\nentry="main"\n[dependencies]\nlib="lib@1.0.0"\n[sources]\nlib="lib"\n');
  writeFileSync(join(dir, 'lib', 'lotus.toml'), '[package]\nname="lib"\nversion="1.0.0"\nkind="library"\nsource="src"\nmodules=["wallet"]\nexports=["wallet"]\n');
  writeFileSync(join(dir, 'src', 'main.lotus'), main); writeFileSync(join(dir, 'lib', 'src', 'wallet.lotus'), library); updateLock(dir);
  return dir;
}
const instances = { alice: { template: 'Wallet', bindings: { owner: A } }, bob: { template: 'Wallet', bindings: { owner: B } } };
const opts = { languageVersion: 1, contract: 'Main', bindings: {}, instances };
async function withProject(fn, ...args) { const dir = project(...args); try { await fn(dir); } finally { rmSync(dir, { recursive: true, force: true }); } }

test('LC04 two bindings of one imported template coexist and match standalone roots', async () => withProject(async dir => {
  const lock = readFileSync(join(dir, 'lotus.lock'), 'utf8');
  const { artifact, parses } = await compilePackage(dir, opts);
  assert.equal(artifact.languageVersion, 1); assert.equal(artifact.links.length, 2);
  assert.equal(artifact.build.interfaceVersion, 'lotus-v2/module-interface/lc1');
  assert.deepEqual(artifact.build.instances.map(i => i.name), ['alice', 'bob']);
  assert(Object.values(parses).every(n => n === 1));
  for (const [name, owner] of [['alice', A], ['bob', B]]) {
    const single = compileContract(`contract ${name}<owner: PublicKey> { entry spend(sig: Signature) { require(checksig(sig, owner)); } }`, { languageVersion: 1, contract: name, bindings: { [name]: { owner } } });
    assert.equal(artifact.links.find(l => l.name === name).root, single.policy.root);
  }
  assert.notEqual(artifact.links[0].root, artifact.links[1].root);
  assert.equal(readFileSync(join(dir, 'lotus.lock'), 'utf8'), lock);
  const schema = JSON.parse(readFileSync(new URL('../artifact-v2.schema.json', import.meta.url), 'utf8'));
  const validation = spawnSync(process.env.LOTUS_V2_PYTHON ?? 'python3', ['-c', 'import json,sys,jsonschema; s,a=json.load(sys.stdin); jsonschema.validate(a,s)'], { input: JSON.stringify([schema, artifact]), encoding: 'utf8' });
  assert.equal(validation.status, 0, validation.stderr);
  assert.deepEqual((await compilePackage(dir, opts)).artifact, artifact);
}));

test('LC04 an imported unbound template is declaration-only and cannot supply a root', async () => {
  await withProject(async dir => {
    const artifact = (await compilePackage(dir, { languageVersion: 1, contract: 'Main', bindings: {} })).artifact;
    assert.equal(artifact.links, undefined); assert.deepEqual(artifact.build.instances, []);
  }, 'import lib::wallet::{Wallet}; contract Main { entry spend() { require(true); } }');
  await withProject(async dir => assert.rejects(compilePackage(dir, { languageVersion: 1, contract: 'Main', bindings: {} }), /explicit bound instance/), 'import lib::wallet::{Wallet}; contract Main { entry spend() { require(contract_root(Wallet) == contract_root(Wallet)); } }');
});

test('LC04 constructor root and leaf references resolve in a typed DAG', async () => withProject(async dir => {
  const configured = { ...opts, contract: 'held', instances: { alice: instances.alice, held: { template: 'Hold', bindings: { digest: { root: 'alice' } } } } };
  const artifact = (await compilePackage(dir, configured)).artifact;
  assert.equal(artifact.bindings[0].value, artifact.links.find(x => x.name === 'alice').root);
  const leaf = (await compilePackage(dir, { ...configured, instances: { ...configured.instances, held: { template: 'Hold', bindings: { digest: { leaf: 'alice.spend' } } } } })).artifact;
  assert.equal(leaf.bindings[0].value, leaf.links.find(x => x.name === 'alice').methods[0].leaf);
}, 'import lib::wallet as wallet; import lib::wallet::{Wallet, Hold}; contract Main { entry spend() { require(true); } }'));

test('LC04 missing, surplus, duplicate, unresolved, wrong-type and unsupported bindings reject', async () => withProject(async dir => {
  for (const bad of [
    { ...instances.alice, bindings: {} }, { ...instances.alice, bindings: { owner: A, extra: A } },
    { ...instances.alice, bindings: { owner: { root: 'bob' } } }, { ...instances.alice, template: 'Absent' },
    { ...instances.alice, state: {} }, { ...instances.alice, bindings: { owner: { state: 'alice' } } },
    { ...instances.alice, bindings: { owner: '00' } }
  ]) await assert.rejects(compilePackage(dir, { ...opts, instances: { ...instances, alice: bad } }));
  await assert.rejects(compilePackage(dir, { ...opts, bindings: { alice: { owner: A } } }), /duplicate/);
  await assert.rejects(compilePackage(dir, { ...opts, languageVersion: 0 }), /languageVersion 1/);
}));

test('LC04 aliases and constructor-bound root cycles reject before emission', async () => {
  await withProject(async dir => {
    for (const configured of [
      { a: { template: 'Hold', bindings: { digest: { root: 'a' } } } },
      { a: { template: 'Hold', bindings: { digest: { root: 'b' } } }, b: { template: 'Hold', bindings: { digest: { root: 'a' } } } }
    ]) await assert.rejects(compilePackage(dir, { languageVersion: 1, contract: 'a', bindings: {}, instances: configured }), e => e.code === 'root-cycle');
  }, 'import lib::wallet::{Hold}; contract Main { entry spend() { require(true); } }');
  await withProject(async dir => assert.rejects(compilePackage(dir, { languageVersion: 1, contract: 'a', bindings: {}, instances: { a: { template: 'First', bindings: {} }, b: { template: 'Second', bindings: { digest: { root: 'a' } } } } }), e => e.code === 'root-cycle'),
    'import lib::wallet::{First as First, Second}; contract Main { entry spend() { require(true); } }',
    'export contract First { entry spend() { require(contract_root(b) == contract_root(b)); } } export contract Second<digest: Bytes32> { entry spend(x: Bytes32) { require(x == digest); } }');
});


test('LC04 module aliases resolve the same template and interface advertises invocation', async () => withProject(async dir => {
  const artifact = (await compilePackage(dir, { ...opts, instances: { alice: { ...instances.alice, template: 'wallet::Wallet' }, bob: { ...instances.bob, template: 'Alias' } } })).artifact;
  assert.equal(artifact.build.modules.find(m => m.path === 'wallet').exports.find(x => x.name === 'Wallet').signature.includes('spend spend'), true);
  assert.notEqual(artifact.links[0].root, artifact.links[1].root);
}, 'import lib::wallet as wallet; import lib::wallet::{Wallet as Alias}; contract Main { entry spend() { require(contract_root(alice) != contract_root(bob)); } }'));

test('LC04 malformed unused explicit bindings and self-root aliases also reject', async () => {
  await withProject(async dir => assert.rejects(compilePackage(dir, { ...opts, instances: { ...instances, unused: { template: 'Wallet', bindings: { owner: '00' } } } })));
  await withProject(async dir => assert.rejects(compilePackage(dir, { languageVersion: 1, contract: 'looped', bindings: {}, instances: { looped: { template: 'Alias', bindings: {} } } }), e => e.code === 'root-cycle'),
    'import lib::wallet::{Wallet as Alias}; contract Main { entry spend() { require(true); } }',
    'export contract Wallet { entry spend() { require(contract_root(Wallet) == contract_root(Wallet)); } }');
});
