import test from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { cpSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { compileContract } from '../dist/generic.js';
import { compilePackage, updateLock } from '../dist/packages.js';
import { CompileError, DIAGNOSTICS_SCHEMA, diagnosticsJson, shouldColor } from '../dist/diagnostics.js';

const key = 'f9308a019258c31049344f85f89d5229b531c845836f99b08601f113bce036f9';
const dist = fileURLToPath(new URL('../dist/', import.meta.url));
const diamond = fileURLToPath(new URL('../examples/packages/diamond/', import.meta.url));
const packageOptions = JSON.parse(readFileSync(join(diamond, 'options.json'), 'utf8'));

function fail(source, options = { contract: 'C', bindings: {} }, file) {
  try {
    compileContract(source, options, file);
  } catch (error) {
    return error;
  }
  assert.fail('compile succeeded');
}

test('parse errors report a 1-based line and column with a caret', () => {
  const source = 'contract C {\n  function m() {\n    require(true)\n  }\n}\n';
  const error = fail(source);
  assert.ok(error instanceof CompileError);
  assert.match(error.message, /^<source>:4:3: error\[E0101\]: expected ;/);
  const text = error.render();
  assert.match(text, /<source>:4:3: error\[E0101\]: expected ;/);
  assert.match(text, /4 \| {3}\}/);
  assert.match(text, /\^ expected ;|\^/);
  const caret = text.split('\n').find(line => line.includes('^'));
  assert.ok(caret);
  assert.equal(caret.indexOf('^'), caret.indexOf('|') + 1 + 3);
});

test('a multi-byte character uses a Unicode scalar column and an exclusive byte end', () => {
  const prefix = 'contract C { function m() { require(';
  const source = `${prefix}é); } }`;
  const error = fail(source);
  assert.ok(error instanceof CompileError);
  const primary = error.toJSON()[0].primary;
  assert.equal(primary.file, '<source>');
  assert.equal(primary.line, 1);
  assert.equal(primary.start, Buffer.byteLength(prefix));
  assert.equal(primary.end - primary.start, 2);
  assert.equal(primary.column, prefix.length + 1);
  assert.equal(primary.endColumn - primary.column, 1);
  assert.match(error.message, new RegExp(`^<source>:1:${prefix.length + 1}: error\\[E0001\\]`));
  assert.match(error.render(), /\^/);
});

test('an unbound name suggests the closest in-scope binding', () => {
  const source = 'contract Pay<owner: PublicKey> { function spend(sig: Signature) { require(checksig(sig, oner)); } }';
  const error = fail(source, { contract: 'Pay', bindings: { Pay: { owner: key } } });
  assert.ok(error instanceof CompileError);
  assert.equal(error.diagnostics[0].code, 'E0301');
  assert.match(error.diagnostics[0].message, /unbound name oner/);
  assert.equal(error.diagnostics[0].help, "did you mean 'owner'?");
  assert.match(error.render(), /help: did you mean 'owner'\?/);
  const named = fail('contract {', { contract: 'C', bindings: {} }, 'vault.lotus');
  assert.match(named.message, /^vault\.lotus:1:10: error\[E0102\]/);
});

test('an error inside an inlined imported helper names the helper file and the call chain', async () => {
  const base = mkdtempSync(join(tmpdir(), 'lotus-diag-pkg-'));
  const dir = join(base, 'project');
  cpSync(diamond, dir, { recursive: true });
  const helper = join(dir, 'packages/core/src/internal.lotus');
  writeFileSync(helper, readFileSync(helper, 'utf8').replace('return x >= 0;', 'return x >= missing;'));
  updateLock(dir);
  try {
    await assert.rejects(compilePackage(dir, packageOptions), error => {
      assert.ok(error instanceof CompileError, error);
      const text = error.render();
      const primary = error.toJSON()[0].primary;
      assert.equal(primary.file, 'packages/core/src/internal.lotus');
      assert.equal(primary.line, 3);
      assert.match(error.message, /^packages\/core\/src\/internal\.lotus:3:\d+: error\[E0301\]: unbound name missing/);
      assert.match(text, /packages\/core\/src\/internal\.lotus:3:\d+: error\[E0301\]: unbound name missing/);
      const direct = error.diagnostics[0].related.find(note => note.message === 'in expansion of helper core@1.0.0/internal::nonNegative called here');
      assert.ok(direct, text);
      assert.equal(direct.file, 'packages/core/src/amounts.lotus');
      assert.ok(error.diagnostics[0].related.some(note => note.file === 'src/main.lotus' && note.message === 'in expansion of helper lib_a@1.0.0/limits::withinBudget called here'));
      assert.match(text, /src\/main\.lotus:\d+:\d+/);
      assert.match(text, /in expansion of helper core@1\.0\.0\/internal::nonNegative called here/);
      assert.ok(error.diagnostics[0].related.length <= 16);
      return true;
    });
  } finally { rmSync(base, { recursive: true, force: true }); }
});

test('recovery stops at 20 diagnostics and keeps the first', () => {
  const body = Array.from({ length: 25 }, (_, i) => `require(n${String(i).padStart(2, '0')});`).join(' ');
  const error = fail(`contract C { function m() { ${body} } }`);
  assert.ok(error instanceof CompileError);
  assert.equal(error.diagnostics.length, 20);
  assert.match(error.diagnostics[0].message, /unbound name n00/);
  assert.ok(error.diagnostics.every(d => !/unbound name n2[0-4]/.test(d.message)));
  assert.match(error.message, /and 19 more errors/);
  assert.doesNotMatch(error.message, /unbound name n20/);
});

test('JSON diagnostics use schema lotus-v2/diagnostics/1 and byte offsets', () => {
  const error = fail('contract C { function m() { require(true) } }');
  assert.ok(error instanceof CompileError);
  const doc = JSON.parse(diagnosticsJson(error.diagnostics, error.sources));
  assert.equal(doc.schema, DIAGNOSTICS_SCHEMA);
  assert.equal(doc.schema, 'lotus-v2/diagnostics/1');
  const d = doc.diagnostics[0];
  for (const key of ['severity', 'code', 'message', 'primary', 'labels', 'notes', 'help', 'related']) assert.ok(Object.hasOwn(d, key));
  assert.equal(d.severity, 'error');
  assert.match(d.code, /^E\d{4}$/);
  assert.equal(d.primary.file, '<source>');
  assert.equal(typeof d.primary.start, 'number');
  assert.equal(typeof d.primary.end, 'number');
  assert.ok(d.primary.end > d.primary.start);
  assert.equal(d.primary.line, 1);
  assert.equal(typeof d.primary.column, 'number');
  assert.equal(typeof d.primary.endColumn, 'number');
  assert.equal(JSON.stringify(error.toJSON()), JSON.stringify(doc.diagnostics));
});

test('existing payment and diamond artifacts keep script bytes and source maps', async () => {
  const fixture = JSON.parse(readFileSync(new URL('../fixtures/generic-payment-v2.json', import.meta.url), 'utf8'));
  const artifact = compileContract(fixture.source, { contract: 'Payment', bindings: { Payment: { owner: fixture.artifact.bindings[0].value } } });
  assert.equal(artifact.methods[0].scriptHex, fixture.artifact.methods[0].scriptHex);
  assert.equal(JSON.stringify(artifact.methods[0].sourceMap), JSON.stringify(fixture.artifact.methods[0].sourceMap));
  assert.equal(JSON.stringify(artifact.methods[0].sourceMap).includes('"file"'), false);
  const { artifact: packaged } = await compilePackage(diamond, packageOptions);
  const golden = JSON.parse(readFileSync(join(diamond, 'expected-artifact.json'), 'utf8'));
  assert.equal(JSON.stringify(packaged.methods), JSON.stringify(golden.methods));
  for (const method of packaged.methods) assert.equal(JSON.stringify(method.sourceMap).includes('"file"'), false);
});

test('CLI colour follows NO_COLOR, FORCE_COLOR and TTY', () => {
  assert.equal(shouldColor({ isTTY: true }, {}), true);
  assert.equal(shouldColor({ isTTY: true }, { NO_COLOR: '1' }), false);
  assert.equal(shouldColor({ isTTY: false }, { FORCE_COLOR: '1' }), true);
  assert.equal(shouldColor({ isTTY: false }, { FORCE_COLOR: '0' }), false);
  assert.equal(shouldColor({ isTTY: false }, {}), false);
  const dir = mkdtempSync(join(tmpdir(), 'lotus-diag-cli-'));
  try {
    const source = join(dir, 'bad.lotus');
    writeFileSync(source, 'contract C { function m() { require(true) } }\n');
    writeFileSync(join(dir, 'options.json'), JSON.stringify({ contract: 'C', bindings: {} }));
    const env = { ...process.env, NO_COLOR: '1' };
    delete env.FORCE_COLOR;
    const run = spawnSync(process.execPath, [join(dist, 'generic-cli.js'), source, join(dir, 'options.json'), join(dir, 'out')], { encoding: 'utf8', env });
    assert.notEqual(run.status, 0);
    assert.match(run.stderr, /bad\.lotus:\d+:\d+: error\[E0101\]/);
    assert.match(run.stderr, /\^/);
    assert.equal(run.stderr.includes('\u001b'), false);
  } finally { rmSync(dir, { recursive: true, force: true }); }
});
