import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:hex/hex.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:lotus_dart/chronik.dart';
import 'package:lotus_dart/electrum.dart';
import 'package:test/test.dart';

void main() {
  test('Chronik protobuf requests, UTXOs, header and broadcast', () async {
    final client = ChronikClient(
      'http://localhost:8331',
      client: MockClient((req) async {
        expect(req.headers['accept'], 'application/x-protobuf');
        switch (req.url.path) {
          case '/blockchain-info':
            return http.Response.bytes(
              BlockchainInfo(tipHeight: 42).writeToBuffer(),
              200,
            );
          case '/script/p2tr/02/utxos':
            return http.Response.bytes(
              ScriptUtxos(
                script: [0x62],
                utxos: [
                  ScriptUtxo(
                    outpoint: OutPoint(txid: List.filled(32, 1), outIdx: 7),
                    blockHeight: -1,
                  ),
                ],
              ).writeToBuffer(),
              200,
            );
          case '/block-header/0':
            return http.Response.bytes(
              BlockHeader(rawHeader: List.filled(80, 0)).writeToBuffer(),
              200,
            );
          case '/broadcast-tx':
            expect(req.method, 'POST');
            expect(BroadcastTxRequest.fromBuffer(req.bodyBytes).rawTx, [
              1,
              2,
              3,
            ]);
            return http.Response.bytes(
              BroadcastTxResponse(
                txid: List.generate(32, (i) => i),
              ).writeToBuffer(),
              200,
            );
          default:
            return http.Response.bytes(
              Error(msg: 'No such tx').writeToBuffer(),
              404,
            );
        }
      }),
    );
    expect((await client.blockchainInfo()).tipHeight, 42);
    final utxos = await client.scriptUtxos('p2tr', '02');
    expect(utxos.utxos.single.blockHeight, -1);
    expect(utxos.utxos.single.outpoint.outIdx, 7);
    expect(() => client.blockHeader('0'), throwsFormatException);
    expect(
      await client.broadcast([1, 2, 3]),
      HEX.encode(List.generate(32, (i) => 31 - i)),
    );
    expect(() => client.tx('00' * 32), throwsA(isA<ChronikException>()));
    expect(() => client.tx('../oops'), throwsArgumentError);
    client.close();
  });

  test(
    'Electrum frames, multiplexes, notifies, errors, and disconnects',
    () async {
      final server = await ServerSocket.bind(InternetAddress.loopbackIPv4, 0);
      final connected = server.first;
      final client = await ElectrumClient.connect(
        '127.0.0.1',
        server.port,
        tls: false,
      );
      final peer = await connected;
      final requests = StreamIterator(
        peer
            .cast<List<int>>()
            .transform(utf8.decoder)
            .transform(const LineSplitter()),
      );
      final first = client.version();
      final second = client.balance('aa');
      await requests.moveNext();
      final a = jsonDecode(requests.current) as Map;
      await requests.moveNext();
      final b = jsonDecode(requests.current) as Map;
      expect(a['method'], 'server.version');
      expect(b['params'], ['aa']);
      peer.write('${jsonEncode({'id': b['id'], 'result': 42})}\n');
      peer.write(
        '${jsonEncode({
          'id': a['id'],
          'result': ['server', '1.4'],
        })}\n',
      );
      expect(await first, ['server', '1.4']);
      expect(await second, 42);
      final notification = client.notifications.first;
      peer.write(
        '${jsonEncode({
          'method': 'blockchain.headers.subscribe',
          'params': [
            {'height': 42},
          ],
        })}\n',
      );
      expect((await notification)['method'], 'blockchain.headers.subscribe');
      final error = client.history('bb');
      final errorExpectation = expectLater(
        error,
        throwsA(isA<ElectrumException>()),
      );
      await requests.moveNext();
      final c = jsonDecode(requests.current) as Map;
      peer.write(
        '${jsonEncode({
          'id': c['id'],
          'error': {'code': 1, 'message': 'bad'},
        })}\n',
      );
      await errorExpectation;
      final pending = client.subscribeHeaders();
      final pendingExpectation = expectLater(pending, throwsStateError);
      await client.close();
      await pendingExpectation;
      await requests.cancel();
      peer.destroy();
      await server.close();
      expect(
        ElectrumClient.scriptHash([0x51]),
        '6032c38c0bc0e91e726f1e55e1832e434509001a7aed5cfd881b6ef07215e84a',
      );
    },
  );
}
