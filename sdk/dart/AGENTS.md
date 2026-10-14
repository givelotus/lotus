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
