import 'dart:convert';
import 'dart:io';
import 'package:hex/hex.dart';
import 'package:lotus_dart/chronik.dart';
import 'package:lotus_dart/lotus.dart';

Future<void> main(List<String> args) async {
  final client = ChronikClient(
    args.isEmpty ? 'http://127.0.0.1:8331' : args[0],
  );
  try {
    final tip = await client.blockchainInfo();
    final header = await client.blockHeader(tip.tipHeight.toString());
    final parsed = LotusBlockHeader(header.rawHeader);
    if (parsed.hash != HEX.encode(tip.tipHash.reversed.toList())) {
      throw StateError('Header hash disagrees with Chronik');
    }
    final fixtures = <Map<String, String>>[];
    for (final height in [0, 1, 143509, 273561, 500054, tip.tipHeight]) {
      final page = await client.blockTxs(height);
      for (final tx in page.txs) {
        final txid = HEX.encode(tx.txid.reversed.toList());
        final raw = await client.rawTx(txid);
        if (lotusTxId(raw) != txid ||
            Transaction.fromHex(HEX.encode(raw)).id != txid) {
          throw StateError('TxId mismatch: $txid');
        }
        fixtures.add({
          'txid': txid,
          'raw': HEX.encode(raw),
          'height': '$height',
        });
      }
    }
    final fixture = {
      'header': HEX.encode(header.rawHeader),
      'blockHash': parsed.hash,
      'height': parsed.height,
      'transactions': fixtures,
    };
    File('test/fixtures/lotus_mainnet.json').writeAsStringSync(
      '${const JsonEncoder.withIndent('  ').convert(fixture)}\n',
    );
    print(
      'Verified live Lotus header at ${tip.tipHeight} and ${fixtures.length} sampled transactions',
    );
  } finally {
    client.close();
  }
}
