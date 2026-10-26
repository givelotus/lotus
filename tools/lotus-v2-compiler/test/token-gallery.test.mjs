import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

test('fungible token gallery compiles separate mint/rules trees and a mandatory holder path', () => {
  const out = mkdtempSync(join(tmpdir(), 'lotus-v2-token-gallery-'));
  try {
    const run = spawnSync(process.execPath, ['examples/gallery/run-fungible-token.mjs', out], {
      cwd: fileURLToPath(new URL('..', import.meta.url)), encoding: 'utf8',
      env: { ...process.env, LOTUS_V2_SKIP_VM: '1' },
    });
    assert.equal(run.status, 0, run.stderr);
    const summary = JSON.parse(readFileSync(join(out, 'fungible-token-summary.json'), 'utf8'));
    assert.equal(summary.holder.tokenId, summary.trees.mint);
    assert.deepEqual(summary.holder.branches, [summary.trees.wallet, summary.trees.rules]);
    assert.deepEqual(summary.holder.paths, [[0, 1]]);
    assert.notEqual(summary.trees.mint, summary.trees.rules);
    assert.equal(summary.examples.implicitBurnAtoms, '50');
    assert.equal(summary.stages.transactionFraming, 'passed');
    assert.equal(summary.stages.signature, 'passed-schnorr');
    assert.equal(summary.stages.accounting, 'passed-candidate-profile');
    assert.equal(summary.stages.block, 'unavailable');
    assert.equal(summary.transactions.mint.feeAtoms, '3000');
    assert.equal(summary.transactions.transfer.implicitBurnAtoms, '50');
    assert.ok(summary.transactions.mint.wireBytes >= 500);
    assert.ok(summary.transactions.transfer.wireBytes >= 500);
    assert.deepEqual(summary.transactions.merge.tokenInputs, ['700', '250']);
    assert.equal(summary.transactions.merge.tokenOutputAtoms, '950');
    assert.equal(summary.transactions.merge.implicitBurnAtoms, '0');
    assert.equal(summary.checks.holderRequiresWallet, true);
    assert.equal(summary.checks.missingWalletPathRejects, true);
    assert.equal(summary.checks.mergeCombinesTwoInputs, true);
    assert.equal(summary.checks.mergeBurnsNoSupply, true);
    assert.ok(Object.values(summary.checks).every(Boolean));
    const mint = JSON.parse(readFileSync(join(out, 'FungibleToken.json'), 'utf8'));
    assert.equal(mint.kind, 'token');
    assert.equal(mint.methods[0].mintAmountParam, 'amount');
    assert.deepEqual(mint.methods[0].args.map(x => x.type), ['Signature']);
  } finally { rmSync(out, { recursive: true, force: true }); }
});
