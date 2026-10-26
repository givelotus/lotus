import {test} from 'node:test';import assert from 'node:assert/strict';
import {ApiError,Client,PinnedView} from '../dist/client.js';
const h='ab'.repeat(32),snapshot={chain_id:h,genesis:h,profile_id:h,tip:h,height:'0',service_epoch:'retry-test',generation:'1'},coverage={from_height:'0',through_height:'0',complete:true,scope:'canonical_confirmed'};
const success=()=>Response.json({api_version:'1',snapshot_token:'original-token',snapshot,coverage,data:{items:[],next_cursor:null,exhausted:true,posting_reads:'0',work:'0'}});
const unavailable=(meaning='Busy')=>Response.json({api_version:'1',error:{code:'index_unavailable',meaning},snapshot:null,coverage:null},{status:503});
const stale=()=>Response.json({api_version:'1',error:{code:'stale_snapshot',meaning:'Changed publication'},snapshot,coverage},{status:409});
const policy={deadlineMs:1000,backoffMs:[1,2,3]};
test('GET retries503 with the exact token/URL/signal and records all attempts',async()=>{
 const calls=[];const client=new Client('http://localhost',async(url,options)=>{calls.push({url:String(url),signal:options.signal,method:options.method});return calls.length<3?unavailable('Busy'+calls.length):success();},policy);
 const result=await client.request('/blocks?page_size=1',new AbortController().signal,'original-token');assert.equal(result.snapshot_token,'original-token');assert.equal(calls.length,3);assert.ok(calls.every(c=>c.url===calls[0].url&&c.signal===calls[0].signal&&c.method==='GET'));assert.match(calls[0].url,/snapshot_token=original-token/);
 assert.deepEqual(client.requestTraces[0].attempts.map(a=>[a.status,a.meaning,a.retry_in_ms]),[[503,'Busy1',1],[503,'Busy2',2],[200,null,null]]);assert.equal(client.requestTraces[0].outcome,'success');
});
test('read-only branch POST retries identical pre-encoded body and pinned snapshot',async()=>{
 const body={any_branch:[h],positions:[{position:'0',roots:[h]}],page_size:'25',include_burn:true},calls=[];
 const client=new Client('http://localhost',async(url,options)=>{calls.push({url:String(url),body:options.body,method:options.method});if(options.method==='POST'&&calls.length===1){body.page_size='100';return unavailable();}return success();},policy);
 const view=new PinnedView(client,new AbortController().signal);await view.get('/blocks');calls.length=0;await view.get('/branches/outputs',body);
 assert.equal(calls.length,2);assert.deepEqual(calls[0],calls[1]);assert.equal(calls[0].method,'POST');assert.equal(JSON.parse(calls[0].body).page_size,'25');assert.match(calls[0].url,/snapshot_token=original-token/);
});
test('409 is never retried in-place, including after a503; other POST routes are never retried',async()=>{
 for(const firstBusy of [false,true]){let calls=0;const client=new Client('http://localhost',async()=>{calls++;return firstBusy&&calls===1?unavailable():stale();},policy);await assert.rejects(client.request('/blocks',new AbortController().signal,'original-token'),e=>e instanceof ApiError&&e.status===409);assert.equal(calls,firstBusy?2:1);assert.equal(client.requestTraces[0].attempts.at(-1).retry_in_ms,null);}
 let calls=0;const client=new Client('http://localhost',async()=>{calls++;return unavailable();},policy);await assert.rejects(client.request('/transactions/submit',new AbortController().signal,undefined,{wire:'00'}),e=>e.status===503);assert.equal(calls,1);
});
test('navigation abort cancels backoff and prevents another attempt',async()=>{
 let calls=0;const controller=new AbortController();const client=new Client('http://localhost',async()=>{calls++;return unavailable();},{deadlineMs:1000,backoffMs:[100,200,300]});const result=client.request('/blocks',controller.signal,'original-token');await new Promise(r=>setTimeout(r,10));controller.abort();await assert.rejects(result,{name:'AbortError'});await new Promise(r=>setTimeout(r,110));assert.equal(calls,1);assert.equal(client.requestTraces[0].outcome,'cancelled');
});
test('one original deadline includes503 delays and stalled headers',async()=>{
 const signals=[];let calls=0;const client=new Client('http://localhost',async(_,options)=>{signals.push(options.signal);calls++;if(calls<3)return unavailable();return new Promise(()=>{});},{deadlineMs:45,backoffMs:[10,10,10]});const started=performance.now();await assert.rejects(client.request('/blocks',new AbortController().signal),e=>e.status===503&&e.message.includes('deadline'));const elapsed=performance.now()-started;assert.equal(calls,3);assert.ok(elapsed>=35&&elapsed<200);assert.ok(signals.every(s=>s===signals[0]));assert.ok(signals[0].aborted);assert.equal(client.requestTraces[0].outcome,'deadline');
});
test('original deadline also cancels a stalled response body',async()=>{
 let cancelled=false;const stream=new ReadableStream({start(c){c.enqueue(new TextEncoder().encode('{'));},cancel(){cancelled=true;}});const client=new Client('http://localhost',async()=>new Response(stream),{deadlineMs:20,backoffMs:[1,2,3]});await assert.rejects(client.request('/blocks',new AbortController().signal),e=>e.status===503&&e.attempts.length===1);assert.equal(cancelled,true);assert.equal(client.requestTraces[0].outcome,'deadline');
});
test('exhaustion preserves the final unavailable error and bounded attempt trace',async()=>{
 let calls=0;const client=new Client('http://localhost',async()=>unavailable('Busy'+ ++calls),policy);await assert.rejects(client.request('/blocks',new AbortController().signal),e=>{assert.equal(e.status,503);assert.equal(e.message,'Busy4');assert.equal(e.attempts.length,4);assert.deepEqual(e.attempts.map(a=>a.retry_in_ms),[1,2,3,null]);return true;});assert.equal(calls,4);assert.equal(client.requestTraces[0].outcome,'error');
});
test('network/validation errors are not retried and trace history stays bounded',async()=>{
 let calls=0;const client=new Client('http://localhost',async()=>{calls++;throw new TypeError('Network failed');},policy);await assert.rejects(client.request('/blocks',new AbortController().signal),/Network failed/);assert.equal(calls,1);
 const valid=new Client('http://localhost',async()=>success(),policy);for(let i=0;i<35;i++)await valid.request('/blocks?before_height='+i,new AbortController().signal);assert.equal(valid.requestTraces.length,32);
 assert.throws(()=>new Client('http://localhost',fetch,{deadlineMs:0}));assert.throws(()=>new Client('http://localhost',fetch,{backoffMs:[1,2,3,4]}));
});
test('navigation abort cancels a stalled body without retrying',async()=>{
 let cancelled=false,calls=0;const controller=new AbortController();const client=new Client('http://localhost',async()=>{calls++;return new Response(new ReadableStream({start(c){c.enqueue(new TextEncoder().encode('{'));},cancel(){cancelled=true;}}));},policy);const result=client.request('/blocks',controller.signal);await new Promise(r=>setTimeout(r,10));controller.abort();await assert.rejects(result,{name:'AbortError'});assert.equal(calls,1);assert.equal(cancelled,true);assert.equal(client.requestTraces[0].outcome,'cancelled');
});
test('status GET uses the same bounded read retry policy',async()=>{
 const status={api_version:'1',ready:true,reason:'ready',indexed_anchor:{block_id:h,height:'0'},authoritative_anchor:{block_id:h,height:'0'},service_epoch:'retry-test',generation:'1',binding:{chain_id:h,genesis:h,profile_id:h},coverage,capabilities:{blocks:true,transactions:true,transaction_wire:true,outputs:true,assets:true,asset_events:true,branches:true,accepted_pool:false,detached_history:false,finality:false},limits:{request_bytes:'32768',response_bytes:'262144',page_size:'100',cursor_bytes:'2048',wire_chunk_bytes:'32768',examined_records:'1024',key_reads:'4096'}};let calls=0;const client=new Client('http://localhost',async()=>++calls===1?unavailable():Response.json(status),policy);assert.deepEqual(await client.status(new AbortController().signal),status);assert.equal(calls,2);assert.equal(client.requestTraces[0].outcome,'success');
});
