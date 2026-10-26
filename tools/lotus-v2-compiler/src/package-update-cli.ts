#!/usr/bin/env node
/**
 * Resolve one root module dependency that may name a branch or a `^`/`~` range,
 * rewrite that manifest entry to an exact tag or commit, then fetch.
 */
import { join } from 'node:path';
import { updatePackages } from './package-sources.js';

try {
  const args = process.argv.slice(2);
  const vendor = args.includes('--vendor');
  const positional = args.filter(arg => !arg.startsWith('--'));
  if (positional.length !== 2 || args.length !== positional.length + (vendor ? 1 : 0)) throw new Error('usage: lotus-v2-package-update DIR SPEC [--vendor]');
  updatePackages(positional[0]!, positional[1]!, { vendor });
  process.stdout.write(`wrote ${join(positional[0]!, 'lotus.lock')}\n`);
} catch (err) { process.stderr.write(`${(err as Error).message}\n`); process.exitCode = 1; }
