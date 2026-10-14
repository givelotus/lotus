/* Offline verification using the daemon's own libsecp256k1 archive. */
#include <stdio.h>
#include <string.h>
#include <secp256k1.h>

static int decode(const char *hex, unsigned char *out, size_t capacity) {
    size_t n = strlen(hex);
    if ((n & 1) || n / 2 > capacity) return -1;
    for (size_t i = 0; i < n / 2; ++i) {
        unsigned value;
        if (sscanf(hex + 2 * i, "%2x", &value) != 1) return -1;
        out[i] = (unsigned char)value;
    }
    return (int)(n / 2);
}

int main(int argc, char **argv) {
    unsigned char digest[32], pub_bytes[65], der[72];
    if (argc != 4 || decode(argv[1], digest, sizeof(digest)) != 32) return 2;
    int pub_size = decode(argv[2], pub_bytes, sizeof(pub_bytes));
    int der_size = decode(argv[3], der, sizeof(der));
    if (pub_size < 0 || der_size < 0) return 2;
    secp256k1_context *ctx = secp256k1_context_create(SECP256K1_CONTEXT_VERIFY);
    secp256k1_pubkey pub;
    secp256k1_ecdsa_signature sig;
    int valid = secp256k1_ec_pubkey_parse(ctx, &pub, pub_bytes, (size_t)pub_size)
        && secp256k1_ecdsa_signature_parse_der(ctx, &sig, der, (size_t)der_size)
        && secp256k1_ecdsa_verify(ctx, &sig, digest, &pub);
    secp256k1_context_destroy(ctx);
    return valid ? 0 : 1;
}
