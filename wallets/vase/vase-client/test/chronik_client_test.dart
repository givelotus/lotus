import 'dart:async';
import 'dart:io';

import 'package:fixnum/fixnum.dart';
import 'package:lotus_dart/chronik.dart' as current;
import 'package:test/test.dart';
import 'package:vase/chronik-client/client.dart';
import 'package:vase/chronik-client/client.types.dart' as legacy;

void main() {
  test(
    'current UTXO, broadcast, and error protobufs cross HTTP as bytes',
    () async {
      final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
      addTearDown(() => server.close(force: true));
      final payload = 'ab' * 20;
      final txidBytes = List<int>.generate(32, (i) => i);
      final calls = <String>[];
      current.BroadcastTxRequest? broadcast;
      server.listen((request) async {
        calls.add(request.uri.path);
        request.response.headers.contentType = ContentType(
          'application',
          'x-protobuf',
        );
        if (request.uri.path == '/script/p2pkh/$payload/utxos') {
          request.response.add(
            current.ScriptUtxos(
              script: [0x76, 0xa9],
              utxos: [
                current.ScriptUtxo(
                  outpoint: current.OutPoint(txid: txidBytes, outIdx: 3),
                  blockHeight: 42,
                  isCoinbase: false,
                  sats: Int64.parseInt('9007199254740993'),
                ),
                current.ScriptUtxo(
                  outpoint: current.OutPoint(txid: txidBytes, outIdx: 4),
                  sats: Int64(100),
                  token: current.Token(tokenId: '01' * 32),
                ),
              ],
            ).writeToBuffer(),
          );
        } else if (request.uri.path == '/broadcast-tx') {
          final bytes = await request.fold<List<int>>(
            [],
            (all, chunk) => all..addAll(chunk),
          );
          broadcast = current.BroadcastTxRequest.fromBuffer(bytes);
          request.response.add(
            current.BroadcastTxResponse(txid: txidBytes).writeToBuffer(),
          );
        } else {
          request.response.statusCode = HttpStatus.badRequest;
          request.response.add(
            current.Error(msg: 'fixture rejected request').writeToBuffer(),
          );
        }
        await request.response.close();
      });
      final client = ChronikClient('http://127.0.0.1:${server.port}');
      final groups = await client.script('p2pkh', payload).utxos();
      expect(groups, hasLength(1));
      expect(groups.single.outputScript, '76a9');
      expect(
        groups.single.utxos,
        hasLength(1),
        reason: 'token UTXOs must not be offered for ordinary XPI spends',
      );
      final coin = groups.single.utxos.single;
      expect(
        coin.outpoint.txid,
        txidBytes.reversed
            .map((b) => b.toRadixString(16).padLeft(2, '0'))
            .join(),
      );
      expect(coin.outpoint.outIdx, 3);
      expect(coin.value, '9007199254740993');
      expect(coin.blockHeight, 42);
      expect(coin.network, legacy.Network.XPI);
      final result = await client.broadcastTx(rawTx: '0001ff');
      expect(broadcast!.rawTx, [0, 1, 255]);
      expect(broadcast!.skipTokenChecks, isFalse);
      expect(result.txid, coin.outpoint.txid);
      await expectLater(
        client.script('p2pkh', 'cd' * 20).utxos(),
        throwsA(
          isA<current.ChronikException>().having(
            (e) => e.message,
            'message',
            contains('fixture rejected request'),
          ),
        ),
      );
      expect(calls, hasLength(3));
    },
  );

  test(
    'WebSocket subscribes as current binary protobuf and reconnects once',
    () async {
      final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
      final frames = StreamController<List<int>>();
      final iterator = StreamIterator(frames.stream);
      final peers = <WebSocket>[];
      final firstConnect = Completer<void>();
      final secondConnect = Completer<void>();
      final received = Completer<legacy.SubscribeMsg>();
      var connects = 0;
      var reconnects = 0;
      server.listen((request) async {
        final peer = await WebSocketTransformer.upgrade(request);
        peers.add(peer);
        peer.listen((frame) => frames.add(frame as List<int>));
      });
      final payload = 'ab' * 20;
      late WsEndpoint endpoint;
      endpoint = ChronikClient('http://127.0.0.1:${server.port}').ws(
        WsConfig(
          onConnect: () {
            connects++;
            endpoint.subscribe(
              'p2pkh',
              payload,
            ); // Must not duplicate queued/resumed subscription.
            if (connects == 1) firstConnect.complete();
            if (connects == 2) secondConnect.complete();
          },
          onReconnect: () => reconnects++,
          onMessage: (message) {
            if (!received.isCompleted) received.complete(message);
          },
        ),
      );
      addTearDown(() async {
        await endpoint.close();
        for (final peer in peers) {
          await peer.close();
        }
        await iterator.cancel();
        await frames.close();
        await server.close(force: true);
      });
      endpoint.subscribe('p2pkh', payload);
      await firstConnect.future.timeout(const Duration(seconds: 5));
      expect(
        await iterator.moveNext().timeout(const Duration(seconds: 5)),
        isTrue,
      );
      final subscription = current.WsSub.fromBuffer(iterator.current);
      expect(subscription.isUnsub, isFalse);
      expect(subscription.script.scriptType, 'p2pkh');
      expect(subscription.script.payload, List.filled(20, 0xab));
      peers.first.add(
        current.WsMsg(
          tx: current.MsgTx(
            msgType: current.TxMsgType.TX_ADDED_TO_MEMPOOL,
            txid: List.filled(32, 0x12),
          ),
        ).writeToBuffer(),
      );
      final notification = await received.future.timeout(
        const Duration(seconds: 5),
      );
      expect(notification, isA<legacy.MsgAddedToMempool>());
      expect((notification as legacy.MsgAddedToMempool).txid, '12' * 32);
      await peers.first.close();
      await secondConnect.future.timeout(const Duration(seconds: 5));
      expect(reconnects, 1);
      expect(
        await iterator.moveNext().timeout(const Duration(seconds: 5)),
        isTrue,
      );
      expect(
        current.WsSub.fromBuffer(iterator.current).script.payload,
        subscription.script.payload,
      );
      endpoint.unsubscribe('p2pkh', payload);
      expect(
        await iterator.moveNext().timeout(const Duration(seconds: 5)),
        isTrue,
      );
      expect(current.WsSub.fromBuffer(iterator.current).isUnsub, isTrue);
      await endpoint.close();
      await Future<void>.delayed(const Duration(milliseconds: 50));
      expect(connects, 2);
    },
  );
}
