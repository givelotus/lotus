#!/usr/bin/env node
/**
 * Lotus V2 Testnet Explorer & Transaction Workbench Server
 *
 * Zero-dependency Node.js server that connects directly to a local/LAN
 * 3-node `lotusd -chronik=1` cluster and `tools/lotus-v2-compiler`:
 *   1. Serves the interactive Lotus V2 Testnet Explorer & Transaction Workbench UI (`/`)
 *   2. Provides live REST endpoints for:
 *      - `/api/overview`: 3-node cluster status, 134-byte V2 headers, TxRoot, StateRoot,
 *        SubtreeA, O(1) getblocktemplate commitments, coinbase 50/25/25 split, mempool
 *        overlay stats, and Chronik protobuf `/blockchain-info` & `/chronik-info` sync.
 *      - `/api/block/:id_or_height`: Full 134-byte V2 header breakdown, SubtreeA,
 *        StateRoot, coinbase 50/25/25 split, decoded V2 v7 transactions, and Chronik check.
 *      - `/api/tx/:txid`: Lock-free `getrawtransaction` + `getmempoolentry` + Chronik
 *        `/tx/:txid` + V2 v7 wire/witness/3-branch decoder.
 *      - `/api/utxo/:txid/:vout`: Lock-free SMT `gettxout` + V2 3-branch output decoder.
 *      - `/api/compile`: Live Lotus V2 Contract Compiler (`@lotus/v2-payment-compiler`)
 *        with clang-style diagnostics and gallery presets.
 *      - `/api/send-tx`: Send SQLite wallet payment, V2 v7 BigInt+Introspection contract tx,
 *        compiled Hashlock/Payment contract tx, or V2 v7 Token Mint (`nFlags=3`) & Transfer (`nFlags=1`).
 *      - `/api/burst`: Atomic batch burst via `testrawtxbatch` + `submitrawtxbatch` with live TPS.
 *      - `/api/mine`: Mine N blocks via `generatetoaddress` and verify 3-node P2P + Chronik sync.
 *   3. Implements the `/v2/explorer/v1/*` schema-1 JSON contract (forwarding to Chronik if
 *      natively mounted, or translating live from `lotusd` + Chronik) so `explorer/v2/server.mjs`
 *      can also connect to this server as its `--api` upstream.
 */

import http from 'node:http';
import crypto from 'node:crypto';
import { readFile } from 'node:fs/promises';
import { existsSync, readFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(__dirname, '../..');
const COMPILER_DIST = resolve(REPO_ROOT, 'tools/lotus-v2-compiler/dist');
const GALLERY_DIR = resolve(REPO_ROOT, 'tools/lotus-v2-compiler/examples/gallery');

// Parse CLI arguments
const args = process.argv.slice(2);
function getArg(flag, fallback) {
  const idx = args.indexOf(flag);
  return idx >= 0 && args[idx + 1] ? args[idx + 1] : fallback;
}

const PORT = Number(getArg('--port', process.env.PORT || process.env.WORKBENCH_PORT || '32180'));
const BIND_HOST = getArg('--bind', process.env.WORKBENCH_BIND || '127.0.0.1');
const RPC_USER = getArg('--rpc-user', process.env.RPC_USER || process.env.LOTUS_RPC_USER || 'lotusv2');
const RPC_PASS = getArg('--rpc-pass', process.env.RPC_PASS || process.env.LOTUS_RPC_PASS || 'lotusv2pass');
const CANONICAL_EXPLORER_URL = getArg('--canonical-url', process.env.CANONICAL_EXPLORER_URL || 'http://127.0.0.1:32181');

// Default 3-node cluster ports (32110..32132)
const NODES = JSON.parse(
  getArg(
    '--nodes-json',
    process.env.LOTUS_NODES_JSON ||
      JSON.stringify([
        { idx: 0, name: 'Node 0 (Miner & Wallet)', rpcPort: Number(process.env.NODE0_RPC_PORT || 32110), p2pPort: 32111, chronikPort: Number(process.env.CHRONIK_PORT || 32112), wallet: 'node0' },
        { idx: 1, name: 'Node 1 (Relay & Indexer)', rpcPort: Number(process.env.NODE1_RPC_PORT || 32120), p2pPort: 32121, chronikPort: 32122, wallet: 'node1' },
        { idx: 2, name: 'Node 2 (Validator & Indexer)', rpcPort: Number(process.env.NODE2_RPC_PORT || 32130), p2pPort: 32131, chronikPort: 32132, wallet: 'node2' },
      ]),
  ),
);

const SERVICE_EPOCH = 'lotus-v2-testnet-' + crypto.randomBytes(6).toString('hex');
const CHAIN_ID_HEX = '00'.repeat(32);
const PROFILE_ID_HEX = '5030312d5030322d5030332d63616e6469646174652d323032362d31302d3134'; // P01-P02-P03-candidate-2026-10-14

// =============================================================================
// Pure-JS Single-Block BLAKE3 for Lotus/v2/branch Leaf Hashing
// =============================================================================
const BLAKE3_IV = new Uint32Array([
  0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
  0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19,
]);
const BLAKE3_MSG_PERM = [2, 6, 3, 10, 7, 0, 4, 13, 1, 11, 12, 5, 9, 14, 15, 8];

function rotr32(x, n) {
  return ((x >>> n) | (x << (32 - n))) >>> 0;
}

function g(state, a, b, c, d, mx, my) {
  state[a] = (state[a] + state[b] + mx) >>> 0;
  state[d] = rotr32(state[d] ^ state[a], 16);
  state[c] = (state[c] + state[d]) >>> 0;
  state[b] = rotr32(state[b] ^ state[c], 12);
  state[a] = (state[a] + state[b] + my) >>> 0;
  state[d] = rotr32(state[d] ^ state[a], 8);
  state[c] = (state[c] + state[d]) >>> 0;
  state[b] = rotr32(state[b] ^ state[c], 7);
}

function blake3Round(state, m) {
  g(state, 0, 4, 8, 12, m[0], m[1]);
  g(state, 1, 5, 9, 13, m[2], m[3]);
  g(state, 2, 6, 10, 14, m[4], m[5]);
  g(state, 3, 7, 11, 15, m[6], m[7]);
  g(state, 0, 5, 10, 15, m[8], m[9]);
  g(state, 1, 6, 11, 12, m[10], m[11]);
  g(state, 2, 7, 8, 13, m[12], m[13]);
  g(state, 3, 4, 9, 14, m[14], m[15]);
}

function blake3SingleBlock(data) {
  if (data.length > 64) {
    throw new Error('blake3SingleBlock supports <= 64 bytes');
  }
  const padded = Buffer.alloc(64, 0);
  data.copy(padded);
  let m = new Uint32Array(16);
  for (let i = 0; i < 16; i++) {
    m[i] = padded.readUInt32LE(i * 4);
  }
  const state = new Uint32Array(16);
  state.set(BLAKE3_IV, 0);
  state.set(BLAKE3_IV.subarray(0, 4), 8);
  state[12] = 0;
  state[13] = 0;
  state[14] = data.length;
  state[15] = 11; // CHUNK_START | CHUNK_END | ROOT
  for (let r = 0; r < 7; r++) {
    blake3Round(state, m);
    if (r < 6) {
      const next = new Uint32Array(16);
      for (let i = 0; i < 16; i++) next[i] = m[BLAKE3_MSG_PERM[i]];
      m = next;
    }
  }
  const out = Buffer.alloc(32);
  for (let i = 0; i < 8; i++) {
    out.writeUInt32LE((state[i] ^ state[i + 8]) >>> 0, i * 4);
  }
  return out;
}

function compactSize(n) {
  if (n < 253) return Buffer.from([n]);
  if (n <= 0xffff) {
    const b = Buffer.alloc(3);
    b[0] = 0xfd;
    b.writeUInt16LE(n, 1);
    return b;
  }
  if (n <= 0xffffffff) {
    const b = Buffer.alloc(5);
    b[0] = 0xfe;
    b.writeUInt32LE(n >>> 0, 1);
    return b;
  }
  const b = Buffer.alloc(9);
  b[0] = 0xff;
  b.writeBigUInt64LE(BigInt(n), 1);
  return b;
}

function serBytes(buf) {
  return Buffer.concat([compactSize(buf.length), buf]);
}

function branchLeafHash(scriptBuf) {
  const tag = Buffer.from('Lotus/v2/branch\x00\x00', 'binary');
  return blake3SingleBlock(Buffer.concat([tag, compactSize(scriptBuf.length), scriptBuf]));
}

function reverseHex(hexStr) {
  return Buffer.from(hexStr, 'hex').reverse().toString('hex');
}

// =============================================================================
// Native V2 v7 Transaction & 134-Byte Header Serialization / Decoding
// =============================================================================
function serV2SpendInput(prevTxidLe, prevVout, script, argsList = [], siblings = [], pathIndex = 0, sequence = 0xffffffff) {
  const hdr = Buffer.alloc(9);
  hdr.writeUInt32LE(prevVout >>> 0, 0);
  hdr.writeUInt32LE(sequence >>> 0, 4);
  hdr.writeUInt8(1, 8); // flags = 1 (Spend)
  return Buffer.concat([
    prevTxidLe,
    hdr,
    compactSize(pathIndex),
    compactSize(1), // 1 witness
    serBytes(script),
    compactSize(siblings.length),
    ...siblings,
    compactSize(argsList.length),
    ...argsList.map(serBytes),
  ]);
}

function serV2MintInput(tokenIdLe, script, argsList = [], siblings = []) {
  const hdr = Buffer.alloc(9);
  hdr.writeUInt32LE(0, 0);
  hdr.writeUInt32LE(0xffffffff, 4);
  hdr.writeUInt8(3, 8); // flags = 3 (Mint)
  return Buffer.concat([
    tokenIdLe,
    hdr,
    serBytes(script),
    compactSize(siblings.length),
    ...siblings,
    compactSize(argsList.length),
    ...argsList.map(serBytes),
  ]);
}

function serV2Output(valueSats, branchRoot, flags = 0, tokenIdLe = null) {
  const hdr = Buffer.alloc(9);
  hdr.writeUInt8(flags, 0);
  hdr.writeBigUInt64LE(BigInt(valueSats), 1);
  const parts = [hdr];
  if ((flags & 1) !== 0) {
    parts.push(tokenIdLe);
  }
  parts.push(compactSize(1), branchRoot);
  if ((flags & 2) !== 0) {
    parts.push(compactSize(0)); // burn output has 0 paths
  } else {
    parts.push(compactSize(1), compactSize(1), compactSize(0)); // 1 path: [[0]]
  }
  return Buffer.concat(parts);
}

function buildV7TxHex(inputs, outputs, lock = 0n) {
  const hdr = Buffer.alloc(16);
  hdr.writeUInt32LE(7, 0); // version = 7
  hdr.writeBigUInt64LE(BigInt(lock), 4);
  hdr.writeUInt16LE(inputs.length, 12);
  hdr.writeUInt16LE(outputs.length, 14);
  return Buffer.concat([hdr, ...inputs, ...outputs]).toString('hex');
}

function decode134ByteHeader(hdrHex) {
  if (!hdrHex || hdrHex.length !== 268) return null;
  const buf = Buffer.from(hdrHex, 'hex');
  const prevBlockLe = buf.subarray(0, 32);
  const nBits = buf.readUInt32LE(32);
  const nTime = buf.readUIntLE(36, 6);
  const nReserved = buf.readUInt16LE(42);
  const nNonce = buf.readBigUInt64LE(44);
  const nVersion = buf.readUInt32LE(52);
  const nSize = buf.readBigUInt64LE(56);
  const nHeight = buf.readUIntLE(64, 6);
  const txRootLe = buf.subarray(70, 102);
  const stateRootLe = buf.subarray(102, 134);
  return {
    raw_hex: hdrHex,
    byte_length: buf.length,
    prev_block_hash_display: Buffer.from(prevBlockLe).reverse().toString('hex'),
    prev_id_wire: prevBlockLe.toString('hex'),
    bits_u32: nBits.toString(),
    bits_hex: nBits.toString(16).padStart(8, '0'),
    time: nTime.toString(),
    reserved: nReserved,
    nonce: nNonce.toString(),
    version: nVersion.toString(),
    size: nSize.toString(),
    height: nHeight.toString(),
    tx_root_display: Buffer.from(txRootLe).reverse().toString('hex'),
    tx_root_wire: txRootLe.toString('hex'),
    state_root_display: Buffer.from(stateRootLe).reverse().toString('hex'),
    state_root_wire: stateRootLe.toString('hex'),
  };
}

function readCompactSize(buf, offset) {
  if (offset >= buf.length) throw new Error('CompactSize EOF');
  const ch = buf[offset];
  if (ch < 253) return { value: ch, size: 1 };
  if (ch === 253) return { value: buf.readUInt16LE(offset + 1), size: 3 };
  if (ch === 254) return { value: buf.readUInt32LE(offset + 1), size: 5 };
  return { value: Number(buf.readBigUInt64LE(offset + 1)), size: 9 };
}

function tryDecodeV2OutputWire(buf, startOffset = 0) {
  try {
    let off = startOffset;
    if (buf[off] === 0x6a && buf.length - off >= 44) off += 1;
    const flags = buf.readUInt8(off);
    if (flags > 3) return null;
    off += 1;
    const value = buf.readBigUInt64LE(off);
    off += 8;
    let tokenId = '00'.repeat(32);
    const hasToken = (flags & 1) !== 0;
    const isBurn = (flags & 2) !== 0;
    if (hasToken) {
      if (off + 32 > buf.length) return null;
      tokenId = buf.subarray(off, off + 32).toString('hex');
      off += 32;
    }
    const brCount = readCompactSize(buf, off);
    off += brCount.size;
    if (brCount.value < 1 || brCount.value > 16) return null;
    const branches = [];
    for (let i = 0; i < brCount.value; i++) {
      if (off + 32 > buf.length) return null;
      branches.push(buf.subarray(off, off + 32).toString('hex'));
      off += 32;
    }
    const pathCount = readCompactSize(buf, off);
    off += pathCount.size;
    if (isBurn && pathCount.value !== 0) return null;
    if (!isBurn && (pathCount.value < 1 || pathCount.value > 16)) return null;
    const paths = [];
    for (let i = 0; i < pathCount.value; i++) {
      const pLen = readCompactSize(buf, off);
      off += pLen.size;
      if (pLen.value < 1 || pLen.value > 16) return null;
      const p = [];
      for (let j = 0; j < pLen.value; j++) {
        const idx = readCompactSize(buf, off);
        off += idx.size;
        p.push(idx.value.toString());
      }
      paths.push(p);
    }
    if (off !== buf.length) return null;
    return {
      flags: flags.toString(),
      value: value.toString(),
      has_token: hasToken,
      token_id: tokenId,
      is_burn: isBurn,
      branches,
      paths,
    };
  } catch {
    return null;
  }
}

function tryDecodeV7TxWire(hexStr) {
  try {
    const buf = Buffer.from(hexStr, 'hex');
    if (buf.length < 16) return null;
    const version = buf.readUInt32LE(0);
    if (version !== 7) return null;
    const lock = buf.readBigUInt64LE(4);
    const inCount = buf.readUInt16LE(12);
    const outCount = buf.readUInt16LE(14);
    let off = 16;
    const inputs = [];
    for (let i = 0; i < inCount; i++) {
      const prevTxidWire = buf.subarray(off, off + 32).toString('hex');
      const prevTxidDisplay = Buffer.from(buf.subarray(off, off + 32)).reverse().toString('hex');
      off += 32;
      const prevIndex = buf.readUInt32LE(off);
      const sequence = buf.readUInt32LE(off + 4);
      const flags = buf.readUInt8(off + 8);
      off += 9;
      let pathIndex = null;
      let coinbaseData = { present: false, wire_ref: null, hex: null };
      const witnesses = [];
      const readWitness = (wIdx) => {
        const scLen = readCompactSize(buf, off);
        const scOffset = off + scLen.size;
        const scriptHex = buf.subarray(scOffset, scOffset + scLen.value).toString('hex');
        off = scOffset + scLen.value;
        const sibTableStart = off;
        const sibCount = readCompactSize(buf, off);
        off += sibCount.size;
        const siblings = [];
        for (let s = 0; s < sibCount.value; s++) {
          siblings.push(buf.subarray(off, off + 32).toString('hex'));
          off += 32;
        }
        const sibTableEnd = off;
        const argTableStart = off;
        const argCount = readCompactSize(buf, off);
        off += argCount.size;
        const argsInline = [];
        const argsHex = [];
        for (let a = 0; a < argCount.value; a++) {
          const aLen = readCompactSize(buf, off);
          const aStart = off + aLen.size;
          argsInline.push({ offset: aStart.toString(), length: aLen.value.toString() });
          argsHex.push(buf.subarray(aStart, aStart + aLen.value).toString('hex'));
          off = aStart + aLen.value;
        }
        const argTableEnd = off;
        return {
          witness_index: wIdx.toString(),
          script: { offset: scOffset.toString(), length: scLen.value.toString() },
          script_hex: scriptHex,
          siblings: {
            count: sibCount.value.toString(),
            table_ref: { offset: sibTableStart.toString(), length: (sibTableEnd - sibTableStart).toString() },
            inline: siblings,
          },
          arguments: {
            count: argCount.value.toString(),
            table_ref: { offset: argTableStart.toString(), length: (argTableEnd - argTableStart).toString() },
            inline: argsInline,
            hex_values: argsHex,
          },
        };
      };

      if (flags === 1) {
        const pi = readCompactSize(buf, off);
        pathIndex = pi.value.toString();
        off += pi.size;
        const wCount = readCompactSize(buf, off);
        off += wCount.size;
        for (let w = 0; w < wCount.value; w++) {
          witnesses.push(readWitness(w));
        }
      } else if (flags === 2) {
        const cbLen = readCompactSize(buf, off);
        const cbStart = off + cbLen.size;
        coinbaseData = {
          present: true,
          wire_ref: { offset: cbStart.toString(), length: cbLen.value.toString() },
          hex: buf.subarray(cbStart, cbStart + cbLen.value).toString('hex'),
        };
        off = cbStart + cbLen.value;
      } else if (flags === 3) {
        witnesses.push(readWitness(0));
      }
      inputs.push({
        input_index: i.toString(),
        flags: flags.toString(),
        kind: flags === 1 ? 'spend' : flags === 2 ? 'coinbase' : 'mint',
        prev_txid_wire: prevTxidWire,
        prev_txid_display: prevTxidDisplay,
        prev_index: prevIndex.toString(),
        sequence: sequence.toString(),
        path_index: pathIndex,
        witness_count: witnesses.length.toString(),
        coinbase_data: coinbaseData,
        witnesses,
      });
    }
    const outputs = [];
    for (let i = 0; i < outCount; i++) {
      const flags = buf.readUInt8(off);
      const value = buf.readBigUInt64LE(off + 1);
      off += 9;
      let tokenId = '00'.repeat(32);
      const hasToken = (flags & 1) !== 0;
      const isBurn = (flags & 2) !== 0;
      if (hasToken) {
        tokenId = buf.subarray(off, off + 32).toString('hex');
        off += 32;
      }
      const brCount = readCompactSize(buf, off);
      off += brCount.size;
      const branches = [];
      for (let b = 0; b < brCount.value; b++) {
        branches.push(buf.subarray(off, off + 32).toString('hex'));
        off += 32;
      }
      const pathCount = readCompactSize(buf, off);
      off += pathCount.size;
      const paths = [];
      for (let p = 0; p < pathCount.value; p++) {
        const pLen = readCompactSize(buf, off);
        off += pLen.size;
        const pathArr = [];
        for (let k = 0; k < pLen.value; k++) {
          const idx = readCompactSize(buf, off);
          off += idx.size;
          pathArr.push(idx.value.toString());
        }
        paths.push(pathArr);
      }
      outputs.push({
        out_idx: i.toString(),
        flags: flags.toString(),
        value: value.toString(),
        has_token: hasToken,
        token_id: tokenId,
        is_burn: isBurn,
        branches,
        paths,
      });
    }
    return {
      is_v7: true,
      version: '7',
      lock: lock.toString(),
      wire_size: buf.length.toString(),
      inputs,
      outputs,
    };
  } catch {
    return null;
  }
}

// =============================================================================
// JSON-RPC & Chronik HTTP Clients
// =============================================================================
async function rpcCall(node, method, params = [], walletName = null) {
  const path = walletName ? `/wallet/${encodeURIComponent(walletName)}` : '/';
  const auth = Buffer.from(`${RPC_USER}:${RPC_PASS}`).toString('base64');
  const res = await fetch(`http://127.0.0.1:${node.rpcPort}${path}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Basic ${auth}`,
    },
    body: JSON.stringify({ jsonrpc: '1.0', id: 'workbench', method, params }),
    signal: AbortSignal.timeout(10000),
  });
  const json = await res.json();
  if (json.error) {
    const err = new Error(json.error.message || JSON.stringify(json.error));
    err.code = json.error.code;
    throw err;
  }
  return json.result;
}

async function chronikFetch(node, path) {
  const url = `http://127.0.0.1:${node.chronikPort}${path}`;
  const res = await fetch(url, { signal: AbortSignal.timeout(5000) });
  const buf = Buffer.from(await res.arrayBuffer());
  return { status: res.status, buffer: buf, hex: buf.toString('hex') };
}

function decodeChronikBlockchainInfo(buf) {
  // Simple protobuf decoder for Chronik BlockchainInfo { bytes tip_hash = 1; int32 tip_height = 2; }
  let off = 0;
  let tipHashHex = '';
  let tipHeight = 0;
  while (off < buf.length) {
    const tag = buf[off++];
    const field = tag >> 3;
    const wire = tag & 7;
    if (wire === 2) {
      let len = 0, shift = 0;
      while (off < buf.length) {
        const b = buf[off++];
        len |= (b & 0x7f) << shift;
        if (!(b & 0x80)) break;
        shift += 7;
      }
      const slice = buf.subarray(off, off + len);
      off += len;
      if (field === 1 && slice.length === 32) {
        tipHashHex = Buffer.from(slice).reverse().toString('hex');
      }
    } else if (wire === 0) {
      let val = 0, shift = 0;
      while (off < buf.length) {
        const b = buf[off++];
        val |= (b & 0x7f) << shift;
        if (!(b & 0x80)) break;
        shift += 7;
      }
      if (field === 2) tipHeight = val;
    } else {
      break;
    }
  }
  return { tipHashHex, tipHeight };
}

// =============================================================================
// Compiler Loader (`tools/lotus-v2-compiler`)
// =============================================================================
let compilerMod = null;
async function getCompiler() {
  if (!compilerMod) {
    const genericUrl = pathToFileURL(join(COMPILER_DIST, 'generic.js')).href;
    const diagUrl = pathToFileURL(join(COMPILER_DIST, 'diagnostics.js')).href;
    const [generic, diagnostics] = await Promise.all([import(genericUrl), import(diagUrl)]);
    compilerMod = { ...generic, ...diagnostics };
  }
  return compilerMod;
}

const PRESET_CONTRACTS = {
  payment: {
    title: 'Payment (Schnorr checksig)',
    contract: 'Payment',
    source: existsSync(join(GALLERY_DIR, 'payment.lotus'))
      ? readFileSync(join(GALLERY_DIR, 'payment.lotus'), 'utf8')
      : `contract Payment<owner: PublicKey> {\n    function spend(signature: Signature) {\n        require(checksig(signature, owner));\n    }\n}\n`,
    bindings: { Payment: { owner: 'f9308a019258c31049344f85f89d5229b531c845836f99b08601f113bce036f9' } },
  },
  hashlock: {
    title: 'Hashlock (SHA-256 Preimage)',
    contract: 'Hashlock',
    source: existsSync(join(GALLERY_DIR, 'hashlock.lotus'))
      ? readFileSync(join(GALLERY_DIR, 'hashlock.lotus'), 'utf8')
      : `contract Hashlock<digest: Bytes32> {\n    function reveal(preimage: Bytes32) {\n        require(sha256(preimage) == digest);\n    }\n}\n`,
    bindings: {
      Hashlock: {
        digest: crypto.createHash('sha256').update(Buffer.alloc(32, 0x42)).digest('hex'),
      },
    },
  },
  fungible_token: {
    title: 'FungibleToken (Mint + Rules Trees)',
    contract: 'FungibleToken',
    source: existsSync(join(GALLERY_DIR, 'fungible-token.lotus'))
      ? readFileSync(join(GALLERY_DIR, 'fungible-token.lotus'), 'utf8')
      : '',
    bindings: {
      FungibleToken: {
        issuer: 'f9308a019258c31049344f85f89d5229b531c845836f99b08601f113bce036f9',
        maxMint: '1000000',
      },
    },
  },
  vault: {
    title: 'Vault (Timelock + Guardian Recovery)',
    contract: 'Vault',
    source: existsSync(join(GALLERY_DIR, 'vault.lotus'))
      ? readFileSync(join(GALLERY_DIR, 'vault.lotus'), 'utf8')
      : '',
    bindings: {
      Vault: {
        owner: 'f9308a019258c31049344f85f89d5229b531c845836f99b08601f113bce036f9',
        guardian: 'e493dbf1c10d80f3581e4904930b1404cc6c13900ee0758474fa94abe8c4cd13',
        unlockHeight: '100',
        maxSpend: '50000000',
      },
    },
  },
  counter: {
    title: 'Counter (Authenticated State Covenant)',
    contract: 'Counter',
    source: existsSync(join(GALLERY_DIR, 'counter.lotus'))
      ? readFileSync(join(GALLERY_DIR, 'counter.lotus'), 'utf8')
      : '',
    bindings: {
      Counter: {
        owner: 'f9308a019258c31049344f85f89d5229b531c845836f99b08601f113bce036f9',
        step: '1',
      },
    },
  },
  diagnostics_demo: {
    title: 'Diagnostics Demo (Clang-Style Error Caret)',
    contract: 'BrokenVault',
    source: `contract BrokenVault<owner: PublicKey> {\n    function spend(sig: Signature) {\n        require(checksig(sig, owenr));\n    }\n}\n`,
    bindings: {
      BrokenVault: {
        owner: 'f9308a019258c31049344f85f89d5229b531c845836f99b08601f113bce036f9',
      },
    },
  },
};

// =============================================================================
// Helper: Fund a V2 Output from Node 0's SQLite Wallet
// =============================================================================
async function fundV2OutputFromWallet(node, branchRootBuf, amountSats, utxoObj = null) {
  let utxo = utxoObj;
  if (!utxo) {
    const unspent = await rpcCall(node, 'listunspent', [0, 999999], node.wallet);
    unspent.sort((a, b) => (b.confirmations || 0) - (a.confirmations || 0));
    utxo = unspent.find((u) => Math.round(Number(u.amount) * 100) >= amountSats + 10000 && u.spendable);
    if (!utxo) {
      throw new Error('No mature spendable UTXO available in node0 wallet. Mine blocks first!');
    }
  }
  const txidLe = Buffer.from(utxo.txid, 'hex').reverse();
  const voutN = Number(utxo.vout);
  const inSats = Math.round(Number(utxo.amount) * 100);
  const feeSats = 2000;
  const changeSats = inSats - amountSats - feeSats;
  const changeAddr = await rpcCall(node, 'getnewaddress', [], node.wallet);
  const addrInfo = await rpcCall(node, 'getaddressinfo', [changeAddr], node.wallet);
  const changeSpk = Buffer.from(addrInfo.scriptPubKey, 'hex');
  const v2OutWire = serV2Output(amountSats, branchRootBuf);

  const verBuf = Buffer.alloc(4);
  verBuf.writeInt32LE(2, 0);
  const prevIdxBuf = Buffer.alloc(4);
  prevIdxBuf.writeUInt32LE(voutN, 0);
  const seqBuf = Buffer.alloc(4);
  seqBuf.writeUInt32LE(0xffffffff, 0);
  const val0Buf = Buffer.alloc(8);
  val0Buf.writeBigInt64LE(BigInt(amountSats), 0);
  const val1Buf = Buffer.alloc(8);
  val1Buf.writeBigInt64LE(BigInt(changeSats), 0);
  const lockBuf = Buffer.alloc(4, 0);

  const rawUnsigned = Buffer.concat([
    verBuf,
    compactSize(1),
    txidLe,
    prevIdxBuf,
    Buffer.from([0x00]),
    seqBuf,
    compactSize(2),
    val0Buf,
    serBytes(v2OutWire),
    val1Buf,
    serBytes(changeSpk),
    lockBuf,
  ]);

  const signed = await rpcCall(node, 'signrawtransactionwithwallet', [rawUnsigned.toString('hex')], node.wallet);
  if (!signed.complete) {
    throw new Error('Failed to sign V2 funding transaction with wallet');
  }
  const decoded = await rpcCall(node, 'decoderawtransaction', [signed.hex]);
  await rpcCall(node, 'sendrawtransaction', [signed.hex]);
  return {
    fundingTxid: decoded.txid,
    vout: 0,
    amountSats,
    changeVout: 1,
    changeSats,
    rawHex: signed.hex,
  };
}

// =============================================================================
// API Handlers for Workbench UI
// =============================================================================
async function handleOverview() {
  const primary = NODES[0];
  const [chainInfo, mempoolInfo, rawMempool, chaintips, gbt] = await Promise.all([
    rpcCall(primary, 'getblockchaininfo'),
    rpcCall(primary, 'getmempoolinfo'),
    rpcCall(primary, 'getrawmempool', [false, true]),
    rpcCall(primary, 'getchaintips').catch(() => []),
    rpcCall(primary, 'getblocktemplate', [{ mode: 'template' }]).catch(() => null),
  ]);

  // Query all 3 nodes in parallel for cluster + Chronik status
  const nodeStatuses = await Promise.all(
    NODES.map(async (n) => {
      try {
        const [binfo, mpool, peers, cInfo, wBal] = await Promise.all([
          rpcCall(n, 'getblockchaininfo'),
          rpcCall(n, 'getmempoolinfo'),
          rpcCall(n, 'getconnectioncount'),
          chronikFetch(n, '/blockchain-info').catch(() => null),
          rpcCall(n, 'getbalance', [], n.wallet).catch(() => null),
        ]);
        const chronikDecoded = cInfo && cInfo.status === 200 ? decodeChronikBlockchainInfo(cInfo.buffer) : null;
        return {
          idx: n.idx,
          name: n.name,
          ok: true,
          online: true,
          p2pPort: n.p2pPort,
          rpcPort: n.rpcPort,
          chronikPort: n.chronikPort,
          height: binfo.blocks,
          blocks: binfo.blocks,
          bestblockhash: binfo.bestblockhash,
          mempoolSize: mpool.size,
          mempoolBytes: mpool.bytes,
          peers,
          connections: peers,
          walletBalanceXpi: wBal,
          chronik: chronikDecoded
            ? {
                ok: true,
                online: true,
                mode: 'chronik-native',
                tipHeight: chronikDecoded.tipHeight,
                tipHash: chronikDecoded.tipHashHex,
                synced: chronikDecoded.tipHeight === binfo.blocks,
              }
            : {
                ok: true,
                online: false,
                mode: 'v2-explorer-adapter',
                tipHeight: binfo.blocks,
                tipHash: binfo.bestblockhash,
                synced: true,
              },
        };
      } catch (e) {
        return {
          idx: n.idx,
          name: n.name,
          ok: false,
          online: false,
          p2pPort: n.p2pPort,
          rpcPort: n.rpcPort,
          chronikPort: n.chronikPort,
          error: e.message,
        };
      }
    }),
  );

  // Fetch recent 12 blocks with 134-byte V2 headers
  const tipHeight = chainInfo.blocks;
  const startHeight = Math.max(0, tipHeight - 11);
  const heights = [];
  for (let h = tipHeight; h >= startHeight; h--) heights.push(h);

  const recentBlocks = await Promise.all(
    heights.map(async (h) => {
      const bhash = await rpcCall(primary, 'getblockhash', [h]);
      const [hdrJson, hdrHex] = await Promise.all([
        rpcCall(primary, 'getblockheader', [bhash, true]),
        rpcCall(primary, 'getblockheader', [bhash, false]),
      ]);
      const v2Hdr = decode134ByteHeader(hdrHex);
      return {
        height: h,
        hash: bhash,
        size: hdrJson.size,
        time: hdrJson.time,
        mediantime: hdrJson.mediantime,
        nTx: hdrJson.nTx,
        bits: hdrJson.bits,
        nonce: hdrJson.nonce,
        difficulty: hdrJson.difficulty,
        merkleroot: hdrJson.merkleroot,
        txRoot: hdrJson.merkleroot,
        stateroot: hdrJson.stateroot,
        stateRoot: hdrJson.stateroot,
        previousblockhash: hdrJson.previousblockhash || '00'.repeat(32),
        header_hex: hdrHex,
        v2_header: v2Hdr,
      };
    }),
  );

  const tipBlock = recentBlocks[0] || null;
  const coinbaseSplit = gbt
    ? {
        totalCoinbaseSats: gbt.coinbasevalue,
        minerFundSats: gbt.coinbasetxn?.minerfund?.minimumvalue
          ? Math.round(Number(gbt.coinbasetxn.minerfund.minimumvalue) * 100)
          : Math.floor(gbt.coinbasevalue * 0.25),
        stakingRewardSats: gbt.coinbasetxn?.stakingrewards?.minimumvalue
          ? Math.round(Number(gbt.coinbasetxn.stakingrewards.minimumvalue) * 100)
          : Math.floor(gbt.coinbasevalue * 0.25),
        minerNetSats:
          gbt.coinbasevalue -
          (gbt.coinbasetxn?.minerfund?.minimumvalue
            ? Math.round(Number(gbt.coinbasetxn.minerfund.minimumvalue) * 100)
            : 0) -
          (gbt.coinbasetxn?.stakingrewards?.minimumvalue
            ? Math.round(Number(gbt.coinbasetxn.stakingrewards.minimumvalue) * 100)
            : 0),
        treasuryAddresses: gbt.coinbasetxn?.minerfund?.addresses || [],
      }
    : null;

  const wInfo = await rpcCall(primary, 'getwalletinfo', [], primary.wallet).catch(() => ({
    balance: nodeStatuses[0]?.walletBalanceXpi || 0,
    immature_balance: 0,
  }));

  return {
    ok: true,
    timestamp: Date.now(),
    canonicalExplorerUrl: CANONICAL_EXPLORER_URL,
    wallet: wInfo,
    chronik: nodeStatuses[0]?.chronik || { ok: false },
    tipHeader: tipBlock
      ? {
          headerHex: tipBlock.header_hex,
          headerBytes: 134,
          headerFields: {
            hashMerkleRoot_TxRoot: tipBlock.merkleroot,
            hashStateRoot: tipBlock.stateroot,
          },
        }
      : null,
    chain: {
      chain: chainInfo.chain,
      network: chainInfo.chain,
      blocks: chainInfo.blocks,
      height: chainInfo.blocks,
      headers: chainInfo.headers,
      bestblockhash: chainInfo.bestblockhash,
      finalized_blockhash: chainInfo.finalized_blockhash,
      difficulty: chainInfo.difficulty,
      time: chainInfo.time,
      mediantime: chainInfo.mediantime,
      chainwork: chainInfo.chainwork,
      size_on_disk: chainInfo.size_on_disk,
      fast_sync_active: chainInfo.fast_sync_active,
      earliest_verified_height: chainInfo.earliest_verified_height,
      tip_tx_root: tipBlock?.merkleroot || '',
      tip_state_root: tipBlock?.stateroot || '',
      tip_header_hex: tipBlock?.header_hex || '',
    },
    template: gbt
      ? {
          templateid: gbt.templateid,
          height: gbt.height,
          subtreearoot: gbt.subtreearoot,
          merkleroot: gbt.merkleroot,
          stateroot: gbt.stateroot,
          bits: gbt.bits,
          target: gbt.target,
          curtime: gbt.curtime,
          mintime: gbt.mintime,
          txCount: (gbt.transactions || []).length,
          coinbaseSplit,
          coinbasetxn: {
            coinbasevalue: gbt.coinbasevalue,
            minerfund: coinbaseSplit.minerFundSats,
            stakingrewards: coinbaseSplit.stakingRewardSats,
          },
        }
      : null,
    mempool: {
      loaded: mempoolInfo.loaded,
      size: mempoolInfo.size,
      bytes: mempoolInfo.bytes,
      usage: mempoolInfo.usage,
      total_fee: mempoolInfo.total_fee,
      maxmempool: mempoolInfo.maxmempool,
      mempoolminfee: mempoolInfo.mempoolminfee,
      unbroadcastcount: mempoolInfo.unbroadcastcount,
      mempool_sequence: rawMempool.mempool_sequence,
      txids: (rawMempool.txids || []).slice(0, 50),
    },
    nodes: nodeStatuses,
    recentBlocks,
    chaintips,
    presets: Object.entries(PRESET_CONTRACTS).map(([id, p]) => ({
      id,
      title: p.title,
      contract: p.contract,
      source: p.source,
      bindings: p.bindings,
    })),
  };
}

async function handleBlockDetail(idOrHeight) {
  const primary = NODES[0];
  let bhash = idOrHeight;
  if (/^\d+$/.test(idOrHeight)) {
    bhash = await rpcCall(primary, 'getblockhash', [Number(idOrHeight)]);
  }
  const [block, hdrHex, gbt, chronikBlk, chronikTxs] = await Promise.all([
    rpcCall(primary, 'getblock', [bhash, 2]),
    rpcCall(primary, 'getblockheader', [bhash, false]),
    rpcCall(primary, 'getblocktemplate', [{ mode: 'template' }]).catch(() => null),
    chronikFetch(primary, `/block/${bhash}`).catch(() => null),
    chronikFetch(primary, `/block-txs/${bhash}`).catch(() => null),
  ]);

  const v2Header = decode134ByteHeader(hdrHex);
  const cbTx = block.tx?.[0] || null;
  let coinbaseBreakdown = null;
  if (cbTx) {
    const outputs = (cbTx.vout || []).map((o) => ({
      n: o.n,
      valueXpi: o.value,
      valueSats: Math.round(Number(o.value) * 100),
      type: o.scriptPubKey?.type || 'unknown',
      addresses: o.scriptPubKey?.addresses || [],
      hex: o.scriptPubKey?.hex || '',
    }));
    const totalSats = outputs.reduce((acc, o) => acc + o.valueSats, 0);
    coinbaseBreakdown = {
      txid: cbTx.txid,
      totalSats,
      totalXpi: (totalSats / 100).toFixed(2),
      outputs,
      policyNote:
        outputs.length >= 2
          ? 'Miner + Treasury/Staker split active'
          : 'Regtest single-output coinbase (50/25/25 split activates with MinerFund/Avalanche Staking Winner)',
      expectedSplitModel: {
        minerShare50PctSats: Math.floor(totalSats * 0.5),
        stakerShare25PctSats: Math.floor(totalSats * 0.25),
        treasuryShare25PctSats: totalSats - Math.floor(totalSats * 0.5) - Math.floor(totalSats * 0.25),
      },
    };
  }

  const decodedTxs = (block.tx || []).map((tx, idx) => {
    const v7 = tx.hex ? tryDecodeV7TxWire(tx.hex) : null;
    const v2Outputs = (tx.vout || [])
      .map((vo) => {
        const spkHex = vo.scriptPubKey?.hex || '';
        const decodedV2 = spkHex ? tryDecodeV2OutputWire(Buffer.from(spkHex, 'hex')) : null;
        return decodedV2 ? { vout: vo.n, ...decodedV2 } : null;
      })
      .filter(Boolean);
    return {
      index: idx,
      txid: tx.txid,
      hash: tx.hash,
      version: tx.version,
      size: tx.size,
      locktime: tx.locktime,
      fee: tx.fee,
      isCoinbase: idx === 0,
      isV7: Boolean(v7),
      vinCount: (tx.vin || []).length,
      voutCount: (tx.vout || []).length,
      v7Details: v7,
      v2Outputs,
      raw: tx,
    };
  });

  return {
    ok: true,
    block: {
      hash: block.hash,
      confirmations: block.confirmations,
      size: block.size,
      height: block.height,
      version: block.version,
      versionHex: block.versionHex,
      merkleroot: block.merkleroot,
      stateroot: block.stateroot,
      time: block.time,
      mediantime: block.mediantime,
      nonce: block.nonce,
      bits: block.bits,
      difficulty: block.difficulty,
      chainwork: block.chainwork,
      nTx: block.nTx,
      tx: decodedTxs,
      previousblockhash: block.previousblockhash || null,
      nextblockhash: block.nextblockhash || null,
    },
    header: {
      headerHex: hdrHex,
      headerBytes: 134,
      headerFields: {
        hashMerkleRoot_TxRoot: block.merkleroot,
        hashStateRoot: block.stateroot,
        ...v2Header,
      },
    },
    v2Header,
    coinbaseBreakdown,
    chronik: {
      indexed: chronikBlk?.status === 200,
      blockProtobufBytes: chronikBlk?.buffer?.length || 0,
      blockTxsProtobufBytes: chronikTxs?.buffer?.length || 0,
    },
    transactions: decodedTxs,
  };
}

async function handleTxDetail(txid) {
  const primary = NODES[0];
  const [rawTx, mempoolEntry, chronikTx] = await Promise.all([
    rpcCall(primary, 'getrawtransaction', [txid, true]),
    rpcCall(primary, 'getmempoolentry', [txid]).catch(() => null),
    chronikFetch(primary, `/tx/${txid}`).catch(() => null),
  ]);

  const v7 = rawTx.hex ? tryDecodeV7TxWire(rawTx.hex) : null;
  const decodedVout = (rawTx.vout || []).map((vo) => {
    const spkHex = vo.scriptPubKey?.hex || '';
    const v2Out = spkHex ? tryDecodeV2OutputWire(Buffer.from(spkHex, 'hex')) : null;
    return {
      ...vo,
      v2Output: v2Out,
    };
  });

  return {
    ok: true,
    tx: {
      ...rawTx,
      vout: decodedVout,
    },
    v7,
    inMempool: Boolean(mempoolEntry),
    mempoolEntry,
    chronik: {
      indexed: chronikTx?.status === 200,
      protobufBytes: chronikTx?.buffer?.length || 0,
      protobufHexPreview: chronikTx?.hex?.slice(0, 256) || '',
    },
  };
}

async function handleUtxoDetail(txid, vout) {
  const primary = NODES[0];
  const [txout, rawTx, chronikTx] = await Promise.all([
    rpcCall(primary, 'gettxout', [txid, Number(vout), true]),
    rpcCall(primary, 'getrawtransaction', [txid, true]).catch(() => null),
    chronikFetch(primary, `/tx/${txid}`).catch(() => null),
  ]);
  const spkHex = txout?.scriptPubKey?.hex || rawTx?.vout?.[Number(vout)]?.scriptPubKey?.hex || '';
  const v2Output = spkHex ? tryDecodeV2OutputWire(Buffer.from(spkHex, 'hex')) : null;

  return {
    ok: true,
    outpoint: `${txid}:${vout}`,
    unspent: Boolean(txout),
    txout,
    v2Output,
    chronikIndexed: chronikTx?.status === 200,
  };
}

async function handleCompile(body) {
  const { compileContract, formatDiagnostics } = await getCompiler();
  const source = String(body.source || '');
  const contract = String(body.contract || '');
  const bindings = body.bindings || {};
  const optimize = body.optimize !== false;

  try {
    const artifact = compileContract(source, {
      contract: contract || undefined,
      bindings,
      optimize,
    });
    const enriched = {
      ...artifact,
      contractName: artifact.contract || contract || 'Contract',
      profile: artifact.version || 'lotus-v2-cabi04',
      branches: (artifact.methods || []).map((m) => ({
        name: m.name,
        asm:
          typeof m.asm === 'string'
            ? m.asm.split(/\s+/).filter(Boolean)
            : Array.isArray(m.asm)
              ? m.asm
              : Array.isArray(m.opcodes)
                ? m.opcodes
                : [m.scriptHex],
        scriptHex: m.scriptHex,
        leafHash: m.leafHash || (m.scriptHex ? branchLeafHash(Buffer.from(m.scriptHex, 'hex')).toString('hex') : ''),
      })),
      commitments: {
        rootHex: artifact.policy?.root || '',
      },
    };
    return {
      ok: true,
      artifact: enriched,
    };
  } catch (err) {
    const formatted = err.diagnostics ? formatDiagnostics(err.diagnostics, err.sources, { color: false }) : err.message;
    return {
      ok: false,
      error: err.message,
      diagnostics: err.diagnostics || [],
      formattedDiagnostics: formatted,
    };
  }
}

async function handleSendTx(body) {
  const primary = NODES[0];
  const mode = body.mode || 'wallet_payment';

  if (mode === 'wallet_payment') {
    const toAddress = body.address || (await rpcCall(NODES[1], 'getnewaddress', [], NODES[1].wallet));
    const amountXpi = Number(body.amount || 25);
    const txid = await rpcCall(primary, 'sendtoaddress', [toAddress, amountXpi], primary.wallet);
    return {
      ok: true,
      mode,
      txid,
      recipient: toAddress,
      amountXpi,
      description: `Sent ${amountXpi} XPI via native SQLite wallet to ${toAddress}`,
    };
  }

  if (mode === 'v2_bigint_introspect' || mode === 'v2_bigint') {
    // Combined 12-byte Lotus V2 VM script exercising 64-byte BigInt ADD + XOR + Cross-Input Introspection
    const combinedScript = Buffer.from([0x9e, 0xa7, 0x90, 0x92, 0x00, 0xd6, 0x4e, 0xd6, 0x9e, 0x00, 0xe1, 0xac]);
    const combinedRoot = branchLeafHash(combinedScript);
    const op1Script = Buffer.from([0x4e]);
    const op1Root = branchLeafHash(op1Script);

    const unspent = await rpcCall(primary, 'listunspent', [0, 999999], primary.wallet);
    unspent.sort((a, b) => (b.confirmations || 0) - (a.confirmations || 0));
    const candidates = unspent.filter((u) => Math.round(Number(u.amount) * 100) >= 60_000_000 && u.spendable);
    if (candidates.length < 2) {
      throw new Error('Need at least 2 mature coinbase UTXOs in node0 wallet. Mine blocks first!');
    }
    const f1 = await fundV2OutputFromWallet(primary, combinedRoot, 20_000_000, candidates[0]);
    const f2 = await fundV2OutputFromWallet(primary, combinedRoot, 30_000_000, candidates[1]);

    const valA = (1n << 400n) + (1n << 200n) + 0x123456789abcdef0n;
    const valB = (1n << 180n) + 0x0fedcba987654321n;
    const valSum = valA + valB;

    const toLeBytes = (bigVal, byteLen) => {
      const b = Buffer.alloc(byteLen, 0);
      let tmp = bigVal;
      for (let i = 0; i < byteLen; i++) {
        b[i] = Number(tmp & 0xffn);
        tmp >>= 8n;
      }
      return b;
    };

    const bigintA64 = toLeBytes(valA, 64);
    const bigintB32 = toLeBytes(valB, 32);
    const bigintExpected64 = toLeBytes(valSum, 64);
    const bwA4 = Buffer.from('11223344', 'hex');
    const bwB8 = Buffer.from('ff00ff0055667788', 'hex');
    const bwExpected8 = Buffer.alloc(8);
    for (let i = 0; i < 8; i++) {
      bwExpected8[i] = (i < 4 ? bwA4[i] : 0) ^ bwB8[i];
    }

    const argsList = [bwExpected8, bwA4, bwB8, bigintExpected64, bigintA64, bigintB32];
    const txin0 = serV2SpendInput(Buffer.from(f1.fundingTxid, 'hex').reverse(), f1.vout, combinedScript, argsList);
    const txin1 = serV2SpendInput(Buffer.from(f2.fundingTxid, 'hex').reverse(), f2.vout, combinedScript, argsList);
    const outVal = f1.amountSats + f2.amountSats - 2000;
    const txout0 = serV2Output(outVal, op1Root);

    const v7Hex = buildV7TxHex([txin0, txin1], [txout0]);
    const decoded = await rpcCall(primary, 'decoderawtransaction', [v7Hex]);
    await rpcCall(primary, 'sendrawtransaction', [v7Hex]);

    return {
      ok: true,
      mode,
      fundTxid: f1.fundingTxid,
      fundingTxids: [f1.fundingTxid, f2.fundingTxid],
      spendTxid: decoded.txid,
      txid: decoded.txid,
      txhash: decoded.hash,
      wireHex: v7Hex,
      description: 'Funded 2 V2 outputs and spent them in a native V2 v7 512-bit BigInt + Bitwise + Cross-Input Introspection transaction',
    };
  }

  if (mode === 'v2_token_mint_transfer' || mode === 'v2_token_mint_and_transfer') {
    const op1Script = Buffer.from([0x4e]);
    const op1Root = branchLeafHash(op1Script);
    const mintScript = Buffer.from([0x9d]); // OP_0NOTEQUAL checks positive 16-byte signed token delta
    const tokenIdLe = branchLeafHash(mintScript);
    const tokenIdHex = tokenIdLe.toString('hex');

    const fund = await fundV2OutputFromWallet(primary, op1Root, 25_000_000);
    const mintAmount = 1_000_000;
    const xpiAfterMint = fund.amountSats - 2000;

    const mintIn0 = serV2SpendInput(Buffer.from(fund.fundingTxid, 'hex').reverse(), fund.vout, op1Script);
    const mintIn1 = serV2MintInput(tokenIdLe, mintScript);
    const mintOut0 = serV2Output(mintAmount, op1Root, 1, tokenIdLe);
    const mintOut1 = serV2Output(xpiAfterMint, op1Root, 0);
    const mintV7Hex = buildV7TxHex([mintIn0, mintIn1], [mintOut0, mintOut1]);
    const mintDecoded = await rpcCall(primary, 'decoderawtransaction', [mintV7Hex]);
    await rpcCall(primary, 'sendrawtransaction', [mintV7Hex]);

    // Immediately spend the unconfirmed minted token output in a V2 v7 Token Transfer splitting 1,000,000 -> 650,000 + 350,000
    const xferIn0 = serV2SpendInput(Buffer.from(mintDecoded.txid, 'hex').reverse(), 0, op1Script);
    const xferIn1 = serV2SpendInput(Buffer.from(mintDecoded.txid, 'hex').reverse(), 1, op1Script);
    const xferOut0 = serV2Output(650_000, op1Root, 1, tokenIdLe);
    const xferOut1 = serV2Output(350_000, op1Root, 1, tokenIdLe);
    const xferOut2 = serV2Output(xpiAfterMint - 2000, op1Root, 0);
    const xferV7Hex = buildV7TxHex([xferIn0, xferIn1], [xferOut0, xferOut1, xferOut2]);
    const xferDecoded = await rpcCall(primary, 'decoderawtransaction', [xferV7Hex]);
    await rpcCall(primary, 'sendrawtransaction', [xferV7Hex]);

    return {
      ok: true,
      mode,
      tokenId: tokenIdHex,
      tokenIdHex,
      mintedAmount: mintAmount,
      transferSplits: [650000, 350000],
      fundingTxid: fund.fundingTxid,
      mintTxid: mintDecoded.txid,
      transferTxid: xferDecoded.txid,
      txid: xferDecoded.txid,
      description: `Minted 1,000,000 native V2 tokens (TokenID ${tokenIdHex.slice(0, 16)}…) and transferred 650k + 350k in V2 v7 transactions`,
    };
  }

  if (mode === 'compiled_hashlock' || mode === 'v2_contract_hashlock') {
    const { compileContract } = await getCompiler();
    const preimage = Buffer.alloc(32, 0x42);
    const digest = crypto.createHash('sha256').update(preimage).digest('hex');
    const artifact = compileContract(PRESET_CONTRACTS.hashlock.source, {
      contract: 'Hashlock',
      bindings: { Hashlock: { digest } },
    });
    const method = artifact.methods[0];
    const scriptBuf = Buffer.from(method.scriptHex, 'hex');
    const rootBuf = Buffer.from(artifact.policy.root, 'hex');

    const op1Script = Buffer.from([0x4e]);
    const op1Root = branchLeafHash(op1Script);

    const fund = await fundV2OutputFromWallet(primary, rootBuf, 15_000_000);
    const spendIn = serV2SpendInput(
      Buffer.from(fund.fundingTxid, 'hex').reverse(),
      fund.vout,
      scriptBuf,
      [preimage],
    );
    const spendOut = serV2Output(fund.amountSats - 2000, op1Root);
    const spendHex = buildV7TxHex([spendIn], [spendOut]);
    const decoded = await rpcCall(primary, 'decoderawtransaction', [spendHex]);
    await rpcCall(primary, 'sendrawtransaction', [spendHex]);

    return {
      ok: true,
      mode,
      contract: 'Hashlock',
      contractName: 'Hashlock',
      branchRoot: artifact.policy.root,
      rootHex: artifact.policy.root,
      scriptHex: method.scriptHex,
      preimageAscii: '0x' + preimage.toString('hex'),
      fundTxid: fund.fundingTxid,
      fundingTxid: fund.fundingTxid,
      spendTxid: decoded.txid,
      txid: decoded.txid,
      description: `Compiled Hashlock.lotus (root ${artifact.policy.root.slice(0, 16)}…), funded UTXO, and unlocked via SHA-256 preimage in V2 v7 tx`,
    };
  }

  throw new Error(`Unknown send mode: ${mode}`);
}

async function handleBatchBurst(body) {
  const primary = NODES[0];
  const count = Math.min(25, Math.max(2, Number(body.count || 8)));
  const op1Script = Buffer.from([0x4e]);
  const op1Root = branchLeafHash(op1Script);

  // Fund a root UTXO first so we can build a package of chained V2 v7 transactions
  // and submit them atomically in a single `testrawtxbatch` + `submitrawtxbatch` call!
  const startAmount = 40_000_000;
  const fund = await fundV2OutputFromWallet(primary, op1Root, startAmount);

  const rawTxs = [];
  let prevTxidHex = fund.fundingTxid;
  let currentVal = startAmount;

  for (let i = 0; i < count; i++) {
    const nextVal = currentVal - 1500;
    const txin = serV2SpendInput(Buffer.from(prevTxidHex, 'hex').reverse(), 0, op1Script);
    const txout = serV2Output(nextVal, op1Root);
    const rawHex = buildV7TxHex([txin], [txout], 0n);
    const decoded = await rpcCall(primary, 'decoderawtransaction', [rawHex]);
    rawTxs.push(rawHex);
    prevTxidHex = decoded.txid;
    currentVal = nextVal;
  }

  const t0 = performance.now();
  const testResult = await rpcCall(primary, 'testrawtxbatch', [rawTxs]);
  const submitResult = await rpcCall(primary, 'submitrawtxbatch', [rawTxs]);
  const elapsedMs = performance.now() - t0;
  const effectiveTps = ((rawTxs.length / (elapsedMs / 1000)) || 0).toFixed(1);

  let minedBlocks = [];
  if (body.mine) {
    const mineRes = await handleMine({ count: 1 });
    minedBlocks = mineRes.blockHashes || [];
  }

  return {
    ok: true,
    count: rawTxs.length,
    fundingTxid: fund.fundingTxid,
    elapsedMs: Number(elapsedMs.toFixed(2)),
    effectiveBatchTps: Number(effectiveTps),
    testResult,
    submitResult,
    submitBatch: {
      accepted: submitResult?.accepted ?? rawTxs.length,
      rejected: submitResult?.rejected ?? 0,
    },
    minedBlocks,
  };
}

async function handleMine(body) {
  const primary = NODES[0];
  const blocks = Math.min(50, Math.max(1, Number(body.blocks || body.count || 1)));
  const addr = await rpcCall(primary, 'getnewaddress', [], primary.wallet);
  const t0 = performance.now();
  const blockHashes = await rpcCall(primary, 'generatetoaddress', [blocks, addr]);
  const elapsedMs = Number((performance.now() - t0).toFixed(2));
  const tipHash = blockHashes[blockHashes.length - 1];
  const hdrJson = await rpcCall(primary, 'getblockheader', [tipHash, true]);

  return {
    ok: true,
    minedBlocks: blocks,
    blocks: blockHashes,
    blockHashes,
    height: hdrJson.height,
    newHeight: hdrJson.height,
    tipHash,
    merkleroot: hdrJson.merkleroot,
    stateroot: hdrJson.stateroot,
    elapsedMs,
  };
}

// =============================================================================
// `/v2/explorer/v1/*` Schema-1 Live Adapter for `explorer/v2`
// =============================================================================
async function buildExplorerSnapshot(primary) {
  const [chainInfo, genesisHash] = await Promise.all([
    rpcCall(primary, 'getblockchaininfo'),
    rpcCall(primary, 'getblockhash', [0]),
  ]);
  const heightStr = String(chainInfo.blocks);
  const tipWire = reverseHex(chainInfo.bestblockhash);
  const genesisWire = reverseHex(genesisHash);
  const snapshot = {
    chain_id: CHAIN_ID_HEX,
    genesis: genesisWire,
    profile_id: PROFILE_ID_HEX,
    tip: tipWire,
    height: heightStr,
    service_epoch: SERVICE_EPOCH,
    generation: '1',
  };
  const coverage = {
    from_height: '0',
    through_height: heightStr,
    complete: true,
    scope: 'canonical_confirmed',
  };
  const snapshotToken = `snap-${heightStr}-${tipWire.slice(0, 16)}`;
  return { chainInfo, snapshot, coverage, snapshotToken };
}

function wrapEnvelope(ctx, data) {
  return {
    api_version: '1',
    snapshot_token: ctx.snapshotToken,
    snapshot: ctx.snapshot,
    coverage: ctx.coverage,
    data,
  };
}

async function buildExplorerTxOutputRecord(primary, tx, blockHashDisplay, blockHeight, txIndex, outIdx) {
  const blockIdWire = reverseHex(blockHashDisplay);
  const txidWire = reverseHex(tx.txid);
  const txhashWire = reverseHex(tx.hash);
  const v7 = tx.hex ? tryDecodeV7TxWire(tx.hex) : null;
  const vo = tx.vout?.[outIdx];
  const spkHex = vo?.scriptPubKey?.hex || '';
  const v2Out =
    v7?.outputs?.[outIdx] ||
    (spkHex ? tryDecodeV2OutputWire(Buffer.from(spkHex, 'hex')) : null) || {
      flags: '0',
      value: String(Math.max(0, Math.round(Number(vo?.value || 0) * 100))),
      has_token: false,
      token_id: '00'.repeat(32),
      is_burn: false,
      branches: [crypto.createHash('sha256').update(Buffer.from(spkHex, 'hex')).digest('hex')],
      paths: [['0']],
    };

  return {
    txid: txidWire,
    out_idx: String(outIdx),
    flags: v2Out.flags,
    value: v2Out.value,
    has_token: v2Out.has_token,
    token_id: v2Out.token_id,
    is_burn: v2Out.is_burn,
    branches: v2Out.branches,
    paths: v2Out.paths,
    creation: {
      block_id: blockIdWire,
      height: String(blockHeight),
      tx_index: String(txIndex),
      txid: txidWire,
      txhash: txhashWire,
    },
    spend: null,
  };
}

async function handleCanonicalExplorerV1(req, urlObj, bodyBuf) {
  const primary = NODES[0];
  // 1. Try forwarding to upstream Chronik first in case Patch 019 /v2/explorer/v1 is mounted
  try {
    const upstream = await fetch(`http://127.0.0.1:${primary.chronikPort}${urlObj.pathname}${urlObj.search}`, {
      method: req.method,
      headers: { 'Content-Type': 'application/json' },
      body: req.method === 'POST' ? bodyBuf : undefined,
      signal: AbortSignal.timeout(2000),
    });
    if (upstream.status !== 404) {
      return { status: upstream.status, json: await upstream.json() };
    }
  } catch {
    // Fall through to live RPC + Chronik synthesis
  }

  const ctx = await buildExplorerSnapshot(primary);
  const sub = urlObj.pathname.replace(/^\/v2\/explorer\/v1/, '');

  if (sub === '/status') {
    const anchor = { block_id: ctx.snapshot.tip, height: ctx.snapshot.height };
    return {
      status: 200,
      json: {
        api_version: '1',
        ready: true,
        reason: 'ready',
        indexed_anchor: anchor,
        authoritative_anchor: anchor,
        service_epoch: SERVICE_EPOCH,
        generation: '1',
        binding: {
          chain_id: CHAIN_ID_HEX,
          genesis: ctx.snapshot.genesis,
          profile_id: PROFILE_ID_HEX,
        },
        coverage: ctx.coverage,
        capabilities: {
          blocks: true,
          transactions: true,
          transaction_wire: true,
          outputs: true,
          assets: true,
          asset_events: true,
          branches: true,
          accepted_pool: false,
          detached_history: false,
          finality: false,
        },
        limits: {
          request_bytes: '32768',
          response_bytes: '262144',
          page_size: '100',
          cursor_bytes: '2048',
          wire_chunk_bytes: '32768',
          examined_records: '1024',
          key_reads: '4096',
        },
      },
    };
  }

  if (sub === '/blocks') {
    const tipH = ctx.chainInfo.blocks;
    const items = [];
    for (let h = tipH; h >= Math.max(0, tipH - 14); h--) {
      const bhash = await rpcCall(primary, 'getblockhash', [h]);
      const hdr = await rpcCall(primary, 'getblockheader', [bhash, true]);
      items.push({
        block_id: reverseHex(bhash),
        prev_id: hdr.previousblockhash ? reverseHex(hdr.previousblockhash) : '00'.repeat(32),
        height: String(hdr.height),
        time: String(hdr.time),
        size: String(hdr.size),
        tx_count: String(hdr.nTx),
        status: 'confirmed',
        confirmations: String(Math.max(1, hdr.confirmations)),
      });
    }
    return { status: 200, json: wrapEnvelope(ctx, { items, next_cursor: null, exhausted: true }) };
  }

  let match;
  if ((match = sub.match(/^\/blocks\/(?:(by-height)\/)?([^/]+)$/))) {
    const isByHeight = Boolean(match[1]);
    const param = match[2];
    let bhashDisplay;
    if (isByHeight) {
      bhashDisplay = await rpcCall(primary, 'getblockhash', [Number(param)]);
    } else {
      // Try both wire-order and display-order block hash
      try {
        await rpcCall(primary, 'getblockheader', [reverseHex(param), true]);
        bhashDisplay = reverseHex(param);
      } catch {
        bhashDisplay = param;
      }
    }
    const [hdr, hdrHex] = await Promise.all([
      rpcCall(primary, 'getblockheader', [bhashDisplay, true]),
      rpcCall(primary, 'getblockheader', [bhashDisplay, false]),
    ]);
    const v2Hdr = decode134ByteHeader(hdrHex);
    const blockIdReply = isByHeight ? reverseHex(bhashDisplay) : param;
    const prevWire = hdr.previousblockhash ? reverseHex(hdr.previousblockhash) : '00'.repeat(32);
    return {
      status: 200,
      json: wrapEnvelope(ctx, {
        block_id: blockIdReply,
        prev_id: prevWire,
        height: String(hdr.height),
        time: String(hdr.time),
        size: String(hdr.size),
        tx_count: String(hdr.nTx),
        status: 'confirmed',
        confirmations: String(Math.max(1, hdr.confirmations)),
        header_wire: hdrHex,
        header: {
          prev_id: prevWire,
          bits: v2Hdr.bits_u32,
          time: String(hdr.time),
          nonce: String(hdr.nonce),
          version: String(hdr.version),
          size: String(hdr.size),
          height: String(hdr.height),
          tx_root: v2Hdr.tx_root_wire,
          state_root: v2Hdr.state_root_wire,
        },
        body_availability: 'complete',
        finality: 'unknown',
      }),
    };
  }

  if ((match = sub.match(/^\/blocks\/([^/]+)\/transactions$/))) {
    const param = match[1];
    let bhashDisplay;
    try {
      await rpcCall(primary, 'getblockheader', [reverseHex(param), true]);
      bhashDisplay = reverseHex(param);
    } catch {
      bhashDisplay = param;
    }
    const blk = await rpcCall(primary, 'getblock', [bhashDisplay, 2]);
    const items = (blk.tx || []).map((tx, idx) => ({
      txid: reverseHex(tx.txid),
      txhash: reverseHex(tx.hash),
      location: {
        block_id: param,
        height: String(blk.height),
        tx_index: String(idx),
      },
      status: 'confirmed',
      confirmations: String(Math.max(1, blk.confirmations)),
      input_count: String((tx.vin || []).length),
      output_count: String((tx.vout || []).length),
      wire_size: String(tx.size),
    }));
    return { status: 200, json: wrapEnvelope(ctx, { items, next_cursor: null, exhausted: true }) };
  }

  if ((match = sub.match(/^\/transactions\/by-(id|hash)\/([^/]+)$/))) {
    const kind = match[1];
    const param = match[2];
    let txDisplay = reverseHex(param);
    let rawTx;
    try {
      rawTx = await rpcCall(primary, 'getrawtransaction', [txDisplay, true]);
    } catch {
      txDisplay = param;
      rawTx = await rpcCall(primary, 'getrawtransaction', [txDisplay, true]);
    }
    const blk = await rpcCall(primary, 'getblock', [rawTx.blockhash, 1]);
    const txIdx = Math.max(0, (blk.tx || []).indexOf(rawTx.txid));
    const v7 = rawTx.hex ? tryDecodeV7TxWire(rawTx.hex) : null;
    return {
      status: 200,
      json: wrapEnvelope(ctx, {
        txid: kind === 'id' ? param : reverseHex(rawTx.txid),
        txhash: kind === 'hash' ? param : reverseHex(rawTx.hash),
        location: {
          block_id: reverseHex(rawTx.blockhash),
          height: String(blk.height),
          tx_index: String(txIdx),
        },
        status: 'confirmed',
        confirmations: String(Math.max(1, rawTx.confirmations || 1)),
        input_count: String((rawTx.vin || []).length),
        output_count: String((rawTx.vout || []).length),
        wire_size: String(rawTx.size),
        lock: v7 ? v7.lock : String(rawTx.locktime || 0),
        core_available: true,
        witness_available: true,
        wire_available: true,
        finality: 'unknown',
        accounting: { availability: 'unknown' },
      }),
    };
  }

  if ((match = sub.match(/^\/transactions\/by-id\/([^/]+)\/(inputs|outputs|witnesses|wire)$/))) {
    const param = match[1];
    const sectionName = match[2];
    let txDisplay = reverseHex(param);
    let rawTx;
    try {
      rawTx = await rpcCall(primary, 'getrawtransaction', [txDisplay, true]);
    } catch {
      txDisplay = param;
      rawTx = await rpcCall(primary, 'getrawtransaction', [txDisplay, true]);
    }
    const blk = await rpcCall(primary, 'getblock', [rawTx.blockhash, 1]);
    const txIdx = Math.max(0, (blk.tx || []).indexOf(rawTx.txid));
    const v7 = rawTx.hex ? tryDecodeV7TxWire(rawTx.hex) : null;

    if (sectionName === 'wire') {
      const hexBytes = rawTx.hex || '';
      const totalBytes = hexBytes.length / 2;
      const offset = Number(urlObj.searchParams.get('offset') || '0');
      const reqLen = Number(urlObj.searchParams.get('length') || '32768');
      const sliceHex = hexBytes.slice(offset * 2, (offset + reqLen) * 2);
      const nextOffset = offset + sliceHex.length / 2 < totalBytes ? String(offset + sliceHex.length / 2) : null;
      return {
        status: 200,
        json: wrapEnvelope(ctx, {
          txid: param,
          txhash: reverseHex(rawTx.hash),
          total_bytes: String(totalBytes),
          offset: String(offset),
          bytes_hex: sliceHex,
          next_offset: nextOffset,
        }),
      };
    }

    if (sectionName === 'outputs') {
      const items = [];
      for (let i = 0; i < (rawTx.vout || []).length; i++) {
        const rec = await buildExplorerTxOutputRecord(primary, rawTx, rawTx.blockhash, blk.height, txIdx, i);
        rec.txid = param;
        rec.creation.txid = param;
        items.push(rec);
      }
      return { status: 200, json: wrapEnvelope(ctx, { items, next_cursor: null, exhausted: true }) };
    }

    if (sectionName === 'inputs') {
      if (v7) {
        const items = await Promise.all(
          v7.inputs.map(async (inp) => {
            if (inp.kind === 'spend') {
              const prevTx = await rpcCall(primary, 'getrawtransaction', [inp.prev_txid_display, true]);
              const prevBlk = await rpcCall(primary, 'getblock', [prevTx.blockhash, 1]);
              const prevTxIdx = Math.max(0, (prevBlk.tx || []).indexOf(prevTx.txid));
              const resolvedRec = await buildExplorerTxOutputRecord(
                primary,
                prevTx,
                prevTx.blockhash,
                prevBlk.height,
                prevTxIdx,
                Number(inp.prev_index),
              );
              delete resolvedRec.spend;
              resolvedRec.txid = inp.prev_txid_wire;
              resolvedRec.creation.txid = inp.prev_txid_wire;
              return {
                input_index: inp.input_index,
                flags: inp.flags,
                kind: 'spend',
                prev_txid: inp.prev_txid_wire,
                prev_index: inp.prev_index,
                sequence: inp.sequence,
                path_index: inp.path_index,
                witness_count: inp.witness_count,
                coinbase_data: { present: false, wire_ref: null },
                resolved_coin: { availability: 'complete', output: resolvedRec },
              };
            }
            return {
              input_index: inp.input_index,
              flags: inp.flags,
              kind: inp.kind,
              prev_txid: inp.prev_txid_wire,
              prev_index: inp.prev_index,
              sequence: inp.sequence,
              path_index: null,
              witness_count: inp.witness_count,
              coinbase_data: {
                present: inp.coinbase_data.present,
                wire_ref: inp.coinbase_data.wire_ref,
              },
              resolved_coin: { availability: 'not_applicable' },
            };
          }),
        );
        return { status: 200, json: wrapEnvelope(ctx, { items, next_cursor: null, exhausted: true }) };
      }
      // Standard/Coinbase tx fallback
      const items = await Promise.all(
        (rawTx.vin || []).map(async (vin, idx) => {
          if (vin.coinbase) {
            return {
              input_index: String(idx),
              flags: '2',
              kind: 'coinbase',
              prev_txid: '00'.repeat(32),
              prev_index: String(blk.height),
              sequence: String(vin.sequence || 0xffffffff),
              path_index: null,
              witness_count: '0',
              coinbase_data: { present: true, wire_ref: { offset: '0', length: String(vin.coinbase.length / 2) } },
              resolved_coin: { availability: 'not_applicable' },
            };
          }
          const prevTx = await rpcCall(primary, 'getrawtransaction', [vin.txid, true]);
          const prevBlk = await rpcCall(primary, 'getblock', [prevTx.blockhash, 1]);
          const prevTxIdx = Math.max(0, (prevBlk.tx || []).indexOf(prevTx.txid));
          const resolvedRec = await buildExplorerTxOutputRecord(
            primary,
            prevTx,
            prevTx.blockhash,
            prevBlk.height,
            prevTxIdx,
            Number(vin.vout),
          );
          delete resolvedRec.spend;
          return {
            input_index: String(idx),
            flags: '1',
            kind: 'spend',
            prev_txid: resolvedRec.txid,
            prev_index: String(vin.vout),
            sequence: String(vin.sequence || 0xffffffff),
            path_index: '0',
            witness_count: '1',
            coinbase_data: { present: false, wire_ref: null },
            resolved_coin: { availability: 'complete', output: resolvedRec },
          };
        }),
      );
      return { status: 200, json: wrapEnvelope(ctx, { items, next_cursor: null, exhausted: true }) };
    }

    if (sectionName === 'witnesses') {
      const inIdx = Number(urlObj.searchParams.get('input_index') || '0');
      const wList = v7?.inputs?.[inIdx]?.witnesses || [
        {
          witness_index: '0',
          script: { offset: '0', length: '1' },
          siblings: { count: '0', table_ref: { offset: '1', length: '1' }, inline: [] },
          arguments: { count: '0', table_ref: { offset: '1', length: '1' }, inline: [] },
        },
      ];
      const items = wList.map((w) => ({
        witness_index: w.witness_index,
        script: w.script,
        siblings: w.siblings,
        arguments: {
          count: w.arguments.count,
          table_ref: w.arguments.table_ref,
          inline: w.arguments.inline,
        },
      }));
      return { status: 200, json: wrapEnvelope(ctx, { items, next_cursor: null, exhausted: true }) };
    }
  }

  if ((match = sub.match(/^\/outputs\/([^/]+)\/(\d+)$/))) {
    const param = match[1];
    const outIdx = Number(match[2]);
    let txDisplay = reverseHex(param);
    let rawTx;
    try {
      rawTx = await rpcCall(primary, 'getrawtransaction', [txDisplay, true]);
    } catch {
      txDisplay = param;
      rawTx = await rpcCall(primary, 'getrawtransaction', [txDisplay, true]);
    }
    const blk = await rpcCall(primary, 'getblock', [rawTx.blockhash, 1]);
    const txIdx = Math.max(0, (blk.tx || []).indexOf(rawTx.txid));
    const rec = await buildExplorerTxOutputRecord(primary, rawTx, rawTx.blockhash, blk.height, txIdx, outIdx);
    rec.txid = param;
    rec.creation.txid = param;
    return { status: 200, json: wrapEnvelope(ctx, rec) };
  }

  if (sub === '/assets') {
    return { status: 200, json: wrapEnvelope(ctx, { items: [], next_cursor: null, exhausted: true }) };
  }

  if (sub === '/branches/outputs' || sub === '/branches/utxos') {
    return {
      status: 200,
      json: wrapEnvelope(ctx, { items: [], next_cursor: null, exhausted: true, posting_reads: '1', work: '1' }),
    };
  }

  return {
    status: 404,
    json: {
      api_version: '1',
      error: { code: 'not_in_covered_chain', meaning: 'Absent from covered canonical history at this observation' },
      snapshot: ctx.snapshot,
      coverage: ctx.coverage,
    },
  };
}

// =============================================================================
// HTTP Server
// =============================================================================
async function readRequestBody(req) {
  const chunks = [];
  let total = 0;
  for await (const chunk of req) {
    total += chunk.length;
    if (total > 262144) throw new Error('Request body too large');
    chunks.push(chunk);
  }
  return Buffer.concat(chunks);
}

function sendJson(res, status, obj) {
  const payload = JSON.stringify(obj);
  res.writeHead(status, {
    'Content-Type': 'application/json; charset=utf-8',
    'Cache-Control': 'no-store',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
  });
  res.end(payload);
}

const server = http.createServer(async (req, res) => {
  if (req.method === 'OPTIONS') {
    res.writeHead(204, {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    });
    res.end();
    return;
  }

  try {
    const urlObj = new URL(req.url, `http://${req.headers.host || '127.0.0.1'}`);
    const pathname = urlObj.pathname;

    // Serve Workbench UI
    if (req.method === 'GET' && (pathname === '/' || pathname === '/index.html' || pathname === '/workbench')) {
      const html = await readFile(join(__dirname, 'workbench.html'), 'utf8');
      res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-store' });
      res.end(html);
      return;
    }

    // Serve `/v2/explorer/v1/*` routes for canonical explorer/v2 compatibility
    if (pathname.startsWith('/v2/explorer/v1/')) {
      const bodyBuf = req.method === 'POST' ? await readRequestBody(req) : Buffer.alloc(0);
      const { status, json } = await handleCanonicalExplorerV1(req, urlObj, bodyBuf);
      sendJson(res, status, json);
      return;
    }

    // Workbench API routes
    if (req.method === 'GET' && pathname === '/api/overview') {
      sendJson(res, 200, await handleOverview());
      return;
    }

    let match;
    if (req.method === 'GET' && (match = pathname.match(/^\/api\/block\/([^/]+)$/))) {
      sendJson(res, 200, await handleBlockDetail(decodeURIComponent(match[1])));
      return;
    }

    if (req.method === 'GET' && (match = pathname.match(/^\/api\/tx\/([^/]+)$/))) {
      sendJson(res, 200, await handleTxDetail(decodeURIComponent(match[1])));
      return;
    }

    if (req.method === 'GET' && (match = pathname.match(/^\/api\/utxo\/([^/]+)\/(\d+)$/))) {
      sendJson(res, 200, await handleUtxoDetail(decodeURIComponent(match[1]), match[2]));
      return;
    }

    if (req.method === 'POST' && pathname === '/api/compile') {
      const body = JSON.parse((await readRequestBody(req)).toString('utf8') || '{}');
      sendJson(res, 200, await handleCompile(body));
      return;
    }

    if (req.method === 'POST' && pathname === '/api/send-tx') {
      const body = JSON.parse((await readRequestBody(req)).toString('utf8') || '{}');
      sendJson(res, 200, await handleSendTx(body));
      return;
    }

    if (req.method === 'POST' && pathname === '/api/burst') {
      const body = JSON.parse((await readRequestBody(req)).toString('utf8') || '{}');
      sendJson(res, 200, await handleBatchBurst(body));
      return;
    }

    if (req.method === 'POST' && pathname === '/api/mine') {
      const body = JSON.parse((await readRequestBody(req)).toString('utf8') || '{}');
      sendJson(res, 200, await handleMine(body));
      return;
    }

    sendJson(res, 404, { error: `Unknown route: ${pathname}` });
  } catch (err) {
    sendJson(res, 500, { ok: false, error: err.message || String(err) });
  }
});

server.listen(PORT, BIND_HOST, () => {
  const addr = server.address();
  console.log(`Lotus V2 Testnet Explorer & Workbench listening at http://${addr.address}:${addr.port}/`);
});
