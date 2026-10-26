import test from 'node:test';
import assert from 'node:assert/strict';
import { chmodSync, cpSync, existsSync, mkdirSync, mkdtempSync, readFileSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { compileContract } from '../dist/generic.js';
import { CompileError } from '../dist/diagnostics.js';
import { compilePackage, generateLock } from '../dist/packages.js';

const fixture = fileURLToPath(new URL('../examples/packages/cross/', import.meta.url));
const OWNER = '79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798';
const key3 = 'f9308a019258c31049344f85f89d5229b531c845836f99b08601f113bce036f9';
const key4 = 'e493dbf1c10d80f3581e4904930b1404cc6c13900ee0758474fa94abe8c4cd13';

function poison(dir) {
  const bin = join(dir, 'bin');
  const log = join(dir, 'git.log');
  mkdirSync(bin, { recursive: true });
  writeFileSync(join(bin, 'git'), `#!/bin/sh\necho invoked >> ${JSON.stringify(log)}\nexit 99\n`);
  chmodSync(join(bin, 'git'), 0o755);
  return { bin, invoked: () => existsSync(log) ? readFileSync(log, 'utf8') : '' };
}

function ops(artifact, name) {
  return artifact.methods.find(method => method.name === name).sourceMap.map(entry => entry.op);
}

test('one offline schema-2 compile keeps quoted imports, linked contracts, statement helpers and checksig fusion', async () => {
  const locked = readFileSync(join(fixture, 'lotus.lock'), 'utf8');
  const lock = JSON.parse(locked);
  assert.equal(lock.schema, 'lotus-v2/package-lock/2');
  const policy = lock.packages.find(pkg => pkg.name === 'policy');
  const std = lock.packages.find(pkg => pkg.name === 'github.com/acme/lotus-std');
  assert.deepEqual(policy.locator, { kind: 'path', path: 'packages/policy' });
  assert.equal(policy.commit, undefined);
  assert.equal(std.override, true);
  assert.deepEqual(std.locator, { kind: 'path', path: 'packages/std' });
  assert.equal(std.commit, undefined);
  assert.equal(std.gitTree, undefined);
  assert.equal(lock.root.replace['github.com/acme/lotus-std'].kind, 'path');

  const base = mkdtempSync(join(tmpdir(), 'lotus-cross-'));
  const { bin, invoked } = poison(join(base, 'poison'));
  const previous = process.env.PATH;
  process.env.PATH = bin;
  let vault;
  let payer;
  try {
    assert.equal(generateLock(fixture), locked);
    vault = (await compilePackage(fixture, { contract: 'Vault', bindings: { Vault: { owner: OWNER } } })).artifact;
    const leaf = vault.methods.find(method => method.name === 'spend').leaf;
    const options = {
      contract: 'Payer',
      bindings: { Vault: { owner: OWNER }, Payer: { a: key3, b: key4, owner: OWNER, vaultRoot: vault.policy.root, vaultLeaf: leaf } },
    };
    payer = (await compilePackage(fixture, options)).artifact;
    assert.equal(generateLock(fixture), locked);
    const escrow = readFileSync(join(fixture, 'packages/policy/src/escrow.lotus'), 'utf8');
    const mark = readFileSync(join(fixture, 'packages/std/src/mark.lotus'), 'utf8');
    const main = readFileSync(join(fixture, 'src/main.lotus'), 'utf8').replace(/^import .*\n/gm, '');
    const flat = compileContract(`${mark.replaceAll('export ', '')}\n${escrow.replaceAll('export ', '')}\n${main}`, options);
    assert.deepEqual(payer.methods.map(method => [method.name, method.scriptHex]), flat.methods.map(method => [method.name, method.scriptHex]));
    assert.equal(payer.policy.root, flat.policy.root);
    assert.equal(flat.build, undefined);
    assert.equal(flat.links, undefined);
  } finally {
    process.env.PATH = previous;
  }
  assert.equal(invoked(), '');

  assert.equal(vault.links, undefined);
  assert.equal(payer.links.length, 1);
  const link = payer.links[0];
  const policyPackage = payer.build.packages.find(pkg => pkg.id === 'policy@1.0.0');
  assert.equal(link.name, 'Vault');
  assert.equal(link.kind, 'contract');
  assert.equal(link.package, 'policy@1.0.0');
  assert.equal(link.module, 'policy@1.0.0/escrow');
  assert.equal(link.packageDigest, policyPackage.treeDigest);
  assert.equal(link.root, vault.policy.root);
  assert.deepEqual(link.methods, [{ name: 'spend', leaf: vault.methods.find(method => method.name === 'spend').leaf }]);
  assert.ok(payer.methods.find(method => method.name === 'spend').scriptHex.includes(vault.policy.root));
  assert.ok(!JSON.stringify(payer).includes('OP_DEFINE') && !JSON.stringify(payer).includes('OP_INVOKE'));
  assert.equal(payer.build.packages.some(pkg => pkg.id === 'github.com/acme/lotus-std@v1.0.0'), true);

  const spend = payer.methods.find(method => method.name === 'spend');
  assert.ok(spend.staticResources.helperExpansions >= 2);
  assert.ok(spend.sourceMap.some(entry => entry.source.module === 'policy@1.0.0/escrow' && entry.expandedFrom));
  assert.ok(spend.sourceMap.some(entry => entry.source.module === 'github.com/acme/lotus-std@v1.0.0/mark' && entry.expandedFrom));
  const library = readFileSync(join(fixture, 'packages/policy/src/escrow.lotus'), 'utf8');
  const andAt = library.indexOf('checksig(s, a) && checksig(t, b)');
  const andEnd = andAt + 'checksig(s, a) && checksig(t, b)'.length;
  const overlapsAnd = span => span && span.start < andEnd && span.end > andAt;
  const fused = spend.sourceMap.filter(entry => entry.op === 'CHECKSIGVERIFY');
  assert.ok(fused.length >= 2);
  assert.ok(fused.every(entry => entry.expandedFrom && entry.source.module === 'policy@1.0.0/escrow'));
  assert.ok(fused.some(entry => overlapsAnd(entry.source) || entry.optimizedFrom?.some(item => overlapsAnd(item.source))));
  const controls = spend.sourceMap.filter(entry => entry.op === 'IF' || entry.op === 'ELSE' || entry.op === 'ENDIF');
  assert.ok(controls.some(entry => entry.op === 'IF'));
  assert.ok(controls.every(entry => entry.expandedFrom && entry.source.module === 'policy@1.0.0/escrow' && !overlapsAnd(entry.source)));

  assert.deepEqual(ops(payer, 'both'), ['N(1)', 'PICK', 'PUSH_32', 'CHECKSIGVERIFY', 'DUP', 'PUSH_32', 'CHECKSIGVERIFY', 'DROP', 'DROP', 'N(1)']);
  assert.equal(ops(payer, 'both').includes('IF'), false);
  assert.ok(ops(payer, 'alternate').includes('IF'));
  assert.equal(ops(payer, 'alternate').includes('CHECKSIGVERIFY'), false);

  const dir = join(base, 'project');
  cpSync(fixture, dir, { recursive: true });
  const helper = join(dir, 'packages/policy/src/escrow.lotus');
  const source = readFileSync(helper, 'utf8').replace('    return ok;\n', '    for input in tx.inputs { require(true); }\n    return ok;\n');
  writeFileSync(helper, source);
  const at = source.indexOf('for');
  process.env.PATH = bin;
  try {
    await assert.rejects(compilePackage(dir, { contract: 'Payer', bindings: { Vault: { owner: OWNER }, Payer: { a: key3, b: key4, owner: OWNER, vaultRoot: vault.policy.root, vaultLeaf: vault.methods[0].leaf } } }), error => {
      assert.ok(error instanceof CompileError);
      assert.equal(error.code, 'E0122');
      assert.equal(error.diagnostics[0].message, 'for is not allowed inside a helper');
      assert.equal(error.diagnostics[0].primary.file, 'packages/policy/src/escrow.lotus');
      assert.equal(error.diagnostics[0].primary.span.start, at);
      assert.equal(error.diagnostics[0].primary.span.end, at + 3);
      return true;
    });
  } finally {
    process.env.PATH = previous;
  }
  assert.equal(invoked(), '');
});
