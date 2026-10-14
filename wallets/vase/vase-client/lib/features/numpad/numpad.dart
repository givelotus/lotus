import 'package:flutter/material.dart';
import 'package:flutter_vibrate/flutter_vibrate.dart';
import 'package:provider/provider.dart';
import 'package:vase/features/numpad/key_widget.dart';
import 'package:vase/features/numpad/numpad_model.dart';

enum KeyValue {
  Zero,
  One,
  Two,
  Three,
  Four,
  Five,
  Six,
  Seven,
  Eight,
  Nine,
  Period,
  Back,
  add,
  subtract,
  multiply,
  divide,
  clear,
  equals,
}

extension KeyValueExts on KeyValue {
  String get value {
    switch (this) {
      case KeyValue.Zero:
        return '0';
      case KeyValue.One:
        return '1';
      case KeyValue.Two:
        return '2';
      case KeyValue.Three:
        return '3';
      case KeyValue.Four:
        return '4';
      case KeyValue.Five:
        return '5';
      case KeyValue.Six:
        return '6';
      case KeyValue.Seven:
        return '7';
      case KeyValue.Eight:
        return '8';
      case KeyValue.Nine:
        return '9';
      case KeyValue.Period:
        return '.';
      case KeyValue.Back:
        return '<';
      case KeyValue.add:
        return '+';
      case KeyValue.subtract:
        return '−';
      case KeyValue.multiply:
        return '×';
      case KeyValue.divide:
        return '÷';
      case KeyValue.clear:
        return 'AC';
      case KeyValue.equals:
        return '=';
    }
  }
}

final List<List<KeyValue>> rows = [
  [KeyValue.Seven, KeyValue.Eight, KeyValue.Nine, KeyValue.divide],
  [KeyValue.Four, KeyValue.Five, KeyValue.Six, KeyValue.multiply],
  [KeyValue.One, KeyValue.Two, KeyValue.Three, KeyValue.subtract],
  [KeyValue.Period, KeyValue.Zero, KeyValue.Back, KeyValue.add],
  [KeyValue.clear, KeyValue.equals],
];

class NumpadWidget extends StatelessWidget {
  const NumpadWidget({Key? key, required this.controller}) : super(key: key);

  final AnimationController controller;

  void _vibrate() async {
    controller.forward(from: 0);
    if (await Vibrate.canVibrate) {
      Vibrate.feedback(FeedbackType.heavy);
    }
  }

  void Function() _handleClick(NumpadModel model, KeyValue value) => () {
    if (value == KeyValue.Back) {
      if (model.expression != '0') {
        model.removeLast();
      } else {
        _vibrate();
      }
    } else if (!model.addValue(value.value)) {
      _vibrate();
    }
  };

  @override
  Widget build(BuildContext context) {
    final model = context.watch<NumpadModel>();
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        for (final row in rows)
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceAround,
            children: [
              for (final col in row)
                KeyWidget(
                  onPressed: _handleClick(model, col),
                  label: col.value,
                ),
            ],
          ),
      ],
    );
  }
}
