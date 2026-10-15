import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';
import 'package:lotus_dart/codex32.dart';
import 'package:lotus_dart/bip39/bip39.dart';
import 'package:test/test.dart';

Uint8List unhex(String v) => Uint8List.fromList([
  for (var i = 0; i < v.length; i += 2)
    int.parse(v.substring(i, i + 2), radix: 16),
]);
Uint8List random(int length) =>
    Uint8List.fromList(List.generate(length, (i) => (i * 31 + 7) & 255));
Matcher code(String expected) =>
    isA<Codex32Exception>().having((e) => e.code, 'code', expected);
final fixture =
    jsonDecode(File('test/fixtures/codex32-frank.json').readAsStringSync())
        as Map<String, dynamic>;

void main() {
  for (final item in fixture['cases'] as List) {
    final secret = unhex(item['secret']);
    final threshold = item['threshold'] as int;
    test(
      'Frank standard parity ${secret.length} bytes $threshold-of-${threshold + 1}',
      () {
        expect(
          encodeCodex32(threshold: 0, identifier: 'test', secret: secret),
          item['encoded'],
        );
        expect(decodeCodex32(item['encoded']).seed, secret);
        expect(
          decodeCodex32((item['encoded'] as String).toUpperCase()).seed,
          secret,
        );
        final shares = splitCodex32(
          secret: secret,
          threshold: threshold,
          identifier: 'test',
          indices: List<String>.from(item['indices']),
          randomBytes: random,
        );
        expect(shares, item['shares']);
        // Every threshold subset of threshold+1 generated shares must recover.
        for (var omitted = 0; omitted < shares.length; omitted++) {
          final recovered = recoverCodex32Exact([
            for (var i = 0; i < shares.length; i++)
              if (i != omitted) shares[i],
          ]);
          expect(recovered.secret, secret);
          expect(recovered.payloadSymbols, codex32SecretPayloadSymbols(secret));
          recovered.destroy();
          expect(recovered.secret.every((b) => b == 0), isTrue);
        }
      },
    );
  }
  for (final item in fixture['typed'] as List) {
    final format = RecoverySecretFormat.values.byName(item['format']);
    final secret = unhex(item['secret']);
    final threshold = item['threshold'] as int;
    test(
      'Frank fr1 ${format.name} parity $threshold-of-${item['shareCount']}',
      () {
        final shares = exportRecoveryShares(
          format: format,
          secret: secret,
          threshold: threshold,
          shareCount: item['shareCount'],
          randomBytes: random,
          identifier: 'test',
        );
        expect(shares, item['shares']);
        for (var offset = 0; offset < shares.length; offset++) {
          final recovered = recoverFrankShares(
            List.generate(
              threshold,
              (i) => shares[(i + offset) % shares.length].toUpperCase(),
            ),
          );
          expect(recovered.format, format);
          expect(recovered.bytes, secret);
          recovered.destroy();
        }
        final share = decodeFrankRecoveryShare(shares.first);
        share.payload.fillRange(0, share.payload.length, 31);
        expect(decodeFrankRecoveryShare(shares.first).payload, share.payload);
      },
    );
  }
  test('Frank account root and domain-separated payment derivation match', () {
    final root = Uint8List.fromList(List.generate(32, (i) => i));
    expect(createMasterPayload(root), unhex(fixture['master']));
    expect(validateMasterPayload(unhex(fixture['master'])), root);
    expect(deriveFrankPaymentSeed(root), unhex(fixture['paymentSeed']));
    final bad = unhex(fixture['master'])..[63] ^= 1;
    expect(() => validateMasterPayload(bad), throwsA(code('bad-format')));
  });
  test('official BIP93 nonzero residual bits are discarded, not rejected', () {
    final vectors = {
      'ms10testsxxxxxxxxxxxxxxxxxxxxxxxxxx4nzvca9cmczlw':
          '318c6318c6318c6318c6318c6318c631',
      'ms10seedsyqsjygeyy5nzw2pf9g4jctfw9ucrzv3nxs6nvdau84gz0632s0xs':
          '202122232425262728292a2b2c2d2e2f3031323334353637',
      'ms10seedsgpq5ys6yg4rywjzfff95cn2wfag9z5jn2324v46ct9d9hrcduqw8c3lccl':
          '404142434445464748494a4b4c4d4e4f505152535455565758595a5b',
    };
    for (final entry in vectors.entries) {
      expect(validateCodex32Checksum(entry.key), isTrue);
      expect(decodeCodex32(entry.key).seed, unhex(entry.value));
    }
  });
  test('invalid size is not legitimized by a valid checksum', () {
    const seventeen = 'ms10seedsqqqsyqcyq5rqwzqfpg9scrgwpugqwngczcas22rt6';
    expect(validateCodex32Checksum(seventeen), isTrue);
    expect(() => decodeCodex32(seventeen), throwsA(code('unsupported-length')));
  });
  test('mixed case, corrupt checksums and incomplete recovery fail', () {
    final shares = List<String>.from(fixture['typed'][1]['shares']);
    expect(
      () => decodeFrankRecoveryShare('fR${shares.first.substring(2)}'),
      throwsA(code('bad-format')),
    );
    final bad =
        '${shares.first.substring(0, shares.first.length - 1)}${shares.first.endsWith('q') ? 'p' : 'q'}';
    expect(
      () => recoverFrankShares([bad, shares[1]]),
      throwsA(code('bad-checksum')),
    );
    expect(
      () => recoverFrankShares([shares.first]),
      throwsA(code('wrong-share-count')),
    );
    expect(
      () => recoverFrankShares(shares),
      throwsA(code('wrong-share-count')),
    );
    expect(
      () => recoverFrankShares([shares.first, shares.first]),
      throwsA(code('duplicate-share')),
    );
  });
  test('same-header shares from different splits fail secret validation', () {
    final secret = Uint8List(64);
    final a = exportRecoveryShares(
      format: RecoverySecretFormat.historical,
      secret: secret,
      threshold: 2,
      shareCount: 3,
      identifier: 'test',
      randomBytes: random,
    );
    secret[0] = 1;
    final b = exportRecoveryShares(
      format: RecoverySecretFormat.historical,
      secret: secret,
      threshold: 2,
      shareCount: 3,
      identifier: 'test',
      randomBytes: random,
    );
    expect(
      () => recoverFrankShares([a[0], b[1]]),
      throwsA(isA<Codex32Exception>()),
    );
  });
  test('CSPRNG failure never falls back or returns backups', () {
    for (final rng in <BackupRandomBytes>[
      (n) => throw StateError('test'),
      (n) => Uint8List(n + 1),
    ]) {
      expect(
        () => exportRecoveryShares(
          format: RecoverySecretFormat.root,
          secret: Uint8List(32),
          threshold: 2,
          shareCount: 3,
          randomBytes: rng,
        ),
        throwsA(code('rng-failed')),
      );
    }
  });
  test('BIP39 backups preserve the exact passphrase-derived BIP32 seed', () {
    const words =
        'abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about';
    final roots = <List<int>>[];
    for (final passphrase in ['', 'Secret', 'secret', ' Secret ']) {
      final shares = backupBip39Mnemonic(
        words,
        passphrase: passphrase,
        randomBytes: random,
      );
      final recovered = recoverFrankShares(shares.take(2).toList());
      expect(recovered.format, RecoverySecretFormat.historical);
      expect(recovered.bytes, Mnemonic().toSeed(words, passphrase));
      roots.add(recovered.bytes.toList());
      recovered.destroy();
    }
    for (var i = 0; i < roots.length; i++) {
      for (var j = i + 1; j < roots.length; j++) {
        expect(roots[i], isNot(roots[j]));
      }
    }
  });
}
