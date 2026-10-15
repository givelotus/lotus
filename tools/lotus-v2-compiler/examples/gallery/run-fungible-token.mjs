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
if (!out) throw new Error('usage: node examples/gallery/run-fungible-token.mjs OUTPUT_DIR');
mkdirSync(out, { recursive: true });
const source = readFileSync(join(here, 'fungible-token.lotus'), 'utf8');
const publicKey = 'f9308a019258c31049344f85f89d5229b531c845836f99b08601f113bce036f9';
const bindings = { TokenWallet: { owner: publicKey }, FungibleRules: {}, FungibleToken: { issuer: publicKey } };
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
const requiresPathBranches = (output, roots) => roots.every(root => requiresBranch(output, root));
const bypass = { ...holder, paths: [[0], [0, 1]] };
const explicitBurn = { ...holder, flags: 3, paths: [] };
const missingWallet = { ...holder, branches: [rules.policy.root], paths: [[0]] };
if (!requiresPathBranches(holder, [rules.policy.root, wallet.policy.root]) ||
    requiresBranch(bypass, rules.policy.root) ||
    requiresPathBranches(missingWallet, [rules.policy.root, wallet.policy.root]) ||
    requiresBranch(explicitBurn, rules.policy.root)) throw new Error('required-path policy check mismatch');
const fixturePath = join(here, '../../fixtures/fungible-token-v2.json');
const fixture = existsSync(fixturePath) ? JSON.parse(readFileSync(fixturePath, 'utf8')) : null;
const artifacts = { TokenWallet: wallet, FungibleRules: rules, FungibleToken: mint };
const transactions = {};
if (fixture) {
  const { encodeAssetOutput, prepareTransactionCall, finalizeTransactionCall } = await import('../../dist/transaction-runtime.js');
  const fromOutput = o => ({ flags: o.flags, value: BigInt(o.valueAtoms),
    ...(o.tokenId === null ? {} : { tokenId: o.tokenId }), branches: o.branches, paths: o.paths });
  const fromWitness = w => ({ artifact: artifacts[w.artifact], methodName: w.methodName, args: w.args });
  function replay(tx) {
    const inputs = tx.inputs.map(input => input.kind === 'mint' ?
      { kind: 'mint', artifact: artifacts[input.artifact], methodName: input.methodName, args: input.args } :
      { kind: 'spend', prevTxid: input.prevTxid, prevIndex: input.prevIndex, sequence: input.sequence,
        coin: fromOutput(input.coin), pathIndex: input.pathIndex, witnesses: input.witnesses.map(fromWitness) });
    const intent = { profile: tx.profile, chainId: tx.chainId, dustLimitAtoms: BigInt(tx.dustLimitAtoms),
      inputs, outputs: tx.outputs.map(fromOutput) };
    const plan = prepareTransactionCall(intent);
    const signatures = Object.fromEntries(tx.requests.map(request => [request.key, Buffer.from(request.signature, 'hex')]));
    const final = finalizeTransactionCall(plan, signatures);
    if (hex(plan.unsignedWire) !== tx.unsignedWire || hex(final.wire) !== tx.wire ||
        final.txid !== tx.txid || final.txhash !== tx.txhash ||
        plan.feeAtoms.toString() !== tx.feeAtoms || plan.minimumFeeAtoms.toString() !== tx.minimumFeeAtoms ||
        plan.projectedFullBytes !== tx.projectedFullBytes) throw new Error('token fixture framing, identities or fee mismatch');
    for (let i = 0; i < inputs.length; i++) {
      const encoded = inputs[i].kind === 'mint' ? null : hex(encodeAssetOutput(inputs[i].coin));
      if (encoded !== tx.coinWires[i]) throw new Error(`token fixture coin wire mismatch at input ${i}`);
    }
    for (const request of plan.requests) {
      const saved = tx.requests.find(x => x.key === request.key);
      if (!saved || saved.digest !== request.digest || saved.leaf !== request.leaf ||
          saved.branchIndex !== request.branchIndex ||
          (request.positiveDelta === undefined) !== (saved.positiveDelta === undefined) ||
          (request.positiveDelta !== undefined && saved.positiveDelta !== hex(Uint8Array.from({ length: 16 }, (_, j) => Number((request.positiveDelta >> BigInt(8 * j)) & 255n)))) ||
          !schnorr.verify(Buffer.from(saved.signature, 'hex'), Buffer.from(request.digest, 'hex'), Buffer.from(saved.publicKey, 'hex')))
        throw new Error(`token fixture signature/selector mismatch for ${request.key}`);
    }
    return { plan, final, intent, fixture: tx };
  }
  for (const [name, artifact] of Object.entries(artifacts)) {
    if (fixture.artifacts[name].policy.root !== artifact.policy.root ||
        fixture.artifacts[name].methods.some((method, i) => method.scriptHex !== artifact.methods[i].scriptHex))
      throw new Error(`${name}: fixture artifact differs from current compiler`);
  }
  transactions.mint = replay(fixture.transactions.mint);
  transactions.transfer = replay(fixture.transactions.transfer);
  transactions.merge = replay(fixture.transactions.merge);
  const id = mint.policy.root;
  if (transactions.mint.plan.tokenDeltas[id] !== 1000n ||
      transactions.transfer.plan.tokenBurns[id] !== 50n ||
      transactions.transfer.intent.inputs[0].prevTxid !== transactions.mint.final.txid ||
      transactions.transfer.intent.inputs[1].prevTxid !== transactions.mint.final.txid)
    throw new Error('token fixture mint, burn or chained outpoint mismatch');
  if (transactions.merge.intent.inputs.filter(input => input.kind === 'spend' && input.coin.tokenId === id).length !== 2 ||
      transactions.merge.plan.tokenBurns[id] !== undefined ||
      transactions.merge.intent.outputs.find(output => output.tokenId === id)?.value !== 950n)
    throw new Error('token merge did not combine both inputs without burning supply');
  const transfer = transactions.transfer.intent;
  const withoutMint = { ...transfer, outputs: [
    { ...transfer.outputs[0], value: 751n }, transfer.outputs[1], transfer.outputs[2] ] };
  try { prepareTransactionCall(withoutMint); throw new Error('inflation without mint accepted'); }
  catch (err) { if (!/mint inputs do not match positive token deltas/.test(err.message)) throw err; }
  const missingRules = { ...transfer, inputs: [{ ...transfer.inputs[0], witnesses: transfer.inputs[0].witnesses.slice(0, 1) }, transfer.inputs[1]] };
  try { prepareTransactionCall(missingRules); throw new Error('missing rules witness accepted'); }
  catch (err) { if (!/required witness count/.test(err.message)) throw err; }
}
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
  function vmAmount(value) {
    const n = BigInt(value);
    if (n < 0n || n > BigInt(Number.MAX_SAFE_INTEGER)) throw new Error('gallery JSON amount exceeds exact JavaScript integer range');
    return Number(n);
  }
  const asVmOutput = output => ({ flags: output.flags, value: vmAmount(output.valueAtoms),
    token_id: output.tokenId, branches: output.branches, paths: output.paths });
  function runCase(input) {
    const run = spawnSync(process.env.LOTUS_V2_PYTHON || 'python3', ['-m','lotus_v2_reference.vm_runner'], {
      input: JSON.stringify(input), encoding: 'utf8', env: { ...process.env, PYTHONPATH: vmPackage },
    });
    if (!run.stdout) throw new Error(`VM runner failed: ${run.stderr}`);
    return JSON.parse(run.stdout);
  }
  function caseFor(tx, inputIndex, witnessIndex = 0, changedOutputs = null) {
    const input = tx.inputs[inputIndex];
    const selected = input.kind === 'mint' ? input : input.witnesses[witnessIndex];
    const artifact = artifacts[selected.artifact];
    const method = artifact.methods.find(m => m.name === selected.methodName);
    const request = tx.requests.find(r => r.inputIndex === inputIndex && r.witnessIndex === witnessIndex);
    const args = method.args.map(arg => {
      if (arg.type !== 'Signature' || !request || request.argumentIndex !== method.args.indexOf(arg))
        throw new Error('unexpected token witness ABI');
      return request.signature;
    });
    const invocation = { inputs: tx.inputs.map(item => item.kind === 'mint' ?
      { flags: 3, coin: null, mint_token_id: mint.policy.root } :
      { flags: 1, coin: asVmOutput(item.coin), mint_token_id: null }),
      outputs: (changedOutputs || tx.outputs).map(asVmOutput),
      invocation_kind: input.kind, input_index: inputIndex, branch_root: artifact.policy.root,
      output_profile: outputProfile,
      selected_path_index: input.kind === 'mint' ? null : input.pathIndex,
      selected_branch_index: input.kind === 'mint' ? null : input.coin.paths[input.pathIndex][witnessIndex],
      mint_delta: input.kind === 'mint' ? vmAmount(tx.tokenDeltas[mint.policy.root]) : null };
    return { script: method.scriptHex, args, profile, invocation,
      ...(request ? { signing: { selected_leaf_hash: method.leaf, messages: { '0': request.digest },
        invocation_kind: input.kind, input_index: inputIndex, output_count: tx.outputs.length } } : {}) };
  }
  if (fixture) {
    const mintTx = fixture.transactions.mint, transferTx = fixture.transactions.transfer;
    const checks = { fundingWallet: runCase(caseFor(mintTx, 0)), mintIssuer: runCase(caseFor(mintTx, 1)),
      transferWallet: runCase(caseFor(transferTx, 0, 0)),
      transferRules: runCase(caseFor(transferTx, 0, 1)),
      feeWallet: runCase(caseFor(transferTx, 1)) };
    if (Object.values(checks).some(result => !result.accepted_invocation))
      throw new Error(`token fixture VM invocation failed: ${JSON.stringify(checks)}`);
    const unauthorized = caseFor(mintTx, 1);
    unauthorized.args[0] = '00'.repeat(64);
    const bypassOutputs = transferTx.outputs.map((item, index) => index === 1 ?
      { ...item, paths: [[0], [0, 1]] } : item);
    const burnOutputs = transferTx.outputs.map((item, index) => index === 1 ?
      { ...item, flags: 3, paths: [] } : item);
    const negatives = { unauthorizedIssuer: runCase(unauthorized),
      bypassPath: runCase(caseFor(transferTx, 0, 1, bypassOutputs)),
      missingWalletPath: runCase(caseFor(transferTx, 0, 1, transferTx.outputs.map((item, index) => index === 1 ?
        { ...item, branches: [rules.policy.root], paths: [[0]] } : item))),
      explicitBurnPath: runCase(caseFor(transferTx, 0, 1, burnOutputs)) };
    if (Object.values(negatives).some(result => result.accepted_invocation))
      throw new Error(`token fixture VM negative accepted: ${JSON.stringify(negatives)}`);
    vm.fixture = { checks, negatives };
    const mergeTx = fixture.transactions.merge;
    vm.fixture.merge = mergeTx.inputs.flatMap((input, inputIndex) => input.kind === 'mint' ? [] :
      input.witnesses.map((_, witnessIndex) => runCase(caseFor(mergeTx, inputIndex, witnessIndex))))
      .map(result => result.accepted_invocation);
    if (vm.fixture.merge.some(result => !result) || vm.fixture.merge.length !== 5)
      throw new Error('one or more merge witness invocations failed');
    const mergeTokenIndex = mergeTx.outputs.findIndex(output => output.tokenId === mint.policy.root);
    const mergeNegatives = {
      missingWalletPath: runCase(caseFor(mergeTx, 0, 1, mergeTx.outputs.map((item, index) => index === mergeTokenIndex ?
        { ...item, branches: [rules.policy.root], paths: [[0]] } : item))),
      missingRulesPath: runCase(caseFor(mergeTx, 1, 1, mergeTx.outputs.map((item, index) => index === mergeTokenIndex ?
        { ...item, branches: [wallet.policy.root], paths: [[0]] } : item))) };
    if (Object.values(mergeNegatives).some(result => result.accepted_invocation))
      throw new Error(`token merge VM negative accepted: ${JSON.stringify(mergeNegatives)}`);
    vm.fixture.mergeNegatives = mergeNegatives;
  }

}
const summary = { schema: 'lotus-v2/fungible-token-gallery/1', target: mint.target,
  trees: { wallet: wallet.policy.root, rules: rules.policy.root, mint: mint.policy.root },
  holder, examples: { mintAtoms: '1000', transferOutputsAtoms: ['700', '250'], implicitBurnAtoms: '50',
    mergeInputsAtoms: ['700', '250'], mergeOutputAtoms: '950' },
  checks: { separateMintTree: true, methodProofs: true, nodeProvidedMintAmount: true,
    holderRequiresRules: true, holderRequiresWallet: true, missingWalletPathRejects: true,
    bypassPathRejects: true, explicitTokenBurnPathRejects: true,
    mergeCombinesTwoInputs: fixture ? true : undefined, mergeBurnsNoSupply: fixture ? true : undefined },
  vm,
  transactions: fixture ? { mint: { txid: fixture.transactions.mint.txid, wireBytes: fixture.transactions.mint.wire.length / 2, feeAtoms: fixture.transactions.mint.feeAtoms, tokenDeltaAtoms: '1000' },
    transfer: { txid: fixture.transactions.transfer.txid, wireBytes: fixture.transactions.transfer.wire.length / 2, feeAtoms: fixture.transactions.transfer.feeAtoms, implicitBurnAtoms: '50' },
    merge: { txid: fixture.transactions.merge.txid, wireBytes: fixture.transactions.merge.wire.length / 2, feeAtoms: fixture.transactions.merge.feeAtoms,
      tokenInputs: fixture.transactions.merge.inputs.filter(input => input.kind === 'spend' && input.coin.tokenId === mint.policy.root).map(input => input.coin.valueAtoms),
      tokenOutputAtoms: fixture.transactions.merge.outputs.find(output => output.tokenId === mint.policy.root).valueAtoms,
      implicitBurnAtoms: fixture.transactions.merge.tokenBurns[mint.policy.root] ?? '0' } } : undefined,
  stages: { compile: 'passed', proof: 'passed', transactionFraming: fixture ? 'passed' : 'unavailable', signature: fixture ? 'passed-schnorr' : 'unavailable',
    vm: vm.fixture ? 'passed-invocation-only' : 'unavailable', accounting: fixture ? 'passed-candidate-profile' : 'unavailable', block: 'unavailable' },
};
writeFileSync(join(out, 'fungible-token-summary.json'), JSON.stringify(summary, null, 2) + '\n');
console.log(JSON.stringify(summary, null, 2));
