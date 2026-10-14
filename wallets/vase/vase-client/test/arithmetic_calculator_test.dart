import 'package:flutter_test/flutter_test.dart';
import 'package:vase/features/numpad/numpad_model.dart';

void main() {
  NumpadModel calculator() {
    final model = NumpadModel();
    addTearDown(model.dispose);
    return model;
  }

  test(
    'historical subtraction button evaluates instead of dropping operand',
    () {
      final model = calculator()..setExpression('8➖2');
      expect(model.amount, BigInt.from(6000000));
      expect(model.value, '6');
    },
  );

  test(
    'chained operations use the historical left-to-right calculator order',
    () {
      final model = calculator()..setExpression('8-2+3*4');
      expect(model.value, '36');
      expect(model.amount, BigInt.from(36000000));
      model.evaluate();
      expect(model.expression, '36');
      expect(model.value, '36');
    },
  );

  test(
    'fractional intermediate results are exact before payment conversion',
    () {
      final model = calculator()..setExpression('1/3*3');
      expect(model.value, '1');
      expect(model.amount, BigInt.from(1000000));
      expect(model.error, isNull);
    },
  );

  test('decimal arithmetic preserves single base units', () {
    final model = calculator()..setExpression('1.000001-1');
    expect(model.value, '0.000001');
    expect(model.amount, BigInt.one);
    model.setExpression('0.000249+0.000001');
    expect(model.value, '0.00025');
    expect(model.amount, BigInt.from(250));
  });

  test('large values do not pass through floating point', () {
    final model = calculator()
      ..setExpression('9007199254740993.000001-9007199254740993');
    expect(model.value, '0.000001');
    expect(model.amount, BigInt.one);
  });

  for (final expression in ['8/0', '1/3', '0.000001/2', '2-8', '8+']) {
    test('unpayable expression cannot expose a stale amount: $expression', () {
      final model = calculator()..setValue('25');
      expect(model.amount, BigInt.from(25000000));
      model.setExpression(expression);
      expect(model.amount, isNull);
      expect(model.error, isNotNull);
    });
  }

  test(
    'invalid intermediate payment can recover in a completed expression',
    () {
      final model = calculator()..setExpression('2-8+10');
      expect(model.amount, BigInt.from(4000000));
      model.setExpression('0.000001/2*2');
      expect(model.amount, BigInt.one);
    },
  );

  test(
    'external expression changes notify even when the total is unchanged',
    () {
      final model = calculator()..setExpression('1+2');
      var notifications = 0;
      model.addListener(() => notifications++);
      model.setExpression('6/2');
      expect(model.expression, '6/2');
      expect(model.amount, BigInt.from(3000000));
      expect(notifications, 1);
    },
  );

  test('external amount resets pending expression and units stay decimal', () {
    final model = calculator()..setExpression('4+');
    model.setValue('1.000001');
    expect(model.expression, '1.000001');
    expect(model.amount, BigInt.from(1000001));
    expect(model.error, isNull);
  });

  test('typing another operator replaces a pending operator', () {
    final model = calculator()..setValue('8');
    expect(model.addValue('+'), isTrue);
    expect(model.addValue('*'), isTrue);
    expect(model.addValue('2'), isTrue);
    expect(model.amount, BigInt.from(16000000));
  });

  test('clear and backspace keep expression and computed amount in sync', () {
    final model = calculator()..setExpression('12+3');
    model.removeLast();
    expect(model.expression, '12+');
    expect(model.amount, isNull);
    model.removeLast();
    expect(model.expression, '12');
    expect(model.amount, BigInt.from(12000000));
    model.clear();
    expect(model.expression, '0');
    expect(model.amount, BigInt.zero);
    expect(model.error, isNull);
  });

  test('an invalid key cannot mutate or notify calculator state', () {
    final model = calculator()..setExpression('2+3');
    var notifications = 0;
    model.addListener(() => notifications++);
    expect(model.addValue('NaN'), isFalse);
    expect(model.expression, '2+3');
    expect(model.amount, BigInt.from(5000000));
    expect(notifications, 0);
  });

  test('evaluating an unpayable expression preserves editable input', () {
    final model = calculator()..setExpression('1/3');
    var notifications = 0;
    model.addListener(() => notifications++);
    expect(model.evaluate(), isFalse);
    expect(model.expression, '1/3');
    expect(model.amount, isNull);
    expect(notifications, 0);
    model.addValue('*');
    model.addValue('3');
    expect(model.evaluate(), isTrue);
    expect(model.expression, '1');
    expect(model.amount, BigInt.from(1000000));
  });

  test(
    'malformed external expressions leave the previous amount untouched',
    () {
      final model = calculator()..setExpression('3+4');
      var notifications = 0;
      model.addListener(() => notifications++);
      for (final input in [
        'NaN',
        '1e6',
        '1++2',
        '1,000',
        '(2+3)',
        '1.0000001',
      ]) {
        expect(() => model.setExpression(input), throwsFormatException);
        expect(model.expression, '3+4');
        expect(model.amount, BigInt.from(7000000));
      }
      expect(notifications, 0);
    },
  );

  test('decimal precision and duplicate points are checked per operand', () {
    final model = calculator()..setExpression('1.000001+');
    for (final key in '.000001'.split('')) {
      expect(model.addValue(key), isTrue);
    }
    expect(model.expression, '1.000001+0.000001');
    expect(model.amount, BigInt.from(1000002));
    expect(model.addValue('.'), isFalse);
    expect(model.addValue('2'), isFalse);
    expect(model.amount, BigInt.from(1000002));
  });
}
