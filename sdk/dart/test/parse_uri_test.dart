import 'package:lotus_dart/utils/parse_uri.dart';
import 'package:test/test.dart';

void main() {
  test('malformed and negative requested amounts cannot become zero', () {
    for (final amount in ['garbage', '-1', '1.5', '']) {
      expect(
        () => parseSendURI('lotus:invalid?amount=$amount'),
        throwsFormatException,
      );
    }
    expect(parseSendURI('lotus:invalid').amount, BigInt.zero);
    expect(parseSendURI('lotus:invalid?amount=123').amount, BigInt.from(123));
  });
}
