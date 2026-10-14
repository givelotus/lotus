import 'package:test/test.dart';

import 'package:lotus_dart/encoding/base32.dart';

void main() {
  test('can encode to base32', () async {
    final base32encoded = 'qpzry9x8gf2tvdw0s3jn54khce6mua7l';

    var address = toBase32(List<int>.generate(32, (i) => i));
    expect(address, base32encoded);
  });

  test('can decode base32', () async {
    final base32encoded = 'qpzry9x8gf2tvdw0s3jn54khce6mua7l';

    var address = fromBase32(base32encoded);

    expect(address, List<int>.generate(32, (i) => i));
  });

  test('can encode and decode', () async {
    var runes = List<int>.from(List<int>.generate(32, (i) => i));
    runes.shuffle();

    var encoded = toBase32(runes);
    var decoded = fromBase32(encoded);

    expect(decoded, runes);
  });
}
