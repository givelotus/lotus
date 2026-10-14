# Dart SDK maintenance

- Preserve the original MIT attribution and upstream license. PointyCastle 4.0.0
  supersedes the original local ASN.1 fork (PR59/rewrite924e526a); old paths are
  compatibility exports, and ASN1Utils delegates to upstream public DER APIs.
  No Git crypto fork or independent ASN.1 integer codec remains. Do not replace compact unsigned
  32-byte signature limbs with DER's signed variable-length integer encoding.
- Lotus TxIds follow current C++ `ComputeTxId`/`TxOutputsMerkleRoot`: output leaves
  hash the serialized CTxOut (value, CompactSize script length, script bytes),
  and the final preimage includes version, both roots/heights and locktime.
- `LotusBlockHeader` parses 160 bytes and uses layered single SHA256. The legacy
  Bitcoin block/proof APIs are explicitly documented as unsuitable for Lotus.
- Keep Chronik HTTP and Electrum TCP/TLS as separate imports so primitives and
  Chronik stay browser compatible. Use generated protobuf types for lossless
  Int64 amounts. Do not add automatic transaction broadcast retries.
- Validate with `dart test`, `dart analyze --no-fatal-warnings`, and the web
  compile smoke tool. Existing inherited analyzer style/warning diagnostics are
  not suppressed globally. No live transaction broadcast is authorized by tests.
- `tool/check_chronik.dart` only performs reads; its optional live fixture refresh
  should be cross-checked with C++ RPC before accepting protocol changes.

- Dependency upgrades must preserve the original high-bit DER padding and 33-byte
  HD key fixes, and pass independent OpenSSL/libsecp256k1 interoperability checks.
  Exact recovered provenance and reproduction commands are in
  `docs/crypto-audit-20261014/README.md`.

- `nakamoto.dart` owns the explicit-chain API; keep it browser safe and preserve
  Vase's existing `lotus.dart` imports. Chain identity/configuration comes from
  pinned Frank Nakamoto descriptors and its canonical protocol registry, never
  inferred from display names or defaulted on unknown input. Update fixtures
  and regenerate/check `chains.dart` together with the documented tools.
- New transaction amounts are `BigInt` integer base units, including JavaScript.
  Signing requires explicit algorithm, hash type and supplied spent-output
  facts; it does not own wallet inventory or transport. Unsupported Script,
  spending and proof capabilities fail explicitly and remain documented in
  `docs/nakamoto-parity/README.md`. BIP340 primitives must not be described as
  BCH Schnorr or as complete Taproot transaction support.

- Latest dependency constraints were reviewed against official pub.dev metadata
  on 2026-10-14. Keep `unorm_dart` aligned with Vase (`^0.3.3`); BIP39 ASCII,
  composed/decomposed accents and compatibility characters have independent seed
  regression vectors. The Dart minimum is 3.11 because current test tooling
  requires it; Flutter's installed Dart 3.13.3 satisfies that bound.
