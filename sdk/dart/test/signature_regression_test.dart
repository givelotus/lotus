import 'package:hex/hex.dart';
import 'package:lotus_dart/lotus.dart';
import 'package:test/test.dart';

void main() {
  test('DER integers are minimally encoded and preserve high bits', () {
    final values = [
      BigInt.one,
      BigInt.from(127),
      BigInt.from(128),
      BigInt.one << 248,
      (BigInt.one << 255) + BigInt.one,
    ];
    for (final r in values) {
      for (final s in values) {
        final sig = BCHSignature.fromECParams(r, s);
        final der = sig.toString();
        expect(BCHSignature.isTxDER('${der}41'), isTrue);
        final decoded = BCHSignature.fromDER(der);
        expect(decoded.r, r);
        expect(decoded.s, s);
      }
    }
    expect(
      BCHSignature.fromECParams(BigInt.from(128), BigInt.one).toString(),
      '300702020080020101',
    );
    expect(
      () => BCHSignature.fromDER('300702020001020101'),
      throwsA(isA<SignatureException>()),
    );
    expect(
      () => BCHSignature.fromDER('3006020180020101'),
      throwsA(isA<SignatureException>()),
    );
  });

  test('compact signatures have fixed unsigned limbs and recover the key', () {
    final key = BCHPrivateKey.fromBigInt(BigInt.one);
    var shortLimb = false;
    var highBit = false;
    for (var n = 0; n < 350; n++) {
      final digest = HEX.encode(sha256([n & 255, n >> 8]));
      final signer = BCHSignature.fromPrivateKey(key);
      final der = signer.sign(digest, forCompact: true);
      expect(signer.hasLowS(), isTrue);
      final verifier = BCHSignature.fromPublicKey(key.publicKey!);
      // Imported DER public key verification is also supported.
      final imported = BCHSignature.fromDER(der, publicKey: key.publicKey);
      expect(imported.verify(digest), isTrue);
      final compact = signer.toCompact();
      expect(compact.length, 65);
      final recovered = BCHSignature.fromCompact(compact, HEX.decode(digest));
      expect(recovered.r, signer.r);
      expect(recovered.s, signer.s);
      expect(recovered.publicKey!.toHex(), key.publicKey!.toHex());
      expect(recovered.verify(digest), isTrue);
      expect(verifier.publicKey!.toHex(), key.publicKey!.toHex());
      shortLimb |= signer.r!.bitLength <= 248 || signer.s!.bitLength <= 248;
      highBit |= signer.r!.bitLength == 256;
      if (shortLimb && highBit) break;
    }
    expect(shortLimb, isTrue);
    expect(highBit, isTrue);
  });
}
