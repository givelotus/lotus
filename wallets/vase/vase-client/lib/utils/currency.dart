import 'package:collection/collection.dart';
import 'package:intl/intl.dart';

const satsPerLotus = 1000000;
const lotusFractionDigits = 6;
final _unit = BigInt.from(satsPerLotus);

/// Canonical editing text is ASCII decimal; localized strings are display only.
/// Ambiguous grouping, exponents, signs, and fractions of a base unit are rejected.
String normalizeLotusInput(String value) {
  final input = value.trim();
  if (input.isEmpty) return '0';
  if (!RegExp(r'^(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)$').hasMatch(input)) {
    throw const FormatException('Expected an unsigned decimal XPI amount');
  }
  final parts = input.split('.');
  final whole = (parts.first.isEmpty ? '0' : parts.first).replaceFirst(
    RegExp(r'^0+(?=[0-9])'),
    '',
  );
  var fraction = parts.length == 2 ? parts[1] : '';
  if (fraction.length > lotusFractionDigits) {
    if (RegExp(r'[1-9]').hasMatch(fraction.substring(lotusFractionDigits))) {
      throw const FormatException('Amount is smaller than one base unit');
    }
    fraction = fraction.substring(0, lotusFractionDigits);
  }
  return parts.length == 2 ? '$whole.$fraction' : whole;
}

BigInt lotusToSats(String amount) {
  final parts = normalizeLotusInput(amount).split('.');
  final fraction = parts.length == 2 ? parts[1] : '';
  return BigInt.parse(parts[0]) * _unit +
      BigInt.parse(fraction.padRight(lotusFractionDigits, '0'));
}

/// Exact, ungrouped decimal for editing and transport, independent of locale.
String satsToLotus(BigInt amount) {
  final magnitude = amount.abs();
  final whole = magnitude ~/ _unit;
  final fraction = (magnitude % _unit)
      .toString()
      .padLeft(lotusFractionDigits, '0')
      .replaceFirst(RegExp(r'0+$'), '');
  final sign = amount.isNegative ? '-' : '';
  return '$sign$whole${fraction.isEmpty ? '' : '.$fraction'}';
}

String formatAmount({
  required BigInt amount,
  int minimumFractionDigits = 0,
  int maximumFractionDigits = lotusFractionDigits,
}) {
  if (minimumFractionDigits < 0 ||
      maximumFractionDigits > lotusFractionDigits ||
      minimumFractionDigits > maximumFractionDigits) {
    throw ArgumentError('Fraction digits must satisfy 0 <= min <= max <= 6');
  }
  final factor = BigInt.from(
    10,
  ).pow(lotusFractionDigits - maximumFractionDigits);
  final magnitude = amount.abs();
  var rounded = magnitude ~/ factor;
  // Presentation uses nearest rounding with ties away from zero. Payment units
  // remain untouched; input and transport never use this rounded display text.
  if ((magnitude % factor) * BigInt.two >= factor) rounded += BigInt.one;
  final scale = BigInt.from(10).pow(maximumFractionDigits);
  final whole = (rounded ~/ scale).toString();
  var fraction = maximumFractionDigits == 0
      ? ''
      : (rounded % scale).toString().padLeft(maximumFractionDigits, '0');
  while (fraction.length > minimumFractionDigits && fraction.endsWith('0')) {
    fraction = fraction.substring(0, fraction.length - 1);
  }
  final format = NumberFormat.decimalPattern();
  final sign = amount.isNegative && rounded != BigInt.zero
      ? format.symbols.MINUS_SIGN
      : '';
  final text =
      '$sign${_groupWhole(whole, format)}'
      '${fraction.isEmpty ? '' : '${format.symbols.DECIMAL_SEP}$fraction'}';
  return '${_localizeDigits(text, format)} XPI';
}

List<String> formatNumpadInput(UnmodifiableListView<String> items) {
  final input = normalizeLotusInput(items.join());
  final parts = input.split('.');
  final format = NumberFormat.decimalPattern();
  final text =
      '${_groupWhole(parts[0], format)}'
      '${parts.length == 2 ? '${format.symbols.DECIMAL_SEP}${parts[1]}' : ''}';
  return _localizeDigits(text, format).split('');
}

String _groupWhole(String digits, NumberFormat format) {
  final pattern = format.symbols.DECIMAL_PATTERN
      .split(';')
      .first
      .split('.')
      .first;
  final groups = pattern.split(',');
  if (groups.length == 1) return digits;
  int width(String group) => RegExp(r'[#0]').allMatches(group).length;
  var groupSize = width(groups.last);
  final secondary = groups.length > 2
      ? width(groups[groups.length - 2])
      : groupSize;
  final result = <String>[];
  var end = digits.length;
  while (end > groupSize && groupSize > 0) {
    result.add(digits.substring(end - groupSize, end));
    end -= groupSize;
    groupSize = secondary;
  }
  result.add(digits.substring(0, end));
  return result.reversed.join(format.symbols.GROUP_SEP);
}

String _localizeDigits(String value, NumberFormat format) {
  final zero = format.symbols.ZERO_DIGIT.codeUnitAt(0);
  if (zero == 48) return value;
  return String.fromCharCodes(
    value.codeUnits.map(
      (code) => code >= 48 && code <= 57 ? zero + code - 48 : code,
    ),
  );
}
