import 'package:collection/collection.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:intl/intl.dart';
import 'package:vase/utils/currency.dart';

void main() {
  setUp(() => Intl.defaultLocale = 'en_US');
  tearDown(() => Intl.defaultLocale = null);

  test(
    'canonical decimals are locale-independent and extra zero precision is exact',
    () {
      expect(lotusToSats('  .5  '), BigInt.from(500000));
      expect(lotusToSats('1.0000000'), BigInt.from(1000000));
      expect(lotusToSats(''), BigInt.zero);
      expect(() => lotusToSats('1,5'), throwsFormatException);
      expect(
        formatAmount(amount: BigInt.from(-1), maximumFractionDigits: 2),
        '0 XPI',
      );
      expect(
        formatAmount(
          amount: BigInt.from(1000000),
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        ),
        '1.00 XPI',
      );
    },
  );

  test('decimal payment entry does not lose a base unit', () {
    expect(lotusToSats('1.000001'), BigInt.from(1000001));
    expect(lotusToSats('0.000249'), BigInt.from(249));
  });

  test('formatting and editing preserve values beyond double precision', () {
    final amount = BigInt.parse('9007199254740993');
    expect(satsToLotus(amount), '9007199254.740993');
    expect(lotusToSats(satsToLotus(amount)), amount);
    expect(formatAmount(amount: amount), '9,007,199,254.740993 XPI');
  });

  test('formatting does not clamp a BigInt to a native integer', () {
    expect(
      satsToLotus(BigInt.parse('9223372036854775808')),
      '9223372036854.775808',
    );
  });

  test('invalid or sub-unit amounts are rejected, not changed to zero', () {
    for (final invalid in [
      'NaN',
      'Infinity',
      '-1',
      '1e3',
      '1,000.5',
      '0.0000001',
    ]) {
      expect(
        () => lotusToSats(invalid),
        throwsFormatException,
        reason: invalid,
      );
    }
  });

  test('empty keypad is safe and decimal entry keeps its trailing zeros', () {
    expect(formatNumpadInput(UnmodifiableListView<String>([])).join(), '0');
    for (final input in ['0.', '0.000001', '12.3400']) {
      expect(
        formatNumpadInput(UnmodifiableListView(input.split(''))).join(),
        input,
      );
    }
  });

  test('localized display uses the locale separators without reparsing', () {
    Intl.defaultLocale = 'de_DE';
    expect(
      formatNumpadInput(UnmodifiableListView('1234.0500'.split(''))).join(),
      '1.234,0500',
    );
    expect(formatAmount(amount: BigInt.from(1234050000)), '1.234,05 XPI');
    expect(satsToLotus(BigInt.from(1234050000)), '1234.05');
  });

  test('display rounds exactly at the requested decimal boundary', () {
    expect(
      formatAmount(amount: BigInt.from(999999), maximumFractionDigits: 2),
      '1 XPI',
    );
    expect(
      formatAmount(amount: BigInt.from(1005000), maximumFractionDigits: 2),
      '1.01 XPI',
    );
  });
}
