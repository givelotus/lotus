import 'dart:typed_data';
import 'package:pointycastle/ecc/api.dart';
import '../../encoding/base58check.dart' as base58;
import '../../encoding/utils.dart' as hashes;
import 'chains.dart';
import 'addresses.dart';

/// Private scalar and public-key compression, independent of chain identity.
class ChainKey {
  final Uint8List _secret;
  final bool compressed;
  static final _curve = ECDomainParameters('secp256k1');
  ChainKey._(this._secret, this.compressed);
  factory ChainKey.fromBytes(Uint8List bytes, {bool compressed = true}) {
    if (bytes.length != 32) {
      throw FormatException('Private key must be 32 bytes');
    }
    final scalar = bytes.fold<BigInt>(
      BigInt.zero,
      (n, b) => (n << 8) | BigInt.from(b),
    );
    if (scalar <= BigInt.zero || scalar >= _curve.n) {
      throw FormatException('Private scalar out of range');
    }
    return ChainKey._(Uint8List.fromList(bytes), compressed);
  }
  factory ChainKey.fromWif(String text, {required ChainDescriptor chain}) {
    final bytes = base58.decodeChecked(text);
    if ((bytes.length != 33 && bytes.length != 34) ||
        bytes[0] != chain.wifVersion ||
        (bytes.length == 34 && bytes.last != 1)) {
      throw FormatException('Invalid WIF for ${chain.protocolId}');
    }
    return ChainKey.fromBytes(
      Uint8List.fromList(bytes.sublist(1, 33)),
      compressed: bytes.length == 34,
    );
  }
  Uint8List get secretBytes => Uint8List.fromList(_secret);
  Uint8List get publicKey {
    final scalar = _secret.fold<BigInt>(
      BigInt.zero,
      (n, b) => (n << 8) | BigInt.from(b),
    );
    return Uint8List.fromList((_curve.G * scalar)!.getEncoded(compressed));
  }

  String toWif({required ChainDescriptor chain}) {
    final body = [chain.wifVersion, ..._secret, if (compressed) 1];
    return base58.encode([...body, ...hashes.sha256Twice(body).take(4)]);
  }

  Address address({
    required ChainDescriptor chain,
    AddressType type = AddressType.p2pkh,
  }) => Address.fromPublicKey(publicKey, chain: chain, type: type);
}
