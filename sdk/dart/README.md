# Lotus Dart SDK

Keys, XAddresses, scripts and transactions for Lotus (XPI), plus separate Chronik
HTTP/protobuf and Electrum TCP/TLS clients. Dart 3.11 or later is required.

```sh
dart pub get
dart test
dart analyze --no-fatal-warnings
dart compile js tool/compile_web.dart -o /tmp/lotus-dart-sdk-web.js
```

The inherited code has analyzer warnings and style diagnostics. Analysis passes
with warnings nonfatal; these are not a claim of a complete cryptographic audit.
Both Dart 3.13.3 and 3.13.5 are checked for this revision.

```dart
import 'package:lotus_dart/chronik.dart' as chronik;
import 'package:lotus_dart/lotus.dart';

final client = chronik.ChronikClient('http://127.0.0.1:8331');
final tip = await client.blockchainInfo();
final header = LotusBlockHeader((await client.blockHeader('${tip.tipHeight}')).rawHeader);
print(header.hash);
final coins = await client.scriptUtxos('p2pkh', '00' * 20);
// Values are protobuf Int64, rather than potentially rounded JavaScript numbers.
for (final coin in coins.utxos) { print(coin.sats); }
client.close();
```

Chronik preserves server-provided merkleized TxIds. Protobuf hashes use little
endian bytes; URL TxIds and `broadcast` results use display hex. `Transaction.id`
and `lotusTxId(rawBytes)` compute the Lotus merkleized ID; `Transaction.hash`
remains SHA256d of the full serialization. Use `LotusBlockHeader` for the 160-byte
Lotus format and its layered SHA256 block hash. The inherited `BlockHeader`,
`Block` and `MerkleBlock` classes describe Bitcoin formats and are unsuitable for
Lotus block/proof validation. The SDK does not implement Lotus Taproot spending
or SIGHASH_LOTUS; legacy FORKID signing remains available. The Chronik client
supports P2TR UTXO lookup without interpreting or spending its outputs.

Electrum is deliberately separate, uses `dart:io` and supports Flutter
mobile/desktop and Dart VM (not browsers):

```dart
import 'package:lotus_dart/electrum.dart';

final client = await ElectrumClient.connect('your-electrum-host', 50002);
await client.version();
final scriptHash = ElectrumClient.scriptHash([0x51]);
final notifications = client.notifications.listen(print);
print(await client.subscribeScript(scriptHash));
print(await client.listUnspent(scriptHash));
await notifications.cancel();
await client.close();
```

TLS uses normal platform certificate verification. Plain TCP requires
`tls: false`. Callers own reconnection and resubscription; requests time out,
and disconnects fail pending requests. Broadcasts are never retried automatically.
No public Lotus Electrum endpoint is bundled or presumed available.

`dart run tool/check_chronik.dart [http://127.0.0.1:8331]` performs read-only live
header/TxId checks and refreshes the mainnet fixtures. Offline tests cover those
fixtures, protocol framing/error paths, DER lengths, unsigned compact signatures,
low-S recovery, and an independent OpenSSL-backed ECDSA fixture. Tests never
broadcast live transactions. Mainnet fixtures were additionally compared against
C++ Lotus RPC, including 23 transactions across six heights and non-coinbase
transactions; the header fixture is at height 1,400,945.

## Provenance

This package was extracted from the Vase wallet. `lib/LICENSE` preserves the
original MIT attribution; root `LICENSE` makes it visible to Dart package tools.
PointyCastle 4.0.0 is the reviewed dependency. The original local ASN.1 fork is
retired: old import paths forward to upstream classes, with a small adapter for
legacy helper names. The original padding submission was PointyCastle PR #59;
upstream incorporated it through a broader BigInt rewrite in December 2020.
See [the crypto audit](docs/crypto-audit-20261014/README.md) for original commit
mapping, upstream links, exact dependency versions and reproducible independent
OpenSSL/libsecp256k1 verification. HD key padding and unsigned fixed-width compact
signatures remain distinct from signed variable-length DER integers.

`proto/chronik.proto` is copied unchanged from Bitcoin ABC commit
`8c67fe1e85a602204a2ce65aa3b643469c2c3a1d` (MIT, copyright The Bitcoin developers).
Regenerate the checked-in Dart bindings with:

```sh
dart pub global activate protoc_plugin 25.1.0
protoc --plugin=protoc-gen-dart="$HOME/.pub-cache/bin/protoc-gen-dart" \
  --dart_out=lib/src/chronik -Iproto proto/chronik.proto
```
