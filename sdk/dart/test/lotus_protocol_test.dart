import 'dart:convert';
import 'dart:io';
import 'package:hex/hex.dart';
import 'package:lotus_dart/lotus.dart';
import 'package:test/test.dart';

void main() {
  test('Lotus header and TxIds match live mainnet fixtures', () {
    final fixture = jsonDecode(
      File('test/fixtures/lotus_mainnet.json').readAsStringSync(),
    );
    final header = LotusBlockHeader(HEX.decode(fixture['header']));
    expect(header.hash, fixture['blockHash']);
    expect(header.height, fixture['height']);
    for (final tx in fixture['transactions']) {
      expect(lotusTxId(HEX.decode(tx['raw'])), tx['txid']);
      expect(Transaction.fromHex(tx['raw']).id, tx['txid']);
    }
    expect(
      lotusTxId(HEX.decode('00000000000000000000')),
      '0aa86a445457f6eab159b7961df079bfd2107240b590d7c037bef3f26eafd291',
    );
  });
  test(
    'unsigned header nonce and serialized output amount preserve all bits',
    () {
      final raw = List<int>.filled(160, 0);
      raw.fillRange(44, 52, 255);
      expect(LotusBlockHeader(raw).nonce, (BigInt.one << 64) - BigInt.one);
      // TxId hashing never parses output amounts into a JavaScript number.
      expect(
        lotusTxId(HEX.decode('010000000001ffffffffffffffff0000000000')),
        'f27ee7fa062aa56937182166967b40f4e03edb2b361faed73e98efec7caaba86',
      );
    },
  );
  test('OpenSSL ECDSA vector verifies independently of signer', () {
    final fixture = jsonDecode(
      File('test/fixtures/openssl_signature.json').readAsStringSync(),
    );
    final publicKey = BCHPublicKey.fromHex(fixture['publicKey']);
    final sig = BCHSignature.fromDER(fixture['der'], publicKey: publicKey);
    expect(sig.verify(fixture['digest']), isTrue);
    expect(sig.verify('00' * 32), isFalse);
  });
}
