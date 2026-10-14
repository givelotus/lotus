# Crypto dependency and original fork audit — 2026-10-14

The original fork is **PointyCastle ASN.1**, not Forge. We recovered it from the
original `givelotus/lotus-vase` Git history, available locally at
`/Users/shammah/repos/lotus-vase`, whose imported tip is
`66abe1b2649b35fc10c8d14c335db4e8b7a5635c`. Searches of the original pubspec
history found PointyCastle, without a Forge or Git crypto dependency. This does
not assert anything about unrelated projects.

## Upstream submission and resolution

Shammah Chancellor (`schancel`) opened [PointyCastle PR #59](https://github.com/bcgit/pc-dart/pull/59)
on November 18, 2020 to add a positive integer sign-padding byte when its high
bit is set. The PR was closed **without a direct merge** on December 15, 2020.
The maintainer said it prompted a broader BigInt API rework. The resulting
[upstream commit `924e526aaf3df88e44fbb060f26fa89bc842a07b`](https://github.com/bcgit/pc-dart/commit/924e526aaf3df88e44fbb060f26fa89bc842a07b)
explicitly lists PR #59 and introduces signed two's-complement encoding plus
separate unsigned operations. The [upstream changelog](https://github.com/bcgit/pc-dart/blob/master/CHANGELOG.md)
records this behavior in version 2.0.1, released January 16, 2021. Thus the
contribution was incorporated through a rewritten upstream change, rather than
a literal merge of the original PR.

The live [pub.dev package API](https://pub.dev/api/packages/pointycastle) identifies
**4.0.0** as the latest release when checked for this audit; its published archive
SHA256 is `92aa3841d083cc4b0f4709b5c74fd6409a3e6ba833ffc7dc6a8fee096366acf5`.
The SDK and wallet now require `pointycastle: ^4.0.0`. Before this change the
constraint was `^3.3.5`: the wallet lockfile used 3.6.2, while the prior isolated
SDK validation resolved 3.9.1. Earlier review did not upgrade that dependency.

## Original changes and their disposition

| Original Vase commit | Purpose | Current disposition |
| --- | --- | --- |
| [`f2962e374c1752f80415e3586f1cd0bae0171265`](https://github.com/givelotus/lotus-vase/commit/f2962e374c1752f80415e3586f1cd0bae0171265) | Call `encode()` before returning DER bytes. | Retained in `BCHSignature.toDER`; now executes upstream PointyCastle. |
| [`209d8ddb0e802888f7f42c4e02a3d8224f05e354`](https://github.com/givelotus/lotus-vase/commit/209d8ddb0e802888f7f42c4e02a3d8224f05e354) | Copy ASN.1 locally and fix positive high-bit integer padding. | Local ASN.1 implementation retired. Upstream 4.0.0 provides the padding behavior, with regression tests for 127/128/255 and 256-bit boundaries. |
| [`20e62c94f226b9f882856115ebd8faca2d8cff2e`](https://github.com/givelotus/lotus-vase/commit/20e62c94f226b9f882856115ebd8faca2d8cff2e) | Separate unsigned key encoding; adjust HD padding; also redirect compact signatures to ASN.1 helpers. | Unsigned key routines retained. The compact-signature redirect was replaced in the earlier SDK repair with unsigned fixed 32-byte limbs; DER is inappropriate there. |
| [`11964342f5e725ed09386e116c0489ca5f2459e7`](https://github.com/givelotus/lotus-vase/commit/11964342f5e725ed09386e116c0489ca5f2459e7) | Add signed decoding/encoding to the local ASN.1 copy. | Superseded by upstream two's-complement implementation. The legacy decoder mutated input and decoded `ff` as -127 instead of -1; new regressions fail before retirement and pass afterward. Positive ECDSA DER limbs were not negative-number cases. |
| [`5f205fe4957ef6db2915a9be68996a7430e0cd39`](https://github.com/givelotus/lotus-vase/commit/5f205fe4957ef6db2915a9be68996a7430e0cd39) | Move short private-key padding into CKDSerializer so xpriv payloads are 33 bytes. | Retained. Explicit short-magnitude padding tests and the existing 1,000-child HD derivation/xpriv regression pass. |
| [`f165701`](https://github.com/givelotus/lotus-vase/commit/f165701) | Null safety and PointyCastle 2.x → `^3.3.5`. | Null handling retained; dependency constraint deliberately advances to 4.0.0 here. |

All original local ASN.1 paths now forward to upstream public PointyCastle
classes. A small compatibility `ASN1Utils` adapter retains old helper names by
calling upstream's public `ASN1Integer` API, without a private `src/` import or
independent integer codec. The inactive wallet ASN.1 import paths forward to the
canonical SDK, eliminating its second copied implementation too. MIT notices
and original repository history are preserved; upstream's license is retained
at [POINTYCASTLE-LICENSE.txt](../POINTYCASTLE-LICENSE.txt).

## Verification and limits

- SDK: 40 tests, including original fork edge cases, DER minimality, short and
  high-bit scalars, malformed padding, low-S signing, compact length and recovery,
  HD key padding and existing derivation vectors.
- 513 Dart signatures verify independently in Python `cryptography` using
  OpenSSL and in the daemon's own libsecp256k1. All are low-S; six have a short
  scalar, 249 have a high-bit R, and DER lengths are 69/70/71 bytes. The same
  513 DER and compact signatures are byte-identical to the previous SDK with
  PointyCastle 3.9.1 and the local ASN.1 copy.
- 64 independently generated OpenSSL signatures (both low-S and high-S forms)
  verify in Dart; incorrect digest verification fails.
- One signature digest is the daemon's existing legacy FORKID fixture;
  SDK digest generation agrees with that fixture, including display/raw byte
  ordering. This is not a claim of complete SIGHASH_LOTUS support.
- Wallet: 44 Flutter tests and release web compilation are checked with 4.0.0.
- Dart SDK browser compilation is checked. No global Dart/Flutter upgrade,
  transaction broadcast, wallet key access, node mutation or asset publication
  is part of this verification. Native mobile camera/packaging remains outside
  this audit.

Machine-readable results are in [interop-summary.json](interop-summary.json).
The before-fix failure log is [legacy-asn1-failures.log](legacy-asn1-failures.log).
The isolated outputs contain only the publicly known test private key 1;
never reuse that key for funds. OpenSSL is an independent implementation from
PointyCastle; daemon libsecp256k1 provides another independent verifier.

## Reproduce offline interoperability

From `sdk/dart`, resolve the reviewed dependencies, then use a disposable Python
venv. The validation environment used `cryptography==50.0.2`; Python packages are
not application dependencies.

```sh
dart pub get
python3 -m venv /tmp/lotus-crypto-verify
/tmp/lotus-crypto-verify/bin/pip install cryptography==50.0.2
# DAEMON_SRC is an already-built isolated Lotus checkout; do not rebuild a live workspace.
clang -Wall -Wextra -Werror -I"$DAEMON_SRC/src/secp256k1/include" \
  tool/secp256k1_verify.c "$DAEMON_SRC/build/src/secp256k1/libsecp256k1.a" \
  -o /tmp/lotus-secp256k1-verify
/tmp/lotus-crypto-verify/bin/python tool/check_signature_interop.py \
  --native-verifier /tmp/lotus-secp256k1-verify \
  --output-dir /tmp/lotus-crypto-results
dart test
dart compile js tool/compile_web.dart -o /tmp/lotus-sdk-web.js
```

`--native-verifier` can be omitted for OpenSSL-only checks; the summary then
explicitly records zero native checks. Tools produce the Dart vectors, independent
OpenSSL vectors and a versioned JSON result; they do not connect to a node.
