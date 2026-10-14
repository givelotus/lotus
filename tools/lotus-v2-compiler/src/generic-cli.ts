#!/usr/bin/env node
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { join } from 'node:path';
import { compileContractWithTrace, type CompileOptions } from './generic.js';
import { generateContractPython, generateContractTypeScript } from './bindings.js';

try {
  if (process.argv.length !== 5 && !(process.argv.length === 6 && process.argv[5] === '--trace')) throw new Error('usage: lotus-v2-contract-compile SOURCE OPTIONS.json OUTPUT_DIR [--trace]');
  const source = readFileSync(process.argv[2]!, 'utf8');
  const options = JSON.parse(readFileSync(process.argv[3]!, 'utf8')) as CompileOptions;
  const { artifact, trace } = await compileContractWithTrace(source, options);
  const out = process.argv[4]!; mkdirSync(out, { recursive: true });
  writeFileSync(join(out,'artifact.json'), JSON.stringify(artifact,null,2) + '\n');
  writeFileSync(join(out,`${artifact.contract}.ts`), generateContractTypeScript(artifact));
  writeFileSync(join(out,`${artifact.contract}.py`), generateContractPython(artifact));
  if (process.argv[5] === '--trace') writeFileSync(join(out,'scheduler-trace.json'), JSON.stringify(trace,null,2) + '\n');
} catch (err) { process.stderr.write(`${(err as Error).message}\n`); process.exitCode = 1; }
