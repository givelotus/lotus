import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter/services.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:vase/chronik-client/client.dart';
import 'package:vase/config/constants.dart';
import 'package:lotus_dart/lotus.dart';
import 'package:vase/wallet/keys.dart';
import 'package:vase/wallet/wallet.dart';
import 'package:vase/wallet/storage/secure_storage.dart';

const SCHEMA_VERSION_KEY = 'schema_version';

const CURRENT_SCHEMA_VERSION = '3';

const STORAGE_SEED_KEY = 'seed';
const STORAGE_PASSWORD_KEY = 'password';
const STORAGE_XPUB_KEY = 'rootKey';
const storageBalanceKey = 'balance';

/// Generate a fresh wallet.
Future<Wallet> generateNewWallet(
  String? seed,
  ChronikClient chronik, {
  NetworkType network = network,
  String? password = '',
}) async {
  final keys = await Keys.construct(seed, password);

  return Wallet(keys, network: network, chronik: chronik);
}

class WalletModel with ChangeNotifier {
  Wallet? _wallet;
  bool _initialized = false;
  String? _seed = '';
  String? _password = '';
  // Internally use a ValueNotifier here, as we don't want the entire wallet
  // to refresh when this field is updated.
  // We should probably introduce a secondary model of some sort.
  WalletBalance? balance;
  final FlutterSecureStorage _storage;
  final ChronikClient chronik;

  final Future<Wallet> Function(String?, String?) _walletFactory;

  WalletModel(
    this.chronik, {
    FlutterSecureStorage? storage,
    Future<Wallet> Function(String?, String?)? walletFactory,
    bool initialize = true,
  }) : _storage = storage ?? walletSecureStorage,
       _walletFactory =
           walletFactory ??
           ((seed, password) =>
               generateNewWallet(seed, chronik, password: password)),
       balance = WalletBalance() {
    if (initialize) initializeModel();
  }

  Future<void> initializeModel() async {
    try {
      final storedBalance = await _storage.read(key: storageBalanceKey);
      if (storedBalance != null) {
        balance = WalletBalance(balance: BigInt.tryParse(storedBalance));
        notifyListeners();
      }
      final readSucceed = await readFromDisk();
      if (!readSucceed) {
        _seed = await readSeedFromDisk();
        _password = await readPasswordFromDisk();
        if (_seed == null || _seed!.isEmpty) {
          final hasStoredWallet =
              await readSchemaVersion() != null ||
              await _storage.read(key: STORAGE_XPUB_KEY) != null ||
              _password != null ||
              storedBalance != null;
          if (hasStoredWallet) {
            throw StateError('Stored wallet seed is unavailable');
          }
          _seed = Mnemonic().generateMnemonic();
        }
        _wallet = await _walletFactory(_seed, _password);
      }
      wallet!.balanceUpdateHandler = (balance) async {
        this.balance = balance;
        notifyListeners();
        if (balance.balance != null) {
          await _storage.write(
            key: storageBalanceKey,
            value: balance.balance.toString(),
          );
        }
      };
      wallet!.initialize();
      initialized = true;
    } catch (error, stack) {
      assert(() {
        debugPrint(
          'Wallet initialization failed: ${error.runtimeType}'
          '${error is PlatformException ? ' (platform code ${error.code})' : ''}',
        );
        debugPrintStack(stackTrace: stack, maxFrames: 6);
        return true;
      }());
      // A failed read is not proof of an empty wallet. Do not generate or write
      // replacement keys, and do not expose native error text containing data.
      _initialized = false;
      balance = WalletBalance(
        error: StateError(
          'Unable to open stored wallet; existing keys were not replaced.',
        ),
      );
      notifyListeners();
    }
  }

  void resetBalance() {
    balance = WalletBalance();
    notifyListeners();
  }

  Future<void> updateWallet() async {
    wallet!.initialize();
  }

  set initialized(bool newValue) {
    _initialized = newValue;
    notifyListeners();
  }

  String? get seed => _seed;
  String? get password => _password;

  void setSeed(String newValue, {String password = ''}) {
    _seed = newValue;
    _password = password;
    balance = null;
    _initialized = false;
    notifyListeners();
    generateNewWallet(_seed, chronik, password: _password).then((newWallet) {
      _wallet = newWallet;
      wallet!.balanceUpdateHandler = (balance) {
        this.balance = balance;
        notifyListeners();
      };
      wallet!.initialize();
      initialized = true;
    });
  }

  bool get initialized => _initialized;

  Wallet? get wallet => _wallet;

  set wallet(Wallet? newValue) {
    _wallet = newValue;
    notifyListeners();
  }

  Future<String?> readSchemaVersion() {
    return _storage.read(key: SCHEMA_VERSION_KEY);
  }

  Future<void> writeSchemaVersion() {
    return _storage.write(
      key: SCHEMA_VERSION_KEY,
      value: CURRENT_SCHEMA_VERSION,
    );
  }

  Future<void> writeToDisk() async {
    if (!initialized || wallet == null) return;
    // Persist schema version
    await writeSchemaVersion();

    // Persist keys
    // TODO: keys.keys is silly naming
    await writeKeysToDisk();
  }

  Future<bool> readFromDisk() async {
    final schemaVersion = await readSchemaVersion();
    if (schemaVersion != CURRENT_SCHEMA_VERSION) return false;
    _seed = await readSeedFromDisk();
    _password = await readPasswordFromDisk();
    if (_seed == null || _seed!.isEmpty) {
      throw StateError('Stored wallet seed is unavailable');
    }
    _wallet = await _walletFactory(_seed, _password);
    return true;
  }

  Future<void> writeKeysToDisk() async {
    // Write private keys
    try {
      // Persist seed
      await _storage.write(key: STORAGE_SEED_KEY, value: seed);

      // Persist password
      await _storage.write(key: STORAGE_PASSWORD_KEY, value: password);

      // Persist XPub
      await _storage.write(
        key: STORAGE_XPUB_KEY,
        value: wallet!.keys.rootKey.toString(),
      );

      // TODO: Write metadata
    } catch (err) {
      print(err);
    }
  }

  Future<String?> readSeedFromDisk() async {
    // TODO: Read metadata

    // Read seed
    return _storage.read(key: STORAGE_SEED_KEY);
  }

  Future<String?> readPasswordFromDisk() async {
    // TODO: Read metadata

    // Read seed
    return _storage.read(key: STORAGE_PASSWORD_KEY);
  }

  Future<Keys> readKeysFromDisk() async {
    // TODO: Read metadata

    // Read seed
    _seed = await readSeedFromDisk();
    _password = await readPasswordFromDisk();

    return Keys.construct(_seed, _password);
  }
}
