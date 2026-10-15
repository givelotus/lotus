import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,writeFileSync,mkdirSync,mkdtempSync,rmSync} from 'node:fs';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {createHash} from 'node:crypto';
import {schnorr} from '@noble/curves/secp256k1';
import {compileContract} from '../dist/generic.js';
import {compilePackage,updateLock} from '../dist/packages.js';
const python=process.env.LOTUS_V2_PYTHON??'python3',reference=process.env.LOTUS_V2_VM_REFERENCE_PACKAGE??fileURLToPath(new URL('../../lotus-v2-reference/',import.meta.url)),runner=fileURLToPath(new URL('cabi04-reference.py',import.meta.url));
const source=readFileSync(new URL('../examples/gallery/stateful-allowance.lotus',import.meta.url),'utf8');
const hex=x=>Buffer.from(x).toString('hex'),key=n=>Buffer.from(n.toString(16).padStart(64,'0'),'hex');
const spender=hex(schnorr.getPublicKey(key(3))),recipientOwner=hex(schnorr.getPublicKey(key(4))),fundOwner=hex(schnorr.getPublicKey(key(5)));
const recipientArtifact=compileContract('contract Recipient<owner: PublicKey> { function spend(sig: Signature) { require(checksig(sig, owner)); } }',{contract:'Recipient',bindings:{Recipient:{owner:recipientOwner}}});
const options={contract:'StatefulAllowance',bindings:{StatefulAllowance:{spender,recipient:recipientArtifact.policy.root,per_call:'20',expected_path:'0100'}}};
const artifact=compileContract(source,options),method=artifact.methods[0],root=artifact.policy.root;
const fundingArtifact=compileContract('contract Funding<owner: PublicKey> { function spend(sig: Signature) { require(checksig(sig, owner)); } }',{contract:'Funding',bindings:{Funding:{owner:fundOwner}}}),fund=fundingArtifact.methods[0];
const n=x=>{let value=BigInt.asUintN(128,BigInt(x)),out='';for(let i=0;i<16;i++,value>>=8n)out+=Number(value&255n).toString(16).padStart(2,'0');return out;};
const state=x=>createHash('sha256').update(Buffer.from(n(x),'hex')).digest('hex');
const other='77'.repeat(32),token='11'.repeat(32);
const coin=(value,branches,token_id=null)=>({flags:token_id===null?0:1,value,token_id,branches,paths:[[0]]});
const input=(coin,m,args)=>({coin,script:m.scriptHex,proof:m.proof,args});
const base=()=>({script:method.scriptHex,proof:method.proof,args:[n(50),n(20),'00'.repeat(64)],inputs:[input(coin(100,[root,state(50)]),method,[n(50),n(20),'00'.repeat(64)]),input(coin(10,[fundingArtifact.policy.root]),fund,['00'.repeat(64)])],outputs:[coin(80,[root,state(30)]),coin(20,[recipientArtifact.policy.root])]});
const invoke=c=>{const p=spawnSync(python,[runner],{env:{...process.env,PYTHONPATH:reference},input:JSON.stringify(c),encoding:'utf8'});assert.equal(p.status,0,p.stderr);return JSON.parse(p.stdout);};
function sign(c,spenderKey=3){for(const [index,k,slot]of [[0,spenderKey,2],[1,5,0]]){const r=invoke({...c,input_index:index,prepare:true});assert.ok(r.message,JSON.stringify(r));c.inputs[index].args[slot]=hex(schnorr.sign(Buffer.from(r.message,'hex'),key(k),new Uint8Array(32)));}return c;}
const records=[];
function check(name,c,expected,evidence={}){const result=invoke(c);records.push({name,source,artifact,fundingArtifact,recipientArtifact,case:c,sourceExpected:expected,bytecodeResult:result,...evidence});if(process.env.LOTUS_V2_CABI04_RESULTS){mkdirSync(process.env.LOTUS_V2_CABI04_RESULTS,{recursive:true});writeFileSync(`${process.env.LOTUS_V2_CABI04_RESULTS}/stateful-allowance.json`,JSON.stringify(records,null,2)+'\n');}assert.equal(result.status,expected,JSON.stringify(result));return result;}
test('signed allowance authenticates budget, decrements state/inventory and pays fixed recipient within cap',()=>{
 const c=sign(base());for(const i of [0,1])check(`positive required input ${i}`,{...c,input_index:i},'accepted');
 // Next transition consumes the prior successor's state; fee input is separate.
 const second=base();second.inputs[0].coin=structuredClone(c.outputs[0]);second.inputs[0].args=[n(30),n(10),'00'.repeat(64)];second.outputs=[coin(70,[root,state(20)]),coin(10,[recipientArtifact.policy.root])];sign(second);for(const i of [0,1])check(`second required input ${i}`,{...second,input_index:i},'accepted');
 const exhausted=base();exhausted.inputs[0].coin.branches[1]=state(20);exhausted.inputs[0].args[0]=n(20);exhausted.outputs[0].branches[1]=state(0);sign(exhausted);for(const i of [0,1])check(`exact budget exhaustion required input ${i}`,{...exhausted,input_index:i},'accepted');
 const afterZero=base();afterZero.inputs[0].coin=structuredClone(exhausted.outputs[0]);afterZero.inputs[0].args=[n(0),n(1),'00'.repeat(64)];afterZero.outputs=[coin(79,[root,state(-1)]),coin(1,[recipientArtifact.policy.root])];sign(afterZero);check('exhausted budget cannot spend again',afterZero,'rejected');
 const replay=structuredClone(second);replay.inputs[0].args[0]=n(50);sign(replay);check('stale budget replay against successor',replay,'rejected');
 const unsigned=base();check('unsigned allowance',unsigned,'rejected');check('wrong delegated signer',sign(base(),4),'rejected');
 const stale=structuredClone(c);stale.outputs[1].value++;check('output changed after signatures',stale,'rejected');
 const altered=structuredClone(c);altered.inputs[0].args[1]=n(19);check('argument changed after signatures',altered,'rejected');
});
test('allowance rejects state, budget, recipient, asset and policy substitutions with fresh valid signatures',()=>{
 const mutations={entireInventory:c=>c.inputs[0].args[1]=n(100),excessInventory:c=>c.inputs[0].args[1]=n(101),zero:c=>c.inputs[0].args[1]=n(0),negative:c=>c.inputs[0].args[1]=n(-1),cap:c=>{c.inputs[0].args[1]=n(21);c.outputs=[coin(79,[root,state(29)]),coin(21,[recipientArtifact.policy.root])];},budget:c=>{c.inputs[0].args[0]=n(10);c.inputs[0].coin.branches[1]=state(10);},forgedBudget:c=>c.inputs[0].args[0]=n(51),negativeBudget:c=>{c.inputs[0].args[0]=n(-1);c.inputs[0].coin.branches[1]=state(-1);},unchangedBudget:c=>c.outputs[0].branches[1]=state(50),overDecrement:c=>c.outputs[0].branches[1]=state(29),underDecrement:c=>c.outputs[0].branches[1]=state(31),inventory:c=>c.outputs[0].value++,recipientAmount:c=>c.outputs[1].value++,recipientPolicy:c=>c.outputs[1].branches=[other],stateAsset:c=>{c.outputs[0].flags=1;c.outputs[0].token_id=token;},recipientAsset:c=>{c.outputs[1].flags=1;c.outputs[1].token_id=token;},code:c=>c.outputs[0].branches[0]=other,reorder:c=>c.outputs[0].branches.reverse(),extraStateBranch:c=>c.outputs[0].branches.push(other),missingState:c=>c.outputs.splice(0,1),missingPayment:c=>c.outputs.splice(1,1),duplicateState:c=>c.outputs.push(structuredClone(c.outputs[0])),duplicateRecipient:c=>c.outputs.push(structuredClone(c.outputs[1])),extraOutput:c=>c.outputs.push(coin(1,[other])),stateBypass:c=>c.outputs[0].paths=[[0],[1]],stateHostage:c=>c.outputs[0].paths=[[0,1]],recipientBypass:c=>{c.outputs[1].branches.push(other);c.outputs[1].paths=[[0],[1]];},recipientHostage:c=>{c.outputs[1].branches.push(other);c.outputs[1].paths=[[0,1]];},redundantStatePath:c=>c.outputs[0].paths=[[0],[0,1]],redundantInputPath:c=>c.inputs[0].coin.paths=[[0],[0,1]],inputBypass:c=>c.inputs[0].coin.paths=[[0],[1]],extraInput:c=>c.inputs.push(input(coin(100,[root,state(50)]),method,[n(50),n(20),'00'.repeat(64)])),optionalExtraInput:c=>{const i=input(coin(100,[root,state(50)]),method,[n(50),n(20),'00'.repeat(64)]);i.coin.paths=[[0],[1]];c.inputs.push(i);},lateRootInput:c=>{const i=input(coin(1,[fundingArtifact.policy.root,...Array.from({length:14},(_,k)=>(0x80+k).toString(16).repeat(32)),root]),fund,['00'.repeat(64)]);i.coin.paths=[[0],[15]];c.inputs.push(i);}};
 for(const [name,mutate]of Object.entries(mutations)){const c=base();mutate(c);sign(c);check(name,c,'rejected');}
});
test('allowance boundary one unit and token inventory use the same authenticated state schema',()=>{
 const single=base();single.inputs[0].args=[n(1),n(1),'00'.repeat(64)];single.inputs[0].coin.branches[1]=state(1);single.outputs=[coin(99,[root,state(0)]),coin(1,[recipientArtifact.policy.root])];sign(single);for(const i of [0,1])check(`one-unit final budget required input ${i}`,{...single,input_index:i},'accepted');
 const c=base();for(const x of [c.inputs[0].coin,...c.outputs]){x.flags=1;x.token_id=token;}sign(c);for(const i of [0,1])check(`token inventory required input ${i}`,{...c,input_index:i},'accepted');
});
test('allowance compiles through packages without changing scripts',async()=>{
 const dir=mkdtempSync(join(tmpdir(),'cabi04-allowance-'));try{mkdirSync(join(dir,'src'));writeFileSync(join(dir,'lotus.toml'),'[package]\nname = "allowance"\nversion = "0.1.0"\nkind = "contract"\nsource = "src"\nentry = "main"\nmodules = ["main"]\n');writeFileSync(join(dir,'src/main.lotus'),source);updateLock(dir);const a=(await compilePackage(dir,options)).artifact;assert.deepEqual(a.methods.map(m=>m.scriptHex),artifact.methods.map(m=>m.scriptHex));}finally{rmSync(dir,{recursive:true,force:true});}
});

test('path primitives retain assigned bytes and reject invalid types, receivers and indices',()=>{
 for(const body of ['require(this.coin.path_count(0) == 1);','require(sha256(this.coin.path(true)) == sha256(this.coin.path(0)));','for output in tx.outputs { require(output.coin.path_count() == 1); }','require(missing.path_count() == 1);'])assert.throws(()=>compileContract(`contract Bad { function spend() { ${body} } }`,{contract:'Bad',bindings:{}}));
 const s='contract Paths { function spend(index: Int) { require(this.coin.path_count() == 1); require(sha256(this.coin.path(index)) == sha256(this.coin.path(0))); for output in tx.outputs { require(output.path_count() == 1); require(sha256(output.path(0)) == sha256(this.coin.path(0))); } for input in tx.inputs { require(input.coin.path_count() == 1); require(sha256(input.path(0)) == sha256(input.coin.path(0))); } } }',a=compileContract(s,{contract:'Paths',bindings:{}}),m=a.methods[0];
 for(const [op,byte]of [['UTXOPATHCOUNT','da'],['UTXOPATH','db'],['OUTPUTPATHCOUNT','e5'],['OUTPUTPATH','e6']])assert.ok(m.sourceMap.some(e=>e.op===op&&m.scriptHex.slice(e.byteStart*2,e.byteEnd*2)===byte));
 for(const index of [0,-1,1,65536]){const c={script:m.scriptHex,proof:m.proof,args:[n(index)],coin:coin(1,[a.policy.root]),outputs:[coin(1,[a.policy.root])]};check(`path index ${index}`,c,index===0?'accepted':'rejected',{source:s,artifact:a});}
});
