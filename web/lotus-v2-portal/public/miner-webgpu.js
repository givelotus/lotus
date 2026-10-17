/**
 * Lotus V2 WebGPU (WGSL) Compute Shader Miner + Web Worker Fallback Controller
 *
 * Ports `miner/kernels/lotus_v2.cl` (`b3_g`, `b3_compress`, 2-stage tagged BLAKE3
 * `WorkHash` -> `BlockID`, and `find_nonce_matches`) to a zero-dependency WGSL
 * compute shader (`@compute @workgroup_size(256)`).
 *
 * Features:
 * - Bit-for-bit parity with `miner/kernels/lotus_v2.cl` and P04 test vectors
 * - `atomicAdd(&hits.count, 1u)` in storage buffer: GPU->CPU readback is only
 *   4 bytes per dispatch when no share is found!
 * - Automatic per-frame dispatch batch size tuning (~3ms target per dispatch)
 *   for 60 FPS UI smoothness at peak GPU throughput.
 * - Automatic fallback to Web Worker (`miner-worker.js`) when WebGPU is unavailable.
 */

(function (root, factory) {
  if (typeof module === 'object' && module.exports) {
    module.exports = factory(require('./miner-worker.js'));
  } else {
    root.LotusV2WebGPUMiner = factory(root.LotusV2MinerCore);
  }
})(typeof self !== 'undefined' ? self : globalThis, function (Core) {
  'use strict';

  const WORKGROUP_SIZE = 256;
  const MAX_HITS_PER_DISPATCH = 32;
  const TARGET_DISPATCH_MS = 3.0;

  /**
   * WGSL Compute Shader implementing exact 2-stage Lotus V2 Tagged BLAKE3
   * (`WorkHash` -> `BlockID`) with `atomicAdd(&hits.count, 1u)`.
   */
  const LOTUS_V2_WGSL = /* wgsl */ `
struct MinerParams {
  work_words: array<u32, 18>,
  id_prefix_words: array<u32, 13>,
  target_words: array<u32, 8>,
  start_nonce_lo: u32,
  start_nonce_hi: u32,
  batch_count: u32,
  max_hits: u32,
  _pad: u32,
};

struct HitRecord {
  nonce_lo: u32,
  nonce_hi: u32,
  block_id: array<u32, 8>,
  work_hash: array<u32, 8>,
};

struct HitBuffer {
  count: atomic<u32>,
  _pad0: u32,
  _pad1: u32,
  _pad2: u32,
  records: array<HitRecord, 32>,
};

@group(0) @binding(0) var<uniform> params: MinerParams;
@group(0) @binding(1) var<storage, read_write> hits: HitBuffer;

const B3_IV0: u32 = 0x6a09e667u;
const B3_IV1: u32 = 0xbb67ae85u;
const B3_IV2: u32 = 0x3c6ef372u;
const B3_IV3: u32 = 0xa54ff53au;
const B3_IV4: u32 = 0x510e527fu;
const B3_IV5: u32 = 0x9b05688cu;
const B3_IV6: u32 = 0x1f83d9abu;
const B3_IV7: u32 = 0x5be0cd19u;

fn rotl32(x: u32, n: u32) -> u32 {
  return (x << n) | (x >> (32u - n));
}

fn b3_g(
  v: ptr<function, array<u32, 16>>,
  a: u32,
  b: u32,
  c: u32,
  d: u32,
  x: u32,
  y: u32
) {
  (*v)[a] = (*v)[a] + (*v)[b] + x;
  (*v)[d] = rotl32((*v)[d] ^ (*v)[a], 16u);
  (*v)[c] = (*v)[c] + (*v)[d];
  (*v)[b] = rotl32((*v)[b] ^ (*v)[c], 20u);
  (*v)[a] = (*v)[a] + (*v)[b] + y;
  (*v)[d] = rotl32((*v)[d] ^ (*v)[a], 24u);
  (*v)[c] = (*v)[c] + (*v)[d];
  (*v)[b] = rotl32((*v)[b] ^ (*v)[c], 25u);
}

fn b3_round(
  v: ptr<function, array<u32, 16>>,
  m: ptr<function, array<u32, 16>>,
  s0: u32, s1: u32, s2: u32, s3: u32,
  s4: u32, s5: u32, s6: u32, s7: u32,
  s8: u32, s9: u32, s10: u32, s11: u32,
  s12: u32, s13: u32, s14: u32, s15: u32
) {
  b3_g(v, 0u, 4u, 8u, 12u, (*m)[s0], (*m)[s1]);
  b3_g(v, 1u, 5u, 9u, 13u, (*m)[s2], (*m)[s3]);
  b3_g(v, 2u, 6u, 10u, 14u, (*m)[s4], (*m)[s5]);
  b3_g(v, 3u, 7u, 11u, 15u, (*m)[s6], (*m)[s7]);
  b3_g(v, 0u, 5u, 10u, 15u, (*m)[s8], (*m)[s9]);
  b3_g(v, 1u, 6u, 11u, 12u, (*m)[s10], (*m)[s11]);
  b3_g(v, 2u, 7u, 8u, 13u, (*m)[s12], (*m)[s13]);
  b3_g(v, 3u, 4u, 9u, 14u, (*m)[s14], (*m)[s15]);
}

fn b3_compress(
  cv: ptr<function, array<u32, 8>>,
  m: ptr<function, array<u32, 16>>,
  block_len: u32,
  flags: u32,
  out: ptr<function, array<u32, 8>>
) {
  var v: array<u32, 16>;
  for (var i: u32 = 0u; i < 8u; i = i + 1u) {
    v[i] = (*cv)[i];
  }
  v[8] = B3_IV0;
  v[9] = B3_IV1;
  v[10] = B3_IV2;
  v[11] = B3_IV3;
  v[12] = 0u;
  v[13] = 0u;
  v[14] = block_len;
  v[15] = flags;

  // 7 BLAKE3 rounds using B3_SCHEDULE[0..6]
  b3_round(&v, m, 0u, 1u, 2u, 3u, 4u, 5u, 6u, 7u, 8u, 9u, 10u, 11u, 12u, 13u, 14u, 15u);
  b3_round(&v, m, 2u, 6u, 3u, 10u, 7u, 0u, 4u, 13u, 1u, 11u, 12u, 5u, 9u, 14u, 15u, 8u);
  b3_round(&v, m, 3u, 4u, 10u, 12u, 13u, 2u, 7u, 14u, 6u, 5u, 9u, 0u, 11u, 15u, 8u, 1u);
  b3_round(&v, m, 10u, 7u, 12u, 9u, 14u, 3u, 13u, 15u, 4u, 0u, 11u, 2u, 5u, 8u, 1u, 6u);
  b3_round(&v, m, 12u, 13u, 9u, 11u, 15u, 10u, 14u, 8u, 7u, 2u, 5u, 3u, 0u, 1u, 6u, 4u);
  b3_round(&v, m, 9u, 14u, 11u, 5u, 8u, 12u, 15u, 1u, 13u, 3u, 0u, 10u, 2u, 6u, 4u, 7u);
  b3_round(&v, m, 11u, 15u, 5u, 0u, 1u, 9u, 8u, 6u, 14u, 10u, 2u, 12u, 3u, 4u, 7u, 13u);

  for (var i: u32 = 0u; i < 8u; i = i + 1u) {
    (*out)[i] = v[i] ^ v[i + 8u];
  }
}

@compute @workgroup_size(256)
fn find_nonce_matches(@builtin(global_invocation_id) gid: vec3<u32>) {
  let lane: u32 = gid.x;
  if (lane >= params.batch_count) {
    return;
  }

  let n_lo: u32 = params.start_nonce_lo + lane;
  let carry: u32 = select(0u, 1u, n_lo < params.start_nonce_lo);
  let n_hi: u32 = params.start_nonce_hi + carry;

  var iv: array<u32, 8> = array<u32, 8>(
    B3_IV0, B3_IV1, B3_IV2, B3_IV3, B3_IV4, B3_IV5, B3_IV6, B3_IV7
  );

  // Stage 1: WorkHash = BLAKE3(work[0..71])
  var m0: array<u32, 16>;
  for (var i: u32 = 0u; i < 16u; i = i + 1u) {
    m0[i] = params.work_words[i];
  }
  m0[7] = (params.work_words[7] & 0x00ffffffu) | ((n_lo & 0xffu) << 24u);
  m0[8] = (n_lo >> 8u) | ((n_hi & 0xffu) << 24u);
  m0[9] = (params.work_words[9] & 0xff000000u) | (n_hi >> 8u);

  var cv: array<u32, 8>;
  b3_compress(&iv, &m0, 64u, 1u, &cv);

  var m1: array<u32, 16>;
  m1[0] = params.work_words[16];
  m1[1] = params.work_words[17] & 0x00ffffffu;
  for (var i: u32 = 2u; i < 16u; i = i + 1u) {
    m1[i] = 0u;
  }
  var work_cv: array<u32, 8>;
  b3_compress(&cv, &m1, 7u, 10u, &work_cv);

  // Stage 2: BlockID = BLAKE3(id[0..81])
  var id0: array<u32, 16>;
  for (var i: u32 = 0u; i < 12u; i = i + 1u) {
    id0[i] = params.id_prefix_words[i];
  }
  id0[12] = (params.id_prefix_words[12] & 0xffu) | (work_cv[0] << 8u);
  id0[13] = (work_cv[0] >> 24u) | (work_cv[1] << 8u);
  id0[14] = (work_cv[1] >> 24u) | (work_cv[2] << 8u);
  id0[15] = (work_cv[2] >> 24u) | (work_cv[3] << 8u);

  b3_compress(&iv, &id0, 64u, 1u, &cv);

  var id1: array<u32, 16>;
  id1[0] = (work_cv[3] >> 24u) | (work_cv[4] << 8u);
  id1[1] = (work_cv[4] >> 24u) | (work_cv[5] << 8u);
  id1[2] = (work_cv[5] >> 24u) | (work_cv[6] << 8u);
  id1[3] = (work_cv[6] >> 24u) | (work_cv[7] << 8u);
  id1[4] = work_cv[7] >> 24u;
  for (var i: u32 = 5u; i < 16u; i = i + 1u) {
    id1[i] = 0u;
  }
  var block_cv: array<u32, 8>;
  b3_compress(&cv, &id1, 17u, 10u, &block_cv);

  // Compare BlockID <= Target as 256-bit unsigned little-endian
  var accept: u32 = 1u;
  for (var k: u32 = 0u; k < 8u; k = k + 1u) {
    let idx: u32 = 7u - k;
    let bw: u32 = block_cv[idx];
    let tw: u32 = params.target_words[idx];
    if (bw < tw) {
      break;
    }
    if (bw > tw) {
      accept = 0u;
      break;
    }
  }

  if (accept == 1u) {
    let hit_idx: u32 = atomicAdd(&hits.count, 1u);
    if (hit_idx < params.max_hits) {
      hits.records[hit_idx].nonce_lo = n_lo;
      hits.records[hit_idx].nonce_hi = n_hi;
      for (var i: u32 = 0u; i < 8u; i = i + 1u) {
        hits.records[hit_idx].block_id[i] = block_cv[i];
        hits.records[hit_idx].work_hash[i] = work_cv[i];
      }
    }
  }
}
`;

  /**
   * High-level Hybrid WebGPU / Web Worker Miner Manager
   */
  class LotusV2MinerEngine {
    constructor(options = {}) {
      this.onShare = options.onShare || (() => {});
      this.onStats = options.onStats || (() => {});
      this.onBackendChange = options.onBackendChange || (() => {});
      this.workerScriptUrl = options.workerScriptUrl || '/miner-worker.js';
      this.preferBackend = options.preferBackend || 'auto'; // 'auto' | 'webgpu' | 'worker'

      this.backend = 'initializing';
      this.device = null;
      this.pipeline = null;
      this.paramsBuffer = null;
      this.hitsBuffer = null;
      this.countReadbackBuffer = null;
      this.fullReadbackBuffer = null;
      this.bindGroup = null;
      this.zeroU32 = new Uint32Array([0]);

      this.worker = null;
      this.running = false;
      this.currentJob = null;
      this.currentNonce = 0n;
      this.workgroupsPerDispatch = 64; // 64 * 256 = 16,384 nonces initial batch
      this.totalHashes = 0;
      this.currentHashrate = 0;
      this.lastDispatchMs = 0;
    }

    async init() {
      if (this.preferBackend !== 'worker' && typeof navigator !== 'undefined' && navigator.gpu) {
        try {
          const adapter = await navigator.gpu.requestAdapter({
            powerPreference: 'high-performance',
          });
          if (adapter) {
            const device = await adapter.requestDevice();
            const shaderModule = device.createShaderModule({
              label: 'Lotus V2 Tagged BLAKE3 WGSL Shader',
              code: LOTUS_V2_WGSL,
            });
            const pipeline = await device.createComputePipelineAsync({
              label: 'Lotus V2 Compute Pipeline',
              layout: 'auto',
              compute: {
                module: shaderModule,
                entryPoint: 'find_nonce_matches',
              },
            });

            // MinerParams: 18 + 13 + 8 + 5 = 44 u32 words = 176 bytes
            const paramsBuffer = device.createBuffer({
              size: 176,
              usage: GPUBufferUsage.UNIFORM | GPUBufferUsage.COPY_DST,
            });

            // HitBuffer: 4 u32 header (16 bytes) + 32 * 18 u32 (2304 bytes) = 2320 bytes
            const hitBufferSize = 16 + MAX_HITS_PER_DISPATCH * 18 * 4;
            const hitsBuffer = device.createBuffer({
              size: hitBufferSize,
              usage: GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_SRC | GPUBufferUsage.COPY_DST,
            });

            // 4-byte staging buffer for fast zero-share check
            const countReadbackBuffer = device.createBuffer({
              size: 4,
              usage: GPUBufferUsage.MAP_READ | GPUBufferUsage.COPY_DST,
            });

            // Full staging buffer only mapped when count > 0
            const fullReadbackBuffer = device.createBuffer({
              size: hitBufferSize,
              usage: GPUBufferUsage.MAP_READ | GPUBufferUsage.COPY_DST,
            });

            const bindGroup = device.createBindGroup({
              layout: pipeline.getBindGroupLayout(0),
              entries: [
                { binding: 0, resource: { buffer: paramsBuffer } },
                { binding: 1, resource: { buffer: hitsBuffer } },
              ],
            });

            this.device = device;
            this.pipeline = pipeline;
            this.paramsBuffer = paramsBuffer;
            this.hitsBuffer = hitsBuffer;
            this.countReadbackBuffer = countReadbackBuffer;
            this.fullReadbackBuffer = fullReadbackBuffer;
            this.bindGroup = bindGroup;
            this.backend = 'webgpu-wgsl';
            this.onBackendChange(this.backend);
            return this.backend;
          }
        } catch (err) {
          console.warn('WebGPU initialization failed, falling back to Web Worker:', err);
        }
      }

      // Fallback to Web Worker or in-thread CPU loop
      this.backend = 'web-worker-cpu';
      this.onBackendChange(this.backend);
      return this.backend;
    }

    setJob(job) {
      const header = Core.hexToBytes(job.header);
      const chainId = Core.hexToBytes(job.chain_id);
      const target = Core.hexToBytes(job.target);
      const prepared = Core.prepareTemplates(header, chainId, target);
      this.currentJob = {
        job_id: job.job_id,
        header,
        chainId,
        target,
        ...prepared,
        bodyHashHex: Core.bytesToHex(prepared.bodyHash),
      };
      // Randomize or reset starting nonce offset per job to avoid duplicate work across tabs
      this.currentNonce =
        job.start_nonce !== undefined
          ? BigInt(job.start_nonce)
          : BigInt(Math.floor(Math.random() * 0x10000000));

      if (this.worker) {
        this.worker.postMessage({
          type: 'job',
          job_id: job.job_id,
          header: job.header,
          chain_id: job.chain_id,
          target: job.target,
          start_nonce: this.currentNonce.toString(),
        });
      }
    }

    async start() {
      if (this.running) return;
      if (this.backend === 'initializing') {
        await this.init();
      }
      this.running = true;

      if (this.backend === 'webgpu-wgsl' && this.device) {
        this._scheduleWebGPUFrame();
      } else {
        this._startWorkerFallback();
      }
    }

    stop() {
      this.running = false;
      if (this.worker) {
        this.worker.postMessage({ type: 'stop' });
      }
    }

    _startWorkerFallback() {
      if (typeof Worker !== 'undefined' && !this.worker) {
        try {
          this.worker = new Worker(this.workerScriptUrl);
          this.worker.onmessage = (ev) => {
            const msg = ev.data || {};
            if (msg.type === 'share') {
              this.onShare(msg);
            } else if (msg.type === 'progress') {
              this.totalHashes += msg.hashes;
              this.currentHashrate = msg.hashrate_hps;
              this.lastDispatchMs = msg.duration_ms;
              this.onStats({
                backend: this.backend,
                hashrate_hps: this.currentHashrate,
                total_hashes: this.totalHashes,
                dispatch_ms: this.lastDispatchMs,
                batch_size: msg.hashes,
              });
            }
          };
          if (this.currentJob) {
            this.worker.postMessage({
              type: 'job',
              job_id: this.currentJob.job_id,
              header: Core.bytesToHex(this.currentJob.header),
              chain_id: Core.bytesToHex(this.currentJob.chainId),
              target: Core.bytesToHex(this.currentJob.target),
              start_nonce: this.currentNonce.toString(),
            });
          }
          this.worker.postMessage({ type: 'start' });
          return;
        } catch (err) {
          console.warn('Dedicated Worker creation failed, using async slice fallback:', err);
        }
      } else if (this.worker) {
        this.worker.postMessage({ type: 'start' });
        return;
      }

      // Direct async slice fallback (for headless environments without Worker)
      const step = () => {
        if (!this.running) return;
        if (!this.currentJob) {
          setTimeout(step, 25);
          return;
        }
        const batchSize = 2048;
        const t0 = performance.now();
        const { matches } = Core.hashNoncesWordBatch(
          this.currentJob.workWords,
          this.currentJob.idPrefixWords,
          this.currentJob.targetWords,
          this.currentNonce,
          batchSize,
          false
        );
        const dt = Math.max(0.2, performance.now() - t0);
        this.currentNonce = BigInt.asUintN(64, this.currentNonce + BigInt(batchSize));
        this.totalHashes += batchSize;
        this.currentHashrate = (batchSize * 1000) / dt;
        this.lastDispatchMs = dt;

        for (const hit of matches) {
          const solvedHeader = Core.writeNonceLE(this.currentJob.header, hit.nonce);
          this.onShare({
            type: 'share',
            backend: this.backend,
            job_id: this.currentJob.job_id,
            nonce: hit.nonce.toString(),
            nonce_hex: hit.nonce.toString(16).padStart(16, '0'),
            header_hex: Core.bytesToHex(solvedHeader),
            block_id_hex: Core.bytesToHex(hit.blockId),
            work_hash_hex: Core.bytesToHex(hit.workHash),
            body_hash_hex: this.currentJob.bodyHashHex,
          });
        }

        this.onStats({
          backend: this.backend,
          hashrate_hps: this.currentHashrate,
          total_hashes: this.totalHashes,
          dispatch_ms: this.lastDispatchMs,
          batch_size: batchSize,
        });

        setTimeout(step, 4);
      };
      setTimeout(step, 0);
    }

    _scheduleWebGPUFrame() {
      const raf =
        typeof requestAnimationFrame === 'function'
          ? requestAnimationFrame
          : (fn) => setTimeout(fn, 16);

      raf(async () => {
        if (!this.running) return;
        if (!this.currentJob) {
          this._scheduleWebGPUFrame();
          return;
        }
        try {
          await this._dispatchWebGPUBatch();
        } catch (err) {
          console.error('WebGPU dispatch error, switching to worker fallback:', err);
          this.backend = 'web-worker-cpu';
          this.onBackendChange(this.backend);
          this._startWorkerFallback();
          return;
        }
        if (this.running) {
          this._scheduleWebGPUFrame();
        }
      });
    }

    async _dispatchWebGPUBatch() {
      const job = this.currentJob;
      const workgroups = this.workgroupsPerDispatch;
      const batchCount = workgroups * WORKGROUP_SIZE;
      const nonceLo = Number(this.currentNonce & 0xffffffffn) >>> 0;
      const nonceHi = Number((this.currentNonce >> 32n) & 0xffffffffn) >>> 0;

      const paramsWords = new Uint32Array(44);
      paramsWords.set(job.workWords, 0); // 0..18
      paramsWords.set(job.idPrefixWords, 18); // 18..31
      paramsWords.set(job.targetWords, 31); // 31..39
      paramsWords[39] = nonceLo;
      paramsWords[40] = nonceHi;
      paramsWords[41] = batchCount >>> 0;
      paramsWords[42] = MAX_HITS_PER_DISPATCH;
      paramsWords[43] = 0;

      const t0 = performance.now();
      this.device.queue.writeBuffer(this.paramsBuffer, 0, paramsWords);
      // Reset atomic hit counter to 0 (4 bytes)
      this.device.queue.writeBuffer(this.hitsBuffer, 0, this.zeroU32);

      const encoder = this.device.createCommandEncoder();
      const pass = encoder.beginComputePass();
      pass.setPipeline(this.pipeline);
      pass.setBindGroup(0, this.bindGroup);
      pass.dispatchWorkgroups(workgroups);
      pass.end();

      // Copy ONLY the 4-byte atomic<u32> count first!
      encoder.copyBufferToBuffer(this.hitsBuffer, 0, this.countReadbackBuffer, 0, 4);
      this.device.queue.submit([encoder.finish()]);

      await this.countReadbackBuffer.mapAsync(GPUMapMode.READ);
      const countView = new Uint32Array(this.countReadbackBuffer.getMappedRange());
      const hitCount = Math.min(countView[0], MAX_HITS_PER_DISPATCH);
      this.countReadbackBuffer.unmap();

      const dt = Math.max(0.2, performance.now() - t0);
      this.currentNonce = BigInt.asUintN(64, this.currentNonce + BigInt(batchCount));
      this.totalHashes += batchCount;
      this.currentHashrate = (batchCount * 1000) / dt;
      this.lastDispatchMs = dt;

      if (hitCount > 0) {
        const readSize = 16 + hitCount * 18 * 4;
        const hitEncoder = this.device.createCommandEncoder();
        hitEncoder.copyBufferToBuffer(this.hitsBuffer, 0, this.fullReadbackBuffer, 0, readSize);
        this.device.queue.submit([hitEncoder.finish()]);

        await this.fullReadbackBuffer.mapAsync(GPUMapMode.READ, 0, readSize);
        const words = new Uint32Array(this.fullReadbackBuffer.getMappedRange(0, readSize));
        for (let i = 0; i < hitCount; i++) {
          const base = 4 + i * 18;
          const hLo = words[base] >>> 0;
          const hHi = words[base + 1] >>> 0;
          const nonce = (BigInt(hHi) << 32n) | BigInt(hLo);

          // Independent CPU verification of GPU candidate before submitting
          const candidateHeader = Core.writeNonceLE(job.header, nonce);
          const verified = Core.hashes(candidateHeader, job.chainId);
          if (Core.meetsTarget(verified.blockId, job.target)) {
            this.onShare({
              type: 'share',
              backend: 'webgpu-wgsl',
              job_id: job.job_id,
              nonce: nonce.toString(),
              nonce_hex: nonce.toString(16).padStart(16, '0'),
              header_hex: Core.bytesToHex(candidateHeader),
              block_id_hex: Core.bytesToHex(verified.blockId),
              work_hash_hex: Core.bytesToHex(verified.workHash),
              body_hash_hex: job.bodyHashHex,
            });
          }
        }
        this.fullReadbackBuffer.unmap();
      }

      // Smoothly auto-tune workgroups toward TARGET_DISPATCH_MS (~3ms per frame)
      const ratio = Math.max(0.5, Math.min(2.0, TARGET_DISPATCH_MS / dt));
      this.workgroupsPerDispatch = Math.max(
        16,
        Math.min(16384, Math.round(workgroups * (0.75 + 0.25 * ratio)))
      );

      this.onStats({
        backend: this.backend,
        hashrate_hps: this.currentHashrate,
        total_hashes: this.totalHashes,
        dispatch_ms: this.lastDispatchMs,
        batch_size: batchCount,
        workgroups: this.workgroupsPerDispatch,
      });
    }
  }

  return {
    WORKGROUP_SIZE,
    MAX_HITS_PER_DISPATCH,
    TARGET_DISPATCH_MS,
    LOTUS_V2_WGSL,
    LotusV2MinerEngine,
  };
});
