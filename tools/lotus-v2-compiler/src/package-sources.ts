/**
 * Decentralized package sources for the Lotus compiler. A package is named by the
 * path where it lives: known forges derive `https://host/owner/repo.git`, and any
 * other host needs an explicit root `[sources]` locator. There is no registry.
 *
 * `fetchPackages` is the only networked entry. It runs git with hooks and templates
 * disabled and writes `.lotus/deps` or `vendor`. `compilePackage` and lock checks
 * stay offline: they read the lock, that cache and declared files, and never spawn git.
 */
import { spawnSync } from 'node:child_process';
import { cpSync, existsSync, mkdirSync, mkdtempSync, readdirSync, readFileSync, realpathSync, renameSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, sep } from 'node:path';
import { hex } from './compiler.js';
import { CompileError } from './diagnostics.js';
import { parseModuleSource } from './generic.js';
import { DEFAULT_PACKAGE_LIMITS, LOCK_FILE, MANIFEST_FILE, PackageError, parseManifest, relPath, resolveWorkspace, scanPackage,
  type Manifest, type PackageInfo, type PackageLimits } from './packages.js';

export const LOCK_SCHEMA_V2 = 'lotus-v2/package-lock/2';
const FORGES = new Set(['github.com', 'gitlab.com', 'bitbucket.org', 'codeberg.org']);
const SEGMENT = /^[A-Za-z0-9][A-Za-z0-9._-]*$/;
const TAG = /^v(0|[1-9][0-9]{0,8})\.(0|[1-9][0-9]{0,8})\.(0|[1-9][0-9]{0,8})$/;
const COMMIT = /^[0-9a-f]{40}$/;
const RANGE = /^([~^])v?(0|[1-9][0-9]{0,8})\.(0|[1-9][0-9]{0,8})\.(0|[1-9][0-9]{0,8})$/;
const GIT_FLAGS = ['-c', 'core.hooksPath=', '-c', 'core.fsmonitor=', '-c', 'credential.helper=', '-c', 'safe.directory=*',
  '-c', 'filter.smudge=', '-c', 'filter.clean=', '-c', 'filter.process=', '-c', 'protocol.file.allow=always'];

export type FetchOptions = {
  /** Write a `vendor/` tree instead of the project-local `.lotus/deps` cache. */
  vendor?: boolean;
  limits?: Partial<PackageLimits>;
  /** Test transport. Default is `https://host/owner/repo.git` for a known forge. */
  resolveRepoUrl?: (repo: { host: string; owner: string; repo: string; module: string }) => string;
};

type SemVer = { major: number; minor: number; patch: number; text: string };
type Selector = { kind: 'tag'; semver: SemVer } | { kind: 'commit'; commit: string } | { kind: 'range'; op: '^' | '~'; semver: SemVer; text: string } | { kind: 'branch'; name: string };
export type ModuleRef = { module: string; host: string; owner?: string; repo?: string; forge: boolean; suffixMajor?: number; subdir: string };
type Requirement = { kind: 'path'; name: string; version: string } | { kind: 'module'; module: string; ref: ModuleRef; selector: Selector };
type Seed = { spec: string; from: string; file: string };
type Requester = { package: string; required: string };
type Locator = { kind: 'path'; path: string } | { kind: 'git'; url: string; dir: string };
type ModChoice = { module: string; ref: ModuleRef; tag?: SemVer; commits: string[]; requesters: Requester[] };
type PathChoice = { name: string; version: string; conflict?: string; requesters: Requester[] };
type Harvested = { info: PackageInfo; seeds: Seed[]; override: boolean; locator: Locator; commit?: string; gitTree?: string };
type Meta = { commit: string; gitTree: string; url: string; dir: string };

const posix = (...parts: string[]): string => parts.filter(part => part !== '' && part !== '.').join('/');

export function isGitLocator(value: string): boolean { return value.startsWith('https://') || value.startsWith('file://'); }

export function assertGitLocator(value: string, file?: string): { url: string; dir: string } {
  const hash = value.lastIndexOf('#');
  const url = hash >= 0 ? value.slice(0, hash) : value;
  const dir = hash >= 0 ? value.slice(hash + 1) : '';
  if (!isGitLocator(url)) throw new PackageError('locator', 'git locator must be an https or file URL', file);
  assertUrl(url, file);
  if (dir) relPath(dir, 'locator dir', file ?? 'lotus.toml');
  return { url, dir };
}

function assertUrl(url: string, file?: string): void {
  if (url.startsWith('-') || /\s/.test(url) || url.includes('\\') || url.includes('@')) throw new PackageError('locator', `refusing git URL ${url}`, file);
  if (url.startsWith('file://')) {
    if (!url.startsWith('file:///')) throw new PackageError('locator', 'file URL must be absolute (file:///...)', file);
    return;
  }
  if (!/^https:\/\/[^/\s]+\/\S+$/.test(url)) throw new PackageError('locator', `git URL must be https or file: ${url}`, file);
}

/** Known-forge and explicit module paths. `/vN` (N >= 2) is only a major suffix when it is the final element. */
export function parseModulePath(module: string, file?: string): ModuleRef {
  if (/\/v[01]$/.test(module)) throw new PackageError('manifest', `module path ${module} must not use a /v0 or /v1 suffix; v0 and v1 have no major suffix`, file);
  if (!module || module.length > 512 || module.includes('\\') || module.includes('@') || module.startsWith('/') || module.endsWith('/'))
    throw new PackageError('manifest', `invalid module path ${module}`, file);
  const parts = module.split('/');
  if (parts.length < 2 || parts.some(part => !SEGMENT.test(part))) throw new PackageError('manifest', `invalid module path ${module}`, file);
  let suffixMajor: number | undefined;
  const suffix = /^v([2-9]|[1-9][0-9]+)$/.exec(parts[parts.length - 1] ?? '');
  if (suffix) {
    suffixMajor = Number(suffix[1]);
    parts.pop();
    if (parts.length < 2) throw new PackageError('manifest', `invalid module path ${module}`, file);
  }
  const host = parts[0]!;
  if (FORGES.has(host)) {
    if (parts.length < 3) throw new PackageError('manifest', `forge module ${module} needs host/owner/repo`, file);
    return { module, host, owner: parts[1], repo: parts[2], forge: true, ...(suffixMajor !== undefined ? { suffixMajor } : {}), subdir: parts.slice(3).join('/') };
  }
  return { module, host, forge: false, ...(suffixMajor !== undefined ? { suffixMajor } : {}), subdir: '' };
}

export function isModulePath(module: string): boolean { try { parseModulePath(module); return true; } catch { return false; } }

/** `https://host/owner/repo.git` for a known forge. Major suffixes and subdirectories are not part of the URL. */
export function forgeGitUrl(module: string, file?: string): string {
  const ref = parseModulePath(module, file);
  if (!ref.forge || !ref.owner || !ref.repo) throw new PackageError('locator', `${module} has no forge repository`, file);
  return `https://${ref.host}/${ref.owner}/${ref.repo}.git`;
}

function semver(major: string, minor: string, patch: string): SemVer {
  const value = { major: Number(major), minor: Number(minor), patch: Number(patch), text: '' };
  value.text = `v${value.major}.${value.minor}.${value.patch}`;
  return value;
}

function classifySelector(selector: string, ref: ModuleRef, file?: string): Selector {
  const tag = TAG.exec(selector);
  if (tag) { const value = semver(tag[1]!, tag[2]!, tag[3]!); assertMajor(ref, value, file); return { kind: 'tag', semver: value }; }
  if (COMMIT.test(selector)) return { kind: 'commit', commit: selector };
  const range = RANGE.exec(selector);
  if (range) { const value = semver(range[2]!, range[3]!, range[4]!); assertMajor(ref, value, file); return { kind: 'range', op: range[1] as '^' | '~', semver: value, text: selector }; }
  return { kind: 'branch', name: selector };
}

function assertMajor(ref: ModuleRef, version: SemVer, file?: string): void {
  if (ref.suffixMajor !== undefined) {
    if (version.major !== ref.suffixMajor) throw new PackageError('manifest', `module ${ref.module} requires v${ref.suffixMajor}.x.y, not ${version.text}`, file);
    return;
  }
  if (version.major >= 2) throw new PackageError('manifest', `${version.text} must use module path ${ref.module}/v${version.major}`, file);
}

export function classifyRequirement(target: string, file?: string): Requirement {
  const at = target.lastIndexOf('@');
  if (at <= 0 || at !== target.indexOf('@')) throw new PackageError('manifest', `dependency ${JSON.stringify(target)} must be name@version or module@selector`, file);
  const left = target.slice(0, at);
  const right = target.slice(at + 1);
  if (!right || right.includes(' ') || right.includes('..')) throw new PackageError('manifest', `invalid selector in ${JSON.stringify(target)}`, file);
  if (!left.includes('/')) {
    if (!/^[a-z_][a-z0-9_]{0,63}$/.test(left) || !/^(0|[1-9][0-9]{0,8})\.(0|[1-9][0-9]{0,8})\.(0|[1-9][0-9]{0,8})$/.test(right))
      throw new PackageError('manifest', `dependency ${JSON.stringify(target)} must be an exact "name@MAJOR.MINOR.PATCH" or a module selector`, file);
    return { kind: 'path', name: left, version: right };
  }
  const ref = parseModulePath(left, file);
  return { kind: 'module', module: left, ref, selector: classifySelector(right, ref, file) };
}

function assertExact(req: Requirement, file?: string): void {
  if (req.kind !== 'module' || req.selector.kind === 'tag' || req.selector.kind === 'commit') return;
  const shown = req.selector.kind === 'branch' ? req.selector.name : req.selector.text;
  throw new PackageError('branch', `selector ${JSON.stringify(shown)} is not an exact vX.Y.Z tag or 40-hex commit; branches and ranges resolve only through lotus-v2-package-update`, file);
}

function cmp(a: SemVer, b: SemVer): number { return a.major - b.major || a.minor - b.minor || a.patch - b.patch; }

function satisfies(version: SemVer, op: '^' | '~', base: SemVer): boolean {
  if (cmp(version, base) < 0) return false;
  if (op === '~') return version.major === base.major && version.minor === base.minor;
  if (base.major > 0) return version.major === base.major;
  if (base.minor > 0) return version.major === 0 && version.minor === base.minor;
  return version.major === 0 && version.minor === 0 && version.patch === base.patch;
}

function selectorText(selector: Selector): string {
  if (selector.kind === 'tag') return selector.semver.text;
  if (selector.kind === 'commit') return selector.commit;
  if (selector.kind === 'range') return selector.text;
  return selector.name;
}

function quotedImports(info: PackageInfo): string[] {
  const specs: string[] = [];
  const entry = info.manifest.entry ? `${info.manifest.source}/${info.manifest.entry}.lotus` : undefined;
  for (const file of info.files) {
    if (!file.path.endsWith('.lotus')) continue;
    const display = posix(info.root, file.path);
    let text: string;
    try { text = new TextDecoder('utf-8', { fatal: true }).decode(file.content); }
    catch { throw new PackageError('manifest', 'file is not valid UTF-8', display); }
    let program;
    try { program = parseModuleSource(text, info.isRoot && file.path === entry, display); }
    catch (error) { if (error instanceof CompileError) throw error; throw new PackageError('parse', (error as Error).message, display); }
    for (const decl of program.imports) if (decl.target.includes('/')) specs.push(decl.target);
  }
  return specs;
}

function collectSeeds(info: PackageInfo): Seed[] {
  const seeds: Seed[] = [];
  for (const spec of info.manifest.dependencies.values()) seeds.push({ spec, from: info.id, file: info.manifestFile });
  for (const spec of quotedImports(info)) seeds.push({ spec, from: info.id, file: info.manifestFile });
  for (const seed of seeds) assertExact(classifyRequirement(seed.spec, seed.file), seed.file);
  return seeds;
}

let templateDir: string | undefined;
let globalConfig: string | undefined;
function gitEnv(): NodeJS.ProcessEnv {
  if (!templateDir) templateDir = mkdtempSync(join(tmpdir(), 'lotus-git-template-'));
  if (!globalConfig) {
    const dir = mkdtempSync(join(tmpdir(), 'lotus-git-config-'));
    globalConfig = join(dir, 'config');
    writeFileSync(globalConfig, '');
  }
  return { ...process.env, GIT_CONFIG_NOSYSTEM: '1', GIT_CONFIG_GLOBAL: globalConfig, GIT_TEMPLATE_DIR: templateDir,
    GIT_TERMINAL_PROMPT: '0', GIT_ASKPASS: 'true', GIT_ATTR_NOSYSTEM: '1' };
}

function runGit(args: string[]): string {
  const result = spawnSync('git', [...GIT_FLAGS, ...args], { encoding: 'utf8', timeout: 60_000, env: gitEnv(), windowsHide: true });
  if (result.error) throw new PackageError('fetch', `git failed to start: ${result.error.message}`);
  if (result.status !== 0) {
    const detail = (result.stderr || result.stdout || '').trim().slice(0, 500);
    throw new PackageError('fetch', `git ${args.filter(arg => !arg.startsWith('-')).slice(0, 3).join(' ')} failed${detail ? `: ${detail}` : ''}`);
  }
  return result.stdout;
}

function locatePackageDir(checkout: string, ref: ModuleRef, prefix: string): string {
  const candidates: string[] = [];
  if (ref.suffixMajor !== undefined) candidates.push(prefix ? `${prefix}/v${ref.suffixMajor}` : `v${ref.suffixMajor}`);
  candidates.push(prefix);
  for (let index = 0; index < candidates.length; index++) {
    const rel = candidates[index]!;
    const manifestPath = join(checkout, ...(rel ? rel.split('/') : []), MANIFEST_FILE);
    if (!existsSync(manifestPath)) continue;
    // A vN/lotus.toml is the package root when it exists. Otherwise the repository
    // (or explicit) directory is the root only when its manifest major matches.
    if (ref.suffixMajor !== undefined && index === 0) return rel;
    const manifest = parseManifest(readFileSync(manifestPath, 'utf8'), rel ? `${rel}/${MANIFEST_FILE}` : MANIFEST_FILE);
    const major = Number(manifest.version.split('.')[0]);
    if (ref.suffixMajor !== undefined) { if (major === ref.suffixMajor) return rel; continue; }
    if (major === 0 || major === 1) return rel;
    throw new PackageError('manifest', `version ${manifest.version} requires module path ${ref.module}/v${major}`, rel ? `${rel}/${MANIFEST_FILE}` : MANIFEST_FILE);
  }
  throw new PackageError('manifest', `no lotus.toml for ${ref.module} identifies its major version`);
}

function contained(parent: string, child: string): boolean {
  const base = parent.endsWith(sep) ? parent : parent + sep;
  return child === parent || child.startsWith(base);
}

function checkIdentity(info: PackageInfo, ref: ModuleRef, selector: string): void {
  if (info.manifest.name !== ref.module) throw new PackageError('manifest', `package name ${JSON.stringify(info.manifest.name)} does not match module path ${ref.module}`, info.manifestFile);
  const major = Number(info.manifest.version.split('.')[0]);
  if (ref.suffixMajor !== undefined && major !== ref.suffixMajor)
    throw new PackageError('manifest', `module ${ref.module} requires major ${ref.suffixMajor}, found ${info.manifest.version}`, info.manifestFile);
  if (ref.suffixMajor === undefined && major >= 2)
    throw new PackageError('manifest', `version ${info.manifest.version} requires module path suffix /v${major}`, info.manifestFile);
  if (selector.startsWith('v') && info.manifest.version !== selector.slice(1))
    throw new PackageError('version-conflict', `tag ${selector} resolved to manifest version ${info.manifest.version}`, info.manifestFile);
  if (info.manifest.kind !== 'library') throw new PackageError('declaration-only', `dependency ${ref.module}@${selector} must be a library package`, info.manifestFile);
}

function fetchInto(project: string, cacheRoot: string, ref: ModuleRef, selector: string, url: string, prefix: string): Meta & { checkoutRel: string } {
  assertUrl(url);
  const temp = mkdtempSync(join(tmpdir(), 'lotus-git-fetch-'));
  try {
    runGit(['init', '--template', templateDir ?? gitEnv().GIT_TEMPLATE_DIR!, temp]);
    runGit(['-C', temp, 'remote', 'add', 'origin', url]);
    runGit(['-C', temp, 'fetch', '--depth=1', 'origin', selector]);
    runGit(['-C', temp, 'checkout', '--detach', 'FETCH_HEAD']);
    const commit = runGit(['-C', temp, 'rev-parse', 'HEAD']).trim();
    const gitTree = runGit(['-C', temp, 'rev-parse', 'HEAD^{tree}']).trim();
    if (!COMMIT.test(commit) || !COMMIT.test(gitTree)) throw new PackageError('fetch', 'git did not return a commit and tree id');
    rmSync(join(temp, '.git'), { recursive: true, force: true });
    const dir = locatePackageDir(temp, ref, prefix);
    const selectorRel = posix(cacheRoot, ref.module, selector);
    const checkoutRel = posix(selectorRel, commit);
    const selectorAbs = join(project, ...selectorRel.split('/'));
    rmSync(selectorAbs, { recursive: true, force: true });
    mkdirSync(selectorAbs, { recursive: true });
    const checkoutAbs = join(project, ...checkoutRel.split('/'));
    try { renameSync(temp, checkoutAbs); }
    catch (error) {
      if ((error as NodeJS.ErrnoException).code !== 'EXDEV') throw error;
      cpSync(temp, checkoutAbs, { recursive: true });
      rmSync(temp, { recursive: true, force: true });
    }
    const meta: Meta = { commit, gitTree, url, dir };
    writeFileSync(join(selectorAbs, `${commit}.json`), JSON.stringify(meta) + '\n');
    return { ...meta, checkoutRel };
  } catch (error) {
    rmSync(temp, { recursive: true, force: true });
    throw error;
  }
}

function readMeta(project: string, module: string, selector: string): Meta & { checkoutRel: string } {
  const hits: { root: string; commit: string }[] = [];
  for (const root of ['.lotus/deps', 'vendor']) {
    const dir = join(project, ...posix(root, module, selector).split('/'));
    if (!existsSync(dir)) continue;
    for (const name of readdirSync(dir)) {
      if (!/^[0-9a-f]{40}\.json$/.test(name)) continue;
      const commit = name.slice(0, 40);
      if (existsSync(join(dir, commit))) hits.push({ root, commit });
    }
  }
  const roots = new Set(hits.map(hit => hit.root));
  if (hits.length === 0) throw new PackageError('unfetched', `no cached ${module}@${selector}; run lotus-v2-package-fetch (compile does not fetch)`);
  if (roots.size > 1) throw new PackageError('unfetched', `both .lotus/deps and vendor contain ${module}@${selector}; keep only one`);
  if (hits.length !== 1) throw new PackageError('unfetched', `cached ${module}@${selector} has more than one commit; run lotus-v2-package-fetch`);
  const hit = hits[0]!;
  const selectorRel = posix(hit.root, module, selector);
  let meta: Meta;
  try { meta = JSON.parse(readFileSync(join(project, ...selectorRel.split('/'), `${hit.commit}.json`), 'utf8')) as Meta; }
  catch { throw new PackageError('unfetched', `cached metadata for ${module}@${selector} is unreadable`); }
  if (meta.commit !== hit.commit || !COMMIT.test(meta.gitTree) || typeof meta.url !== 'string' || typeof meta.dir !== 'string')
    throw new PackageError('unfetched', `cached metadata for ${module}@${selector} is not a fetch record`);
  if (meta.dir) relPath(meta.dir, 'cached dir', `${module}@${selector}`);
  assertUrl(meta.url);
  return { ...meta, checkoutRel: posix(selectorRel, hit.commit) };
}

function adopt(project: string, checkoutRel: string, dir: string, ref: ModuleRef, selector: string, budget: { bytes: number; limit: number }): PackageInfo {
  const packageRel = dir ? posix(checkoutRel, dir) : checkoutRel;
  const checkoutAbs = join(project, ...checkoutRel.split('/'));
  const packageAbs = join(project, ...packageRel.split('/'));
  if (!contained(realpathSync(checkoutAbs), realpathSync(packageAbs)))
    throw new PackageError('symlink-escape', 'package root resolves outside the fetched repository', packageRel);
  const info = scanPackage(project, packageRel, false, budget);
  checkIdentity(info, ref, selector);
  info.id = `${ref.module}@${selector}`;
  info.selectedVersion = selector;
  return info;
}

type Session = {
  project: string;
  root: PackageInfo;
  limits: PackageLimits;
  budget: { bytes: number; limit: number };
  online?: FetchOptions;
};

function derive(session: Session, ref: ModuleRef): { url: string; dir: string; replaced: boolean } {
  const replacement = session.root.manifest.replace.get(ref.module);
  if (replacement !== undefined && isGitLocator(replacement)) return { ...assertGitLocator(replacement, session.root.manifestFile), replaced: true };
  if (!ref.forge) {
    const pinned = session.root.manifest.sources.get(ref.module);
    if (pinned === undefined) throw new PackageError('locator', `no root [sources] locator for ${ref.module}; unknown hosts are not guessed and dependency locators are ignored`, session.root.manifestFile);
    return { ...assertGitLocator(pinned, session.root.manifestFile), replaced: false };
  }
  const url = session.online?.resolveRepoUrl?.({ host: ref.host, owner: ref.owner ?? '', repo: ref.repo ?? '', module: ref.module })
    ?? forgeGitUrl(ref.module, session.root.manifestFile);
  assertUrl(url, session.root.manifestFile);
  return { url, dir: '', replaced: false };
}

function prefixFor(ref: ModuleRef, explicitDir: string, replaced: boolean): string {
  if (replaced || !ref.forge) return explicitDir;
  return ref.subdir;
}

function loadGit(session: Session, ref: ModuleRef, selector: string, replacedGit: { url: string; dir: string } | undefined): Harvested {
  const derived = replacedGit ?? derive(session, ref);
  const located = session.online
    ? fetchInto(session.project, session.online.vendor ? 'vendor' : '.lotus/deps', ref, selector, derived.url, prefixFor(ref, derived.dir, replacedGit !== undefined))
    : readMeta(session.project, ref.module, selector);
  const info = adopt(session.project, located.checkoutRel, located.dir, ref, selector, session.budget);
  return { info, seeds: collectSeeds(info), override: replacedGit !== undefined, locator: { kind: 'git', url: located.url, dir: located.dir }, commit: located.commit, gitTree: located.gitTree };
}

function loadPathReplace(session: Session, choice: ModChoice, path: string): Harvested {
  relPath(path, `[replace] ${choice.module}`, session.root.manifestFile);
  const info = scanPackage(session.project, path, false, session.budget);
  if (info.manifest.name !== choice.module) throw new PackageError('manifest', `replacement ${path} is ${info.id}, not ${choice.module}`, info.manifestFile);
  const major = Number(info.manifest.version.split('.')[0]);
  if (choice.ref.suffixMajor !== undefined && major !== choice.ref.suffixMajor)
    throw new PackageError('manifest', `replacement ${path} has major ${major}, required ${choice.ref.suffixMajor}`, info.manifestFile);
  if (choice.ref.suffixMajor === undefined && major >= 2)
    throw new PackageError('manifest', `replacement version ${info.manifest.version} requires /v${major}`, info.manifestFile);
  if (info.manifest.kind !== 'library') throw new PackageError('declaration-only', `dependency ${choice.module} must be a library package`, info.manifestFile);
  const selected = `v${info.manifest.version}`;
  info.id = `${choice.module}@${selected}`;
  info.selectedVersion = selected;
  return { info, seeds: collectSeeds(info), override: true, locator: { kind: 'path', path } };
}

function loadPath(session: Session, choice: PathChoice): Harvested {
  const locator = session.root.manifest.sources.get(choice.name);
  if (locator === undefined || isModulePath(choice.name)) throw new PackageError('manifest', `no [sources] locator for ${choice.name} in the root manifest`, session.root.manifestFile);
  const info = scanPackage(session.project, locator, false, session.budget);
  if (info.id !== `${choice.name}@${choice.version}`) throw new PackageError('version-conflict', `locator ${locator} contains ${info.id}, expected ${choice.name}@${choice.version}`, info.manifestFile);
  if (info.manifest.kind !== 'library') throw new PackageError('declaration-only', `dependency ${info.id} must be a library package`, info.manifestFile);
  return { info, seeds: collectSeeds(info), override: false, locator: { kind: 'path', path: locator } };
}

function semverOf(selected: string | undefined): SemVer | undefined {
  const match = /^v(0|[1-9][0-9]{0,8})\.(0|[1-9][0-9]{0,8})\.(0|[1-9][0-9]{0,8})$/.exec(selected ?? '');
  return match ? semver(match[1]!, match[2]!, match[3]!) : undefined;
}

function selectorKey(choice: ModChoice): string {
  if (choice.tag) return choice.tag.text;
  const commit = choice.commits[0];
  if (choice.commits.length === 1 && commit) return commit;
  throw new PackageError('manifest', `no version selected for ${choice.module}`);
}

function pushReq(list: Requester[], pkg: string, required: string): void {
  if (!list.some(item => item.package === pkg && item.required === required)) list.push({ package: pkg, required });
}

/** Resolve module requirements from the root and selected manifests. Offline when `online` is omitted. */
export function resolveDistributedSources(project: string, root: PackageInfo, limits: PackageLimits, budget: { bytes: number; limit: number }, online?: FetchOptions):
  { packages: Map<string, PackageInfo>; lockText: string; modules: Map<string, PackageInfo> } {
  const session: Session = { project, root, limits, budget, ...(online ? { online } : {}) };
  for (const [key, value] of root.manifest.replace) {
    if (!isModulePath(key)) throw new PackageError('manifest', `[replace] key ${key} must be a module path`, root.manifestFile);
    if (!isGitLocator(value)) relPath(value, `[replace] ${key}`, root.manifestFile);
    else assertGitLocator(value, root.manifestFile);
  }
  for (const [key, value] of root.manifest.sources) if (isModulePath(key)) {
    const ref = parseModulePath(key, root.manifestFile);
    if (ref.forge) throw new PackageError('manifest', `[sources] cannot override forge module ${key}; use [replace]`, root.manifestFile);
    assertGitLocator(value, root.manifestFile);
  }
  // Go minimal version selection: the highest tag required by the root or by a
  // selected version. Requirements of a version that lost the max are ignored.
  // A raw commit is never bumped to a different object. Tag and commit agree only
  // when that tag resolves to the commit.
  const cache = new Map<string, Harvested>();
  const selectedMods = new Map<string, { selector: string; got: Harvested }>();
  const selectedPaths = new Map<string, { got: Harvested }>();
  const edgesFrom = (): Seed[] => {
    const edges = [...collectSeeds(root)];
    for (const item of selectedMods.values()) edges.push(...item.got.seeds);
    for (const item of selectedPaths.values()) edges.push(...item.got.seeds);
    return edges;
  };
  const buildChoices = (edges: Seed[]): { choices: Map<string, ModChoice>; paths: Map<string, PathChoice> } => {
    const choices = new Map<string, ModChoice>();
    const paths = new Map<string, PathChoice>();
    for (const seed of edges) {
      const req = classifyRequirement(seed.spec, seed.file);
      if (req.kind === 'path') {
        if (req.name === root.manifest.name) throw new PackageError('package-cycle', `${seed.from} depends on the root package ${root.id}`, seed.file);
        const prior = paths.get(req.name);
        if (prior && prior.version !== req.version) prior.conflict = `${seed.from} requires ${req.name}@${req.version} but ${prior.version} is also required`;
        const choice = prior ?? { name: req.name, version: req.version, requesters: [] };
        if (!prior) paths.set(req.name, choice);
        pushReq(choice.requesters, seed.from, req.version);
        continue;
      }
      if (req.module === root.manifest.name) throw new PackageError('package-cycle', `${seed.from} depends on the root package ${root.id}`, seed.file);
      const prior = choices.get(req.module);
      const choice = prior ?? { module: req.module, ref: req.ref, commits: [], requesters: [] };
      if (!prior) choices.set(req.module, choice);
      pushReq(choice.requesters, seed.from, selectorText(req.selector));
      if (req.selector.kind === 'tag') { if (!choice.tag || cmp(req.selector.semver, choice.tag) > 0) choice.tag = req.selector.semver; }
      else if (req.selector.kind === 'commit' && !choice.commits.includes(req.selector.commit)) choice.commits.push(req.selector.commit);
    }
    return { choices, paths };
  };
  const loadChoice = (choice: ModChoice): Harvested => {
    const replacement = root.manifest.replace.get(choice.module);
    if (replacement !== undefined && !isGitLocator(replacement)) {
      const key = `${choice.module}\0replace`;
      const cached = cache.get(key);
      if (cached) return cached;
      const got = loadPathReplace(session, choice, replacement);
      cache.set(key, got);
      return got;
    }
    const gitReplace = replacement !== undefined ? assertGitLocator(replacement, root.manifestFile) : undefined;
    const key = `${choice.module}\0${gitReplace ? 'git-replace:' : ''}${selectorKey(choice)}`;
    const cached = cache.get(key);
    if (cached) return cached;
    const got = loadGit(session, choice.ref, selectorKey(choice), gitReplace);
    cache.set(key, got);
    return got;
  };
  const assertCovers = (got: Harvested, choice: ModChoice): void => {
    if (choice.commits.length && got.locator.kind === 'path')
      throw new PackageError('version-conflict', `path replacement for ${choice.module} cannot satisfy commit pin ${choice.commits.join(', ')}`, got.info.manifestFile);
    const pinned = choice.commits[0];
    if (choice.tag && choice.commits.length === 1 && pinned && got.commit !== pinned)
      throw new PackageError('version-conflict', `tag ${choice.tag.text} of ${choice.module} resolves to ${got.commit ?? 'no commit'}, not ${pinned}`, got.info.manifestFile);
    if (choice.tag && got.locator.kind === 'path') {
      const [major, minor, patch] = got.info.manifest.version.split('.').map(Number);
      const local = { major: major ?? 0, minor: minor ?? 0, patch: patch ?? 0, text: '' };
      if (cmp(local, choice.tag) < 0) throw new PackageError('version-conflict', `${got.info.id} is older than required ${choice.tag.text}`, got.info.manifestFile);
    }
  };
  let stable = false;
  for (let guard = 0; guard < limits.maxPackages * 8 + 8 && !stable; guard++) {
    const { choices, paths } = buildChoices(edgesFrom());
    if (choices.size + paths.size > limits.maxPackages) throw new PackageError('limit', `package graph exceeds ${limits.maxPackages} packages`, root.manifestFile);
    let upgraded = false;
    for (const choice of choices.values()) {
      const prev = selectedMods.get(choice.module);
      if (!prev || !choice.tag) continue;
      if (prev.selector === choice.tag.text) continue;
      const loaded = semverOf(prev.selector);
      if (loaded && cmp(choice.tag, loaded) <= 0) continue;
      selectedMods.set(choice.module, { selector: choice.tag.text, got: loadChoice(choice) });
      upgraded = true;
    }
    if (upgraded) continue;
    let dropped = false;
    for (const key of [...selectedMods.keys()]) if (!choices.has(key)) { selectedMods.delete(key); dropped = true; }
    for (const key of [...selectedPaths.keys()]) if (!paths.has(key)) { selectedPaths.delete(key); dropped = true; }
    if (dropped) continue;
    let moved = false;
    for (const choice of choices.values()) {
      if (choice.tag || choice.commits.length !== 1) continue;
      const prev = selectedMods.get(choice.module);
      const only = choice.commits[0]!;
      if (prev && prev.got.commit !== only) { selectedMods.set(choice.module, { selector: only, got: loadChoice(choice) }); moved = true; }
    }
    if (moved) continue;
    for (const choice of paths.values()) if (choice.conflict) throw new PackageError('version-conflict', choice.conflict, root.manifestFile);
    for (const choice of choices.values()) {
      if (choice.commits.length > 1) throw new PackageError('version-conflict', `${choice.module} is pinned to commits ${choice.commits.join(' and ')}`, root.manifestFile);
      const prev = selectedMods.get(choice.module);
      if (prev) assertCovers(prev.got, choice);
    }
    let added = false;
    for (const choice of choices.values()) {
      if (selectedMods.has(choice.module)) continue;
      selectedMods.set(choice.module, { selector: selectorKey(choice), got: loadChoice(choice) });
      added = true;
    }
    for (const choice of paths.values()) {
      if (selectedPaths.has(choice.name)) continue;
      const key = `path\0${choice.name}`;
      let got = cache.get(key);
      if (!got) { got = loadPath(session, choice); cache.set(key, got); }
      selectedPaths.set(choice.name, { got });
      added = true;
    }
    if (!added) stable = true;
  }
  if (!stable) throw new PackageError('limit', 'version selection did not converge', root.manifestFile);
  const { choices, paths } = buildChoices(edgesFrom());
  const packages = new Map<string, PackageInfo>();
  const modules = new Map<string, PackageInfo>();
  const winners: { harvested: Harvested; requesters: Requester[] }[] = [];
  const keep = new Set<string>([root.id]);
  for (const choice of choices.values()) {
    const got = selectedMods.get(choice.module)?.got;
    if (!got) throw new PackageError('unfetched', `missing ${choice.module}@${selectorKey(choice)}`);
    assertCovers(got, choice);
    packages.set(got.info.manifest.name, got.info);
    modules.set(choice.module, got.info);
    keep.add(got.info.id);
    winners.push({ harvested: got, requesters: choice.requesters });
  }
  for (const choice of paths.values()) {
    if (choice.conflict) throw new PackageError('version-conflict', choice.conflict, root.manifestFile);
    const got = selectedPaths.get(choice.name)?.got;
    if (!got) throw new PackageError('manifest', `missing path package ${choice.name}`);
    packages.set(got.info.manifest.name, got.info);
    keep.add(got.info.id);
    winners.push({ harvested: got, requesters: choice.requesters });
  }
  for (const key of root.manifest.sources.keys()) {
    const used = isModulePath(key) ? choices.has(key) : paths.has(key);
    if (!used) throw new PackageError('manifest', `[sources] locator ${key} is not used by the dependency graph`, root.manifestFile);
  }
  for (const key of root.manifest.replace.keys()) if (!choices.has(key)) throw new PackageError('manifest', `[replace] ${key} is not used by the dependency graph`, root.manifestFile);
  const state = new Map<string, 'active' | 'done'>();
  const visit = (info: PackageInfo, chain: string[]): void => {
    if (state.get(info.id) === 'done') return;
    if (state.get(info.id) === 'active') throw new PackageError('package-cycle', `package dependency cycle: ${[...chain, info.id].join(' -> ')}`, info.manifestFile);
    state.set(info.id, 'active');
    const winner = winners.find(item => item.harvested.info === info);
    for (const seed of winner?.harvested.seeds ?? []) {
      const req = classifyRequirement(seed.spec, seed.file);
      const dep = req.kind === 'module' ? modules.get(req.module) : packages.get(req.name);
      if (!dep) throw new PackageError('manifest', `missing dependency ${seed.spec}`, info.manifestFile);
      visit(dep, [...chain, info.id]);
    }
    state.set(info.id, 'done');
  };
  for (const info of packages.values()) visit(info, []);
  const entries = winners.map(({ harvested: got, requesters }) => lockEntry(got, requesters.filter(item => keep.has(item.package))));
  entries.sort((a, b) => a.name < b.name ? -1 : a.name > b.name ? 1 : a.version < b.version ? -1 : a.version > b.version ? 1 : 0);
  const replace: Record<string, Locator> = {};
  for (const key of [...root.manifest.replace.keys()].sort()) replace[key] = replaceLocator(root.manifest.replace.get(key)!, root.manifestFile);
  const lock = {
    schema: LOCK_SCHEMA_V2,
    root: { name: root.manifest.name, version: root.manifest.version,
      ...(root.manifest.edition !== undefined ? { edition: root.manifest.edition } : {}),
      ...(root.manifest.optimizer !== undefined ? { optimizer: root.manifest.optimizer } : {}),
      dependencies: Object.fromEntries([...root.manifest.dependencies].sort(([a], [b]) => a < b ? -1 : a > b ? 1 : 0)),
      ...(root.manifest.replace.size ? { replace } : {}) },
    packages: entries,
  };
  return { packages, lockText: JSON.stringify(lock, null, 2) + '\n', modules };
}

function replaceLocator(value: string, file: string): Locator {
  if (isGitLocator(value)) { const loc = assertGitLocator(value, file); return { kind: 'git', url: loc.url, dir: loc.dir }; }
  return { kind: 'path', path: relPath(value, '[replace]', file) };
}

function lockEntry(got: Harvested, requesters: Requester[]): { name: string; version: string; commit?: string; gitTree?: string; locator: Locator; override: boolean; requesters: Requester[]; root: string; dependencies: Record<string, string>; files: { path: string; digest: string }[]; treeDigest: string } {
  const requestersSorted = [...requesters].sort((a, b) => a.package < b.package ? -1 : a.package > b.package ? 1 : a.required < b.required ? -1 : a.required > b.required ? 1 : 0);
  return { name: got.info.manifest.name, version: got.info.selectedVersion ?? got.info.manifest.version,
    ...(got.commit ? { commit: got.commit } : {}), ...(got.gitTree ? { gitTree: got.gitTree } : {}),
    locator: got.locator, override: got.override, requesters: requestersSorted, root: got.info.root,
    dependencies: Object.fromEntries([...got.info.manifest.dependencies].sort(([a], [b]) => a < b ? -1 : a > b ? 1 : 0)),
    files: got.info.files.map(file => ({ path: file.path, digest: hex(file.digest) })), treeDigest: hex(got.info.treeDigest) };
}

function listRefs(url: string): { tags: { semver: SemVer; commit: string }[]; heads: Map<string, string> } {
  const out = runGit(['ls-remote', url, 'refs/tags/*', 'refs/heads/*']);
  const tags = new Map<string, string>();
  const peeled = new Map<string, string>();
  const heads = new Map<string, string>();
  for (const line of out.split('\n')) {
    if (!line.trim()) continue;
    const [sha, ref] = line.split('\t');
    if (!sha || !ref || !COMMIT.test(sha)) continue;
    if (ref.startsWith('refs/heads/')) heads.set(ref.slice('refs/heads/'.length), sha);
    else if (ref.startsWith('refs/tags/') && ref.endsWith('^{}')) peeled.set(ref.slice('refs/tags/'.length, -3), sha);
    else if (ref.startsWith('refs/tags/')) tags.set(ref.slice('refs/tags/'.length), sha);
  }
  const parsed: { semver: SemVer; commit: string }[] = [];
  for (const [name, sha] of tags) {
    const match = TAG.exec(name);
    if (!match) continue;
    parsed.push({ semver: semver(match[1]!, match[2]!, match[3]!), commit: peeled.get(name) ?? sha });
  }
  return { tags: parsed, heads };
}

function resolveInexact(module: string, selector: string, manifest: Manifest, options: FetchOptions): string {
  const ref = parseModulePath(module, MANIFEST_FILE);
  const classified = classifySelector(selector, ref, MANIFEST_FILE);
  if (classified.kind === 'tag' || classified.kind === 'commit') return `${module}@${selectorText(classified)}`;
  const session: Session = { project: '', root: { manifest } as PackageInfo, limits: { maxPackages: 1, maxModules: 1, maxImportDepth: 1, maxImportBindings: 1, maxSourceBytes: 1 }, budget: { bytes: 0, limit: 1 }, online: options };
  const url = derive(session, ref).url;
  const refs = listRefs(url);
  if (classified.kind === 'range') {
    const matches = refs.tags.filter(tag => {
      if (ref.suffixMajor !== undefined ? tag.semver.major !== ref.suffixMajor : tag.semver.major >= 2) return false;
      return satisfies(tag.semver, classified.op, classified.semver);
    });
    if (!matches.length) throw new PackageError('fetch', `no tag of ${module} satisfies ${selector}`);
    matches.sort((a, b) => cmp(a.semver, b.semver));
    return `${module}@${matches[matches.length - 1]!.semver.text}`;
  }
  if (!/^[A-Za-z0-9][A-Za-z0-9._/-]{0,127}$/.test(classified.name) || classified.name.split('/').includes('..'))
    throw new PackageError('branch', `refusing branch name ${JSON.stringify(classified.name)}`);
  const commit = refs.heads.get(classified.name);
  if (!commit) throw new PackageError('fetch', `branch ${JSON.stringify(classified.name)} was not found for ${module}`);
  return `${module}@${commit}`;
}

function replaceAliasValue(text: string, alias: string, from: string, to: string): string {
  const escaped = from.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const pattern = new RegExp(`(^|\\n)(${alias}[ \\t]*=[ \\t]*")${escaped}(")`);
  const next = text.replace(pattern, `$1$2${to}$3`);
  if (next === text) throw new PackageError('manifest', `could not rewrite dependency ${alias}`, MANIFEST_FILE);
  return next;
}

/** Fetch exact tags and commits into the cache and write `lotus.lock`. Branch names and ranges are rejected. */
export function fetchPackages(projectDir: string, options: FetchOptions = {}): string {
  const workspace = resolveWorkspace(projectDir, { ...DEFAULT_PACKAGE_LIMITS, ...(options.limits ?? {}) }, options);
  writeFileSync(join(projectDir, LOCK_FILE), workspace.lockText);
  return workspace.lockText;
}

/**
 * Resolve one root dependency that may be a branch or semver range (`^` / `~`), rewrite that
 * manifest entry to an exact tag or commit, then fetch. This is the only command that may name a branch.
 */
export function updatePackages(projectDir: string, spec: string, options: FetchOptions = {}): string {
  const file = join(projectDir, MANIFEST_FILE);
  const text = readFileSync(file, 'utf8');
  const manifest = parseManifest(text, MANIFEST_FILE);
  const at = spec.lastIndexOf('@');
  const left = at < 0 ? spec : spec.slice(0, at);
  const selector = at < 0 ? undefined : spec.slice(at + 1);
  if (!left || left.startsWith('-')) throw new PackageError('manifest', 'usage: lotus-v2-package-update DIR SPEC [--vendor]');
  let alias: string | undefined;
  let module: string | undefined;
  if (left.includes('/')) module = left;
  else alias = left;
  const entries = [...manifest.dependencies].map(([name, value]) => ({ name, value, req: classifyRequirement(value, MANIFEST_FILE) }));
  const entry = alias ? entries.find(item => item.name === alias) : entries.find(item => item.req.kind === 'module' && item.req.module === module);
  if (!entry || entry.req.kind !== 'module') throw new PackageError('manifest', `update spec ${JSON.stringify(spec)} does not name a module dependency of the root package`, MANIFEST_FILE);
  const currentSelector = selector ?? selectorText(entry.req.selector);
  const resolved = resolveInexact(entry.req.module, currentSelector, manifest, options);
  if (resolved !== entry.value) writeFileSync(file, replaceAliasValue(text, entry.name, entry.value, resolved));
  return fetchPackages(projectDir, options);
}
