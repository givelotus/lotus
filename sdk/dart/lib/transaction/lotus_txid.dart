import 'dart:typed_data';
import 'package:buffer/buffer.dart';
import 'package:hex/hex.dart';
import '../encoding/utils.dart';

/// Computes Lotus's merkleized TxId from serialized transaction bytes.
/// Unlocking scripts are excluded; TxHash remains SHA256d of all bytes.
String lotusTxId(List<int> rawTx) {
  final reader = ByteDataReader()..add(rawTx);
  final version = reader.read(4);
  final inputs = <List<int>>[];
  for (var n = readVarIntNum(reader); n > 0; n--) {
    final prevout = reader.read(36);
    reader.read(readVarIntNum(reader));
    inputs.add(sha256Twice([...prevout, ...reader.read(4)]));
  }
  final outputs = <List<int>>[];
  for (var n = readVarIntNum(reader); n > 0; n--) {
    final value = reader.read(8);
    final size = readVarIntNum(reader);
    outputs.add(
      sha256Twice([...value, ...varintBufNum(size), ...reader.read(size)]),
    );
  }
  final locktime = reader.read(4);
  if (reader.remainingLength != 0) {
    throw FormatException('Trailing transaction bytes');
  }
  final inRoot = _merkle(inputs);
  final outRoot = _merkle(outputs);
  return HEX.encode(
    sha256Twice([
      ...version,
      ...inRoot.$1,
      inRoot.$2,
      ...outRoot.$1,
      outRoot.$2,
      ...locktime,
    ]).reversed.toList(),
  );
}

(List<int>, int) _merkle(List<List<int>> leaves) {
  if (leaves.isEmpty) return (Uint8List(32), 0);
  var height = 1;
  while (leaves.length > 1) {
    if (leaves.length.isOdd) leaves.add(Uint8List(32));
    leaves = [
      for (var i = 0; i < leaves.length; i += 2)
        sha256Twice([...leaves[i], ...leaves[i + 1]]),
    ];
    height++;
  }
  return (leaves.single, height);
}
