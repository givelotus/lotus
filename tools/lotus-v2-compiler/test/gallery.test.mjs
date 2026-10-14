import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { compileContract } from '../dist/generic.js';

test('gallery emits deterministically checked scripts and membership proofs', () => {
  const dir = mkdtempSync(join(tmpdir(), 'lotus-v2-gallery-'));
  try {
    const run = spawnSync(process.execPath, ['examples/gallery/run-gallery.mjs', dir], { cwd: fileURLToPath(new URL('..', import.meta.url)), encoding: 'utf8' });
    assert.equal(run.status, 0, run.stderr);
    const summary = JSON.parse(readFileSync(join(dir, 'summary.json'), 'utf8'));
    assert.equal(summary.examples.length, 7);
    assert.deepEqual(summary.checks, { templateKeyChangesRoot: true, linkedTargetChangesRoot: true });
    assert.equal(summary.examples.find(x => x.name === 'recovery').methods.length, 2);
    for (const item of summary.examples) {
      assert.equal(item.stages.compile, 'passed');
      assert.equal(item.stages.proof, 'passed');
      assert.ok(item.methods.every(m => m.scriptHex && m.leaf && Array.isArray(m.proof)));
    }
    const helper = JSON.parse(readFileSync(join(dir, 'helper.json'), 'utf8'));
    const hashlock = JSON.parse(readFileSync(join(dir, 'hashlock.json'), 'utf8'));
    assert.equal(helper.methods[0].scriptHex, hashlock.methods[0].scriptHex);
    assert.equal(helper.methods[0].leaf, hashlock.methods[0].leaf);
    assert.ok(helper.methods[0].staticResources.helperExpansions > 0);
    const recovery = JSON.parse(readFileSync(join(dir, 'recovery.json'), 'utf8'));
    assert.notEqual(recovery.methods[0].leaf, recovery.methods[1].leaf);
    assert.ok(recovery.methods.every(m => m.proof.length === 1));
  } finally { rmSync(dir, { recursive: true, force: true }); }
});

test('unbound and cyclic compile-time references reject', () => {
  const payment = `contract Payment<owner: PublicKey> { function spend(sig: Signature) { require(checksig(sig, owner)); } }`;
  assert.throws(() => compileContract(payment, { contract: 'Payment', bindings: {} }), /bound|binding|missing|arity/i);
  const self = `contract Loop { function spend() { require(contract_root(Loop) == contract_root(Loop)); } }`;
  assert.throws(() => compileContract(self, { contract: 'Loop', bindings: { Loop: {} } }), /cycl|self/i);
  const pair = `contract A { function spend() { require(contract_root(B) == contract_root(B)); } }
    contract B { function spend() { require(contract_root(A) == contract_root(A)); } }`;
  assert.throws(() => compileContract(pair, { contract: 'A', bindings: { A: {}, B: {} } }), /cycl/i);
});
