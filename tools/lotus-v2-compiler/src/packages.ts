/**
 * CABI-07: deterministic package/module resolution for the contract compiler.
 *
 * Build-time only. Nothing here is consensus, VM, runtime or transaction code.
 * Local path packages and `compilePackage` read declared files, `lotus.lock` and
 * (for module paths) the project cache or `vendor/` tree. They do not spawn git
 * or use the network. `lotus-v2-package-fetch` is the networked entry. The resolver
 * parses each immutable module identity once, links explicit imports into one helper
 * namespace and hands the linked program to the existing scheduler/compiler. Library
 * contracts are compiled into the same program so `contract_root` / `leaf_hash` /
 * `merkle_root` pin their bytecode roots; helpers stay inlined. There is no registry,
 * clock, VM call (`OP_DEFINE` / `OP_INVOKE`) or environment input.
 */
import { lstatSync, readdirSync, readFileSync, realpathSync, statSync, writeFileSync } from 'node:fs';
import { join, relative, sep } from 'node:path';
import { bytes, concat, cs, hex, tagged, type Span } from './compiler.js';
import { CompileError, SourceManager, diagnostic } from './diagnostics.js';
import { compileLinkedProgramAsync, parseModuleSource, type CompileOptions, type Contract, type ContractArtifact, type Expr, type Helper,
  type HelperStmt, type ImportDecl, type LinkedContract, type Method, type Param, type Program, type SchedulerEvent, type Stmt } from './generic.js';
import { assertPortableName } from './names.js';
import { assertGitLocator, classifyRequirement, isGitLocator, isModulePath, resolveDistributedSources, type FetchOptions } from './package-sources.js';
import { PromiseScheduler } from './scheduler.js';
import { parseTomlSubset, type TomlValue } from './toml-subset.js';

export const COMPILER_NAME = '@lotus/v2-payment-compiler';
export const COMPILER_VERSION = '0.1.0';
export const MANIFEST_FILE = 'lotus.toml';
export const LOCK_FILE = 'lotus.lock';
export const LOCK_SCHEMA = 'lotus-v2/package-lock/1';
export const BUILD_GRAPH_SCHEMA = 'lotus-v2/build-graph/1';
const TARGET = 'P01-P02-P03-candidate-2026-10-14';
const BUILTINS = new Set(['leaf_hash', 'contract_root', 'merkle_root', 'checksig', 'sha256', 'hash256', 'blake3', 'num_bytes', 'check_lock', 'check_sequence']);
const COMMITMENT_BUILTINS = new Set(['leaf_hash', 'contract_root', 'merkle_root']);
const MAX_WALK_ENTRIES = 4096;

export type PackageLimits = { maxPackages: number; maxModules: number; maxImportDepth: number; maxImportBindings: number; maxSourceBytes: number };
export const DEFAULT_PACKAGE_LIMITS: PackageLimits = { maxPackages: 64, maxModules: 256, maxImportDepth: 32, maxImportBindings: 4096, maxSourceBytes: 4 * 1024 * 1024 };

export type PackageErrorCode = 'manifest' | 'path-escape' | 'symlink-escape' | 'path-collision' | 'undeclared-file' | 'missing-module' | 'lock-missing' |
  'lock-mismatch' | 'lock-stale' | 'version-conflict' | 'package-cycle' | 'parse' | 'unknown-alias' | 'not-exported' | 'missing-symbol' |
  'visibility' | 'duplicate-name' | 'import-cycle' | 'declaration-only' | 'limit' | 'branch' | 'unfetched' | 'locator' | 'fetch';

/** Diagnostic with a project-relative file and an optional UTF-8 byte span (`file:start..end: message [code]`). */
export class PackageError extends Error {
  constructor(readonly code: PackageErrorCode, readonly detail: string, readonly file?: string, readonly span?: Span) {
    super(`${file ? `${file}${span ? `:${span.start}..${span.end}` : ''}: ` : ''}${detail} [${code}]`);
    this.name = 'PackageError';
  }
}

const PACKAGE_DIAGNOSTIC: Record<PackageErrorCode, string> = {
  manifest: 'E0901', 'path-escape': 'E0902', 'symlink-escape': 'E0903', 'path-collision': 'E0904', 'undeclared-file': 'E0905',
  'missing-module': 'E0906', 'lock-missing': 'E0907', 'lock-mismatch': 'E0908', 'lock-stale': 'E0909', 'version-conflict': 'E0910',
  'package-cycle': 'E0911', parse: 'E0912', 'unknown-alias': 'E0913', 'not-exported': 'E0914', 'missing-symbol': 'E0915',
  visibility: 'E0916', 'duplicate-name': 'E0917', 'import-cycle': 'E0918', 'declaration-only': 'E0919', limit: 'E0920',
  branch: 'E0921', unfetched: 'E0922', locator: 'E0923', fetch: 'E0924',
};
/** CLI view of a package error. The library still throws `PackageError` with its own code. */
export function packageCompileError(error: PackageError, sources = new SourceManager()): CompileError {
  const primary = error.file ? { file: error.file, ...(error.span ? { span: error.span } : {}) } : undefined;
  return new CompileError([diagnostic(PACKAGE_DIAGNOSTIC[error.code], error.detail, primary)], sources);
}

export type Manifest = { name: string; version: string; kind: 'library' | 'contract'; source: string; modules: string[]; exports: string[]; entry?: string;
  /** alias -> `name@version` or `module@selector` */ dependencies: Map<string, string>;
  /** Root-only locators. Short names are project-relative paths; other hosts are git URLs. */ sources: Map<string, string>;
  /** Root-only module-path replacements (relative path or git locator). Never inherited. */ replace: Map<string, string> };
export type PackageFile = { path: string; digest: Uint8Array; content: Uint8Array };
export type PackageInfo = { id: string; manifest: Manifest; root: string; manifestFile: string; files: PackageFile[]; treeDigest: Uint8Array; isRoot: boolean;
  /** Git/replace packages record the selected tag (`vX.Y.Z`) or commit. Path packages omit it. */ selectedVersion?: string };
type ModuleNode = { id: string; pkg: PackageInfo; path: string; file: string; digest: Uint8Array; program: Program; isEntry: boolean; imports: { decl: ImportDecl; target: ModuleNode }[] };
type LockPackage = { name: string; version: string; locator: { kind: 'path'; path: string }; root: string; dependencies: Record<string, string>; files: { path: string; digest: string }[]; treeDigest: string };
export type LockFile = { schema: typeof LOCK_SCHEMA; root: { name: string; version: string; dependencies: Record<string, string> }; packages: LockPackage[] };

export type BuildGraph = {
  schema: typeof BUILD_GRAPH_SCHEMA;
  compiler: { name: string; version: string; profile: 'optimized' | 'unoptimized' };
  target: string;
  root: { package: string; module: string };
  lockDigest: string;
  packages: { id: string; name: string; version: string; root: string; treeDigest: string; dependencies: Record<string, string> }[];
  modules: { id: string; package: string; path: string; file: string; sourceDigest: string; interfaceDigest: string;
    exports: { name: string; signature: string; digest: string }[]; imports: string[] }[];
  digest: string;
};
export type PackageCompileOptions = CompileOptions & { limits?: Partial<PackageLimits> };
export type PackageBuild = { artifact: ContractArtifact; trace: SchedulerEvent[]; parses: Record<string, number> };

const utf8 = (text: string): Uint8Array => new TextEncoder().encode(text);
const str = (text: string): Uint8Array => bytes(utf8(text));
const fold = (text: string): string => text.normalize('NFKC').toUpperCase().toLowerCase().normalize('NFKC');
const posix = (...parts: string[]): string => parts.filter(part => part !== '' && part !== '.').join('/') || '.';
const sorted = (record: Map<string, string>): Record<string, string> => Object.fromEntries([...record].sort(([a], [b]) => a < b ? -1 : a > b ? 1 : 0));
function graphDependencies(pkg: PackageInfo, ws: Workspace): Record<string, string> {
  if (!ws.modules) return sorted(pkg.manifest.dependencies);
  const mapped = new Map<string, string>();
  for (const [alias, spec] of pkg.manifest.dependencies) {
    const req = classifyRequirement(spec, pkg.manifestFile);
    const selected = req.kind === 'module' ? ws.modules.get(req.module) : ws.packages.get(req.name);
    if (!selected) throw new PackageError('manifest', `missing dependency ${spec}`, pkg.manifestFile);
    mapped.set(alias, selected.id);
  }
  return sorted(mapped);
}
const byName = <T extends { name: string }>(a: T, b: T): number => a.name < b.name ? -1 : a.name > b.name ? 1 : 0;

function decode(data: Uint8Array, file: string): string {
  try { return new TextDecoder('utf-8', { fatal: true, ignoreBOM: false }).decode(data); }
  catch { throw new PackageError('manifest', 'file is not valid UTF-8', file); }
}

/** Project/package-relative path: no absolute paths, traversal, empty or `.` segments, backslashes. */
export function relPath(value: string, what: string, file: string): string {
  if (value.startsWith('/') || /^[A-Za-z]:/.test(value) || value.includes('\\')) throw new PackageError('path-escape', `${what} ${JSON.stringify(value)} must be a relative POSIX path`, file);
  const parts = value.split('/');
  if (parts.includes('..')) throw new PackageError('path-escape', `${what} ${JSON.stringify(value)} contains path traversal`, file);
  for (const part of parts) if (!/^[A-Za-z0-9_][A-Za-z0-9_.-]*$/.test(part)) throw new PackageError('manifest', `${what} ${JSON.stringify(value)} is not a normalized relative path`, file);
  return value;
}

function inside(child: string, parent: string): boolean { return child === parent || child.startsWith(parent.endsWith(sep) ? parent : parent + sep); }

// ---------------------------------------------------------------------------
// Manifest

export function parseManifest(text: string, file: string): Manifest {
  let doc;
  try { doc = parseTomlSubset(text, file); } catch (error) { throw new PackageError('manifest', (error as Error).message.replace(`${file}:`, 'line '), file); }
  for (const table of doc.keys()) if (!['package', 'dependencies', 'sources', 'replace'].includes(table)) throw new PackageError('manifest', `unknown table [${table}]`, file);
  const pkg = doc.get('package'); if (!pkg) throw new PackageError('manifest', 'missing [package] table', file);
  for (const key of pkg.keys()) if (!['name', 'version', 'kind', 'source', 'modules', 'exports', 'entry'].includes(key)) throw new PackageError('manifest', `unknown package key ${key}`, file);
  const string = (key: string, required = true): string | undefined => {
    const value = pkg.get(key);
    if (value === undefined) { if (required) throw new PackageError('manifest', `missing package.${key}`, file); return undefined; }
    if (typeof value !== 'string') throw new PackageError('manifest', `package.${key} must be a string`, file);
    return value;
  };
  const list = (key: string): string[] => {
    const value: TomlValue | undefined = pkg.get(key);
    if (value === undefined) return [];
    if (!Array.isArray(value)) throw new PackageError('manifest', `package.${key} must be a string array`, file);
    return value;
  };
  const name = string('name')!;
  if (/^[a-z_][a-z0-9_]{0,63}$/.test(name)) {
    try { assertPortableName(name); } catch { throw new PackageError('manifest', `package name ${name} is reserved`, file); }
  } else if (!isModulePath(name)) throw new PackageError('manifest', `package name ${JSON.stringify(name)} must be a short name or a module path`, file);
  const version = string('version')!;
  if (!/^(0|[1-9][0-9]{0,8})\.(0|[1-9][0-9]{0,8})\.(0|[1-9][0-9]{0,8})$/.test(version)) throw new PackageError('manifest', `version ${JSON.stringify(version)} must be exact MAJOR.MINOR.PATCH`, file);
  const kind = string('kind')!;
  if (kind !== 'library' && kind !== 'contract') throw new PackageError('manifest', 'package.kind must be "library" or "contract"', file);
  const source = relPath(string('source')!, 'package.source', file);
  const modules = list('modules');
  if (!modules.length) throw new PackageError('manifest', 'package.modules must declare at least one module', file);
  const folded = new Map<string, string>();
  for (const module of modules) {
    if (!/^[A-Za-z_][A-Za-z0-9_]*(\/[A-Za-z_][A-Za-z0-9_]*)*$/.test(module)) {
      if (module.split('/').includes('..') || module.startsWith('/')) throw new PackageError('path-escape', `module path ${JSON.stringify(module)} escapes the source root`, file);
      throw new PackageError('manifest', `module path ${JSON.stringify(module)} must be '/'-separated identifiers`, file);
    }
    const key = fold(module), prior = folded.get(key);
    if (prior !== undefined) throw new PackageError(prior === module ? 'manifest' : 'path-collision', prior === module ? `duplicate module ${module}` : `module paths ${prior} and ${module} collide under case folding`, file);
    folded.set(key, module);
  }
  const exports = list('exports');
  for (const module of exports) if (!modules.includes(module)) throw new PackageError('manifest', `exported module ${module} is not declared in package.modules`, file);
  if (new Set(exports).size !== exports.length) throw new PackageError('manifest', 'duplicate exported module', file);
  const entry = string('entry', false);
  if (kind === 'contract' && (entry === undefined || !modules.includes(entry))) throw new PackageError('manifest', 'contract packages require package.entry naming a declared module', file);
  if (kind === 'library' && entry !== undefined) throw new PackageError('manifest', 'library packages are declaration-only and have no entry', file);
  const table = (title: string): Map<string, string> => {
    const out = new Map<string, string>();
    for (const [key, value] of doc.get(title) ?? []) {
      if (typeof value !== 'string') throw new PackageError('manifest', `[${title}] ${key} must be a string`, file);
      out.set(key, value);
    }
    return out;
  };
  const dependencies = table('dependencies');
  for (const [alias, target] of dependencies) {
    try { assertPortableName(alias); } catch { throw new PackageError('manifest', `dependency alias ${alias} is reserved or invalid`, file); }
    const req = classifyRequirement(target, file);
    if ((req.kind === 'path' ? req.name : req.module) === name) throw new PackageError('package-cycle', `package ${name} depends on itself`, file);
  }
  const sources = table('sources');
  for (const [pkgName, path] of sources) {
    if (isModulePath(pkgName)) {
      if (!isGitLocator(path)) throw new PackageError('manifest', `[sources] ${pkgName} must be an https or file locator`, file);
      assertGitLocator(path, file);
    } else {
      if (!/^[a-z_][a-z0-9_]{0,63}$/.test(pkgName)) throw new PackageError('manifest', `[sources] key ${pkgName} must be a package name`, file);
      relPath(path, `[sources] ${pkgName}`, file);
    }
  }
  const replace = table('replace');
  for (const [pkgName, path] of replace) {
    if (!isModulePath(pkgName)) throw new PackageError('manifest', `[replace] key ${pkgName} must be a module path`, file);
    if (isGitLocator(path)) assertGitLocator(path, file);
    else relPath(path, `[replace] ${pkgName}`, file);
  }
  return { name, version, kind, source, modules, exports, ...(entry !== undefined ? { entry } : {}), dependencies, sources, replace };
}

// ---------------------------------------------------------------------------
// Package scanning: one immutable snapshot of each package's declared files.

export function scanPackage(project: string, locator: string, isRoot: boolean, budget: { bytes: number; limit: number }): PackageInfo {
  const dir = locator === '.' ? project : join(project, ...locator.split('/'));
  let real: string;
  try { real = realpathSync(dir); } catch { throw new PackageError('manifest', `package directory ${locator} does not exist`, locator); }
  if (!inside(real, project)) throw new PackageError('symlink-escape', `package directory ${locator} resolves outside the root project`, locator);
  if (!isRoot && real === project) throw new PackageError('manifest', 'a dependency cannot be the root project', locator);
  // The resolved package root (after any in-project symlinks) names the package in diagnostics, lock and build graph.
  const root = relative(project, real).split(sep).join('/') || '.';
  const manifestFile = posix(root, MANIFEST_FILE);
  const readContained = (abs: string, display: string): Uint8Array => {
    let st;
    try { st = lstatSync(abs); } catch { throw new PackageError('missing-module', 'file not found', display); }
    if (st.isSymbolicLink()) {
      let target: string;
      try { target = realpathSync(abs); } catch { throw new PackageError('symlink-escape', 'dangling symlink', display); }
      if (!inside(target, real)) throw new PackageError('symlink-escape', 'symlink resolves outside the package root', display);
      if (!statSync(target).isFile()) throw new PackageError('manifest', 'symlinked directories and special files are not supported', display);
    } else if (!st.isFile()) throw new PackageError('manifest', 'expected a regular file', display);
    const data = readFileSync(abs);
    budget.bytes += data.length;
    if (budget.bytes > budget.limit) throw new PackageError('limit', `total package source exceeds ${budget.limit} bytes`, display);
    return Uint8Array.from(data);
  };
  const manifestBytes = readContained(join(real, MANIFEST_FILE), manifestFile);
  const manifest = parseManifest(decode(manifestBytes, manifestFile), manifestFile);
  const srcAbs = join(real, ...manifest.source.split('/'));
  let srcReal: string;
  try { srcReal = realpathSync(srcAbs); } catch { throw new PackageError('manifest', `source root ${manifest.source} does not exist`, manifestFile); }
  if (!inside(srcReal, real) || srcReal === real) throw new PackageError('symlink-escape', `source root ${manifest.source} must resolve to a subdirectory inside the package`, manifestFile);
  if (!statSync(srcReal).isDirectory()) throw new PackageError('manifest', `source root ${manifest.source} is not a directory`, manifestFile);
  // Walk the source root with exact on-disk names (case-insensitive file systems
  // cannot satisfy a differently cased declaration), rejecting undeclared files,
  // escaping symlinks and case/Unicode-folding collisions.
  const declared = new Map(manifest.modules.map(module => [`${module}.lotus`, module]));
  const found = new Map<string, string>(); const folded = new Map<string, string>(); let entries = 0;
  const walk = (abs: string, rel: string): void => {
    for (const name of readdirSync(abs).sort()) {
      if (++entries > MAX_WALK_ENTRIES) throw new PackageError('limit', `source root has more than ${MAX_WALK_ENTRIES} entries`, posix(root, manifest.source));
      const childRel = rel ? `${rel}/${name}` : name, childAbs = join(abs, name), display = posix(root, manifest.source, childRel);
      const key = fold(childRel), prior = folded.get(key);
      if (prior !== undefined) throw new PackageError('path-collision', `${prior} and ${childRel} collide under case/Unicode folding`, display);
      folded.set(key, childRel);
      const st = lstatSync(childAbs);
      if (st.isSymbolicLink()) {
        let target: string;
        try { target = realpathSync(childAbs); } catch { throw new PackageError('symlink-escape', 'dangling symlink', display); }
        if (!inside(target, real)) throw new PackageError('symlink-escape', 'symlink resolves outside the package root', display);
        if (!statSync(target).isFile()) throw new PackageError('manifest', 'symlinked directories are not supported', display);
      } else if (st.isDirectory()) { walk(childAbs, childRel); continue; }
      else if (!st.isFile()) throw new PackageError('manifest', 'unsupported file type', display);
      if (!declared.has(childRel)) throw new PackageError('undeclared-file', 'file is not a declared module of this package', display);
      found.set(childRel, childAbs);
    }
  };
  walk(srcReal, '');
  const files: PackageFile[] = [{ path: MANIFEST_FILE, content: manifestBytes, digest: tagged('package/file', bytes(manifestBytes)) }];
  for (const [rel, module] of declared) {
    const abs = found.get(rel), display = posix(root, manifest.source, rel);
    if (!abs) throw new PackageError('missing-module', `declared module ${module} has no file (names are case-sensitive)`, display);
    const content = readContained(abs, display);
    decode(content, display);
    files.push({ path: posix(manifest.source, rel), content, digest: tagged('package/file', bytes(content)) });
  }
  files.sort((a, b) => a.path < b.path ? -1 : a.path > b.path ? 1 : 0);
  const treeDigest = tagged('package/tree', concat(str(manifest.name), str(manifest.version), cs(files.length), ...files.map(f => concat(str(f.path), f.digest))));
  return { id: `${manifest.name}@${manifest.version}`, manifest, root, manifestFile, files, treeDigest, isRoot };
}

export type Workspace = { project: string; root: PackageInfo; packages: Map<string, PackageInfo>; lockText: string;
  /** Selected git packages by module path. Absent for a path-only graph so lock bytes stay schema 1. */ modules?: Map<string, PackageInfo> };

function needsDistributed(info: PackageInfo): boolean {
  if (info.manifest.replace.size > 0) return true;
  for (const spec of info.manifest.dependencies.values()) if (spec.includes('/')) return true;
  for (const [key, value] of info.manifest.sources) if (key.includes('/') || isGitLocator(value)) return true;
  for (const file of info.files) {
    if (!file.path.endsWith('.lotus')) continue;
    if (/(^|\n)[ \t]*import[ \t]+"/.test(decode(file.content, posix(info.root, file.path)))) return true;
  }
  return false;
}

function finishDistributed(project: string, root: PackageInfo, limits: PackageLimits, budget: { bytes: number; limit: number }, online?: FetchOptions): Workspace {
  const resolved = resolveDistributedSources(project, root, limits, budget, online);
  return { project, root, packages: resolved.packages, lockText: resolved.lockText, modules: resolved.modules };
}

export function resolveWorkspace(projectDir: string, limits: PackageLimits, online?: FetchOptions): Workspace {
  let project: string;
  try { project = realpathSync(projectDir); } catch { throw new PackageError('manifest', 'root project directory does not exist'); }
  const budget = { bytes: 0, limit: limits.maxSourceBytes };
  const root = scanPackage(project, '.', true, budget);
  const fresh = (): { bytes: number; limit: number } => ({ bytes: root.files.reduce((sum, file) => sum + file.content.length, 0), limit: limits.maxSourceBytes });
  if (needsDistributed(root)) return finishDistributed(project, root, limits, budget, online);
  const packages = new Map<string, PackageInfo>();
  const queue: { id: string; from: PackageInfo }[] = [...root.manifest.dependencies.values()].map(id => ({ id, from: root }));
  while (queue.length) {
    const { id, from } = queue.shift()!;
    if (id.includes('/')) return finishDistributed(project, root, limits, fresh(), online);
    const [name, version] = id.split('@') as [string, string];
    if (name === root.manifest.name) throw new PackageError('package-cycle', `${from.id} depends on the root package ${root.id}`, from.manifestFile);
    const prior = packages.get(name);
    if (prior) {
      if (prior.manifest.version !== version) throw new PackageError('version-conflict', `${from.id} requires ${id} but ${prior.id} is already in the graph`, from.manifestFile);
      continue;
    }
    // Locators come only from the root manifest; dependency [sources] are never inherited.
    const locator = root.manifest.sources.get(name);
    if (locator === undefined) throw new PackageError('manifest', `no [sources] locator for ${name} in the root manifest`, root.manifestFile);
    if (packages.size >= limits.maxPackages) throw new PackageError('limit', `package graph exceeds ${limits.maxPackages} packages`, from.manifestFile);
    const info = scanPackage(project, locator, false, budget);
    if (info.id !== id) throw new PackageError('version-conflict', `locator ${locator} contains ${info.id}, expected ${id}`, info.manifestFile);
    if (info.manifest.kind !== 'library') throw new PackageError('declaration-only', `dependency ${id} must be a library package`, info.manifestFile);
    packages.set(name, info);
    for (const dep of info.manifest.dependencies.values()) queue.push({ id: dep, from: info });
  }
  for (const name of root.manifest.sources.keys()) if (!packages.has(name)) throw new PackageError('manifest', `[sources] locator ${name} is not used by the dependency graph`, root.manifestFile);
  // Package-level dependency cycles (module cycles are diagnosed separately with spans).
  const state = new Map<string, 'active' | 'done'>();
  const visit = (pkg: PackageInfo, chain: string[]): void => {
    if (state.get(pkg.id) === 'done') return;
    if (state.get(pkg.id) === 'active') throw new PackageError('package-cycle', `package dependency cycle: ${[...chain, pkg.id].join(' -> ')}`, pkg.manifestFile);
    state.set(pkg.id, 'active');
    for (const dep of pkg.manifest.dependencies.values()) visit(packages.get(dep.split('@')[0]!)!, [...chain, pkg.id]);
    state.set(pkg.id, 'done');
  };
  for (const pkg of packages.values()) visit(pkg, []);
  if ([root, ...packages.values()].some(needsDistributed)) return finishDistributed(project, root, limits, fresh(), online);
  return { project, root, packages, lockText: renderLock(root, packages) };
}

function renderLock(root: PackageInfo, packages: Map<string, PackageInfo>): string {
  const lock: LockFile = {
    schema: LOCK_SCHEMA,
    root: { name: root.manifest.name, version: root.manifest.version, dependencies: sorted(root.manifest.dependencies) },
    packages: [...packages.values()].map(pkg => ({ name: pkg.manifest.name, version: pkg.manifest.version,
      locator: { kind: 'path' as const, path: root.manifest.sources.get(pkg.manifest.name)! }, root: pkg.root,
      dependencies: sorted(pkg.manifest.dependencies), files: pkg.files.map(f => ({ path: f.path, digest: hex(f.digest) })), treeDigest: hex(pkg.treeDigest) })).sort(byName),
  };
  return JSON.stringify(lock, null, 2) + '\n';
}

/** Compute the canonical lock text from local files only (no network). */
export function generateLock(projectDir: string, limits: Partial<PackageLimits> = {}): string {
  return resolveWorkspace(projectDir, { ...DEFAULT_PACKAGE_LIMITS, ...limits }).lockText;
}
/** Rewrite `lotus.lock` from local files. Returns the written text. */
export function updateLock(projectDir: string, limits: Partial<PackageLimits> = {}): string {
  const text = generateLock(projectDir, limits);
  writeFileSync(join(projectDir, LOCK_FILE), text);
  return text;
}

function verifyLock(ws: Workspace): Uint8Array {
  let actual: Uint8Array;
  try { actual = Uint8Array.from(readFileSync(join(ws.project, LOCK_FILE))); }
  catch { throw new PackageError('lock-missing', `missing ${LOCK_FILE}; run lotus-v2-package-lock`, LOCK_FILE); }
  const text = decode(actual, LOCK_FILE);
  if (text !== ws.lockText) {
    // Explain the first difference: a changed file digest is the common case.
    let lock: LockFile | undefined;
    try { lock = JSON.parse(text) as LockFile; } catch { /* reported below */ }
    if (lock && Array.isArray(lock.packages)) for (const entry of lock.packages) {
      const pkg = ws.packages.get(entry?.name);
      // Git lock versions are selected tags (`vX.Y.Z`) or commits, not the manifest's MAJOR.MINOR.PATCH.
      if (!pkg || !Array.isArray(entry.files)) continue;
      for (const file of pkg.files) {
        const pinned = entry.files.find(x => x?.path === file.path);
        if (pinned && pinned.digest !== hex(file.digest))
          throw new PackageError('lock-mismatch', `source digest ${hex(file.digest)} of ${pkg.id} differs from locked ${String(pinned.digest)}; review the change and run lotus-v2-package-lock`, posix(pkg.root, file.path));
      }
    }
    throw new PackageError('lock-stale', `${LOCK_FILE} does not match the manifests and local package files; run lotus-v2-package-lock`, LOCK_FILE);
  }
  return tagged('package/lock', bytes(actual));
}

// ---------------------------------------------------------------------------
// Module graph, import resolution and linking.

function signature(helper: Helper): string { return `${helper.name}(${helper.params.map(p => `${p.name}: ${p.type}`).join(', ')}): ${helper.result}`; }

export async function compilePackage(projectDir: string, options: PackageCompileOptions): Promise<PackageBuild> {
  if (typeof options?.contract !== 'string' || !options.bindings || typeof options.bindings !== 'object') throw new Error('compile options require contract and bindings');
  const limits = { ...DEFAULT_PACKAGE_LIMITS, ...(options.limits ?? {}) };
  const ws = resolveWorkspace(projectDir, limits);
  const { root } = ws;
  if (root.manifest.kind !== 'contract' || !root.manifest.entry) throw new PackageError('declaration-only', 'the root package must be a contract package with an entry module', root.manifestFile);
  const lockDigest = verifyLock(ws);
  const byId = new Map<string, PackageInfo>([[root.id, root], ...[...ws.packages.values()].map(pkg => [pkg.id, pkg] as const)]);
  const modules = new Map<string, ModuleNode>(); const parses: Record<string, number> = {};
  const sources = new SourceManager();
  let bindings = 0;
  const load = (pkg: PackageInfo, path: string, from?: { file: string; span: Span }): ModuleNode => {
    const id = `${pkg.id}/${path}`;
    const old = modules.get(id); if (old) return old;
    if (modules.size >= limits.maxModules) throw new PackageError('limit', `module graph exceeds ${limits.maxModules} modules`, from?.file, from?.span);
    const rel = posix(pkg.manifest.source, `${path}.lotus`), file = posix(pkg.root, rel);
    const data = pkg.files.find(f => f.path === rel)!;
    const isEntry = pkg.isRoot && path === pkg.manifest.entry;
    let program: Program;
    try { program = parseModuleSource(decode(data.content, file), isEntry, file, sources); }
    catch (error) { if (error instanceof CompileError) throw error; throw new PackageError('parse', (error as Error).message, file); }
    parses[id] = (parses[id] ?? 0) + 1;
    const node: ModuleNode = { id, pkg, path, file, digest: data.digest, program, isEntry, imports: [] };
    modules.set(id, node);
    return node;
  };
  const entry = load(root, root.manifest.entry);
  // Depth-first import resolution with an explicit stack: cycles report every hop.
  const done = new Set<string>();
  const visit = (node: ModuleNode, stack: { node: ModuleNode; decl: ImportDecl }[]): void => {
    if (done.has(node.id)) return;
    if (stack.length > limits.maxImportDepth) { const last = stack.at(-1)!; throw new PackageError('limit', `import depth exceeds ${limits.maxImportDepth}`, last.node.file, last.decl.span); }
    const active = stack.map(x => x.node.id);
    for (const decl of node.program.imports) {
      bindings += decl.items?.length ?? 1;
      if (bindings > limits.maxImportBindings) throw new PackageError('limit', `import bindings exceed ${limits.maxImportBindings}`, node.file, decl.span);
      let pkg: PackageInfo;
      if (decl.target === 'package') pkg = node.pkg;
      else if (ws.modules && decl.target.includes('/')) {
        const req = classifyRequirement(decl.target, node.file);
        const selected = req.kind === 'module' ? ws.modules.get(req.module) : undefined;
        if (!selected) throw new PackageError('unknown-alias', `${decl.target} is not a resolved module of ${node.pkg.id}`, node.file, decl.targetSpan);
        pkg = selected;
      } else {
        const dep = node.pkg.manifest.dependencies.get(decl.target);
        if (!dep) throw new PackageError('unknown-alias', `${decl.target} is not a dependency alias of ${node.pkg.id}`, node.file, decl.targetSpan);
        if (ws.modules) {
          const req = classifyRequirement(dep, node.pkg.manifestFile);
          const selected = req.kind === 'module' ? ws.modules.get(req.module) : ws.packages.get(req.name);
          if (!selected) throw new PackageError('unknown-alias', `${decl.target} does not resolve in ${node.pkg.id}`, node.file, decl.targetSpan);
          pkg = selected;
        } else pkg = byId.get(dep)!;
      }
      const path = decl.path.join('/');
      if (!pkg.manifest.modules.includes(path)) throw new PackageError('missing-module', `module ${decl.target}::${decl.path.join('::')} does not exist in ${pkg.id}`, node.file, decl.pathSpan);
      if (pkg !== node.pkg && !pkg.manifest.exports.includes(path)) throw new PackageError('not-exported', `module ${path} is not exported by ${pkg.id}`, node.file, decl.pathSpan);
      const target = load(pkg, path, { file: node.file, span: decl.span });
      const at = active.indexOf(target.id);
      if (target === node || at >= 0) {
        const hops = [...stack.slice(at < 0 ? stack.length : at), { node, decl }];
        throw new PackageError('import-cycle', `import cycle: ${hops.map(h => `${h.node.id} (${h.node.file}:${h.decl.span.start}..${h.decl.span.end})`).join(' -> ')} -> ${target.id}`, node.file, decl.span);
      }
      node.imports.push({ decl, target });
      visit(target, [...stack, { node, decl }]);
    }
    done.add(node.id);
  };
  visit(entry, []);
  // One scheduler job per module identity; each job links its module after its imports.
  const trace: SchedulerEvent[] = [];
  const scheduler = new PromiseScheduler<void>(event => trace.push(event), { maxJobs: limits.maxModules });
  const helpers = new Map<string, Helper>(); const contracts = new Map<string, Contract>();
  const owners = new Map<string, { pkg: PackageInfo; moduleId: string; kind: Contract['kind'] }>();
  const interfaces = new Map<string, { digest: Uint8Array; exports: { name: string; signature: string; digest: string }[] }>();
  for (const node of modules.values())
    scheduler.register(`module:${node.id}`, [...new Set(node.imports.map(x => `module:${x.target.id}`))], () => link(node));
  const link = (node: ModuleNode): void => {
    type Entry = { kind: 'helper'; canonical: string } | { kind: 'module'; target: ModuleNode } | { kind: 'contract'; programName: string; owner: ModuleNode };
    const scope = new Map<string, Entry>();
    const declare = (name: string, entryValue: Entry, span: Span): void => {
      if (BUILTINS.has(name)) throw new PackageError('duplicate-name', `${name} shadows a builtin`, node.file, span);
      if (scope.has(name)) throw new PackageError('duplicate-name', `ambiguous local name ${name} (already declared or imported in this module)`, node.file, span);
      scope.set(name, entryValue);
    };
    const canonical = (owner: ModuleNode, name: string): string => `${owner.id}::${name}`;
    // Helpers and contracts share a module namespace. Visibility matches helpers: private to the module,
    // package within the package, export only from another package (and only via an exported module).
    const lookup = (owner: ModuleNode, name: string, span: Span): { kind: 'helper'; canonical: string } | { kind: 'contract'; programName: string } => {
      const helper = owner.program.helpers.get(name);
      const contract = owner.program.contracts.get(name);
      if (helper && contract) throw new PackageError('duplicate-name', `${owner.id} declares both a function and a contract named ${name}`, node.file, span);
      if (!helper && !contract) throw new PackageError('missing-symbol', `${owner.id} has no function or contract ${name}`, node.file, span);
      const visibility = helper ? helper.visibility : contract!.visibility;
      if (owner !== node) {
        if (visibility === 'private') throw new PackageError('visibility', `${name} is private to module ${owner.id}`, node.file, span);
        if (owner.pkg !== node.pkg && visibility !== 'export') throw new PackageError('visibility', `${name} is package-scoped in ${owner.pkg.id}`, node.file, span);
      }
      return helper ? { kind: 'helper', canonical: canonical(owner, helper.name) } : { kind: 'contract', programName: contract!.name };
    };
    for (const helper of node.program.helpers.values()) declare(helper.name, { kind: 'helper', canonical: canonical(node, helper.name) }, helper.span);
    for (const contract of node.program.contracts.values()) declare(contract.name, { kind: 'contract', programName: contract.name, owner: node }, contract.span);
    for (const { decl, target } of node.imports) {
      if (decl.moduleAlias) declare(decl.moduleAlias.name, { kind: 'module', target }, decl.moduleAlias.span);
      for (const item of decl.items ?? []) {
        const symbol = lookup(target, item.name, item.span);
        if (symbol.kind === 'helper') declare(item.local, { kind: 'helper', canonical: symbol.canonical }, item.span);
        else declare(item.local, { kind: 'contract', programName: symbol.programName, owner: target }, item.span);
      }
    }
    const span = (s: Span): Span => ({ start: s.start, end: s.end, module: node.id, ...(s.file !== undefined ? { file: s.file } : {}) });
    // Rewrite commitment arguments to the contract's declared name. The compiler then pins that bytecode root.
    const rewriteContractRef = (text: string, at: Span, expectMethod: boolean): string => {
      let owner = node, body = text;
      if (text.includes('::')) {
        const parts = text.split('::');
        if (parts.length !== 2) throw new PackageError('missing-symbol', `invalid contract reference ${text}`, node.file, at);
        const alias = parts[0]!, rest = parts[1]!;
        const bound = scope.get(alias);
        if (bound?.kind !== 'module') throw new PackageError('missing-symbol', `${alias} is not an imported module alias`, node.file, at);
        owner = bound.target; body = rest;
      }
      const dot = body.split('.');
      if (dot.length > 2 || !dot[0]) throw new PackageError('missing-symbol', `invalid contract reference ${text}`, node.file, at);
      const method = dot[1];
      if (expectMethod !== (method !== undefined)) throw new PackageError('missing-symbol', expectMethod ? 'leaf_hash requires Contract.method' : `${text} must name a contract`, node.file, at);
      let programName: string, home: ModuleNode;
      if (text.includes('::')) {
        const symbol = lookup(owner, dot[0]!, at);
        if (symbol.kind !== 'contract') throw new PackageError('missing-symbol', `${dot[0]} is not a contract`, node.file, at);
        programName = symbol.programName; home = owner;
      } else {
        const bound = scope.get(dot[0]!);
        if (bound?.kind !== 'contract') throw new PackageError('missing-symbol', `${dot[0]} is not a contract in scope`, node.file, at);
        programName = bound.programName; home = bound.owner;
      }
      const contract = home.program.contracts.get(programName);
      if (method && !contract?.methods.some(m => m.name === method)) throw new PackageError('missing-symbol', `${programName} has no method ${method}`, node.file, at);
      return method ? `${programName}.${method}` : programName;
    };
    const expr = (e: Expr): Expr => {
      let value = e.value, args = e.args;
      if (e.kind === 'call' && value !== undefined && COMMITMENT_BUILTINS.has(value)) {
        const arg = args?.[0];
        if (args?.length === 1 && arg?.kind === 'name' && arg.value !== undefined)
          args = [{ ...arg, span: span(arg.span), value: rewriteContractRef(arg.value, arg.span, value === 'leaf_hash') }];
        else if (args) args = args.map(expr);
      } else if (e.kind === 'call' && value !== undefined && !BUILTINS.has(value) && !value.includes('.')) {
        if (value.includes('::')) {
          const [alias, member] = value.split('::') as [string, string];
          const bound = scope.get(alias);
          if (bound?.kind !== 'module') throw new PackageError('missing-symbol', `${alias} is not an imported module alias`, node.file, e.span);
          const symbol = lookup(bound.target, member, e.span);
          if (symbol.kind !== 'helper') throw new PackageError('missing-symbol', `${member} is not a function`, node.file, e.span);
          value = symbol.canonical;
        } else {
          const bound = scope.get(value);
          if (bound?.kind === 'contract') throw new PackageError('missing-symbol', `${value} is a contract, not a function`, node.file, e.span);
          if (bound?.kind !== 'helper') throw new PackageError('missing-symbol', `unknown function ${value}`, node.file, e.span);
          value = bound.canonical;
        }
        if (args) args = args.map(expr);
      } else if (args) args = args.map(expr);
      return { ...e, span: span(e.span), ...(value !== undefined ? { value } : {}),
        ...(args ? { args } : {}), ...(e.left ? { left: expr(e.left) } : {}), ...(e.right ? { right: expr(e.right) } : {}) };
    };
    const stmt = (s: Stmt): Stmt => ({ ...s, span: span(s.span), ...(s.expr ? { expr: expr(s.expr) } : {}),
      ...(s.then ? { then: s.then.map(stmt) } : {}), ...(s.otherwise ? { otherwise: s.otherwise.map(stmt) } : {}) });
    const helperStmt = (s: HelperStmt): HelperStmt => s.kind === 'let'
      ? { ...s, span: span(s.span), nameSpan: span(s.nameSpan), expr: expr(s.expr) }
      : s.kind === 'if'
        ? { ...s, span: span(s.span), expr: expr(s.expr), then: s.then.map(helperStmt), otherwise: s.otherwise.map(helperStmt) }
        : { ...s, span: span(s.span), expr: expr(s.expr) };
    const param = (p: Param): Param => ({ ...p, span: span(p.span) });
    for (const helper of node.program.helpers.values()) {
      const name = canonical(node, helper.name);
      helpers.set(name, { ...helper, name, params: helper.params.map(param), body: helper.body.map(helperStmt), span: span(helper.span) });
    }
    for (const contract of node.program.contracts.values()) {
      if (contracts.has(contract.name)) throw new PackageError('duplicate-name', `contract ${contract.name} is already declared in ${owners.get(contract.name)!.moduleId}`, node.file, contract.span);
      const linked = { ...contract, params: contract.params.map(param), span: span(contract.span),
        methods: contract.methods.map((m: Method) => ({ ...m, params: m.params.map(param), body: m.body.map(stmt), span: span(m.span) })) };
      owners.set(contract.name, { pkg: node.pkg, moduleId: node.id, kind: contract.kind });
      contracts.set(contract.name, linked);
    }
    // Stable interface: exported helper signatures, then exported contract/token signatures.
    // Helper declaration bytes stay exactly as before so helper-only modules keep their digest.
    const helperExports = [...node.program.helpers.values()].filter(h => h.visibility === 'export').sort(byName).map(h => {
      const digest = tagged('package/declaration', concat(str(h.name), cs(h.params.length), ...h.params.map(p => concat(str(p.name), str(p.type))), str(h.result)));
      return { name: h.name, signature: signature(h), digest };
    });
    const contractExports = [...node.program.contracts.values()].filter(c => c.visibility === 'export').sort(byName).map(c => {
      const head = c.params.length ? `${c.kind} ${c.name}<${c.params.map(p => `${p.name}: ${p.type}`).join(', ')}>` : `${c.kind} ${c.name}`;
      const methods = c.methods.map(m => `${m.name}(${m.params.map(p => `${p.name}: ${p.type}`).join(', ')})`).join('; ');
      const digest = tagged('package/contract', concat(str(c.kind), str(c.name), cs(c.params.length), ...c.params.map(p => concat(str(p.name), str(p.type))),
        cs(c.methods.length), ...c.methods.flatMap(m => [str(m.name), cs(m.params.length), ...m.params.map(p => concat(str(p.name), str(p.type)))])));
      return { name: c.name, signature: `${head} { ${methods} }`, digest };
    });
    const exported = [...helperExports, ...contractExports];
    interfaces.set(node.id, { digest: tagged('package/interface', concat(str(node.pkg.manifest.name), str(node.path), cs(exported.length), ...exported.map(x => x.digest))),
      exports: exported.map(x => ({ name: x.name, signature: x.signature, digest: hex(x.digest) })) });
  };
  await scheduler.run(`module:${entry.id}`);
  const { artifact, roots } = await compileLinkedProgramAsync({ helpers, contracts, imports: [] }, options, event => trace.push(event), sources);
  const links: LinkedContract[] = roots.filter(item => item.name !== artifact.contract && owners.get(item.name)?.pkg.id !== root.id).map(item => {
    const owner = owners.get(item.name)!;
    return { name: item.name, kind: owner.kind, package: owner.pkg.id, module: owner.moduleId, packageDigest: hex(owner.pkg.treeDigest), root: item.root, methods: item.methods };
  }).sort(byName);
  const graph: Omit<BuildGraph, 'digest'> = {
    schema: BUILD_GRAPH_SCHEMA,
    compiler: { name: COMPILER_NAME, version: COMPILER_VERSION, profile: options.optimize === false ? 'unoptimized' : 'optimized' },
    target: TARGET,
    root: { package: root.id, module: entry.id },
    lockDigest: hex(lockDigest),
    packages: [...byId.values()].map(pkg => ({ id: pkg.id, name: pkg.manifest.name, version: pkg.selectedVersion ?? pkg.manifest.version, root: pkg.root, treeDigest: hex(pkg.treeDigest),
      dependencies: graphDependencies(pkg, ws) })).sort((a, b) => a.id < b.id ? -1 : 1),
    modules: [...modules.values()].map(node => ({ id: node.id, package: node.pkg.id, path: node.path, file: node.file, sourceDigest: hex(node.digest),
      interfaceDigest: hex(interfaces.get(node.id)!.digest), exports: interfaces.get(node.id)!.exports,
      imports: [...new Set(node.imports.map(x => x.target.id))].sort() })).sort((a, b) => a.id < b.id ? -1 : 1),
  };
  const build: BuildGraph = { ...graph, digest: hex(tagged('build-graph', utf8(JSON.stringify(graph)))) };
  return { artifact: links.length ? { ...artifact, links, build } : { ...artifact, build }, trace, parses };
}
