export type Json = null | boolean | string | number | Json[] | {[key: string]: Json};
export type ObjectValue = {[key: string]: Json};
export type Snapshot = {chain_id:string; genesis:string; profile_id:string; tip:string; height:string; service_epoch:string; generation:string};
export interface BlockSummary {block_id:string;prev_id:string;height:string;time:string;size:string;tx_count:string;status:'confirmed';confirmations:string}
export interface TxSummary {txid:string;txhash:string;location:ObjectValue;status:'confirmed';confirmations:string;input_count:string;output_count:string;wire_size:string}
export interface ByteRef {offset:string;length:string}
export type Envelope = {api_version:'1'; snapshot_token:string; snapshot:Snapshot; coverage:ObjectValue; data:ObjectValue};
export class ApiError extends Error { constructor(public status:number, public code:string, message:string) { super(message); } }
export const decimal = (value:unknown, max:bigint=340282366920938463463374607431768211455n):string => {
  if(typeof value !== 'string' || !/^(0|[1-9][0-9]*)$/.test(value) || value.length>39 || (max!==undefined && BigInt(value)>max)) throw new Error('Invalid canonical unsigned integer');
  return value;
};
export const hash = (value:unknown):string => { if(typeof value!=='string'|| !/^[0-9a-f]{64}$/.test(value)) throw new Error('Invalid native-order identity'); return value; };
export const object = (value:unknown):ObjectValue => { if(!value || typeof value!=='object'||Array.isArray(value)) throw new Error('Invalid object'); return value as ObjectValue; };
const u64=(v:unknown)=>decimal(v,18446744073709551615n);
const strings = new Set(['height','time','size','tx_count','confirmations','tx_index','input_count','output_count','wire_size','lock','input_index','flags','prev_index','sequence','path_index','witness_count','witness_index','count','offset','length','total_bytes','next_offset','out_idx','value','creation_height','spent_units','output_units','explicit_burn_units','minted_units','implicit_burn_units','event_count','posting_reads','work','position','generation','from_height','through_height','bits','nonce','version']);
const hashes=new Set(['block_id','prev_id','txid','txhash','prev_txid','token_id','tx_root','state_root','chain_id','genesis','profile_id','tip']);
// All wire integers must stay strings; arbitrary metadata text is never interpreted as markup.
export function validateTree(value:unknown,key='',depth=0): asserts value is Json {
  if(depth>40) throw new Error('Response nesting limit');
  if(strings.has(key) && value!==null) decimal(value);
  if(hashes.has(key) && value!==null) hash(value);
  if(typeof value==='number') throw new Error('Unexpected JSON number in explorer schema');
  if(key==='header_wire' && (typeof value!=='string'|| !/^[0-9a-f]{268}$/.test(value))) throw new Error('Invalid 134-byte header');
  if(key==='bytes_hex' && (typeof value!=='string'||value.length>65536|| !/^(?:[0-9a-f]{2})*$/.test(value))) throw new Error('Invalid wire chunk');
  if(Array.isArray(value)) { if(key==='branches'||key==='roots')value.forEach(hash); if(key==='matching_positions')value.forEach(v=>decimal(v,255n)); if(key==='paths')for(const path of value){if(!Array.isArray(path))throw new Error('Invalid ordered path');path.forEach(v=>decimal(v,255n));} if(value.length>4096) throw new Error('Array limit'); value.forEach(v=>validateTree(v,'',depth+1)); }
  else if(value && typeof value==='object') { if(Object.keys(value).length>128) throw new Error('Object limit'); for(const [k,v] of Object.entries(value)) validateTree(v,k,depth+1); }
  else if(!['string','boolean'].includes(typeof value)&&value!==null) throw new Error('Invalid JSON value');
  if(typeof value==='string' && value.length>262144) throw new Error('String limit');
}
export function validateEnvelope(value:unknown):Envelope {
 validateTree(value); const o=object(value),s=object(o.snapshot),c=object(o.coverage); object(o.data);
 if(o.api_version!=='1'||typeof o.snapshot_token!=='string'|| !o.snapshot_token || o.snapshot_token.length>2048) throw new Error('Invalid response envelope');
 for(const k of ['chain_id','genesis','profile_id','tip']) hash(s[k]); u64(s.height);u64(s.generation);
 if(typeof s.service_epoch!=='string'||!s.service_epoch||s.service_epoch.length>2048) throw new Error('Invalid service epoch');
 if(c.complete!==true||c.scope!=='canonical_confirmed'||c.from_height!=='0'||c.through_height!==s.height) throw new Error('Incomplete canonical coverage');
 return value as unknown as Envelope;
}
export function sameSnapshot(a:Envelope,b:Envelope):boolean { return a.snapshot_token===b.snapshot_token && (Object.keys(a.snapshot) as (keyof Snapshot)[]).every(k=>a.snapshot[k]===b.snapshot[k]); }
export type SearchKind='height'|'block'|'txid'|'txhash'|'asset'|'branch'|'outpoint';
export function searchRoute(kind:SearchKind,value:string):string {
 value=value.trim(); if(kind==='height') return '/blocks/by-height/'+u64(value);
 if(kind==='outpoint') { const parts=value.split(':'); if(parts.length!==2) throw new Error('Use TxID:output_index'); return '/outputs/'+hash(parts[0])+'/'+decimal(parts[1],4294967295n); }
 const id=hash(value); return ({block:'/blocks/',txid:'/transactions/by-id/',txhash:'/transactions/by-hash/',asset:'/assets/',branch:'/branches/outputs?root='} as const)[kind]+id;
}
export class Client {
 constructor(public base:string, private fetcher:typeof fetch=fetch) { const url=new URL(base); if(!['http:','https:'].includes(url.protocol)||url.username||url.password||url.search||url.hash) throw new Error('Use an HTTP API base without credentials/query/fragment'); this.base=base.replace(/\/$/,''); }
 async request(route:string, signal:AbortSignal, token?:string, body?:ObjectValue):Promise<Envelope> {
   if(token&&token.length>2048)throw new Error('Snapshot token limit'); const encoded=body?JSON.stringify(body):undefined;if(encoded&&new TextEncoder().encode(encoded).length>32768)throw new Error('Request body limit'); const url=new URL(this.base+'/v2/explorer/v1'+route); if(token) url.searchParams.set('snapshot_token',token);
   if(new TextEncoder().encode(url.search).length>32768)throw new Error('Query limit'); const response=await this.fetcher(url,{signal,cache:'no-store',method:body?'POST':'GET',headers:body?{'Content-Type':'application/json'}:{},body:encoded});
   const parsed=await readJson(response).catch(e=>{if(response.status===503)throw new ApiError(503,'index_unavailable','Unavailable service sent an invalid response: '+String(e));throw e;});
   if(!response.ok) { try{validateError(parsed,response.status);}catch(e){if(response.status===503)throw new ApiError(503,'index_unavailable','Unavailable service sent an invalid error envelope');throw e;} const error=object(object(parsed).error); throw new ApiError(response.status,String(error.code),String(error.meaning)); }
   const envelope=validateEnvelope(parsed); validateRoute(route,envelope.data); return envelope;
 }
 async status(signal:AbortSignal):Promise<ObjectValue> {
   const response=await this.fetcher(this.base+'/v2/explorer/v1/status',{signal,cache:'no-store'});
   const parsed=await readJson(response).catch(e=>{if(response.status===503)throw new ApiError(503,'index_unavailable','Unavailable service sent an invalid response: '+String(e));throw e;});
   if(!response.ok) {try{validateError(parsed,response.status);}catch(e){if(response.status===503)throw new ApiError(503,'index_unavailable','Unavailable service sent an invalid error envelope');throw e;}const e=object(object(parsed).error);throw new ApiError(response.status,String(e.code),String(e.meaning));}
   return validateStatus(parsed);
 }
}
export class PinnedView {
 envelope?:Envelope;
 constructor(public client:Client,public signal:AbortSignal){}
 async get(route:string,body?:ObjectValue):Promise<Envelope>{
  const result=await this.client.request(route,this.signal,this.envelope?.snapshot_token,body);
  if(this.envelope&&!sameSnapshot(this.envelope,result)) throw new ApiError(409,'stale_snapshot','Server mixed snapshot observations');
  this.envelope??=result; return result;
 }
}

const U8=255n,U32=4294967295n,U64=18446744073709551615n;
function requireFields(o:ObjectValue,fields:string[]){for(const f of fields)if(!(f in o))throw new Error('Missing response field: '+f);}
function bool(v:unknown){if(typeof v!=='boolean')throw new Error('Expected boolean');}
function literal(v:unknown,want:string|boolean|null){if(v!==want)throw new Error('Expected '+String(want));}
function text(v:unknown,max=2048){if(typeof v!=='string'||!v||v.length>max)throw new Error('Expected bounded nonempty string');}
function hex(v:unknown,bytes?:number){if(typeof v!=='string'|| !/^(?:[0-9a-f]{2})*$/.test(v)||(bytes!==undefined&&v.length!==bytes*2))throw new Error('Invalid exact hex bytes');}
function array(v:unknown,max=4096):Json[]{if(!Array.isArray(v)||v.length>max)throw new Error('Expected bounded array');return v as Json[];}
function fields(o:ObjectValue,hashes:string[]=[],integers:Record<string,bigint>={}){for(const k of hashes)hash(o[k]);for(const [k,max] of Object.entries(integers))decimal(o[k],max);}
function location(v:unknown,full=false){const o=object(v);fields(o,['block_id'],{height:U64,tx_index:U32});if(full)fields(o,['txid','txhash']);return o;}
function binding(v:unknown){const o=object(v);fields(o,['chain_id','genesis','profile_id']);return o;}
function snapshot(v:unknown){const o=binding(v);hash(o.tip);u64(o.height);u64(o.generation);text(o.service_epoch);return o;}
function coverage(v:unknown,complete?:boolean){const o=object(v);literal(o.from_height,'0');u64(o.through_height);bool(o.complete);if(complete!==undefined)literal(o.complete,complete);literal(o.scope,'canonical_confirmed');return o;}
function anchorValue(v:unknown){if(v===null)return null;const o=object(v);hash(o.block_id);u64(o.height);return o;}
function block(o:ObjectValue,detail=false){fields(o,['block_id','prev_id'],{height:U64,time:281474976710655n,size:U64,tx_count:U32,confirmations:U64});literal(o.status,'confirmed');if(o.confirmations==='0')throw new Error('Confirmed block without confirmations');if(detail){hex(o.header_wire,134);literal(o.body_availability,'complete');literal(o.finality,'unknown');const h=object(o.header);fields(h,['prev_id','tx_root','state_root'],{bits:U32,time:281474976710655n,nonce:U64,version:U32,size:U64,height:U64});for(const k of ['prev_id','height','time','size'])if(h[k]!==o[k])throw new Error('Contradictory block header');}}
function transaction(o:ObjectValue,detail=false){fields(o,['txid','txhash'],{confirmations:U64,input_count:U32,output_count:U32,wire_size:U64});location(o.location);literal(o.status,'confirmed');if(o.confirmations==='0')throw new Error('Confirmed transaction without confirmations');if(detail){u64(o.lock);for(const k of ['core_available','witness_available','wire_available'])literal(o[k],true);literal(o.finality,'unknown');literal(object(o.accounting).availability,'unknown');}}
function output(v:unknown,frozen=false){const o=object(v);fields(o,['txid','token_id'],{out_idx:U32,flags:U8});decimal(o.value);bool(o.has_token);bool(o.is_burn);const branches=array(o.branches);branches.forEach(hash);for(const path of array(o.paths)){for(const position of array(path)){decimal(position,U8);if(BigInt(String(position))>=BigInt(branches.length))throw new Error('Path references absent branch');}}location(o.creation,true);
 if(frozen){if('spend' in o)throw new Error('Frozen creation cannot contain spend state');}
 else {requireFields(o,['spend']);if(o.spend!==null){const s=object(o.spend);location(s.transaction,true);decimal(s.input_index,U32);}}
 return o;
}
function byteRef(v:unknown){const o=object(v);u64(o.offset);u64(o.length);if(BigInt(String(o.offset))+BigInt(String(o.length))>U64)throw new Error('Byte range overflow');}
function input(o:ObjectValue){fields(o,['prev_txid'],{input_index:U32,flags:U8,prev_index:U32,sequence:U32,witness_count:U32});const expected={spend:'1',coinbase:'2',mint:'3'};if(typeof o.kind!=='string'||!(o.kind in expected)||o.flags!==expected[o.kind as keyof typeof expected])throw new Error('Contradictory input kind/flags');
 const resolved=object(o.resolved_coin);if(o.kind==='spend'){decimal(o.path_index,U8);literal(resolved.availability,'complete');const prior=output(resolved.output,true);if(prior.txid!==o.prev_txid||prior.out_idx!==o.prev_index)throw new Error('Resolved creation does not match spend');}else{literal(o.path_index,null);literal(resolved.availability,'not_applicable');if('output' in resolved)throw new Error('Non-spend has resolved coin');}
 const data=object(o.coinbase_data);bool(data.present);if(data.present===true)byteRef(data.wire_ref);else literal(data.wire_ref,null);
}
function witness(o:ObjectValue){decimal(o.witness_index,U32);byteRef(o.script);for(const k of ['siblings','arguments']){const table=object(o[k]);decimal(table.count,U32);byteRef(table.table_ref);requireFields(table,['inline']);if(table.inline!==null){const entries=array(table.inline);if(BigInt(entries.length)!==BigInt(String(table.count)))throw new Error('Incomplete inline witness table');for(const entry of entries){if(k==='siblings')hash(entry);else byteRef(entry);}}}}
function asset(o:ObjectValue){hash(o.token_id);location(o.first_seen,true);fields(o,[],{event_count:U64,output_count:U64});const metadata=object(o.metadata);literal(metadata.availability,'unknown');for(const k of ['name','symbol','decimals','issuer','mint_cap'])literal(metadata[k],null);literal(object(o.supply).availability,'unknown');}
function event(o:ObjectValue){hash(o.token_id);location(o.location,true);for(const k of ['spent_units','output_units','explicit_burn_units','minted_units','implicit_burn_units'])decimal(o[k]);bool(o.has_mint_input);}
function wire(o:ObjectValue,query:URLSearchParams){fields(o,['txid','txhash'],{total_bytes:U64,offset:U64});hex(o.bytes_hex);const length=BigInt(String(o.bytes_hex).length/2),offset=BigInt(String(o.offset)),total=BigInt(String(o.total_bytes));const requestedOffset=BigInt(decimal(query.get('offset')??'0',U64)),requestedLength=BigInt(decimal(query.get('length')??'32768',32768n));if(requestedLength===0n||offset!==requestedOffset||offset>total||length>requestedLength||offset+length>total)throw new Error('Invalid wire range');if(offset+length===total)literal(o.next_offset,null);else{u64(o.next_offset);if(length===0n||BigInt(String(o.next_offset))!==offset+length)throw new Error('Invalid wire continuation');}}
function list(data:ObjectValue){const entries=array(data.items,100).map(object);bool(data.exhausted);requireFields(data,['next_cursor']);if(data.next_cursor!==null)text(data.next_cursor);if((data.exhausted===true)!==(data.next_cursor===null))throw new Error('Contradictory list exhaustion');return entries;}
export function validateRoute(route:string,data:ObjectValue){
 const url=new URL(route,'http://local'),path=url.pathname;let match:RegExpMatchArray|null;
 if(path==='/blocks'){for(const o of list(data))block(o);}
 else if((match=path.match(/^\/blocks\/(by-height\/)?([^/]+)$/))){block(data,true);if(match[1]){if(data.height!==match[2])throw new Error('Wrong block height');}else if(data.block_id!==match[2])throw new Error('Wrong block identity');}
 else if((match=path.match(/^\/blocks\/([^/]+)\/transactions$/))){for(const o of list(data)){transaction(o);if(object(o.location).block_id!==match[1])throw new Error('Wrong transaction block');}}
 else if((match=path.match(/^\/transactions\/by-(id|hash)\/([^/]+)$/))){transaction(data,true);if(data[match[1]==='id'?'txid':'txhash']!==match[2])throw new Error('Wrong transaction identity');}
 else if((match=path.match(/^\/transactions\/by-id\/([^/]+)\/(inputs|outputs|witnesses|wire)$/))){const id=match[1],kind=match[2];if(kind==='wire'){wire(data,url.searchParams);if(data.txid!==id)throw new Error('Wrong wire identity');}else for(const o of list(data)){if(kind==='inputs')input(o);else if(kind==='witnesses')witness(o);else {output(o);if(o.txid!==id)throw new Error('Wrong output transaction');}}}
 else if((match=path.match(/^\/outputs\/([^/]+)\/([^/]+)$/))){output(data);if(data.txid!==match[1]||data.out_idx!==match[2])throw new Error('Wrong outpoint');}
 else if(path==='/assets'){for(const o of list(data))asset(o);}
 else if((match=path.match(/^\/assets\/([^/]+)(?:\/(events|outputs))?$/))){if(!match[2]){asset(data);if(data.token_id!==match[1])throw new Error('Wrong asset identity');}else for(const o of list(data)){if(match[2]==='events')event(o);else{output(o);literal(o.has_token,true);if(url.searchParams.get('view')==='unspent'&&(o.spend!==null||o.is_burn!==false))throw new Error('Nonspendable output in unspent view');}if(o.token_id!==match[1])throw new Error('Wrong asset occurrence');}}
 else if(path==='/branches/outputs'||path==='/branches/utxos'){for(const o of list(data)){output(o.record);for(const p of array(o.matching_positions)){decimal(p,U8);if(BigInt(String(p))>=BigInt(array(object(o.record).branches).length))throw new Error('Invalid matching branch position');}if(path.endsWith('/utxos')){const r=object(o.record);literal(r.spend,null);literal(r.is_burn,false);}}u64(data.posting_reads);u64(data.work);}
 else throw new Error('Unknown explorer route');
}
export function validateStatus(value:unknown):ObjectValue{
 validateTree(value);const o=object(value);literal(o.api_version,'1');bool(o.ready);if(typeof o.reason!=='string'||!['ready','initializing','catching_up','authority_unknown','recovery','busy','schema_incomplete','index_error'].includes(o.reason))throw new Error('Unknown readiness reason');
 const indexed=anchorValue(o.indexed_anchor),authority=anchorValue(o.authoritative_anchor);text(o.service_epoch);if(o.generation!==null)u64(o.generation);binding(o.binding);const c=o.coverage===null?null:coverage(o.coverage);const caps=object(o.capabilities);
 for(const k of ['blocks','transactions','transaction_wire','outputs','assets','asset_events','branches','accepted_pool','detached_history','finality'])bool(caps[k]);for(const k of ['accepted_pool','detached_history','finality'])literal(caps[k],false);
 const limits=object(o.limits);for(const [k,max] of Object.entries({request_bytes:32768n,response_bytes:262144n,page_size:100n,cursor_bytes:2048n,wire_chunk_bytes:32768n,examined_records:1024n,key_reads:4096n})){decimal(limits[k],max);if(limits[k]==='0')throw new Error('Invalid zero service limit');}
 if(o.ready){literal(o.reason,'ready');if(!indexed||!authority||!c||o.generation===null||indexed.block_id!==authority.block_id||indexed.height!==authority.height||c.through_height!==indexed.height||c.complete!==true)throw new Error('Contradictory ready observation');for(const k of ['blocks','transactions','transaction_wire','outputs','assets','asset_events','branches'])literal(caps[k],true);}
 else if(o.reason==='ready'||c?.complete===true)throw new Error('Contradictory unavailable observation');return o;
}
function validateError(value:unknown,status:number){validateTree(value);const o=object(value);literal(o.api_version,'1');const e=object(o.error);text(e.code,64);text(e.meaning,4096);const codes:Record<string,number>={invalid_request:400,invalid_limits:400,invalid_cursor:400,stale_cursor:409,stale_snapshot:409,request_limit:413,record_limit:413,invalid_range:416,index_unavailable:503,not_in_covered_chain:404};if(typeof e.code!=='string'||codes[e.code]!==status)throw new Error('Invalid API error code/status');if(o.snapshot!==null)snapshot(o.snapshot);if(o.coverage!==null)coverage(o.coverage);if([404,409].includes(status)&&(o.snapshot===null||o.coverage===null))throw new Error('Missing fenced error observation');}
async function readJson(response:Response):Promise<unknown>{
 const reader=response.body?.getReader();if(!reader)throw new Error('Missing response body');let size=0;const chunks:Uint8Array[]=[];
 try{while(true){const {done,value}=await reader.read();if(done)break;size+=value.byteLength;if(size>262144)throw new Error('Response exceeds 256 KiB');chunks.push(value);}}catch(e){await reader.cancel().catch(()=>{});throw e;}finally{reader.releaseLock();}
 const bytes=new Uint8Array(size);let offset=0;for(const c of chunks){bytes.set(c,offset);offset+=c.byteLength;}return JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes));
}
