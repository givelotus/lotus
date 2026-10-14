#!/usr/bin/env node
import { readFileSync, writeFileSync } from 'node:fs';
import { buildPaymentFixture, type PaymentFixtureInput } from './fixtures.js';
import type { PaymentOutput } from './runtime.js';

function object(x: unknown): Record<string, unknown> { if (!x || typeof x !== 'object' || Array.isArray(x)) throw new Error('expected object'); return x as Record<string, unknown>; }
function string(x: unknown): string { if (typeof x !== 'string') throw new Error('expected string'); return x; }
function number(x: unknown): number { if (!Number.isInteger(x)) throw new Error('expected integer'); return x as number; }
function decimal(x: unknown): bigint { const s = string(x); if (!/^(0|[1-9][0-9]*)$/.test(s)) throw new Error('expected canonical decimal atom string'); return BigInt(s); }
function output(x: unknown): PaymentOutput {
  const o = object(x);
  if (o.flags !== 0 || !Array.isArray(o.branches) || !Array.isArray(o.paths)) throw new Error('payment output shape');
  return { flags: 0, value: decimal(o.valueAtoms), branches: o.branches.map(string), paths: o.paths.map(p => { if (!Array.isArray(p)) throw new Error('path array'); return p.map(number); }) };
}
function parse(x: unknown): PaymentFixtureInput {
  const o = object(x); if (o.schema !== 'lotus-v2/payment-fixture-input/1') throw new Error('fixture input schema');
  const outpoint = object(o.outpoint); if (!Array.isArray(o.outputs)) throw new Error('outputs array');
  if (o.signingMode !== 0 || o.profile !== 'payment-fixture-p01-v1') throw new Error('FULL fixture profile only');
  return { source: string(o.source), owner: string(o.owner), testSecret: string(o.testSecret), chainId: string(o.chainId),
    outpoint: { txid: string(outpoint.txid), index: number(outpoint.index) }, sequence: number(o.sequence), lock: decimal(o.lock),
    coin: output(o.coin), outputs: o.outputs.map(output), profile: o.profile, signingMode: 0 };
}
try {
  if (process.argv.length !== 4) throw new Error('usage: lotus-v2-payment-fixture INPUT.json OUTPUT.json');
  const fixture = buildPaymentFixture(parse(JSON.parse(readFileSync(process.argv[2]!, 'utf8'))));
  writeFileSync(process.argv[3]!, JSON.stringify(fixture, null, 2) + '\n');
} catch (err) { process.stderr.write(`${(err as Error).message}\n`); process.exitCode = 1; }
