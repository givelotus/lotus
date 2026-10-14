#!/usr/bin/env node
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { join } from 'node:path';
import { compileContract, type CompileOptions } from './generic.js';
import { generateContractTypeScript } from './bindings.js';

try {
  if (process.argv.length !== 5) throw new Error('usage: lotus-v2-contract-compile SOURCE OPTIONS.json OUTPUT_DIR');
  const source = readFileSync(process.argv[2]!, 'utf8');
  const options = JSON.parse(readFileSync(process.argv[3]!, 'utf8')) as CompileOptions;
  const artifact = compileContract(source, options);
  const out = process.argv[4]!; mkdirSync(out, { recursive: true });
  writeFileSync(join(out,'artifact.json'), JSON.stringify(artifact,null,2) + '\n');
  writeFileSync(join(out,`${artifact.contract}.ts`), generateContractTypeScript(artifact));
} catch (err) { process.stderr.write(`${(err as Error).message}\n`); process.exitCode = 1; }
