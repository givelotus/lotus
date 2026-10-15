import test from 'node:test';
import assert from 'node:assert/strict';
import { writeFileSync, appendFileSync } from 'node:fs';
import { resolveTarget } from '../dist/targets.js';
import { createHash } from 'node:crypto';
import { spawnSync } from 'node:child_process';
import { compileEcash } from '../dist/ecash.js';
const span={start:0,end:1,file:'hashlock.lotus'};
const bytes=hex=>({kind:'bytes',hex,span});
const bool=value=>({kind:'bool',value,span});
const arg=name=>({kind:'arg',name,span});
const equal=(left,right)=>({kind:'equal',left,right,span});
const require_=condition=>({kind:'require',condition,span});
const program=(args,body)=>({schema:'lotus/semantic-ir/1',entrypoint:'main',args:args.map(([name,type])=>({name,type,span})),body,span});
const byteType=length=>({kind:'bytes',length});
const hash=(kind,value)=>({kind,value,span});
const sha=hex=>createHash('sha256').update(Buffer.from(hex,'hex')).digest('hex');
const preimage='42'.repeat(32);
const hashlock=(kind='sha256')=>program([['preimage',byteType(32)]],[require_(equal(hash(kind,arg('preimage')),bytes(kind==='sha256'?sha(preimage):sha(sha(preimage)))))]);
function compile(input) {const result=compileEcash(input);assert.equal(result.ok,true,JSON.stringify(result));return result.artifact;}
function rejected(input,message) {const result=compileEcash(input);assert.equal(result.ok,false);assert.equal(result.artifact,undefined);assert.match(result.diagnostics.map(x=>x.message).join(' '),message);}

// Only a configured exact ABC harness can establish execution evidence.
const native=process.env.LOTUS_ECASH_NATIVE;
const evidence=process.env.LOTUS_ECASH_EVIDENCE;
function invoke(artifact,args) {
 const result=spawnSync(native,[artifact.scriptHex,...args],{encoding:'utf8',timeout:5000,maxBuffer:1048576});
 if(evidence)appendFileSync(evidence,JSON.stringify({artifact,args,exit:result.status,stdout:result.stdout,stderr:result.stderr})+'\n');
 assert.equal(result.status,0,result.stderr||result.stdout);
 const outcome=JSON.parse(result.stdout);
 assert.ok(['accepted','rejected'].includes(outcome.status),JSON.stringify(outcome));
 assert.equal(outcome.executed,true,JSON.stringify(outcome));
 return outcome;
}

test('eCash artifact is distinct, pinned, source-mapped and deterministic',()=>{
 const input=hashlock();const before=structuredClone(input);const artifact=compile(input);
 assert.deepEqual(compile(input),artifact);assert.deepEqual(input,before);
 assert.equal(artifact.schema,'ecash/script-artifact/1');assert.equal(artifact.target,'ecash');
 assert.equal(artifact.targetRevision,'1fb7db17c176cdea8a2c60d887891589382ee4e3');
 assert.ok(artifact.sourceMap.length>0);assert.equal(artifact.staticResources.scriptBytes,artifact.scriptHex.length/2);
 assert.ok(artifact.staticResources.opCount<=201);assert.ok(artifact.staticResources.maxStackItems<=1000);
 assert.equal(artifact.sourceMap.at(-1).byteEnd,artifact.scriptHex.length/2);
 assert.equal(artifact.scriptHex.slice(-4),'7551');
});

test('unsupported semantic nodes and bad types reject without an artifact',()=>{
 for(const kind of ['checksig','lotus-int128','transaction-reflection','define','invoke']) {
  const input=hashlock();input.body[0].condition={kind,span};rejected(input,/./);
 }
 const wrong=hashlock();wrong.args[0].type={kind:'Int'};rejected(wrong,/./);
 const missing=hashlock();missing.body[0].condition.left.value.name='unknown';rejected(missing,/./);
});

test('minimal exact-data pushes cover zero and PUSHDATA boundaries',()=>{
 for(const [hex,prefix] of [['','00'],['00','0100'],['01','51'],['10','60'],['81','4f'],['80','0180'],['11'.repeat(75),'4b'],['11'.repeat(76),'4c4c'],['11'.repeat(255),'4cff'],['11'.repeat(256),'4d0001'],['11'.repeat(520),'4d0802']]) {
  const artifact=compile(program([],[require_(equal(bytes(hex),bytes(hex)))]));
  assert.ok(artifact.scriptHex.startsWith(prefix),`${hex.length/2} bytes: ${artifact.scriptHex}`);
 }
});

test('resource validation includes unused arguments and both unexecuted branches',()=>{
 rejected(program([['unused',byteType(521)]],[require_(bool(true))]),/520/);
 const branch=program([],[{kind:'if',condition:bool(false),then:[require_(equal(bytes('11'.repeat(521)),bytes('11'.repeat(521))))],otherwise:[],span}]);
 rejected(branch,/520/);
 rejected(program([],Array.from({length:10},()=>require_(equal(bytes('11'.repeat(520)),bytes('11'.repeat(520)))))),/10000/);
 rejected(program([],Array.from({length:202},()=>require_(bool(true)))),/201/);
});

test('pinned ABC executes hashlocks, branches, exact byte widths and clean stacks',{skip:!native},()=>{
 const description=spawnSync(native,['--describe'],{encoding:'utf8',timeout:5000});
 assert.equal(description.status,0,description.stderr);
 const provenance=JSON.parse(description.stdout);
 const target=resolveTarget('ecash');
 assert.equal(provenance.revision,target.revision);
 assert.equal(provenance.tree,target.sourceTree);
 assert.deepEqual(provenance.flags.map(flag=>flag.replace(/^SCRIPT_(VERIFY_|ENABLE_)?/,'')).sort(),[...target.evaluationFlags].sort());
 if(evidence)writeFileSync(evidence,JSON.stringify({schema:'ecash-backend-native-evidence/1',native,provenance})+'\n',{flag:'wx'});
 for(const kind of ['sha256','hash256']) {
  const artifact=compile(hashlock(kind));
  const accepted=invoke(artifact,[preimage]);assert.equal(accepted.accepted,true,JSON.stringify(accepted));
  assert.deepEqual(accepted.final_stack,['01']);
  assert.equal(invoke(artifact,['43'.repeat(32)]).accepted,false);
  assert.equal(invoke(artifact,['42'.repeat(31)]).accepted,false);
  assert.equal(invoke(artifact,['',preimage]).accepted,false);
 }
 const repeated=compile(program([['x',byteType(32)]],[require_(equal(hash('sha256',arg('x')),hash('sha256',arg('x'))))]));
 assert.equal(invoke(repeated,[preimage]).accepted,true);
 const branch=compile(program([['flag',{kind:'bool'}]],[{kind:'if',condition:arg('flag'),then:[require_(bool(true))],otherwise:[require_(bool(false))],span}]));
 assert.equal(invoke(branch,['01']).accepted,true);
 assert.equal(invoke(branch,['']).accepted,false);
 for(const malformed of ['00','02','80','0100'])assert.equal(invoke(branch,[malformed]).accepted,false,malformed);
 for(const declarations of [[['x',byteType(32)],['flag',{kind:'bool'}]],[['flag',{kind:'bool'}],['x',byteType(32)]]]) {
  const mixed=compile(program(declarations,[{kind:'if',condition:arg('flag'),then:[require_(equal(arg('x'),bytes(preimage)))],otherwise:[require_(equal(arg('x'),bytes(preimage)))],span}]));
  for(const flag of ['','01']) {
   const args=declarations.map(([name])=>name==='x'?preimage:flag);
   assert.equal(invoke(mixed,args).accepted,true,JSON.stringify(declarations));
   assert.equal(invoke(mixed,['',...args]).accepted,false,'extra bottom argument');
  }
 }
 const boundary=compile(program([],Array.from({length:201},()=>require_(bool(true)))));
 assert.equal(boundary.staticResources.opCount,201);
 assert.equal(invoke(boundary,[]).accepted,true);
 const large=compile(program([],Array.from({length:9},()=>require_(equal(bytes('11'.repeat(520)),bytes('11'.repeat(520)))))));
 assert.equal(invoke(large,[]).accepted,true);
 assert.equal(invoke(compile(program([],[require_(bool(true))])),Array(1001).fill('')).accepted,false);
 const both=compile(program([['flag',{kind:'bool'}]],[{kind:'if',condition:arg('flag'),then:[require_(bool(true))],otherwise:[require_(bool(true))],span}]));
 for(const value of ['','01'])assert.equal(invoke(both,[value]).accepted,true);
 for(const length of [0,1,75,76,255,256,520]) {
  const data='11'.repeat(length);const artifact=compile(program([],[require_(equal(bytes(data),bytes(data)))]));
  assert.equal(invoke(artifact,[]).accepted,true,`push length ${length}`);
 }
});
