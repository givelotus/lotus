// Adaptation of Frank's typed fr1 recovery shares (MIT); see docs/codex32.md.
import 'dart:convert';
import 'dart:typed_data';
import 'package:pointycastle/export.dart';
import '../../bip39/bip39.dart';
import 'codex32.dart';

/// The formats are never guessed from secret length or converted into each other.
enum RecoverySecretFormat { root, historical }

class FrankRecoveryShare {
  final RecoverySecretFormat format;
  final int threshold;
  final String identifier;
  final String index;
  final Uint8List _common;
  final Uint8List _payload;
  FrankRecoveryShare(
    this.format,
    this.threshold,
    this.identifier,
    this.index,
    Uint8List common,
    Uint8List payload,
  ) : _common = Uint8List.fromList(common),
      _payload = Uint8List.fromList(payload);
  int get byteLength => format == RecoverySecretFormat.root ? 32 : 64;
  Uint8List get commonMetadata => Uint8List.fromList(_common);
  Uint8List get payload => Uint8List.fromList(_payload);
}

class RecoveredWalletSecret {
  final RecoverySecretFormat format;
  final Uint8List bytes;
  RecoveredWalletSecret(this.format, Uint8List secret)
    : bytes = Uint8List.fromList(secret);
  void destroy() => bytes.fillRange(0, bytes.length, 0);
}

Never _fail(String code) => throw Codex32Exception(code);
Uint8List _ascii(String value) => Uint8List.fromList(ascii.encode(value));
Uint8List _sha(List<int> value) =>
    SHA256Digest().process(Uint8List.fromList(value));

Uint8List createMasterPayload(Uint8List root) {
  final owned = Uint8List.fromList(root);
  try {
    if (owned.length != 32) _fail('unsupported-length');
    return Uint8List.fromList([
      ...owned,
      ..._sha([..._ascii('frank/master-validation/v1'), 0, ...owned]),
    ]);
  } finally {
    owned.fillRange(0, owned.length, 0);
  }
}

Uint8List validateMasterPayload(Uint8List payload) {
  final owned = Uint8List.fromList(payload);
  Uint8List? expected;
  try {
    if (owned.length != 64) _fail('unsupported-length');
    final root = Uint8List.fromList(owned.sublist(0, 32));
    expected = createMasterPayload(root);
    var difference = 0;
    for (var i = 32; i < 64; i++) {
      difference |= expected[i] ^ owned[i];
    }
    if (difference != 0) {
      root.fillRange(0, root.length, 0);
      _fail('bad-format');
    }
    return root;
  } finally {
    owned.fillRange(0, owned.length, 0);
    expected?.fillRange(0, expected.length, 0);
  }
}

Uint8List _validation(
  Uint8List secret,
  Uint8List common,
  RecoverySecretFormat format,
) => _sha([
  ..._ascii('frank/recovery-share/v1\u0000'),
  ...common,
  ..._ascii(
    format == RecoverySecretFormat.root
        ? 'frank-root-v1\u0000'
        : 'frank-bip39-bip32-v1\u0000',
  ),
  ...secret,
]);

/// Same fr1 bytes as Frank. Secret material is read only by this explicit call.
List<String> exportRecoveryShares({
  required RecoverySecretFormat format,
  required Uint8List secret,
  required int threshold,
  required int shareCount,
  required BackupRandomBytes randomBytes,
  String? identifier,
  List<String>? indices,
}) {
  final owned = Uint8List.fromList(secret);
  Uint8List? payload, symbols;
  List<Uint8List> rows = [];
  try {
    final length = format == RecoverySecretFormat.root ? 32 : 64;
    if (owned.length != length) _fail('bad-format');
    if (threshold < 1 ||
        threshold > 9 ||
        shareCount < threshold ||
        shareCount > 31 ||
        (threshold == 1 && shareCount != 1)) {
      _fail('invalid-threshold');
    }
    if (identifier == null) {
      Uint8List random;
      try {
        random = Uint8List.fromList(randomBytes(4));
      } catch (_) {
        _fail('rng-failed');
      }
      try {
        if (random.length != 4) _fail('rng-failed');
        identifier = random.map((v) => gf32Alphabet[v & 31]).join();
      } finally {
        random.fillRange(0, random.length, 0);
      }
    }
    if (identifier.length != 4 ||
        identifier.split('').any((v) => !gf32Alphabet.contains(v))) {
      _fail('invalid-identifier');
    }
    final common = Uint8List.fromList([
      1,
      format.index,
      length >> 5,
      length & 31,
      threshold,
      ...identifier.split('').map(gf32Alphabet.indexOf),
    ]);
    final names = indices == null
        ? gf32Alphabet.replaceAll('s', '').split('').take(shareCount).toList()
        : List<String>.of(indices);
    if (names.length != shareCount) _fail('wrong-share-count');
    payload = Uint8List.fromList([
      ...owned,
      ..._validation(owned, common, format),
    ]);
    symbols = bytesToGf32Symbols(payload);
    rows = splitGf32Symbols(
      payload: symbols,
      threshold: threshold,
      indices: names,
      randomBytes: randomBytes,
    );
    final encoded = List<String>.generate(rows.length, (i) {
      final data = [...common, gf32Alphabet.indexOf(names[i]), ...rows[i]];
      return 'fr1${[...data, ...createLongBchChecksum('fr', data)].map((v) => gf32Alphabet[v]).join()}';
    });
    // Match Frank's writer verification before returning paper backups.
    for (var first = 0; first < encoded.length; first++) {
      final recovered = recoverFrankShares(
        List.generate(
          threshold,
          (offset) => encoded[(first + offset) % encoded.length],
        ),
      );
      try {
        var difference = 0;
        for (var i = 0; i < owned.length; i++) {
          difference |= owned[i] ^ recovered.bytes[i];
        }
        if (difference != 0) _fail('confirmation-mismatch');
      } finally {
        recovered.destroy();
      }
    }
    return List.unmodifiable(encoded);
  } finally {
    owned.fillRange(0, owned.length, 0);
    payload?.fillRange(0, payload.length, 0);
    symbols?.fillRange(0, symbols.length, 0);
    for (final row in rows) {
      row.fillRange(0, row.length, 0);
    }
  }
}

FrankRecoveryShare decodeFrankRecoveryShare(String text) {
  if (text != text.toLowerCase() && text != text.toUpperCase()) {
    _fail('bad-format');
  }
  if (text.length != 131 && text.length != 182) _fail('unsupported-length');
  final canonical = text.toLowerCase();
  if (!canonical.startsWith('fr1')) _fail('bad-format');
  final values = canonical
      .substring(3)
      .split('')
      .map(gf32Alphabet.indexOf)
      .toList();
  if (values.any((v) => v < 0)) _fail('bad-format');
  if (!verifyLongBchChecksum('fr', values)) _fail('bad-checksum');
  final kind = values[1],
      length = (values[2] << 5) | values[3],
      threshold = values[4];
  if (values[0] != 1 ||
      (kind != 0 && kind != 1) ||
      length != (kind == 0 ? 32 : 64) ||
      canonical.length != (kind == 0 ? 131 : 182)) {
    _fail('bad-format');
  }
  if (threshold < 1 || threshold > 9) _fail('invalid-threshold');
  final index = gf32Alphabet[values[9]];
  if (index == 's') _fail('invalid-index');
  return FrankRecoveryShare(
    RecoverySecretFormat.values[kind],
    threshold,
    values.sublist(5, 9).map((v) => gf32Alphabet[v]).join(),
    index,
    Uint8List.fromList(values.sublist(0, 9)),
    Uint8List.fromList(values.sublist(10, values.length - 15)),
  );
}

/// Recover one explicitly selected set, using exactly its threshold shares.
/// No candidate guessing, correction, or silent dropping of malformed shares.
RecoveredWalletSecret recoverFrankShares(List<String> encodedShares) {
  final input = List<String>.of(encodedShares);
  if (input.isEmpty || input.length > 9) _fail('wrong-share-count');
  final shares = input.map(decodeFrankRecoveryShare).toList();
  final first = shares.first;
  if (shares.length != first.threshold) _fail('wrong-share-count');
  if (shares.any(
    (s) =>
        s.format != first.format ||
        s.threshold != first.threshold ||
        s.identifier != first.identifier ||
        s._payload.length != first._payload.length,
  )) {
    _fail('inconsistent-share');
  }
  final symbols = interpolateGf32Symbols(
    shares
        .map(
          (s) => Codex32Share(s.threshold, s.identifier, s.index, s._payload),
        )
        .toList(),
    's',
  );
  Uint8List? payload, expected;
  try {
    payload = gf32SymbolsToBytes(symbols, first.byteLength + 32);
    final secret = Uint8List.fromList(payload.sublist(0, first.byteLength));
    try {
      expected = _validation(secret, first._common, first.format);
      var difference = 0;
      for (var i = 0; i < 32; i++) {
        difference |= expected[i] ^ payload[first.byteLength + i];
      }
      if (difference != 0) _fail('confirmation-mismatch');
      return RecoveredWalletSecret(first.format, secret);
    } finally {
      secret.fillRange(0, secret.length, 0);
    }
  } finally {
    symbols.fillRange(0, symbols.length, 0);
    payload?.fillRange(0, payload.length, 0);
    expected?.fillRange(0, expected.length, 0);
  }
}

/// Accept additional shares only if every one belongs to the same polynomial.
/// Corrupted or unrelated shares are rejected rather than silently ignored.
RecoveredWalletSecret recoverFrankBackup(List<String> encodedShares) {
  final input = List<String>.of(encodedShares);
  if (input.isEmpty || input.length > 31) _fail('wrong-share-count');
  final parsed = input.map(decodeFrankRecoveryShare).toList();
  final first = parsed.first;
  if (input.length < first.threshold) _fail('insufficient-shares');
  if (parsed.map((s) => s.index).toSet().length != parsed.length) {
    _fail('duplicate-share');
  }
  if (parsed.any(
    (s) =>
        s.format != first.format ||
        s.threshold != first.threshold ||
        s.identifier != first.identifier,
  )) {
    _fail('inconsistent-share');
  }
  final basis = parsed
      .take(first.threshold)
      .map((s) => Codex32Share(s.threshold, s.identifier, s.index, s._payload))
      .toList();
  for (final extra in parsed.skip(first.threshold)) {
    final expected = interpolateGf32Symbols(basis, extra.index);
    try {
      var difference = 0;
      for (var i = 0; i < expected.length; i++) {
        difference |= expected[i] ^ extra._payload[i];
      }
      if (difference != 0) _fail('inconsistent-share');
    } finally {
      expected.fillRange(0, expected.length, 0);
    }
  }
  return recoverFrankShares(input.take(first.threshold).toList());
}

/// Backs up the exact PBKDF2 seed, including the optional passphrase's effect.
/// Restoring it preserves BIP32 keys but cannot reconstruct the mnemonic words.
List<String> backupBip39Mnemonic(
  String mnemonic, {
  String passphrase = '',
  int threshold = 2,
  int shareCount = 3,
  required BackupRandomBytes randomBytes,
}) {
  final normalized = mnemonic.trim().toLowerCase().replaceAll(
    RegExp(r'\s+'),
    ' ',
  );
  final bip39 = Mnemonic();
  if (!bip39.validateMnemonic(normalized)) _fail('invalid-mnemonic');
  final seed = bip39.toSeed(normalized, passphrase);
  try {
    return exportRecoveryShares(
      format: RecoverySecretFormat.historical,
      secret: seed,
      threshold: threshold,
      shareCount: shareCount,
      randomBytes: randomBytes,
    );
  } finally {
    seed.fillRange(0, seed.length, 0);
  }
}

/// Frozen Frank domain-registry v1 payment seed; not a BIP39 conversion.
Uint8List deriveFrankPaymentSeed(Uint8List accountRoot) {
  final owned = Uint8List.fromList(accountRoot);
  Uint8List? prk;
  Uint8List hmac(Uint8List key, List<int> data) => (HMac(
    SHA256Digest(),
    64,
  )..init(KeyParameter(key))).process(Uint8List.fromList(data));
  List<int> u16(int n) => [n >> 8, n & 255];
  try {
    if (owned.length != 32) _fail('bad-format');
    final registry = _ascii('frank-domain-roots-v1');
    final label = _ascii('frank/domain-root/v1/ecash-bch-wallet');
    prk = hmac(_ascii('frank/domain-root-registry/v1'), owned);
    return hmac(prk, [
      ...u16(registry.length),
      ...registry,
      ...u16(1),
      ...u16(label.length),
      ...label,
      ...u16(32),
      1,
    ]);
  } finally {
    owned.fillRange(0, owned.length, 0);
    prk?.fillRange(0, prk.length, 0);
  }
}
