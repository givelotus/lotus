#!/usr/bin/env node
/** Rewrite or check `lotus.lock` from local files only. No network or registry access. */
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { generateLock, LOCK_FILE, updateLock } from './packages.js';

try {
  const [dir, flag] = process.argv.slice(2);
  if (!dir || process.argv.length > 4 || (flag !== undefined && flag !== '--check')) throw new Error('usage: lotus-v2-package-lock DIR [--check]');
  if (flag === '--check') {
    let current = '';
    try { current = readFileSync(join(dir, LOCK_FILE), 'utf8'); } catch { /* missing lock is stale */ }
    if (current !== generateLock(dir)) throw new Error(`${LOCK_FILE} is stale; review the dependency changes and run lotus-v2-package-lock ${dir}`);
    process.stdout.write(`${LOCK_FILE} is up to date\n`);
  } else {
    updateLock(dir);
    process.stdout.write(`wrote ${join(dir, LOCK_FILE)}\n`);
  }
} catch (err) { process.stderr.write(`${(err as Error).message}\n`); process.exitCode = 1; }
