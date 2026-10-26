import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {mkdtempSync,readFileSync,writeFileSync,readdirSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {spawnSync} from 'node:child_process';
import {compileContract,compileContractAsync,compileContractWithTrace} from '../dist/generic.js';
import {compileTargetContract} from '../dist/target-compiler.js';
import {CompileError} from '../dist/diagnostics.js';

const preimage='42'.repeat(32);
const sha=x=>createHash('sha256').update(Buffer.from(x,'hex')).digest('hex');
const source='contract Hashlock<expected: Bytes32> { function main(preimage: Bytes32) { require(sha256(preimage) == expected); } }';
const options={contract:'Hashlock',bindings:{Hashlock:{expected:sha(preimage)}}};
function rejection(run,code,pattern){
 assert.throws(run,error=>{
  assert.ok(error instanceof CompileError);
  assert.equal(error.diagnostics[0].code,code);
  assert.match(error.diagnostics[0].message,pattern);
  return true;
 });
}

test('default and explicit Lotus artifacts and scheduler results remain identical',async()=>{
 const before=compileContract(source,options);
 assert.deepEqual(compileTargetContract(source,options),before);
 assert.deepEqual(compileTargetContract(source,{...options,target:'lotus-v2'}),before);
 assert.deepEqual(compileContract(source,{...options,target:'lotus-v2'}),before);
 assert.deepEqual(await compileContractAsync(source,{...options,target:'lotus-v2'}),before);
 assert.deepEqual(await compileContractWithTrace(source,options),await compileContractWithTrace(source,{...options,target:'lotus-v2'}));
 // Historical optimizer output, independent of the new routing path.
 const c=compileContract('contract C { function m(x: Int) { require(x == 1); } }',{contract:'C',bindings:{}});
 assert.equal(c.methods[0].scriptHex,'4e924e');
 assert.equal(before.schema,'lotus-v2/contract-artifact/2');
});

test('explicit source eCash artifact has correct target and no Lotus policy wrappers',()=>{
 const result=compileTargetContract(source,{...options,target:'ecash'});
 assert.equal(result.schema,'ecash/script-artifact/1');assert.equal(result.target,'ecash');
 assert.equal(result.entrypoint,'main');assert.equal(result.args[0].type.length,32);
 assert.equal(result.policy,undefined);assert.equal(result.methods,undefined);assert.equal(result.root,undefined);
 assert.ok(result.sourceMap.some(m=>m.op==='SHA256'));
 const expression=result.sourceMap.find(m=>m.op==='SHA256').source;
 assert.equal(source.slice(expression.start,expression.end),'sha256(preimage)');
 assert.deepEqual(compileTargetContract(source,{...options,target:'ecash',optimize:false}),result);
});

test('source selection fails closed for unknown targets and unsupported capabilities',async()=>{
 for(const target of ['ECash','bitcoin','',null])rejection(()=>compileTargetContract(source,{...options,target}),'E1200',/Unknown compiler target/);
 rejection(()=>compileContract(source,{...options,target:'ecash'}),'E1201',/compileTargetContract/);
 await assert.rejects(compileContractAsync(source,{...options,target:'ecash'}),e=>e.diagnostics[0].code==='E1201');
 const inputs=[
  ['contract C { function m(x: Int) { require(x == 1); } }','sixteen-byte signed int128'],
  ['contract C { function m(s: Signature) { require(true); } }','P01 authenticated message'],
  ['contract C { function m() { for i in tx.inputs { require(true); } } }','transaction-context iteration'],
  ['contract C { function m() { require(output_value(0) == 1); } }','branch/path semantics'],
 ];
 for(const [s,message] of inputs)rejection(()=>compileTargetContract(s,{target:'ecash',contract:'C',bindings:{}},'target.lotus'),'E1201',new RegExp(message));
 rejection(()=>compileTargetContract(source,{...options,target:'ecash',optimize:true}),'E1203',/no optimizer/);
});

test('bounded source bytes are not silently narrowed to exact-byte IR',()=>{
 for(const s of [
  'contract C { function main(x: Bytes(32)) { require(x == x); } }',
  'contract C<x: Bytes(32)> { function main() { require(x == x); } }',
 ]){
  const o={contract:'C',bindings:{C:{x:'42'}},target:'ecash'};
  if(!s.includes('C<x'))o.bindings={};
  rejection(()=>compileTargetContract(s,o),'E1203',/maximum byte bound/);
 }
 const s='contract C<x: Bytes(32)> { function main() { require(x == x); } }';
 assert.equal(compileContract(s,{contract:'C',bindings:{C:{x:'42'}}}).methods.length,1);
});

test('selected method, helpers, constructor types and IR type failures are explicit',()=>{
 const multi='contract C { function main(x: Bytes32) { require(x == x); } function other(s: Signature) { require(true); } }';
 rejection(()=>compileTargetContract(multi,{target:'ecash',contract:'C',bindings:{}}),'E1202',/explicit selected method/);
 assert.equal(compileTargetContract(multi,{target:'ecash',method:'main',contract:'C',bindings:{}}).entrypoint,'main');
 rejection(()=>compileTargetContract(multi,{target:'ecash',method:'absent',contract:'C',bindings:{}}),'E1202',/unknown selected method/);
 const helper='function same(x: Bytes32): Bool { return x == x; } contract C { function main(x: Bytes32) { require(same(x)); } }';
 rejection(()=>compileTargetContract(helper,{target:'ecash',contract:'C',bindings:{}}),'E1203',/helper inlining/);
 rejection(()=>compileTargetContract(source,{...options,target:'ecash',bindings:{Hashlock:{expected:'42'}}}),'E0604',/exactly 32 bytes/);
 const bad='contract C { function main(x: Bytes32) { require(x); } }';
 assert.throws(()=>compileTargetContract(bad,{target:'ecash',contract:'C',bindings:{}},'bad.lotus'),error=>{
  assert.equal(error.diagnostics[0].code,'E1204');assert.equal(error.diagnostics[0].primary.file,'bad.lotus');
  assert.ok(error.diagnostics[0].primary.span.end>error.diagnostics[0].primary.span.start);return true;
 });
});

const native=process.env.LOTUS_ECASH_NATIVE;
test('real source predicates execute in exact pinned ABC interpreter',{skip:!native},()=>{
 const descriptor=JSON.parse(spawnSync(native,['--describe'],{encoding:'utf8',timeout:5000}).stdout);
 assert.equal(descriptor.revision,'1fb7db17c176cdea8a2c60d887891589382ee4e3');assert.equal(descriptor.flags_mask,15820783);
 const execute=(artifact,args)=>{
  const run=spawnSync(native,[artifact.scriptHex,...args],{encoding:'utf8',timeout:5000});
  assert.equal(run.status,0,run.stderr);return JSON.parse(run.stdout);
 };
 for(const kind of ['sha256','hash256']){
  const s=source.replace('sha256',kind),expected=kind==='sha256'?sha(preimage):sha(sha(preimage));
  const artifact=compileTargetContract(s,{...options,target:'ecash',bindings:{Hashlock:{expected}}});
  assert.equal(execute(artifact,[preimage]).accepted,true);
  for(const args of [['43'.repeat(32)],['42'.repeat(31)],['',preimage]])assert.equal(execute(artifact,args).accepted,false);
 }
 const branch='contract C { function main(flag: Bool, x: Bytes32) { if (flag) { require(sha256(x) == sha256(x)); } else { require(hash256(x) == hash256(x)); } } }';
 const artifact=compileTargetContract(branch,{target:'ecash',contract:'C',bindings:{}});
 for(const flag of ['','01'])assert.equal(execute(artifact,[flag,preimage]).accepted,true);
 for(const flag of ['00','02','80'])assert.equal(execute(artifact,[flag,preimage]).accepted,false);
});

test('CLI routes JSON target options and emits only script artifact for eCash',()=>{
 const dir=mkdtempSync(join(tmpdir(),'lotus-target-cli-'));
 const input=join(dir,'hashlock.lotus'),config=join(dir,'options.json'),out=join(dir,'out');
 writeFileSync(input,source);writeFileSync(config,JSON.stringify({...options,target:'ecash'}));
 const cli=new URL('../dist/generic-cli.js',import.meta.url).pathname;
 const run=(args)=>spawnSync(process.execPath,[cli,...args],{encoding:'utf8',timeout:5000});
 const result=run([input,config,out]);assert.equal(result.status,0,result.stderr);
 assert.deepEqual(readdirSync(out).sort(),['artifact.json','script.hex']);
 assert.equal(JSON.parse(readFileSync(join(out,'artifact.json'))).schema,'ecash/script-artifact/1');
 const traced=run([input,config,join(dir,'trace'),'--trace']);assert.equal(traced.status,1);assert.match(traced.stderr,/E1203/);
 const packaged=run(['--package',dir,config,join(dir,'package')]);assert.equal(packaged.status,1);assert.match(packaged.stderr,/package linking/);
 writeFileSync(config,'null');const malformed=run([input,config,join(dir,'malformed')]);assert.equal(malformed.status,1);assert.match(malformed.stderr,/E0601/);
 writeFileSync(config,JSON.stringify({...options,target:'unknown'}));const unknown=run([input,config,join(dir,'unknown')]);assert.equal(unknown.status,1);assert.match(unknown.stderr,/E1200/);
});
