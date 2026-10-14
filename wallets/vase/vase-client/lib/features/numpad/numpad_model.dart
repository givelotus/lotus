import 'package:collection/collection.dart';
import 'package:flutter/foundation.dart';
import 'package:vase/utils/currency.dart';

// Bound editing length without preventing any of the six base-unit decimals.
const maxIntegerDigits = 19;
const maxLength = maxIntegerDigits + 1 + lotusFractionDigits;

class NumpadModel extends ChangeNotifier {
  final List<String> _items = ['0'];

  UnmodifiableListView<String> get items => UnmodifiableListView(_items);
  String get value => _items.join();

  void setValue(String value) {
    final normalized = normalizeLotusInput(value);
    if (normalized.split('.').first.length > maxIntegerDigits) {
      throw const FormatException('Amount has too many integer digits');
    }
    _items
      ..clear()
      ..addAll(normalized.split(''));
    notifyListeners();
  }

  bool addValue(String key) {
    if (!RegExp(r'^[0-9.]$').hasMatch(key)) return false;
    if (key == '.' && value.contains('.')) return false;
    final candidate = value == '0' && key != '.' ? key : '$value$key';
    final parts = candidate.split('.');
    if (parts.first.length > maxIntegerDigits ||
        (parts.length == 2 && parts[1].length > lotusFractionDigits)) {
      return false;
    }
    _items
      ..clear()
      ..addAll(candidate.split(''));
    notifyListeners();
    return true;
  }

  void removeLast() {
    if (_items.length == 1 && _items.first == '0') return;
    _items.removeLast();
    if (_items.isEmpty) _items.add('0');
    notifyListeners();
  }
}
