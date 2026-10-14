import 'dart:convert';
import 'dart:typed_data';
import 'package:pointycastle/export.dart';
import '../../encoding/base58check.dart' as base58;
import '../../encoding/utils.dart' as hashes;
import 'chains.dart';
import 'curve.dart' show validatePublicKey, CurveException;
import 'keys.dart';

/// Strict BIP32 node. No implicit chain or coin-type selection.
class ChainHDKey {
  static final _curve = ECDomainParameters('secp256k1');
  final ChainKey? key;
  final Uint8List _publicKey, _chainCode, _parentFingerprint;
  final int depth, childIndex;
  ChainHDKey._(
    this.key,
    List<int> publicKey,
    List<int> chainCode,
    List<int> parentFingerprint,
    this.depth,
    this.childIndex,
  ) : _publicKey = Uint8List.fromList(publicKey),
      _chainCode = Uint8List.fromList(chainCode),
      _parentFingerprint = Uint8List.fromList(parentFingerprint);
  factory ChainHDKey.fromSeed(Uint8List seed) {
    if (seed.length < 16 || seed.length > 64) {
      throw FormatException('BIP32 seed must be 16–64 bytes');
    }
    final mac = _hmac(utf8.encode('Bitcoin seed'), seed);
    final key = ChainKey.fromBytes(Uint8List.fromList(mac.sublist(0, 32)));
    return ChainHDKey._(
      key,
      key.publicKey,
      mac.sublist(32),
      List.filled(4, 0),
      0,
      0,
    );
  }
  factory ChainHDKey.parse(String text, {required ChainDescriptor chain}) {
    final body = base58.decodeChecked(text);
    if (body.length != 78) {
      throw FormatException('BIP32 payload must be 78 bytes');
    }
    final version = _read32(body, 0);
    final isPrivate = version == chain.hdPrivateVersion;
    if (!isPrivate && version != chain.hdPublicVersion) {
      throw FormatException('BIP32 network version mismatch');
    }
    final depth = body[4], index = _read32(body, 9);
    final fp = body.sublist(5, 9);
    if (depth == 0 && (index != 0 || fp.any((b) => b != 0))) {
      throw FormatException('Invalid root metadata');
    }
    ChainKey? key;
    late Uint8List pub;
    if (isPrivate) {
      if (body[45] != 0) throw FormatException('Invalid private BIP32 prefix');
      key = ChainKey.fromBytes(Uint8List.fromList(body.sublist(46)));
      pub = key.publicKey;
    } else {
      pub = Uint8List.fromList(body.sublist(45));
      if (pub.first != 2 && pub.first != 3) {
        throw FormatException('Invalid BIP32 public key marker');
      }
      try {
        validatePublicKey(pub);
      } on CurveException catch (error) {
        throw FormatException('Invalid BIP32 public key: ${error.message}');
      }
    }
    return ChainHDKey._(key, pub, body.sublist(13, 45), fp, depth, index);
  }
  Uint8List get publicKey => Uint8List.fromList(_publicKey);
  Uint8List get chainCode => Uint8List.fromList(_chainCode);
  Uint8List get parentFingerprint => Uint8List.fromList(_parentFingerprint);
  ChainHDKey neuter() => ChainHDKey._(
    null,
    _publicKey,
    _chainCode,
    _parentFingerprint,
    depth,
    childIndex,
  );
  ChainHDKey derive(int index) {
    if (index < 0 || index > 0xffffffff || depth >= 255) {
      throw RangeError('BIP32 index/depth out of range');
    }
    if (key == null && index >= 0x80000000) {
      throw StateError('Cannot derive hardened public child');
    }
    final data = [
      if (index >= 0x80000000) ...[0, ...key!.secretBytes] else ..._publicKey,
      ..._ser32(index),
    ];
    final mac = _hmac(_chainCode, data);
    final tweak = _big(mac.sublist(0, 32));
    if (tweak >= _curve.n) throw StateError('Invalid BIP32 child');
    ChainKey? childKey;
    late Uint8List pub;
    if (key != null) {
      final scalar = (_big(key!.secretBytes) + tweak) % _curve.n;
      if (scalar == BigInt.zero) throw StateError('Invalid BIP32 child');
      childKey = ChainKey.fromBytes(_bytes32(scalar));
      pub = childKey.publicKey;
    } else {
      final parent = _curve.curve.decodePoint(_publicKey)!;
      final point = tweak == BigInt.zero
          ? parent
          : (parent + (_curve.G * tweak))!;
      if (point.isInfinity) throw StateError('Invalid BIP32 child');
      pub = Uint8List.fromList(point.getEncoded(true));
    }
    return ChainHDKey._(
      childKey,
      pub,
      mac.sublist(32),
      hashes.hash160(_publicKey).take(4).toList(),
      depth + 1,
      index,
    );
  }

  ChainHDKey derivePath(String path) {
    final parts = path.split('/');
    if (parts.first != 'm' && parts.first != 'M') {
      throw FormatException('BIP32 path must begin m/M');
    }
    var node = this;
    for (final step in parts.skip(1)) {
      if (!RegExp(r"^(0|[1-9][0-9]*)'?$").hasMatch(step)) {
        throw FormatException('Invalid BIP32 path');
      }
      final hardened = step.endsWith("'");
      final index = int.tryParse(
        hardened ? step.substring(0, step.length - 1) : step,
      );
      if (index == null || index > 0x7fffffff) {
        throw FormatException('Invalid BIP32 path index');
      }
      node = node.derive(index + (hardened ? 0x80000000 : 0));
    }
    return node;
  }

  ChainHDKey deriveBip44Account({required int coinType, int account = 0}) {
    if (coinType < 0 ||
        coinType > 0x7fffffff ||
        account < 0 ||
        account > 0x7fffffff) {
      throw RangeError('BIP44 coin/account out of range');
    }
    return derivePath("m/44'/$coinType'/$account'");
  }

  String serialize({required ChainDescriptor chain}) {
    final body = [
      ..._ser32(key == null ? chain.hdPublicVersion : chain.hdPrivateVersion),
      depth,
      ..._parentFingerprint,
      ..._ser32(childIndex),
      ..._chainCode,
      if (key == null) ..._publicKey else ...[0, ...key!.secretBytes],
    ];
    return base58.encode([...body, ...hashes.sha256Twice(body).take(4)]);
  }
}

Uint8List _hmac(List<int> key, List<int> data) =>
    (HMac(SHA512Digest(), 128)..init(KeyParameter(Uint8List.fromList(key))))
        .process(Uint8List.fromList(data));
BigInt _big(List<int> bytes) =>
    bytes.fold(BigInt.zero, (BigInt n, int b) => (n << 8) | BigInt.from(b));
Uint8List _bytes32(BigInt n) => Uint8List.fromList(
  List.generate(32, (i) => ((n >> (8 * (31 - i))) & BigInt.from(255)).toInt()),
);
List<int> _ser32(int n) => [
  (n >> 24) & 255,
  (n >> 16) & 255,
  (n >> 8) & 255,
  n & 255,
];
int _read32(List<int> b, int i) =>
    b[i] * 0x1000000 + b[i + 1] * 0x10000 + b[i + 2] * 256 + b[i + 3];
