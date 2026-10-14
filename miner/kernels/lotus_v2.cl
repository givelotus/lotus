// P04 candidate: tagged BLAKE3 work and BlockID layers for one nonce per lane.
// BodyHash is computed once on the CPU from the fixed body and ChainID.
__constant uint B3_IV[8] = {
    0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
    0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19
};

__constant uchar B3_SCHEDULE[7][16] = {
    {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15},
    {2, 6, 3, 10, 7, 0, 4, 13, 1, 11, 12, 5, 9, 14, 15, 8},
    {3, 4, 10, 12, 13, 2, 7, 14, 6, 5, 9, 0, 11, 15, 8, 1},
    {10, 7, 12, 9, 14, 3, 13, 15, 4, 0, 11, 2, 5, 8, 1, 6},
    {12, 13, 9, 11, 15, 10, 14, 8, 7, 2, 5, 3, 0, 1, 6, 4},
    {9, 14, 11, 5, 8, 12, 15, 1, 13, 3, 0, 10, 2, 6, 4, 7},
    {11, 15, 5, 0, 1, 9, 8, 6, 14, 10, 2, 12, 3, 4, 7, 13},
};

void b3_g(__private uint *v, uint a, uint b, uint c, uint d, uint x, uint y) {
    v[a] += v[b] + x;
    v[d] = rotate(v[d] ^ v[a], 16u);
    v[c] += v[d];
    v[b] = rotate(v[b] ^ v[c], 20u);
    v[a] += v[b] + y;
    v[d] = rotate(v[d] ^ v[a], 24u);
    v[c] += v[d];
    v[b] = rotate(v[b] ^ v[c], 25u);
}

void b3_compress(__private uint *cv, __private uchar *block, uint block_len,
                 uint flags, __private uint *out) {
    uint m[16];
    uint v[16];
    for (uint i = 0; i < 16; ++i) {
        uint j = i * 4;
        m[i] = (uint)block[j] | ((uint)block[j + 1] << 8) |
               ((uint)block[j + 2] << 16) | ((uint)block[j + 3] << 24);
    }
    for (uint i = 0; i < 8; ++i) {
        v[i] = cv[i];
    }
    for (uint i = 0; i < 4; ++i) {
        v[i + 8] = B3_IV[i];
    }
    v[12] = 0; // one BLAKE3 chunk, counter zero
    v[13] = 0;
    v[14] = block_len;
    v[15] = flags;
    for (uint r = 0; r < 7; ++r) {
        b3_g(v, 0, 4, 8, 12, m[B3_SCHEDULE[r][0]], m[B3_SCHEDULE[r][1]]);
        b3_g(v, 1, 5, 9, 13, m[B3_SCHEDULE[r][2]], m[B3_SCHEDULE[r][3]]);
        b3_g(v, 2, 6, 10, 14, m[B3_SCHEDULE[r][4]], m[B3_SCHEDULE[r][5]]);
        b3_g(v, 3, 7, 11, 15, m[B3_SCHEDULE[r][6]], m[B3_SCHEDULE[r][7]]);
        b3_g(v, 0, 5, 10, 15, m[B3_SCHEDULE[r][8]], m[B3_SCHEDULE[r][9]]);
        b3_g(v, 1, 6, 11, 12, m[B3_SCHEDULE[r][10]], m[B3_SCHEDULE[r][11]]);
        b3_g(v, 2, 7, 8, 13, m[B3_SCHEDULE[r][12]], m[B3_SCHEDULE[r][13]]);
        b3_g(v, 3, 4, 9, 14, m[B3_SCHEDULE[r][14]], m[B3_SCHEDULE[r][15]]);
    }
    for (uint i = 0; i < 8; ++i) {
        out[i] = v[i] ^ v[i + 8];
    }
}

void b3_hash(__private uchar *msg, uint len, __private uchar *digest) {
    uint cv[8];
    uint out[8];
    uchar block[64];
    for (uint i = 0; i < 8; ++i) cv[i] = B3_IV[i];
    uint blocks = (len + 63) / 64;
    for (uint b = 0; b < blocks; ++b) {
        for (uint j = 0; j < 64; ++j) {
            uint index = b * 64 + j;
            block[j] = index < len ? msg[index] : 0;
        }
        uint last = b + 1 == blocks;
        uint flags = (b == 0 ? 1u : 0u) | (last ? 2u | 8u : 0u);
        uint block_len = last ? len - b * 64 : 64;
        b3_compress(cv, block, block_len, flags, out);
        if (!last) {
            for (uint i = 0; i < 8; ++i) cv[i] = out[i];
        }
    }
    for (uint i = 0; i < 8; ++i) {
        digest[i * 4] = (uchar)out[i];
        digest[i * 4 + 1] = (uchar)(out[i] >> 8);
        digest[i * 4 + 2] = (uchar)(out[i] >> 16);
        digest[i * 4 + 3] = (uchar)(out[i] >> 24);
    }
}

__kernel void hash_nonces(__global const uchar *work_template,
                          __global const uchar *id_template,
                          __global const uchar *target,
                          ulong start_nonce,
                          __global uchar *digests,
                          __global uint *matches) {
    uint lane = get_global_id(0);
    ulong nonce = start_nonce + (ulong)lane;
    uchar work[71];
    uchar id[81];
    uchar work_hash[32];
    uchar block_id[32];
    for (uint i = 0; i < 71; ++i) work[i] = work_template[i];
    for (uint i = 0; i < 81; ++i) id[i] = id_template[i];
    for (uint i = 0; i < 8; ++i) work[31 + i] = (uchar)(nonce >> (8 * i));
    b3_hash(work, 71, work_hash);
    for (uint i = 0; i < 32; ++i) id[49 + i] = work_hash[i];
    b3_hash(id, 81, block_id);
    uint accept = 1;
    for (int i = 31; i >= 0; --i) {
        if (block_id[i] < target[i]) break;
        if (block_id[i] > target[i]) { accept = 0; break; }
    }
    for (uint i = 0; i < 32; ++i) digests[lane * 32 + i] = block_id[i];
    matches[lane] = accept;
}
