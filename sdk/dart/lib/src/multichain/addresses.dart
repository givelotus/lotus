import 'dart:typed_data';
import 'package:collection/collection.dart';
import '../../encoding/base58check.dart' as base58;
import '../../encoding/utils.dart' as hashes;
import 'chains.dart';
import 'curve.dart' show validatePublicKey, CurveException;

enum AddressType { p2pkh, p2sh, p2wpkh, p2wsh, p2tr }

enum AddressEncoding { base58check, cashaddr, bech32, bech32m, lotus }

/// A destination bound to an explicit network. Returned bytes are copies.
class Address {
  final ChainDescriptor chain;
  final AddressType type;
  final Uint8List _payload;
  Address._(this.chain, this.type, List<int> payload)
    : _payload = Uint8List.fromList(payload) {
    final expected = type == AddressType.p2wsh || type == AddressType.p2tr
        ? 32
        : 20;
    if (_payload.length != expected) {
      throw FormatException('Invalid destination size');
    }
    if ((type == AddressType.p2wpkh ||
            type == AddressType.p2wsh ||
            type == AddressType.p2tr) &&
        chain.bech32Hrp == null) {
      throw UnsupportedChainCapability(chain.protocolId, type.name);
    }
  }
  factory Address.fromPublicKey(
    Uint8List publicKey, {
    required ChainDescriptor chain,
    AddressType type = AddressType.p2pkh,
  }) {
    final validLength =
        publicKey.length == 33 &&
            (publicKey.first == 2 || publicKey.first == 3) ||
        publicKey.length == 65 && publicKey.first == 4;
    if (!validLength) throw FormatException('Invalid SEC public key');
    try {
      validatePublicKey(publicKey);
    } on CurveException catch (error) {
      throw FormatException('Invalid SEC point: ${error.message}');
    }
    if (type != AddressType.p2pkh && type != AddressType.p2wpkh) {
      throw UnsupportedChainCapability(
        chain.protocolId,
        'derive ${type.name} from public key (explicit script/output key required)',
      );
    }
    if (type == AddressType.p2wpkh && publicKey.length != 33) {
      throw FormatException('Witness requires compressed public key');
    }
    return Address._(chain, type, hashes.hash160(publicKey));
  }
  factory Address.fromScriptPubKey(
    Uint8List script, {
    required ChainDescriptor chain,
  }) {
    if (script.length == 25 &&
        script[0] == 0x76 &&
        script[1] == 0xa9 &&
        script[2] == 20 &&
        script[23] == 0x88 &&
        script[24] == 0xac) {
      return Address._(chain, AddressType.p2pkh, script.sublist(3, 23));
    }
    if (script.length == 23 &&
        script[0] == 0xa9 &&
        script[1] == 20 &&
        script[22] == 0x87) {
      return Address._(chain, AddressType.p2sh, script.sublist(2, 22));
    }
    if (script.length == 22 && script[0] == 0 && script[1] == 20) {
      return Address._(chain, AddressType.p2wpkh, script.sublist(2));
    }
    if (script.length == 34 &&
        script[1] == 32 &&
        (script[0] == 0 || script[0] == 0x51)) {
      return Address._(
        chain,
        script[0] == 0 ? AddressType.p2wsh : AddressType.p2tr,
        script.sublist(2),
      );
    }
    throw FormatException('Unsupported output script');
  }
  Uint8List get scriptPubKey => Uint8List.fromList(switch (type) {
    AddressType.p2pkh => [0x76, 0xa9, 20, ..._payload, 0x88, 0xac],
    AddressType.p2sh => [0xa9, 20, ..._payload, 0x87],
    AddressType.p2wpkh => [0, 20, ..._payload],
    AddressType.p2wsh => [0, 32, ..._payload],
    AddressType.p2tr => [0x51, 32, ..._payload],
  });
  String encode({AddressEncoding? encoding}) {
    encoding ??= chain.lotusNetChar != null
        ? AddressEncoding.lotus
        : (type == AddressType.p2wpkh || type == AddressType.p2wsh)
        ? AddressEncoding.bech32
        : type == AddressType.p2tr
        ? AddressEncoding.bech32m
        : chain.cashaddrPrefix != null
        ? AddressEncoding.cashaddr
        : AddressEncoding.base58check;
    if (chain.lotusNetChar != null) {
      if (encoding != AddressEncoding.lotus) {
        throw UnsupportedChainCapability(chain.protocolId, encoding.name);
      }
      final body = [0, ...scriptPubKey];
      return 'lotus${chain.lotusNetChar}${base58.encode([
        ...body,
        ...hashes.sha256([...'lotus${chain.lotusNetChar}'.codeUnits, ...body]).take(4),
      ])}';
    }
    switch (encoding) {
      case AddressEncoding.base58check:
        if (type != AddressType.p2pkh && type != AddressType.p2sh) break;
        final body = [
          type == AddressType.p2pkh
              ? chain.pubkeyHashVersion
              : chain.scriptHashVersion,
          ..._payload,
        ];
        return base58.encode([...body, ...hashes.sha256Twice(body).take(4)]);
      case AddressEncoding.cashaddr:
        if (chain.cashaddrPrefix == null ||
            (type != AddressType.p2pkh && type != AddressType.p2sh)) {
          break;
        }
        final prefix = chain.cashaddrPrefix!;
        final data = _bits(
          [type == AddressType.p2pkh ? 0 : 8, ..._payload],
          8,
          5,
          true,
        );
        final checksum =
            _cashPolymod([
              ...prefix.codeUnits.map((c) => c & 31),
              0,
              ...data,
              ...List.filled(8, 0),
            ]) ^
            BigInt.one;
        return '$prefix:${[...data, ...List.generate(8, (i) => ((checksum >> (5 * (7 - i))) & BigInt.from(31)).toInt())].map((i) => _alphabet[i]).join()}';
      case AddressEncoding.bech32:
      case AddressEncoding.bech32m:
        final v = type == AddressType.p2tr ? 1 : 0;
        if (chain.bech32Hrp == null ||
            (type != AddressType.p2wpkh &&
                type != AddressType.p2wsh &&
                type != AddressType.p2tr) ||
            (v == 0) != (encoding == AddressEncoding.bech32)) {
          break;
        }
        final prefix = chain.bech32Hrp!;
        final data = [v, ..._bits(_payload, 8, 5, true)];
        final checksum =
            _bechPolymod([..._expand(prefix), ...data, ...List.filled(6, 0)]) ^
            (v == 0 ? 1 : 0x2bc830a3);
        return '${prefix}1${[...data, ...List.generate(6, (i) => (checksum >> (5 * (5 - i))) & 31)].map((i) => _alphabet[i]).join()}';
      case AddressEncoding.lotus:
        break;
    }
    throw UnsupportedChainCapability(
      chain.protocolId,
      '${encoding.name}/${type.name}',
    );
  }

  static Address parse(String text, {required ChainDescriptor chain}) {
    if (chain.lotusNetChar != null) {
      final prefix = 'lotus${chain.lotusNetChar}';
      if (!text.startsWith(prefix)) {
        throw FormatException('Wrong Lotus network');
      }
      final bytes = base58.decode(text.substring(prefix.length));
      if (bytes.length < 5 || bytes.first != 0) {
        throw FormatException('Invalid XAddress');
      }
      final body = bytes.sublist(0, bytes.length - 4);
      final checksum = hashes
          .sha256([...prefix.codeUnits, ...body])
          .take(4)
          .toList();
      if (!const ListEquality<int>().equals(
        checksum,
        bytes.sublist(bytes.length - 4),
      )) {
        throw FormatException('Invalid XAddress checksum');
      }
      return Address.fromScriptPubKey(
        Uint8List.fromList(body.sublist(1)),
        chain: chain,
      );
    }
    if (text.toLowerCase().startsWith('${chain.bech32Hrp}1') &&
        chain.bech32Hrp != null) {
      _caseCheck(text);
      final lower = text.toLowerCase();
      if (lower.length > 90) throw FormatException('Bech32 too long');
      final prefix = chain.bech32Hrp!;
      final data = _decode32(lower.substring(prefix.length + 1));
      if (data.length < 7) throw FormatException('Short witness address');
      final v = data.first;
      final pm = _bechPolymod([..._expand(prefix), ...data]);
      if ((v == 0 ? 1 : 0x2bc830a3) != pm) {
        throw FormatException('Witness checksum mismatch');
      }
      final program = _bits(data.sublist(1, data.length - 6), 5, 8, false);
      if (v == 0 && program.length == 20) {
        return Address._(chain, AddressType.p2wpkh, program);
      }
      if (v == 0 && program.length == 32) {
        return Address._(chain, AddressType.p2wsh, program);
      }
      if (v == 1 && program.length == 32) {
        return Address._(chain, AddressType.p2tr, program);
      }
      throw FormatException('Unsupported witness program');
    }
    if (chain.cashaddrPrefix != null &&
        (text.contains(':') ||
            RegExp(r'^[qp][a-z0-9]+$', caseSensitive: false).hasMatch(text))) {
      _caseCheck(text);
      final parts = text.toLowerCase().split(':');
      if (parts.length > 2 ||
          (parts.length == 2 && parts.first != chain.cashaddrPrefix)) {
        throw FormatException('Wrong CashAddr prefix');
      }
      final data = _decode32(parts.last);
      if (data.length < 9 ||
          _cashPolymod([
                ...chain.cashaddrPrefix!.codeUnits.map((c) => c & 31),
                0,
                ...data,
              ]) !=
              BigInt.one) {
        throw FormatException('CashAddr checksum mismatch');
      }
      final payload = _bits(data.sublist(0, data.length - 8), 5, 8, false);
      if (payload.length != 21 || (payload.first != 0 && payload.first != 8)) {
        throw FormatException('Unsupported CashAddr type');
      }
      return Address._(
        chain,
        payload.first == 0 ? AddressType.p2pkh : AddressType.p2sh,
        payload.sublist(1),
      );
    }
    final payload = base58.decodeChecked(text);
    if (payload.length != 21) throw FormatException('Invalid legacy payload');
    final type = payload.first == chain.pubkeyHashVersion
        ? AddressType.p2pkh
        : payload.first == chain.scriptHashVersion
        ? AddressType.p2sh
        : null;
    if (type == null) throw FormatException('Wrong address version');
    return Address._(chain, type, payload.sublist(1));
  }

  @override
  String toString() => encode();
}

const _alphabet = 'qpzry9x8gf2tvdw0s3jn54khce6mua7l';
void _caseCheck(String text) {
  if (text != text.toLowerCase() && text != text.toUpperCase()) {
    throw FormatException('Mixed address case');
  }
}

List<int> _decode32(String text) => text.split('').map((c) {
  final n = _alphabet.indexOf(c);
  if (n < 0) throw FormatException('Invalid base32 character');
  return n;
}).toList();
List<int> _bits(List<int> data, int from, int to, bool pad) {
  var acc = 0, bits = 0;
  final out = <int>[];
  final mask = (1 << to) - 1;
  for (final value in data) {
    if (value < 0 || value >= (1 << from)) {
      throw FormatException('Invalid group');
    }
    acc = ((acc << from) | value) & ((1 << (from + to - 1)) - 1);
    bits += from;
    while (bits >= to) {
      bits -= to;
      out.add((acc >> bits) & mask);
    }
  }
  if (pad) {
    if (bits > 0) out.add((acc << (to - bits)) & mask);
  } else if (bits >= from || ((acc << (to - bits)) & mask) != 0) {
    throw FormatException('Noncanonical padding');
  }
  return out;
}

List<int> _expand(String prefix) => [
  ...prefix.codeUnits.map((c) => c >> 5),
  0,
  ...prefix.codeUnits.map((c) => c & 31),
];
int _bechPolymod(List<int> values) {
  var c = 1;
  const generators = [
    0x3b6a57b2,
    0x26508e6d,
    0x1ea119fa,
    0x3d4233dd,
    0x2a1462b3,
  ];
  for (final d in values) {
    final top = c >> 25;
    c = ((c & 0x1ffffff) << 5) ^ d;
    for (var i = 0; i < 5; i++) {
      if (((top >> i) & 1) != 0) c ^= generators[i];
    }
  }
  return c;
}

BigInt _cashPolymod(List<int> values) {
  var c = BigInt.one;
  final generators = [
    0x98f2bc8e61,
    0x79b76d99e2,
    0xf33e5fb3c4,
    0xae2eabe2a8,
    0x1e4f43e470,
  ].map(BigInt.from).toList();
  for (final d in values) {
    final top = (c >> 35).toInt();
    c = ((c & BigInt.parse('07ffffffff', radix: 16)) << 5) ^ BigInt.from(d);
    for (var i = 0; i < 5; i++) {
      if (((top >> i) & 1) != 0) c ^= generators[i];
    }
  }
  return c;
}
