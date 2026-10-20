import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { sha256, sha256d, blake3SingleChunk, v2HeaderHashes, v2BlockHash, setHeaderNonce, meetsTarget, hexToBytes, bytesToHex } from '../../src/lib/mining-hashes.js';
const header = hexToBytes('202122232425262728292a2b2c2d2e2f303132333435363738393a3b3c3d3e3fffff001d0605040302010f0e0d0c0b0a090802000000887766554433221100ffeeddccbbaa99404142434445464748494a4b4c4d4e4f505152535455565758595a5b5c5d5e5f606162636465666768696a6b6c6d6e6f707172737475767778797a7b7c7d7e7f');
const chain = Uint8Array.from({length:32},(_,i)=>i);
// Source: lotus_v2/test_header.cpp; independently generated with Python blake3
// 1.0.11, rather than the C++ vendored BLAKE3 or this JS implementation.
test('V2 body/work/block ID match independent Python consensus vectors', () => {
  const hashes = v2HeaderHashes(header,chain);
  assert.equal(bytesToHex(hashes.bodyHash),'1704e11edcbc47eb829d210ac1affb606dd4021c82305e07a028962456efec3d');
  assert.equal(bytesToHex(hashes.workHash),'56c49269bcb4709b42d48312a382badc0906162e5bd6e49aac48a7096288ffd1');
  assert.equal(bytesToHex(hashes.blockHash),'fbe9243579627fc3a41043c80395d33a8a01b91a9b86b6c6e629530595c83370');
  assert.equal(bytesToHex(v2BlockHash(setHeaderNonce(header,0x08090a0b0c0d0e10n),chain)),'8a967f4522d06f683830cf003b9f456001e045f617bf4d4336754a91c75f5824');
  assert.equal(bytesToHex(v2BlockHash(setHeaderNonce(header,0xffffffffffffffffn),chain)),'ce606e015b769cf60502917d0bac3597048e25668c7df323f817b53969aab371');
  const altered = chain.slice(); altered[0]++;
  assert.notDeepEqual(v2HeaderHashes(header,altered).bodyHash,hashes.bodyHash);
});
test('SHA256 CPU reference agrees with independent Node/OpenSSL', () => {
  for(const size of [0,1,32,55,56,63,64,65,80,134,1024]) {
    const input = Uint8Array.from({length:size},(_,i)=>(i*73+19)&255);
    assert.equal(bytesToHex(sha256(input)),createHash('sha256').update(input).digest('hex'));
    if(size===80) assert.equal(bytesToHex(sha256d(input)),createHash('sha256').update(createHash('sha256').update(input).digest()).digest('hex'));
  }
});
test('Bitcoin genesis SHA256D header and nonce encoding', () => {
  const genesis = hexToBytes('01000000'+'00'.repeat(32)+'3ba3edfd7a7b12b27ac72c3e67768f617fc81bc3888a51323a9fb8aa4b1e5e4a'+'29ab5f49ffff001d1dac2b7c');
  assert.equal(bytesToHex(sha256d(genesis).slice().reverse()),'000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f');
  assert.equal(bytesToHex(setHeaderNonce(genesis,0x12345678n).subarray(76)),'78563412');
  assert.throws(()=>setHeaderNonce(genesis,0x100000000n),RangeError);
  assert.throws(()=>setHeaderNonce(header,-1n),RangeError);
  assert.throws(()=>setHeaderNonce(header,1n<<64n),RangeError);
});
test('BLAKE3 official empty/abc vectors and explicit single-chunk bound', () => {
  assert.equal(bytesToHex(blake3SingleChunk(new Uint8Array())),'af1349b9f5f9a1a6a0404dea36dcc9499bcb25c9adc112b7cc9a93cae41f3262');
  assert.equal(bytesToHex(blake3SingleChunk(new TextEncoder().encode('abc'))),'6437b3ac38465133ffb63b75273a8db548c558465d79db03fd359c6cd5bd9d85');
  assert.throws(()=>blake3SingleChunk(new Uint8Array(1025)),RangeError);
});
test('target comparisons are unsigned little-endian including equality', () => {
  const a=new Uint8Array(32), b=new Uint8Array(32); a[0]=255; b[31]=1;
  assert.ok(meetsTarget(a,b)); assert.ok(!meetsTarget(b,a)); assert.ok(meetsTarget(b,b));
  assert.throws(()=>meetsTarget(a,new Uint8Array(31)),TypeError);
  assert.throws(()=>hexToBytes('0xz1'),TypeError);
  assert.throws(()=>sha256d(header),TypeError);
});

// Opt-in hardware check: MINING_GPU=1 node --test test/unit/mining-hashes.test.js
// Controlled loopback server and isolated Chrome profile; never contacts a node.
test('actual Chrome WebGPU SHA256D/V2 BLAKE3 differential vectors', {skip:process.env.MINING_GPU !== '1'}, async () => {
  const { chromium } = await import('@playwright/test');
  const { createServer } = await import('node:http');
  const { readFile } = await import('node:fs/promises');
  const server = createServer(async(req,res)=>{
    if(req.url==='/') { res.setHeader('Content-Type','text/html'); res.end('<title>Mining kernel test</title>'); return; }
    if(!['/sha256d.wgsl','/blake3.wgsl','/mining-hashes.js'].includes(req.url)) {res.writeHead(404);res.end();return;}
    const file=req.url.endsWith('.wgsl')?new URL('../../src/mining'+req.url,import.meta.url):new URL('../../src/lib/mining-hashes.js',import.meta.url);
    res.setHeader('Content-Type',req.url.endsWith('.js')?'text/javascript':'text/plain');
    try { res.end(await readFile(file)); } catch {res.writeHead(500);res.end();}
  });
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  let browser;
  try {
    browser=await chromium.launch({channel:'chrome',headless:true,args:['--enable-unsafe-webgpu']});
    const page=await browser.newPage(); await page.goto(`http://127.0.0.1:${server.address().port}/`);
    const result=await page.evaluate(async({headerHex})=>{
      const cpu=await import('/mining-hashes.js');
      const adapter=await navigator.gpu?.requestAdapter(); if(!adapter) throw Error('No WebGPU adapter; hardware validation not performed');
      const device=await adapter.requestDevice(); const results=[];
      for(const kind of ['sha256d','blake3']) {
        const module=device.createShaderModule({code:await(await fetch('/'+kind+'.wgsl')).text()});
        const errors=(await module.getCompilationInfo()).messages.filter(m=>m.type==='error');
        if(errors.length) throw Error(JSON.stringify(errors.map(m=>m.message)));
        device.pushErrorScope('validation');
        const pipeline=await device.createComputePipelineAsync({layout:'auto',compute:{module,entryPoint:'main'}});
        // Non-multiple workgroup count plus low-word carry for the 64-bit V2 nonce.
        for(const start of [0x08090a0b0c0d0e0fn,0x08090a0bfffffff0n,0xffffffffffffffbfn]) {
          const count=65, h=kind==='blake3'?cpu.hexToBytes(headerHex):Uint8Array.from({length:80},(_,i)=>(i*73+19)&255);
          const nonce=kind==='blake3'?start:start&0xffffffffn;
          const padded=new Uint8Array(Math.ceil(h.length/4)*4);padded.set(h);
          const params=new Uint32Array([Number(nonce&0xffffffffn),count,Number(nonce>>32n),0]);
          const chain=Uint8Array.from({length:32},(_,i)=>i);
          const buffers=[];
          const storage=(data,usage=GPUBufferUsage.STORAGE|GPUBufferUsage.COPY_DST)=>{
            const b=device.createBuffer({size:data.byteLength,usage});device.queue.writeBuffer(b,0,data);buffers.push(b);return b;
          };
          const input=storage(padded),parameters=storage(params);
          const out=device.createBuffer({size:count*32,usage:GPUBufferUsage.STORAGE|GPUBufferUsage.COPY_SRC});buffers.push(out);
          const entries=[input,parameters,out]; if(kind==='blake3')entries.push(storage(chain));
          const group=device.createBindGroup({layout:pipeline.getBindGroupLayout(0),entries:entries.map((buffer,binding)=>({binding,resource:{buffer}}))});
          const read=device.createBuffer({size:count*32,usage:GPUBufferUsage.COPY_DST|GPUBufferUsage.MAP_READ});buffers.push(read);
          const encoder=device.createCommandEncoder();const pass=encoder.beginComputePass();pass.setPipeline(pipeline);pass.setBindGroup(0,group);pass.dispatchWorkgroups(Math.ceil(count/64));pass.end();encoder.copyBufferToBuffer(out,0,read,0,count*32);device.queue.submit([encoder.finish()]);await read.mapAsync(GPUMapMode.READ);
          const actual=new Uint8Array(read.getMappedRange());
          for(let i=0;i<count;i++){
            const n=kind==='blake3'?nonce+BigInt(i):(nonce+BigInt(i))&0xffffffffn;
            const candidate=cpu.setHeaderNonce(h,n);const expected=kind==='blake3'?cpu.v2BlockHash(candidate,chain):cpu.sha256d(candidate);
            if(cpu.bytesToHex(actual.subarray(i*32,(i+1)*32))!==cpu.bytesToHex(expected))throw Error(`${kind} nonce ${n}: GPU digest mismatch`);
          }
          read.unmap();buffers.forEach(b=>b.destroy());results.push({kind,count,start:nonce.toString()});
        }
        const validation=await device.popErrorScope();if(validation)throw Error(validation.message);
      }
      device.destroy();return results;
    },{headerHex:bytesToHex(header)});
    assert.equal(result.length,6);
  } finally { await browser?.close(); await new Promise(resolve=>server.close(resolve)); }
});
