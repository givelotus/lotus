import test from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { compileContract } from '../dist/generic.js';

const source = readFileSync(new URL('../examples/gallery/token-upgrade.lotus', import.meta.url), 'utf8');
const oldToken = '11'.repeat(32);
const walletRoot = '22'.repeat(32);
const bindings = { Token: { old_token: oldToken } };
const python = process.env.LOTUS_V2_PYTHON ?? 'python3';
const vmPackage = process.env.LOTUS_V2_VM_REFERENCE_PACKAGE ?? fileURLToPath(new URL('../../lotus-v2-reference/', import.meta.url));
const schemaPath = fileURLToPath(new URL('../artifact-v2.schema.json', import.meta.url));
const artifact = name => compileContract(source, { contract: name, bindings });

test('generated contract and token artifacts validate against the schema', t => {
  const probe = spawnSync(python, ['-c', 'import jsonschema'], { encoding: 'utf8' });
  if (probe.status !== 0) { t.skip('install test/requirements-vm.txt and set LOTUS_V2_PYTHON'); return; }
  const contract = artifact('Rules'), token = artifact('Token');
  const caseJson = { schema: JSON.parse(readFileSync(schemaPath, 'utf8')), artifacts: [contract, token] };
  const script = `import json, sys
from jsonschema import Draft202012Validator
case = json.load(sys.stdin)
Draft202012Validator.check_schema(case['schema'])
validator = Draft202012Validator(case['schema'])
for artifact in case['artifacts']:
    validator.validate(artifact)
`;
  const run = spawnSync(python, ['-c', script], { input: JSON.stringify(caseJson), encoding: 'utf8' });
  assert.equal(run.status, 0, run.stderr);
});

test('compiled upgrade guards mint input reads and enforces burned amount', t => {
  if (!existsSync(`${vmPackage}/lotus_v2_reference/vm_context.py`)) {
    t.skip('P03 invocation context is not installed'); return;
  }
  const env = { ...process.env, PYTHONPATH: vmPackage };
  const probe = spawnSync(python, ['-c', 'import blake3, lotus_v2_reference.vm_context'], { env, encoding: 'utf8' });
  if (probe.status !== 0) { t.skip('install test/requirements-vm.txt and set LOTUS_V2_PYTHON'); return; }

  const rules = artifact('Rules'), token = artifact('Token');
  const method = token.methods.find(m => m.name === 'upgrade');
  assert.equal(token.kind, 'token');
  assert.equal(method.invocation, 'mint');
  assert.deepEqual(method.args, []); // The positive delta is node-pushed, never supplied as witness data.

  const opcodeCosts = {};
  for (const [lo, hi] of [[0x00,0x5d],[0x60,0x6b],[0x70,0x81],[0x88,0x94],[0x98,0xb4],[0xb8,0xc2],[0xc8,0xdd],[0xe0,0xea],[0xf0,0xf4]]) {
    for (let op = lo; op <= hi; op++) opcodeCosts[op.toString(16).padStart(2,'0')] = 1;
  }
  const profile = { max_script_bytes:8192, max_arguments:16, max_element_bytes:8192,
    max_stack_items:128, max_altstack_items:64, max_vm_bytes:65536, max_ast_depth:32,
    max_invocation_cost:1000000, structural_byte_cost:1, opcode_costs:opcodeCosts };
  const outputProfile = { max_output_branches:16, max_output_paths:16,
    max_output_bytes:812, max_bytes_field:8192 };
  const oldCoin = { flags:1, value:1000, token_id:oldToken, branches:[walletRoot], paths:[[0]] };
  const invoke = oldRemainder => {
    const invocation = { invocation_kind:'mint', input_index:1, branch_root:token.policy.root,
      mint_delta:700, output_profile:outputProfile,
      inputs:[{ flags:1, coin:oldCoin }, { flags:3, mint_token_id:token.policy.root }],
      outputs:[
        { flags:1, value:oldRemainder, token_id:oldToken, branches:[walletRoot], paths:[[0]] },
        { flags:1, value:700, token_id:token.policy.root,
          branches:[walletRoot,rules.policy.root], paths:[[0,1]] },
      ] };
    const run = spawnSync(python, ['-m','lotus_v2_reference.vm_runner'], {
      env, encoding:'utf8', input:JSON.stringify({ script:method.scriptHex, args:[], profile, invocation }),
    });
    assert.ok(run.stdout, run.stderr);
    return JSON.parse(run.stdout);
  };
  const accepted = invoke(250); // 1000 - 250 = 750 old units burned; mint delta 700.
  assert.equal(accepted.accepted_invocation, true, JSON.stringify(accepted));
  assert.deepEqual(accepted.final_stack, ['01' + '00'.repeat(15)]);
  const rejected = invoke(400); // 1000 - 400 = 600 old units burned.
  assert.equal(rejected.accepted_invocation, false);
  assert.equal(rejected.stage, 'execution');
  assert.match(rejected.error, /VERIFY failed/);
});
