import http from 'node:http';
import {readFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
const args=process.argv.slice(2),portIndex=args.indexOf('--port'),apiIndex=args.indexOf('--api');
if(portIndex<0||!/^\d+$/.test(args[portIndex+1]??'')||Number(args[portIndex+1])>65535)throw new Error('Supply explicit --port 0 (ephemeral) or a local port.');
const api=apiIndex<0?undefined:new URL(args[apiIndex+1]);
if(api&&(!['127.0.0.1','localhost','[::1]'].includes(api.hostname)||api.protocol!=='http:'||api.username||api.password||api.search||api.hash||api.pathname!=='/'))throw new Error('Private proxy requires a loopback HTTP origin without credentials.');
const root=new URL('./',import.meta.url);
const files=new Map([['/',['index.html','text/html']],['/index.html',['index.html','text/html']],['/style.css',['style.css','text/css']],['/dist/app.js',['dist/app.js','text/javascript']],['/dist/client.js',['dist/client.js','text/javascript']]]);
const server=http.createServer(async(req,res)=>{
 res.setHeader('Cache-Control','no-store');res.setHeader('X-Content-Type-Options','nosniff');res.setHeader('Content-Security-Policy',"default-src 'self'; connect-src 'self' http://127.0.0.1:* http://localhost:* http://[::1]:*; style-src 'self'; script-src 'self'; base-uri 'none'; frame-ancestors 'none'");
 try{
 const incoming=new URL(req.url,'http://127.0.0.1');
 if(incoming.pathname.startsWith('/v2/explorer/v1/')&&api){
  if(!['GET','POST'].includes(req.method)){res.writeHead(405).end();return;}
  let bytes=0;const chunks=[];for await(const chunk of req){bytes+=chunk.length;if(bytes>32768){res.writeHead(413).end();return;}chunks.push(chunk);}
  if(req.url.length>32768){res.writeHead(413).end();return;}
  const abort=new AbortController();req.on('aborted',()=>abort.abort());res.on('close',()=>abort.abort());
  const remote=await fetch(new URL(incoming.pathname+incoming.search,api),{method:req.method,headers:{'Content-Type':'application/json'},body:req.method==='POST'?Buffer.concat(chunks):undefined,signal:AbortSignal.any([abort.signal,AbortSignal.timeout(15000)]),redirect:'error'});
  const reader=remote.body.getReader();let total=0;const parts=[];while(true){const {done,value}=await reader.read();if(done)break;total+=value.length;if(total>262144){await reader.cancel();throw new Error('Upstream response limit');}parts.push(value);}
  res.writeHead(remote.status,{'Content-Type':'application/json'}).end(Buffer.concat(parts));return;
 }
 if(req.method!=='GET'){res.writeHead(405).end();return;}
 const entry=files.get(incoming.pathname);if(!entry){res.writeHead(404).end();return;}
 const bytes=await readFile(fileURLToPath(new URL(entry[0],root)));res.writeHead(200,{'Content-Type':entry[1]}).end(bytes);
 }catch(e){if(!res.headersSent)res.writeHead(503,{'Content-Type':'application/json'});res.end(JSON.stringify({api_version:'1',error:{code:'index_unavailable',meaning:'Private proxy unavailable'},snapshot:null,coverage:null}));}
});
server.listen(Number(args[portIndex+1]),'127.0.0.1',()=>{const address=server.address();console.log(`Private explorer: http://127.0.0.1:${address.port}/${api?'?api='+encodeURIComponent('http://127.0.0.1:'+address.port):''}`);});
