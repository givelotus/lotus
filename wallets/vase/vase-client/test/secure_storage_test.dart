import 'package:flutter/services.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:vase/chronik-client/client.dart';
import 'package:vase/features/wallet/wallet_model.dart';
import 'package:vase/wallet/storage/secure_storage.dart';

class MemoryStorage extends FlutterSecureStorage {
  final Map<String, String> values;
  final String? failKey;
  final writes = <String>[];
  MemoryStorage(this.values, {this.failKey});

  @override
  Future<String?> read({
    required String key,
    AndroidOptions? aOptions,
    AppleOptions? iOptions,
    LinuxOptions? lOptions,
    WebOptions? webOptions,
    AppleOptions? mOptions,
    WindowsOptions? wOptions,
  }) async {
    if (key == failKey) throw PlatformException(code: 'migration_failed');
    return values[key];
  }

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
  }
}

void main() {
  test(
    'legacy storage namespaces stay stable and failures cannot reset keys',
    () {
      expect(walletSecureStorage.aOptions.toMap()['resetOnError'], 'false');
      expect(
        walletSecureStorage.aOptions.toMap()['migrateOnAlgorithmChange'],
        'true',
      );
      expect(walletSecureStorage.aOptions.toMap()['migrateWithBackup'], 'true');
      expect(
        walletSecureStorage.iOptions.toMap()['accountName'],
        'flutter_secure_storage_service',
      );
      expect(walletSecureStorage.iOptions.toMap()['accessibility'], 'unlocked');
      expect(walletSecureStorage.iOptions.toMap()['synchronizable'], 'false');
      expect(
        walletSecureStorage.mOptions.toMap()['usesDataProtectionKeychain'],
        'true',
      );
      expect(
        walletSecureStorage.wOptions.toMap()['useBackwardCompatibility'],
        'true',
      );
    },
  );

  for (final key in [
    storageBalanceKey,
    SCHEMA_VERSION_KEY,
    STORAGE_SEED_KEY,
    STORAGE_PASSWORD_KEY,
  ]) {
    test(
      'failed read of $key never generates or persists replacement keys',
      () async {
        final storage = MemoryStorage({}, failKey: key);
        var calls = 0;
        final model = WalletModel(
          ChronikClient('http://unused.invalid'),
          storage: storage,
          initialize: false,
          walletFactory: (seed, password) async {
            calls++;
            throw StateError('factory must not run');
          },
        );
        await model.initializeModel();
        await model.writeToDisk();
        expect(calls, 0);
        expect(model.initialized, isFalse);
        expect(model.wallet, isNull);
        expect(model.balance!.error, isA<StateError>());
        expect(storage.writes, isEmpty);
      },
    );
  }

  for (final key in [
    SCHEMA_VERSION_KEY,
    STORAGE_XPUB_KEY,
    STORAGE_PASSWORD_KEY,
    storageBalanceKey,
  ]) {
    test(
      'missing seed with existing $key marker cannot create another wallet',
      () async {
        final storage = MemoryStorage({
          key: key == storageBalanceKey ? '123' : 'existing',
        });
        var calls = 0;
        final model = WalletModel(
          ChronikClient('http://unused.invalid'),
          storage: storage,
          initialize: false,
          walletFactory: (seed, password) async {
            calls++;
            throw StateError('factory must not run');
          },
        );
        await model.initializeModel();
        await model.writeToDisk();
        expect(calls, 0);
        expect(storage.writes, isEmpty);
        expect(model.initialized, isFalse);
      },
    );
  }

  test('existing seed and password reach factory unchanged', () async {
    final storage = MemoryStorage({
      SCHEMA_VERSION_KEY: CURRENT_SCHEMA_VERSION,
      STORAGE_SEED_KEY: 'fixture seed',
      STORAGE_PASSWORD_KEY: 'fixture password',
    });
    final seen = <String?>[];
    final model = WalletModel(
      ChronikClient('http://unused.invalid'),
      storage: storage,
      initialize: false,
      walletFactory: (seed, password) async {
        seen.addAll([seed, password]);
        throw StateError('stop before creating a wallet');
      },
    );
    await model.initializeModel();
    expect(seen, ['fixture seed', 'fixture password']);
    expect(storage.writes, isEmpty);
  });

  test('successful empty reads permit a new mnemonic', () async {
    final storage = MemoryStorage({});
    String? createdSeed;
    final model = WalletModel(
      ChronikClient('http://unused.invalid'),
      storage: storage,
      initialize: false,
      walletFactory: (seed, password) async {
        createdSeed = seed;
        throw StateError('stop before creating a wallet');
      },
    );
    await model.initializeModel();
    expect(createdSeed!.split(' '), hasLength(12));
    expect(storage.writes, isEmpty);
  });
}
