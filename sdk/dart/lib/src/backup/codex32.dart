// Port of @frank/codex32 (MIT), pinned source recorded in docs/codex32.md.
import 'dart:typed_data';

const gf32Alphabet = 'qpzry9x8gf2tvdw0s3jn54khce6mua7l';
const _sizes = [16, 20, 24, 28, 32, 64];
const _lengths = [48, 54, 61, 67, 74, 127];
final _initial = BigInt.parse('23181b3', radix: 16);
final _regularResidue = BigInt.parse('10ce0795c2fd1e62a', radix: 16);
final _longResidue = BigInt.parse('43381e570bf4798ab26', radix: 16);
final _regularGenerators = [
  '19dc500ce73fde210',
  '1bfae00def77fe529',
  '1fbd920fffe7bee52',
  '1739640bdeee3fdad',
  '07729a039cfc75f5a',
].map((v) => BigInt.parse(v, radix: 16)).toList(growable: false);
final _longGenerators = [
  '3d59d273535ea62d897',
  '7a9becb6361c6c51507',
  '543f9b7e6c38d8a2a0e',
  '0c577eaeccf1990d13c',
  '1887f74f8dc71b10651',
].map((v) => BigInt.parse(v, radix: 16)).toList(growable: false);

typedef BackupRandomBytes = Uint8List Function(int length);

/// Errors contain a public code, never input material.
class Codex32Exception extends FormatException {
  final String code;
  Codex32Exception(this.code) : super(code);
}

Never _fail(String code) => throw Codex32Exception(code);

class Codex32Share {
  final int threshold;
  final String identifier;
  final String index;
  final Uint8List _payload;
  Codex32Share(this.threshold, this.identifier, this.index, Uint8List payload)
    : _payload = Uint8List.fromList(payload);
  Uint8List get payload => Uint8List.fromList(_payload);
  Uint8List? get seed => index == 's' ? _decodeBytes(_payload) : null;
}

class RecoveredCodex32 {
  final Uint8List secret;
  final Uint8List payloadSymbols;
  RecoveredCodex32(this.secret, this.payloadSymbols);
  void destroy() {
    secret.fillRange(0, secret.length, 0);
    payloadSymbols.fillRange(0, payloadSymbols.length, 0);
  }
}

bool _validIndex(String value) =>
    value.length == 1 && gf32Alphabet.contains(value);
bool _validIdentifier(String value) =>
    value.length == 4 && value.split('').every(_validIndex);
bool _validThreshold(int value) => value == 0 || (value >= 2 && value <= 9);

BigInt _polymod(List<int> values, {bool long = false, BigInt? initial}) {
  var result = initial ?? _initial;
  final shift = long ? 70 : 60;
  final mask = (BigInt.one << shift) - BigInt.one;
  final generators = long ? _longGenerators : _regularGenerators;
  for (final value in values) {
    final top = result >> shift;
    result = ((result & mask) << 5) ^ BigInt.from(value);
    for (var i = 0; i < 5; i++) {
      if (((top >> i) & BigInt.one) != BigInt.zero) result ^= generators[i];
    }
  }
  return result;
}

List<int> _check(List<int> values, {bool long = false, BigInt? initial}) {
  final count = long ? 15 : 13;
  final result =
      _polymod(
        [...values, ...List.filled(count, 0)],
        long: long,
        initial: initial,
      ) ^
      (long ? _longResidue : _regularResidue);
  return List.generate(
    count,
    (i) => ((result >> (5 * (count - i - 1))) & BigInt.from(31)).toInt(),
  );
}

bool _isLong(int length) => length + 2 >= 96;

String _encode(
  int threshold,
  String identifier,
  String index,
  List<int> payload,
) {
  final values = [
    ...'$threshold$identifier$index'.split('').map(gf32Alphabet.indexOf),
    ...payload,
  ];
  final long = values.length + 13 + 5 > 93;
  return 'ms1${[...values, ..._check(values, long: long)].map((v) => gf32Alphabet[v]).join()}';
}

String encodeCodex32({
  required int threshold,
  required String identifier,
  String index = 's',
  required Uint8List secret,
}) {
  final owned = Uint8List.fromList(secret);
  try {
    if (!_sizes.contains(owned.length)) _fail('unsupported-length');
    if (!_validThreshold(threshold)) _fail('invalid-threshold');
    if (!_validIdentifier(identifier)) _fail('invalid-identifier');
    if (index != 's') _fail('invalid-index');
    return _encode(threshold, identifier, index, bytesToGf32Symbols(owned));
  } finally {
    owned.fillRange(0, owned.length, 0);
  }
}

/// Full strict BIP93 parsing. Residual payload bits are discarded per BIP93.
Codex32Share decodeCodex32(String text) {
  if (!_lengths.contains(text.length)) _fail('unsupported-length');
  if (text != text.toLowerCase() && text != text.toUpperCase()) {
    _fail('bad-format');
  }
  final canonical = text.toLowerCase();
  if (!canonical.startsWith('ms1')) _fail('bad-format');
  final values = canonical
      .substring(3)
      .split('')
      .map(gf32Alphabet.indexOf)
      .toList();
  if (values.any((v) => v < 0)) _fail('bad-format');
  final long = _isLong(text.length);
  if (_polymod(values, long: long) != (long ? _longResidue : _regularResidue)) {
    _fail('bad-checksum');
  }
  final threshold = int.tryParse(canonical[3]);
  if (threshold == null || !_validThreshold(threshold)) {
    _fail('invalid-threshold');
  }
  final identifier = canonical.substring(4, 8), index = canonical[8];
  if (!_validIdentifier(identifier)) _fail('invalid-identifier');
  if (!_validIndex(index) || (threshold == 0 && index != 's')) {
    _fail('invalid-index');
  }
  return Codex32Share(
    threshold,
    identifier,
    index,
    Uint8List.fromList(values.sublist(6, values.length - (long ? 15 : 13))),
  );
}

/// Checksum validation is distinct from supported master-seed format validation.
bool validateCodex32Checksum(String text) {
  final expanded = text.length + 2;
  if (expanded > 1023 ||
      (expanded > 93 && expanded < 96) ||
      (text != text.toLowerCase() && text != text.toUpperCase())) {
    return false;
  }
  final canonical = text.toLowerCase();
  if (!canonical.startsWith('ms1')) return false;
  final values = canonical
      .substring(3)
      .split('')
      .map(gf32Alphabet.indexOf)
      .toList();
  final long = _isLong(text.length);
  return values.length >= (long ? 15 : 13) &&
      values.every((v) => v >= 0) &&
      _polymod(values, long: long) == (long ? _longResidue : _regularResidue);
}

Uint8List bytesToGf32Symbols(Uint8List bytes) {
  final out = <int>[];
  var accumulator = 0, bits = 0;
  for (final byte in bytes) {
    accumulator = (accumulator << 8) | byte;
    bits += 8;
    while (bits >= 5) {
      bits -= 5;
      out.add((accumulator >> bits) & 31);
      accumulator &= (1 << bits) - 1;
    }
  }
  if (bits > 0) out.add((accumulator << (5 - bits)) & 31);
  return Uint8List.fromList(out);
}

Uint8List _decodeBytes(
  Uint8List symbols, {
  int? byteLength,
  bool canonical = false,
}) {
  if (symbols.any((v) => v > 31)) _fail('bad-format');
  final length = byteLength ?? (symbols.length * 5 ~/ 8);
  if (length < 1 || symbols.length != (length * 8 + 4) ~/ 5) {
    _fail('bad-format');
  }
  final out = <int>[];
  var accumulator = 0, bits = 0;
  for (final symbol in symbols) {
    accumulator = (accumulator << 5) | symbol;
    bits += 5;
    if (bits >= 8) {
      bits -= 8;
      out.add((accumulator >> bits) & 255);
      accumulator &= (1 << bits) - 1;
    }
  }
  if (canonical && accumulator != 0) _fail('bad-format');
  if (byteLength == null && !_sizes.contains(out.length)) {
    _fail('unsupported-length');
  }
  return Uint8List.fromList(out);
}

Uint8List gf32SymbolsToBytes(Uint8List symbols, int byteLength) => _decodeBytes(
  Uint8List.fromList(symbols),
  byteLength: byteLength,
  canonical: true,
);

int _multiply(int left, int right) {
  var a = left, b = right, result = 0;
  for (var i = 0; i < 5; i++) {
    if ((b & 1) != 0) result ^= a;
    b >>= 1;
    a <<= 1;
    if ((a & 32) != 0) a ^= 0x29;
  }
  return result & 31;
}

int _inverse(int value) {
  if (value == 0) _fail('duplicate-share');
  var result = 1;
  for (var i = 0; i < 30; i++) {
    result = _multiply(result, value);
  }
  return result;
}

int _evaluate(List<int> coefficients, int x) {
  var result = 0;
  for (final coefficient in coefficients.reversed) {
    result = _multiply(result, x) ^ coefficient;
  }
  return result;
}

/// Caller must supply a CSPRNG. No fallback or seeded PRNG is selected here.
List<Uint8List> splitGf32Symbols({
  required Uint8List payload,
  required int threshold,
  required List<String> indices,
  required BackupRandomBytes randomBytes,
}) {
  final symbols = Uint8List.fromList(payload), names = List<String>.of(indices);
  Uint8List? random;
  try {
    if (symbols.isEmpty || symbols.any((v) => v > 31)) _fail('bad-format');
    if (threshold < 1 ||
        threshold > 9 ||
        names.length < threshold ||
        names.length > 31 ||
        (threshold == 1 && names.length != 1)) {
      _fail('invalid-threshold');
    }
    if (names.any((v) => !_validIndex(v) || v == 's')) _fail('invalid-index');
    if (names.toSet().length != names.length) _fail('duplicate-share');
    final count = symbols.length * (threshold - 1);
    try {
      random = Uint8List.fromList(randomBytes(count));
    } catch (_) {
      _fail('rng-failed');
    }
    if (random.length != count) _fail('rng-failed');
    final rows = List.generate(names.length, (_) => Uint8List(symbols.length));
    for (var column = 0; column < symbols.length; column++) {
      final coefficients = [
        symbols[column],
        for (var degree = 1; degree < threshold; degree++)
          random[column * (threshold - 1) + degree - 1] & 31,
      ];
      for (var row = 0; row < rows.length; row++) {
        rows[row][column] = _evaluate(
          coefficients,
          gf32Alphabet.indexOf(names[row]) ^ gf32Alphabet.indexOf('s'),
        );
      }
      coefficients.fillRange(0, coefficients.length, 0);
    }
    return rows;
  } finally {
    symbols.fillRange(0, symbols.length, 0);
    random?.fillRange(0, random.length, 0);
  }
}

Uint8List interpolateGf32Symbols(
  List<Codex32Share> shares,
  String targetIndex,
) {
  final snapshots = List<Codex32Share>.of(shares);
  if (snapshots.isEmpty || snapshots.length > 9) _fail('wrong-share-count');
  if (!_validIndex(targetIndex)) _fail('invalid-index');
  if (snapshots.any((v) => !_validIndex(v.index))) _fail('invalid-index');
  final xs = snapshots.map((v) => gf32Alphabet.indexOf(v.index)).toList();
  final rows = snapshots.map((v) => v.payload).toList();
  try {
    if (xs.any((v) => v < 0)) _fail('invalid-index');
    if (xs.toSet().length != xs.length) _fail('duplicate-share');
    if (rows.any(
      (v) => v.length != rows.first.length || v.any((s) => s > 31),
    )) {
      _fail('inconsistent-share');
    }
    final target = gf32Alphabet.indexOf(targetIndex);
    final weights = List.generate(xs.length, (current) {
      var numerator = 1, denominator = 1;
      for (var other = 0; other < xs.length; other++) {
        if (other == current) continue;
        numerator = _multiply(numerator, target ^ xs[other]);
        denominator = _multiply(denominator, xs[current] ^ xs[other]);
      }
      return _multiply(numerator, _inverse(denominator));
    });
    return Uint8List.fromList(
      List.generate(rows.first.length, (column) {
        var result = 0;
        for (var row = 0; row < rows.length; row++) {
          result ^= _multiply(rows[row][column], weights[row]);
        }
        return result;
      }),
    );
  } finally {
    for (final row in rows) {
      row.fillRange(0, row.length, 0);
    }
  }
}

List<String> splitCodex32({
  required Uint8List secret,
  required int threshold,
  required String identifier,
  required List<String> indices,
  required BackupRandomBytes randomBytes,
}) {
  final owned = Uint8List.fromList(secret);
  List<Uint8List> rows = [];
  try {
    if (!_sizes.contains(owned.length)) _fail('unsupported-length');
    if (threshold < 2 || threshold > 9) _fail('invalid-threshold');
    if (!_validIdentifier(identifier)) _fail('invalid-identifier');
    final names = List<String>.of(indices);
    rows = splitGf32Symbols(
      payload: bytesToGf32Symbols(owned),
      threshold: threshold,
      indices: names,
      randomBytes: randomBytes,
    );
    return List.unmodifiable(
      List.generate(
        rows.length,
        (i) => _encode(threshold, identifier, names[i], rows[i]),
      ),
    );
  } finally {
    owned.fillRange(0, owned.length, 0);
    for (final row in rows) {
      row.fillRange(0, row.length, 0);
    }
  }
}

RecoveredCodex32 recoverCodex32Exact(List<String> encodedShares) {
  final input = List<String>.of(encodedShares);
  if (input.isEmpty || input.length > 31) _fail('insufficient-shares');
  final shares = input.map(decodeCodex32).toList();
  final first = shares.first;
  if (first.threshold == 0) _fail('invalid-threshold');
  if (shares.length != first.threshold) _fail('wrong-share-count');
  if (shares.any((v) => v.index == 's')) _fail('invalid-index');
  if (shares.any(
    (v) =>
        v.threshold != first.threshold ||
        v.identifier != first.identifier ||
        v._payload.length != first._payload.length,
  )) {
    _fail('inconsistent-share');
  }
  final symbols = interpolateGf32Symbols(shares, 's');
  return RecoveredCodex32(_decodeBytes(symbols), symbols);
}

Uint8List recoverCodex32(List<String> shares) {
  final recovered = recoverCodex32Exact(shares);
  try {
    return Uint8List.fromList(recovered.secret);
  } finally {
    recovered.destroy();
  }
}

Uint8List codex32SecretPayloadSymbols(Uint8List secret) {
  final owned = Uint8List.fromList(secret);
  try {
    if (!_sizes.contains(owned.length)) _fail('unsupported-length');
    return bytesToGf32Symbols(owned);
  } finally {
    owned.fillRange(0, owned.length, 0);
  }
}

Uint8List codex32SymbolsToBytes(Uint8List symbols) =>
    _decodeBytes(Uint8List.fromList(symbols));

Uint8List interpolateCodex32Symbols(
  List<Codex32Share> shares,
  String targetIndex,
) {
  if (shares.length < 2) _fail('wrong-share-count');
  return interpolateGf32Symbols(shares, targetIndex);
}

List<int> _expand(String hrp) {
  if (!RegExp(r'^[a-z]{1,83}$').hasMatch(hrp)) _fail('bad-format');
  return [
    ...hrp.codeUnits.map((v) => v >> 5),
    0,
    ...hrp.codeUnits.map((v) => v & 31),
  ];
}

List<int> createLongBchChecksum(String hrp, List<int> data) {
  final values = [..._expand(hrp), ...List<int>.of(data)];
  if (values.length + 15 < 96 ||
      values.length + 15 > 1023 ||
      data.any((v) => v < 0 || v > 31)) {
    _fail('bad-format');
  }
  return _check(values, long: true, initial: BigInt.one);
}

bool verifyLongBchChecksum(String hrp, List<int> data) {
  final values = [..._expand(hrp), ...List<int>.of(data)];
  return values.length >= 96 &&
      values.length <= 1023 &&
      data.every((v) => v >= 0 && v <= 31) &&
      _polymod(values, long: true, initial: BigInt.one) == _longResidue;
}
