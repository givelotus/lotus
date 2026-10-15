import test from 'node:test';
import assert from 'node:assert/strict';
import { cpSync, mkdtempSync, mkdirSync, readFileSync, readdirSync, renameSync, rmSync, symlinkSync, writeFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { compileContract } from '../dist/generic.js';
import { COMPILER_VERSION, compilePackage, generateLock, updateLock } from '../dist/packages.js';

const fixture = fileURLToPath(new URL('../examples/packages/diamond/', import.meta.url));
const options = JSON.parse(readFileSync(join(fixture, 'options.json'), 'utf8'));
const python = process.env.LOTUS_V2_PYTHON ?? 'python3';
const dist = fileURLToPath(new URL('../dist/', import.meta.url));

function copy() {
  const base = mkdtempSync(join(tmpdir(), 'lotus-pkg-'));
  const dir = join(base, 'project');
  cpSync(fixture, dir, { recursive: true });
  return { base, dir };
}
function edit(dir, rel, change, relock = false) {
  const path = join(dir, rel);
  writeFileSync(path, change(readFileSync(path, 'utf8')));
  if (relock) updateLock(dir);
}
async function rejects(dir, code, check = () => true, opts = options) {
  await assert.rejects(compilePackage(dir, opts), error => {
    assert.equal(error.code, code, error.message);
    assert(check(error), error.message);
    return true;
  });
}
const flattened = `
function nonNegative(x: Amount): Bool { return x >= 0; }
function checkedAdd(a: Amount, b: Amount): Amount { return a + b; }
function atLeast(x: Amount, floor: Amount): Bool { return nonNegative(x) && x >= floor; }
function budgetOk(spent: Amount, extra: Amount, budget: Amount): Bool { return atLeast(budget, checkedAdd(spent, extra)); }
function paid(value: Amount, fee: Amount, minimum: Amount): Bool { return atLeast(checkedAdd(value, fee), minimum); }
function opens(preimage: Bytes32, digest: Bytes32): Bool { return sha256(preimage) == digest; }
function authorized(sig: Signature, owner: PublicKey): Bool { return checksig(sig, owner); }
contract Treasury<owner: PublicKey, digest: Bytes32, budget: Amount> {
    function spend(sig: Signature, spent: Amount, extra: Amount) { require(budgetOk(spent, extra, budget)); require(authorized(sig, owner)); }
    function reveal(preimage: Bytes32, value: Amount, fee: Amount) { require(opens(preimage, digest)); require(paid(value, fee, budget)); }
}`;

test('diamond package builds offline, parses each module identity once and matches a flattened single file', async () => {
  const { artifact, trace, parses } = await compilePackage(fixture, options);
  assert.deepEqual(Object.values(parses), Object.values(parses).map(() => 1));
  assert.equal(parses['core@1.0.0/amounts'], 1);
  assert.equal(trace.filter(e => e.kind === 'start' && e.job === 'module:core@1.0.0/amounts').length, 1);
  for (const parent of ['module:lib_a@1.0.0/limits', 'module:lib_b@1.0.0/digests'])
    assert(trace.some(e => e.kind === 'await' && e.job === parent && e.dependency === 'module:core@1.0.0/amounts'));
  const modules = artifact.build.modules.map(m => m.id);
  assert.deepEqual(modules, ['app@0.1.0/main', 'app@0.1.0/policy', 'core@1.0.0/amounts', 'core@1.0.0/internal', 'lib_a@1.0.0/limits', 'lib_b@1.0.0/digests']);
  assert.deepEqual(artifact.build.packages.map(p => p.id), ['app@0.1.0', 'core@1.0.0', 'lib_a@1.0.0', 'lib_b@1.0.0']);
  assert.equal(artifact.build.compiler.version, COMPILER_VERSION);
  assert.equal(COMPILER_VERSION, JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8')).version);
  assert(!JSON.stringify(artifact).includes(fixture), 'artifact must not contain absolute paths');
  // Imported helpers expand exactly like the equivalent single-file source.
  const single = compileContract(flattened, options);
  assert.deepEqual(artifact.methods.map(m => [m.name, m.scriptHex, m.leaf]), single.methods.map(m => [m.name, m.scriptHex, m.leaf]));
  assert.equal(artifact.policy.root, single.policy.root);
  assert(artifact.methods[0].sourceMap.some(entry => entry.source.module === 'core@1.0.0/internal'));
  assert.equal(single.build, undefined);
  assert(single.methods.every(m => m.sourceMap.every(entry => !('module' in entry.source))));
});

test('package artifacts are byte-identical across runs and checkouts, match the golden file and lock', async () => {
  const first = JSON.stringify((await compilePackage(fixture, options)).artifact, null, 2) + '\n';
  const again = JSON.stringify((await compilePackage(fixture, options)).artifact, null, 2) + '\n';
  const { dir } = copy();
  const moved = JSON.stringify((await compilePackage(dir, options)).artifact, null, 2) + '\n';
  assert.equal(first, again); assert.equal(first, moved);
  assert.equal(first, readFileSync(join(fixture, 'expected-artifact.json'), 'utf8'));
  assert.equal(generateLock(fixture), readFileSync(join(fixture, 'lotus.lock'), 'utf8'));
});

test('package artifact validates against the schema-2 artifact schema', t => {
  const probe = spawnSync(python, ['-c', 'import jsonschema'], { encoding: 'utf8' });
  if (probe.status !== 0) { t.skip('install test/requirements-vm.txt and set LOTUS_V2_PYTHON'); return; }
  const artifact = JSON.parse(readFileSync(join(fixture, 'expected-artifact.json'), 'utf8'));
  const schema = JSON.parse(readFileSync(new URL('../artifact-v2.schema.json', import.meta.url), 'utf8'));
  const script = 'import json, sys\nfrom jsonschema import Draft202012Validator\ncase = json.load(sys.stdin)\nDraft202012Validator.check_schema(case[0])\nDraft202012Validator(case[0]).validate(case[1])\n';
  const run = spawnSync(python, ['-c', script], { input: JSON.stringify([schema, artifact]), encoding: 'utf8' });
  assert.equal(run.status, 0, run.stderr);
});

test('a dependency byte change is rejected until relocked, then changes digests (and the root when bytecode changes)', async () => {
  const { dir } = copy();
  const base = (await compilePackage(dir, options)).artifact;
  const amounts = 'packages/core/src/amounts.lotus';
  edit(dir, amounts, s => s.replace('the diamond', 'The diamond'));
  await rejects(dir, 'lock-mismatch', e => e.file === amounts);
  const lockBefore = readFileSync(join(dir, 'lotus.lock'), 'utf8');
  updateLock(dir);
  assert.notEqual(readFileSync(join(dir, 'lotus.lock'), 'utf8'), lockBefore);
  const comment = (await compilePackage(dir, options)).artifact;
  const mod = (a, id) => a.build.modules.find(m => m.id === id);
  assert.notEqual(mod(comment, 'core@1.0.0/amounts').sourceDigest, mod(base, 'core@1.0.0/amounts').sourceDigest);
  assert.equal(mod(comment, 'core@1.0.0/amounts').interfaceDigest, mod(base, 'core@1.0.0/amounts').interfaceDigest);
  assert.notEqual(comment.build.lockDigest, base.build.lockDigest);
  assert.notEqual(comment.build.digest, base.build.digest);
  assert.notEqual(JSON.stringify(comment), JSON.stringify(base));
  assert.equal(comment.policy.root, base.policy.root, 'a comment-only change keeps the bytecode and root');
  // A semantic change alters bytecode and therefore the contract root.
  edit(dir, 'packages/core/src/internal.lotus', s => s.replace('x >= 0', 'x > 0'));
  await rejects(dir, 'lock-mismatch', e => e.file === 'packages/core/src/internal.lotus');
  updateLock(dir);
  const semantic = (await compilePackage(dir, options)).artifact;
  assert.notEqual(semantic.policy.root, base.policy.root);
  assert.notEqual(semantic.methods[0].scriptHex, base.methods[0].scriptHex);
  // Exported signature changes alter the stable interface digest.
  edit(dir, amounts, s => s.replace('atLeast(x: Amount, floor: Amount): Bool {\n    return nonNegative(x) && x >= floor;', 'atLeast(x: Amount, minimum: Amount): Bool {\n    return nonNegative(x) && x >= minimum;'), true);
  const renamed = (await compilePackage(dir, options)).artifact;
  assert.notEqual(mod(renamed, 'core@1.0.0/amounts').interfaceDigest, mod(base, 'core@1.0.0/amounts').interfaceDigest);
});

test('lock file is required, canonical and bound to the root manifest', async () => {
  let { dir } = copy();
  rmSync(join(dir, 'lotus.lock'));
  await rejects(dir, 'lock-missing');
  ({ dir } = copy());
  edit(dir, 'lotus.lock', s => s.replace('{\n', '{ \n'));
  await rejects(dir, 'lock-stale');
  ({ dir } = copy());
  edit(dir, 'lotus.toml', s => s.replace('lib_b = "lib_b@1.0.0"', 'lib_b = "lib_b@1.0.0"\nextra_b = "lib_b@1.0.0"'));
  await rejects(dir, 'lock-stale');
  // Dependency [sources] are never inherited: a bogus locator in lib_a is ignored.
  ({ dir } = copy());
  edit(dir, 'packages/lib_a/lotus.toml', s => s + '\n[sources]\ncore = "does/not/exist"\n', true);
  await compilePackage(dir, options);
});

test('imports diagnose duplicate names, visibility, missing modules/symbols and unknown aliases with file spans', async () => {
  const main = 'src/main.lotus';
  const cases = [
    [main, s => s.replace('import package::', 'import lib_b::digests::{paid as budgetOk};\nimport package::'), 'duplicate-name', main],
    [main, s => s + '\nfunction authorized(x: Bool): Bool { return x; }\n', 'duplicate-name', main],
    [main, s => s.replace('import package::', 'import lib_b::digests::{opens as sha256};\nimport package::'), 'duplicate-name', main],
    [main, s => s.replace('{withinBudget as budgetOk}', '{withinBudget}'), 'missing-symbol', main],
    [main, s => s.replace('{withinBudget as budgetOk}', '{withinBudget as budgetOk, nope}'), 'missing-symbol', main],
    [main, s => s.replace('lib_a::limits::', 'lib_a::nothing::'), 'missing-module', main],
    [main, s => s.replace('lib_a::limits::', 'nope::limits::'), 'unknown-alias', main],
    [main, s => s.replace('lib_a::limits::', 'core::amounts::'), 'unknown-alias', main],
    ['src/policy.lotus', s => s.replace('package function', 'function'), 'visibility', main],
    ['packages/lib_a/src/limits.lotus', s => s.replace('{checkedAdd, atLeast}', '{checkedAdd, atLeast, positive}'), 'visibility', 'packages/lib_a/src/limits.lotus', true],
    ['packages/lib_a/src/limits.lotus', s => s.replace('{checkedAdd, atLeast}', '{checkedAdd, atLeast, bounded}'), 'visibility', 'packages/lib_a/src/limits.lotus', true],
    ['packages/lib_b/src/digests.lotus', s => s.replace('amounts::atLeast(', 'amounts::positive('), 'visibility', 'packages/lib_b/src/digests.lotus', true],
    ['packages/lib_a/src/limits.lotus', s => 'import core::internal::{nonNegative};\n' + s, 'not-exported', 'packages/lib_a/src/limits.lotus', true],
    ['packages/core/src/amounts.lotus', s => s + '\ncontract Hidden { function f() { require(true); } }\n', 'declaration-only', 'packages/core/src/amounts.lotus', true],
  ];
  for (const [file, change, code, at, relock] of cases) {
    const { dir } = copy();
    edit(dir, file, change, relock);
    await rejects(dir, code, e => e.file === at && e.span !== undefined && /:\d+\.\.\d+: /.test(e.message));
  }
  assert.throws(() => compileContract('import lib::m::{f};\ncontract C { function f() { require(true); } }', { contract: 'C', bindings: {} }), /requires a package build/);
  assert.throws(() => compileContract('import "github.com/acme/lotus-std@v1.2.0"::amounts::{checkedAdd};\ncontract C { function f() { require(true); } }', { contract: 'C', bindings: {} }), /requires a package build/);
});

test('import cycles report every hop with file spans', async () => {
  const { dir } = copy();
  edit(dir, 'lotus.toml', s => s.replace('modules = ["main", "policy"]', 'modules = ["main", "policy", "a", "b"]'));
  writeFileSync(join(dir, 'src/a.lotus'), 'import package::b::{fb};\npackage function fa(x: Amount): Bool { return fb(x); }\n');
  writeFileSync(join(dir, 'src/b.lotus'), 'import package::a::{fa};\npackage function fb(x: Amount): Bool { return fa(x); }\n');
  edit(dir, 'src/main.lotus', s => 'import package::a::{fa};\n' + s);
  await rejects(dir, 'import-cycle', e => e.file === 'src/b.lotus' && e.message.includes('src/a.lotus:0..') && e.message.includes('app@0.1.0/a (src/a.lotus'));
});

test('paths: traversal, absolute, symlink escapes, case/Unicode collisions and undeclared files reject', async () => {
  let { base, dir } = copy();
  edit(dir, 'lotus.toml', s => s.replace('core = "packages/core"', 'core = "../outside"'));
  await rejects(dir, 'path-escape');
  assert.throws(() => generateLock(dir), e => e.code === 'path-escape');
  ({ dir } = copy());
  edit(dir, 'packages/core/lotus.toml', s => s.replace('"internal"]', '"internal", "../evil"]'));
  await rejects(dir, 'path-escape', e => e.file === 'packages/core/lotus.toml');
  ({ dir } = copy());
  edit(dir, 'lotus.toml', s => s.replace('source = "src"', 'source = "/etc"'));
  await rejects(dir, 'path-escape');
  // Module file symlinked outside the package root.
  ({ base, dir } = copy());
  writeFileSync(join(base, 'outside.lotus'), 'package function nonNegative(x: Amount): Bool { return true; }\n');
  rmSync(join(dir, 'packages/core/src/internal.lotus'));
  symlinkSync(join(base, 'outside.lotus'), join(dir, 'packages/core/src/internal.lotus'));
  await rejects(dir, 'symlink-escape', e => e.file === 'packages/core/src/internal.lotus');
  // Package directory symlinked outside the root project.
  ({ base, dir } = copy());
  renameSync(join(dir, 'packages/core'), join(base, 'core'));
  symlinkSync(join(base, 'core'), join(dir, 'packages/core'));
  await rejects(dir, 'symlink-escape');
  // In-project symlinks are allowed; the lock records locator and resolved root.
  ({ dir } = copy());
  symlinkSync(join(dir, 'packages/core'), join(dir, 'packages/core_link'));
  edit(dir, 'lotus.toml', s => s.replace('core = "packages/core"', 'core = "packages/core_link"'), true);
  const core = JSON.parse(readFileSync(join(dir, 'lotus.lock'), 'utf8')).packages.find(p => p.name === 'core');
  assert.deepEqual([core.locator.path, core.root], ['packages/core_link', 'packages/core']);
  await compilePackage(dir, options);
  // Declared module paths that collide under case folding.
  ({ dir } = copy());
  edit(dir, 'packages/core/lotus.toml', s => s.replace('"internal"]', '"internal", "Amounts"]'));
  await rejects(dir, 'path-collision');
  // On-disk name differs only by case from the declaration.
  ({ dir } = copy());
  renameSync(join(dir, 'packages/core/src/internal.lotus'), join(dir, 'packages/core/src/tmp.lotus'));
  renameSync(join(dir, 'packages/core/src/tmp.lotus'), join(dir, 'packages/core/src/Internal.lotus'));
  await rejects(dir, 'undeclared-file', e => e.file === 'packages/core/src/Internal.lotus');
  // Unicode normalization: NFC and NFD spellings of one name.
  ({ dir } = copy());
  writeFileSync(join(dir, 'packages/core/src/caf\u00e9.lotus'), '');
  writeFileSync(join(dir, 'packages/core/src/cafe\u0301.lotus'), '');
  const distinct = readdirSync(join(dir, 'packages/core/src')).filter(name => name.startsWith('caf')).length;
  await rejects(dir, distinct === 2 ? 'path-collision' : 'undeclared-file');
  // Undeclared file inside a source root.
  ({ dir } = copy());
  writeFileSync(join(dir, 'packages/core/src/extra.lotus'), 'export function x(a: Amount): Amount { return a; }\n');
  await rejects(dir, 'undeclared-file', e => e.file === 'packages/core/src/extra.lotus');
  assert.throws(() => generateLock(dir), e => e.code === 'undeclared-file');
  ({ dir } = copy());
  mkdirSync(join(dir, 'src/nested'));
  writeFileSync(join(dir, 'src/nested/notes.txt'), 'not a module\n');
  await rejects(dir, 'undeclared-file', e => e.file === 'src/nested/notes.txt');
});

test('graph limits are enforced with clear diagnostics', async () => {
  for (const [limits, pattern] of [[{ maxModules: 3 }, /module graph exceeds 3 modules/], [{ maxImportDepth: 1 }, /import depth exceeds 1/],
    [{ maxImportBindings: 2 }, /import bindings exceed 2/], [{ maxPackages: 1 }, /package graph exceeds 1 packages/], [{ maxSourceBytes: 256 }, /exceeds 256 bytes/]])
    await rejects(fixture, 'limit', e => pattern.test(e.message), { ...options, limits });
});

test('CLI compiles a package and the lock helper checks local files only', () => {
  const { base, dir } = copy();
  const out = join(base, 'out');
  const run = spawnSync(process.execPath, [join(dist, 'generic-cli.js'), '--package', dir, join(dir, 'options.json'), out, '--trace'], { encoding: 'utf8' });
  assert.equal(run.status, 0, run.stderr);
  assert.equal(readFileSync(join(out, 'artifact.json'), 'utf8'), readFileSync(join(fixture, 'expected-artifact.json'), 'utf8'));
  assert(JSON.parse(readFileSync(join(out, 'scheduler-trace.json'), 'utf8')).some(e => e.job === 'module:core@1.0.0/amounts'));
  const check = () => spawnSync(process.execPath, [join(dist, 'package-lock-cli.js'), dir, '--check'], { encoding: 'utf8' });
  assert.equal(check().status, 0, check().stderr);
  edit(dir, 'packages/lib_b/src/digests.lotus', s => s + '\n');
  assert.equal(check().status, 1);
  assert.equal(spawnSync(process.execPath, [join(dist, 'package-lock-cli.js'), dir], { encoding: 'utf8' }).status, 0);
  assert.equal(check().status, 0);
  const failed = spawnSync(process.execPath, [join(dist, 'generic-cli.js'), '--package', join(base, 'missing'), join(dir, 'options.json'), out], { encoding: 'utf8' });
  assert.equal(failed.status, 1);
});

test('strict lotus.toml subset rejects non-subset syntax', async () => {
  for (const change of [s => s.replace('version = "0.1.0"', 'version = 1'), s => s.replace('name = "app"', 'name = "app"\nname = "app"'),
    s => s.replace('[package]', '[package.extra]'), s => s.replace('kind = "contract"', 'kind = "contract"\nflavor = "x"'), s => s + '\n[tools]\n']) {
    const { dir } = copy();
    edit(dir, 'lotus.toml', change);
    await rejects(dir, 'manifest', e => e.file === 'lotus.toml');
  }
});
