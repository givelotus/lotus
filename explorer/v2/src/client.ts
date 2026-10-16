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
   const reader=response.body?.getReader(); let bytes=0; const chunks:Uint8Array[]=[];
   if(!reader) throw new Error('Missing response body');
   while(true) { const {done,value}=await reader.read(); if(done) break; bytes+=value.byteLength; if(bytes>262144) {await reader.cancel(); throw new Error('Response exceeds 256 KiB');} chunks.push(value); }
   const all=new Uint8Array(bytes);let offset=0;for(const chunk of chunks){all.set(chunk,offset);offset+=chunk.length;}
   const parsed=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(all));
   if(!response.ok) { const error=object(object(parsed).error); if(typeof error.code!=='string'||typeof error.meaning!=='string') throw new Error('Malformed API error'); throw new ApiError(response.status,error.code,error.meaning); }
   const envelope=validateEnvelope(parsed); validateRoute(route,envelope.data); return envelope;
 }
 async status(signal:AbortSignal):Promise<ObjectValue> {
   const response=await this.fetcher(this.base+'/v2/explorer/v1/status',{signal,cache:'no-store'});
   const body=await response.text();if(body.length>262144) throw new Error('Status exceeds limit');
   if(!response.ok) throw new ApiError(response.status,'index_unavailable','Status unavailable');
   const parsed=JSON.parse(body); validateTree(parsed); const o=object(parsed);
   if(o.api_version!=='1'||typeof o.ready!=='boolean'||typeof o.reason!=='string') throw new Error('Invalid status'); object(o.capabilities); return o;
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

function required(o:ObjectValue,fields:string[]){for(const f of fields)if(!(f in o))throw new Error('Missing response field: '+f);}
function confirmed(o:ObjectValue){if(o.status!=='confirmed')throw new Error('Unsupported confirmation status');}
function block(o:ObjectValue){required(o,['block_id','prev_id','height','time','size','tx_count','status','confirmations']);confirmed(o);}
function tx(o:ObjectValue){required(o,['txid','txhash','location','status','confirmations','input_count','output_count','wire_size']);confirmed(o);location(object(o.location));}
function location(o:ObjectValue){required(o,['block_id','height','tx_index']);}
function output(o:ObjectValue){required(o,['txid','out_idx','flags','value','has_token','token_id','is_burn','branches','paths','creation','spend']);if(typeof o.has_token!=='boolean'||typeof o.is_burn!=='boolean'||!Array.isArray(o.branches)||!Array.isArray(o.paths))throw new Error('Invalid output');location(object(o.creation));if(o.spend!==null)object(o.spend);}
function asset(o:ObjectValue){required(o,['token_id','first_seen','event_count','output_count','metadata','supply']);location(object(o.first_seen));if(object(o.metadata).availability!=='unknown'||object(o.supply).availability!=='unknown')throw new Error('Unsupported metadata/supply claim');}
function ref(o:Json|undefined){required(object(o),['offset','length']);}
export function validateRoute(route:string,data:ObjectValue){
 const path=route.split('?')[0]!;
 const list=path==='/blocks'||path==='/assets'||/\/(transactions|inputs|outputs|witnesses|events|utxos)$/.test(path);
 let entries:ObjectValue[]=[data];
 if(list){required(data,['items','next_cursor','exhausted']);if(!Array.isArray(data.items)||data.items.length>100||typeof data.exhausted!=='boolean'||!(data.next_cursor===null||typeof data.next_cursor==='string')||(!data.exhausted&&data.next_cursor===null))throw new Error('Invalid bounded list');entries=data.items.map(object);}
 for(const o of entries){
  if(path==='/blocks'||/^\/blocks\/(by-height\/)?[^/]+$/.test(path)){block(o);if(path!=='/blocks'){required(o,['header_wire','header','body_availability','finality']);if(o.body_availability!=='complete'||o.finality!=='unknown')throw new Error('Unsupported block availability');}}
  else if(/\/blocks\/[^/]+\/transactions$/.test(path)||/^\/transactions\/by-(id|hash)\/[^/]+$/.test(path)){tx(o);if(path.startsWith('/transactions')){required(o,['lock','core_available','witness_available','wire_available','finality','accounting']);if(o.core_available!==true||o.witness_available!==true||o.wire_available!==true||o.finality!=='unknown'||object(o.accounting).availability!=='unknown')throw new Error('Invalid transaction availability');}}
  else if(path.endsWith('/inputs')){required(o,['input_index','flags','kind','prev_txid','prev_index','sequence','path_index','witness_count','coinbase_data','resolved_coin']);if(!['spend','coinbase','mint'].includes(String(o.kind)))throw new Error('Invalid input kind');const coin=object(o.resolved_coin);if(coin.availability!==(o.kind==='spend'?'complete':'not_applicable'))throw new Error('Invalid resolved input');const data=object(o.coinbase_data);if(typeof data.present!=='boolean')throw new Error('Invalid coinbase presence');if(data.present)ref(data.wire_ref);else if(data.wire_ref!==null)throw new Error('Absent coinbase data reference');}
  else if(path.endsWith('/witnesses')){required(o,['witness_index','script','siblings','arguments']);ref(o.script);for(const k of ['siblings','arguments']){const t=object(o[k]);required(t,['count','table_ref','inline']);ref(t.table_ref);if(t.inline!==null&&!Array.isArray(t.inline))throw new Error('Invalid witness table');}}
  else if(path.endsWith('/wire')){required(o,['txid','txhash','total_bytes','offset','bytes_hex','next_offset']);}
  else if(path.startsWith('/branches/')){required(o,['record','matching_positions']);output(object(o.record));if(!Array.isArray(o.matching_positions))throw new Error('Invalid matching positions');}
  else if(path.startsWith('/outputs/')||path.endsWith('/outputs'))output(o);
  else if(path==='/assets'||/^\/assets\/[^/]+$/.test(path))asset(o);
  else if(path.endsWith('/events')){required(o,['token_id','location','spent_units','output_units','explicit_burn_units','minted_units','implicit_burn_units','has_mint_input']);location(object(o.location));if(typeof o.has_mint_input!=='boolean')throw new Error('Invalid mint indicator');}
 }
}
