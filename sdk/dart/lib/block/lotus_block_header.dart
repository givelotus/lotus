import 'dart:typed_data';
import 'package:hex/hex.dart';
import '../encoding/utils.dart';

/// The 160-byte Lotus V1 header, with its layered single-SHA256 block hash.
/// The inherited [BlockHeader] API describes 80-byte Bitcoin headers.
class LotusBlockHeader {
  final List<int> bytes;
  LotusBlockHeader(List<int> bytes) : bytes = List<int>.unmodifiable(bytes) {
    if (bytes.length != 160 || bytes.any((v) => v < 0 || v > 255)) {
      throw FormatException('Expected 160-byte Lotus header');
    }
  }
  int _le(int offset, int size) {
    var result = 0;
    for (var i = size - 1; i >= 0; i--) {
      result = (result << 8) | bytes[offset + i];
    }
    return result;
  }

  String _hash(int offset) =>
      HEX.encode(bytes.sublist(offset, offset + 32).reversed.toList());
  String get previousHash => _hash(0);
  int get bits => _le(32, 4);
  int get time => _le(36, 6);
  int get reserved => _le(42, 2);
  BigInt get nonce => bytes
      .sublist(44, 52)
      .reversed
      .fold(BigInt.zero, (n, b) => (n << 8) | BigInt.from(b));
  int get version => bytes[52];
  int get size => _le(53, 7);
  int get height => ByteData.sublistView(
    Uint8List.fromList(bytes),
  ).getInt32(60, Endian.little);
  String get epochHash => _hash(64);
  String get merkleRoot => _hash(96);
  String get metadataHash => _hash(128);
  String get hash {
    final layer3 = sha256(bytes.sublist(52));
    final layer2 = sha256([...bytes.sublist(32, 52), ...layer3]);
    return HEX.encode(
      sha256([...bytes.sublist(0, 32), ...layer2]).reversed.toList(),
    );
  }
}
