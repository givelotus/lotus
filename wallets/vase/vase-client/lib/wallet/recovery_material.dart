import 'dart:convert';
import 'dart:math';
import 'dart:typed_data';
import 'package:lotus_dart/bip39/bip39.dart';
import 'package:lotus_dart/codex32.dart';

const _rootPrefix = 'vase-frank-root-v1:';
const _seedPrefix = 'vase-bip32-seed-v1:';

bool isMnemonicMaterial(String value) =>
    !value.startsWith(_rootPrefix) && !value.startsWith(_seedPrefix);

String _hex(Uint8List value) =>
    value.map((b) => b.toRadixString(16).padLeft(2, '0')).join();
Uint8List _unhex(String value, int length) {
  if (value.length != length * 2 || !RegExp(r'^[0-9a-f]+$').hasMatch(value)) {
    throw const FormatException('Invalid wallet recovery material');
  }
  return Uint8List.fromList([
    for (var i = 0; i < value.length; i += 2)
      int.parse(value.substring(i, i + 2), radix: 16),
  ]);
}

/// Existing mnemonic wallets keep their original BIP39 derivation unchanged.
Uint8List walletSeedBytes(String material, String passphrase) {
  if (material.startsWith(_rootPrefix)) {
    if (passphrase.isNotEmpty)
      throw const FormatException('Unexpected passphrase');
    final root = _unhex(material.substring(_rootPrefix.length), 32);
    try {
      return deriveFrankPaymentSeed(root);
    } finally {
      root.fillRange(0, root.length, 0);
    }
  }
  if (material.startsWith(_seedPrefix)) {
    if (passphrase.isNotEmpty)
      throw const FormatException('Unexpected passphrase');
    return _unhex(material.substring(_seedPrefix.length), 64);
  }
  // Do not normalize persisted phrases or passphrases. Import UI validates words.
  return Mnemonic().toSeed(material, passphrase);
}

String materialFromShares(List<String> shares) {
  final recovered = recoverFrankBackup(shares);
  try {
    return '${recovered.format == RecoverySecretFormat.root ? _rootPrefix : _seedPrefix}${_hex(recovered.bytes)}';
  } finally {
    recovered.destroy();
  }
}

Uint8List secureRecoveryRandom(int length) {
  final random = Random.secure();
  return Uint8List.fromList(List.generate(length, (_) => random.nextInt(256)));
}

List<String> backupWalletMaterial(
  String material,
  String passphrase, {
  int threshold = 2,
  int shareCount = 3,
  BackupRandomBytes randomBytes = secureRecoveryRandom,
}) {
  Uint8List secret;
  RecoverySecretFormat format;
  if (material.startsWith(_rootPrefix)) {
    secret = _unhex(material.substring(_rootPrefix.length), 32);
    format = RecoverySecretFormat.root;
  } else {
    secret = walletSeedBytes(material, passphrase);
    format = RecoverySecretFormat.historical;
  }
  try {
    return exportRecoveryShares(
      format: format,
      secret: secret,
      threshold: threshold,
      shareCount: shareCount,
      randomBytes: randomBytes,
    );
  } finally {
    secret.fillRange(0, secret.length, 0);
  }
}

String encodeWalletMaterial(String material, String passphrase) =>
    jsonEncode({'version': 1, 'material': material, 'passphrase': passphrase});

({String material, String passphrase}) decodeWalletMaterial(String encoded) {
  final value = jsonDecode(encoded);
  if (value is! Map ||
      value['version'] != 1 ||
      value['material'] is! String ||
      value['passphrase'] is! String ||
      (value['material'] as String).isEmpty) {
    throw const FormatException('Invalid stored wallet material');
  }
  return (
    material: value['material'] as String,
    passphrase: value['passphrase'] as String,
  );
}
