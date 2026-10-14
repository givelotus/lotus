import 'package:collection/collection.dart';
import 'package:flutter/foundation.dart';
import 'package:vase/utils/currency.dart';

const maxIntegerDigits = 19;
const maxLength = maxIntegerDigits + 1 + lotusFractionDigits;

/// Model-owned left-to-right arithmetic. Intermediate fractions stay exact;
/// only completed nonnegative six-decimal results can become payment amounts.
class NumpadModel extends ChangeNotifier {
  String _expression = '0';
  String get expression => _expression;
  UnmodifiableListView<String> get items =>
      UnmodifiableListView(value.split(''));
  String get value {
    if (!_expression.contains(RegExp(r'[+*/-]'))) return _expression;
    final result = _result;
    if (result != null) return satsToLotus(result);
    // Preserve the last complete preview while an operator is being entered.
    if (RegExp(r'[+*/-]$').hasMatch(_expression)) {
      return _decimal(_expression.substring(0, _expression.length - 1)) ?? '0';
    }
    return '0';
  }

  BigInt? get amount => error == null ? _result : null;
  BigInt? get _result => _calculate(_expression)?.units;
  String? get error {
    if (RegExp(r'[+*/-]$').hasMatch(_expression)) {
      return 'Complete the expression';
    }
    final result = _calculate(_expression);
    if (result == null) return 'Cannot divide by zero';
    if (result.numerator < BigInt.zero) return 'Amount cannot be negative';
    if (result.units == null) return 'Result must be exact to six decimals';
    return null;
  }

  String? _decimal(String expression) {
    final units = _calculate(expression)?.units;
    return units == null ? null : satsToLotus(units);
  }

  void setValue(String value) {
    final normalized = normalizeLotusInput(value);
    _checkOperand(normalized);
    _expression = normalized;
    notifyListeners();
  }

  /// External expression changes notify even when their totals are identical.
  void setExpression(String expression) {
    final normalized = _normalize(expression);
    if (normalized.length > 256 ||
        !RegExp(
          r'^\d+(?:\.\d*)?(?:[+*/-]\d+(?:\.\d*)?)*[+*/-]?$',
        ).hasMatch(normalized)) {
      throw const FormatException('Invalid expression');
    }
    for (final operand in normalized.split(RegExp(r'[+*/-]'))) {
      if (operand.isNotEmpty) _checkOperand(operand);
    }
    _expression = normalized;
    notifyListeners();
  }

  static String _normalize(String value) => value
      .replaceAll('➖', '-')
      .replaceAll('−', '-')
      .replaceAll('➕', '+')
      .replaceAll('✖️', '*')
      .replaceAll('×', '*')
      .replaceAll('➗', '/')
      .replaceAll('÷', '/');

  static void _checkOperand(String operand) {
    final parts = operand.split('.');
    if (parts.first.length > maxIntegerDigits ||
        (parts.length == 2 && parts.last.length > lotusFractionDigits)) {
      throw const FormatException('Amount exceeds editing precision');
    }
  }

  bool addValue(String key) {
    key = _normalize(key);
    if (key == '=') return evaluate();
    if (key == 'AC') {
      clear();
      return true;
    }
    if (RegExp(r'^[+*/-]$').hasMatch(key)) {
      if (_expression.length >= 256) return false;
      if (RegExp(r'[+*/-]$').hasMatch(_expression)) {
        _expression = _expression.substring(0, _expression.length - 1) + key;
      } else {
        _expression += key;
      }
      notifyListeners();
      return true;
    }
    if (!RegExp(r'^[0-9.]$').hasMatch(key)) return false;
    final start = _expression.lastIndexOf(RegExp(r'[+*/-]')) + 1;
    final operand = _expression.substring(start);
    if (key == '.' && operand.contains('.')) return false;
    final next = operand.isEmpty && key == '.'
        ? '0.'
        : operand == '0' && key != '.'
        ? key
        : '$operand$key';
    try {
      _checkOperand(next);
    } on FormatException {
      return false;
    }
    final candidate = _expression.substring(0, start) + next;
    if (candidate.length > 256) return false;
    _expression = candidate;
    notifyListeners();
    return true;
  }

  bool evaluate() {
    final units = amount;
    if (units == null) return false;
    // A result may be larger than an individual typed operand; don't truncate it.
    _expression = satsToLotus(units);
    notifyListeners();
    return true;
  }

  void clear() {
    _expression = '0';
    notifyListeners();
  }

  void removeLast() {
    if (_expression == '0') return;
    _expression = _expression.length == 1
        ? '0'
        : _expression.substring(0, _expression.length - 1);
    notifyListeners();
  }
}

class _Fraction {
  _Fraction(BigInt numerator, BigInt denominator)
    : numerator = numerator ~/ numerator.gcd(denominator),
      denominator = denominator ~/ numerator.gcd(denominator);
  final BigInt numerator;
  final BigInt denominator;
  BigInt? get units {
    final scaled = numerator * BigInt.from(1000000);
    return scaled.remainder(denominator) == BigInt.zero
        ? scaled ~/ denominator
        : null;
  }

  static _Fraction decimal(String value) {
    final parts = value.split('.');
    final fraction = parts.length == 2 ? parts.last : '';
    return _Fraction(
      BigInt.parse(parts.first + fraction),
      BigInt.from(10).pow(fraction.length),
    );
  }
}

_Fraction? _calculate(String expression) {
  final tokens = RegExp(
    r'\d+(?:\.\d*)?|[+*/-]',
  ).allMatches(expression).map((match) => match.group(0)!).toList();
  if (tokens.isEmpty || tokens.length.isEven) return null;
  var result = _Fraction.decimal(tokens.first);
  for (var i = 1; i < tokens.length; i += 2) {
    final right = _Fraction.decimal(tokens[i + 1]);
    final a = result.numerator;
    final b = result.denominator;
    final c = right.numerator;
    final d = right.denominator;
    switch (tokens[i]) {
      case '+':
        result = _Fraction(a * d + c * b, b * d);
      case '-':
        result = _Fraction(a * d - c * b, b * d);
      case '*':
        result = _Fraction(a * c, b * d);
      case '/':
        if (c == BigInt.zero) return null;
        result = _Fraction(a * d, b * c);
    }
  }
  return result;
}
