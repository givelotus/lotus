import 'dart:convert';
import 'dart:io';
import 'package:lotus_dart/lotus.dart';
import 'dart:typed_data';
import 'package:hex/hex.dart';
import 'package:lotus_dart/encoding/asn1.dart' as local;
import 'package:lotus_dart/encoding/ckdserializer.dart';
import 'package:pointycastle/asn1.dart' as upstream;
import 'package:test/test.dart';

class _SerializedKey extends CKDSerializer {}

void main() {
  test('original DER high-bit padding remains minimal', () {
    final vectors = <int, String>{
      0: '020100',
      127: '02017f',
      128: '02020080',
      255: '020200ff',
      256: '02020100',
      -1: '0201ff',
      -127: '020181',
      -128: '020180',
      -129: '0202ff7f',
      -255: '0202ff01',
      -256: '0202ff00',
    };
    for (final entry in vectors.entries) {
      final value = BigInt.from(entry.key);
      final encoded = local.ASN1Integer(value).encode();
      expect(HEX.encode(encoded), entry.value, reason: '$value');
      expect(encoded, upstream.ASN1Integer(value).encode());
      final input = Uint8List.fromList(encoded);
      expect(local.ASN1Integer.fromBytes(input).integer, value);
      expect(input, encoded, reason: 'DER parser must not mutate input');
    }
  });

  test('signed codec handles 256-bit boundaries without mutating callers', () {
    for (final value in [
      BigInt.one << 255,
      (BigInt.one << 256) - BigInt.one,
      -(BigInt.one << 255),
      -(BigInt.one << 255) - BigInt.one,
    ]) {
      final encoded = local.ASN1Integer(value).encode();
      expect(encoded, upstream.ASN1Integer(value).encode());
      expect(local.ASN1Integer.fromBytes(encoded).integer, value);
    }
    final bytes = <int>[255];
    expect(local.ASN1Utils.decodeBigInt(bytes), -BigInt.one);
    expect(bytes, [255]);
    expect(() => local.ASN1Utils.decodeBigInt([]), throwsFormatException);
  });

  test('legacy FORKID digest still matches the daemon fixture', () {
    final fixture = jsonDecode(
      File('test/fixtures/legacy_forkid_digest.json').readAsStringSync(),
    );
    final digest = Sighash().hash(
      Transaction.fromHex(fixture['raw']),
      fixture['hashType'],
      fixture['input'],
      BCHScript.fromHex(fixture['script']),
      BigInt.from(fixture['amount']),
    );
    expect(digest, HEX.encode(HEX.decode(fixture['digest']).reversed.toList()));
  });

  test('original HD key workaround pads all short magnitudes to 33 bytes', () {
    final key = _SerializedKey();
    for (final bytes in [
      <int>[1],
      <int>[128],
      List<int>.filled(31, 255),
      List<int>.filled(32, 255),
    ]) {
      key.keyBuffer = bytes;
      expect(key.keyBuffer.length, 33);
      expect(key.keyBuffer.sublist(33 - bytes.length), bytes);
      expect(key.keyBuffer.sublist(0, 33 - bytes.length), everyElement(0));
    }
  });
}
