import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,writeFileSync,mkdirSync} from 'node:fs';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {compileContract} from '../dist/generic.js';
const python=process.env.LOTUS_V2_PYTHON ?? 'python3';
const reference=process.env.LOTUS_V2_VM_REFERENCE_PACKAGE ?? fileURLToPath(new URL('../../lotus-v2-reference/',import.meta.url));
const root=new URL('../examples/gallery/',import.meta.url);
const asset='11'.repeat(32),quote='22'.repeat(32),settlement='33'.repeat(32),wrong='44'.repeat(32);
const opcode_costs={};
for(const [lo,hi] of [[0,0x5d],[0x60,0x6b],[0x70,0x81],[0x88,0x94],[0x98,0xb4],[0xb8,0xc2],[0xc8,0xdd],[0xe0,0xea],[0xf0,0xf4]]) for(let n=lo;n<=hi;n++) opcode_costs[n.toString(16).padStart(2,'0')]=1;
const profile={max_script_bytes:8192,max_arguments:16,max_element_bytes:8192,max_stack_items:128,max_altstack_items:64,max_vm_bytes:65536,max_ast_depth:32,max_invocation_cost:1000000,structural_byte_cost:1,opcode_costs};
const output_profile={max_output_branches:16,max_output_paths:16,max_output_bytes:812,max_bytes_field:8192};
const fixtures=JSON.parse(readFileSync(new URL('cabi04-scenarios.json',root),'utf8'));
for(const fixture of fixtures.executed) test(`CABI04 ${fixture.file}: reference positive and mutations`,()=>{
 const source=readFileSync(new URL(`${fixture.file}.lotus`,root),'utf8');
 const artifact=compileContract(source,{contract:fixture.contract,bindings:{LimitOrder:{quote,price:'7',settlement}}});
 const policy=artifact.policy.root;
 const coin=(value,token_id=asset,branches=[policy])=>({flags:1,value,token_id,branches,paths:[[0]]});
 const inputs=fixture.inputs.map(value=>({flags:1,coin:coin(value)}));
 const outputs=fixture.outputs.map(value=>coin(value,fixture.file==='limit-order'?quote:asset,fixture.file==='limit-order'?[settlement]:[policy]));
 const base={script:artifact.methods[0].scriptHex,args:[],profile,invocation:{invocation_kind:'spend',input_index:0,branch_root:policy,selected_path_index:0,selected_branch_index:0,output_profile,inputs,outputs}};
 const records=[];
 const run=(name,payload,expected)=>{
  const proc=spawnSync(python,['-m','lotus_v2_reference.vm_runner'],{env:{...process.env,PYTHONPATH:reference},input:JSON.stringify(payload),encoding:'utf8'});
  assert.ok(proc.stdout,proc.stderr);const result=JSON.parse(proc.stdout);
  records.push({name,sourceExpected:expected,bytecodeResult:result,invocation:payload});
  if(process.env.LOTUS_V2_CABI04_RESULTS){mkdirSync(process.env.LOTUS_V2_CABI04_RESULTS,{recursive:true});writeFileSync(`${process.env.LOTUS_V2_CABI04_RESULTS}/${fixture.file}.json`,JSON.stringify({source,artifact,records},null,2)+'\n');}
  assert.notEqual(result.error_kind,'UnsupportedFeature',JSON.stringify(result));
  assert.equal(result.accepted_invocation,expected,JSON.stringify(result));
  if(!expected) assert.equal(result.stage,'execution',JSON.stringify(result));
 };
 for(let index=0;index<inputs.length;index++){const c=structuredClone(base);c.invocation.input_index=index;run(`positive-input-${index}`,c,true);}
 for(const mutation of fixture.mutations){const c=structuredClone(base);
  if(mutation==='asset')c.invocation.outputs[0].token_id=wrong;
  if(mutation==='policy')c.invocation.outputs[0].branches=[wrong];
  if(mutation==='value')c.invocation.outputs[0].value+=1;
  if(mutation==='missing')c.invocation.outputs=[];
  if(mutation==='duplicate')c.invocation.outputs.push(structuredClone(c.invocation.outputs[0]));
  if(mutation==='counterpart')c.invocation.inputs[1].coin.token_id=wrong;
  run(mutation,c,false);
 }
});
for(const fixture of fixtures.unsupported)test(`CABI04 unsupported intent: ${fixture.name}`,()=>{
 assert.throws(()=>compileContract(fixture.source,{contract:fixture.contract,bindings:{}}),new RegExp(fixture.diagnostic));
});
