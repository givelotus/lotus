// Explicit opt-in only. Uses public fixture keys, never platform wallet storage.
import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:hex/hex.dart';
import 'package:lotus_dart/chronik.dart' as proto;
import 'package:lotus_dart/lotus.dart';
import 'package:vase/chronik-client/client.dart';
import 'package:vase/wallet/keys.dart';
import 'package:vase/wallet/wallet.dart';

void main() {
  final datadir = Platform.environment['VASE_REGTEST_DATADIR'];
  test(
    'real regtest mining, exact payment, broadcast, confirmation and WS balances',
    () async {
      final rpcPort = int.parse(
        Platform.environment['VASE_REGTEST_RPC_PORT'] ?? '22604',
      );
      final chronikPort = int.parse(
        Platform.environment['VASE_REGTEST_CHRONIK_PORT'] ?? '22331',
      );
      final http = HttpClient();
      addTearDown(() => http.close(force: true));
      final cookie = (await File(
        '$datadir/regtest/.cookie',
      ).readAsString()).trim();
      Future<dynamic> rpc(
        String method, [
        List<Object?> params = const [],
      ]) async {
        final request = await http.postUrl(
          Uri.parse('http://127.0.0.1:$rpcPort'),
        );
        request.headers.set(
          HttpHeaders.authorizationHeader,
          'Basic ${base64Encode(utf8.encode(cookie))}',
        );
        request.headers.contentType = ContentType.json;
        request.write(
          jsonEncode({
            'jsonrpc': '2.0',
            'id': 1,
            'method': method,
            'params': params,
          }),
        );
        final response = await request.close();
        final body =
            jsonDecode(await utf8.decoder.bind(response).join()) as Map;
        if (body['error'] != null)
          throw StateError('$method: ${body['error']}');
        return body['result'];
      }

      Future<void> eventually(Future<bool> Function() predicate) async {
        for (var i = 0; i < 100; i++) {
          if (await predicate()) return;
          await Future<void>.delayed(const Duration(milliseconds: 100));
        }
        fail('Timed out waiting for regtest/Chronik state');
      }

      // Both services must be the same fresh regtest chain before mining/signing.
      final chain = await rpc('getblockchaininfo') as Map;
      expect(chain['chain'], 'regtest');
      expect(
        chain['blocks'],
        0,
        reason: 'Use a fresh disposable regtest datadir',
      );
      final infoRequest = await http.getUrl(
        Uri.parse('http://127.0.0.1:$chronikPort/blockchain-info'),
      );
      final infoResponse = await infoRequest.close();
      final bytes = await infoResponse.fold<List<int>>(
        [],
        (a, b) => a..addAll(b),
      );
      final info = proto.BlockchainInfo.fromBuffer(bytes);
      expect(
        HEX.encode(info.tipHash.reversed.toList()),
        chain['bestblockhash'],
      );

      Keys fixture(int receiving, int change) => Keys(
        null,
        null,
        HDPrivateKey.fromSeed(
          '000102030405060708090a0b0c0d0e0f',
          NetworkType.MAIN,
        ),
        [
          KeyInfo(
            key: BCHPrivateKey.fromBigInt(BigInt.from(receiving)),
            keyIndex: 0,
          ),
          KeyInfo(
            key: BCHPrivateKey.fromBigInt(BigInt.from(change)),
            keyIndex: 1,
            isChange: true,
          ),
        ],
      );
      final senderKeys = fixture(1, 2), receiverKeys = fixture(3, 4);
      final minerKey = BCHPrivateKey.fromBigInt(BigInt.from(5));
      final sender = Wallet(
        senderKeys,
        network: NetworkType.MAIN,
        chronik: ChronikClient('http://127.0.0.1:$chronikPort'),
      );
      final receiver = Wallet(
        receiverKeys,
        network: NetworkType.MAIN,
        chronik: ChronikClient('http://127.0.0.1:$chronikPort'),
      );
      addTearDown(sender.close);
      addTearDown(receiver.close);
      await rpc('generatetodescriptor', [
        1,
        'pkh(${senderKeys.keys!.first.key.publicKey})',
      ]);
      await rpc('generatetodescriptor', [100, 'pkh(${minerKey.publicKey})']);
      await sender.updateUtxosChronik();
      sender.refreshBalanceLocal();
      final before = sender.balanceSatoshis();
      expect(before, greaterThan(BigInt.from(1000001)));
      final amount = BigInt.from(1000001); // Exactly 1.000001 XPI.
      final transaction = (await sender.sendTransaction(
        receiverKeys.keys!.first.address!,
        amount,
      ))!;
      final txid = lotusTxId(HEX.decode(transaction.serialize()));
      expect(await rpc('getrawmempool'), contains(txid));
      final raw = await rpc('getrawtransaction', [txid]);
      expect(raw, transaction.serialize());
      await eventually(() async => receiver.balanceSatoshis() == amount);
      await eventually(
        () async =>
            sender.balanceSatoshis() == transaction.outputAmount - amount,
      );
      final block =
          (await rpc('generatetodescriptor', [1, 'pkh(${minerKey.publicKey})'])
                  as List)
              .single;
      final confirmed =
          await rpc('getrawtransaction', [txid, true, block]) as Map;
      expect(confirmed['confirmations'], 1);
      expect(confirmed['txid'], txid);
      expect(await rpc('getrawmempool'), isEmpty);
      await receiver.updateUtxosChronik();
      receiver.refreshBalanceLocal();
      expect(receiver.balanceSatoshis(), amount);
      final reply = (await receiver.sendTransaction(
        senderKeys.keys!.first.address!,
        BigInt.from(500001),
      ))!;
      final replyId = lotusTxId(HEX.decode(reply.serialize()));
      expect(await rpc('getrawmempool'), contains(replyId));
      await rpc('generatetodescriptor', [1, 'pkh(${minerKey.publicKey})']);
      expect(await rpc('verifychain', [4, 0]), true);
      print(
        'REGTEST PASS: height=103 payment=$amount TxId=$txid reply=$replyId',
      );
    },
    skip: datadir == null
        ? 'Set VASE_REGTEST_DATADIR to a fresh isolated regtest node'
        : false,
    timeout: const Timeout(Duration(minutes: 2)),
  );
}
