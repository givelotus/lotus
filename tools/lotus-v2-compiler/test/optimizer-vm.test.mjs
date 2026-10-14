import test from 'node:test';
import assert from 'node:assert/strict';
import { existsSync } from 'node:fs';
import { join } from 'node:path';
import { spawnSync } from 'node:child_process';
import { compileContract } from '../dist/generic.js';

const reference = process.env.LOTUS_V2_REFERENCE_PATH ?? join(import.meta.dirname, '../../lotus-v2-reference');
const available = existsSync(join(reference, 'lotus_v2_reference/vm.py'));

test('optimized and unoptimized scripts agree in independent P03 VM', { skip: !available }, () => {
  const sources = [
    ['single', 'contract C { function m(x: Bool) { require(x == true); } }'],
    ['reused', 'contract C { function m(x: Bool) { require(x == true); require(x == true); } }'],
    ['branch', 'contract C { function m(x: Bool) { if (x) { require(true); } else { require(false); } } }'],
    ['overflow', 'contract C { function m(x: Int) { require(x + 1 > 0); } }'],
  ];
  const bools = ['00'.repeat(16), '01' + '00'.repeat(15), '02' + '00'.repeat(15)];
  const maxInt = 'ff'.repeat(15) + '7f';
  const fixtures = [];
  for (const [name, source] of sources) {
    const options = { contract: 'C', bindings: {} };
    const before = compileContract(source, { ...options, optimize: false }).methods[0].scriptHex;
    const after = compileContract(source, options).methods[0].scriptHex;
    for (const arg of name === 'overflow' ? ['00'.repeat(16), '01' + '00'.repeat(15), maxInt] : bools) {
      fixtures.push({ name: `${name}:${arg.slice(0, 4)}`, before, after, args: [arg] });
    }
  }
  const payment = 'contract Payment<owner: PublicKey> { function spend(sig: Signature) { require(checksig(sig, owner)); } }';
  const paymentOptions = { contract: 'Payment', bindings: { Payment: { owner: 'f9308a019258c31049344f85f89d5229b531c845836f99b08601f113bce036f9' } } };
  fixtures.push({ name: 'invalid signature length',
    before: compileContract(payment, { ...paymentOptions, optimize: false }).methods[0].scriptHex,
    after: compileContract(payment, paymentOptions).methods[0].scriptHex,
    args: [''], signing: true });
  const run = spawnSync(process.env.PYTHON ?? 'python3', [new URL('./optimizer-vm.py', import.meta.url).pathname], {
    encoding: 'utf8', input: JSON.stringify(fixtures),
    env: { ...process.env, PYTHONPATH: [reference, process.env.PYTHONPATH].filter(Boolean).join(':') },
  });
  assert.equal(run.status, 0, run.stderr || run.stdout);
  assert.match(run.stdout, /differential passed/);
});
