import 'dart:typed_data';
import 'package:hex/hex.dart';
import '../../block/lotus_block_header.dart';
import 'chains.dart';
import 'transaction.dart';

/// Fixed header codecs, not block/PoW validation. Dogecoin AuxPoW and Litecoin
/// MWEB extended block framing are not parsed by this header-only API.
class ChainBlockHeader {
  final ChainDescriptor chain;
  final Uint8List _bytes;
  ChainBlockHeader(List<int> bytes, {required this.chain})
    : _bytes = Uint8List.fromList(bytes) {
    final size = chain.family == ChainFamily.xpi ? 160 : 80;
    if (bytes.length != size || bytes.any((b) => b < 0 || b > 255)) {
      throw FormatException(
        'Expected $size-byte base header for ${chain.protocolId}',
      );
    }
  }
  factory ChainBlockHeader.fromHex(
    String hex, {
    required ChainDescriptor chain,
  }) => ChainBlockHeader(HEX.decode(hex), chain: chain);
  Uint8List get bytes => Uint8List.fromList(_bytes);
  BigInt _integer(int offset, int length) => _bytes
      .sublist(offset, offset + length)
      .reversed
      .fold(BigInt.zero, (n, b) => (n << 8) | BigInt.from(b));
  String _hash(int offset) =>
      HEX.encode(_bytes.sublist(offset, offset + 32).reversed.toList());
  String get hash => chain.family == ChainFamily.xpi
      ? LotusBlockHeader(_bytes).hash
      : HEX.encode(chainHash256(_bytes).reversed.toList());
  String get previousHash => _hash(chain.family == ChainFamily.xpi ? 0 : 4);
  String get merkleRoot => _hash(chain.family == ChainFamily.xpi ? 96 : 36);
  int get version => chain.family == ChainFamily.xpi
      ? _bytes[52]
      : ByteData.sublistView(_bytes).getInt32(0, Endian.little);
  int get time => _integer(
    chain.family == ChainFamily.xpi ? 36 : 68,
    chain.family == ChainFamily.xpi ? 6 : 4,
  ).toInt();
  int get bits =>
      _integer(chain.family == ChainFamily.xpi ? 32 : 72, 4).toInt();
  BigInt get nonce => _integer(
    chain.family == ChainFamily.xpi ? 44 : 76,
    chain.family == ChainFamily.xpi ? 8 : 4,
  );
  void _requireLotus() {
    if (chain.family != ChainFamily.xpi) {
      throw UnsupportedChainCapability(chain.protocolId, 'Lotus header fields');
    }
  }

  int get height {
    _requireLotus();
    return ByteData.sublistView(_bytes).getInt32(60, Endian.little);
  }

  int get reserved {
    _requireLotus();
    return _integer(42, 2).toInt();
  }

  BigInt get size {
    _requireLotus();
    return _integer(53, 7);
  }

  String get epochHash {
    _requireLotus();
    return _hash(64);
  }

  String get metadataHash {
    _requireLotus();
    return _hash(128);
  }
}
