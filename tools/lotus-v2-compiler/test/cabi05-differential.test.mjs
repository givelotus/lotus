import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync,readFileSync,rmSync,writeFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { corpus,signedCases,linkedCases,compare,saveReport,python,native,runCorpus,comparison,reportFailed } from './differential/harness.mjs';
test('versioned seeded corpus is reproducible and bounds generation',()=>{
 assert.deepEqual(corpus(123,2),corpus(123,2));
 assert.notDeepEqual(corpus(123,2),corpus(124,2));
 assert.throws(()=>corpus(0,81));
 assert.throws(()=>runCorpus({schema:'future',cases:[]}));
 assert.ok(corpus(123,1).cases.some(c=>c.source&&c.artifact));
 assert.ok(corpus(123,1).cases.some(c=>c.id.startsWith('hand-')));
});
test('disagreements survive exclusive artifact retention; unsupported is separate',()=>{
 assert.deepEqual(compare({status:'accept',accounting_charge:10},{status:'accept',accounting_charge:11}),['accounting_charge']);
 assert.deepEqual(compare({status:'unsupported'},{status:'reject'}),[]);
 const dir=mkdtempSync(join(tmpdir(),'cabi05-'));
 try {
  const discrepancy={case:{id:'independent-discrepancy',script:'51',source:'retained'},discrepancies:['status'],python:{status:'accept'},native:{status:'reject'}};
  saveReport({cases:[discrepancy]},dir);
  const retained=JSON.parse(readFileSync(join(dir,'independent-discrepancy.json'),'utf8'));
  assert.deepEqual(retained.evidence,discrepancy);
  assert.deepEqual(retained.cases,[discrepancy.case]);
  assert.throws(()=>saveReport({cases:[]},dir),/EEXIST/);
 }finally{rmSync(dir,{recursive:true});}
});
test('compiled signed fixture accepts and single signature mutation rejects in Python',t=>{
 const cases=signedCases(); const results=cases.map(c=>python(c));
 if(!process.env.LOTUS_V2_PYTHON && results.some(r=>r.status==='tool-error')) {t.skip('set LOTUS_V2_PYTHON to reference venv');return;}
 assert.deepEqual(results.map(r=>r.status),['accept','reject']);
 assert.equal(results[0].leaf,cases[0].artifact.methods[0].leaf);
 assert.equal(native(cases[0]).status,'unsupported');
 if(process.env.LOTUS_V2_NATIVE_VM) {
  const n=cases.map(c=>native(c,process.env.LOTUS_V2_NATIVE_VM));
  assert.deepEqual(n.map(r=>r.status),['accept','reject']);
  for(let i=0;i<2;i++)assert.deepEqual(compare(results[i],n[i]),[]);
 }
});

test('linked package fixtures derive signing contexts from exact wire and resolved coins', async t=>{
 const cases=await linkedCases();
 assert.equal(cases.length,8);
 for(const c of cases) {
  assert.equal(c.signing,undefined);
  assert.equal(c.transaction_context.full_tx,c.native_context[0]);
  assert.equal(c.transaction_context.coins[0],c.native_context[4]);
  const r=python(c);
  if(!process.env.LOTUS_V2_PYTHON && r.status==='tool-error') { t.skip('authenticated reference VM unavailable');return; }
  assert.equal(r.status,c.expected,c.id);
  const mismatched=structuredClone(c);mismatched.args=['00'.repeat(64)];
  assert.equal(python(mismatched).status,'reject',`${c.id}: witness mismatch`);
  if(process.env.LOTUS_V2_NATIVE_VM) {
   const result=native(c,process.env.LOTUS_V2_NATIVE_VM);
   assert.equal(result.status,c.expected,c.id);
   assert.deepEqual(compare(r,result),[],c.id);
  }
 }
});

function mockRunner(directory,name,output,exit=0) {
 const file=join(directory,name);
 writeFileSync(file,`#!/bin/sh\nprintf '%s\\n' '${output.replaceAll("'", "'\\''")}'\nexit ${exit}\n`,{mode:0o700});
 return file;
}
test('native operational E remains distinct from consensus verdicts and protocol failures',()=>{
 const dir=mkdtempSync(join(tmpdir(),'cabi05-status-'));
 const c=corpus(1,0).cases[0];
 try {
  for(const [wire,status] of [['S 10','accept'],['A 0','accept'],['I -','reject'],['U -','unsupported'],['E -','operational-error'],['E 100 101 ab','operational-error']]) {
   const runner=mockRunner(dir,'runner',wire);
   const result=native(c,runner);
   assert.equal(result.status,status,wire);
   assert.equal(result.process.stdout,wire+'\n');
   if(status==='operational-error') {
    assert.equal(result.accounting_charge,undefined);
    assert.equal(result.automatic_success,undefined);
    const assessed=comparison({status:'accept',accounting_charge:100},result);
    assert.equal(assessed.status,'inconclusive');
    assert.deepEqual(assessed.outcomes,{python:'accept',native:'operational-error'});
    assert.deepEqual(assessed.reasons,['native:operational-error']);
   }
  }
  const failed=native(c,mockRunner(dir,'nonzero','E -',2));
  assert.equal(failed.status,'tool-error');
  assert.equal(failed.process.stdout,'E -\n');
  assert.equal(native(c,mockRunner(dir,'invalid','not-a-protocol')).status,'tool-error');
  assert.equal(comparison({status:'accept'},{status:'reject'}).status,'disagreement');
  assert.deepEqual(compare({status:'accept'},{status:'reject'}),['status']);
  assert.equal(comparison({status:'reject'},{status:'unsupported'}).status,'inconclusive');
  for(const [status,expected] of [['tool-error',true],['operational-error',true],['unsupported',false]]) {
   assert.equal(reportFailed({cases:[{python:{status:'accept'},native:{status},discrepancies:[]}]}),expected,status);
  }
  assert.equal(reportFailed({cases:[{python:{status:'accept'},native:{status:'reject'},discrepancies:['status']}]}),true);
 }finally{rmSync(dir,{recursive:true});}
});
test('CLI retains executable operational failure evidence and exits nonzero',()=>{
 const dir=mkdtempSync(join(tmpdir(),'cabi05-cli-operational-'));
 try {
  const nativeRunner=mockRunner(dir,'native','E 100 101');
  const pythonRunner=mockRunner(dir,'python',JSON.stringify({status:'accept',accepted_invocation:true}));
  const input=join(dir,'input.json');
  const c=corpus(1,0);c.cases=c.cases.slice(0,1);
  writeFileSync(input,JSON.stringify(c));
  const output=join(dir,'output');
  const run=spawnSync(process.execPath,[join(import.meta.dirname,'differential/run.mjs'),output,'1',input],{encoding:'utf8',env:{...process.env,LOTUS_V2_NATIVE_VM:nativeRunner,LOTUS_V2_PYTHON:pythonRunner}});
  assert.equal(run.status,1,run.stderr);
  const count=JSON.parse(run.stdout);
  assert.equal(count.operational_errors,1);
  assert.equal(count.inconclusive,1);
  assert.equal(count.tool_errors,0);
  const report=JSON.parse(readFileSync(join(output,'report.json'),'utf8'));
  assert.equal(reportFailed(report),true);
  assert.equal(report.cases[0].native.status,'operational-error');
  assert.deepEqual(report.cases[0].native.diagnostic_charges,{accounting:'100',enforcement:'101'});
  const retained=JSON.parse(readFileSync(join(output,c.cases[0].id+'.json'),'utf8'));
  assert.deepEqual(retained.cases,[c.cases[0]]);
  assert.equal(retained.evidence.native.process.stdout,'E 100 101\n');
  assert.equal(retained.evidence.comparison.status,'inconclusive');
 }finally{rmSync(dir,{recursive:true});}
});
