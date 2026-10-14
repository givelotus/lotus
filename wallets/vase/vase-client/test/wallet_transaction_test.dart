import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:lotus_dart/lotus.dart';
import 'package:vase/chronik-client/client.dart';
import 'package:vase/chronik-client/client.types.dart' as chronik;
import 'package:vase/wallet/keys.dart';
import 'package:vase/wallet/wallet.dart';

class FakeSocket implements WsEndpoint {
  final subscriptions = <String>[];

  @override
  void subscribe(String scriptType, String scriptPayload) {
    subscriptions.add(scriptPayload);
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class FakeScript extends ScriptEndpoint {
  final List<chronik.Utxo> coins;
  final bool fail;

  FakeScript(String payload, this.coins, this.fail)
    : super(
        url: 'http://unused.invalid',
        scriptType: 'p2pkh',
        scriptPayload: payload,
      );

  @override
  Future<List<chronik.ScriptUtxos>> utxos() async {
    if (fail) throw StateError('fixture request failed');
    return [chronik.ScriptUtxos(outputScript: '', utxos: coins)];
  }
}

class FakeChronik extends ChronikClient {
  final socket = FakeSocket();
  final responses = <String, List<chronik.Utxo>>{};
  final requestedPayloads = <String>[];
  String? failingPayload;
  int broadcastCalls = 0;
  WsConfig? config;

  FakeChronik() : super('http://unused.invalid');

  @override
  WsEndpoint ws(WsConfig config) {
    this.config = config;
    return socket;
  }

  @override
  Future<chronik.BroadcastTxResponse> broadcastTx({
    dynamic rawTx,
    dynamic skipSlpCheck = false,
  }) async {
    broadcastCalls++;
    throw StateError('fixture broadcast rejected');
  }

  @override
  ScriptEndpoint script(String scriptType, String scriptPayload) {
    requestedPayloads.add(scriptPayload);
    return FakeScript(
      scriptPayload,
      responses[scriptPayload] ?? [],
      failingPayload == scriptPayload,
    );
  }
}

chronik.Utxo coin(int amount, [int index = 0]) => chronik.Utxo(
  outpoint: chronik.OutPoint(txid: '01' * 32, outIdx: index),
  blockHeight: 1,
  isCoinbase: false,
  value: '$amount',
  slpMeta: null,
  network: chronik.Network.XPI,
);

void main() {
  late Wallet wallet;
  late Keys keys;
  late FakeChronik client;
  late String payload;

  TransactionOutput output(int amount) {
    return TransactionOutput(
      scriptBuilder: P2PKHLockBuilder(keys.keys!.first.address),
    )..satoshis = BigInt.from(amount);
  }

  Future<void> fund(List<chronik.Utxo> coins) async {
    client.responses[payload] = coins;
    await wallet.updateUtxosChronik();
    wallet.refreshBalanceLocal();
  }

  setUp(() {
    final root = HDPrivateKey.fromSeed(
      '000102030405060708090a0b0c0d0e0f',
      NetworkType.MAIN,
    );
    keys = Keys(null, null, root, [
      KeyInfo(key: BCHPrivateKey.fromBigInt(BigInt.one), keyIndex: 0),
      KeyInfo(
        key: BCHPrivateKey.fromBigInt(BigInt.two),
        keyIndex: 1,
        isChange: true,
      ),
    ]);
    payload = keys.keys!.first.address!.pubkeyHash160!;
    client = FakeChronik();
    wallet = Wallet(keys, network: NetworkType.MAIN, chronik: client);
  });

  test(
    'Chronik queries and subscriptions use 20-byte public key hashes',
    () async {
      await fund([coin(10000)]);
      await wallet.startUtxoListenersChronik();
      expect(client.requestedPayloads, contains(payload));
      expect(
        client.requestedPayloads.every((value) => value.length == 40),
        isTrue,
      );
      expect(client.socket.subscriptions, client.requestedPayloads);
    },
  );

  test(
    'refresh removes spent coins and failed refresh preserves prior vault',
    () async {
      await fund([coin(10000)]);
      client.failingPayload = keys.keys!.last.address!.pubkeyHash160!;
      client.responses[payload] = [];
      await expectLater(wallet.updateUtxosChronik(), throwsStateError);
      wallet.refreshBalanceLocal();
      expect(wallet.balanceSatoshis(), BigInt.from(10000));
      client.failingPayload = null;
      await fund([]);
      expect(wallet.balanceSatoshis(), BigInt.zero);
    },
  );

  test(
    'transaction notifications refresh the vault and reported balance',
    () async {
      await fund([coin(10000)]);
      final updated = Completer<WalletBalance>();
      wallet.balanceUpdateHandler = (balance) {
        if (!updated.isCompleted) updated.complete(balance);
      };
      client.responses[payload] = [];
      client.config!.onMessage!(chronik.MsgAddedToMempool(txid: '01' * 32));
      expect(
        (await updated.future.timeout(const Duration(seconds: 2))).balance,
        BigInt.zero,
      );
      expect(wallet.balanceSatoshis(), BigInt.zero);
    },
  );

  test(
    'insufficient funds includes signed fees and preserves coins for retry',
    () async {
      await fund([coin(10000)]);
      expect(
        () =>
            wallet.constructTransaction([output(9990)], feePerByte: BigInt.one),
        throwsException,
      );
      wallet.refreshBalanceLocal();
      expect(wallet.balanceSatoshis(), BigInt.from(10000));
      final result = wallet.constructTransaction([
        output(8000),
      ], feePerByte: BigInt.one);
      expect(result.usedUtxos, hasLength(1));
      final tx = result.transaction!;
      expect(
        tx.inputAmount - tx.outputAmount,
        greaterThanOrEqualTo(BigInt.from(tx.uncheckedSerialize().length)),
      );
      wallet.refreshBalanceLocal();
      expect(wallet.balanceSatoshis(), BigInt.zero);
    },
  );

  test('omitted fee uses default and pays for signed transaction', () async {
    await fund([coin(10000)]);
    final tx = wallet.constructTransaction([output(5000)]).transaction!;
    expect(
      tx.inputAmount - tx.outputAmount,
      greaterThanOrEqualTo(BigInt.from(tx.uncheckedSerialize().length * 10)),
    );
  });

  test('finalization failure preserves selected coins', () async {
    await fund([coin(10000)]);
    keys.keys!.last.isChange = false;
    expect(
      () => wallet.constructTransaction([output(5000)], feePerByte: BigInt.one),
      throwsStateError,
    );
    wallet.refreshBalanceLocal();
    expect(wallet.balanceSatoshis(), BigInt.from(10000));
    keys.keys!.last.isChange = true;
    expect(
      wallet.constructTransaction([
        output(5000),
      ], feePerByte: BigInt.one).usedUtxos,
      hasLength(1),
    );
  });

  test('failed send restores coins and balance', () async {
    await fund([coin(10000)]);
    await expectLater(
      wallet.sendTransaction(keys.keys!.first.address!, BigInt.from(5000)),
      throwsStateError,
    );
    expect(client.broadcastCalls, 1);
    expect(wallet.balanceSatoshis(), BigInt.from(10000));
    expect(wallet.constructTransaction([output(5000)]).usedUtxos, hasLength(1));
  });

  test('serialization failure restores coins before broadcast', () async {
    await fund([coin(10000)]);
    await expectLater(
      wallet.sendTransaction(keys.keys!.first.address!, BigInt.one),
      throwsA(anything),
    );
    expect(client.broadcastCalls, 0);
    expect(wallet.balanceSatoshis(), BigInt.from(10000));
    expect(wallet.constructTransaction([output(5000)]).usedUtxos, hasLength(1));
  });

  test(
    'rejects empty outputs, nonpositive amounts, and negative fees',
    () async {
      await fund([coin(10000)]);
      expect(() => wallet.constructTransaction([]), throwsArgumentError);
      expect(
        () => wallet.constructTransaction([output(0)]),
        throwsArgumentError,
      );
      expect(
        () => wallet.constructTransaction([output(-1)]),
        throwsArgumentError,
      );
      expect(
        () => wallet.constructTransaction([output(1)], feePerByte: -BigInt.one),
        throwsArgumentError,
      );
      wallet.refreshBalanceLocal();
      expect(wallet.balanceSatoshis(), BigInt.from(10000));
    },
  );
}
