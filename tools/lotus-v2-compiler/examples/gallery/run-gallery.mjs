#!/usr/bin/env node
import { readFileSync, mkdirSync, writeFileSync, existsSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import { blake3 } from '@noble/hashes/blake3';
import { schnorr } from '@noble/curves/secp256k1';
import { compileContract } from '../../dist/generic.js';

const here = dirname(fileURLToPath(import.meta.url));
const out = process.argv[2];
if (!out) throw new Error('usage: node examples/gallery/run-gallery.mjs OUTPUT_DIR [VM_REFERENCE_PACKAGE]');
mkdirSync(out, { recursive: true });
const owner3 = 'f9308a019258c31049344f85f89d5229b531c845836f99b08601f113bce036f9';
const owner4 = 'e493dbf1c10d80f3581e4904930b1404cc6c13900ee0758474fa94abe8c4cd13';
const preimage = Buffer.alloc(32);
preimage.set(Buffer.from('lotus gallery', 'utf8'));
const digest = Buffer.from((await import('node:crypto')).createHash('sha256').update(preimage).digest()).toString('hex');
const read = name => readFileSync(join(here, `${name}.lotus`), 'utf8');
const hex = data => Buffer.from(data).toString('hex');
const tag = (name, data) => blake3(Buffer.concat([Buffer.from(`Lotus/v2/${name}\0`), data]));
const compactSize = n => n < 253 ? Buffer.from([n]) : n <= 65535 ? Buffer.from([253, n & 255, n >> 8]) : (() => { throw new Error('gallery script too large'); })();
function compareLE(a, b) { for (let i = 31; i >= 0; i--) if (a[i] !== b[i]) return a[i] - b[i]; return 0; }
function checkMethod(method, root) {
  const script = Buffer.from(method.scriptHex, 'hex');
  const leaf = tag('branch', Buffer.concat([Buffer.from([0]), compactSize(script.length), script]));
  if (hex(leaf) !== method.leaf) throw new Error(`${method.name}: leaf mismatch`);
  let current = leaf;
  for (const siblingHex of method.proof) {
    const sibling = Buffer.from(siblingHex, 'hex');
    if (sibling.length !== 32) throw new Error(`${method.name}: proof sibling width`);
    const [a, b] = compareLE(current, sibling) <= 0 ? [current, sibling] : [sibling, current];
    current = tag('branch', Buffer.concat([Buffer.from([1]), a, b]));
  }
  if (hex(current) !== root) throw new Error(`${method.name}: proof root mismatch`);
}
function compile(name, sourceName, contract, bindings) {
  const artifact = compileContract(read(sourceName), { contract, bindings });
  if (artifact.policy.root !== artifact.policy.branches[0]) throw new Error(`${name}: output branch root mismatch`);
  for (const method of artifact.methods) checkMethod(method, artifact.policy.root);
  writeFileSync(join(out, `${name}.json`), JSON.stringify(artifact, null, 2) + '\n');
  return artifact;
}

const results = {};
results.payment = compile('payment', 'payment', 'Payment', { Payment: { owner: owner3 } });
results.twoKey = compile('two-key', 'two-key', 'TwoKey', { TwoKey: { alice: owner3, bob: owner4 } });
results.hashlock = compile('hashlock', 'hashlock', 'Hashlock', { Hashlock: { digest } });
results.signedHashlock = compile('signed-hashlock', 'signed-hashlock', 'SignedHashlock', { SignedHashlock: { owner: owner3, digest } });
results.recovery = compile('recovery', 'recovery', 'Recovery', { Recovery: { owner: owner3, guardian: owner4 } });
results.helper = compile('helper', 'helper', 'HelperVault', { HelperVault: { digest } });
const target = compile('linked-target', 'linked', 'LinkedTarget', { LinkedTarget: { owner: owner3 } });
results.linked = compile('linked-verifier', 'linked', 'LinkedVerifier', {
  LinkedTarget: { owner: owner3 }, LinkedVerifier: { expectedRoot: target.policy.root, expectedLeaf: target.methods[0].leaf },
});

const changedPayment = compileContract(read('payment'), { contract: 'Payment', bindings: { Payment: { owner: owner4 } } });
if (changedPayment.policy.root === results.payment.policy.root) throw new Error('changed template key did not change root');
const changedTarget = compileContract(read('linked'), { contract: 'LinkedTarget', bindings: { LinkedTarget: { owner: owner4 } } });
if (changedTarget.policy.root === target.policy.root) throw new Error('linked target root did not change');
const changedLink = compileContract(read('linked'), { contract: 'LinkedVerifier', bindings: {
  LinkedTarget: { owner: owner4 }, LinkedVerifier: { expectedRoot: changedTarget.policy.root, expectedLeaf: changedTarget.methods[0].leaf },
} });
if (changedLink.policy.root === results.linked.policy.root) throw new Error('linked commitment did not change with target');

const fixturePath = join(here, '../../fixtures/generic-payment-v2.json');
let paymentEvidence;
if (existsSync(fixturePath)) {
  const fixture = JSON.parse(readFileSync(fixturePath, 'utf8'));
  const method = results.payment.methods[0];
  if (fixture.artifact.methods[0].scriptHex !== method.scriptHex || fixture.valid.leaf !== method.leaf ||
      fixture.context.coin.branches[0] !== results.payment.policy.root) throw new Error('signed generic Payment fixture uses a different compiler artifact');
  const { prepareContractCall, finalizeContractCall } = await import('../../dist/call-runtime.js');
  const coin = o => ({ value: BigInt(o.valueAtoms), branches: o.branches, paths: o.paths });
  const context = { profile: fixture.context.profile, chainId: fixture.context.chainId, prevTxid: fixture.context.prevTxid,
    prevIndex: fixture.context.prevIndex, sequence: fixture.context.sequence, coin: coin(fixture.context.coin),
    outputs: fixture.context.outputs.map(coin) };
  const plan = prepareContractCall(results.payment, 'spend', context, { signature: null });
  const final = finalizeContractCall(plan, { signature: Buffer.from(fixture.valid.signature, 'hex') });
  if (plan.requests[0].digest !== fixture.valid.message || plan.requests[0].leaf !== method.leaf ||
      hex(final.wire) !== fixture.valid.wire || final.txid !== fixture.valid.txid || final.txhash !== fixture.valid.txhash)
    throw new Error('signed generic Payment fixture framing or commitments mismatch');
  if (!schnorr.verify(Buffer.from(fixture.valid.signature, 'hex'), Buffer.from(fixture.valid.message, 'hex'), Buffer.from(owner3, 'hex')))
    throw new Error('signed generic Payment fixture signature mismatch');
  paymentEvidence = { wire: fixture.valid.wire, txid: final.txid, txhash: final.txhash,
    signingMessage: fixture.valid.message, signature: fixture.valid.signature, feeAtoms: plan.requests[0].feeAtoms.toString() };
}

const localVmPackage = join(here, '../../../../tools/lotus-v2-reference');
const vmPackage = process.env.LOTUS_V2_SKIP_VM === '1' ? undefined :
  process.argv[3] ?? (existsSync(join(localVmPackage, 'lotus_v2_reference', 'vm_runner.py')) ? localVmPackage : undefined);
const vmResults = {};
if (vmPackage) {
  if (!existsSync(join(vmPackage, 'lotus_v2_reference', 'vm_runner.py'))) throw new Error('VM_REFERENCE_PACKAGE does not contain vm_runner.py');
  const assigned = [[0x00,0x5d],[0x60,0x6b],[0x70,0x81],[0x88,0x94],[0x98,0xb4],[0xb8,0xc2],[0xc8,0xdd],[0xe0,0xea],[0xf0,0xf4]];
  const opcodeCosts = {};
  for (const [first,last] of assigned) for (let op = first; op <= last; op++) opcodeCosts[op.toString(16).padStart(2,'0')] = op === 0xbb ? 1000 : 1;
  const profile = { max_script_bytes: 8192, max_arguments: 16, max_element_bytes: 8192, max_stack_items: 128,
    max_altstack_items: 64, max_vm_bytes: 65536, max_ast_depth: 32, max_invocation_cost: 1000000,
    structural_byte_cost: 1, opcode_costs: opcodeCosts };
  function invoke(method, args, signing) {
    const invocation = { script: method.scriptHex, args, input_count: 1, output_count: 1, profile, ...(signing ? { signing } : {}) };
    const run = spawnSync(process.env.LOTUS_V2_PYTHON || 'python3', ['-m', 'lotus_v2_reference.vm_runner'], {
      input: JSON.stringify(invocation), encoding: 'utf8', env: { ...process.env, PYTHONPATH: vmPackage },
    });
    if (!run.stdout) throw new Error(`VM runner failed: ${run.stderr}`);
    return JSON.parse(run.stdout);
  }
  for (const name of ['hashlock','helper']) {
    const method = results[name].methods[0];
    const positive = invoke(method, [hex(preimage)]);
    const bad = Buffer.from(preimage); bad[0] ^= 1;
    const negative = invoke(method, [hex(bad)]);
    if (!positive.accepted_invocation || negative.accepted_invocation) throw new Error(`${name}: VM acceptance mismatch: ${JSON.stringify({positive,negative})}`);
    vmResults[name] = { positive, negative };
  }
  const linkedPositive = invoke(results.linked.methods[0], []);
  if (!linkedPositive.accepted_invocation) throw new Error(`linked: VM acceptance mismatch: ${JSON.stringify(linkedPositive)}`);
  vmResults.linked = { positive: linkedPositive };
  if (paymentEvidence) {
    const method = results.payment.methods[0];
    const signing = { selected_leaf_hash: method.leaf, messages: { 0: paymentEvidence.signingMessage },
      invocation_kind: 'spend', input_index: 0, output_count: 1 };
    const positive = invoke(method, [paymentEvidence.signature], signing);
    const bad = Buffer.from(paymentEvidence.signature, 'hex'); bad[0] ^= 1;
    const negative = invoke(method, [hex(bad)], signing);
    if (!positive.accepted_invocation || negative.accepted_invocation) throw new Error(`payment: VM signature acceptance mismatch: ${JSON.stringify({positive,negative})}`);
    vmResults.payment = { positive, negative };
  }
}

const summary = {
  schema: 'lotus-v2/compiler-gallery-summary/1', target: results.payment.target,
  samplePreimageHex: hex(preimage), sampleSha256Hex: digest,
  examples: Object.entries(results).map(([name, artifact]) => ({ name, artifact: `${name === 'twoKey' ? 'two-key' : name === 'signedHashlock' ? 'signed-hashlock' : name === 'linked' ? 'linked-verifier' : name === 'recovery' ? 'recovery' : name === 'helper' ? 'helper' : name === 'hashlock' ? 'hashlock' : 'payment'}.json`, root: artifact.policy.root,
    methods: artifact.methods.map(m => ({ name: m.name, scriptHex: m.scriptHex, leaf: m.leaf, proof: m.proof, staticResources: m.staticResources })),
    stages: { compile: 'passed', proof: 'passed', transactionFraming: name === 'payment' && paymentEvidence ? 'passed' : 'unavailable',
      signature: name === 'payment' && paymentEvidence ? 'passed' : 'unavailable', vm: vmResults[name] ? 'passed' : 'unavailable',
      accounting: 'unavailable', block: 'unavailable' } })),
  checks: { templateKeyChangesRoot: true, linkedTargetChangesRoot: true },
  payment: paymentEvidence ?? null,
  vm: vmResults,
  limitations: ['No state, token mint, relative lock, or complete block validation in this compiler slice.', 'A linked constant comparison commits to known bytes; it does not enforce execution of the referenced contract.', 'VM execution is one invocation with caller-supplied signing digest, not a full transaction or block verdict.'],
};
writeFileSync(join(out, 'summary.json'), JSON.stringify(summary, null, 2) + '\n');
console.log(JSON.stringify(summary, null, 2));
