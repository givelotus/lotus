import assert from 'node:assert/strict';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { join, resolve } from 'node:path';
import { compileContract, compileContractWithTrace } from '../../dist/generic.js';

const source = readFileSync(new URL('./demo.lotus', import.meta.url), 'utf8');
const options = { contract: 'Demonstration', bindings: {} };
const out = resolve(process.argv[2] ?? '/tmp/lotus-compiler-pipeline');
mkdirSync(out, { recursive: true });
const { artifact, trace } = await compileContractWithTrace(source, options);
assert.equal(trace.filter(event => event.kind === 'start' && event.job === 'leaf:Base.check').length,1);
for (const parent of ['leaf:Left.check','leaf:Right.check'])
  assert(trace.some(event => event.kind === 'await' && event.job === parent && event.dependency === 'leaf:Base.check'));
assert.deepEqual(artifact, compileContract(source, options), 'scheduled and synchronous artifacts differ');
const plain = compileContract(source, { ...options, optimize: false });
const before = plain.methods[0], after = artifact.methods[0];
assert(after.staticResources.opcodes < before.staticResources.opcodes);

// Explicit demonstration costs, not a proposed consensus fee schedule.
const ranges = [[0,0x5d],[0x60,0x6b],[0x70,0x81],[0x88,0x94],[0x98,0xb4],
  [0xb8,0xc2],[0xc8,0xdd],[0xe0,0xea],[0xf0,0xf4]];
const opcode_costs = {};
for (const [lo,hi] of ranges) for (let op = lo; op <= hi; op++) opcode_costs[op.toString(16).padStart(2,'0')] = 1;
const profile = { max_script_bytes:8192, max_arguments:16, max_element_bytes:8192,
  max_stack_items:128, max_altstack_items:64, max_vm_bytes:65536,
  max_ast_depth:32, max_invocation_cost:1000000, structural_byte_cost:1, opcode_costs };
const reference = resolve(process.env.LOTUS_V2_REFERENCE_PATH ?? join(import.meta.dirname, '../../../lotus-v2-reference'));
function invoke(script, args) {
  const result = spawnSync(process.env.LOTUS_V2_PYTHON ?? 'python3', ['-m','lotus_v2_reference.vm_runner'], {
    encoding:'utf8', input:JSON.stringify({ script, args, input_count:0, output_count:0, profile }),
    env:{ ...process.env, PYTHONPATH:reference },
  });
  if (!result.stdout) throw new Error(`Reference VM failed: ${result.error ?? result.stderr}`);
  const parsed = JSON.parse(result.stdout);
  assert.notEqual(parsed.error_kind, 'UnsupportedFeature', JSON.stringify(parsed));
  return parsed;
}
const cases = [];
for (const [name, flag, expected] of [
  ['true branch', '01' + '00'.repeat(15), true],
  ['false branch', '00'.repeat(16), true],
  ['noncanonical Boolean', '02' + '00'.repeat(15), false],
  ['malformed Boolean width', '01', false],
]) {
  const args = [flag, 'ab'.repeat(32)];
  const original = invoke(before.scriptHex,args), optimized = invoke(after.scriptHex,args);
  assert.equal(original.accepted_invocation,expected, JSON.stringify(original));
  assert.equal(optimized.accepted_invocation,expected, JSON.stringify(optimized));
  if (expected) {
    assert.deepEqual(original.stack,optimized.stack);
    assert(optimized.charged_cost <= original.charged_cost);
  } else assert.equal(optimized.error_kind,original.error_kind);
  cases.push({ name, expected, original, optimized });
}
let cycleDiagnostic;
try {
  await compileContractWithTrace('contract Cycle { function check() { require(contract_root(Cycle) == contract_root(Cycle)); } }',
    { contract:'Cycle', bindings:{} });
  throw new Error('cycle unexpectedly compiled');
} catch (error) {
  assert.match(error.message,/cycle/i);
  assert.notEqual(error.message,'cycle unexpectedly compiled');
  cycleDiagnostic = error.message;
}
const summary = { before:before.staticResources, after:after.staticResources,
  beforeOpcodes:before.sourceMap.map(x => x.op), afterOpcodes:after.sourceMap.map(x => x.op),
  cycleDiagnostic, cases, trace,
  scope:'One invocation in the independent reference VM, using explicit demonstration costs; not full transaction or block validation.' };
for (const [name,value] of [['optimized.json',artifact],['unoptimized.json',plain],['trace.json',trace],['summary.json',summary]])
  writeFileSync(join(out,name),JSON.stringify(value,null,2) + '\n');
console.log(`Opcodes: ${before.staticResources.opcodes} -> ${after.staticResources.opcodes}`);
console.log(`Bytes: ${before.staticResources.scriptBytes} -> ${after.staticResources.scriptBytes}`);
console.log('Scheduler: Left.check and Right.check awaited Base.check; Base.check compiled once.');
for (const item of cases) console.log(`${item.name}: ${item.expected ? 'accepted' : 'rejected'} by both versions`);
console.log(`Cycle rejected: ${cycleDiagnostic}`);
console.log(`Artifacts and scheduler trace: ${out}`);
