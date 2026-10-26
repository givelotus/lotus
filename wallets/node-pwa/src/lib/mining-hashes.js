// CPU reference implementations for mining verification, not a fast mining loop.
// Digest bytes retain node uint256 memory order; display hashes reverse these bytes.
const IV = Uint32Array.of(0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19);
const K = Uint32Array.of(0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2);
const rotr = (x,n) => (x >>> n) | (x << (32-n));
function bytes(value, length) {
  if (!(value instanceof Uint8Array) || (length !== undefined && value.length !== length)) throw new TypeError(`Expected Uint8Array${length === undefined ? '' : `(${length})`}`);
  return value;
}
// One SHA256 compression without padding. State and message words use SHA's
// big-endian convention; callers retain their input state unchanged.
export function sha256Compress(state, block) {
  if (!(state instanceof Uint32Array) || state.length !== 8) throw new TypeError('Expected eight SHA256 state words');
  bytes(block, 64);
  const view = new DataView(block.buffer, block.byteOffset, block.byteLength);
  const h = state.slice(), w = new Uint32Array(64);
  for (let i = 0; i < 16; i++) w[i] = view.getUint32(4*i);
  for (let i = 16; i < 64; i++) {
    const x = w[i-15], y = w[i-2];
    w[i] = w[i-16] + (rotr(x,7)^rotr(x,18)^(x>>>3)) + w[i-7] + (rotr(y,17)^rotr(y,19)^(y>>>10));
  }
  let [a,b,c,d,e,f,g,z] = h;
  for (let i = 0; i < 64; i++) {
    const t = (z + (rotr(e,6)^rotr(e,11)^rotr(e,25)) + ((e&f)^(~e&g)) + K[i] + w[i]) >>> 0;
    const u = ((rotr(a,2)^rotr(a,13)^rotr(a,22)) + ((a&b)^(a&c)^(b&c))) >>> 0;
    z=g; g=f; f=e; e=(d+t)>>>0; d=c; c=b; b=a; a=(t+u)>>>0;
  }
  [a,b,c,d,e,f,g,z].forEach((v,i) => { h[i] += v; });
  return h;
}
export function sha256(input) {
  bytes(input);
  const data = new Uint8Array(Math.ceil((input.length + 9) / 64) * 64);
  data.set(input); data[input.length] = 128;
  const view = new DataView(data.buffer);
  view.setBigUint64(data.length - 8, BigInt(input.length) * 8n);
  let h = IV.slice();
  for (let pos = 0; pos < data.length; pos += 64) h = sha256Compress(h, data.subarray(pos, pos + 64));
  const result = new Uint8Array(32), out = new DataView(result.buffer);
  h.forEach((v,i) => out.setUint32(i*4,v));
  return result;
}

// Cache only the first unpadded 64 bytes of an eCash 80-byte header. Nonce,
// timestamp, bits and the final four Merkle bytes belong to the second block.
// Snapshot the prefix and return a copy so caller mutation cannot poison it.
export function createSha256dMidstateCache() {
  let prefix, midstate;
  return (header) => {
    bytes(header, 80);
    if (!prefix || prefix.some((byte, i) => byte !== header[i])) {
      prefix = header.slice(0, 64);
      midstate = sha256Compress(IV, prefix);
    }
    return midstate.slice();
  };
}
export function sha256d(header) { return sha256(sha256(bytes(header,80))); }

// Only a single BLAKE3 chunk is needed for the header domains (<=137 bytes).
// Deliberately reject larger inputs rather than silently omit tree reduction.
export function blake3SingleChunk(input) {
  bytes(input);
  if (input.length > 1024) throw new RangeError('BLAKE3 reference supports at most 1024 bytes');
  let cv = IV.slice();
  const blocks = Math.max(1,Math.ceil(input.length/64));
  for (let block = 0; block < blocks; block++) {
    const size = Math.min(64,input.length-block*64), m = new Uint32Array(16);
    for (let j=0;j<size;j++) m[j>>>2] |= input[block*64+j] << ((j&3)*8);
    const last = block === blocks-1;
    const v = Uint32Array.from([...cv,...IV.slice(0,4),0,0,size,(block===0?1:0)|(last?10:0)]);
    const g = (a,b,c,d,x,y) => {
      v[a] += v[b]+x; v[d]=rotr(v[d]^v[a],16); v[c]+=v[d]; v[b]=rotr(v[b]^v[c],12);
      v[a] += v[b]+y; v[d]=rotr(v[d]^v[a],8); v[c]+=v[d]; v[b]=rotr(v[b]^v[c],7);
    };
    let schedule = m;
    for(let r=0;r<7;r++) {
      g(0,4,8,12,schedule[0],schedule[1]); g(1,5,9,13,schedule[2],schedule[3]);
      g(2,6,10,14,schedule[4],schedule[5]); g(3,7,11,15,schedule[6],schedule[7]);
      g(0,5,10,15,schedule[8],schedule[9]); g(1,6,11,12,schedule[10],schedule[11]);
      g(2,7,8,13,schedule[12],schedule[13]); g(3,4,9,14,schedule[14],schedule[15]);
      schedule = Uint32Array.from([2,6,3,10,7,0,4,13,1,11,12,5,9,14,15,8],i=>schedule[i]);
    }
    cv = Uint32Array.from({length:8},(_,i)=>v[i]^v[i+8]);
  }
  const out = new Uint8Array(32), view = new DataView(out.buffer);
  cv.forEach((v,i)=>view.setUint32(i*4,v,true)); return out;
}
export function taggedBlake3(tag, payload) {
  bytes(payload);
  const prefix = new TextEncoder().encode(tag), input = new Uint8Array(prefix.length+1+payload.length);
  input.set(prefix); input.set(payload,prefix.length+1); return blake3SingleChunk(input);
}
export function v2HeaderHashes(header, chainId) {
  bytes(header,134); bytes(chainId,32);
  const body = new Uint8Array(116); body.set(chainId); body.set(header.subarray(50),32);
  const bodyHash = taggedBlake3('Lotus/v2/header/body',body);
  const work = new Uint8Array(50); work.set(header.subarray(32,50)); work.set(bodyHash,18);
  const workHash = taggedBlake3('Lotus/v2/header/work',work);
  const id = new Uint8Array(64); id.set(header.subarray(0,32)); id.set(workHash,32);
  return { bodyHash, workHash, blockHash: taggedBlake3('Lotus/v2/blockid',id) };
}
export function v2BlockHash(header,chainId) { return v2HeaderHashes(header,chainId).blockHash; }
export function setHeaderNonce(header, nonce) {
  bytes(header);
  if (header.length !== 80 && header.length !== 134) throw new RangeError('Expected 80-byte or 134-byte header');
  if (typeof nonce !== 'bigint' || nonce < 0n || nonce >= (1n << (header.length===80?32n:64n))) throw new RangeError('Nonce outside header range');
  const result = header.slice(), view = new DataView(result.buffer);
  if (header.length===80) view.setUint32(76,Number(nonce),true); else view.setBigUint64(42,nonce,true);
  return result;
}
export function meetsTarget(hash,target) {
  bytes(hash,32); bytes(target,32);
  for(let i=31;i>=0;i--) { if(hash[i]<target[i]) return true; if(hash[i]>target[i]) return false; }
  return true;
}
export function hexToBytes(hex) {
  if (typeof hex !== 'string' || hex.length % 2 || !/^[0-9a-f]*$/i.test(hex)) throw new TypeError('Expected even-length hexadecimal string');
  return Uint8Array.from(hex.match(/../g) || [], part => Number.parseInt(part,16));
}
export function bytesToHex(value) { return Array.from(bytes(value),b=>b.toString(16).padStart(2,'0')).join(''); }
