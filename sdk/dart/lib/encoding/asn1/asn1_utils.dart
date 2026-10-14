import 'dart:typed_data';
import 'package:pointycastle/asn1.dart' as upstream;

/// Compatibility helpers for the former local ASN.1 copy.
/// Integer encoding/decoding delegates to upstream's public DER implementation;
/// raw keys and compact ECDSA limbs must use unsigned fixed-width encoding.
class ASN1Utils {
  static final negativeFlag = BigInt.from(0x80);

  static BigInt decodeBigInt(List<int> bytes) {
    if (bytes.isEmpty) throw FormatException('Empty ASN.1 integer');
    final der = Uint8List.fromList([
      2,
      ...upstream.ASN1Utils.encodeLength(bytes.length),
      ...bytes,
    ]);
    return upstream.ASN1Integer.fromBytes(der).integer!;
  }

  static Uint8List encodeBigInt(BigInt number) {
    final integer = upstream.ASN1Integer(number)..encode();
    return Uint8List.fromList(integer.valueBytes!);
  }

  static int calculateValueStartPosition(Uint8List bytes) =>
      upstream.ASN1Utils.calculateValueStartPosition(bytes);
  static int decodeLength(Uint8List bytes) =>
      upstream.ASN1Utils.decodeLength(bytes);
  static Uint8List encodeLength(int length, {bool longform = false}) =>
      upstream.ASN1Utils.encodeLength(length, longform: longform);
  static bool isConstructed(int value) =>
      upstream.ASN1Utils.isConstructed(value);
  static bool isASN1Tag(int value) => upstream.ASN1Utils.isASN1Tag(value);
  static bool hasIndefiniteLengthEnding(Uint8List bytes) =>
      upstream.ASN1Utils.hasIndefiniteLengthEnding(bytes);
}
