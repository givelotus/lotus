import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,writeFileSync,mkdirSync,mkdtempSync,rmSync} from 'node:fs';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {schnorr} from '@noble/curves/secp256k1';
import {compileContract} from '../dist/generic.js';
import {compilePackage,updateLock} from '../dist/packages.js';
const python=process.env.LOTUS_V2_PYTHON??'python3',reference=process.env.LOTUS_V2_VM_REFERENCE_PACKAGE??fileURLToPath(new URL('../../lotus-v2-reference/',import.meta.url));
const runner=fileURLToPath(new URL('cabi04-reference.py',import.meta.url)),source=readFileSync(new URL('../examples/gallery/limit-order.lotus',import.meta.url),'utf8');
const offered='11'.repeat(32),quote='22'.repeat(32),seller='33'.repeat(32),buyer='44'.repeat(32),wrong='77'.repeat(32);
const n=x=>{let value=BigInt(x),out='';for(let i=0;i<16;i++,value>>=8n)out+=Number(value&255n).toString(16).padStart(2,'0');return out;};
const options={contract:'PartialLimitOrder',bindings:{PartialLimitOrder:{quote,price:'3',seller}}};
const artifact=compileContract(source,options),method=artifact.methods[0],root=artifact.policy.root;
const privateKey=Buffer.from('00'.repeat(31)+'03','hex'),owner=Buffer.from(schnorr.getPublicKey(privateKey)).toString('hex');
const funding=compileContract('contract Funding<owner: PublicKey> { function spend(sig: Signature) { require(checksig(sig, owner)); } }',{contract:'Funding',bindings:{Funding:{owner}}}),fundMethod=funding.methods[0];
const coin=(value,token_id,branches)=>({flags:token_id===null?0:1,value,token_id,branches,paths:[[0]]});
const input=(coin,method)=>({coin,script:method.scriptHex,proof:method.proof,args:method===fundMethod?['00'.repeat(64)]:[n(4),buyer]});
const base=()=>({script:method.scriptHex,proof:method.proof,args:[n(4),buyer],inputs:[input(coin(10,offered,[root]),method),input(coin(12,quote,[funding.policy.root]),fundMethod),input(coin(100,null,[funding.policy.root]),fundMethod)],outputs:[coin(6,offered,[root]),coin(4,offered,[buyer]),coin(12,quote,[seller])]});
const invoke=c=>{const p=spawnSync(python,[runner],{env:{...process.env,PYTHONPATH:reference},input:JSON.stringify(c),encoding:'utf8'});assert.equal(p.status,0,p.stderr);return JSON.parse(p.stdout);};
const records=[];
function check(name,c,expected,evidence={}){const result=invoke(c);records.push({name,source,artifact,fundingArtifact:funding,case:c,sourceExpected:expected,bytecodeResult:result,...evidence});if(process.env.LOTUS_V2_CABI04_RESULTS){mkdirSync(process.env.LOTUS_V2_CABI04_RESULTS,{recursive:true});writeFileSync(`${process.env.LOTUS_V2_CABI04_RESULTS}/partial-limit-order.json`,JSON.stringify(records,null,2)+'\n');}assert.equal(result.status,expected,JSON.stringify(result));return result;}
function attach(c){for(const index of [1,2]){const p=invoke({...c,input_index:index,prepare:true});assert.ok(p.message,JSON.stringify(p));c.inputs[index].args=[Buffer.from(schnorr.sign(Buffer.from(p.message,'hex'),privateKey,new Uint8Array(32))).toString('hex')];}return c;}
test('partial fill delivers units, settles exact quote, and preserves remainder policy in exact signed transaction',()=>{
 const c=base();check('unsigned permissionless order invocation',c,'accepted');
 const signed=attach(c);for(const index of [0,1,2])check(`signed transaction input ${index}`,{...signed,input_index:index},'accepted');
 // The order witness has no signature; both funding inputs authenticate the same core.
 const stale=structuredClone(signed);stale.outputs[1].value++;check('funding signature output mutation',{...stale,input_index:1},'rejected');
 const repeat=base();repeat.inputs[0].coin.value=6;repeat.inputs[0].args=[n(2),buyer];repeat.inputs[1].coin.value=6;repeat.outputs=[coin(4,offered,[root]),coin(2,offered,[buyer]),coin(6,quote,[seller])];check('second partial fill preserves remaining order',repeat,'accepted');
});
test('partial fill rejects adversarial amounts, assets, policies, duplicate roles and extra order inputs',()=>{
 const mutations={zero:c=>c.inputs[0].args[0]=n(0),fullFill:c=>c.inputs[0].args[0]=n(10),overFill:c=>c.inputs[0].args[0]=n(11),negative:c=>c.inputs[0].args[0]='ff'.repeat(16),remainingValue:c=>c.outputs[0].value++,buyerValue:c=>c.outputs[1].value++,quoteValue:c=>c.outputs[2].value--,quoteOverpay:c=>c.outputs[2].value++,remainingAsset:c=>c.outputs[0].token_id=quote,buyerAsset:c=>c.outputs[1].token_id=quote,paymentAsset:c=>c.outputs[2].token_id=offered,remainingPolicy:c=>c.outputs[0].branches=[wrong],buyerPolicy:c=>c.outputs[1].branches=[wrong],sellerPolicy:c=>c.outputs[2].branches=[wrong],buyerOrderAlias:c=>c.inputs[0].args[1]=root,missingRemaining:c=>c.outputs.splice(0,1),missingBuyer:c=>c.outputs.splice(1,1),missingPayment:c=>c.outputs.splice(2,1),duplicateRemaining:c=>c.outputs.push(structuredClone(c.outputs[0])),duplicateBuyer:c=>c.outputs.push(structuredClone(c.outputs[1])),duplicatePayment:c=>c.outputs.push(structuredClone(c.outputs[2])),extraOutput:c=>c.outputs.push(coin(1,null,[wrong])),extraOfferedInput:c=>c.inputs.push(input(coin(1,offered,[funding.policy.root]),fundMethod)),extraOrderInput:c=>c.inputs.push(input(coin(10,offered,[root]),method)),extraOtherAssetOrder:c=>c.inputs.push(input(coin(1,wrong,[root]),method)),extraLateBranchOrder:c=>{const i=input(coin(1,wrong,[funding.policy.root,...Array.from({length:14},(_,k)=>(0x80+k).toString(16).repeat(32)),root]),fundMethod);i.coin.paths=[[0],[15]];c.inputs.push(i);},extraOptionalOrder:c=>{const i=input(coin(1,wrong,[root,funding.policy.root]),method);i.coin.paths=[[0],[1]];c.inputs.push(i);},buyerHostage:c=>{c.outputs[1].branches.push(wrong);c.outputs[1].paths=[[0,1]];},sellerHostage:c=>{c.outputs[2].branches.push(wrong);c.outputs[2].paths=[[0,1]];},remainingHostage:c=>{c.outputs[0].branches.push(wrong);c.outputs[0].paths=[[0,1]];}};
 for(const [name,mutate] of Object.entries(mutations)){const c=base();mutate(c);check(name,c,'rejected');}
});
test('partial fill preserves all pre-existing successor policy branches and paths',()=>{
 const c=base();c.inputs[0].coin.branches.push(wrong);c.outputs[0].branches.push(wrong);
 check('preserve unexecuted data branch',c,'accepted');
 const changed=structuredClone(c);changed.outputs[0].branches[1]=seller;check('substituted data branch',changed,'rejected');
 const hostage=structuredClone(c);hostage.outputs[0].paths=[[0,1]];check('substituted successor path',hostage,'rejected');
});
test('partial order package compilation is byte-identical and input mandatory predicate uses assigned dd',async()=>{
 const dir=mkdtempSync(join(tmpdir(),'cabi04-partial-'));try{mkdirSync(join(dir,'src'));writeFileSync(join(dir,'lotus.toml'),'[package]\nname = "partial"\nversion = "0.1.0"\nkind = "contract"\nsource = "src"\nentry = "main"\nmodules = ["main"]\n');writeFileSync(join(dir,'src/main.lotus'),source);updateLock(dir);const a=(await compilePackage(dir,options)).artifact;assert.deepEqual(a.methods.map(m=>m.scriptHex),artifact.methods.map(m=>m.scriptHex));}finally{rmSync(dir,{recursive:true,force:true});}
 const s='contract Guard { function spend() { for input in tx.inputs { require(input.coin.requires_branch(this.root)); } } }',a=compileContract(s,{contract:'Guard',bindings:{}}),m=a.methods[0];assert.ok(m.sourceMap.some(e=>e.op==='UTXOREQUIRESBRANCH'&&m.scriptHex.slice(e.byteStart*2,e.byteEnd*2)==='dd'));
 const c={script:m.scriptHex,proof:m.proof,args:[],coin:coin(1,offered,[a.policy.root]),outputs:[coin(1,offered,[a.policy.root])]};check('input mandatory root',c,'accepted',{source:s,artifact:a});
});

test('partial fill preserves a mandatory token-rules branch and executes both obligations independently',()=>{
 const rules=compileContract('contract Rules { function transfer() { require(true); } }',{contract:'Rules',bindings:{}}),r=rules.methods[0];
 const c=base();c.inputs[0].coin.branches.push(rules.policy.root);c.inputs[0].coin.paths=[[0,1]];
 c.outputs[0].branches.push(rules.policy.root);c.outputs[0].paths=[[0,1]];
 c.inputs[0].witnesses=[{script:method.scriptHex,proof:method.proof,args:c.inputs[0].args},{script:r.scriptHex,proof:r.proof,args:[]}];
 check('order with mandatory rules',c,'accepted');check('independent rules invocation',{...c,witness_index:1},'accepted',{rulesArtifact:rules,rulesSource:'contract Rules { function transfer() { require(true); } }'});
 const removed=structuredClone(c);removed.outputs[0].branches.pop();removed.outputs[0].paths=[[0]];check('stripped mandatory rules',removed,'rejected');
 const bypass=structuredClone(c);bypass.outputs[0].paths=[[0],[1]];check('weakened mandatory rules paths',bypass,'rejected');
});
