import 'package:flutter_test/flutter_test.dart';
import 'package:vase/features/numpad/numpad_model.dart';

void main() {
  test('smallest base unit can be entered one key at a time', () {
    final model = NumpadModel();
    for (final key in '.000001'.split('')) {
      model.addValue(key);
    }
    expect(model.value, '0.000001');
  });

  test('clearing then entering a decimal has one leading zero', () {
    final model = NumpadModel()..setValue('');
    expect(model.value, '0');
    model.addValue('.');
    model.addValue('5');
    expect(model.value, '0.5');
    for (var i = 0; i < 5; i++) {
      model.removeLast();
    }
    expect(model.value, '0');
  });

  test(
    'model rejects duplicate decimals, operators and invalid pasted text',
    () {
      final model = NumpadModel()..setValue('12.34');
      model.addValue('.');
      model.addValue('+');
      expect(model.value, '12.34');
      expect(() => model.setValue('NaN'), throwsFormatException);
      expect(model.value, '12.34');
    },
  );

  test(
    'pasted exact values remain editable beyond the old seven-character cap',
    () {
      final model = NumpadModel()..setValue('12345678.123456');
      model.removeLast();
      model.addValue('9');
      expect(model.value, '12345678.123459');
    },
  );
}
