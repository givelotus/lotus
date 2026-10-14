# Dart SDK maintenance

- Preserve the original MIT license and local ASN.1 code. No Git crypto fork is
  configured; PointyCastle resolves from pub.dev. Do not replace compact unsigned
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
