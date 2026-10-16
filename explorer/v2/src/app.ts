import {Client,PinnedView,ApiError,object,searchRoute,hash,decimal,type Json,type ObjectValue,type Envelope,type SearchKind} from './client.js';
const $=<T extends HTMLElement>(s:string)=>document.querySelector<T>(s)!;
const node=(tag:string,text?:string)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=text;return e;};
let client:Client,controller=new AbortController(),view:PinnedView,current='/blocks',body:ObjectValue|undefined;
const results=$('#results'),notice=$('#notice'),anchor=$('#anchor');
function button(label:string,fn:()=>void){const b=node('button',label) as HTMLButtonElement;b.type='button';b.onclick=fn;return b;}
function render(value:Json,key='',parent?:ObjectValue):HTMLElement {
 if(value===null)return node('span','Unknown / not applicable');
 if(Array.isArray(value)){const list=node('ol');if(!value.length)list.append(node('li','No records on this page.'));for(const v of value){const li=node('li');li.append(render(v));list.append(li);}return list;}
 if(typeof value==='object'){const dl=node('dl');for(const [k,v] of Object.entries(value)){const dd=node('dd');dd.append(render(v,k,value));dl.append(node('dt',k.replaceAll('_',' ')),dd);}return dl;}
 let prefix=key==='prev_txid'&&parent?.kind==='mint'?'/assets/':key==='txid'||key==='prev_txid'&&parent?.kind==='spend'?'/transactions/by-id/':key==='txhash'?'/transactions/by-hash/':key==='block_id'||key==='prev_id'?'/blocks/':key==='token_id'&&parent?.has_token!==false?'/assets/':null;
 if(prefix&&typeof value==='string'&&/^[0-9a-f]{64}$/.test(value)){const a=node('a',value) as HTMLAnchorElement;a.href='#'+prefix+value;return a;}
 return node(key.includes('wire')||key.includes('hex')?'code':'span',String(value));
}
function observation(e:Envelope){anchor.replaceChildren(node('strong','Confirmed canonical observation'),render(e.snapshot),node('p','Coverage '+String(e.coverage.from_height)+'–'+String(e.coverage.through_height)+'. Hashes use native wire order. Finality unknown.'));}
function error(e:unknown){
 if(e instanceof ApiError){
  if(e.status===503){controller.abort();notice.textContent='Index unavailable. Retained content is stale. '+e.message;results.classList.add('stale');for(const button of results.querySelectorAll('button'))button.disabled=true;}
  else if(e.status===409){controller.abort();notice.textContent='Snapshot changed. Paging cleared; reload for a fresh observation.';results.replaceChildren();anchor.replaceChildren();}
  else if(e.status===404)notice.textContent='Absent from covered canonical history. Pending membership, rejection and detached history are unknown.';
  else notice.textContent=e.code+': '+e.message;
 }else notice.textContent='Invalid or unavailable response: '+String(e);
 notice.append(button('Reload screen',()=>void navigate(current,body)));
}
async function extra(fn:()=>Promise<unknown>){try{await fn();}catch(e){if(!controller.signal.aborted)error(e);}}
async function section(title:string,route:string,payload?:ObjectValue){
 const pinned=view,signal=controller.signal;const env=await pinned.get(route,payload);signal.throwIfAborted();observation(env);
 const s=node('section');s.append(node('h3',title),render(env.data));results.append(s);
 if(Array.isArray(env.data.items)){
  const cursor=env.data.next_cursor;
  if(typeof env.data.exhausted!=='boolean'||!(cursor===null||typeof cursor==='string')||(!env.data.exhausted&&cursor===null))throw new Error('Invalid page continuation');
  if(cursor!==null){const url=new URL(route,'http://local');if(url.searchParams.get('cursor')===cursor||payload?.cursor===cursor)throw new Error('Nonadvancing cursor');
   s.append(button('Load next page',()=>{s.querySelector('button')?.remove();if(payload)void extra(()=>section(title,route,{...payload,cursor}));else{url.searchParams.set('cursor',cursor);void extra(()=>section(title,url.pathname+url.search));}}));}
 }
 return env;
}
async function wire(id:string,offset:string){const env=await section('Exact wire bytes at '+offset,'/transactions/by-id/'+id+'/wire?offset='+offset+'&length=32768');if(env.data.next_offset!==null){const next=decimal(env.data.next_offset);if(BigInt(next)<=BigInt(offset))throw new Error('Nonadvancing wire offset');results.append(button('Next wire chunk',()=>void extra(()=>wire(id,next))));}}
async function navigate(route:string,payload?:ObjectValue,retry=0):Promise<void>{
 controller.abort();controller=new AbortController();const own=controller;view=new PinnedView(client,own.signal);current=route;body=payload;notice.textContent='Loading canonical observation…';results.classList.remove('stale');
 const previousAnchor=Array.from(anchor.childNodes);const previous=Array.from(results.childNodes);results.replaceChildren();
 try{
  if(route==='/status'){const status=await client.status(own.signal);own.signal.throwIfAborted();results.append(node('h2','Index status'),render(status));anchor.replaceChildren();}
  else if(route.startsWith('/branches')){results.append(node('h2','Public branch / path inspector'),node('p','OR within root sets; AND across positions on the same output. Roots do not prove ownership. Hidden scripts, hidden leaves and unknown proof positions remain unknown.'));await section('Matching outputs',route,payload);}
  else if(/^\/transactions\/by-(id|hash)\//.test(route)){
   results.append(node('h2','Transaction'),node('p','Exact integer units. Accounting and finality unknown. Mint selectors identify assets; coinbase selectors identify parent/height.'));
   const env=await section('Identity and confirmation',route),id=hash(env.data.txid);
   const inputs=await section('Inputs','/transactions/by-id/'+id+'/inputs');
   for(const item of inputs.data.items as Json[]??[]){const i=object(item);if(typeof i.input_index==='string')results.append(button('Witnesses: input '+i.input_index,()=>void extra(()=>section('Public witnesses for input '+i.input_index,'/transactions/by-id/'+id+'/witnesses?input_index='+i.input_index))));}
   const form=node('form');const input=node('input') as HTMLInputElement;input.inputMode='numeric';input.value='0';input.setAttribute('aria-label','Witness input index');form.append(input,node('button','Inspect witnesses for input'));form.onsubmit=e=>{e.preventDefault();try{const index=decimal(input.value,4294967295n);void extra(()=>section('Public witnesses for input '+index,'/transactions/by-id/'+id+'/witnesses?input_index='+index));}catch(e){error(e);}};results.append(form);
   await section('Outputs: ordered branches and paths','/transactions/by-id/'+id+'/outputs');results.append(button('Inspect exact transaction wire',()=>void extra(()=>wire(id,'0'))));
  }else if(/^\/blocks\/(by-height\/)?[^/?]+$/.test(route)){results.append(node('h2','Block'));const env=await section('Header and confirmation',route);await section('Transactions','/blocks/'+hash(env.data.block_id)+'/transactions');}
  else if(/^\/assets\/[^/?]+$/.test(route)){results.append(node('h2','Native asset'),node('p','Integer units; decimals, issuer, mint cap and supply unknown. First observed occurrence is not a unique genesis or issuer proof.'));const env=await section('Registry detail',route),id=hash(env.data.token_id);await section('Events','/assets/'+id+'/events');await section('Output history including burns','/assets/'+id+'/outputs?view=history');await section('Unspent outputs','/assets/'+id+'/outputs?view=unspent');}
  else{results.append(node('h2',route.startsWith('/assets')?'Native assets':route.startsWith('/outputs')?'Historical output':'Canonical blocks'));await section('Records',route);}
  own.signal.throwIfAborted();notice.textContent='Observation loaded. Pending membership unsupported; detached history unavailable; finality unknown.';
 }catch(e){if(own.signal.aborted)return;if(e instanceof ApiError&&e.status===409&&retry<1){results.replaceChildren();anchor.replaceChildren();await navigate(route,payload,retry+1);return;}if(e instanceof ApiError&&e.status===503&&previous.length){results.replaceChildren(...previous);anchor.replaceChildren(...previousAnchor);}error(e);}
}
$('#connect').addEventListener('submit',e=>{e.preventDefault();try{client=new Client($<HTMLInputElement>('#base').value);sessionStorage.setItem('lotus-explorer-base',client.base);void navigate('/blocks');}catch(e){error(e);}});
$('#search').addEventListener('submit',e=>{e.preventDefault();try{const kind=$<HTMLSelectElement>('#kind').value as SearchKind,value=$<HTMLInputElement>('#query').value;const route=searchRoute(kind,value);if(kind==='branch')void navigate('/branches/outputs',{any_branch:[hash(value.trim())],page_size:'25',include_burn:true});else location.hash=route;}catch(e){error(e);}});
$('#branches').addEventListener('submit',e=>{e.preventDefault();try{
 const any_branch=$<HTMLTextAreaElement>('#roots').value.split(/\s+/).filter(Boolean).map(hash);const positions=JSON.parse($<HTMLTextAreaElement>('#positions').value);
 if(!Array.isArray(positions))throw new Error('Positions must be an array');for(const p of positions){decimal(p.position,255n);if(!Array.isArray(p.roots))throw new Error('Position requires roots');p.roots.forEach(hash);}
 const unspent=$<HTMLInputElement>('#unspent').checked;const payload:ObjectValue={any_branch,positions,page_size:'25'};if(!unspent)payload.include_burn=$<HTMLInputElement>('#burn').checked;void navigate(unspent?'/branches/utxos':'/branches/outputs',payload);
 }catch(e){error(e);}});
window.addEventListener('hashchange',()=>{const route=location.hash.slice(1);if(route==='branch-form')return;if(!/^\/(blocks|transactions|assets|outputs|status)(\/|\?|$)/.test(route)){notice.textContent='Unknown route';return;}void navigate(route);});
const configured=new URL(location.href).searchParams.get('api')??sessionStorage.getItem('lotus-explorer-base')??'http://127.0.0.1:18331';$<HTMLInputElement>('#base').value=configured;
try{client=new Client(configured);void navigate(location.hash.slice(1)||'/status');}catch(e){error(e);}
