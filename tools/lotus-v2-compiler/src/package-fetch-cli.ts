#!/usr/bin/env node
/** Fetch module-path packages into `.lotus/deps` (or `vendor/`) and write `lotus.lock`. */
import { join } from 'node:path';
import { fetchPackages } from './package-sources.js';

try {
  const args = process.argv.slice(2);
  const vendor = args.includes('--vendor');
  const positional = args.filter(arg => !arg.startsWith('--'));
  if (positional.length !== 1 || args.length !== positional.length + (vendor ? 1 : 0)) throw new Error('usage: lotus-v2-package-fetch DIR [--vendor]');
  fetchPackages(positional[0]!, { vendor });
  process.stdout.write(`wrote ${join(positional[0]!, 'lotus.lock')}\n`);
} catch (err) { process.stderr.write(`${(err as Error).message}\n`); process.exitCode = 1; }
