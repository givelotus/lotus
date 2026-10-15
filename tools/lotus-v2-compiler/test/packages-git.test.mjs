import test from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { chmodSync, cpSync, existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, symlinkSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { compilePackage, generateLock } from '../dist/packages.js';
import { fetchPackages, forgeGitUrl, parseModulePath, updatePackages } from '../dist/package-sources.js';

const dist = fileURLToPath(new URL('../dist/', import.meta.url));
const diamond = fileURLToPath(new URL('../examples/packages/diamond/', import.meta.url));
const OWNER = '79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798';

function git(cwd, args, env) {
  const result = spawnSync('git', ['-c', 'core.hooksPath=', '-c', 'init.defaultBranch=main', ...args], { cwd, encoding: 'utf8', env });
  assert.equal(result.status, 0, `${args.join(' ')}\n${result.stderr}\n${result.stdout}`);
  return (result.stdout || '').trim();
}

function repoEnv(base) {
  const config = join(base, 'gitconfig');
  if (!existsSync(config)) writeFileSync(config, '');
  return { ...process.env, GIT_AUTHOR_NAME: 'Lotus', GIT_AUTHOR_EMAIL: 'lotus@example.com', GIT_COMMITTER_NAME: 'Lotus', GIT_COMMITTER_EMAIL: 'lotus@example.com', GIT_CONFIG_NOSYSTEM: '1', GIT_CONFIG_GLOBAL: config };
}

function writeFiles(dir, files) {
  for (const [rel, body] of Object.entries(files)) {
    mkdirSync(join(dir, dirname(rel)), { recursive: true });
    writeFileSync(join(dir, rel), body);
  }
}

function library({ name, version, module = 'amounts', body, deps = {}, sources = {} }) {
  const depLines = Object.entries(deps).map(([key, value]) => `${key} = "${value}"`);
  const sourceLines = Object.entries(sources).map(([key, value]) => `${key.includes('.') || key.includes('/') ? `"${key}"` : key} = "${value}"`);
  const manifest = [`[package]`, `name = "${name}"`, `version = "${version}"`, `kind = "library"`, `source = "src"`, `modules = ["${module}"]`, `exports = ["${module}"]`,
    ...(depLines.length ? ['', '[dependencies]', ...depLines] : []),
    ...(sourceLines.length ? ['', '[sources]', ...sourceLines] : []), ''].join('\n');
  return { [`src/${module}.lotus`]: body ?? 'export function checkedAdd(a: Amount, b: Amount): Amount { return a + b; }\n', 'lotus.toml': manifest };
}

function startRepo(base, name, env) {
  const bare = join(base, 'bare', `${name}.git`);
  const work = join(base, 'work', name);
  mkdirSync(dirname(bare), { recursive: true });
  git(base, ['init', '--bare', bare], env);
  mkdirSync(work, { recursive: true });
  git(work, ['init'], env);
  git(work, ['remote', 'add', 'origin', bare], env);
  return { bare, work };
}

function publish(work, env, message, tag) {
  git(work, ['add', '-A'], env);
  const commit = git(work, ['commit', '-m', message], env).includes(' ') ? git(work, ['rev-parse', 'HEAD'], env) : git(work, ['rev-parse', 'HEAD'], env);
  if (tag) git(work, ['tag', tag], env);
  git(work, ['push', 'origin', 'HEAD'], env);
  if (tag) git(work, ['push', 'origin', tag], env);
  return git(work, ['rev-parse', 'HEAD'], env) || commit;
}

function fileUrl(abs) { return `file://${abs}`; }

function poison(dir) {
  const bin = join(dir, 'bin');
  const log = join(dir, 'git.log');
  mkdirSync(bin, { recursive: true });
  writeFileSync(join(bin, 'git'), `#!/bin/sh\necho invoked >> ${JSON.stringify(log)}\nexit 99\n`);
  chmodSync(join(bin, 'git'), 0o755);
  return { bin, log, invoked: () => existsSync(log) ? readFileSync(log, 'utf8') : '' };
}

function contract(dir, source, manifest) {
  writeFiles(dir, { 'lotus.toml': manifest, 'src/main.lotus': source, 'options.json': JSON.stringify({ contract: 'Treasury', bindings: { Treasury: { owner: OWNER, budget: '1000' } } }) });
  return JSON.parse(readFileSync(join(dir, 'options.json'), 'utf8'));
}

const MAIN = `import std::amounts::{checkedAdd as safeAdd};
import "github.com/acme/lotus-std@v1.2.0"::amounts::{checkedAdd as alsoAdd};
import std2::amounts::{checkedAdd as addV2};
import left::wrap::{fromLeft};
import right::wrap::{fromRight};
import libs::mark::{marked};

contract Treasury<owner: PublicKey, budget: Amount> {
    function spend(sig: Signature) {
        require(checksig(sig, owner));
        require(safeAdd(budget, budget) == alsoAdd(budget, budget));
        require(addV2(budget, budget) >= budget);
        require(fromLeft(budget));
        require(fromRight(budget));
        require(marked(budget));
    }
}
`;

function world() {
  const base = mkdtempSync(join(tmpdir(), 'lotus-git-src-'));
  const env = repoEnv(base);
  const repos = {};
  const open = name => { const repo = startRepo(base, name, env); repos[name] = repo.bare; return repo.work; };
  const std = open('lotus-std');
  writeFiles(std, library({ name: 'github.com/acme/lotus-std', version: '1.2.0' }));
  publish(std, env, 'std 1.2.0', 'v1.2.0');
  const at12 = git(std, ['rev-parse', 'HEAD'], env);
  writeFiles(std, library({ name: 'github.com/acme/lotus-std', version: '1.3.0' }));
  writeFiles(std, library({ name: 'github.com/acme/lotus-std/libs', version: '1.3.0', module: 'mark', body: 'export function marked(x: Amount): Bool { return x >= 0; }\n' }));
  // library() writes lotus.toml at the repo root; put the subdir manifest back after that call.
  writeFiles(std, { 'libs/lotus.toml': readFileSync(join(std, 'lotus.toml'), 'utf8'), 'libs/src/mark.lotus': readFileSync(join(std, 'src/mark.lotus'), 'utf8') });
  rmSync(join(std, 'src/mark.lotus'));
  writeFiles(std, library({ name: 'github.com/acme/lotus-std', version: '1.3.0' }));
  publish(std, env, 'std 1.3.0', 'v1.3.0');
  const at13 = git(std, ['rev-parse', 'HEAD'], env);
  writeFiles(std, { 'v2/lotus.toml': `[package]\nname = "github.com/acme/lotus-std/v2"\nversion = "2.0.0"\nkind = "library"\nsource = "src"\nmodules = ["amounts"]\nexports = ["amounts"]\n`, 'v2/src/amounts.lotus': 'export function checkedAdd(a: Amount, b: Amount): Amount { return a + b; }\n' });
  publish(std, env, 'std 2.0.0', 'v2.0.0');
  const left = open('left');
  writeFiles(left, library({ name: 'github.com/acme/left', version: '1.0.0', module: 'wrap', deps: { std: 'github.com/acme/lotus-std@v1.2.0' }, body: 'import std::amounts::{checkedAdd};\nexport function fromLeft(x: Amount): Bool { return checkedAdd(x, x) >= x; }\n' }));
  publish(left, env, 'left', 'v1.0.0');
  const right = open('right');
  writeFiles(right, library({ name: 'github.com/acme/right', version: '1.0.0', module: 'wrap', deps: { std: 'github.com/acme/lotus-std@v1.3.0' }, body: 'import std::amounts::{checkedAdd};\nexport function fromRight(x: Amount): Bool { return checkedAdd(x, x) >= x; }\n' }));
  publish(right, env, 'right', 'v1.0.0');
  const project = join(base, 'app');
  mkdirSync(project);
  const manifest = `[package]\nname = "app"\nversion = "0.1.0"\nkind = "contract"\nsource = "src"\nentry = "main"\nmodules = ["main"]\n\n[dependencies]\nstd = "github.com/acme/lotus-std@v1.2.0"\nleft = "github.com/acme/left@v1.0.0"\nright = "github.com/acme/right@v1.0.0"\nstd2 = "github.com/acme/lotus-std/v2@v2.0.0"\nlibs = "github.com/acme/lotus-std/libs@v1.3.0"\n`;
  const options = contract(project, MAIN, manifest);
  const resolveRepoUrl = ({ repo }) => { const bare = repos[repo]; if (!bare) throw new Error(`unexpected repo ${repo}`); return fileUrl(bare); };
  return { base, project, options, resolveRepoUrl, at12, at13, repos, env };
}

test('forge URLs use host/owner/repo and keep major suffixes and subdirectories out of the remote', () => {
  assert.equal(forgeGitUrl('github.com/acme/lotus-std'), 'https://github.com/acme/lotus-std.git');
  assert.equal(forgeGitUrl('github.com/acme/lotus-std/v2'), 'https://github.com/acme/lotus-std.git');
  assert.equal(forgeGitUrl('gitlab.com/acme/lotus-std/libs'), 'https://gitlab.com/acme/lotus-std.git');
  assert.equal(forgeGitUrl('bitbucket.org/acme/lotus-std'), 'https://bitbucket.org/acme/lotus-std.git');
  assert.equal(forgeGitUrl('codeberg.org/acme/lotus-std/v3'), 'https://codeberg.org/acme/lotus-std.git');
  const v2 = parseModulePath('github.com/acme/lotus-std/v2');
  assert.equal(v2.suffixMajor, 2);
  assert.equal(v2.subdir, '');
  assert.equal(parseModulePath('github.com/acme/lotus-std/libs/math').subdir, 'libs/math');
  assert.equal(parseModulePath('example.com/acme/widget').forge, false);
  assert.throws(() => forgeGitUrl('example.com/acme/widget'), /no forge repository/);
  assert.throws(() => parseModulePath('github.com/acme/lotus-std/v0'), /\/v0 or \/v1/);
  assert.throws(() => parseModulePath('github.com/acme/lotus-std/v1'), /\/v0 or \/v1/);
});

test('alias and quoted imports parse one selected module; MVS keeps v1 and v2 apart', async () => {
  const { project, options, resolveRepoUrl, at13 } = world();
  fetchPackages(project, { resolveRepoUrl });
  const lock = JSON.parse(readFileSync(join(project, 'lotus.lock'), 'utf8'));
  assert.equal(lock.schema, 'lotus-v2/package-lock/2');
  const std = lock.packages.find(pkg => pkg.name === 'github.com/acme/lotus-std');
  const std2 = lock.packages.find(pkg => pkg.name === 'github.com/acme/lotus-std/v2');
  const libs = lock.packages.find(pkg => pkg.name === 'github.com/acme/lotus-std/libs');
  assert.equal(std.version, 'v1.3.0');
  assert.equal(std.commit, at13);
  assert.match(std.gitTree, /^[0-9a-f]{40}$/);
  assert.equal(std.override, false);
  assert.equal(std.locator.kind, 'git');
  assert.equal(std.locator.dir, '');
  assert.equal(std2.version, 'v2.0.0');
  assert.equal(std2.locator.dir, 'v2');
  assert.equal(libs.locator.dir, 'libs');
  assert.deepEqual(std.requesters.map(item => `${item.package} ${item.required}`).sort(), [
    'app@0.1.0 v1.2.0',
    'github.com/acme/left@v1.0.0 v1.2.0',
    'github.com/acme/right@v1.0.0 v1.3.0',
  ]);
  assert.equal(existsSync(join(project, std.root, '.git')), false);
  const built = await compilePackage(project, options);
  assert.equal(built.parses['github.com/acme/lotus-std@v1.3.0/amounts'], 1);
  assert.equal(built.parses['github.com/acme/lotus-std/v2@v2.0.0/amounts'], 1);
  assert.equal(Object.values(built.parses).every(count => count === 1), true);
  const root = built.artifact.build.packages.find(pkg => pkg.id === 'app@0.1.0');
  assert.equal(root.dependencies.std, 'github.com/acme/lotus-std@v1.3.0');
  assert.equal(root.dependencies.std2, 'github.com/acme/lotus-std/v2@v2.0.0');
});

test('MVS ignores requirements of a version that lost to a higher tag', () => {
  const base = mkdtempSync(join(tmpdir(), 'lotus-git-mvs-'));
  const env = repoEnv(base);
  const repos = {};
  const open = name => { const repo = startRepo(base, name, env); repos[name] = repo.bare; return repo.work; };
  const extra = open('extra');
  writeFiles(extra, library({ name: 'github.com/acme/extra', version: '1.0.0', module: 'mark', body: 'export function marker(x: Amount): Bool { return x >= 0; }\n' }));
  publish(extra, env, 'extra 1.0.0', 'v1.0.0');
  writeFiles(extra, library({ name: 'github.com/acme/extra', version: '1.9.0', module: 'mark', body: 'export function marker(x: Amount): Bool { return x > 0; }\n' }));
  publish(extra, env, 'extra 1.9.0', 'v1.9.0');
  const std = open('lotus-std');
  writeFiles(std, library({ name: 'github.com/acme/lotus-std', version: '1.2.0', deps: { extra: 'github.com/acme/extra@v1.9.0' } }));
  publish(std, env, 'std 1.2.0', 'v1.2.0');
  writeFiles(std, library({ name: 'github.com/acme/lotus-std', version: '1.3.0', deps: { extra: 'github.com/acme/extra@v1.0.0' } }));
  publish(std, env, 'std 1.3.0', 'v1.3.0');
  const right = open('right');
  writeFiles(right, library({ name: 'github.com/acme/right', version: '1.0.0', module: 'wrap', deps: { std: 'github.com/acme/lotus-std@v1.3.0' }, body: 'export function fromRight(x: Amount): Bool { return x >= 0; }\n' }));
  publish(right, env, 'right', 'v1.0.0');
  const project = join(base, 'app');
  mkdirSync(project);
  const options = contract(project, 'import std::amounts::{checkedAdd as safeAdd};\ncontract Treasury<owner: PublicKey, budget: Amount> {\n    function spend(sig: Signature) { require(checksig(sig, owner)); require(safeAdd(budget, budget) >= budget); }\n}\n',
    `[package]\nname = "app"\nversion = "0.1.0"\nkind = "contract"\nsource = "src"\nentry = "main"\nmodules = ["main"]\n\n[dependencies]\nstd = "github.com/acme/lotus-std@v1.2.0"\nright = "github.com/acme/right@v1.0.0"\n`);
  fetchPackages(project, { resolveRepoUrl: ({ repo }) => fileUrl(repos[repo]) });
  const lock = JSON.parse(readFileSync(join(project, 'lotus.lock'), 'utf8'));
  assert.equal(lock.packages.find(pkg => pkg.name === 'github.com/acme/extra').version, 'v1.0.0');
  assert.equal(existsSync(join(project, '.lotus/deps/github.com/acme/extra/v1.9.0')), false);
  return compilePackage(project, options);
});

test('a commit pin is recorded and a mismatched digest is rejected', async () => {
  const { base, project, options, resolveRepoUrl, at12 } = world();
  writeFileSync(join(project, 'lotus.toml'), readFileSync(join(project, 'lotus.toml'), 'utf8').replace(
    '[dependencies]\nstd = "github.com/acme/lotus-std@v1.2.0"\nleft = "github.com/acme/left@v1.0.0"\nright = "github.com/acme/right@v1.0.0"\nstd2 = "github.com/acme/lotus-std/v2@v2.0.0"\nlibs = "github.com/acme/lotus-std/libs@v1.3.0"\n',
    `[dependencies]\nstd = "github.com/acme/lotus-std@${at12}"\n`));
  writeFileSync(join(project, 'src/main.lotus'), 'import std::amounts::{checkedAdd as safeAdd};\ncontract Treasury<owner: PublicKey, budget: Amount> {\n    function spend(sig: Signature) { require(checksig(sig, owner)); require(safeAdd(budget, budget) >= budget); }\n}\n');
  fetchPackages(project, { resolveRepoUrl });
  const lockPath = join(project, 'lotus.lock');
  const lock = JSON.parse(readFileSync(lockPath, 'utf8'));
  const std = lock.packages.find(pkg => pkg.name === 'github.com/acme/lotus-std');
  assert.equal(std.version, at12);
  assert.equal(std.commit, at12);
  const source = join(project, std.root, 'src/amounts.lotus');
  writeFileSync(source, readFileSync(source, 'utf8').replace('a + b', 'a +  b'));
  await assert.rejects(compilePackage(project, options), err => err.code === 'lock-mismatch' && err.file.endsWith('amounts.lotus'));
  writeFileSync(source, readFileSync(source, 'utf8').replace('a +  b', 'a + b'));
  const broken = readFileSync(lockPath, 'utf8').replace(std.files.find(file => file.path.endsWith('amounts.lotus')).digest, '00'.repeat(32));
  writeFileSync(lockPath, broken);
  await assert.rejects(compilePackage(project, options), err => err.code === 'lock-mismatch');
  assert.equal(base.length > 0, true);
});

function onlyStd(project, spec) {
  writeFileSync(join(project, 'lotus.toml'), `[package]\nname = "app"\nversion = "0.1.0"\nkind = "contract"\nsource = "src"\nentry = "main"\nmodules = ["main"]\n\n[dependencies]\n${spec}\n`);
  writeFileSync(join(project, 'src/main.lotus'), 'import std::amounts::{checkedAdd as safeAdd};\ncontract Treasury<owner: PublicKey, budget: Amount> {\n    function spend(sig: Signature) { require(checksig(sig, owner)); require(safeAdd(budget, budget) >= budget); }\n}\n');
}

test('a tag and a commit agree only when they are the same object', () => {
  const agreed = world();
  onlyStd(agreed.project, `std = "github.com/acme/lotus-std@v1.2.0"\npin = "github.com/acme/lotus-std@${agreed.at12}"`);
  fetchPackages(agreed.project, { resolveRepoUrl: agreed.resolveRepoUrl });
  const lock = JSON.parse(readFileSync(join(agreed.project, 'lotus.lock'), 'utf8'));
  const std = lock.packages.find(pkg => pkg.name === 'github.com/acme/lotus-std');
  assert.equal(std.version, 'v1.2.0');
  assert.equal(std.commit, agreed.at12);
  const higher = world();
  onlyStd(higher.project, `std = "github.com/acme/lotus-std@v1.2.0"\nright = "github.com/acme/right@v1.0.0"\npin = "github.com/acme/lotus-std@${higher.at13}"`);
  fetchPackages(higher.project, { resolveRepoUrl: higher.resolveRepoUrl });
  const selected = JSON.parse(readFileSync(join(higher.project, 'lotus.lock'), 'utf8')).packages.find(pkg => pkg.name === 'github.com/acme/lotus-std');
  assert.equal(selected.version, 'v1.3.0');
  assert.equal(selected.commit, higher.at13);
  const clash = world();
  onlyStd(clash.project, `std = "github.com/acme/lotus-std@v1.2.0"\npin = "github.com/acme/lotus-std@${clash.at13}"`);
  assert.throws(() => fetchPackages(clash.project, { resolveRepoUrl: clash.resolveRepoUrl }), err => err.code === 'version-conflict');
  const two = world();
  onlyStd(two.project, `std = "github.com/acme/lotus-std@${two.at12}"\npin = "github.com/acme/lotus-std@${two.at13}"`);
  assert.throws(() => fetchPackages(two.project, { resolveRepoUrl: two.resolveRepoUrl }), err => err.code === 'version-conflict' && /pinned to commits/.test(err.message));
});

test('compile stays offline when git is removed from PATH', async () => {
  const { base, project, options, resolveRepoUrl } = world();
  fetchPackages(project, { resolveRepoUrl });
  const locked = readFileSync(join(project, 'lotus.lock'), 'utf8');
  const { bin, invoked } = poison(join(base, 'poison'));
  const previous = process.env.PATH;
  process.env.PATH = bin;
  try {
    const built = await compilePackage(project, options);
    assert.equal(built.parses['github.com/acme/lotus-std@v1.3.0/amounts'], 1);
    assert.equal(generateLock(project), locked);
  } finally { process.env.PATH = previous; }
  assert.equal(invoked(), '');
  const out = join(base, 'out');
  const run = spawnSync(process.execPath, [join(dist, 'generic-cli.js'), '--package', project, join(project, 'options.json'), out], { encoding: 'utf8', env: { ...process.env, PATH: bin } });
  assert.equal(run.status, 0, run.stderr);
  const check = spawnSync(process.execPath, [join(dist, 'package-lock-cli.js'), project, '--check'], { encoding: 'utf8', env: { ...process.env, PATH: bin } });
  assert.equal(check.status, 0, check.stderr);
  assert.equal(invoked(), '');
  const unfetched = join(base, 'empty');
  mkdirSync(unfetched);
  writeFiles(unfetched, { 'lotus.toml': `[package]\nname = "app"\nversion = "0.1.0"\nkind = "contract"\nsource = "src"\nentry = "main"\nmodules = ["main"]\n\n[dependencies]\nstd = "github.com/acme/lotus-std@v1.2.0"\n`, 'src/main.lotus': 'contract Treasury<owner: PublicKey, budget: Amount> { function spend(sig: Signature) { require(checksig(sig, owner)); } }\n' });
  process.env.PATH = bin;
  try { assert.throws(() => generateLock(unfetched), err => err.code === 'unfetched'); }
  finally { process.env.PATH = previous; }
  assert.equal(invoked(), '');
});

test('fetched trees reject symlink escape and .. traversal', () => {
  const base = mkdtempSync(join(tmpdir(), 'lotus-git-escape-'));
  const env = repoEnv(base);
  const repos = {};
  const open = name => { const repo = startRepo(base, name, env); repos[name] = repo.bare; return repo.work; };
  const link = open('lotus-std');
  writeFileSync(join(base, 'outside.lotus'), 'export function checkedAdd(a: Amount, b: Amount): Amount { return a; }\n');
  mkdirSync(join(link, 'src'));
  symlinkSync(join(base, 'outside.lotus'), join(link, 'src/amounts.lotus'));
  writeFiles(link, { 'lotus.toml': library({ name: 'github.com/acme/lotus-std', version: '1.2.0' })['lotus.toml'] });
  publish(link, env, 'symlink', 'v1.2.0');
  const linked = join(base, 'linked');
  mkdirSync(linked);
  contract(linked, 'import std::amounts::{checkedAdd as safeAdd};\ncontract Treasury<owner: PublicKey, budget: Amount> { function spend(sig: Signature) { require(checksig(sig, owner)); require(safeAdd(budget, budget) >= budget); } }\n',
    `[package]\nname = "app"\nversion = "0.1.0"\nkind = "contract"\nsource = "src"\nentry = "main"\nmodules = ["main"]\n\n[dependencies]\nstd = "github.com/acme/lotus-std@v1.2.0"\n`);
  assert.throws(() => fetchPackages(linked, { resolveRepoUrl: () => fileUrl(repos['lotus-std']) }), err => err.code === 'symlink-escape');
  const dot = open('dot');
  writeFiles(dot, { 'lotus.toml': `[package]\nname = "example.com/acme/dot"\nversion = "1.0.0"\nkind = "library"\nsource = ".."\nmodules = ["amounts"]\nexports = ["amounts"]\n`, 'src/amounts.lotus': 'export function checkedAdd(a: Amount, b: Amount): Amount { return a + b; }\n' });
  publish(dot, env, 'dotdot', 'v1.0.0');
  const dotted = join(base, 'dotted');
  mkdirSync(dotted);
  contract(dotted, 'contract Treasury<owner: PublicKey, budget: Amount> { function spend(sig: Signature) { require(checksig(sig, owner)); } }\n',
    `[package]\nname = "app"\nversion = "0.1.0"\nkind = "contract"\nsource = "src"\nentry = "main"\nmodules = ["main"]\n\n[dependencies]\nstd = "example.com/acme/dot@v1.0.0"\n\n[sources]\n"example.com/acme/dot" = "${fileUrl(repos.dot)}"\n`);
  assert.throws(() => fetchPackages(dotted, { resolveRepoUrl: () => { throw new Error('forge transport should not be used'); } }), err => err.code === 'path-escape');
});

test('root replace can point a module path at a local directory', async () => {
  const { base, resolveRepoUrl } = world();
  const project = join(base, 'replaced');
  mkdirSync(project);
  const { bin, invoked } = poison(join(base, 'replace-poison'));
  const options = contract(project, 'import std::amounts::{checkedAdd as safeAdd};\ncontract Treasury<owner: PublicKey, budget: Amount> {\n    function spend(sig: Signature) { require(checksig(sig, owner)); require(safeAdd(budget, budget) >= budget); }\n}\n',
    `[package]\nname = "app"\nversion = "0.1.0"\nkind = "contract"\nsource = "src"\nentry = "main"\nmodules = ["main"]\n\n[dependencies]\nstd = "github.com/acme/lotus-std@v1.2.0"\n\n[replace]\n"github.com/acme/lotus-std" = "packages/std"\n`);
  writeFiles(project, library({ name: 'github.com/acme/lotus-std', version: '1.4.0' }));
  writeFiles(project, { 'packages/std/lotus.toml': readFileSync(join(project, 'lotus.toml'), 'utf8').includes('kind = "library"') ? '' : '' });
  // library() wrote the package at the project root; move that library under packages/std and restore the contract manifest.
  const libToml = `[package]\nname = "github.com/acme/lotus-std"\nversion = "1.4.0"\nkind = "library"\nsource = "src"\nmodules = ["amounts"]\nexports = ["amounts"]\n`;
  mkdirSync(join(project, 'packages/std/src'), { recursive: true });
  writeFileSync(join(project, 'packages/std/lotus.toml'), libToml);
  writeFileSync(join(project, 'packages/std/src/amounts.lotus'), 'export function checkedAdd(a: Amount, b: Amount): Amount { return a + b; }\n');
  writeFileSync(join(project, 'lotus.toml'), `[package]\nname = "app"\nversion = "0.1.0"\nkind = "contract"\nsource = "src"\nentry = "main"\nmodules = ["main"]\n\n[dependencies]\nstd = "github.com/acme/lotus-std@v1.2.0"\n\n[replace]\n"github.com/acme/lotus-std" = "packages/std"\n`);
  rmSync(join(project, 'src/amounts.lotus'), { force: true });
  const previous = process.env.PATH;
  process.env.PATH = bin;
  try { fetchPackages(project, { resolveRepoUrl }); }
  finally { process.env.PATH = previous; }
  assert.equal(invoked(), '');
  const lock = JSON.parse(readFileSync(join(project, 'lotus.lock'), 'utf8'));
  const std = lock.packages.find(pkg => pkg.name === 'github.com/acme/lotus-std');
  assert.equal(std.override, true);
  assert.deepEqual(std.locator, { kind: 'path', path: 'packages/std' });
  assert.equal(std.commit, undefined);
  assert.equal(lock.root.replace['github.com/acme/lotus-std'].kind, 'path');
  process.env.PATH = bin;
  try { await compilePackage(project, options); }
  finally { process.env.PATH = previous; }
  assert.equal(invoked(), '');
  writeFileSync(join(project, 'packages/std/lotus.toml'), libToml.replace('1.4.0', '1.1.0'));
  process.env.PATH = bin;
  try { assert.throws(() => fetchPackages(project, { resolveRepoUrl }), err => err.code === 'version-conflict'); }
  finally { process.env.PATH = previous; }
});

test('branch names are rejected on compile and fetch; update may pin a branch or range', async () => {
  const { base, project, options, resolveRepoUrl } = world();
  const original = readFileSync(join(project, 'lotus.toml'), 'utf8');
  writeFileSync(join(project, 'lotus.toml'), original.replace('std = "github.com/acme/lotus-std@v1.2.0"', 'std = "github.com/acme/lotus-std@main"'));
  await assert.rejects(compilePackage(project, options), err => err.code === 'branch' && err.message.includes('main'));
  assert.throws(() => fetchPackages(project, { resolveRepoUrl }), err => err.code === 'branch');
  writeFileSync(join(project, 'lotus.toml'), original.replace('std = "github.com/acme/lotus-std@v1.2.0"', 'std = "github.com/acme/lotus-std@^1.2.0"'));
  updatePackages(project, 'std', { resolveRepoUrl });
  assert.match(readFileSync(join(project, 'lotus.toml'), 'utf8'), /std = "github.com\/acme\/lotus-std@v1\.3\.0"/);
  const ranged = JSON.parse(readFileSync(join(project, 'lotus.lock'), 'utf8'));
  assert.equal(ranged.packages.find(pkg => pkg.name === 'github.com/acme/lotus-std').version, 'v1.3.0');
  const branchApp = join(base, 'branch-app');
  mkdirSync(branchApp);
  contract(branchApp, 'import std::amounts::{checkedAdd as safeAdd};\ncontract Treasury<owner: PublicKey, budget: Amount> {\n    function spend(sig: Signature) { require(checksig(sig, owner)); require(safeAdd(budget, budget) >= budget); }\n}\n',
    `[package]\nname = "app"\nversion = "0.1.0"\nkind = "contract"\nsource = "src"\nentry = "main"\nmodules = ["main"]\n\n[dependencies]\nstd = "github.com/acme/lotus-std@main"\n`);
  updatePackages(branchApp, 'github.com/acme/lotus-std@main', { resolveRepoUrl });
  const rewritten = readFileSync(join(branchApp, 'lotus.toml'), 'utf8');
  assert.match(rewritten, /std = "github.com\/acme\/lotus-std@[0-9a-f]{40}"/);
  const branchOptions = JSON.parse(readFileSync(join(branchApp, 'options.json'), 'utf8'));
  const { bin, invoked } = poison(join(base, 'update-poison'));
  const previous = process.env.PATH;
  process.env.PATH = bin;
  try { await compilePackage(branchApp, branchOptions); }
  finally { process.env.PATH = previous; }
  assert.equal(invoked(), '');
});

test('dependency locators are ignored; an unknown host needs a root pin', () => {
  const base = mkdtempSync(join(tmpdir(), 'lotus-git-locator-'));
  const env = repoEnv(base);
  const real = startRepo(base, 'real', env);
  const decoy = startRepo(base, 'decoy', env);
  writeFiles(real.work, library({ name: 'example.com/widgets/math', version: '1.0.0', module: 'mark', body: 'export function marked(x: Amount): Bool { return x >= 0; } // REAL_MARKER\n' }));
  publish(real.work, env, 'real', 'v1.0.0');
  writeFiles(decoy.work, library({ name: 'example.com/widgets/math', version: '1.0.0', module: 'mark', body: 'export function marked(x: Amount): Bool { return x >= 0; } // DECOY_MARKER\n' }));
  publish(decoy.work, env, 'decoy', 'v1.0.0');
  const left = startRepo(base, 'left', env);
  writeFiles(left.work, library({
    name: 'github.com/acme/left', version: '1.0.0', module: 'wrap',
    deps: { math: 'example.com/widgets/math@v1.0.0' },
    sources: { 'example.com/widgets/math': fileUrl(decoy.bare) },
    body: 'export function fromLeft(x: Amount): Bool { return x >= 0; }\n',
  }));
  publish(left.work, env, 'left', 'v1.0.0');
  const project = join(base, 'app');
  mkdirSync(project);
  const resolveRepoUrl = ({ repo }) => fileUrl(repo === 'left' ? left.bare : real.bare);
  contract(project, 'import math::mark::{marked};\ncontract Treasury<owner: PublicKey, budget: Amount> { function spend(sig: Signature) { require(checksig(sig, owner)); require(marked(budget)); } }\n',
    `[package]\nname = "app"\nversion = "0.1.0"\nkind = "contract"\nsource = "src"\nentry = "main"\nmodules = ["main"]\n\n[dependencies]\nleft = "github.com/acme/left@v1.0.0"\nmath = "example.com/widgets/math@v1.0.0"\n`);
  assert.throws(() => fetchPackages(project, { resolveRepoUrl }), err => err.code === 'locator');
  assert.equal(existsSync(join(project, '.lotus/deps/example.com/widgets/math')), false);
  const pinned = `${readFileSync(join(project, 'lotus.toml'), 'utf8')}\n[sources]\n"example.com/widgets/math" = "${fileUrl(real.bare)}"\n`;
  writeFileSync(join(project, 'lotus.toml'), pinned);
  fetchPackages(project, { resolveRepoUrl });
  const lock = JSON.parse(readFileSync(join(project, 'lotus.lock'), 'utf8'));
  const math = lock.packages.find(pkg => pkg.name === 'example.com/widgets/math');
  assert.equal(math.locator.url, fileUrl(real.bare));
  assert.match(readFileSync(join(project, math.root, 'src/mark.lotus'), 'utf8'), /REAL_MARKER/);
  assert.doesNotMatch(readFileSync(join(project, math.root, 'src/mark.lotus'), 'utf8'), /DECOY_MARKER/);
});

test('v2 uses the repository root when vN/lotus.toml is absent, and a v2 tag needs /v2', () => {
  const base = mkdtempSync(join(tmpdir(), 'lotus-git-major-'));
  const env = repoEnv(base);
  const repo = startRepo(base, 'onlyv2', env);
  writeFiles(repo.work, library({ name: 'github.com/acme/onlyv2/v2', version: '2.0.0' }));
  publish(repo.work, env, 'root is v2', 'v2.0.0');
  const project = join(base, 'app');
  mkdirSync(project);
  contract(project, 'import std::amounts::{checkedAdd as safeAdd};\ncontract Treasury<owner: PublicKey, budget: Amount> { function spend(sig: Signature) { require(checksig(sig, owner)); require(safeAdd(budget, budget) >= budget); } }\n',
    `[package]\nname = "app"\nversion = "0.1.0"\nkind = "contract"\nsource = "src"\nentry = "main"\nmodules = ["main"]\n\n[dependencies]\nstd = "github.com/acme/onlyv2/v2@v2.0.0"\n`);
  fetchPackages(project, { resolveRepoUrl: () => fileUrl(repo.bare) });
  const lock = JSON.parse(readFileSync(join(project, 'lotus.lock'), 'utf8'));
  const std = lock.packages.find(pkg => pkg.name === 'github.com/acme/onlyv2/v2');
  assert.equal(std.locator.dir, '');
  assert.equal(std.version, 'v2.0.0');
  writeFileSync(join(project, 'lotus.toml'), readFileSync(join(project, 'lotus.toml'), 'utf8').replace('github.com/acme/onlyv2/v2@v2.0.0', 'github.com/acme/onlyv2@v2.0.0'));
  assert.throws(() => fetchPackages(project, { resolveRepoUrl: () => fileUrl(repo.bare) }), err => err.code === 'manifest' && /\/v2/.test(err.message));
});

test('vendor and the local cache cannot both supply one selector, and path projects do not spawn git', () => {
  const { base, project, resolveRepoUrl } = world();
  fetchPackages(project, { resolveRepoUrl, vendor: true });
  assert.equal(existsSync(join(project, 'vendor')), true);
  assert.equal(existsSync(join(project, '.lotus')), false);
  assert.equal(generateLock(project), readFileSync(join(project, 'lotus.lock'), 'utf8'));
  fetchPackages(project, { resolveRepoUrl });
  assert.throws(() => generateLock(project), err => err.code === 'unfetched' && /both \.lotus\/deps and vendor/.test(err.message));
  const copy = join(base, 'diamond');
  cpSync(diamond, copy, { recursive: true });
  const { bin, invoked } = poison(join(base, 'diamond-poison'));
  const previous = process.env.PATH;
  process.env.PATH = bin;
  try {
    const text = fetchPackages(copy);
    assert.equal(text, readFileSync(join(diamond, 'lotus.lock'), 'utf8'));
    assert.equal(JSON.parse(text).schema, 'lotus-v2/package-lock/1');
  } finally { process.env.PATH = previous; }
  assert.equal(invoked(), '');
});
