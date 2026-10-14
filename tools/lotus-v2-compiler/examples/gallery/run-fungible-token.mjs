#!/usr/bin/env node
import { readFileSync, mkdirSync, writeFileSync, existsSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import { blake3 } from '@noble/hashes/blake3';
import { compileContract } from '../../dist/generic.js';

const here = dirname(fileURLToPath(import.meta.url));
const out = process.argv[2];
if (!out) throw new Error('usage: node examples/gallery/run-fungible-token.mjs OUTPUT_DIR');
mkdirSync(out, { recursive: true });
const source = readFileSync(join(here, 'fungible-token.lotus'), 'utf8');
const publicKey = 'f9308a019258c31049344f85f89d5229b531c845836f99b08601f113bce036f9';
const bindings = { TokenWallet: { owner: publicKey }, FungibleToken: { issuer: publicKey } };
const compile = contract => compileContract(source, { contract, bindings });
const wallet = compile('TokenWallet');
const rules = compile('FungibleRules');
const mint = compile('FungibleToken');

const hex = value => Buffer.from(value).toString('hex');
const tagged = (name, payload) => blake3(Buffer.concat([Buffer.from(`Lotus/v2/${name}\0`), payload]));
function compareLE(a, b) { for (let i = 31; i >= 0; i--) if (a[i] !== b[i]) return a[i] - b[i]; return 0; }
function proofRoot(method) {
  const script = Buffer.from(method.scriptHex, 'hex');
  if (script.length >= 253) throw new Error('gallery proof helper expects short scripts');
  let root = tagged('branch', Buffer.concat([Buffer.from([0, script.length]), script]));
  if (hex(root) !== method.leaf) throw new Error(`${method.name}: leaf mismatch`);
  for (const siblingHex of method.proof) {
    const sibling = Buffer.from(siblingHex, 'hex');
    if (sibling.length !== 32) throw new Error(`${method.name}: invalid sibling width`);
    const [a, b] = compareLE(root, sibling) <= 0 ? [root, sibling] : [sibling, root];
    root = tagged('branch', Buffer.concat([Buffer.from([1]), a, b]));
  }
  return hex(root);
}
for (const artifact of [wallet, rules, mint]) {
  for (const method of artifact.methods) if (proofRoot(method) !== artifact.policy.root) throw new Error(`${artifact.contract}.${method.name}: proof mismatch`);
  writeFileSync(join(out, `${artifact.contract}.json`), JSON.stringify(artifact, null, 2) + '\n');
}
if (wallet.kind !== 'contract' || rules.kind !== 'contract' || mint.kind !== 'token') throw new Error('spend and mint trees are not separated');
if (mint.methods[0].mintAmountParam !== 'amount' || mint.methods[0].args.length !== 1 ||
    mint.methods[0].args[0].type !== 'Signature') throw new Error('mint amount must be node-provided, not a witness argument');
const holder = { flags: 1, valueAtoms: '1000', tokenId: mint.policy.root,
  branches: [wallet.policy.root, rules.policy.root], paths: [[0, 1]] };
const requiresBranch = (output, root) => {
  if ((output.flags & 2) !== 0 || output.paths.length === 0) return false;
  const index = output.branches.indexOf(root);
  return index !== -1 && output.paths.every(path => path.includes(index));
};
const bypass = { ...holder, paths: [[0], [0, 1]] };
const explicitBurn = { ...holder, flags: 3, paths: [] };
if (!requiresBranch(holder, rules.policy.root) || requiresBranch(bypass, rules.policy.root) ||
    requiresBranch(explicitBurn, rules.policy.root)) throw new Error('required-path policy check mismatch');
const localVm = join(here, '../../../../tools/lotus-v2-reference');
const vmPackage = process.env.LOTUS_V2_SKIP_VM === '1' ? undefined :
  process.argv[3] ?? (existsSync(join(localVm, 'lotus_v2_reference', 'vm_runner.py')) ? localVm : undefined);
const vm = {};
if (vmPackage) {
  const assigned = [[0x00,0x5d],[0x60,0x6b],[0x70,0x81],[0x88,0x94],[0x98,0xb4],[0xb8,0xc2],[0xc8,0xdd],[0xe0,0xea],[0xf0,0xf4]];
  const opcodeCosts = {};
  for (const [first,last] of assigned) for (let op = first; op <= last; op++) opcodeCosts[op.toString(16).padStart(2,'0')] = 1;
  const profile = { max_script_bytes: 8192, max_arguments: 16, max_element_bytes: 8192, max_stack_items: 128,
    max_altstack_items: 64, max_vm_bytes: 65536, max_ast_depth: 32, max_invocation_cost: 1000000,
    structural_byte_cost: 1, opcode_costs: opcodeCosts };
  const outputProfile = { max_output_branches: 16, max_output_paths: 16, max_output_bytes: 812, max_bytes_field: 8192 };
  const native = { flags: 0, value: 5000, token_id: null, branches: [wallet.policy.root], paths: [[0]] };
  const asVmOutput = (value, policy = holder) => ({ flags: policy.flags, value,
    token_id: policy.tokenId, branches: policy.branches, paths: policy.paths });
  function invoke(secondOutput) {
    const invocation = { inputs: [{ flags: 1, coin: asVmOutput(1000), mint_token_id: null },
      { flags: 1, coin: native, mint_token_id: null }],
    outputs: [asVmOutput(700), secondOutput, native], invocation_kind: 'spend', input_index: 0,
    branch_root: rules.policy.root, output_profile: outputProfile, selected_path_index: 0,
    selected_branch_index: 1, mint_delta: null };
    const input = { script: rules.methods[0].scriptHex, args: [], profile, invocation };
    const run = spawnSync(process.env.LOTUS_V2_PYTHON || 'python3', ['-m','lotus_v2_reference.vm_runner'], {
      input: JSON.stringify(input), encoding: 'utf8', env: { ...process.env, PYTHONPATH: vmPackage },
    });
    if (!run.stdout) throw new Error(`VM runner failed: ${run.stderr}`);
    return JSON.parse(run.stdout);
  }
  const valid = invoke(asVmOutput(250));
  const bypassed = invoke(asVmOutput(250, bypass));
  const burned = invoke(asVmOutput(250, explicitBurn));
  if (!valid.accepted_invocation || bypassed.accepted_invocation || burned.accepted_invocation)
    throw new Error(`token rules VM mismatch: ${JSON.stringify({valid,bypassed,burned})}`);
  vm.transferRules = { valid, bypassed, explicitBurn: burned };
}
const summary = { schema: 'lotus-v2/fungible-token-gallery/1', target: mint.target,
  trees: { wallet: wallet.policy.root, rules: rules.policy.root, mint: mint.policy.root },
  holder, examples: { mintAtoms: '1000', transferOutputsAtoms: ['700', '250'], implicitBurnAtoms: '50' },
  checks: { separateMintTree: true, methodProofs: true, nodeProvidedMintAmount: true,
    holderRequiresRules: true, bypassPathRejects: true, explicitTokenBurnPathRejects: true },
  vm,
  stages: { compile: 'passed', proof: 'passed', transactionFraming: 'unavailable', signature: 'unavailable',
    vm: vm.transferRules ? 'partial-transfer-rules' : 'unavailable', accounting: 'unavailable', block: 'unavailable' },
};
writeFileSync(join(out, 'fungible-token-summary.json'), JSON.stringify(summary, null, 2) + '\n');
console.log(JSON.stringify(summary, null, 2));
