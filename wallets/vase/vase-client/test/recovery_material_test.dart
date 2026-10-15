import 'dart:async';
import 'dart:typed_data';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lotus_dart/bip39/bip39.dart';
import 'package:lotus_dart/codex32.dart';
import 'package:vase/chronik-client/client.dart';
import 'package:vase/features/wallet/wallet_model.dart';
import 'package:vase/wallet/keys.dart';
import 'package:vase/wallet/recovery_material.dart';
import 'package:vase/wallet/wallet.dart';
import 'secure_storage_test.dart' show MemoryStorage;

const words =
    'abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about';
const otherWords =
    'legal winner thank year wave sausage worth useful legal winner thank yellow';
Uint8List random(int n) =>
    Uint8List.fromList(List.generate(n, (i) => (i * 17 + 9) & 255));

class TestWallet implements Wallet {
  @override
  BalanceUpdateHandler? balanceUpdateHandler;
  @override
  void initialize() {}
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class RecordStorage extends MemoryStorage {
  RecordStorage(super.values);
  bool failWrites = false;
  Completer<void>? gate;
  @override
  Future<void> write({
    required String key,
    required String? value,
    AndroidOptions? aOptions,
    AppleOptions? iOptions,
    LinuxOptions? lOptions,
    WebOptions? webOptions,
    AppleOptions? mOptions,
    WindowsOptions? wOptions,
  }) async {
    writes.add(key);
    final wait = gate;
    gate = null;
    if (wait != null) await wait.future;
    if (failWrites) throw StateError('storage failure');
    if (value == null) {
      values.remove(key);
    } else {
      values[key] = value;
    }
  }
}

WalletModel model(
  RecordStorage storage, {
  Future<Wallet> Function(String?, String?)? factory,
}) => WalletModel(
  ChronikClient('http://unused.invalid'),
  storage: storage,
  initialize: false,
  walletFactory: factory ?? (_, _) async => TestWallet(),
);
RecordStorage legacy() => RecordStorage({
  SCHEMA_VERSION_KEY: CURRENT_SCHEMA_VERSION,
  STORAGE_SEED_KEY: words,
  STORAGE_PASSWORD_KEY: ' Existing Passphrase ',
});

void main() {
  test('legacy mnemonic wallets preserve the existing BIP39 seed bytes', () {
    for (final passphrase in ['', 'TREZOR', ' Secret ', 'é', 'e\u0301']) {
      final actual = walletSeedBytes(words, passphrase);
      final expected = Mnemonic().toSeedHex(words, passphrase);
      expect(
        actual.map((b) => b.toRadixString(16).padLeft(2, '0')).join(),
        expected,
      );
      actual.fillRange(0, actual.length, 0);
    }
  });
  test(
    'BIP39 and shard recovery derive the same complete Vase key inventory',
    () async {
      final original = await Keys.construct(words, ' Mixed Case ');
      final shares = backupWalletMaterial(
        words,
        ' Mixed Case ',
        randomBytes: random,
      );
      final material = materialFromShares(shares);
      final restored = await Keys.construct(material);
      expect(restored.rootKey.toString(), original.rootKey.toString());
      expect(
        restored.keys!.map((k) => k.address!.toXAddress()).toList(),
        original.keys!.map((k) => k.address!.toXAddress()).toList(),
      );
      final again = backupWalletMaterial(material, '', randomBytes: random);
      expect(
        walletSeedBytes(materialFromShares(again), ''),
        walletSeedBytes(words, ' Mixed Case '),
      );
    },
  );
  test('Frank root backups keep domain-separated payment derivation', () {
    final root = Uint8List.fromList(List.generate(32, (i) => i));
    final shares = exportRecoveryShares(
      format: RecoverySecretFormat.root,
      secret: root,
      threshold: 2,
      shareCount: 3,
      randomBytes: random,
    );
    final material = materialFromShares(shares);
    expect(walletSeedBytes(material, ''), deriveFrankPaymentSeed(root));
    final again = backupWalletMaterial(material, '', randomBytes: random);
    expect(recoverFrankBackup(again).format, RecoverySecretFormat.root);
  });
  test(
    'invalid typed material propagates an error instead of hanging an isolate',
    () async {
      await expectLater(
        Keys.construct(
          'vase-frank-root-v1:00',
        ).timeout(const Duration(seconds: 5)),
        throwsA(isA<FormatException>()),
      );
    },
  );
  test(
    'failed construction preserves current wallet and writes nothing',
    () async {
      final storage = legacy();
      var fail = false;
      final wallet = model(
        storage,
        factory: (_, _) async {
          if (fail) throw StateError('derivation failure');
          return TestWallet();
        },
      );
      await wallet.initializeModel();
      final previous = wallet.wallet;
      fail = true;
      await expectLater(wallet.setSeed(otherWords), throwsStateError);
      expect(wallet.wallet, same(previous));
      expect(wallet.seed, words);
      expect(wallet.initialized, isTrue);
      expect(storage.writes, isEmpty);
    },
  );
  test(
    'failed authoritative write preserves current wallet and legacy keys',
    () async {
      final storage = legacy();
      final wallet = model(storage);
      await wallet.initializeModel();
      final previous = wallet.wallet;
      storage.failWrites = true;
      await expectLater(wallet.setSeed(otherWords), throwsStateError);
      expect(wallet.wallet, same(previous));
      expect(wallet.seed, words);
      expect(storage.values[STORAGE_SEED_KEY], words);
      expect(storage.values.containsKey(walletMaterialStorageKey), isFalse);
    },
  );
  test(
    'successful restore persists one record and restarts with exact passphrase',
    () async {
      final storage = legacy();
      final wallet = model(storage);
      await wallet.initializeModel();
      await wallet.setSeed(otherWords, password: 'Case and spaces ');
      expect(storage.writes, [walletMaterialStorageKey]);
      expect(
        storage.values[STORAGE_SEED_KEY],
        words,
      ); // Existing legacy data stays intact.
      String? seenSeed, seenPassword;
      final restarted = model(
        storage,
        factory: (seed, password) async {
          seenSeed = seed;
          seenPassword = password;
          return TestWallet();
        },
      );
      await restarted.initializeModel();
      expect(seenSeed, otherWords);
      expect(seenPassword, 'Case and spaces ');
      expect(restarted.initialized, isTrue);
    },
  );
  test(
    'bad authoritative record never falls back to an older wallet',
    () async {
      final storage = legacy()
        ..values[walletMaterialStorageKey] = '{"version":99}';
      var calls = 0;
      final wallet = model(
        storage,
        factory: (_, _) async {
          calls++;
          return TestWallet();
        },
      );
      await wallet.initializeModel();
      expect(calls, 0);
      expect(wallet.initialized, isFalse);
      expect(storage.writes, isEmpty);
    },
  );
  test(
    'in-flight lifecycle persistence cannot overwrite a later restoration',
    () async {
      final storage = legacy();
      final wallet = model(storage);
      await wallet.initializeModel();
      final gate = Completer<void>();
      storage.gate = gate;
      final oldWrite = wallet.writeToDisk();
      final restore = wallet.setSeed(otherWords, password: 'New');
      await Future<void>.delayed(Duration.zero);
      gate.complete();
      await Future.wait([oldWrite, restore]);
      final saved = decodeWalletMaterial(
        storage.values[walletMaterialStorageKey]!,
      );
      expect(saved.material, otherWords);
      expect(saved.passphrase, 'New');
    },
  );
  test(
    'parallel restoration is rejected and old balance events cannot switch sessions',
    () async {
      final storage = legacy();
      final gate = Completer<Wallet>();
      var calls = 0;
      final wallet = model(
        storage,
        factory: (_, _) async => ++calls == 1 ? TestWallet() : gate.future,
      );
      await wallet.initializeModel();
      final old = wallet.wallet!;
      final pending = wallet.setSeed(otherWords);
      await expectLater(wallet.setSeed(words), throwsStateError);
      gate.complete(TestWallet());
      await pending;
      final newBalance = wallet.balance;
      old.balanceUpdateHandler!(WalletBalance(balance: BigInt.from(999)));
      expect(wallet.balance, same(newBalance));
      expect(calls, 2);
    },
  );
}
