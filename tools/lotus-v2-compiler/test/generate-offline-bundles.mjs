// Explicit generator: never called by offline verification.
import { readFileSync, writeFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { spawnSync } from 'node:child_process';
import { compilePackage } from '../dist/packages.js';
import { prepareContractCall, finalizeContractCall } from '../dist/call-runtime.js';
import { schnorr } from '@noble/curves/secp256k1';
const base = new URL('../', import.meta.url);
const python = process.env.LOTUS_V2_PYTHON ?? 'python3';
const sha = bytes => createHash('sha256').update(bytes).digest('hex');
const canonical = x => x === null || typeof x !== 'object' ? JSON.stringify(x) : Array.isArray(x) ? '[' + x.map(canonical).join(',') + ']' : '{' + Object.keys(x).sort().map(k => JSON.stringify(k) + ':' + canonical(x[k])).join(',') + '}';
const file = path => { const utf8 = readFileSync(new URL(path, base), 'utf8'); return { path, utf8, sha256: sha(utf8) }; };
const load = path => JSON.parse(readFileSync(new URL(path, base)));
const opcode_costs = {};
for (const [lo,hi] of [[0,0x5d],[0x60,0x6b],[0x70,0x81],[0x88,0x94],[0x98,0xb4],[0xb8,0xc2],[0xc8,0xdd],[0xe0,0xea],[0xf0,0xf4]]) for(let op=lo;op<=hi;op++) opcode_costs[op.toString(16).padStart(2,'0')] = op===0xbb||op===0xbc ? 1000 : 1;
const profile = {max_script_bytes:8192,max_arguments:16,max_element_bytes:8192,max_stack_items:128,max_altstack_items:64,max_vm_bytes:65536,max_ast_depth:32,max_invocation_cost:1000000,structural_byte_cost:1,opcode_costs};
function expected(input) {
 const run=spawnSync(python,[new URL('./offline-bundle-consumer.py',import.meta.url).pathname,'--execute'],{input:JSON.stringify(input),encoding:'utf8'});
 if(run.status!==0) throw Error(run.stderr); return JSON.parse(run.stdout);
}
function add(payload,name,artifact,method,input) {
 const result=expected(input); if(!result.accepted_invocation) throw Error(name+JSON.stringify(result));
 payload.cases.push({name,artifact,method,input,expected:result});
 if(input.signing) { const bad=structuredClone(input); bad.args[0]='00'.repeat(64); const result=expected(bad); if(result.accepted_invocation) throw Error('bad signature accepted'); payload.cases.push({name:name+'-bad-signature',artifact,method,input:bad,expected:result}); }
}
function save(name,payload) { payload.artifactBytes=Object.fromEntries(Object.entries(payload.artifacts).map(([name,a])=>[name,{utf8:canonical(a),sha256:sha(canonical(a))}])); const bundle={schema:'lotus-v2/offline-bundle/1',payload,sha256:sha(canonical(payload))}; writeFileSync(new URL(`fixtures/offline/${name}.json`,base),JSON.stringify(bundle,null,2)+'\n'); }
const payment=load('fixtures/generic-payment-v2.json');
const p={files:[file('fixtures/generic-payment-v2.json')],artifacts:{Payment:payment.artifact},context:payment.context,transaction:payment.valid,source:payment.source,cases:[]};
add(p,'payment-spend','Payment','spend',{script:payment.artifact.methods[0].scriptHex,args:[payment.valid.signature],input_count:1,output_count:1,profile,signing:{selected_leaf_hash:payment.valid.leaf,messages:{0:payment.valid.message},invocation_kind:'spend',input_index:0,output_count:1}}); save('payment',p);
const f=load('fixtures/fungible-token-v2.json');
const t={files:[file('fixtures/fungible-token-v2.json')],artifacts:f.artifacts,source:f.source,transactions:f.transactions,cases:[]};
const output=o=>({flags:o.flags,value:o.valueAtoms,token_id:o.tokenId,branches:o.branches,paths:o.paths});
for(const [name,tx] of Object.entries(f.transactions)) for(const [i,input] of tx.inputs.entries()) {
 const witnesses=input.kind==='mint'?[input]:input.witnesses;
 for(const [w,selected] of witnesses.entries()) {
 const artifact=f.artifacts[selected.artifact],method=artifact.methods.find(m=>m.name===selected.methodName),request=tx.requests.find(r=>r.inputIndex===i&&r.witnessIndex===w);
 const invocation={inputs:tx.inputs.map(x=>x.kind==='mint'?{flags:3,mint_token_id:f.artifacts.FungibleToken.policy.root}:{flags:1,coin:output(x.coin)}),outputs:tx.outputs.map(output),invocation_kind:input.kind,input_index:i,branch_root:artifact.policy.root,output_profile:{max_output_branches:16,max_output_paths:16,max_output_bytes:812,max_bytes_field:8192},selected_path_index:input.kind==='mint'?null:input.pathIndex,selected_branch_index:input.kind==='mint'?null:input.coin.paths[input.pathIndex][w],mint_delta:input.kind==='mint'?tx.tokenDeltas[f.artifacts.FungibleToken.policy.root]:null};
 add(t,`${name}-${i}-${w}`,selected.artifact,method.name,{script:method.scriptHex,args:method.args.map(()=>request.signature),profile,invocation,...(request?{signing:{selected_leaf_hash:method.leaf,messages:{0:request.digest},invocation_kind:input.kind,input_index:i,output_count:tx.outputs.length}}:{})});
 }
} save('fungible-token',t);
const owner='79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798';
const packageDir=new URL('examples/packages/linked/',base).pathname;
const bindings={Escrow:{owner}};
const build=async contract=>(await compilePackage(packageDir,{contract,bindings})).artifact;
const escrow=await build('Escrow'); bindings.Payer={owner,escrowRoot:escrow.policy.root,escrowLeaf:escrow.methods.find(m=>m.name==='spend').leaf}; bindings.Receiver={owner,escrowRoot:escrow.policy.root};
const l={files:['lotus.toml','lotus.lock','src/main.lotus','packages/policy/lotus.toml','packages/policy/src/escrow.lotus'].map(x=>file('examples/packages/linked/'+x)),artifacts:{Escrow:escrow,Payer:await build('Payer'),Receiver:await build('Receiver')},transactions:{},cases:[]};
for(const [name,a] of Object.entries(l.artifacts)) {
 const context={profile:a.target,chainId:'44'.repeat(32),prevTxid:'11'.repeat(32),prevIndex:0,sequence:0xffffffff,coin:{value:2000n,branches:[a.policy.root],paths:[[0]]},outputs:[{value:1000n,branches:[a.policy.root],paths:[[0]]}]};
 const plan=prepareContractCall(a,'spend',context,{sig:null});
 const sig=schnorr.sign(Buffer.from(plan.requests[0].digest,'hex'),Buffer.from('00'.repeat(31)+'01','hex'),new Uint8Array(32));
 const final=finalizeContractCall(plan,{sig});
 l.transactions[name]=JSON.parse(JSON.stringify({context,wire:Buffer.from(final.wire).toString('hex'),txid:final.txid,txhash:final.txhash,requests:plan.requests},(_,v)=>typeof v==='bigint'?v.toString():v));
 const m=a.methods.find(m=>m.name==='spend'); add(l,name+'-spend',name,'spend',{script:m.scriptHex,args:[Buffer.from(sig).toString('hex')],input_count:1,output_count:1,profile,signing:{selected_leaf_hash:m.leaf,messages:{0:plan.requests[0].digest},invocation_kind:'spend',input_index:0,output_count:1}});
} save('linked',l);
