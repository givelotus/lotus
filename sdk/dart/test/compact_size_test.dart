import 'package:buffer/buffer.dart';
import 'package:lotus_dart/encoding/utils.dart';
import 'package:test/test.dart';

void main() {
  test(
    'CompactSize rejects unsafe unsigned 64-bit values instead of rounding',
    () {
      for (final value in [
        BigInt.parse('9007199254740993'),
        (BigInt.one << 64) - BigInt.one,
      ]) {
        final bytes = [
          255,
          for (var n = 0; n < 8; n++)
            ((value >> (8 * n)) & BigInt.from(255)).toInt(),
        ];
        expect(
          () => readVarIntNum(ByteDataReader()..add(bytes)),
          throwsFormatException,
        );
      }
    },
  );
}
