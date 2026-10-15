import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,mkdirSync,writeFileSync,mkdtempSync,rmSync} from 'node:fs';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {schnorr} from '@noble/curves/secp256k1';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {compilePackage,updateLock} from '../dist/packages.js';
import {compileContract} from '../dist/generic.js';
const python=process.env.LOTUS_V2_PYTHON ?? 'python3';
const reference=process.env.LOTUS_V2_VM_REFERENCE_PACKAGE ?? fileURLToPath(new URL('../../lotus-v2-reference/',import.meta.url));
const runner=fileURLToPath(new URL('cabi04-reference.py',import.meta.url));
const files=new URL('../examples/gallery/',import.meta.url), asset='11'.repeat(32), other='22'.repeat(32);
const int=n=>{let x=BigInt.asUintN(128,BigInt(n)),s='';for(let i=0;i<16;i++,x>>=8n)s+=Number(x&255n).toString(16).padStart(2,'0');return s;};
const state=n=>createHash('sha256').update(Buffer.from(int(n),'hex')).digest('hex');
const coin=(branches,paths=[[0]])=>({flags:1,value:5,token_id:asset,branches,paths});
const source=name=>readFileSync(new URL(`${name}.lotus`,files),'utf8');
const run=c=>{const p=spawnSync(python,[runner],{encoding:'utf8',env:{...process.env,PYTHONPATH:reference},input:JSON.stringify(c)});assert.equal(p.status,0,p.stderr);return JSON.parse(p.stdout);};
const records=[];
function check(name,source,artifact,c,expected){const result=run(c);records.push({name,source,artifact,case:c,sourceExpected:expected,bytecodeResult:result});if(process.env.LOTUS_V2_CABI04_RESULTS){mkdirSync(process.env.LOTUS_V2_CABI04_RESULTS,{recursive:true});writeFileSync(`${process.env.LOTUS_V2_CABI04_RESULTS}/frontend.json`,JSON.stringify(records,null,2)+'\n');}assert.equal(result.status,expected,JSON.stringify(result));return result;}
test('committed counter state authenticates old value and constrains successor independently of amount',()=>{
 const s=source('counter'),a=compileContract(s,{contract:'Counter',bindings:{}}),m=a.methods[0],root=a.policy.root;
 const base={script:m.scriptHex,proof:m.proof,args:[int(9)],coin:coin([root,state(9)]),outputs:[coin([root,state(10)])]};
 check('counter positive',s,a,base,'accepted');
 for(const n of [0n,(1n<<127n)-2n]){const c=structuredClone(base);c.args=[int(n)];c.coin.branches[1]=state(n);c.outputs[0].branches[1]=state(n+1n);check(`counter boundary ${n}`,s,a,c,'accepted');}
 const mutations={stale:c=>c.outputs[0].branches[1]=state(9),skip:c=>c.outputs[0].branches[1]=state(11),forged:c=>c.args=[int(8)],asset:c=>c.outputs[0].token_id=other,value:c=>c.outputs[0].value++,missing:c=>c.outputs=[],duplicate:c=>c.outputs.push(structuredClone(c.outputs[0])),hostage:c=>c.outputs[0].paths=[[0,1]],bypass:c=>c.outputs[0].paths=[[0],[1]],extraBranch:c=>c.outputs[0].branches.push(other),policy:c=>c.outputs[0].branches[0]=other,reorder:c=>c.outputs[0].branches.reverse(),negative:c=>c.args=[int(-1)],overflow:c=>{c.args=[int((1n<<127n)-1n)];c.coin.branches[1]=state((1n<<127n)-1n);}};
 for(const [name,mutate] of Object.entries(mutations)){const c=structuredClone(base);mutate(c);check(`counter ${name}`,s,a,c,'rejected');}
});
const privateKey=n=>Buffer.from(n.toString(16).padStart(64,'0'),'hex');
const owner=schnorr.getPublicKey(privateKey(3)),guardian=schnorr.getPublicKey(privateKey(4));
const bound={Vault:{owner:Buffer.from(owner).toString('hex'),guardian:Buffer.from(guardian).toString('hex'),recovery_height:'100'}};
function signed(c,key){const request=run({...c,prepare:true});assert.ok(request.message,JSON.stringify(request));return {...c,args:[Buffer.from(schnorr.sign(Buffer.from(request.message,'hex'),privateKey(key),new Uint8Array(32))).toString('hex')]};}
test('vault recovery checks signed guardian and absolute lock below/at/above boundary',()=>{
 const s=source('vault'),a=compileContract(s,{contract:'Vault',bindings:bound}),m=a.methods.find(x=>x.name==='recover');
 const base={script:m.scriptHex,proof:m.proof,args:['00'.repeat(64)],coin:coin([a.policy.root]),outputs:[coin([other])]};
 for(const height of [99,100,101])check(`recovery height ${height}`,s,a,signed({...base,lock:height*256+1},4),height>=100?'accepted':'rejected');
 check('recovery wrong kind',s,a,signed({...base,lock:100*256+2},4),'rejected');
 check('recovery disabled lock',s,a,signed({...base,lock:0},4),'rejected');
 check('recovery wrong signer',s,a,signed({...base,lock:100*256+1},3),'rejected');
 const stale=signed({...base,lock:100*256+1},4);stale.outputs[0].value++;check('recovery stale output signature',s,a,stale,'rejected');
});
test('owner continuation preserves paths and other policy branches',()=>{
 const s=source('vault'),a=compileContract(s,{contract:'Vault',bindings:bound}),m=a.methods.find(x=>x.name==='preserve');
 // Additional unexecuted data branch must remain untouched; only path [[0]] executes.
 const base={script:m.scriptHex,proof:m.proof,args:['00'.repeat(64)],coin:coin([a.policy.root,other]),outputs:[coin([a.policy.root,other])]};
 check('owner preserve data branch',s,a,signed(base,3),'accepted');
 for(const [name,mutate] of Object.entries({policy:c=>c.outputs[0].branches[1]=asset,paths:c=>c.outputs[0].paths=[[0,1]],asset:c=>c.outputs[0].token_id=other,value:c=>c.outputs[0].value++,missing:c=>c.outputs=[],duplicate:c=>c.outputs.push(structuredClone(c.outputs[0]))})){const c=structuredClone(base);mutate(c);check(`owner ${name}`,s,a,signed(c,3),'rejected');}
 check('owner wrong signer',s,a,signed(base,4),'rejected');
});
test('new primitives enforce argument types and receiver types',()=>{
 for(const body of ['require(check_lock(true, 100));','require(check_sequence(1));','require(sha256(num_bytes(true)) == sha256(num_bytes(0)));','require(this.coin.branch(true) == this.coin.branch(0));','require(this.coin.branch_count(1) == 2);','require(this.coin.exclusive_branch(this.root));','for output in tx.outputs { require(output.coin.exclusive_branch(this.root)); }'])assert.throws(()=>compileContract(`contract Bad { function spend() { ${body} } }`,{contract:'Bad',bindings:{}}));
 const helper='function encoded(n: Int): Bytes(16) { return num_bytes(n); } contract HelperCounter { function spend(n: Int) { require(sha256(encoded(n)) == sha256(num_bytes(n))); } }';
 assert.ok(compileContract(helper,{contract:'HelperCounter',bindings:{}}).methods[0].scriptHex);
});

test('branch index bounds and numeric byte casts reject adversarial runtime arguments',()=>{
 const programs=[
  ['Index', 'contract Index { function spend(i: Int) { require(this.coin.branch(i) == this.coin.branch(0)); } }', [-1n,2n,65536n]],
  ['Cast', 'contract Cast { function spend(n: Int) { require(sha256(num_bytes(n)) == sha256(num_bytes(n))); } }', ['','00','00'.repeat(17)]],
 ];
 for(const [contract,s,values] of programs){const a=compileContract(s,{contract,bindings:{}}),m=a.methods[0];for(const value of values){const c={script:m.scriptHex,proof:m.proof,args:[typeof value==='bigint'?int(value):value],coin:coin([a.policy.root,other]),outputs:[coin([a.policy.root,other])]};check(`${contract} invalid ${value}`,s,a,c,'rejected');}}
});
test('package and standalone frontends agree on new functions and branch receiver calls',async()=>{
 const dir=mkdtempSync(join(tmpdir(),'cabi04-package-'));
 try{
  mkdirSync(join(dir,'src'));
  writeFileSync(join(dir,'lotus.toml'),'[package]\nname = "cabi04"\nversion = "0.1.0"\nkind = "contract"\nsource = "src"\nentry = "main"\nmodules = ["main"]\n');
  const extra='contract Relative { function spend() { require(check_sequence(1, 5)); for input in tx.inputs { require(input.coin.branch_count() == 2); require(input.coin.branch(0) == input.branch(0)); } } }';
  for(const [file,contract,bindings] of [['counter','Counter',{}],['vault','Vault',bound],[null,'Relative',{}]]){
   const s=file?source(file):extra;writeFileSync(join(dir,'src/main.lotus'),s);updateLock(dir);
   const packaged=(await compilePackage(dir,{contract,bindings})).artifact;
   const standalone=compileContract(s,{contract,bindings});
   assert.deepEqual(packaged.methods.map(m=>[m.name,m.scriptHex,m.leaf]),standalone.methods.map(m=>[m.name,m.scriptHex,m.leaf]));
   assert.equal(packaged.policy.root,standalone.policy.root);
  }
 }finally{rmSync(dir,{recursive:true,force:true});}
});
test('lock primitives emit assigned f3/f4 and relative delay boundary executes',()=>{
 for(const [name,op] of [['check_lock',0xf3],['check_sequence',0xf4]]){
  const s=`contract Lock { function spend() { require(${name}(1, 5)); } }`,a=compileContract(s,{contract:'Lock',bindings:{}}),m=a.methods[0];
  assert.ok(m.sourceMap.some(entry=>entry.op===(op===0xf3?'CHECKLOCKTIMEVERIFY':'CHECKSEQUENCEVERIFY')&&m.scriptHex.slice(entry.byteStart*2,entry.byteEnd*2)===op.toString(16)));
  for(const bound of [4,5,6]){const c={script:m.scriptHex,proof:m.proof,args:[],coin:coin([a.policy.root]),outputs:[coin([a.policy.root])],...(op===0xf3?{lock:bound*256+1}:{sequence:bound})};check(`${name} ${bound}`,s,a,c,bound>=5?'accepted':'rejected');}
 }
});
