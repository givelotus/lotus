#!/usr/bin/env node
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { join } from 'node:path';
import { compileContractWithTrace, type SchedulerEvent } from './generic.js';
import { compilePackage, PackageError, packageCompileError } from './packages.js';
import { generateContractPython, generateContractTypeScript } from './bindings.js';
import { compileTargetContract, type TargetCompileOptions, type TargetArtifact } from './target-compiler.js';
import { resolveTarget } from './targets.js';
import { CompileError, DiagnosticBag, SourceManager, errorDiagnostics, renderDiagnostics, shouldColor } from './diagnostics.js';

function present(err: unknown, packageDir?: string): string {
  const color = shouldColor(process.stderr);
  if (err instanceof CompileError) return err.render({ color });
  if (err instanceof PackageError) {
    const sources = new SourceManager();
    if (packageDir && err.file) { try { sources.add(err.file, readFileSync(join(packageDir, err.file), 'utf8')); } catch { /* file-level diagnostic */ } }
    return packageCompileError(err, sources).render({ color });
  }
  return renderDiagnostics(errorDiagnostics(err).diagnostics, new SourceManager(), { color });
}

try {
  // `--package DIR` compiles the root package at DIR (lotus.toml + lotus.lock) instead of one source file.
  const packageMode = process.argv[2] === '--package';
  const args = packageMode ? process.argv.slice(1) : process.argv;
  if (args.length !== 5 && !(args.length === 6 && args[5] === '--trace')) throw new Error('usage: lotus-v2-contract-compile (SOURCE | --package DIR) OPTIONS.json OUTPUT_DIR [--trace]');
  const options = JSON.parse(readFileSync(args[3]!, 'utf8')) as TargetCompileOptions;
  function fail(code: string, message: string): never { return new DiagnosticBag(new SourceManager()).raise(code, message); }
  if (!options || typeof options !== 'object' || Array.isArray(options)) fail('E0601', 'compile options must be an object with contract and bindings');
  let selected;
  try { selected = resolveTarget(options.target === undefined ? 'lotus-v2' : options.target); } catch (error) { fail('E1200', (error as Error).message); }
  let artifact: TargetArtifact, trace: SchedulerEvent[] = [];
  if (packageMode) {
    if (selected!.id !== 'lotus-v2') fail('E1203', 'eCash package linking is not implemented; compile a single selected source method.');
    if (options.method !== undefined) fail('E1202', 'Lotus package compilation commits the complete policy; selected-method output is not supported.');
    ({ artifact, trace } = await compilePackage(args[2]!, { ...options, target: 'lotus-v2' }));
  } else if (selected!.id === 'ecash') {
    if (args[5] === '--trace') fail('E1203', 'eCash source compilation does not produce a Lotus scheduler trace.');
    artifact = compileTargetContract(readFileSync(args[2]!, 'utf8'), options, args[2]!);
  } else {
    if (options.method !== undefined) fail('E1202', 'Lotus compilation commits the complete policy; selected-method output is not supported.');
    ({ artifact, trace } = await compileContractWithTrace(readFileSync(args[2]!, 'utf8'), { ...options, target: 'lotus-v2' }, args[2]!));
  }
  const out = args[4]!; mkdirSync(out, { recursive: true });
  writeFileSync(join(out,'artifact.json'), JSON.stringify(artifact,null,2) + '\n');
  if (artifact.schema === 'ecash/script-artifact/1') {
    writeFileSync(join(out,'script.hex'), artifact.scriptHex + '\n');
  } else {
    writeFileSync(join(out,`${artifact.contract}.ts`), generateContractTypeScript(artifact));
    writeFileSync(join(out,`${artifact.contract}.py`), generateContractPython(artifact));
  }
  if (args[5] === '--trace') writeFileSync(join(out,'scheduler-trace.json'), JSON.stringify(trace,null,2) + '\n');
} catch (err) {
  const packageDir = process.argv[2] === '--package' ? process.argv[3] : undefined;
  const text = present(err, packageDir);
  process.stderr.write(text.endsWith('\n') ? text : `${text}\n`);
  process.exitCode = 1;
}
