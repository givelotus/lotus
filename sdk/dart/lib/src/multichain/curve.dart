/// Browser-compatible secp256k1 helpers backed by PointyCastle.
/// Dart BigInt/PointyCastle operations do not provide constant-time guarantees.
/// These primitives do not implement Script, BCH Schnorr, or BIP374 DLEQ.
library;

import 'dart:convert';
import 'dart:typed_data';

import 'package:hex/hex.dart';
import 'package:pointycastle/export.dart';

import '../../privatekey.dart';
import '../../publickey.dart';
import '../../signature.dart';

/// Failures at the explicitly byte-oriented secp256k1 API boundary.
enum CurveErrorCode {
  badLength,
  scalarOutOfRange,
  pointInvalid,
  pointAtInfinity,
  highS,
  signatureInvalid,
}

class CurveException implements Exception {
  final CurveErrorCode code;
  final String message;
  const CurveException(this.code, this.message);
  @override
  String toString() => 'CurveException(${code.name}): $message';
}

final _domain = ECDomainParameters('secp256k1');
final _field = BigInt.parse(
  'fffffffffffffffffffffffffffffffffffffffffffffffffffffffefffffc2f',
  radix: 16,
);

void _length(Uint8List bytes, int length, String name) {
  if (bytes.length != length) {
    throw CurveException(
      CurveErrorCode.badLength,
      '$name must be $length bytes',
    );
  }
}

BigInt _integer(List<int> bytes) =>
    bytes.fold(BigInt.zero, (value, byte) => (value << 8) | BigInt.from(byte));

Uint8List _bytes(BigInt value) => Uint8List.fromList(
  List.generate(
    32,
    (index) => ((value >> (8 * (31 - index))) & BigInt.from(255)).toInt(),
  ),
);

BigInt _scalar(Uint8List bytes) {
  _length(bytes, 32, 'Scalar');
  final value = _integer(bytes);
  if (value <= BigInt.zero || value >= _domain.n) {
    throw const CurveException(
      CurveErrorCode.scalarOutOfRange,
      'Scalar must be in [1, n)',
    );
  }
  return value;
}

ECPoint _point(Uint8List bytes) {
  final Uint8List encoded;
  if (bytes.length == 32) {
    encoded = Uint8List.fromList([2, ...bytes]);
  } else if ((bytes.length == 33 && (bytes[0] == 2 || bytes[0] == 3)) ||
      (bytes.length == 65 && bytes[0] == 4)) {
    encoded = bytes;
  } else {
    throw const CurveException(
      CurveErrorCode.pointInvalid,
      'Expected SEC1 or x-only public key',
    );
  }
  if (_integer(encoded.sublist(1, 33)) >= _field ||
      (encoded.length == 65 && _integer(encoded.sublist(33)) >= _field)) {
    throw const CurveException(
      CurveErrorCode.pointInvalid,
      'Coordinate outside field',
    );
  }
  try {
    final point = _domain.curve.decodePoint(encoded);
    if (point == null || point.isInfinity) throw const FormatException();
    final x = point.x!.toBigInteger()!;
    final y = point.y!.toBigInteger()!;
    if ((y * y - x * x * x - BigInt.from(7)) % _field != BigInt.zero) {
      throw const FormatException();
    }
    return point;
  } catch (_) {
    throw const CurveException(
      CurveErrorCode.pointInvalid,
      'Point is not on secp256k1',
    );
  }
}

/// Validates canonical SEC1 encoding, field bounds and curve membership.
/// X-only keys are accepted only when explicitly requested; addresses and HD
/// keys must retain their SEC1 compression marker.
void validatePublicKey(Uint8List bytes, {bool allowXOnly = false}) {
  if (bytes.length != 33 &&
      bytes.length != 65 &&
      !(allowXOnly && bytes.length == 32)) {
    throw const CurveException(
      CurveErrorCode.badLength,
      'Expected 33/65-byte SEC1 key',
    );
  }
  _point(bytes);
}

Uint8List _compressed(ECPoint point) {
  if (point.isInfinity) {
    throw const CurveException(
      CurveErrorCode.pointAtInfinity,
      'Result is infinity',
    );
  }
  return point.getEncoded(true);
}

Uint8List _tagged(String tag, List<int> data) {
  final hash = SHA256Digest();
  final tagHash = hash.process(Uint8List.fromList(utf8.encode(tag)));
  return hash.process(Uint8List.fromList([...tagHash, ...tagHash, ...data]));
}

/// RFC6979 deterministic ECDSA over a 32-byte digest; strict DER, low-S.
/// No sighash byte is appended and no message hashing is performed.
Uint8List signEcdsa(Uint8List digest, Uint8List secret) {
  _length(digest, 32, 'Digest');
  final key = BCHPrivateKey.fromBigInt(_scalar(secret));
  final signature = BCHSignature.fromPrivateKey(key);
  signature.sign(HEX.encode(digest));
  return Uint8List.fromList(signature.toDER()!);
}

/// Rejects malformed DER/high-S explicitly; a different valid signature is false.
/// Like Nakamoto, a 32-byte x-only key is lifted with even Y; SEC1 also works.
bool verifyEcdsa(Uint8List signature, Uint8List digest, Uint8List publicKey) {
  _length(digest, 32, 'Digest');
  final point = _point(publicKey);
  if (!BCHSignature.isTxDER('${HEX.encode(signature)}01')) {
    throw const CurveException(
      CurveErrorCode.signatureInvalid,
      'Noncanonical DER',
    );
  }
  final parsed = BCHSignature.fromDER(
    HEX.encode(signature),
    publicKey: BCHPublicKey.fromPoint(point),
  );
  if (parsed.r! <= BigInt.zero ||
      parsed.r! >= _domain.n ||
      parsed.s! <= BigInt.zero ||
      parsed.s! >= _domain.n) {
    throw const CurveException(
      CurveErrorCode.signatureInvalid,
      'Signature scalar outside [1, n)',
    );
  }
  if (!parsed.hasLowS()) {
    throw const CurveException(CurveErrorCode.highS, 'ECDSA S must be low');
  }
  return parsed.verify(HEX.encode(digest));
}

/// BIP340 Schnorr, distinct from BCH/Lotus Schnorr. Message bytes are not hashed
/// automatically. Caller must supply 32 auxiliary bytes from a secure source;
/// explicit zero bytes are permitted for reproducible test vectors.
Uint8List signSchnorrBip340(
  Uint8List message,
  Uint8List secret, {
  required Uint8List auxRand,
}) {
  _length(auxRand, 32, 'Auxiliary randomness');
  final initial = _scalar(secret);
  final public = (_domain.G * initial)!;
  final d = public.y!.toBigInteger()!.isEven ? initial : _domain.n - initial;
  final mask = _tagged('BIP0340/aux', auxRand);
  final secretBytes = _bytes(d);
  final hidden = List.generate(32, (i) => secretBytes[i] ^ mask[i]);
  final publicX = _bytes(public.x!.toBigInteger()!);
  final nonce =
      _integer(_tagged('BIP0340/nonce', [...hidden, ...publicX, ...message])) %
      _domain.n;
  secretBytes.fillRange(0, secretBytes.length, 0);
  hidden.fillRange(0, hidden.length, 0);
  if (nonce == BigInt.zero) {
    throw const CurveException(
      CurveErrorCode.scalarOutOfRange,
      'BIP340 nonce is zero',
    );
  }
  final rPoint = (_domain.G * nonce)!;
  final k = rPoint.y!.toBigInteger()!.isEven ? nonce : _domain.n - nonce;
  final r = _bytes(rPoint.x!.toBigInteger()!);
  final e =
      _integer(_tagged('BIP0340/challenge', [...r, ...publicX, ...message])) %
      _domain.n;
  final signature = Uint8List.fromList([
    ...r,
    ..._bytes((k + e * d) % _domain.n),
  ]);
  if (!verifySchnorrBip340(signature, message, publicX)) {
    throw const CurveException(
      CurveErrorCode.signatureInvalid,
      'Schnorr self-check failed',
    );
  }
  return signature;
}

/// BIP340 verification uses exactly a 32-byte x-only public key. Invalid
/// signatures/points return false; invalid input lengths throw CurveException.
bool verifySchnorrBip340(
  Uint8List signature,
  Uint8List message,
  Uint8List publicKey,
) {
  _length(signature, 64, 'Signature');
  _length(publicKey, 32, 'X-only public key');
  ECPoint public;
  try {
    public = _point(publicKey);
  } on CurveException {
    return false;
  }
  final r = _integer(signature.sublist(0, 32));
  final s = _integer(signature.sublist(32));
  if (r >= _field || s >= _domain.n) return false;
  final e =
      _integer(
        _tagged('BIP0340/challenge', [
          ...signature.sublist(0, 32),
          ...publicKey,
          ...message,
        ]),
      ) %
      _domain.n;
  final result =
      ((_domain.G * s)! + (public * ((_domain.n - e) % _domain.n))!)!;
  return !result.isInfinity &&
      result.y!.toBigInteger()!.isEven &&
      result.x!.toBigInteger() == r;
}

/// Compressed SEC1 shared point; deliberately no implicit hash or KDF.
/// Like Nakamoto, a 32-byte peer key is lifted with even Y before multiplication.
Uint8List ecdh(Uint8List secret, Uint8List publicKey) =>
    _compressed((_point(publicKey) * _scalar(secret))!);

/// (secret + tweak) mod n. Like Nakamoto, zero tweaks are rejected.
Uint8List tweakAddPrivateKey(Uint8List secret, Uint8List tweak) {
  final sum = (_scalar(secret) + _scalar(tweak)) % _domain.n;
  if (sum == BigInt.zero) {
    throw const CurveException(
      CurveErrorCode.scalarOutOfRange,
      'Tweaked key is zero',
    );
  }
  return _bytes(sum);
}

/// P + tweak*G, encoded compressed. X-only P is lifted with even Y.
Uint8List tweakAddPublicKey(Uint8List publicKey, Uint8List tweak) =>
    _compressed((_point(publicKey) + (_domain.G * _scalar(tweak))!)!);
