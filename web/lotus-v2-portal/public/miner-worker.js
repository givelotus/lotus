/**
 * Lotus V2 Tagged BLAKE3 Miner Worker & CPU/SIMD Fallback Engine
 *
 * Implements bit-for-bit parity with `miner/kernels/lotus_v2.cl` and `v2_header.rs`:
 * - BodyHash = BLAKE3("Lotus/v2/header/body" || 0x00 || ChainID[32] || header[50..134])
 * - WorkHash = BLAKE3("Lotus/v2/header/work" || 0x00 || bits[4] || time[6] || nonce[8] || BodyHash[32])
 * - BlockID  = BLAKE3("Lotus/v2/blockid"     || 0x00 || parentID[32] || WorkHash[32])
 * - Target comparison: 256-bit unsigned little-endian inclusive (BlockID <= Target)
 */

(function (root, factory) {
  if (typeof module === 'object' && module.exports) {
    module.exports = factory();
  } else {
    const api = factory();
    root.LotusV2MinerCore = api;
  }
})(typeof self !== 'undefined' ? self : globalThis, function () {
  'use strict';

  const HEADER_LEN = 134;
  const NONCE_OFFSET = 42;
  const BODY_OFFSET = 50;

  const B3_IV = new Uint32Array([
    0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
    0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19,
  ]);

  const B3_SCHEDULE = [
    new Uint8Array([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]),
    new Uint8Array([2, 6, 3, 10, 7, 0, 4, 13, 1, 11, 12, 5, 9, 14, 15, 8]),
    new Uint8Array([3, 4, 10, 12, 13, 2, 7, 14, 6, 5, 9, 0, 11, 15, 8, 1]),
    new Uint8Array([10, 7, 12, 9, 14, 3, 13, 15, 4, 0, 11, 2, 5, 8, 1, 6]),
    new Uint8Array([12, 13, 9, 11, 15, 10, 14, 8, 7, 2, 5, 3, 0, 1, 6, 4]),
    new Uint8Array([9, 14, 11, 5, 8, 12, 15, 1, 13, 3, 0, 10, 2, 6, 4, 7]),
    new Uint8Array([11, 15, 5, 0, 1, 9, 8, 6, 14, 10, 2, 12, 3, 4, 7, 13]),
  ];

  const TAG_BODY = encodeAsciiWithNull('Lotus/v2/header/body');
  const TAG_WORK = encodeAsciiWithNull('Lotus/v2/header/work');
  const TAG_BLOCKID = encodeAsciiWithNull('Lotus/v2/blockid');

  function encodeAsciiWithNull(str) {
    const out = new Uint8Array(str.length + 1);
    for (let i = 0; i < str.length; i++) {
      out[i] = str.charCodeAt(i) & 0xff;
    }
    out[str.length] = 0;
    return out;
  }

  function rotl32(x, n) {
    return ((x << n) | (x >>> (32 - n))) >>> 0;
  }

  /**
   * Exact port of `b3_g` from `miner/kernels/lotus_v2.cl`
   */
  function b3_g(v, a, b, c, d, x, y) {
    v[a] = (v[a] + v[b] + x) >>> 0;
    v[d] = rotl32(v[d] ^ v[a], 16);
    v[c] = (v[c] + v[d]) >>> 0;
    v[b] = rotl32(v[b] ^ v[c], 20);
    v[a] = (v[a] + v[b] + y) >>> 0;
    v[d] = rotl32(v[d] ^ v[a], 24);
    v[c] = (v[c] + v[d]) >>> 0;
    v[b] = rotl32(v[b] ^ v[c], 25);
  }

  /**
   * Exact port of `b3_compress` from `miner/kernels/lotus_v2.cl` operating on 16 u32 words
   */
  function b3_compress_words(cv, m, blockLen, flags, out) {
    const v = new Uint32Array(16);
    for (let i = 0; i < 8; i++) v[i] = cv[i];
    for (let i = 0; i < 4; i++) v[i + 8] = B3_IV[i];
    v[12] = 0;
    v[13] = 0;
    v[14] = blockLen >>> 0;
    v[15] = flags >>> 0;

    for (let r = 0; r < 7; r++) {
      const s = B3_SCHEDULE[r];
      b3_g(v, 0, 4, 8, 12, m[s[0]], m[s[1]]);
      b3_g(v, 1, 5, 9, 13, m[s[2]], m[s[3]]);
      b3_g(v, 2, 6, 10, 14, m[s[4]], m[s[5]]);
      b3_g(v, 3, 7, 11, 15, m[s[6]], m[s[7]]);
      b3_g(v, 0, 5, 10, 15, m[s[8]], m[s[9]]);
      b3_g(v, 1, 6, 11, 12, m[s[10]], m[s[11]]);
      b3_g(v, 2, 7, 8, 13, m[s[12]], m[s[13]]);
      b3_g(v, 3, 4, 9, 14, m[s[14]], m[s[15]]);
    }

    for (let i = 0; i < 8; i++) {
      out[i] = (v[i] ^ v[i + 8]) >>> 0;
    }
  }

  /**
   * Exact port of `b3_compress` from `miner/kernels/lotus_v2.cl` operating on a 64-byte block
   */
  function b3_compress(cv, block, blockLen, flags, out) {
    const m = new Uint32Array(16);
    for (let i = 0; i < 16; i++) {
      const j = i * 4;
      m[i] =
        (block[j] |
          (block[j + 1] << 8) |
          (block[j + 2] << 16) |
          (block[j + 3] << 24)) >>>
        0;
    }
    b3_compress_words(cv, m, blockLen, flags, out);
  }

  /**
   * Exact port of `b3_hash` from `miner/kernels/lotus_v2.cl` (single-chunk messages <= 1024 bytes)
   */
  function b3_hash(msg) {
    const len = msg.length;
    const cv = new Uint32Array(B3_IV);
    const out = new Uint32Array(8);
    const block = new Uint8Array(64);
    const blocks = Math.max(1, Math.ceil(len / 64));

    for (let b = 0; b < blocks; b++) {
      block.fill(0);
      for (let j = 0; j < 64; j++) {
        const index = b * 64 + j;
        if (index < len) block[j] = msg[index];
      }
      const last = b + 1 === blocks;
      const flags = (b === 0 ? 1 : 0) | (last ? 2 | 8 : 0);
      const blockLen = last ? len - b * 64 : 64;
      b3_compress(cv, block, blockLen, flags, out);
      if (!last) {
        cv.set(out);
      }
    }

    const digest = new Uint8Array(32);
    for (let i = 0; i < 8; i++) {
      digest[i * 4] = out[i] & 0xff;
      digest[i * 4 + 1] = (out[i] >>> 8) & 0xff;
      digest[i * 4 + 2] = (out[i] >>> 16) & 0xff;
      digest[i * 4 + 3] = (out[i] >>> 24) & 0xff;
    }
    return digest;
  }

  function taggedHash(tagBytes, payload) {
    const msg = new Uint8Array(tagBytes.length + payload.length);
    msg.set(tagBytes, 0);
    msg.set(payload, tagBytes.length);
    return b3_hash(msg);
  }

  /**
   * Computes BodyHash, WorkHash, and BlockID for a 134-byte Lotus V2 header and 32-byte ChainID.
   */
  function hashes(header, chainId) {
    if (header.length !== HEADER_LEN) {
      throw new Error(`V2 header must be exactly ${HEADER_LEN} bytes, got ${header.length}`);
    }
    if (chainId.length !== 32) {
      throw new Error(`ChainID must be 32 bytes, got ${chainId.length}`);
    }

    const bodyPayload = new Uint8Array(116);
    bodyPayload.set(chainId, 0);
    bodyPayload.set(header.subarray(BODY_OFFSET, HEADER_LEN), 32);
    const bodyHash = taggedHash(TAG_BODY, bodyPayload);

    const workPayload = new Uint8Array(50);
    workPayload.set(header.subarray(32, BODY_OFFSET), 0);
    workPayload.set(bodyHash, 18);
    const workHash = taggedHash(TAG_WORK, workPayload);

    const idPayload = new Uint8Array(64);
    idPayload.set(header.subarray(0, 32), 0);
    idPayload.set(workHash, 32);
    const blockId = taggedHash(TAG_BLOCKID, idPayload);

    return { bodyHash, workHash, blockId };
  }

  /**
   * Compare two 32-byte arrays as unsigned 256-bit little-endian integers (inclusive: blockId <= target).
   */
  function meetsTarget(blockId, target) {
    for (let i = 31; i >= 0; i--) {
      if (blockId[i] < target[i]) return true;
      if (blockId[i] > target[i]) return false;
    }
    return true;
  }

  /**
   * Pre-packs a 134-byte header, 32-byte chainId, and 32-byte target into:
   * - workWords[18] (u32 LE words for 71-byte work template padded to 72 bytes)
   * - idPrefixWords[13] (u32 LE words for 49-byte id prefix padded to 52 bytes)
   * - targetWords[8] (u32 LE words for 32-byte target)
   * - bodyHash (Uint8Array[32])
   * - workTemplate (Uint8Array[71])
   * - idTemplate (Uint8Array[81])
   */
  function prepareTemplates(header, chainId, target) {
    const { bodyHash } = hashes(header, chainId);

    const workTemplate = new Uint8Array(71);
    workTemplate.set(TAG_WORK, 0); // 21 bytes
    workTemplate.set(header.subarray(32, NONCE_OFFSET), 21); // 10 bytes (bits + time)
    // bytes 31..39 are nonce (zeroed in template)
    workTemplate.set(bodyHash, 39); // 32 bytes

    const idTemplate = new Uint8Array(81);
    idTemplate.set(TAG_BLOCKID, 0); // 17 bytes
    idTemplate.set(header.subarray(0, 32), 17); // 32 bytes (parentID)

    const workPadded = new Uint8Array(72);
    workPadded.set(workTemplate, 0);
    const workWords = new Uint32Array(18);
    for (let i = 0; i < 18; i++) {
      const j = i * 4;
      workWords[i] =
        (workPadded[j] |
          (workPadded[j + 1] << 8) |
          (workPadded[j + 2] << 16) |
          (workPadded[j + 3] << 24)) >>>
        0;
    }

    const idPrefixPadded = new Uint8Array(52);
    idPrefixPadded.set(idTemplate.subarray(0, 49), 0);
    const idPrefixWords = new Uint32Array(13);
    for (let i = 0; i < 13; i++) {
      const j = i * 4;
      idPrefixWords[i] =
        (idPrefixPadded[j] |
          (idPrefixPadded[j + 1] << 8) |
          (idPrefixPadded[j + 2] << 16) |
          (idPrefixPadded[j + 3] << 24)) >>>
        0;
    }

    const targetWords = new Uint32Array(8);
    if (target) {
      for (let i = 0; i < 8; i++) {
        const j = i * 4;
        targetWords[i] =
          (target[j] |
            (target[j + 1] << 8) |
            (target[j + 2] << 16) |
            (target[j + 3] << 24)) >>>
          0;
      }
    }

    return {
      bodyHash,
      workTemplate,
      idTemplate,
      workWords,
      idPrefixWords,
      targetWords,
    };
  }

  /**
   * Fast word-level 2-stage BLAKE3 batch evaluator matching `find_nonce_matches` & `hash_nonces` in `lotus_v2.cl`.
   */
  function hashNoncesWordBatch(workWords, idPrefixWords, targetWords, startNonceBigInt, count, collectAllDigests = false) {
    const m0 = new Uint32Array(16);
    const m1 = new Uint32Array(16);
    const id0 = new Uint32Array(16);
    const id1 = new Uint32Array(16);
    const cv = new Uint32Array(8);
    const workCv = new Uint32Array(8);
    const blockCv = new Uint32Array(8);

    for (let i = 0; i < 16; i++) m0[i] = workWords[i];
    m1[0] = workWords[16];
    m1[1] = workWords[17] & 0x00ffffff;

    for (let i = 0; i < 12; i++) id0[i] = idPrefixWords[i];
    const idWord12Base = idPrefixWords[12] & 0xff;

    const matches = [];
    const allResults = collectAllDigests ? [] : null;
    const baseNonce = BigInt.asUintN(64, BigInt(startNonceBigInt));

    for (let lane = 0; lane < count; lane++) {
      const nonce = BigInt.asUintN(64, baseNonce + BigInt(lane));
      const nLo = Number(nonce & 0xffffffffn) >>> 0;
      const nHi = Number((nonce >> 32n) & 0xffffffffn) >>> 0;

      m0[7] = ((workWords[7] & 0x00ffffff) | ((nLo & 0xff) << 24)) >>> 0;
      m0[8] = ((nLo >>> 8) | ((nHi & 0xff) << 24)) >>> 0;
      m0[9] = ((workWords[9] & 0xff000000) | (nHi >>> 8)) >>> 0;

      // Stage 1: WorkHash (71 bytes = 64 + 7)
      b3_compress_words(B3_IV, m0, 64, 1, cv);
      b3_compress_words(cv, m1, 7, 10, workCv);

      // Stage 2: BlockID (81 bytes = 64 + 17)
      id0[12] = (idWord12Base | (workCv[0] << 8)) >>> 0;
      id0[13] = ((workCv[0] >>> 24) | (workCv[1] << 8)) >>> 0;
      id0[14] = ((workCv[1] >>> 24) | (workCv[2] << 8)) >>> 0;
      id0[15] = ((workCv[2] >>> 24) | (workCv[3] << 8)) >>> 0;

      id1[0] = ((workCv[3] >>> 24) | (workCv[4] << 8)) >>> 0;
      id1[1] = ((workCv[4] >>> 24) | (workCv[5] << 8)) >>> 0;
      id1[2] = ((workCv[5] >>> 24) | (workCv[6] << 8)) >>> 0;
      id1[3] = ((workCv[6] >>> 24) | (workCv[7] << 8)) >>> 0;
      id1[4] = (workCv[7] >>> 24) >>> 0;

      b3_compress_words(B3_IV, id0, 64, 1, cv);
      b3_compress_words(cv, id1, 17, 10, blockCv);

      let accept = true;
      for (let i = 7; i >= 0; i--) {
        const bw = blockCv[i] >>> 0;
        const tw = targetWords[i] >>> 0;
        if (bw < tw) break;
        if (bw > tw) {
          accept = false;
          break;
        }
      }

      if (accept || collectAllDigests) {
        const blockId = wordsToBytes32(blockCv);
        if (accept) {
          matches.push({
            nonce,
            nonceLo: nLo,
            nonceHi: nHi,
            blockId,
            workHash: wordsToBytes32(workCv),
          });
        }
        if (collectAllDigests) {
          allResults.push({
            nonce,
            blockId,
            meetsTarget: accept,
          });
        }
      }
    }

    return { matches, allResults };
  }

  function wordsToBytes32(words) {
    const out = new Uint8Array(32);
    for (let i = 0; i < 8; i++) {
      const w = words[i] >>> 0;
      out[i * 4] = w & 0xff;
      out[i * 4 + 1] = (w >>> 8) & 0xff;
      out[i * 4 + 2] = (w >>> 16) & 0xff;
      out[i * 4 + 3] = (w >>> 24) & 0xff;
    }
    return out;
  }

  function hexToBytes(hex) {
    const clean = String(hex).trim().replace(/^0x/i, '');
    if (clean.length % 2 !== 0) {
      throw new Error(`Invalid hex length: ${clean.length}`);
    }
    const out = new Uint8Array(clean.length / 2);
    for (let i = 0; i < out.length; i++) {
      const byte = parseInt(clean.substr(i * 2, 2), 16);
      if (Number.isNaN(byte)) throw new Error(`Invalid hex at index ${i * 2}`);
      out[i] = byte;
    }
    return out;
  }

  function bytesToHex(bytes) {
    let s = '';
    for (let i = 0; i < bytes.length; i++) {
      s += bytes[i].toString(16).padStart(2, '0');
    }
    return s;
  }

  function writeNonceLE(header, nonceBigInt) {
    const out = new Uint8Array(header);
    let n = BigInt.asUintN(64, BigInt(nonceBigInt));
    for (let i = 0; i < 8; i++) {
      out[NONCE_OFFSET + i] = Number(n & 0xffn);
      n >>= 8n;
    }
    return out;
  }

  // Web Worker message loop when loaded inside a dedicated Worker
  const isDedicatedWorker =
    typeof WorkerGlobalScope !== 'undefined' && self instanceof WorkerGlobalScope;

  if (isDedicatedWorker) {
    let mining = false;
    let currentJob = null;
    let currentNonce = 0n;
    let batchSize = 4096;
    let loopTimer = null;

    function runStep() {
      if (!mining || !currentJob) return;
      const t0 = performance.now();
      const { matches } = hashNoncesWordBatch(
        currentJob.workWords,
        currentJob.idPrefixWords,
        currentJob.targetWords,
        currentNonce,
        batchSize,
        false
      );
      const dt = Math.max(0.2, performance.now() - t0);
      const hashesDone = batchSize;
      currentNonce = BigInt.asUintN(64, currentNonce + BigInt(batchSize));

      for (const hit of matches) {
        const solvedHeader = writeNonceLE(currentJob.header, hit.nonce);
        self.postMessage({
          type: 'share',
          backend: 'web-worker-cpu',
          job_id: currentJob.job_id,
          nonce: hit.nonce.toString(),
          nonce_hex: hit.nonce.toString(16).padStart(16, '0'),
          header_hex: bytesToHex(solvedHeader),
          block_id_hex: bytesToHex(hit.blockId),
          work_hash_hex: bytesToHex(hit.workHash),
          body_hash_hex: currentJob.bodyHashHex,
        });
      }

      self.postMessage({
        type: 'progress',
        backend: 'web-worker-cpu',
        hashes: hashesDone,
        duration_ms: dt,
        hashrate_hps: (hashesDone * 1000) / dt,
      });

      // Auto-tune worker slice toward ~8ms so it stays responsive to job updates
      batchSize = Math.max(512, Math.min(32768, Math.round(batchSize * (8.0 / dt))));
      loopTimer = setTimeout(runStep, 0);
    }

    self.onmessage = function (ev) {
      const msg = ev.data || {};
      if (msg.type === 'job') {
        const header = hexToBytes(msg.header);
        const chainId = hexToBytes(msg.chain_id);
        const target = hexToBytes(msg.target);
        const prepared = prepareTemplates(header, chainId, target);
        currentJob = {
          job_id: msg.job_id,
          header,
          chainId,
          target,
          ...prepared,
          bodyHashHex: bytesToHex(prepared.bodyHash),
        };
        currentNonce = BigInt(msg.start_nonce || 0);
      } else if (msg.type === 'start') {
        if (!mining) {
          mining = true;
          runStep();
        }
      } else if (msg.type === 'stop') {
        mining = false;
        if (loopTimer) {
          clearTimeout(loopTimer);
          loopTimer = null;
        }
      }
    };
  }

  return {
    HEADER_LEN,
    NONCE_OFFSET,
    BODY_OFFSET,
    B3_IV,
    B3_SCHEDULE,
    b3_g,
    b3_compress,
    b3_compress_words,
    b3_hash,
    hashes,
    meetsTarget,
    prepareTemplates,
    hashNoncesWordBatch,
    hexToBytes,
    bytesToHex,
    writeNonceLE,
  };
});
