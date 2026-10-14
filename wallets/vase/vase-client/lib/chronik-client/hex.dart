import 'dart:typed_data';
import 'package:hex/hex.dart';

String toHex(List<int> bytes) => HEX.encode(bytes);
String toHexRev(List<int> bytes) => HEX.encode(bytes.reversed.toList());
Uint8List fromHex(String text) {
  if (text.length.isOdd) {
    throw const FormatException('Hex must contain whole bytes');
  }
  return Uint8List.fromList(HEX.decode(text));
}

Uint8List fromHexRev(String text) =>
    Uint8List.fromList(fromHex(text).reversed.toList());
