import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {compileContract} from '../dist/generic.js';
import {buildPolicy,assertPolicyArtifact,selectPolicyWitnesses,selectMintWitness,programArtifactDigest,canonicalPolicyJson,spendPolicyBranch,requireEveryPath} from '../dist/policy.js';
const metadata={target:'P01-P02-P03-candidate-2026-10-14',targetDigest:'11'.repeat(32),profileDigest:'22'.repeat(32),compilerRevision:'lc03-test',optimizerMode:'off',constructor:[],bindings:{},provenance:{}};
function program(n){return compileContract(`contract A { entry run() { require(${n} == ${n}); } }`,{contract:'A',bindings:{},optimize:false,languageVersion:1});}
const a=program(1),b=program(2);
const branch=(name,index,a)=>({name,index,kind:'spend',root:a.policy.root,artifactDigest:programArtifactDigest(a)});
const spec={name:'Escrow',branches:[branch('owner',0,a),branch('rules',1,b),{name:'state',index:2,kind:'data',root:'33'.repeat(32)}],paths:[{name:'all',branches:['rules','owner']},{name:'ownerOnly',branches:['owner']}]};
const witness=(name,a)=>({branchName:name,artifact:a,methodName:'run',arguments:{}});
function py(op,payload){const r=spawnSync(process.env.LOTUS_V2_PYTHON??'python3',['-c',`import sys,json\nsys.path.insert(0,'python')\nfrom lotus_v2_policy_lc03 import *\ndef restore(x):\n if isinstance(x,dict):\n  if set(x)=={'__lc03bytes'}: return bytes.fromhex(x['__lc03bytes'])\n  if set(x)=={'__lc03int'}: return int(x['__lc03int'])\n  return {k:restore(v) for k,v in x.items()}\n if isinstance(x,list): return [restore(v) for v in x]\n return x\np=restore(json.load(sys.stdin))\ntry:\n if p['op']=='build': out=build_policy(p['spec'],p['metadata'])\n elif p['op']=='load': out=assert_policy_artifact(p['artifact'])\n elif p['op']=='select': out=select_policy_witnesses(p['artifact'],p['path'],p['witnesses'])\n else: out=select_mint_witness(p['witness'])\n print(json.dumps({'ok':out},sort_keys=True))\nexcept ValueError as e: print(json.dumps({'error':str(e)}))`],{input:JSON.stringify({op,...payload},(_k,v)=>v instanceof Uint8Array?{__lc03bytes:Buffer.from(v).toString('hex')}:typeof v==='bigint'?{__lc03int:String(v)}:v),encoding:'utf8'});assert.equal(r.status,0,r.stderr);return JSON.parse(r.stdout);}
function parityError(s,error){assert.throws(()=>buildPolicy(s,metadata),{message:error});assert.deepEqual(py('build',{spec:s,metadata}),{error});}
test('LC03 canonical policy bytes and named paths ignore declaration order',()=>{const p=buildPolicy(spec,metadata);assertPolicyArtifact(p);assert.deepEqual(py('build',{spec,metadata}),{ok:p});assert.equal(p.policyEncoding,`03${a.policy.root}${b.policy.root}${'33'.repeat(32)}020100020001`);assert.deepEqual(p.paths.map(p=>[p.name,p.pathIndex,p.slots]),[['ownerOnly',0,[0]],['all',1,[0,1]]]);for(const branches of [spec.branches,[...spec.branches].reverse()])for(const paths of [spec.paths,[...spec.paths].reverse()])assert.deepEqual(buildPolicy({...spec,branches,paths},metadata),p);assert.equal(buildPolicy({...spec,name:'Renamed'},metadata).policyDigest,p.policyDigest);});
test('LC03 invalid slots roots paths data and bounds reject identically',()=>{const mutate=fn=>{const s=structuredClone(spec);fn(s);return s;};parityError(mutate(s=>s.branches[2].index=3),'policy slots');parityError(mutate(s=>s.branches[2].index=1),'policy slots');parityError(mutate(s=>s.branches[2].root=s.branches[0].root),'duplicate branch root');parityError(mutate(s=>s.paths[0].branches=['state']),'data branch in path');parityError(mutate(s=>s.paths[0].branches=['owner','owner']),'duplicate path slot');parityError(mutate(s=>s.paths[0].branches=['owner']),'duplicate path');parityError(mutate(s=>s.paths=[]),'policy branch/path count');parityError(mutate(s=>s.branches=Array(17).fill(s.branches[0])),'policy branch/path count');parityError(mutate(s=>s.paths=Array(17).fill(s.paths[0])),'policy branch/path count');});
test('LC03 named witnesses exact membership and canonical branch order',()=>{const p=buildPolicy(spec,metadata),ws=[witness('rules',b),witness('owner',a)],result=selectPolicyWitnesses(p,'all',ws);assert.deepEqual(result.witnesses.map(w=>w.branchIndex),[0,1]);assert.deepEqual(py('select',{artifact:p,path:'all',witnesses:ws}),{ok:result});for(const [w,error] of [[[ws[0]],'policy witness membership'],[[...ws,witness('extra',a)],'policy witness membership'],[[ws[0],ws[0]],'duplicate named witness']]){assert.throws(()=>selectPolicyWitnesses(p,'all',w),{message:error});assert.deepEqual(py('select',{artifact:p,path:'all',witnesses:w}),{error});}});
test('LC03 loaded artifacts and witness proofs/identities/kinds are checked',()=>{const p=buildPolicy(spec,metadata);const cases=[['proof',w=>w.artifact.methods[0].proof=['44'.repeat(32)],'policy program artifact'],['root',w=>w.artifact=b,'policy program identity'],['kind',w=>w.artifact.methods[0].invocation='mint','policy invocation kind'],['method',w=>w.methodName='missing','policy method'],['args',w=>w.arguments.extra=true,'policy arguments']];for(const [label,mutate,error] of cases){const w=structuredClone(witness('owner',a));mutate(w);assert.throws(()=>selectPolicyWitnesses(p,'ownerOnly',[w]),{message:error},label);assert.deepEqual(py('select',{artifact:p,path:'ownerOnly',witnesses:[w]}),{error});}for(const mutate of [p=>p.policyEncoding='00',p=>p.policyDigest='00'.repeat(32),p=>p.paths[0].pathIndex=9,p=>p.branches.reverse()]){const q=structuredClone(p);mutate(q);assert.throws(()=>assertPolicyArtifact(q));assert.ok(py('load',{artifact:q}).error);}});
test('LC03 mint has no output slot/path and rejects spend programs',()=>{const mint=compileContract('token A { mint run(delta: Amount) { require(delta > 0); } }',{contract:'A',bindings:{},languageVersion:1});const w={artifact:mint,methodName:'run',arguments:{}};const result=selectMintWitness(w);assert.equal(result.tokenId,mint.policy.root);assert.equal('branchIndex' in result,false);assert.equal('pathIndex' in result,false);assert.deepEqual(py('mint',{witness:w}),{ok:result});assert.throws(()=>selectMintWitness(witness('owner',a)),{message:'policy invocation kind'});});
test('LC03 canonical JSON rejects ambiguous diagnostic encodings',()=>{assert.equal(canonicalPolicyJson({b:1,a:'x'}),'{"a":"x","b":1}');for(const value of [1.5,Number.MAX_SAFE_INTEGER+1])assert.throws(()=>canonicalPolicyJson(value),{message:'policy JSON number'});assert.throws(()=>canonicalPolicyJson('é'),{message:'policy JSON string'});});

test('LC03 exact 16 branch/path bound and declaration permutations',()=>{
 const branches=Array.from({length:16},(_,i)=>({name:`b${i}`,index:i,kind:'spend',root:i.toString(16).padStart(64,'0'),artifactDigest:'44'.repeat(32)}));
 const full={name:'Bound',branches,paths:branches.map(b=>({name:`p${b.index}`,branches:[b.name]}))};
 const policy=buildPolicy(full,metadata);assertPolicyArtifact(policy);assert.deepEqual(py('build',{spec:full,metadata}),{ok:policy});
 const permute=xs=>xs.length?xs.flatMap((x,i)=>permute(xs.filter((_,j)=>i!==j)).map(rest=>[x,...rest])):[[]];
 const expected=buildPolicy(spec,metadata);for(const branches of permute(spec.branches))for(const paths of permute(spec.paths))assert.deepEqual(buildPolicy({...spec,branches,paths},metadata),expected);
 const renamed=structuredClone(spec);renamed.branches[0].name='holder';renamed.paths.forEach(p=>p.branches=p.branches.map(n=>n==='owner'?'holder':n));assert.equal(buildPolicy(renamed,metadata).policyEncoding,expected.policyEncoding);
});
test('LC03 typed spend branch rejects mint and mandatory branch assertion is explicit',()=>{
 assert.deepEqual(spendPolicyBranch('owner',0,a),spec.branches[0]);
 const mint=compileContract('token A { mint run(delta: Amount) { require(delta > 0); } }',{contract:'A',bindings:{},languageVersion:1});assert.throws(()=>spendPolicyBranch('mint',0,mint),{message:'policy invocation kind'});
 const p=buildPolicy(spec,metadata);requireEveryPath(p,'owner');for(const n of ['rules','state','unknown'])assert.throws(()=>requireEveryPath(p,n),{message:'policy every path'});
});

test('LC03 named argument encoding/order and malformed loaded artifacts parity',()=>{
 const artifact=compileContract('contract Args { entry run(n: Int, z: Bytes32) { require(n == n); require(z == z); } }',{contract:'Args',bindings:{},optimize:false,languageVersion:1});
 const policy=buildPolicy({name:'Args',branches:[spendPolicyBranch('args',0,artifact)],paths:[{name:'call',branches:['args']}]},metadata);
 const w={branchName:'args',artifact,methodName:'run',arguments:{z:new Uint8Array(32),n:123n}};
 const result=selectPolicyWitnesses(policy,'call',[w]);assert.deepEqual(result.witnesses[0].argumentNames,['n','z']);assert.equal(result.witnesses[0].argumentOrder[0],'7b'+'00'.repeat(15));assert.deepEqual(py('select',{artifact:policy,path:'call',witnesses:[w]}),{ok:result});
 w.arguments.z=new Uint8Array(31);assert.throws(()=>selectPolicyWitnesses(policy,'call',[w]),{message:'policy argument value'});assert.deepEqual(py('select',{artifact:policy,path:'call',witnesses:[w]}),{error:'policy argument value'});
 for(const malformed of [null,{}, {...policy,paths:[{name:'x',slots:[false]}]}]){assert.throws(()=>assertPolicyArtifact(malformed),{message:'policy artifact structure'});assert.deepEqual(py('load',{artifact:malformed}),{error:'policy artifact structure'});}
 const mint=compileContract('token A { mint run(delta: Amount) { require(delta > 0); } }',{contract:'A',bindings:{},languageVersion:1});const mw={artifact:mint,methodName:'run',arguments:{},branchIndex:0};assert.throws(()=>selectMintWitness(mw),{message:'mint policy selector'});assert.deepEqual(py('mint',{witness:mw}),{error:'mint policy selector'});
});

test('LC03 malformed index types reject before sorting with exact peer errors',()=>{
 for(const index of [null,true,'0',0.5,-1,16]) {const invalid=structuredClone(spec);invalid.branches[1].index=index;parityError(invalid,'policy slots');}
});
test('LC03 closed schema rejects unknown fields at builder and loader boundaries',()=>{
 for(const mutate of [s=>s.extra=1,s=>s.branches[0].extra=1,s=>s.paths[0].extra=1]) {const invalid=structuredClone(spec);mutate(invalid);parityError(invalid,'policy unknown field');}
 const policy=buildPolicy(spec,metadata);
 for(const mutate of [p=>p.extra=1,p=>p.branches[0].extra=1,p=>p.paths[0].extra=1]) {const invalid=structuredClone(policy);mutate(invalid);assert.throws(()=>assertPolicyArtifact(invalid),{message:'policy unknown field'});assert.deepEqual(py('load',{artifact:invalid}),{error:'policy unknown field'});}
 const extra={...metadata,extra:1};assert.throws(()=>buildPolicy(spec,extra),{message:'policy unknown field'});assert.deepEqual(py('build',{spec,metadata:extra}),{error:'policy unknown field'});
});
test('LC03 real LC02 guard artifacts select and independently execute under both invocation kinds',()=>{
 const fixtures=[];
 for(const optimize of [false,true]) {
  const spend=compileContract('contract C { entry use(x: Int) { require(x > 0); } }',{contract:'C',bindings:{},languageVersion:1,optimize});
  const mint=compileContract('token C { mint issue(delta: Amount, x: Int) { require(x > 0); require(delta > 0); } }',{contract:'C',bindings:{},languageVersion:1,optimize});
  const policy=buildPolicy({name:'RealGuard',branches:[spendPolicyBranch('spend',0,spend)],paths:[{name:'call',branches:['spend']}]},metadata);
  const witnesses=[{branchName:'spend',artifact:spend,methodName:'use',arguments:{x:1n}}];
  const result=selectPolicyWitnesses(policy,'call',witnesses);assert.deepEqual(py('select',{artifact:policy,path:'call',witnesses}),{ok:result});
  const witness={artifact:mint,methodName:'issue',arguments:{x:1n}};assert.deepEqual(py('mint',{witness}),{ok:selectMintWitness(witness)});
  for(const [kind,artifact] of [['spend',spend],['mint',mint]]) {assert.equal(artifact.methods[0].sourceMap[0].op,'INVOCATIONKIND');fixtures.push({kind,method:artifact.methods[0]});}
 }
 const run=spawnSync(process.env.LOTUS_V2_PYTHON??'python3',[new URL('./lc02-vm.py',import.meta.url).pathname],{input:JSON.stringify(fixtures),encoding:'utf8',env:{...process.env,PYTHONPATH:new URL('../../lotus-v2-reference',import.meta.url).pathname}});
 assert.equal(run.status,0,run.stderr||run.stdout);assert.match(run.stdout,/16 cases passed/);
});
