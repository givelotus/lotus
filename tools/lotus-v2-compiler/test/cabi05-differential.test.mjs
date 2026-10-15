import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync,readFileSync,rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { corpus,signedCases,linkedCases,compare,saveReport,python,native,runCorpus } from './differential/harness.mjs';
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
