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
import {
  DEFAULT_COMPILER_EDITION,
  DEFAULT_OPTIMIZER_VERSION,
  SUPPORTED_COMPILER_EDITIONS,
  SUPPORTED_OPTIMIZER_VERSIONS,
  compileContract,
  compileLinkedProgramAsync,
  isSupportedCompilerEdition,
  isSupportedOptimizerVersion,
  parseModuleSource,
  resolveCompilerEdition,
  resolveOptimizerVersion,
  type BoundValue,
  type CompileOptions,
  type CompilerEdition,
  type Contract,
  type ContractArtifact,
  type Expr,
  type Helper,
  type HelperStmt,
  type ImportDecl,
  type LanguageVersion,
  type LinkedContract,
  type Method,
  type OptimizerVersion,
  type Param,
  type Program,
  type SchedulerEvent,
  type Stmt,
} from './generic.js';
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
  'instance' | 'root-cycle' | 'visibility' | 'duplicate-name' | 'import-cycle' | 'declaration-only' | 'limit' | 'branch' | 'unfetched' | 'locator' | 'fetch';

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
  instance: 'E0930', 'root-cycle': 'E0931',
  branch: 'E0921', unfetched: 'E0922', locator: 'E0923', fetch: 'E0924',
};
/** CLI view of a package error. The library still throws `PackageError` with its own code. */
export function packageCompileError(error: PackageError, sources = new SourceManager()): CompileError {
  const primary = error.file ? { file: error.file, ...(error.span ? { span: error.span } : {}) } : undefined;
  return new CompileError([diagnostic(PACKAGE_DIAGNOSTIC[error.code], error.detail, primary)], sources);
}

export type Manifest = { name: string; version: string; kind: 'library' | 'contract'; source: string; modules: string[]; exports: string[]; entry?: string;
  edition?: CompilerEdition; optimizer?: OptimizerVersion;
  /** alias -> `name@version` or `module@selector` */ dependencies: Map<string, string>;
  /** Root-only locators. Short names are project-relative paths; other hosts are git URLs. */ sources: Map<string, string>;
  /** Root-only module-path replacements (relative path or git locator). Never inherited. */ replace: Map<string, string> };
export type PackageFile = { path: string; digest: Uint8Array; content: Uint8Array };
export type PackageInfo = { id: string; manifest: Manifest; root: string; manifestFile: string; files: PackageFile[]; treeDigest: Uint8Array; isRoot: boolean;
  /** Git/replace packages record the selected tag (`vX.Y.Z`) or commit. Path packages omit it. */ selectedVersion?: string };
type ModuleNode = { id: string; pkg: PackageInfo; path: string; file: string; digest: Uint8Array; program: Program; isEntry: boolean; imports: { decl: ImportDecl; target: ModuleNode }[] };
type LockPackage = { name: string; version: string; locator: { kind: 'path'; path: string }; root: string; dependencies: Record<string, string>; files: { path: string; digest: string }[]; treeDigest: string };
export type LockFile = { schema: typeof LOCK_SCHEMA; root: { name: string; version: string; edition?: CompilerEdition; optimizer?: OptimizerVersion; dependencies: Record<string, string> }; packages: LockPackage[] };

export type BuildGraph = {
  schema: typeof BUILD_GRAPH_SCHEMA;
  interfaceVersion?: 'lotus-v2/module-interface/lc1';
  instances?: { name: string; template: string; bindings: ContractArtifact['bindings']; root: string }[];
  compiler: { name: string; version: string; profile: 'optimized' | 'unoptimized'; edition?: CompilerEdition; optimizerVersion?: OptimizerVersion };
  target: string;
  root: { package: string; module: string };
  lockDigest: string;
  packages: { id: string; name: string; version: string; root: string; treeDigest: string; dependencies: Record<string, string> }[];
  modules: { id: string; package: string; path: string; file: string; sourceDigest: string; interfaceDigest: string;
    exports: { name: string; signature: string; digest: string }[]; imports: string[] }[];
  digest: string;
};
/** Explicit compile-time references, never state reads or deployment actions. */
export type ProgramBinding = BoundValue | { root: string } | { leaf: string };
export type ProgramInstance = { template: string; bindings: Record<string, ProgramBinding> };
export type PackageCompileOptions = Omit<CompileOptions, 'bindings'> & {
  bindings: Record<string, Record<string, ProgramBinding>>;
  /** LC1 only. Templates resolve in the entry module's import namespace. */
  instances?: Record<string, ProgramInstance>;
  limits?: Partial<PackageLimits>;
};
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
  for (const table of doc.keys()) if (!['package', 'build', 'dependencies', 'sources', 'replace'].includes(table)) throw new PackageError('manifest', `unknown table [${table}]`, file);
  const pkg = doc.get('package'); if (!pkg) throw new PackageError('manifest', 'missing [package] table', file);
  for (const key of pkg.keys()) if (!['name', 'version', 'kind', 'source', 'modules', 'exports', 'entry', 'edition', 'optimizer', 'optimizer_version'].includes(key)) throw new PackageError('manifest', `unknown package key ${key}`, file);
  const buildTable = doc.get('build');
  if (buildTable) {
    for (const key of buildTable.keys()) if (!['edition', 'optimizer', 'optimizer_version'].includes(key)) throw new PackageError('manifest', `unknown build key ${key}`, file);
  }
  const string = (key: string, required = true): string | undefined => {
    const value = pkg.get(key);
    if (value === undefined) { if (required) throw new PackageError('manifest', `missing package.${key}`, file); return undefined; }
    if (typeof value !== 'string') throw new PackageError('manifest', `package.${key} must be a string`, file);
    return value;
  };
  const buildString = (key: string): string | undefined => {
    const value = buildTable?.get(key);
    if (value === undefined) return undefined;
    if (typeof value !== 'string') throw new PackageError('manifest', `build.${key} must be a string`, file);
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
  const pkgEdition = string('edition', false), buildEdition = buildString('edition');
  if (pkgEdition !== undefined && buildEdition !== undefined && pkgEdition !== buildEdition) {
    throw new PackageError('manifest', `conflicting edition in [package] (${JSON.stringify(pkgEdition)}) and [build] (${JSON.stringify(buildEdition)})`, file);
  }
  const rawEdition = pkgEdition ?? buildEdition;
  if (rawEdition !== undefined && !isSupportedCompilerEdition(rawEdition)) {
    throw new PackageError('manifest', `unsupported compiler edition ${JSON.stringify(rawEdition)}; expected one of: ${SUPPORTED_COMPILER_EDITIONS.join(', ')}`, file);
  }
  const pkgOpt = string('optimizer', false), pkgOptVer = string('optimizer_version', false);
  const buildOpt = buildString('optimizer'), buildOptVer = buildString('optimizer_version');
  const optCandidates = [pkgOpt, pkgOptVer, buildOpt, buildOptVer].filter((x): x is string => x !== undefined);
  if (new Set(optCandidates).size > 1) {
    throw new PackageError('manifest', `conflicting optimizer version settings in manifest: ${optCandidates.map(x => JSON.stringify(x)).join(', ')}`, file);
  }
  const rawOptimizer = optCandidates[0];
  if (rawOptimizer !== undefined && !isSupportedOptimizerVersion(rawOptimizer)) {
    throw new PackageError('manifest', `unsupported optimizer version ${JSON.stringify(rawOptimizer)}; expected one of: ${SUPPORTED_OPTIMIZER_VERSIONS.join(', ')}`, file);
  }
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
  return { name, version, kind, source, modules, exports, ...(entry !== undefined ? { entry } : {}),
    ...(rawEdition !== undefined ? { edition: rawEdition } : {}),
    ...(rawOptimizer !== undefined ? { optimizer: rawOptimizer } : {}),
    dependencies, sources, replace };
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
    root: {
      name: root.manifest.name,
      version: root.manifest.version,
      ...(root.manifest.edition !== undefined ? { edition: root.manifest.edition } : {}),
      ...(root.manifest.optimizer !== undefined ? { optimizer: root.manifest.optimizer } : {}),
      dependencies: sorted(root.manifest.dependencies),
    },
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
    if (lock?.root) {
      if (lock.root.edition !== ws.root.manifest.edition) {
        throw new PackageError('lock-mismatch', `manifest edition ${JSON.stringify(ws.root.manifest.edition)} differs from locked ${JSON.stringify(lock.root.edition)}; run lotus-v2-package-lock`, LOCK_FILE);
      }
      if (lock.root.optimizer !== ws.root.manifest.optimizer) {
        throw new PackageError('lock-mismatch', `manifest optimizer ${JSON.stringify(ws.root.manifest.optimizer)} differs from locked ${JSON.stringify(lock.root.optimizer)}; run lotus-v2-package-lock`, LOCK_FILE);
      }
    }
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

/** Validate explicit bindings and the complete root DAG before emitting any program. */
function bindInstances(contracts: Map<string, Contract>, templates: Map<string, { contract: Contract; owner: ModuleNode }>,
  owners: Map<string, { pkg: PackageInfo; moduleId: string; kind: Contract['kind'] }>, resolve: (name: string) => string, options: PackageCompileOptions, linkedHelpersForBindings: Map<string, Helper>) {
  const fail = (message: string): never => { throw new PackageError('instance', message); };
  const instances = options.instances ?? {};
  if (!instances || typeof instances !== 'object' || Array.isArray(instances)) fail('instances must be a named map');
  const inputs: Record<string, Record<string, ProgramBinding>> = { ...options.bindings };
  const templateNames = new Map<string, string>();
  const rewrite = (e: Expr, from: string, to: string): Expr => ({ ...e,
    ...(e.kind === 'name' && (e.value === from || e.value?.startsWith(from + '.')) ? { value: to + e.value!.slice(from.length) } : {}),
    ...(e.args ? { args: e.args.map(a => rewrite(a, from, to)) } : {}),
    ...(e.left ? { left: rewrite(e.left, from, to) } : {}), ...(e.right ? { right: rewrite(e.right, from, to) } : {}) });
  const statements = (body: Stmt[], from: string, to: string): Stmt[] => body.map(s => ({ ...s,
    ...(s.expr ? { expr: rewrite(s.expr, from, to) } : {}), ...(s.then ? { then: statements(s.then, from, to) } : {}),
    ...(s.otherwise ? { otherwise: statements(s.otherwise, from, to) } : {}) }));
  for (const [name, instance] of Object.entries(instances)) {
    try { assertPortableName(name); } catch { fail(`invalid instance name ${name}`); }
    if (contracts.has(name) || Object.hasOwn(options.bindings, name)) fail(`duplicate instance binding ${name}`);
    if (!instance || typeof instance !== 'object' || Object.keys(instance).some(k => !['template', 'bindings'].includes(k)) || typeof instance.template !== 'string') fail(`invalid instance ${name}; expected template and bindings only (state/effect lowering is unsupported)`);
    const key = resolve(instance.template), template = templates.get(key);
    if (!template) fail(`unresolved template ${instance.template}`);
    const c = template!.contract;
    templateNames.set(name, c.name);
    contracts.set(name, { ...c, name, methods: c.methods.map(m => ({ ...m, body: statements(m.body, c.name, name) })) });
    owners.set(name, { pkg: template!.owner.pkg, moduleId: template!.owner.id, kind: c.kind });
    inputs[name] = instance.bindings;
  }
  // Local contracts use their ordinary names; canonical self references must follow them.
  for (const [name, c] of contracts) {
    const owner = owners.get(name)!;
    const canonical = `${owner.moduleId}::${name}`;
    if (!templateNames.has(name)) templateNames.set(name, canonical);
    if (!Object.hasOwn(instances, name)) contracts.set(name, { ...c, methods: c.methods.map(m => ({ ...m, body: statements(m.body, canonical, name) })) });
  }
  const references = new Map<string, [string, { name: string; method?: string }][]>();
  const bindings: CompileOptions['bindings'] = {};
  const deps = new Map<string, Set<string>>();
  for (const [name, c] of contracts) {
    const input = inputs[name] ?? (c.params.length === 0 ? {} : undefined);
    if (!input || typeof input !== 'object' || Array.isArray(input)) fail(`missing binding map for ${name}`);
    if (Object.keys(input!).some(p => !c.params.some(x => x.name === p))) fail(`surplus constructor binding for ${name}`);
    const refs: [string, { name: string; method?: string }][] = [], edges = new Set<string>();
    const values: Record<string, BoundValue> = {};
    for (const p of c.params) {
      if (!Object.hasOwn(input!, p.name)) fail(`missing constructor binding ${name}.${p.name}`);
      const value = input![p.name]!;
      if (value !== null && typeof value === 'object') {
        const keys = Object.keys(value);
        if (keys.length !== 1 || !['root', 'leaf'].includes(keys[0]!)) fail(`unsupported binding ${name}.${p.name}; expected a literal, root or leaf reference`);
        const leaf = keys[0] === 'leaf', text = leaf ? (value as { leaf: string }).leaf : (value as { root: string }).root;
        if (typeof text !== 'string') fail(`invalid reference ${name}.${p.name}`);
        const parts = text.split('.'), target = contracts.get(parts[0]!);
        if (!target || parts.length !== (leaf ? 2 : 1)) fail(`unresolved bound program reference ${text}`);
        if (leaf && !target!.methods.some(m => m.name === parts[1])) fail(`missing entry ${text}`);
        const valid = leaf ? ['MethodLeafHash', 'Bytes32'] : target!.kind === 'token' ? ['TokenId', 'Bytes32'] : ['ContractRootHash', 'Bytes32'];
        if (!valid.includes(p.type)) fail(`reference type mismatch for ${name}.${p.name}: ${p.type}`);
        refs.push([p.name, { name: parts[0]!, ...(leaf ? { method: parts[1]! } : {}) }]); edges.add(parts[0]!);
      } else values[p.name] = value as BoundValue;
    }
    bindings[name] = values; references.set(name, refs); deps.set(name, edges);
  }
  for (const name of Object.keys(options.bindings)) if (!contracts.has(name)) fail(`binding names unbound template ${name}`);
  // Include source/helper root dependencies, so constructor edges cannot hide mixed cycles.
  let scanningName = '';
  const scanExpr = (e: Expr, edges: Set<string>, seen: Set<string>): void => {
    if (e.kind === 'call') {
      if (COMMITMENT_BUILTINS.has(e.value!) && e.args?.[0]?.kind === 'name') {
        const text = e.args[0].value!;
        const reference = e.value === 'leaf_hash' ? text.slice(0, text.lastIndexOf('.')) : text;
        const target = reference === templateNames.get(scanningName) ? scanningName : reference;
        if (!contracts.has(target)) fail(`root reference ${target} requires an explicit bound instance`);
        edges.add(target);
      } else if (!seen.has(e.value!)) {
        seen.add(e.value!);
        const h = linkedHelpersForBindings?.get(e.value!);
        if (h) scanBody(h.body, edges, seen);
      }
    }
    for (const arg of e.args ?? []) scanExpr(arg, edges, seen);
    if (e.left) scanExpr(e.left, edges, seen); if (e.right) scanExpr(e.right, edges, seen);
  };
  const scanBody = (body: (Stmt | HelperStmt)[], edges: Set<string>, seen: Set<string>): void => {
    for (const s of body) { if (s.expr) scanExpr(s.expr, edges, seen); if ('then' in s && s.then) scanBody(s.then, edges, seen); if ('otherwise' in s && s.otherwise) scanBody(s.otherwise, edges, seen); }
  };
  for (const [name, c] of contracts) { scanningName = name; for (const m of c.methods) scanBody(m.body, deps.get(name)!, new Set()); }
  const active: string[] = [], done = new Set<string>(), order: string[] = [];
  const visit = (name: string): void => {
    if (done.has(name)) return;
    if (active.includes(name)) throw new PackageError('root-cycle', `root dependency cycle: ${[...active.slice(active.indexOf(name)), name].join(' -> ')}`);
    if (!deps.has(name)) fail(`unknown bound program ${name}`);
    active.push(name); for (const dependency of deps.get(name)!) visit(dependency); active.pop(); done.add(name); order.push(name);
  };
  visit(options.contract);
  for (const name of Object.keys(instances).sort()) visit(name);
  return { bindings, references, order };
}

export async function compilePackage(projectDir: string, options: PackageCompileOptions): Promise<PackageBuild> {
  if (typeof options?.contract !== 'string' || !options.bindings || typeof options.bindings !== 'object') throw new Error('compile options require contract and bindings');
  if (options.instances !== undefined && options.languageVersion !== 1) throw new PackageError('instance', 'explicit instances require languageVersion 1');
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
    try { program = parseModuleSource(decode(data.content, file), isEntry, file, sources, options.languageVersion); }
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
  const templates = new Map<string, { contract: Contract; owner: ModuleNode }>();
  let resolveTemplate: ((name: string) => string) | undefined;
  const lc1 = options.languageVersion === 1;
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
      const direct = text.split('.');
      if (lc1 && options.instances && Object.hasOwn(options.instances, direct[0]!)) {
        if (expectMethod !== (direct.length === 2) || direct.length > 2) throw new PackageError('instance', `invalid bound program reference ${text}`, node.file, at);
        return text;
      }
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
      const selectedName = lc1 ? canonical(home, programName) : programName;
      return method ? `${selectedName}.${method}` : selectedName;
    };
    if (node.isEntry) resolveTemplate = name => rewriteContractRef(name, node.program.contracts.values().next().value?.span ?? { start: 0, end: 0 }, false);
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
      if (!lc1 && contracts.has(contract.name)) throw new PackageError('duplicate-name', `contract ${contract.name} is already declared in ${owners.get(contract.name)!.moduleId}`, node.file, contract.span);
      const linked = { ...contract, params: contract.params.map(param), span: span(contract.span),
        methods: contract.methods.map((m: Method) => ({ ...m, params: m.params.map(param), body: m.body.map(stmt), span: span(m.span) })) };
      const name = lc1 ? canonical(node, contract.name) : contract.name;
      templates.set(canonical(node, contract.name), { contract: { ...linked, name }, owner: node });
      if (!lc1 || (node.isEntry && contract.name === options.contract && !Object.hasOwn(options.instances ?? {}, contract.name))) {
        // LC1 imports expose templates only. A local entry contract may still be selected directly.
        const selected = lc1 ? contract.name : name;
        owners.set(selected, { pkg: node.pkg, moduleId: node.id, kind: contract.kind });
        contracts.set(selected, { ...linked, name: selected });
      }
    }
    // Stable interface: exported helper signatures, then exported contract/token signatures.
    // Helper declaration bytes stay exactly as before so helper-only modules keep their digest.
    const helperExports = [...node.program.helpers.values()].filter(h => h.visibility === 'export').sort(byName).map(h => {
      const digest = tagged('package/declaration', concat(str(h.name), cs(h.params.length), ...h.params.map(p => concat(str(p.name), str(p.type))), str(h.result)));
      return { name: h.name, signature: signature(h), digest };
    });
    const contractExports = [...node.program.contracts.values()].filter(c => c.visibility === 'export').sort(byName).map(c => {
      const head = c.params.length ? `${c.kind} ${c.name}<${c.params.map(p => `${p.name}: ${p.type}`).join(', ')}>` : `${c.kind} ${c.name}`;
      const methods = c.methods.map(m => `${lc1 ? m.invocation + ' ' : ''}${m.name}(${m.params.map(p => `${p.name}: ${p.type}`).join(', ')})`).join('; ');
      const digest = tagged(lc1 ? 'package/contract/lc1' : 'package/contract', concat(str(c.kind), str(c.name), cs(c.params.length), ...c.params.map(p => concat(str(p.name), str(p.type))),
        cs(c.methods.length), ...c.methods.flatMap(m => [...(lc1 ? [str(m.invocation!)] : []), str(m.name), cs(m.params.length), ...m.params.map(p => concat(str(p.name), str(p.type)))])));
      return { name: c.name, signature: `${head} { ${methods} }`, digest };
    });
    const exported = [...helperExports, ...contractExports];
    interfaces.set(node.id, { digest: tagged(lc1 ? 'package/interface/lc1' : 'package/interface', concat(str(node.pkg.manifest.name), str(node.path), cs(exported.length), ...exported.map(x => x.digest))),
      exports: exported.map(x => ({ name: x.name, signature: x.signature, digest: hex(x.digest) })) });
  };
  await scheduler.run(`module:${entry.id}`);
  if (options.edition !== undefined && !isSupportedCompilerEdition(options.edition)) {
    throw new PackageError('manifest', `unsupported compiler edition ${JSON.stringify(options.edition)}; expected one of: ${SUPPORTED_COMPILER_EDITIONS.join(', ')}`, root.manifestFile);
  }
  if (options.optimizerVersion !== undefined && !isSupportedOptimizerVersion(options.optimizerVersion)) {
    throw new PackageError('manifest', `unsupported optimizerVersion ${JSON.stringify(options.optimizerVersion)}; expected one of: ${SUPPORTED_OPTIMIZER_VERSIONS.join(', ')}`, root.manifestFile);
  }
  if (options.edition !== undefined && root.manifest.edition !== undefined && options.edition !== root.manifest.edition) {
    throw new PackageError('manifest', `compile option edition ${JSON.stringify(options.edition)} conflicts with manifest edition ${JSON.stringify(root.manifest.edition)}`, root.manifestFile);
  }
  if (options.optimizerVersion !== undefined && root.manifest.optimizer !== undefined && options.optimizerVersion !== root.manifest.optimizer) {
    throw new PackageError('manifest', `compile option optimizerVersion ${JSON.stringify(options.optimizerVersion)} conflicts with manifest optimizer ${JSON.stringify(root.manifest.optimizer)}`, root.manifestFile);
  }
  if (options.optimize === false && root.manifest.optimizer !== undefined && root.manifest.optimizer !== 'none') {
    throw new PackageError('manifest', `compile option optimize: false conflicts with manifest optimizer ${JSON.stringify(root.manifest.optimizer)}`, root.manifestFile);
  }
  if (options.optimize === true && root.manifest.optimizer === 'none') {
    throw new PackageError('manifest', 'compile option optimize: true conflicts with manifest optimizer "none"', root.manifestFile);
  }
  const explicitEdition = options.edition ?? root.manifest.edition;
  const explicitOptimizer = options.optimizerVersion ?? root.manifest.optimizer;
  const effectiveOptimize = explicitOptimizer !== undefined ? explicitOptimizer !== 'none' : options.optimize;
  let effectiveOptions: CompileOptions = {
    ...(options as CompileOptions),
    ...(explicitEdition !== undefined ? { edition: explicitEdition } : {}),
    ...(explicitOptimizer !== undefined ? { optimizerVersion: explicitOptimizer } : {}),
    ...(effectiveOptimize !== undefined ? { optimize: effectiveOptimize } : {}),
  };
  const instanceArtifacts = new Map<string, ContractArtifact>();
  if (lc1) {
    if (Object.keys(options.instances ?? {}).length > limits.maxImportBindings) throw new PackageError('limit', `instances exceed ${limits.maxImportBindings}`);
    const bound = bindInstances(contracts, templates, owners, resolveTemplate!, options, helpers);
    effectiveOptions = { ...effectiveOptions, bindings: bound.bindings };
    const program: Program = { languageVersion: 1, helpers, contracts, imports: [] };
    // Resolve constructor references in topological order. Every explicitly requested binding is checked.
    const completed = instanceArtifacts;
    for (const name of bound.order) {
      for (const [param, reference] of bound.references.get(name) ?? []) {
        const target = completed.get(reference.name)!;
        bound.bindings[name]![param] = reference.method ? target.methods.find(m => m.name === reference.method)!.leaf : target.policy.root;
      }
      const result = await compileLinkedProgramAsync(program, { ...effectiveOptions, contract: name }, undefined, sources);
      completed.set(name, result.artifact);
    }
  }
  const { artifact, roots } = await compileLinkedProgramAsync({ ...(options.languageVersion === 1 ? { languageVersion: 1 as const } : {}), helpers, contracts, imports: [] }, effectiveOptions, event => trace.push(event), sources);
  const allRoots = new Map(roots.map(item => [item.name, item]));
  for (const [name, item] of instanceArtifacts) allRoots.set(name, { name, root: item.policy.root, methods: item.methods.map(m => ({ name: m.name, leaf: m.leaf })) });
  const links: LinkedContract[] = [...allRoots.values()].filter(item => item.name !== artifact.contract && owners.get(item.name)?.pkg.id !== root.id).map(item => {
    const owner = owners.get(item.name)!;
    return { name: item.name, kind: owner.kind, package: owner.pkg.id, module: owner.moduleId, packageDigest: hex(owner.pkg.treeDigest), root: item.root, methods: item.methods };
  }).sort(byName);
  const graph: Omit<BuildGraph, 'digest'> = {
    schema: BUILD_GRAPH_SCHEMA,
    ...(lc1 ? { interfaceVersion: 'lotus-v2/module-interface/lc1' as const,
      instances: [...instanceArtifacts].filter(([name]) => Object.hasOwn(options.instances ?? {}, name)).map(([name, item]) => ({ name, template: options.instances![name]!.template, bindings: item.bindings, root: item.policy.root })).sort(byName) } : {}),
    compiler: {
      name: COMPILER_NAME,
      version: COMPILER_VERSION,
      profile: effectiveOptimize === false ? 'unoptimized' : 'optimized',
      ...(explicitEdition !== undefined ? { edition: explicitEdition } : {}),
      ...(explicitOptimizer !== undefined ? { optimizerVersion: explicitOptimizer } : {}),
    },
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

// ---------------------------------------------------------------------------
// Permanent BranchRoot Spendability & Source-Lock Reproducibility Verifier

export const SPEND_BUNDLE_SCHEMA = 'lotus-v2/spend-bundle/1' as const;

export type SpendBundleSourceFile = {
  path: string;
  content: string;
  digest: string;
};

export type SpendBundle = {
  schema: typeof SPEND_BUNDLE_SCHEMA;
  contract: string;
  kind: 'contract' | 'token';
  edition: CompilerEdition;
  optimizerVersion: OptimizerVersion;
  languageVersion: LanguageVersion;
  entryFile: string;
  sources: SpendBundleSourceFile[];
  bindings: Record<string, Record<string, BoundValue>>;
  expectedRoot: string;
  expectedMethods: { name: string; leaf: string; scriptHex: string; proof: string[] }[];
  bundleDigest: string;
};

export type SpendBundleOptions = {
  edition?: CompilerEdition;
  optimizerVersion?: OptimizerVersion;
  optimize?: boolean;
  languageVersion?: LanguageVersion;
  bindings?: Record<string, Record<string, BoundValue>>;
  entryFile?: string;
};

export type SpendBundleVerification = {
  ok: boolean;
  contractRoot: string;
  recomputedRoot?: string;
  matchesRoot: boolean;
  matchesMethods: boolean;
  edition: CompilerEdition;
  optimizerVersion: OptimizerVersion;
  artifact?: ContractArtifact;
  error?: string;
};

function sourceFileDigest(content: string): string {
  return hex(tagged('package/file', bytes(utf8(content))));
}

function normalizeSpendBundleSources(
  sources: string | Record<string, string> | readonly { path: string; content: string }[],
  defaultEntryFile: string,
): { entryFile: string; files: SpendBundleSourceFile[] } {
  if (typeof sources === 'string') {
    const entryFile = defaultEntryFile;
    return {
      entryFile,
      files: [{ path: entryFile, content: sources, digest: sourceFileDigest(sources) }],
    };
  }
  if (Array.isArray(sources)) {
    if (!sources.length) throw new Error('spend bundle requires at least one source file');
    const files = sources
      .map(item => ({ path: item.path, content: item.content, digest: sourceFileDigest(item.content) }))
      .sort((a, b) => (a.path < b.path ? -1 : a.path > b.path ? 1 : 0));
    const entryFile = defaultEntryFile !== '<source>' ? defaultEntryFile : files[0]!.path;
    return { entryFile, files };
  }
  if (sources && typeof sources === 'object') {
    const entries = Object.entries(sources as Record<string, string>);
    if (!entries.length) throw new Error('spend bundle requires at least one source file');
    const files = entries
      .map(([path, content]) => ({ path, content, digest: sourceFileDigest(content) }))
      .sort((a, b) => (a.path < b.path ? -1 : a.path > b.path ? 1 : 0));
    const entryFile = defaultEntryFile !== '<source>' ? defaultEntryFile : entries[0]![0];
    return { entryFile, files };
  }
  throw new Error('invalid sources for spend bundle');
}

function serializeBindingsForDigest(bindings: Record<string, Record<string, BoundValue>>): Record<string, Record<string, string | boolean>> {
  const out: Record<string, Record<string, string | boolean>> = {};
  for (const contractName of Object.keys(bindings).sort()) {
    const inner = bindings[contractName]!;
    const innerSorted: Record<string, string | boolean> = {};
    for (const key of Object.keys(inner).sort()) {
      const val = inner[key]!;
      innerSorted[key] = typeof val === 'bigint' ? val.toString() : val;
    }
    out[contractName] = innerSorted;
  }
  return out;
}

function computeSpendBundleDigest(bundle: Omit<SpendBundle, 'bundleDigest'>): string {
  const canonical = {
    schema: bundle.schema,
    contract: bundle.contract,
    kind: bundle.kind,
    edition: bundle.edition,
    optimizerVersion: bundle.optimizerVersion,
    languageVersion: bundle.languageVersion,
    entryFile: bundle.entryFile,
    sources: bundle.sources.map(s => ({ path: s.path, digest: s.digest })),
    bindings: serializeBindingsForDigest(bundle.bindings),
    expectedRoot: bundle.expectedRoot,
    expectedMethods: bundle.expectedMethods,
  };
  return hex(tagged('spend-bundle', utf8(JSON.stringify(canonical))));
}

/**
 * Package canonical `.lotus` source files, compiler `edition`, `optimizerVersion`, constructor
 * `bindings`, and expected `BranchRoot` + leaf commitments into a self-contained `SpendBundle`
 * so covenant UTXOs remain permanently spendable and reproducible across compiler upgrades.
 */
export function createSpendBundle(
  artifact: ContractArtifact,
  sources: string | Record<string, string> | readonly { path: string; content: string }[],
  options: SpendBundleOptions = {},
): SpendBundle {
  const edition = resolveCompilerEdition(options.edition ?? artifact.build?.compiler?.edition ?? DEFAULT_COMPILER_EDITION);
  const optimizerVersion = resolveOptimizerVersion({
    optimize: options.optimize ?? (artifact.build?.compiler?.profile === 'unoptimized' ? false : undefined),
    optimizerVersion: options.optimizerVersion ?? artifact.build?.compiler?.optimizerVersion,
  });
  const languageVersion: LanguageVersion = options.languageVersion ?? artifact.languageVersion ?? 0;
  const reconstructedContractBindings: Record<string, BoundValue> = {};
  for (const b of artifact.bindings) {
    reconstructedContractBindings[b.name] = b.value;
  }
  const bindings: Record<string, Record<string, BoundValue>> = {
    [artifact.contract]: reconstructedContractBindings,
    ...(options.bindings ?? {}),
  };
  const { entryFile, files } = normalizeSpendBundleSources(sources, options.entryFile ?? '<source>');
  const expectedMethods = artifact.methods.map(m => ({
    name: m.name,
    leaf: m.leaf,
    scriptHex: m.scriptHex,
    proof: [...m.proof],
  }));
  const unsigned: Omit<SpendBundle, 'bundleDigest'> = {
    schema: SPEND_BUNDLE_SCHEMA,
    contract: artifact.contract,
    kind: artifact.kind ?? 'contract',
    edition,
    optimizerVersion,
    languageVersion,
    entryFile,
    sources: files,
    bindings,
    expectedRoot: artifact.policy.root,
    expectedMethods,
  };
  return {
    ...unsigned,
    bundleDigest: computeSpendBundleDigest(unsigned),
  };
}

/**
 * Verify that a `SpendBundle` has intact BLAKE3 source/bundle digests and that recompiling its
 * sources under the pinned `edition` and `optimizerVersion` reproduces the exact byte-for-byte
 * method leaf scripts, Merkle proofs, and 32-byte `BranchRoot`.
 */
export function verifySpendBundleReproducibility(bundle: SpendBundle): SpendBundleVerification {
  const fail = (error: string, recomputedRoot?: string): SpendBundleVerification => ({
    ok: false,
    contractRoot: bundle?.expectedRoot ?? '',
    ...(recomputedRoot !== undefined ? { recomputedRoot } : {}),
    matchesRoot: false,
    matchesMethods: false,
    edition: (bundle?.edition ?? DEFAULT_COMPILER_EDITION) as CompilerEdition,
    optimizerVersion: (bundle?.optimizerVersion ?? DEFAULT_OPTIMIZER_VERSION) as OptimizerVersion,
    error,
  });
  if (!bundle || bundle.schema !== SPEND_BUNDLE_SCHEMA) {
    return fail(`unsupported spend bundle schema "${String(bundle?.schema)}"`);
  }
  if (!isSupportedCompilerEdition(bundle.edition)) {
    return fail(`unsupported compiler edition "${String(bundle.edition)}"; expected one of: ${SUPPORTED_COMPILER_EDITIONS.join(', ')}`);
  }
  if (!isSupportedOptimizerVersion(bundle.optimizerVersion)) {
    return fail(`unsupported optimizerVersion "${String(bundle.optimizerVersion)}"; expected one of: ${SUPPORTED_OPTIMIZER_VERSIONS.join(', ')}`);
  }
  if (!Array.isArray(bundle.sources) || !bundle.sources.length) {
    return fail('spend bundle has no source files');
  }
  for (const file of bundle.sources) {
    if (typeof file?.path !== 'string' || typeof file?.content !== 'string' || typeof file?.digest !== 'string') {
      return fail('malformed source file entry in spend bundle');
    }
    const actualDigest = sourceFileDigest(file.content);
    if (actualDigest !== file.digest) {
      return fail(`source digest mismatch for ${file.path}: expected ${file.digest}, got ${actualDigest}`);
    }
  }
  const expectedBundleDigest = computeSpendBundleDigest(bundle);
  if (bundle.bundleDigest !== expectedBundleDigest) {
    return fail(`spend bundle digest mismatch: expected ${bundle.bundleDigest}, computed ${expectedBundleDigest}`);
  }
  const entry = bundle.sources.find(s => s.path === bundle.entryFile) ?? bundle.sources[0]!;
  let artifact: ContractArtifact;
  try {
    artifact = compileContract(
      entry.content,
      {
        contract: bundle.contract,
        bindings: bundle.bindings,
        edition: bundle.edition,
        optimizerVersion: bundle.optimizerVersion,
        languageVersion: bundle.languageVersion,
      },
      entry.path,
    );
  } catch (error) {
    return fail(`recompilation failed: ${(error as Error).message}`);
  }
  const recomputedRoot = artifact.policy.root;
  const matchesRoot = recomputedRoot === bundle.expectedRoot;
  let matchesMethods = artifact.methods.length === bundle.expectedMethods.length;
  if (matchesMethods) {
    for (let i = 0; i < bundle.expectedMethods.length; i++) {
      const exp = bundle.expectedMethods[i]!;
      const got = artifact.methods.find(m => m.name === exp.name);
      if (
        !got ||
        got.leaf !== exp.leaf ||
        got.scriptHex !== exp.scriptHex ||
        JSON.stringify(got.proof) !== JSON.stringify(exp.proof)
      ) {
        matchesMethods = false;
        break;
      }
    }
  }
  if (!matchesRoot || !matchesMethods) {
    return {
      ok: false,
      contractRoot: bundle.expectedRoot,
      recomputedRoot,
      matchesRoot,
      matchesMethods,
      edition: bundle.edition,
      optimizerVersion: bundle.optimizerVersion,
      artifact,
      error: !matchesRoot
        ? `recomputed BranchRoot ${recomputedRoot} does not match expected ${bundle.expectedRoot}`
        : 'recomputed method leaves or scriptHex do not match expected methods',
    };
  }
  return {
    ok: true,
    contractRoot: bundle.expectedRoot,
    recomputedRoot,
    matchesRoot: true,
    matchesMethods: true,
    edition: bundle.edition,
    optimizerVersion: bundle.optimizerVersion,
    artifact,
  };
}

export const verifyBranchRootReproducibility = verifySpendBundleReproducibility;

export function assertSpendBundleReproducibility(bundle: SpendBundle): ContractArtifact {
  const result = verifySpendBundleReproducibility(bundle);
  if (!result.ok) throw new Error(result.error ?? 'spend bundle reproducibility verification failed');
  return result.artifact!;
}

