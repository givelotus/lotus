import 'dart:async';
import 'dart:typed_data';

import 'package:hex/hex.dart';
import 'package:pool/pool.dart';
import 'package:vase/chronik-client/client.dart';
import 'package:vase/chronik-client/client.types.dart';
import 'package:lotus_dart/lotus.dart';
import 'package:vase/wallet/vault.dart';

import '../config/constants.dart';
import 'keys.dart';

class TransactionMetadata {
  List<VaultUtxo>? usedUtxos;
  Transaction? transaction;
  TransactionMetadata({this.usedUtxos, this.transaction});
}

class WalletBalance {
  BigInt? balance;
  dynamic error;

  WalletBalance({this.balance, this.error});
}

typedef BalanceUpdateHandler = void Function(WalletBalance result);

class Wallet {
  BalanceUpdateHandler? balanceUpdateHandler;
  Wallet(
    this.keys, {
    this.network,
    this.balanceUpdateHandler,
    required this.chronik,
  }) {
    _ws = chronik.ws(
      WsConfig(
        onConnect: () {
          startUtxoListenersChronik();
          _refreshFromNotification();
        },
        onMessage: (message) {
          if (message is MsgError) {
            updateBalance(WalletBalance(error: message.msg));
          } else {
            _refreshFromNotification();
          }
        },
        onError: (error) => updateBalance(WalletBalance(error: error)),
      ),
    );
  }

  bool _refreshing = false;
  bool _refreshAgain = false;

  Future<void> _refreshFromNotification() async {
    if (_refreshing) {
      _refreshAgain = true;
      return;
    }
    _refreshing = true;
    try {
      do {
        _refreshAgain = false;
        await updateUtxosChronik();
        refreshBalanceLocal();
      } while (_refreshAgain);
    } catch (error) {
      updateBalance(WalletBalance(error: error));
    } finally {
      _refreshing = false;
    }
  }

  Future<void> close() async => await _ws?.close();

  NetworkType? network;
  ChronikClient chronik;
  WsEndpoint? _ws;

  Keys keys;

  final Vault _vault = Vault([]);

  BigInt _balance = BigInt.zero;

  /// Gets the fees per byte.
  Future<BigInt> fetchFeePerByte() async {
    // TODO: Refresh from electrum.
    return BigInt.from(defaultFeePerByte);
  }

  void addressUpdated(result) async {
    // Extract script hash from result (of form [scripthash, status])
    final scriptHash = result[0];

    final keyInfo = keys.findKeyByScriptHash(
      Uint8List.fromList(HEX.decode(scriptHash)),
    );

    // Refresh UTXOs
    final unspentUtxos = await chronik
        .script(ScriptType.p2pkh, keyInfo.address!.pubkeyHash160!)
        .utxos();
    // Keep the previous balance if fetching fails.
    _vault.removeByKeyIndex(keyInfo.keyIndex);
    // TODO: Remove keyIndex concept. It is not particularly necessary;
    for (final unspent in unspentUtxos) {
      for (final uxto in unspent.utxos) {
        final spendable = VaultUtxo(
          VaultOutpoint(
            uxto.outpoint.txid,
            uxto.outpoint.outIdx,
            BigInt.from(int.parse(uxto.value)),
            uxto.blockHeight,
          ),
          keyInfo.keyIndex,
        );
        _vault.addUtxo(spendable);
      }
    }
    refreshBalanceLocal();
  }

  /// Start UTXO listeners.
  Future<void> startUtxoListenersChronik() async {
    for (final keyInfo in keys.keys!) {
      if (keyInfo.isDeprecated == true) {
        // We don't care about deprecated keys being listened to. Only load them
        // on startup. Listening to lots of keys is slow.
        continue;
      }
      final scriptPayload = keyInfo.address!.pubkeyHash160!;
      _ws?.subscribe(ScriptType.p2pkh, scriptPayload);
    }
  }

  /// Replace the vault only after every Chronik request succeeds.
  Future<void> updateUtxosChronik() async {
    final pool = Pool(5, timeout: const Duration(seconds: 60));

    final refreshedVault = Vault([]);
    final futures =
        keys.keys?.map((keyInfo) {
          final scriptPayload = keyInfo.address!.pubkeyHash160!;
          return pool.withResource(() async {
            final unspentUtxos = await chronik
                .script(ScriptType.p2pkh, scriptPayload)
                .utxos();
            // TODO: Remove keyIndex concept. It is not particularly necessary;
            for (final unspent in unspentUtxos) {
              for (final uxto in unspent.utxos) {
                final spendable = VaultUtxo(
                  VaultOutpoint(
                    uxto.outpoint.txid,
                    uxto.outpoint.outIdx,
                    BigInt.from(int.parse(uxto.value)),
                    uxto.blockHeight,
                  ),
                  keyInfo.keyIndex,
                );
                refreshedVault.addUtxo(spendable);
              }
            }
          });
        }) ??
        [];
    try {
      await Future.wait(futures);
      _vault.clear();
      _vault.addAllUtxos(refreshedVault.values.expand((utxos) => utxos));
    } finally {
      await pool.close();
    }
  }

  void updateBalance(WalletBalance update) {
    if (balanceUpdateHandler != null) {
      balanceUpdateHandler!(update);
    }
  }

  /// Use locally stored UTXOs to refresh balance.
  void refreshBalanceLocal() {
    _balance = _vault.calculateBalance();
    updateBalance(WalletBalance(balance: _balance));
  }

  void initialize() async {
    // Refresh atomically so a failed request preserves the previous vault.
    try {
      await updateUtxosChronik();
    } catch (err) {
      print(err);
      updateBalance(WalletBalance(balance: null, error: err));
      return;
    }
    refreshBalanceLocal();
  }

  BigInt balanceSatoshis() {
    return _balance;
  }

  Transaction _finalizeTransaction(
    Transaction transaction,
    BigInt feePerByte, {
    required List<BCHPrivateKey> signingKeys,
  }) {
    // Unsigned inputs have empty scriptSigs. Reserve the largest DER signature
    // (including sighash byte), both push bytes, and the actual public key size.
    final signedSize = _estimatedSignedSize(transaction, signingKeys);
    final changeAmount =
        transaction.inputAmount -
        transaction.outputAmount -
        (BigInt.from(outputSize + signedSize) * feePerByte);

    if (changeAmount > BigInt.from(512)) {
      final shuffledKeys = keys.keys!.sublist(0)..shuffle();
      final changeKeyInfo = shuffledKeys.firstWhere(
        (keyInfo) => keyInfo.isChange == true && !keyInfo.isDeprecated,
      );
      transaction = transaction.spendTo(changeKeyInfo.address, changeAmount);
    }

    // BIP69 sorting
    // transaction.sort();

    // TODO: Shuffle outputs here to obfuscate change.

    // Sign transaction
    signingKeys.asMap().forEach((index, privateKey) {
      transaction.signInput(
        index,
        privateKey,
        sighashType: SighashType.SIGHASH_ALL | SighashType.SIGHASH_FORKID,
      );
    });

    return transaction;
  }

  int _estimatedSignedSize(
    Transaction transaction,
    List<BCHPrivateKey> signingKeys,
  ) {
    return transaction.estimatedSize +
        signingKeys.fold<int>(
          0,
          (size, key) =>
              size + 75 + HEX.decode(key.publicKey.toString()).length,
        );
  }

  TransactionMetadata constructTransaction(
    List<TransactionOutput> outputs, {
    BigInt? feePerByte,
  }) {
    final effectiveFeePerByte = feePerByte ?? BigInt.from(defaultFeePerByte);
    if (effectiveFeePerByte < BigInt.zero ||
        outputs.isEmpty ||
        outputs.any((output) => output.satoshis <= BigInt.zero)) {
      throw ArgumentError(
        'Positive outputs and a nonnegative fee are required',
      );
    }
    var transaction = Transaction();

    var amountRequired = BigInt.from(0);
    // Add outputs
    for (final output in outputs) {
      amountRequired += output.satoshis;
      transaction.addOutput(output);
    }

    // Coin selection
    final signingKeys = <BCHPrivateKey>[];
    final usedUtxos = <VaultUtxo>[];

    final Iterable<List<VaultUtxo>> utxos = _vault.values;
    final allUtxos = utxos.expand((utxos) => utxos).toList();
    // Use oldest outpoints first
    allUtxos.sort(
      (VaultUtxo a, VaultUtxo b) =>
          (a.outpoint.height ?? -1).compareTo(b.outpoint.height ?? -1),
    );
    var satoshis = BigInt.from(0);

    for (final utxo in allUtxos) {
      final txnSize = _estimatedSignedSize(transaction, signingKeys);
      if (satoshis >=
          amountRequired + BigInt.from(txnSize) * effectiveFeePerByte) {
        break;
      }
      final privateKeyInfo = keys.keys![utxo.keyIndex!];
      final privateKey = privateKeyInfo.key;

      usedUtxos.add(utxo);
      signingKeys.add(privateKey);

      // Create input
      final unlockBuilder = P2PKHUnlockBuilder(privateKey.publicKey);
      final address = privateKey.toAddress(networkType: network);
      assert(
        address.toBase58() == privateKeyInfo.address!.toBase58(),
        'Key info corrupt for $address != ${privateKeyInfo.address}',
      );
      var output = TransactionOutput(scriptBuilder: P2PKHLockBuilder(address));
      output.satoshis = utxo.outpoint.amount;
      output.transactionId = utxo.outpoint.transactionId;
      output.outputIndex = utxo.outpoint.vout;
      transaction = transaction.spendFromOutput(
        output,
        NLOCKTIME_MAX_VALUE,
        scriptBuilder: unlockBuilder,
      );
      satoshis += utxo.outpoint.amount;
    }

    if (satoshis <
        amountRequired +
            BigInt.from(_estimatedSignedSize(transaction, signingKeys)) *
                effectiveFeePerByte) {
      throw Exception('Not enough funds to construct transaction');
    }

    // TODO: Need change UTXOs here so we can add them to the vault and spend from
    // them before confirmation
    transaction = _finalizeTransaction(
      transaction,
      effectiveFeePerByte,
      signingKeys: signingKeys,
    );

    // Do not reserve coins until construction and signing have both succeeded.
    for (final utxo in usedUtxos) {
      _vault.removeUtxo(utxo);
    }
    return TransactionMetadata(transaction: transaction, usedUtxos: usedUtxos);
  }

  Future<Transaction?> sendTransaction(
    Address recipientAddress,
    BigInt amount,
  ) async {
    final feePerByte = await fetchFeePerByte();
    final output = TransactionOutput(
      scriptBuilder: P2PKHLockBuilder(recipientAddress),
    );
    output.satoshis = amount;
    final txnMetadata = constructTransaction([output], feePerByte: feePerByte);
    try {
      final transactionHex = txnMetadata.transaction!.serialize();
      await chronik.broadcastTx(rawTx: transactionHex);
    } catch (err) {
      _vault.addAllUtxos(txnMetadata.usedUtxos!);
      print(err.toString());
      rethrow;
    } finally {
      refreshBalanceLocal();
    }

    return txnMetadata.transaction;
  }

  Future<void> updateSeedPhrase(String newSeed, [String password = '']) async {
    keys = await Keys.construct(newSeed, password);
    initialize();
  }
}
