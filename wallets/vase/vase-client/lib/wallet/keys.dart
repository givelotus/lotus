import 'dart:typed_data';
import 'package:flutter/foundation.dart' show compute;
import 'package:collection/collection.dart';
import 'package:pointycastle/digests/sha256.dart';

import 'package:lotus_dart/lotus.dart';
import 'package:vase/config/constants.dart' as constants;
import 'package:vase/wallet/recovery_material.dart';

Uint8List calculateScriptHash(Address? address) {
  final p2pkhBuilder = P2PKHLockBuilder(address);
  final script = p2pkhBuilder.getScriptPubkey();
  final scriptHash = SHA256Digest().process(script.buffer).toList();
  return Uint8List.fromList(scriptHash.reversed.toList());
}

typedef KeyDerivationInput = ({
  String material,
  String passphrase,
  NetworkType network,
});

class KeyInfo {
  BCHPrivateKey key;
  Address? address;
  Uint8List? scriptHash;
  bool? isChange;
  bool isDeprecated;
  int? keyIndex;

  KeyInfo({
    required this.key,
    this.isChange = false,
    this.isDeprecated = false,
    this.keyIndex,
    NetworkType network = constants.network,
  }) {
    address = key.toAddress(networkType: network);
    scriptHash = calculateScriptHash(address);
  }
}

List<KeyInfo>? constructChildKeys({
  required HDPrivateKey rootKey,
  required int childKeyCount,
  NetworkType network = constants.network,
}) {
  // Default electron cash path

  final generateKeys =
      (
        Iterable<KeyInfo> priorList,
        generationRootKey,
        bool isChange,
        bool isDeprecated,
        int number,
      ) => priorList.followedBy(
        List<KeyInfo>.generate(
          number,
          (index) => KeyInfo(
            // TODO: Remove this keyIndex crap. it makes it very hard to handle
            // finding various other values because we have this unnecessary
            // surrogate key
            keyIndex: index + priorList.length as int?,
            key: generationRootKey.deriveChildNumber(index).privateKey,
            isChange: isChange,
            isDeprecated: isDeprecated,
            network: network,
          ),
        ),
      );

  final btcParentKey = rootKey.deriveChildKey("m/44'/0'");
  final bchParentKey = rootKey.deriveChildKey("m/44'/145'");
  final ecashParentKey = rootKey.deriveChildKey("m/44'/899'");
  final lotusParentKey = rootKey.deriveChildKey("m/44'/10605'");

  final withLotusDerivationKeys = generateKeys(
    <KeyInfo>[],
    lotusParentKey.deriveChildNumber(0, hardened: true).deriveChildNumber(0),
    false,
    true,
    childKeyCount,
  );

  // Marking only the first key as not deprecated
  withLotusDerivationKeys.first.isDeprecated = false;

  final withLotusChangeKeys = generateKeys(
    withLotusDerivationKeys,
    lotusParentKey.deriveChildNumber(0, hardened: true).deriveChildNumber(1),
    true,
    false,
    childKeyCount,
  );
  // Deprecated keys were incorrectly missing part of the deriviation path. We now
  // include them only so that they load up the balance, but won't be used by the
  // code elsewhere for change or receiving. We need to generally clean up this
  // keystore stuff, as all the state is a bit annoying to deal with elsewhere.
  var allKeys = withLotusChangeKeys;
  for (final parentKey in [btcParentKey, bchParentKey, ecashParentKey]) {
    allKeys = generateKeys(
      allKeys,
      parentKey.deriveChildNumber(0, hardened: true).deriveChildNumber(0),
      false,
      true,
      childKeyCount,
    );
    allKeys = generateKeys(
      allKeys,
      parentKey.deriveChildNumber(0, hardened: true).deriveChildNumber(1),
      true,
      true,
      childKeyCount,
    );
  }

  return allKeys.toList();
}

// compute propagates derivation errors and uses the same function on web/native.
Keys _constructKeys(KeyDerivationInput input) {
  final seedBytes = walletSeedBytes(input.material, input.passphrase);
  try {
    final seedHex = seedBytes
        .map((b) => b.toRadixString(16).padLeft(2, '0'))
        .join();
    final rootKey = HDPrivateKey.fromSeed(seedHex, input.network);
    final childKeys = constructChildKeys(
      rootKey: rootKey,
      childKeyCount: constants.defaultNumberOfChildKeys,
      network: input.network,
    );
    return Keys(
      input.material,
      input.passphrase,
      rootKey,
      childKeys,
      network: input.network,
    );
  } finally {
    seedBytes.fillRange(0, seedBytes.length, 0);
  }
}

class Keys {
  NetworkType network;
  HDPrivateKey rootKey;
  String? seed;
  String? password;
  List<KeyInfo>? keys;
  int totalKeys;

  Keys(
    this.seed,
    this.password,
    this.rootKey,
    this.keys, {
    this.network = constants.network,
    this.totalKeys = constants.defaultNumberOfChildKeys,
  });

  /// Find the index of a script hash.
  KeyInfo findKeyByScriptHash(Uint8List scriptHash) {
    final keyInfo = keys!.firstWhere(
      (keyInfo) => ListEquality().equals(scriptHash, keyInfo.scriptHash),
    );
    return keyInfo;
  }

  static Future<Keys> construct(String? seed, [String? password = '']) {
    if (seed == null) throw ArgumentError('Wallet material is unavailable');
    return compute(_constructKeys, (
      material: seed,
      passphrase: password ?? '',
      network: constants.network,
    ));
  }
}
