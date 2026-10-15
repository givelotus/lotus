import test from 'node:test';
import assert from 'node:assert/strict';
import { cpSync, existsSync, mkdtempSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { pathToFileURL, fileURLToPath } from 'node:url';
import { schnorr } from '@noble/curves/secp256k1';
import ts from 'typescript';
import { hex, unhex } from '../dist/compiler.js';
import { compileContract } from '../dist/generic.js';
import { generateContractPython, generateContractTypeScript } from '../dist/bindings.js';
import { compilePackage, generateLock, updateLock } from '../dist/packages.js';
import { prepareContractCall } from '../dist/call-runtime.js';

const fixture = fileURLToPath(new URL('../examples/packages/linked/', import.meta.url));
const owner = '79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798';
const secret = unhex('00'.repeat(31) + '01');
const python = process.env.LOTUS_V2_PYTHON ?? 'python3';
const vmPackage = process.env.LOTUS_V2_VM_REFERENCE_PACKAGE ?? fileURLToPath(new URL('../../lotus-v2-reference/', import.meta.url));
const compilerRoot = fileURLToPath(new URL('../', import.meta.url));
const escrowBindings = { Escrow: { owner } };

function copy() {
  const base = mkdtempSync(join(tmpdir(), 'lotus-link-'));
  const dir = join(base, 'project');
  cpSync(fixture, dir, { recursive: true });
  return { base, dir };
}
function edit(dir, rel, change, relock = false) {
  const path = join(dir, rel);
  writeFileSync(path, change(readFileSync(path, 'utf8')));
  if (relock) updateLock(dir);
}
const escrowOnly = { contract: 'Escrow', bindings: escrowBindings };
async function build(dir, contract, extra) {
  return compilePackage(dir, { contract, bindings: { ...escrowBindings, ...extra } });
}
function flatEscrow() {
  return `function authorized(sig: Signature, owner: PublicKey): Bool { return checksig(sig, owner); }
contract Escrow<owner: PublicKey> {
    function spend(sig: Signature) { require(authorized(sig, owner)); require(1 == 1); }
    function refund(sig: Signature, tag: Bytes32) {
        require(authorized(sig, owner));
        require(blake3(tag) == blake3(tag));
        require(leaf_hash(Escrow.spend) == leaf_hash(Escrow.spend));
    }
}`;
}

test('two contracts link one library, inline its helper, and record its digest and root', async () => {
  assert.equal(hex(schnorr.getPublicKey(secret)), owner);
  assert.equal(generateLock(fixture), readFileSync(join(fixture, 'lotus.lock'), 'utf8'));
  const escrow = (await build(fixture, 'Escrow')).artifact;
  assert.equal(escrow.contract, 'Escrow');
  assert.equal(escrow.links, undefined);
  assert.equal(escrow.build.root.module, 'pay@0.1.0/main');
  const root = escrow.policy.root;
  const leaf = escrow.methods.find(m => m.name === 'spend').leaf;
  const payerBindings = { Payer: { owner, escrowRoot: root, escrowLeaf: leaf } };
  const receiverBindings = { Receiver: { owner, escrowRoot: root } };
  const payer = (await build(fixture, 'Payer', payerBindings)).artifact;
  const receiver = (await build(fixture, 'Receiver', receiverBindings)).artifact;
  const policy = payer.build.packages.find(p => p.id === 'policy@1.0.0');
  for (const artifact of [payer, receiver]) {
    assert.equal(artifact.links.length, 1);
    assert.equal(artifact.links[0].name, 'Escrow');
    assert.equal(artifact.links[0].kind, 'contract');
    assert.equal(artifact.links[0].package, 'policy@1.0.0');
    assert.equal(artifact.links[0].module, 'policy@1.0.0/escrow');
    assert.equal(artifact.links[0].packageDigest, policy.treeDigest);
    assert.equal(artifact.links[0].root, root);
    assert.deepEqual(artifact.links[0].methods.map(m => m.name), ['spend', 'refund']);
    assert.equal(artifact.links[0].methods[0].leaf, leaf);
    assert.ok(artifact.methods[0].scriptHex.includes(root));
    assert.equal(artifact.build.root.package, 'pay@0.1.0');
  }
  assert.equal(payer.links[0].packageDigest, receiver.links[0].packageDigest);
  assert.ok(!payer.links.some(link => link.name === 'Receiver'));
  const flatPayer = compileContract(`${flatEscrow()}
contract Payer<owner: PublicKey, escrowRoot: ContractRootHash, escrowLeaf: MethodLeafHash> {
    function spend(sig: Signature) {
        require(authorized(sig, owner));
        require(contract_root(Escrow) == escrowRoot);
        require(leaf_hash(Escrow.spend) == escrowLeaf);
    }
}`, { contract: 'Payer', bindings: { ...escrowBindings, ...payerBindings } });
  const flatReceiver = compileContract(`${flatEscrow()}
contract Receiver<owner: PublicKey, escrowRoot: ContractRootHash> {
    function spend(sig: Signature) {
        require(authorized(sig, owner));
        require(contract_root(Escrow) == escrowRoot);
        require(merkle_root(Escrow) == escrowRoot);
    }
}`, { contract: 'Receiver', bindings: { ...escrowBindings, ...receiverBindings } });
  assert.equal(payer.methods[0].scriptHex, flatPayer.methods[0].scriptHex);
  assert.equal(payer.policy.root, flatPayer.policy.root);
  assert.equal(receiver.methods[0].scriptHex, flatReceiver.methods[0].scriptHex);
  assert.equal(receiver.policy.root, flatReceiver.policy.root);
  assert.equal(flatPayer.build, undefined);
  assert.ok(payer.methods[0].staticResources.helperExpansions >= 1);
  const mentionsLibrary = entry => entry?.module === 'policy@1.0.0/escrow';
  assert.ok(payer.methods[0].sourceMap.some(entry => mentionsLibrary(entry.source) || mentionsLibrary(entry.expandedFrom) || entry.optimizedFrom?.some(item => mentionsLibrary(item.source) || mentionsLibrary(item.expandedFrom))));
  const schemaProbe = spawnSync(python, ['-c', 'import jsonschema'], { encoding: 'utf8' });
  if (schemaProbe.status === 0) {
    const schema = JSON.parse(readFileSync(new URL('../artifact-v2.schema.json', import.meta.url), 'utf8'));
    const script = 'import json, sys\nfrom jsonschema import Draft202012Validator\ncase = json.load(sys.stdin)\nDraft202012Validator.check_schema(case[0])\nfor artifact in case[1:]:\n    Draft202012Validator(case[0]).validate(artifact)\n';
    const run = spawnSync(python, ['-c', script], { input: JSON.stringify([schema, payer, receiver, escrow]), encoding: 'utf8' });
    assert.equal(run.status, 0, run.stderr);
  }
  const exported = payer.build.modules.find(m => m.id === 'policy@1.0.0/escrow').exports.map(item => item.name);
  assert.deepEqual(exported, ['authorized', 'Escrow']);
  assert.ok(exported.every(name => name === 'authorized' || name === 'Escrow'));
});

test('a semantic library byte changes the linked root; a comment does not; a stale lock fails', async () => {
  const { dir } = copy();
  const escrow = (await build(dir, 'Escrow')).artifact;
  const payerBindings = { Payer: { owner, escrowRoot: escrow.policy.root, escrowLeaf: escrow.methods[0].leaf } };
  const before = (await build(dir, 'Payer', payerBindings)).artifact;
  const file = 'packages/policy/src/escrow.lotus';
  edit(dir, file, s => s.replace('// Shared escrow', '// shared escrow'));
  await assert.rejects(compilePackage(dir, { contract: 'Payer', bindings: { ...escrowBindings, ...payerBindings } }), error => {
    assert.equal(error.code, 'lock-mismatch');
    assert.equal(error.file, file);
    return true;
  });
  updateLock(dir);
  const commentEscrow = (await build(dir, 'Escrow')).artifact;
  const comment = (await build(dir, 'Payer', payerBindings)).artifact;
  const digest = artifact => artifact.build.modules.find(m => m.id === 'policy@1.0.0/escrow').sourceDigest;
  assert.notEqual(digest(comment), digest(before));
  assert.notEqual(comment.build.lockDigest, before.build.lockDigest);
  assert.notEqual(comment.links[0].packageDigest, before.links[0].packageDigest);
  assert.equal(commentEscrow.policy.root, escrow.policy.root);
  assert.equal(comment.links[0].root, before.links[0].root);
  assert.equal(comment.policy.root, before.policy.root);
  edit(dir, file, s => s.replace('require(1 == 1);', 'require(2 == 1);'));
  await assert.rejects(compilePackage(dir, escrowOnly), error => error.code === 'lock-mismatch');
  updateLock(dir);
  const changedEscrow = (await build(dir, 'Escrow')).artifact;
  assert.notEqual(changedEscrow.policy.root, escrow.policy.root);
  const changedBindings = { Payer: { owner, escrowRoot: changedEscrow.policy.root, escrowLeaf: changedEscrow.methods.find(m => m.name === 'spend').leaf } };
  const changed = (await build(dir, 'Payer', changedBindings)).artifact;
  assert.notEqual(changed.links[0].root, before.links[0].root);
  assert.equal(changed.links[0].root, changedEscrow.policy.root);
  assert.notEqual(changed.policy.root, before.policy.root);
  assert.notEqual(changed.methods[0].scriptHex, before.methods[0].scriptHex);
  assert.ok(changed.methods[0].scriptHex.includes(changedEscrow.policy.root));
});

test('private and package-scoped library names are not importable, and recursion still rejects', async () => {
  const file = 'src/main.lotus';
  const cases = [
    [file, s => s.replace('import policy::', 'import policy::escrow::{Hidden};\nimport policy::'), 'visibility'],
    [file, s => s.replace('import policy::', 'import policy::escrow::{privateNote};\nimport policy::'), 'visibility'],
    [file, s => s.replace('import policy::', 'import policy::escrow::{Sibling};\nimport policy::'), 'visibility'],
    [file, s => s.replace('require(authorized(sig, owner));', 'require(escrow::privateNote(true));'), 'visibility'],
    [file, s => s.replace('require(authorized(sig, owner));', 'require(Escrow(sig));'), 'missing-symbol'],
    [file, s => s.replace('contract Payer', 'contract Escrow { function spend(sig: Signature) { require(true); } }\ncontract Payer'), 'duplicate-name'],
  ];
  for (const [rel, change, code] of cases) {
    const { dir } = copy();
    edit(dir, rel, change, true);
    await assert.rejects(compilePackage(dir, escrowOnly), error => {
      assert.equal(error.code, code, error.message);
      assert.equal(error.file, rel);
      return true;
    });
  }
  const { dir } = copy();
  edit(dir, 'packages/policy/src/escrow.lotus', s => s.replace(
    'return checksig(sig, owner);',
    'return loop(checksig(sig, owner));',
  ) + '\nexport function loop(x: Bool): Bool { return loop(x); }\n', true);
  await assert.rejects(compilePackage(dir, escrowOnly), error => {
    assert.match(error.message, /recursive helper/);
    return true;
  });
});

test('generated clients dump the linked contract root and method names', async () => {
  const escrow = (await build(fixture, 'Escrow')).artifact;
  const bindings = { Payer: { owner, escrowRoot: escrow.policy.root, escrowLeaf: escrow.methods.find(m => m.name === 'spend').leaf } };
  const payer = (await build(fixture, 'Payer', bindings)).artifact;
  const typescript = generateContractTypeScript(payer);
  const pythonSource = generateContractPython(payer);
  assert.equal(typescript, generateContractTypeScript(payer));
  assert.equal(pythonSource, generateContractPython(payer));
  assert.match(typescript, new RegExp(`name: 'Escrow'.*packageDigest: '${payer.links[0].packageDigest}'.*root: '${escrow.policy.root}'.*methods: \\['spend', 'refund'\\]`, 's'));
  assert.match(pythonSource, new RegExp(`"name": "Escrow".*"package_digest": "${payer.links[0].packageDigest}".*"root": "${escrow.policy.root}".*"methods": \\("spend", "refund",\\)`, 's'));
  const base = mkdtempSync(join(tmpdir(), 'lotus-link-cli-'));
  const options = join(base, 'options.json');
  writeFileSync(options, JSON.stringify({ contract: 'Payer', bindings: { ...escrowBindings, ...bindings } }));
  const out = join(base, 'out');
  const cli = spawnSync(process.execPath, [join(compilerRoot, 'dist/generic-cli.js'), '--package', fixture, options, out], { encoding: 'utf8' });
  assert.equal(cli.status, 0, cli.stderr);
  assert.equal(readFileSync(join(out, 'Payer.ts'), 'utf8'), typescript);
  assert.equal(readFileSync(join(out, 'Payer.py'), 'utf8'), pythonSource);
  const javascript = ts.transpileModule(typescript, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext } }).outputText;
  const modulePath = fileURLToPath(new URL('./GeneratedLinkedPayer.mjs', import.meta.url));
  writeFileSync(modulePath, javascript);
  try {
    const loaded = await import(`${pathToFileURL(modulePath).href}?run=${Date.now()}`);
    assert.equal(loaded.linkedContracts[0].root, escrow.policy.root);
    assert.deepEqual([...loaded.linkedContracts[0].methods], ['spend', 'refund']);
  } finally { rmSync(modulePath, { force: true }); }
  const probe = spawnSync(python, ['-c', 'import blake3'], { encoding: 'utf8' });
  if (probe.status === 0) {
    const pyPath = join(out, 'Payer.py');
    const run = spawnSync(python, ['-c', `import importlib.util\nspec = importlib.util.spec_from_file_location("payer", ${JSON.stringify(pyPath)})\nmod = importlib.util.module_from_spec(spec)\nspec.loader.exec_module(mod)\nitem = mod.LINKED_CONTRACTS[0]\nprint(item["root"])\nprint(",".join(item["methods"]))`], {
      encoding: 'utf8', env: { ...process.env, PYTHONPATH: join(compilerRoot, 'python') },
    });
    assert.equal(run.status, 0, run.stderr);
    assert.equal(run.stdout, `${escrow.policy.root}\nspend,refund\n`);
  }
});

test('an exported library token links as a TokenId commitment', async () => {
  const base = mkdtempSync(join(tmpdir(), 'lotus-token-link-'));
  const dir = join(base, 'project');
  mkdirSync(join(dir, 'src'), { recursive: true });
  mkdirSync(join(dir, 'packages/policy/src'), { recursive: true });
  writeFileSync(join(dir, 'lotus.toml'), `[package]
name = "pay"
version = "0.1.0"
kind = "contract"
source = "src"
entry = "main"
modules = ["main"]

[dependencies]
policy = "policy@1.0.0"

[sources]
policy = "packages/policy"
`);
  writeFileSync(join(dir, 'packages/policy/lotus.toml'), `[package]
name = "policy"
version = "1.0.0"
kind = "library"
source = "src"
modules = ["badge"]
exports = ["badge"]
`);
  writeFileSync(join(dir, 'packages/policy/src/badge.lotus'), `export token Badge<issuer: PublicKey> {
    function issue(amount: Amount, sig: Signature) { require(checksig(sig, issuer)); }
}
`);
  writeFileSync(join(dir, 'src/main.lotus'), `import policy::badge::{Badge};
contract Gate<id: TokenId> {
    function enter() { require(contract_root(Badge) == id); }
}
`);
  updateLock(dir);
  const badge = (await compilePackage(dir, { contract: 'Badge', bindings: { Badge: { issuer: owner } } })).artifact;
  assert.equal(badge.kind, 'token');
  const gate = (await compilePackage(dir, { contract: 'Gate', bindings: { Badge: { issuer: owner }, Gate: { id: badge.policy.root } } })).artifact;
  assert.equal(gate.links.length, 1);
  assert.equal(gate.links[0].kind, 'token');
  assert.equal(gate.links[0].name, 'Badge');
  assert.equal(gate.links[0].root, badge.policy.root);
  assert.deepEqual(gate.links[0].methods.map(m => m.name), ['issue']);
  assert.ok(gate.methods[0].scriptHex.includes(badge.policy.root));
});

function vmProfile() {
  const opcodeCosts = {};
  for (const [lo, hi] of [[0x00, 0x5d], [0x60, 0x6b], [0x70, 0x81], [0x88, 0x94], [0x98, 0xb4], [0xb8, 0xc2], [0xc8, 0xdd], [0xe0, 0xea], [0xf0, 0xf4]]) {
    for (let op = lo; op <= hi; op++) opcodeCosts[op.toString(16).padStart(2, '0')] = (op === 0xbb || op === 0xbc) ? 1000 : 1;
  }
  return { max_script_bytes: 8192, max_arguments: 16, max_element_bytes: 8192, max_stack_items: 128,
    max_altstack_items: 64, max_vm_bytes: 65536, max_ast_depth: 32, max_invocation_cost: 1000000,
    structural_byte_cost: 1, opcode_costs: opcodeCosts };
}
function callContext(artifact) {
  const output = { value: 1000n, branches: [artifact.policy.root], paths: [[0]] };
  return { profile: artifact.target, chainId: '44'.repeat(32), prevTxid: '11'.repeat(32), prevIndex: 0,
    sequence: 0xffffffff, coin: { value: 2000n, branches: [artifact.policy.root], paths: [[0]] }, outputs: [output] };
}
function signed(artifact, method) {
  const plan = prepareContractCall(artifact, method, callContext(artifact), { sig: null });
  const signature = schnorr.sign(unhex(plan.requests[0].digest), secret, new Uint8Array(32));
  return { plan, signature: hex(signature) };
}
function invoke(method, args, signing) {
  const run = spawnSync(python, ['-m', 'lotus_v2_reference.vm_runner'], {
    input: JSON.stringify({ script: method.scriptHex, args, input_count: 1, output_count: 1, profile: vmProfile(), ...(signing ? { signing } : {}) }),
    encoding: 'utf8', env: { ...process.env, PYTHONPATH: vmPackage },
  });
  assert.ok(run.stdout, run.stderr);
  return JSON.parse(run.stdout);
}

test('Python reference VM executes signed linked calls; native CHECKSIG is not a signing runner', async t => {
  const probe = spawnSync(python, ['-c', 'import blake3, coincurve, lotus_v2_reference.vm_runner'], {
    encoding: 'utf8', env: { ...process.env, PYTHONPATH: vmPackage },
  });
  const escrow = (await build(fixture, 'Escrow')).artifact;
  const leaf = escrow.methods.find(m => m.name === 'spend').leaf;
  const payer = (await build(fixture, 'Payer', { Payer: { owner, escrowRoot: escrow.policy.root, escrowLeaf: leaf } })).artifact;
  const receiver = (await build(fixture, 'Receiver', { Receiver: { owner, escrowRoot: escrow.policy.root } })).artifact;
  if (probe.status !== 0) {
    t.diagnostic(`Python reference VM was not run (${probe.stderr.trim() || 'import failed'})`);
  } else {
    const spend = escrow.methods.find(m => m.name === 'spend');
    const good = signed(escrow, 'spend');
    const signing = { selected_leaf_hash: spend.leaf, messages: { 0: good.plan.requests[0].digest }, invocation_kind: 'spend', input_index: 0, output_count: 1 };
    const accepted = invoke(spend, [good.signature], signing);
    assert.equal(accepted.accepted_invocation, true, JSON.stringify(accepted));
    const badSig = `${good.signature.slice(0, 2) === '00' ? '01' : '00'}${good.signature.slice(2)}`;
    const rejected = invoke(spend, [badSig], signing);
    assert.equal(rejected.accepted_invocation, false, JSON.stringify(rejected));
    for (const artifact of [payer, receiver]) {
      const method = artifact.methods[0];
      const call = signed(artifact, 'spend');
      const context = { selected_leaf_hash: method.leaf, messages: { 0: call.plan.requests[0].digest }, invocation_kind: 'spend', input_index: 0, output_count: 1 };
      const ok = invoke(method, [call.signature], context);
      assert.equal(ok.accepted_invocation, true, `${artifact.contract} ${JSON.stringify(ok)}`);
    }
    const wrongRoot = escrow.policy.root.replace(/^../, escrow.policy.root.startsWith('00') ? '11' : '00');
    const wrong = (await build(fixture, 'Payer', { Payer: { owner, escrowRoot: wrongRoot, escrowLeaf: leaf } })).artifact;
    const wrongCall = signed(wrong, 'spend');
    const wrongResult = invoke(wrong.methods[0], [wrongCall.signature], {
      selected_leaf_hash: wrong.methods[0].leaf, messages: { 0: wrongCall.plan.requests[0].digest },
      invocation_kind: 'spend', input_index: 0, output_count: 1,
    });
    assert.equal(wrongResult.accepted_invocation, false, JSON.stringify(wrongResult));
    t.diagnostic('Python reference VM executed the signed Escrow, Payer and Receiver calls');
  }
  const native = process.env.LOTUS_V2_NATIVE_VM;
  if (!native || !existsSync(native)) {
    t.diagnostic('Native signed execution was not run (LOTUS_V2_NATIVE_VM unset)');
    return;
  }
  const call = signed(escrow, 'spend');
  const run = spawnSync(native, [escrow.methods.find(m => m.name === 'spend').scriptHex, '1', '1', call.signature], { encoding: 'utf8' });
  const status = (run.stdout || '').trim().slice(0, 1);
  if (status === 'I') assert.fail(`native VM rejected a valid signature: ${run.stdout} ${run.stderr}`);
  if (status === 'S' || status === 'A') t.diagnostic('Native VM executed and accepted the signed Escrow spend');
  else t.diagnostic(`Native signed execution was not performed (runner status ${status || run.status}; this CLI has no signing context)`);
});
