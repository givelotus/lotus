import { spawnSync } from 'node:child_process';
import { mkdirSync,writeFileSync,readFileSync } from 'node:fs';
import { join,resolve } from 'node:path';
import { schnorr } from '@noble/curves/secp256k1';
import { compilePackage } from '../../dist/packages.js';
import { compileContract } from '../../dist/generic.js';
import { hex,unhex } from '../../dist/compiler.js';
import { encodeOutput } from '../../dist/runtime.js';
import { finalizeContractCall,prepareContractCall,methodRoot } from '../../dist/call-runtime.js';
export const schema='lotus-v2/differential-corpus/1';
export const limits={timeout:5000,maxBuffer:1048576,maxCases:256};
const ranges=[[0,0x5d],[0x60,0x6b],[0x70,0x81],[0x88,0x94],[0x98,0xb4],[0xb8,0xc2],[0xc8,0xdd],[0xe0,0xea],[0xf0,0xf4]];
export const profile={max_script_bytes:512,max_arguments:8,max_element_bytes:128,max_stack_items:16,max_altstack_items:8,max_vm_bytes:256,max_ast_depth:8,max_invocation_cost:10000000,structural_byte_cost:1,opcode_costs:Object.fromEntries(ranges.flatMap(([a,b])=>Array.from({length:b-a+1},(_,i)=>[(a+i).toString(16).padStart(2,'0'),{base:1,operand_byte:1,result_byte:1}])))};
export function corpus(seed=79225,count=16) {
 if(!Number.isInteger(seed)||seed<0||seed>0xffffffff||!Number.isInteger(count)||count<0||count>80)throw Error('invalid seed/count');
 let state=seed;const cases=[];
 for(let i=0;i<count;i++) {
  state=(Math.imul(state,1664525)+1013904223)>>>0;
  const source=`contract C { function m(x: Int) { require(x + ${state%32} > 0); } }`;
  const artifact=compileContract(source,{contract:'C',bindings:{}});
  for(const [name,arg] of [['positive','01'+'00'.repeat(15)],['negative','ff'.repeat(16)],['malformed','01']])cases.push({id:`seed-${i}-${name}`,source,artifact,script:artifact.methods[0].scriptHex,args:[arg],input_count:0,output_count:0,profile});
 }
 for(const [id,script]of [['true','51'],['truncated','02ff'],['reserved','ff']])cases.push({id:`hand-${id}`,script,args:[],input_count:0,output_count:0,profile});
 return {schema,seed,cases};
}
export function signedCases() {
 const f=JSON.parse(readFileSync(new URL('../../fixtures/generic-payment-v2.json',import.meta.url)));
 const out=o=>({value:BigInt(o.valueAtoms),branches:o.branches,paths:o.paths});
 const context={...f.context,coin:out(f.context.coin),outputs:f.context.outputs.map(out)};
 const plan=prepareContractCall(f.artifact,'spend',context,{signature:null});
 const sig=unhex(f.valid.signature);
 return [false,true].map(bad=>{
  const signature=sig.slice();if(bad)signature[0]^=1;
  const final=finalizeContractCall(plan,{signature});
  return {id:bad?'signed-bad-signature':'signed-payment',artifact:f.artifact,source:readFileSync(new URL('../../examples/gallery/payment.lotus',import.meta.url),'utf8'),script:f.artifact.methods[0].scriptHex,args:[hex(signature)],input_count:1,output_count:context.outputs.length,
   profile:{...profile,max_script_bytes:8192,max_arguments:1024,max_element_bytes:8192,max_stack_items:1024,max_altstack_items:1024,max_vm_bytes:1048576,max_ast_depth:16,max_invocation_cost:1000000000},
   transaction_context:transactionContext(final.wire,context),
   native_context:[hex(final.wire),context.chainId,'0','0',hex(encodeOutput(context.coin))]};
 });
}
export const contextProfile={...profile,max_script_bytes:8192,max_arguments:1024,max_element_bytes:8192,max_stack_items:1024,max_altstack_items:1024,max_vm_bytes:1048576,max_ast_depth:16,max_invocation_cost:1000000000};
export function transactionContext(wire,context) {
 return {full_tx:hex(wire),chain_id:context.chainId,input_index:0,witness_index:0,coins:[hex(encodeOutput(context.coin))],
  profile:{max_inputs:65535,max_outputs:65535,max_mints:65535,max_script_bytes:8192,max_arguments:1024,max_argument_bytes:8192,max_branch_proof_depth:64}};
}
export async function linkedCases() {
 const directory=resolve(import.meta.dirname,'../../examples/packages/linked');
 const owner='79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798';
 const secret=unhex('00'.repeat(31)+'01');
 const build=async(contract,bindings={})=>(await compilePackage(directory,{contract,bindings:{Escrow:{owner},...bindings}})).artifact;
 const escrow=await build('Escrow');
 const leaf=escrow.methods.find(m=>m.name==='spend').leaf;
 const payer=await build('Payer',{Payer:{owner,escrowRoot:escrow.policy.root,escrowLeaf:leaf}});
 const receiver=await build('Receiver',{Receiver:{owner,escrowRoot:escrow.policy.root}});
 const wrongRoot=escrow.policy.root.replace(/^../,escrow.policy.root.startsWith('00')?'11':'00');
 const wrong=await build('Payer',{Payer:{owner,escrowRoot:wrongRoot,escrowLeaf:leaf}});
 const cases=[];
 const sources={main:readFileSync(join(directory,'src/main.lotus'),'utf8'),library:readFileSync(join(directory,'packages/policy/src/escrow.lotus'),'utf8')};
 for(const artifact of [escrow,payer,receiver,wrong]) {
  const context={profile:artifact.target,chainId:'44'.repeat(32),prevTxid:'11'.repeat(32),prevIndex:0,sequence:0xffffffff,
   coin:{value:2000n,branches:[artifact.policy.root],paths:[[0]]},outputs:[{value:1000n,branches:[artifact.policy.root],paths:[[0]]}]};
  const plan=prepareContractCall(artifact,'spend',context,{sig:null});
  const signature=schnorr.sign(unhex(plan.requests[0].digest),secret,new Uint8Array(32));
  for(const bad of [false,true]) {
   const sig=signature.slice();if(bad)sig[0]^=1;
   const final=finalizeContractCall(plan,{sig});
   const method=artifact.methods.find(m=>m.name==='spend');
   cases.push({id:`linked-${artifact.contract.toLowerCase()}-${artifact===wrong?'wrong-root-':''}${bad?'bad-signature':'valid'}`,expected:bad||artifact===wrong?'reject':'accept',artifact,source:sources,script:method.scriptHex,args:[hex(sig)],input_count:1,output_count:1,profile:contextProfile,
    transaction_context:transactionContext(final.wire,context),native_context:[hex(final.wire),context.chainId,'0','0',hex(encodeOutput(context.coin))]});
  }
 }
 return cases;
}
export function processResult(command,args,input,env=process.env) {
 const start=performance.now();const r=spawnSync(command,args,{input:input===undefined?undefined:JSON.stringify(input),encoding:'utf8',env,timeout:limits.timeout,maxBuffer:limits.maxBuffer});
 return {exit:r.status,signal:r.signal,error:r.error?.message,stdout:r.stdout,stderr:r.stderr,elapsed_ms:performance.now()-start};
}
export function python(c,o={}) {
 const env={...process.env,PYTHONPATH:o.reference??process.env.LOTUS_V2_REFERENCE_PATH??resolve(import.meta.dirname,'../../../lotus-v2-reference')};
 const run=processResult(o.python??process.env.LOTUS_V2_PYTHON??'python3',[join(import.meta.dirname,'reference.py')],c,env);
 try{return {...JSON.parse(run.stdout),process:run};}catch{return {status:'tool-error',process:run};}
}
export function native(c,executable) {
 if(!executable)return {status:'unsupported',reason:'native executable not configured'};
 const args=c.native_context?['--context',...c.native_context]:['--charge',c.script,String(c.input_count),String(c.output_count),...c.args];
 const run=processResult(executable,args);
 const match=/^([SAIUE]) (\d+|-)(?: (\d+|-))?(?: (.*?))?\s*$/.exec(run.stdout??'');
 if(!match||run.exit!==0)return {status:'tool-error',process:run};
 if(match[1]==='E')return {status:'operational-error',reason:'native VM operational failure',
  diagnostic_charges:{accounting:match[2]==='-'?null:match[2],enforcement:!match[3]||match[3]==='-'?null:match[3]},process:run};
 return {status:({S:'accept',A:'accept',I:'reject',U:'unsupported'})[match[1]],automatic_success:match[1]==='A',accounting_charge:match[2]==='-'?null:Number(match[2]),enforcement_charge:!match[3]||match[3]==='-'?null:Number(match[3]),final_stack:match[4]?match[4].split(' ').map(x=>x==='-'?'':x):null,leaf:methodRoot(c.script,[]),process:run};
}
export function compare(a,b) {
 if([a.status,b.status].some(s=>!['accept','reject'].includes(s)))return [];
 return ['status','automatic_success','accounting_charge','enforcement_charge','final_stack','leaf'].filter(k=>a[k]!=null&&b[k]!=null&&JSON.stringify(a[k])!==JSON.stringify(b[k]));
}
export function comparison(a,b) {
 const outcomes={python:a.status,native:b.status};
 const reasons=Object.entries(outcomes).filter(([,status])=>!['accept','reject'].includes(status)).map(([engine,status])=>`${engine}:${status}`);
 const discrepancies=compare(a,b);
 return {status:reasons.length?'inconclusive':discrepancies.length?'disagreement':'compared',outcomes,reasons,discrepancies};
}
export function reportFailed(report) {
 return report.cases.some(c=>c.discrepancies.length||[c.python.status,c.native.status].some(s=>['operational-error','tool-error'].includes(s)));
}
export function runCorpus(input,o={}) {
 if(input.schema!==schema||!Array.isArray(input.cases)||input.cases.length>limits.maxCases)throw Error('unsupported or oversized corpus');
 for(const c of input.cases) {
  if(!/^[a-zA-Z0-9_-]{1,100}$/.test(c.id)||typeof c.script!=='string'||! /^(?:[0-9a-f]{2})*$/.test(c.script)||c.script.length>16384||!Array.isArray(c.args)||c.args.length>1024||c.args.some(a=>typeof a!=='string'||! /^(?:[0-9a-f]{2})*$/.test(a)||a.length>16384))throw Error('invalid bounded case');
 }
 return {schema:'lotus-v2/differential-report/1',seed:input.seed,node:process.version,platform:process.platform,arch:process.arch,limits,cases:input.cases.map(c=>{const a=python(c,o),b=native(c,o.native);return {case:c,compiler:c.artifact?{status:'compiled',root:c.artifact.policy.root,leaf:c.artifact.methods.find(m=>m.scriptHex===c.script)?.leaf}:null,python:a,native:b,discrepancies:compare(a,b),comparison:comparison(a,b)};})};
}
export function saveReport(report,directory) {
 mkdirSync(directory,{recursive:true});writeFileSync(join(directory,'report.json'),JSON.stringify(report,null,2)+'\n',{flag:'wx'});
 for(const c of report.cases.filter(c=>c.discrepancies.length||[c.python.status,c.native.status].some(s=>['operational-error','tool-error'].includes(s))))writeFileSync(join(directory,`${c.case.id}.json`),JSON.stringify({schema,seed:report.seed,cases:[c.case],evidence:c},null,2)+'\n',{flag:'wx'});
}
