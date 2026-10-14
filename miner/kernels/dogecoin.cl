// Copyright (c) 2026 The Lotus developers. MIT license.
// Straightforward correctness-first Scrypt(1024,1,1), one nonce per work item.
// SHA-256 and Salsa20/8 follow their published algorithm definitions.
constant uint K[64] = {
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1,
    0x923f82a4, 0xab1c5ed5, 0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
    0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174, 0xe49b69c1, 0xefbe4786,
    0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147,
    0x06ca6351, 0x14292967, 0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
    0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85, 0xa2bfe8a1, 0xa81a664b,
    0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a,
    0x5b9cca4f, 0x682e6ff3, 0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
    0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2};
uint rr(uint x, uint n) { return rotate(x, 32 - n); }
void sha(const uchar *m, uint n, uchar *out) {
  uint h[8] = {0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
               0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19};
  uint blocks = (n + 72) / 64;
  for (uint block = 0; block < blocks; block++) {
    uint w[64];
    for (uint i = 0; i < 16; i++) {
      uint v = 0;
      for (uint j = 0; j < 4; j++) {
        uint pos = block * 64 + i * 4 + j;
        uchar b = pos < n ? m[pos] : (pos == n ? 128 : 0);
        if (pos >= blocks * 64 - 4)
          b = (uchar)((n * 8) >> ((blocks * 64 - 1 - pos) * 8));
        v = (v << 8) | b;
      }
      w[i] = v;
    }
    for (uint i = 16; i < 64; i++)
      w[i] = w[i - 16] +
             (rr(w[i - 15], 7) ^ rr(w[i - 15], 18) ^ (w[i - 15] >> 3)) +
             w[i - 7] +
             (rr(w[i - 2], 17) ^ rr(w[i - 2], 19) ^ (w[i - 2] >> 10));
    uint a = h[0], b = h[1], c = h[2], d = h[3], e = h[4], f = h[5], g = h[6],
         z = h[7];
    for (uint i = 0; i < 64; i++) {
      uint t = z + (rr(e, 6) ^ rr(e, 11) ^ rr(e, 25)) + ((e & f) ^ ((~e) & g)) +
               K[i] + w[i];
      uint u =
          (rr(a, 2) ^ rr(a, 13) ^ rr(a, 22)) + ((a & b) ^ (a & c) ^ (b & c));
      z = g;
      g = f;
      f = e;
      e = d + t;
      d = c;
      c = b;
      b = a;
      a = t + u;
    }
    h[0] += a;
    h[1] += b;
    h[2] += c;
    h[3] += d;
    h[4] += e;
    h[5] += f;
    h[6] += g;
    h[7] += z;
  }
  for (uint i = 0; i < 32; i++)
    out[i] = (uchar)(h[i / 4] >> (24 - 8 * (i % 4)));
}
void mac(const uchar *key, const uchar *msg, uint n, uchar *out) {
  uchar b[196], tmp[32];
  for (uint i = 0; i < 64; i++)
    b[i] = (i < 32 ? key[i] : 0) ^ 0x36;
  for (uint i = 0; i < n; i++)
    b[64 + i] = msg[i];
  sha(b, 64 + n, tmp);
  for (uint i = 0; i < 64; i++)
    b[i] = (i < 32 ? key[i] : 0) ^ 0x5c;
  for (uint i = 0; i < 32; i++)
    b[64 + i] = tmp[i];
  sha(b, 96, out);
}
#define QR(a, b, c, d)                                                         \
  x[b] ^= rotate(x[a] + x[d], 7u);                                             \
  x[c] ^= rotate(x[b] + x[a], 9u);                                             \
  x[d] ^= rotate(x[c] + x[b], 13u);                                            \
  x[a] ^= rotate(x[d] + x[c], 18u);
void salsa(uint *v) {
  uint x[16];
  for (uint i = 0; i < 16; i++)
    x[i] = v[i];
  for (uint i = 0; i < 4; i++) {
    QR(0, 4, 8, 12);
    QR(5, 9, 13, 1);
    QR(10, 14, 2, 6);
    QR(15, 3, 7, 11);
    QR(0, 1, 2, 3);
    QR(5, 6, 7, 4);
    QR(10, 11, 8, 9);
    QR(15, 12, 13, 14);
  }
  for (uint i = 0; i < 16; i++)
    v[i] += x[i];
}
void mix(uint *x) {
  uint t[16];
  for (uint i = 0; i < 16; i++)
    t[i] = x[16 + i] ^ x[i];
  salsa(t);
  for (uint i = 0; i < 16; i++) {
    x[i] = t[i];
    t[i] ^= x[16 + i];
  }
  salsa(t);
  for (uint i = 0; i < 16; i++)
    x[16 + i] = t[i];
}
kernel void scrypt_hash(global const uchar *header, uint offset,
                        global uint *scratch, global uchar *hashes) {
  uint id = get_global_id(0);
  global uint *v = scratch + id * 32768;
  uchar msg[132], key[32], digest[32];
  uint x[32];
  for (uint i = 0; i < 80; i++)
    msg[i] = header[i];
  uint nonce = offset + id;
  for (uint i = 0; i < 4; i++)
    msg[76 + i] = (uchar)(nonce >> (8 * i));
  sha(msg, 80, key);
  msg[80] = msg[81] = msg[82] = 0;
  for (uint j = 0; j < 4; j++) {
    msg[83] = (uchar)(j + 1);
    mac(key, msg, 84, digest);
    for (uint i = 0; i < 8; i++)
      x[j * 8 + i] = (uint)digest[4 * i] | ((uint)digest[4 * i + 1] << 8) |
                     ((uint)digest[4 * i + 2] << 16) |
                     ((uint)digest[4 * i + 3] << 24);
  }
  for (uint j = 0; j < 1024; j++) {
    for (uint i = 0; i < 32; i++)
      v[j * 32 + i] = x[i];
    mix(x);
  }
  for (uint j = 0; j < 1024; j++) {
    uint k = (x[16] & 1023) * 32;
    for (uint i = 0; i < 32; i++)
      x[i] ^= v[k + i];
    mix(x);
  }
  for (uint i = 0; i < 128; i++)
    msg[i] = (uchar)(x[i / 4] >> (8 * (i % 4)));
  msg[128] = msg[129] = msg[130] = 0;
  msg[131] = 1;
  mac(key, msg, 132, digest);
  for (uint i = 0; i < 32; i++)
    hashes[id * 32 + i] = digest[i];
}
