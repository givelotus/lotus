import 'dart:io';
import 'dart:convert';
import 'dart:typed_data';

import 'package:hex/hex.dart';
import 'package:lotus_dart/src/multichain/curve.dart';
import 'package:lotus_dart/signature.dart';
import 'package:test/test.dart';

Uint8List hex(String value) => Uint8List.fromList(HEX.decode(value));
Uint8List scalar(int n) => Uint8List(32)..[31] = n;
const generator =
    '0279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798';

void main() {
  test('Nakamoto curve APIs intentionally lift x-only keys with even Y', () {
    final sec = hex(generator);
    final xOnly = sec.sublist(1);
    final digest = scalar(23);
    final signature = signEcdsa(digest, scalar(1));
    // Independently confirmed against Nakamoto nobleBackend.verifyEcdsa/ecdh.
    expect(verifyEcdsa(signature, digest, xOnly), isTrue);
    expect(ecdh(scalar(1), xOnly), sec);
    expect(ecdh(scalar(2), xOnly), ecdh(scalar(2), sec));
    // Address/HD boundary validation remains SEC1-only unless explicitly opted in.
    expect(() => validatePublicKey(xOnly), throwsA(isA<CurveException>()));
    validatePublicKey(xOnly, allowXOnly: true);
  });
  test(
    'Public SEC1 validation rejects noncanonical coordinates and off-curve points',
    () {
      final g = hex(generator);
      validatePublicKey(g);
      expect(
        () => validatePublicKey(g.sublist(1)),
        throwsA(isA<CurveException>()),
      );
      validatePublicKey(g.sublist(1), allowXOnly: true);
      final field =
          'fffffffffffffffffffffffffffffffffffffffffffffffffffffffefffffc2f';
      expect(
        () => validatePublicKey(hex('02$field')),
        throwsA(
          isA<CurveException>().having(
            (e) => e.code,
            'code',
            CurveErrorCode.pointInvalid,
          ),
        ),
      );
      expect(
        () => validatePublicKey(hex('04$field${'00' * 32}')),
        throwsA(isA<CurveException>()),
      );
      expect(
        () => validatePublicKey(Uint8List.fromList([4, ...List.filled(64, 0)])),
        throwsA(isA<CurveException>()),
      );
      final hybrid = Uint8List.fromList([6, ...List.filled(64, 0)]);
      expect(() => validatePublicKey(hybrid), throwsA(isA<CurveException>()));
    },
  );
  test('Nakamoto independent raw ECDH and key-tweak fixtures', () {
    final fixture =
        jsonDecode(
              File('test/fixtures/nakamoto-parity.json').readAsStringSync(),
            )
            as Map<String, dynamic>;
    final curve = fixture['curve'] as Map<String, dynamic>;
    for (final entry in curve['ecdh'] as List) {
      expect(
        ecdh(hex(entry['privateKeyHex']), hex(entry['peerPublicKeyHex'])),
        hex(entry['sharedCompressedHex']),
      );
    }
    const errors = {
      'scalar-out-of-range': CurveErrorCode.scalarOutOfRange,
      'point-at-infinity': CurveErrorCode.pointAtInfinity,
    };
    for (final entry in curve['tweaks'] as List) {
      final tweak = hex(entry['tweakHex']);
      for (final kind in ['private', 'public']) {
        final expected = entry['${kind}Result'] as Map;
        Uint8List operation() => kind == 'private'
            ? tweakAddPrivateKey(hex(entry['privateKeyHex']), tweak)
            : tweakAddPublicKey(hex(entry['publicKeyHex']), tweak);
        if (expected['ok'] == true) {
          expect(operation(), hex(expected['hex']));
        } else {
          expect(
            operation,
            throwsA(
              isA<CurveException>().having(
                (e) => e.code,
                'code',
                errors[expected['error']],
              ),
            ),
          );
        }
      }
    }
  });
  test('Nakamoto independent deterministic DER fixtures', () {
    final fixture =
        jsonDecode(
              File('test/fixtures/nakamoto-parity.json').readAsStringSync(),
            )
            as Map<String, dynamic>;
    final secret = hex(fixture['inputs']['privateKeyHex'] as String);
    final public = hex(fixture['inputs']['publicKeyHex'] as String);
    var count = 0;
    for (final transaction in fixture['transactions'] as List) {
      for (final sighash in transaction['sighashes'] as List) {
        final digest = hex(sighash['digestHex'] as String);
        final expected = hex(sighash['signatureDerHex'] as String);
        expect(signEcdsa(digest, secret), expected);
        expect(verifyEcdsa(expected, digest, public), isTrue);
        count++;
      }
    }
    expect(count, greaterThanOrEqualTo(78));
  });
  // Unmodified official Bitcoin BIPs repository vectors, including messages
  // of sizes 0, 1, 17 and 100 bytes and all invalid verification cases.
  // https://github.com/bitcoin/bips/blob/master/bip-0340/test-vectors.csv
  final rows = File(
    'test/fixtures/bip340-test-vectors.csv',
  ).readAsLinesSync().skip(1);
  for (final row in rows) {
    final columns = row.split(',');
    test('Official BIP340 vector ${columns[0]} verify', () {
      expect(
        verifySchnorrBip340(hex(columns[5]), hex(columns[4]), hex(columns[2])),
        columns[6] == 'TRUE',
      );
    });
    if (columns[1].isNotEmpty) {
      test('Official BIP340 vector ${columns[0]} sign exactly', () {
        expect(
          signSchnorrBip340(
            hex(columns[4]),
            hex(columns[1]),
            auxRand: hex(columns[3]),
          ),
          hex(columns[5]),
        );
      });
    }
  }
  test('ECDSA deterministic strict low-S DER with mutation rejection', () {
    final digest = scalar(23);
    final signature = signEcdsa(digest, scalar(1));
    expect(signEcdsa(digest, scalar(1)), signature);
    expect(verifyEcdsa(signature, digest, hex(generator)), isTrue);
    expect(verifyEcdsa(signature, scalar(24), hex(generator)), isFalse);
    final parsed = BCHSignature.fromDER(HEX.encode(signature));
    final n = BigInt.parse(
      'fffffffffffffffffffffffffffffffebaaedce6af48a03bbfd25e8cd0364141',
      radix: 16,
    );
    final high = Uint8List.fromList(
      BCHSignature.fromECParams(parsed.r!, n - parsed.s!).toDER()!,
    );
    expect(
      () => verifyEcdsa(high, digest, hex(generator)),
      throwsA(
        isA<CurveException>().having(
          (e) => e.code,
          'code',
          CurveErrorCode.highS,
        ),
      ),
    );
    expect(
      () => verifyEcdsa(Uint8List(1), digest, hex(generator)),
      throwsA(isA<CurveException>()),
    );
  });
  test('ECDH raw compressed point is symmetric and tweak paths agree', () {
    final g = hex(generator);
    final public2 = tweakAddPublicKey(g, scalar(1));
    final public3 = tweakAddPublicKey(g, scalar(2));
    expect(ecdh(scalar(2), public3), ecdh(scalar(3), public2));
    expect(ecdh(scalar(1), public2), public2);
    expect(tweakAddPrivateKey(scalar(1), scalar(2)), scalar(3));
    expect(tweakAddPublicKey(g.sublist(1), scalar(2)), public3);
  });
  test('Reject scalar boundaries, infinity, malformed/off-curve keys', () {
    final n = BigInt.parse(
      'fffffffffffffffffffffffffffffffebaaedce6af48a03bbfd25e8cd0364141',
      radix: 16,
    );
    final negateOne = hex((n - BigInt.one).toRadixString(16));
    expect(
      () => tweakAddPrivateKey(scalar(1), negateOne),
      throwsA(isA<CurveException>()),
    );
    expect(
      () => tweakAddPublicKey(hex(generator), negateOne),
      throwsA(
        isA<CurveException>().having(
          (e) => e.code,
          'code',
          CurveErrorCode.pointAtInfinity,
        ),
      ),
    );
    expect(
      () => signEcdsa(scalar(1), Uint8List(32)),
      throwsA(isA<CurveException>()),
    );
    expect(
      () => signEcdsa(Uint8List(31), scalar(1)),
      throwsA(isA<CurveException>()),
    );
    expect(
      () => ecdh(scalar(1), Uint8List(33)),
      throwsA(isA<CurveException>()),
    );
    expect(
      () => ecdh(scalar(1), Uint8List.fromList([4, ...List.filled(64, 0)])),
      throwsA(isA<CurveException>()),
    );
    expect(
      () => signSchnorrBip340(scalar(1), scalar(1), auxRand: Uint8List(31)),
      throwsA(isA<CurveException>()),
    );
  });
}
