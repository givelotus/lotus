// A dedicated worker owns a bounded GPU dispatch. Terminating it stops further
// dispatches; one already submitted GPU batch may finish. No RPC/auth here.
import { validateMiningDescriptor } from '../lib/chainconfig.js';
import { sha256d, v2BlockHash, setHeaderNonce, meetsTarget } from '../lib/mining-hashes.js';

const COUNT = 1024;
const STRIDE = 32;
let device;
let buffers = [];
let running = false;
self.onmessage = async ({ data }) => {
  if (data.type !== 'start' || running) return;
  running = true;
  const start = performance.now();
  let hashes = 0;
  try {
    if (!self.navigator.gpu) throw new Error('WebGPU is unavailable in this browser worker.');
    const adapter = await navigator.gpu.requestAdapter();
    if (!adapter) throw new Error('No WebGPU adapter is available.');
    device = await adapter.requestDevice();
    let lost = false;
    device.lost.then((info) => { if (info.reason === 'destroyed') return; lost = true; self.postMessage({ type: 'error', message: `GPU device lost: ${info.message || info.reason}` }); });
    const { header, target, chainid } = data.work;
    const descriptor = validateMiningDescriptor(data.work.descriptor);
    if (!(header instanceof Uint8Array) || header.length !== descriptor.headerbytes || !(target instanceof Uint8Array) || target.length !== 32 || (descriptor.chainid && (!(chainid instanceof Uint8Array) || chainid.length !== 32))) throw new Error('Invalid mining work buffers.');
    const file = descriptor.algorithm === 'sha256d' ? 'sha256d.wgsl' : descriptor.algorithm === 'lotus-v2-blockid' ? 'blake3.wgsl' : null;
    if (!file) throw new Error('Unsupported mining algorithm.');
    const response = await fetch(new URL(file, import.meta.url));
    if (!response.ok) throw new Error('Could not load the local mining shader.');
    const module = device.createShaderModule({ code: await response.text() });
    const diagnostics = await module.getCompilationInfo();
    if (diagnostics.messages.some((m) => m.type === 'error')) throw new Error(diagnostics.messages.filter((m) => m.type === 'error').map((m) => m.message).join('; '));
    const pipeline = await device.createComputePipelineAsync({ layout: 'auto', compute: { module, entryPoint: 'main' } });
    const make = (size, usage) => { const b = device.createBuffer({ size, usage }); buffers.push(b); return b; };
    const head = make(Math.ceil(header.length / 4) * 4, GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_DST);
    const params = make(16, GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_DST);
    const result = make(COUNT * STRIDE, GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_SRC);
    const readback = make(COUNT * STRIDE, GPUBufferUsage.MAP_READ | GPUBufferUsage.COPY_DST);
    const padded = new Uint8Array(Math.ceil(header.length / 4) * 4); padded.set(header);
    device.queue.writeBuffer(head, 0, padded);
    const entries = [head, params, result].map((buffer, binding) => ({ binding, resource: { buffer } }));
    if (chainid) {
      const chain = make(32, GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_DST);
      device.queue.writeBuffer(chain, 0, chainid); entries.push({ binding: 3, resource: { buffer: chain } });
    }
    const group = device.createBindGroup({ layout: pipeline.getBindGroupLayout(0), entries });
    const fullLimit = 1n << BigInt(descriptor.noncebytes * 8);
    const first = data.work.nonceStart === undefined ? 0n : BigInt(data.work.nonceStart);
    const limit = data.work.nonceEnd === undefined ? fullLimit : BigInt(data.work.nonceEnd);
    if (first < 0n || first >= limit || limit > fullLimit) throw new Error('Invalid mining nonce range.');
    for (let nonce = first; nonce < limit && !lost; nonce += BigInt(COUNT)) {
      const count = Number(limit - nonce < BigInt(COUNT) ? limit - nonce : BigInt(COUNT));
      device.queue.writeBuffer(params, 0, new Uint32Array([Number(nonce & 0xffffffffn), count, Number(nonce >> 32n), 0]));
      const encoder = device.createCommandEncoder();
      const pass = encoder.beginComputePass(); pass.setPipeline(pipeline); pass.setBindGroup(0, group); pass.dispatchWorkgroups(Math.ceil(count / 64)); pass.end();
      encoder.copyBufferToBuffer(result, 0, readback, 0, count * STRIDE);
      device.queue.submit([encoder.finish()]);
      await readback.mapAsync(GPUMapMode.READ, 0, count * STRIDE);
      const digests = new Uint8Array(readback.getMappedRange(0, count * STRIDE)).slice(); readback.unmap();
      const firstHeader = setHeaderNonce(header, nonce);
      const firstCpu = descriptor.algorithm === 'sha256d' ? sha256d(firstHeader) : v2BlockHash(firstHeader, chainid);
      if (firstCpu.some((byte, j) => byte !== digests[j])) throw new Error('GPU result disagrees with CPU hash verification.');
      hashes += count;
      for (let i = 0; i < count; ++i) {
        const digest = digests.subarray(i * STRIDE, (i + 1) * STRIDE);
        if (!meetsTarget(digest, target)) continue;
        const solvedNonce = nonce + BigInt(i);
        const candidate = setHeaderNonce(header, solvedNonce);
        const cpu = descriptor.algorithm === 'sha256d' ? sha256d(candidate) : v2BlockHash(candidate, chainid);
        if (cpu.some((byte, j) => byte !== digest[j])) throw new Error('GPU result disagrees with CPU hash verification.');
        self.postMessage({ type: 'candidate', nonce: solvedNonce.toString(), hashes, elapsedMs: performance.now() - start });
        return;
      }
      self.postMessage({ type: 'progress', hashes, elapsedMs: performance.now() - start });
    }
    if (!lost) self.postMessage({ type: 'exhausted', hashes, elapsedMs: performance.now() - start });
  } catch (error) { self.postMessage({ type: 'error', message: error.message }); }
  finally { for (const buffer of buffers) buffer.destroy(); device?.destroy(); buffers = []; }
};
