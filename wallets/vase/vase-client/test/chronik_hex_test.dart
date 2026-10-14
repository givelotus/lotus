import 'package:flutter_test/flutter_test.dart';
import 'package:vase/chronik-client/hex.dart';

void main() {
  test('multi-byte hex and reverse hex round trip', () {
    expect(fromHex('01a2ff'), [1, 162, 255]);
    expect(fromHexRev('01a2ff'), [255, 162, 1]);
    expect(toHex(fromHex('01a2ff')), '01a2ff');
    expect(toHexRev(fromHexRev('01a2ff')), '01a2ff');
    expect(fromHex(''), isEmpty);
  });
  test('invalid hex is rejected', () {
    expect(() => fromHex('abc'), throwsFormatException);
    expect(() => fromHex('gg'), throwsFormatException);
  });
}
