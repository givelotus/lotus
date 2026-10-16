// Synthetic fixtures conform to the reviewed contract, including full native locations.
import {test} from 'node:test';import assert from 'node:assert/strict';
import {Client,validateRoute,validateStatus,ApiError} from '../dist/client.js';
const h='ab'.repeat(32),x='cd'.repeat(32),loc={block_id:h,height:'0',tx_index:'0'},full={...loc,txid:h,txhash:x};
const out={txid:h,out_idx:'0',flags:'1',value:'1',has_token:true,token_id:h,is_burn:false,branches:[h],paths:[['0']],creation:full,spend:null};
const tx={txid:h,txhash:x,location:loc,status:'confirmed',confirmations:'1',input_count:'1',output_count:'1',wire_size:'2',lock:'0',core_available:true,witness_available:true,wire_available:true,finality:'unknown',accounting:{availability:'unknown'}};
const block={block_id:h,prev_id:h,height:'0',time:'0',size:'134',tx_count:'1',status:'confirmed',confirmations:'1',header_wire:'00'.repeat(134),header:{prev_id:h,bits:'0',time:'0',nonce:'0',version:'0',size:'134',height:'0',tx_root:h,state_root:h},body_availability:'complete',finality:'unknown'};
const asset={token_id:h,first_seen:full,event_count:'1',output_count:'1',metadata:{availability:'unknown',name:null,symbol:null,decimals:null,issuer:null,mint_cap:null},supply:{availability:'unknown'}};
const input={input_index:'0',flags:'1',kind:'spend',prev_txid:h,prev_index:'0',sequence:'0',path_index:'0',witness_count:'1',coinbase_data:{present:false,wire_ref:null},resolved_coin:{availability:'complete',output:Object.fromEntries(Object.entries(out).filter(([k])=>k!=='spend'))}};
const witness={witness_index:'0',script:{offset:'0',length:'1'},siblings:{count:'1',table_ref:{offset:'1',length:'33'},inline:[h]},arguments:{count:'1',table_ref:{offset:'34',length:'2'},inline:[{offset:'35',length:'1'}]}};
const wire={txid:h,txhash:x,total_bytes:'2',offset:'0',bytes_hex:'aabb',next_offset:null};
const event={token_id:h,location:full,spent_units:'1',output_units:'1',explicit_burn_units:'0',minted_units:'0',implicit_burn_units:'0',has_mint_input:false};
const page=items=>({items,next_cursor:null,exhausted:true});
const coverage={from_height:'0',through_height:'0',complete:true,scope:'canonical_confirmed'};
const snapshot={chain_id:h,genesis:h,profile_id:h,tip:h,height:'0',service_epoch:'review',generation:'1'};
const env=data=>({api_version:'1',snapshot_token:'opaque',snapshot,coverage,data});
const status={api_version:'1',ready:true,reason:'ready',indexed_anchor:{block_id:h,height:'0'},authoritative_anchor:{block_id:h,height:'0'},service_epoch:'review',generation:'1',binding:{chain_id:h,genesis:h,profile_id:h},coverage,capabilities:{blocks:true,transactions:true,transaction_wire:true,outputs:true,assets:true,asset_events:true,branches:true,accepted_pool:false,detached_history:false,finality:false},limits:{request_bytes:'32768',response_bytes:'262144',page_size:'100',cursor_bytes:'2048',wire_chunk_bytes:'32768',examined_records:'1024',key_reads:'4096'}};
const routeFixtures=[['/blocks',page([block])],['/blocks/'+h,block],['/blocks/by-height/0',block],['/blocks/'+h+'/transactions',page([tx])],['/transactions/by-id/'+h,tx],['/transactions/by-hash/'+x,tx],['/transactions/by-id/'+h+'/inputs',page([input])],['/transactions/by-id/'+h+'/outputs',page([out])],['/transactions/by-id/'+h+'/witnesses?input_index=0',page([witness])],['/transactions/by-id/'+h+'/wire?offset=0&length=32768',wire],['/outputs/'+h+'/0',out],['/assets',page([asset])],['/assets/'+h,asset],['/assets/'+h+'/events',page([event])],['/assets/'+h+'/outputs?view=history',page([out])],['/assets/'+h+'/outputs?view=unspent',page([out])],['/branches/outputs',{...page([{record:out,matching_positions:['0']}]),posting_reads:'1',work:'1'}],['/branches/utxos',{...page([{record:out,matching_positions:['0']}]),posting_reads:'1',work:'1'}]];
// Each required primitive is mutated independently; validators must reject before rendering.
function leaves(value,path=[]){if(value&&typeof value==='object')return Object.entries(value).flatMap(([k,v])=>leaves(v,[...path,k]));return [[path,value]];}
function set(value,path,replacement){let o=value;for(const k of path.slice(0,-1))o=o[k];o[path.at(-1)]=replacement;}
test('all 18 data routes validate required primitives and reject null/wrong primitive mutations',()=>{
 for(const [route,data] of routeFixtures){validateRoute(route,data);for(const [path,value] of leaves(data)){
  // Optional nulls are deliberately valid; extra block detail fields on block list are ignored.
  if(value===null||route==='/blocks'&&['header_wire','header','body_availability','finality'].includes(path[2])||route.endsWith('/transactions')&&['lock','core_available','witness_available','wire_available','finality','accounting'].includes(path[2]))continue;
  for(const replacement of [null,typeof value==='boolean'?'true':false]){const bad=structuredClone(data);set(bad,path,replacement);assert.throws(()=>validateRoute(route,bad),route+' '+path.join('.')+'='+replacement);}
 }}
});
test('independent review malformed response regressions remain rejected',()=>{
 const cases=[['/outputs/'+h+'/0',{...out,value:null}],['/outputs/'+h+'/0',{...out,out_idx:'4294967296'}],['/outputs/'+h+'/0',{...out,spend:{}}],['/transactions/by-id/'+h+'/inputs',page([{...input,flags:'3',path_index:null,resolved_coin:{availability:'complete'}}])],['/assets/'+h,{...asset,metadata:{availability:'unknown',name:'Trusted issuer',issuer:'verified'}}],['/transactions/by-id/'+x,tx],['/transactions/by-id/'+h+'/wire?offset=0&length=32768',{...wire,total_bytes:'0',offset:'1'}],['/blocks/'+h,{...block,header:false}],['/blocks',{items:[],next_cursor:'x'.repeat(2049),exhausted:true}],['/blocks',{items:[],next_cursor:'cursor',exhausted:true}],['/branches/outputs',page([])],['/outputs/'+h+'/0',{...out,paths:[['1']]}]];
 for(const [route,data] of cases)assert.throws(()=>validateRoute(route,data),route);
 // Raw native outputs preserve the token_id field even when not interpreted as a token.
 validateRoute('/outputs/'+h+'/0',{...out,has_token:false,token_id:h});
 validateRoute('/blocks',{items:[],next_cursor:'next',exhausted:false});
});
test('witness table counts, proof hashes, byte ranges and arguments are strict',()=>{for(const mutate of [w=>w.siblings.inline=['bad'],w=>w.siblings.count='2',w=>w.arguments.inline=['bad'],w=>w.arguments.inline[0].length=null,w=>w.script={offset:'18446744073709551615',length:'1'}]){const w=structuredClone(witness);mutate(w);assert.throws(()=>validateRoute('/transactions/by-id/'+h+'/witnesses',page([w])));}});
test('status requires complete typed anchors/binding/limits/capabilities and known readiness',()=>{
 validateStatus(status);for(const key of Object.keys(status)){const bad=structuredClone(status);delete bad[key];assert.throws(()=>validateStatus(bad),'missing '+key);}
 for(const mutate of [s=>s.reason='invented',s=>s.capabilities.accepted_pool=true,s=>s.capabilities.finality=true,s=>s.capabilities.detached_history=true,s=>s.indexed_anchor.height=null,s=>s.authoritative_anchor.block_id=x,s=>s.limits.page_size='101',s=>s.binding.chain_id=null]){const bad=structuredClone(status);mutate(bad);assert.throws(()=>validateStatus(bad));}
 const unavailable={...status,ready:false,reason:'authority_unknown',indexed_anchor:null,authoritative_anchor:null,generation:null,coverage:null};validateStatus(unavailable);
});
test('status streaming byte limit cancels before consuming oversized stream',async()=>{let chunks=0,cancelled=false;const stream=new ReadableStream({pull(c){chunks++;c.enqueue(new Uint8Array(65536));},cancel(){cancelled=true;}});const client=new Client('http://localhost',async()=>new Response(stream));await assert.rejects(client.status(new AbortController().signal),/256 KiB/);assert.equal(cancelled,true);assert.ok(chunks<=6);});
test('malformed 503 retains unavailable HTTP meaning; mismatched error codes fail',async()=>{for(const body of ['not JSON',JSON.stringify({error:{code:'wrong'}})]){const client=new Client('http://localhost',async()=>new Response(body,{status:503}));await assert.rejects(client.request('/blocks',new AbortController().signal),e=>e instanceof ApiError&&e.status===503);await assert.rejects(client.status(new AbortController().signal),e=>e instanceof ApiError&&e.status===503);}const client=new Client('http://localhost',async()=>Response.json({api_version:'1',error:{code:'stale_cursor',meaning:'Changed'},snapshot,coverage},{status:404}));await assert.rejects(client.request('/blocks',new AbortController().signal),/code\/status/);});
