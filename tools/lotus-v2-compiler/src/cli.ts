#!/usr/bin/env node
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { join } from 'node:path';
import { compilePayment } from './compiler.js';
import { generatePython, generateTypeScript } from './bindings.js';

function main(args: string[]): void {
  if (args.length !== 3) throw new Error('usage: lotus-v2-compile SOURCE OWNER_XONLY_HEX OUTPUT_DIR');
  const [sourceFile, owner, out] = args as [string, string, string];
  const artifact = compilePayment(readFileSync(sourceFile, 'utf8'), owner);
  mkdirSync(out, { recursive: true });
  writeFileSync(join(out, 'artifact.json'), JSON.stringify(artifact, null, 2) + '\n');
  writeFileSync(join(out, `${artifact.contract}.ts`), generateTypeScript(artifact));
  writeFileSync(join(out, `${artifact.contract}.py`), generatePython(artifact));
}
try { main(process.argv.slice(2)); } catch (err) { process.stderr.write(`${(err as Error).message}\n`); process.exitCode = 1; }
