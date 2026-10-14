import 'dart:typed_data';
import 'package:hex/hex.dart';
import '../../encoding/utils.dart' as crypto;
import 'chains.dart';

/// A structurally invalid wire transaction (not a consensus verdict).
class TransactionFormatException implements FormatException {
  @override
  final String message;
  @override
  final int? offset;
  @override
  final dynamic source = null;
  TransactionFormatException(this.message, [this.offset]);
  @override
  String toString() => 'TransactionFormatException: $message';
}

Uint8List chainHash256(List<int> bytes) =>
    Uint8List.fromList(crypto.sha256Twice(bytes));
Uint8List chainUintLE(BigInt value, int width) {
  if (value < BigInt.zero || value >= (BigInt.one << (width * 8))) {
    throw RangeError('Unsigned integer does not fit $width bytes');
  }
  return Uint8List.fromList(
    List.generate(
      width,
      (i) => ((value >> (i * 8)) & BigInt.from(255)).toInt(),
    ),
  );
}

List<int> chainU32(int value) => chainUintLE(BigInt.from(value), 4);
List<int> chainCompactSize(int value) {
  if (value < 0) throw RangeError.value(value);
  if (value < 253) return [value];
  if (value <= 0xffff) return [253, ...chainUintLE(BigInt.from(value), 2)];
  if (value <= 0xffffffff) return [254, ...chainU32(value)];
  return [255, ...chainUintLE(BigInt.from(value), 8)];
}

List<int> chainVarBytes(List<int> value) => [
  ...chainCompactSize(value.length),
  ...value,
];
Uint8List _bytes(List<int> value) {
  if (value.any((b) => b < 0 || b > 255)) throw RangeError('Invalid byte');
  return Uint8List.fromList(value);
}

class ChainTxInput {
  final Uint8List _previousTxId;
  final int outputIndex;
  final Uint8List _scriptSig;
  final int sequence;
  final List<Uint8List> _witness;

  /// previousTxId uses raw/internal hash order, never explorer display order.
  ChainTxInput({
    required List<int> previousTxId,
    required this.outputIndex,
    List<int> scriptSig = const [],
    this.sequence = 0xffffffff,
    List<List<int>> witness = const [],
  }) : _previousTxId = _bytes(previousTxId),
       _scriptSig = _bytes(scriptSig),
       _witness = witness.map(_bytes).toList(growable: false) {
    if (_previousTxId.length != 32) {
      throw ArgumentError('Expected 32-byte previousTxId');
    }
    chainU32(outputIndex);
    chainU32(sequence);
  }
  factory ChainTxInput.fromDisplayTxId({
    required String txid,
    required int outputIndex,
    List<int> scriptSig = const [],
    int sequence = 0xffffffff,
    List<List<int>> witness = const [],
  }) => ChainTxInput(
    previousTxId: HEX.decode(txid).reversed.toList(),
    outputIndex: outputIndex,
    scriptSig: scriptSig,
    sequence: sequence,
    witness: witness,
  );
  Uint8List get previousTxId => Uint8List.fromList(_previousTxId);
  String get displayTxId => HEX.encode(_previousTxId.reversed.toList());
  Uint8List get scriptSig => Uint8List.fromList(_scriptSig);
  List<Uint8List> get witness =>
      List.unmodifiable(_witness.map((b) => Uint8List.fromList(b)));
  List<int> get outpointBytes => [..._previousTxId, ...chainU32(outputIndex)];
  List<int> get serialized => [
    ...outpointBytes,
    ...chainVarBytes(_scriptSig),
    ...chainU32(sequence),
  ];
  ChainTxInput copyWith({
    List<int>? scriptSig,
    int? sequence,
    List<List<int>>? witness,
  }) => ChainTxInput(
    previousTxId: _previousTxId,
    outputIndex: outputIndex,
    scriptSig: scriptSig ?? _scriptSig,
    sequence: sequence ?? this.sequence,
    witness: witness ?? _witness,
  );
}

class ChainTxOutput {
  final BigInt value;
  final Uint8List _scriptPubKey;

  /// Integer base units. No double or JavaScript-number conversion is used.
  ChainTxOutput({required this.value, required List<int> scriptPubKey})
    : _scriptPubKey = _bytes(scriptPubKey) {
    chainUintLE(value, 8);
  }
  Uint8List get scriptPubKey => Uint8List.fromList(_scriptPubKey);
  List<int> get serialized => [
    ...chainUintLE(value, 8),
    ...chainVarBytes(_scriptPubKey),
  ];
}

/// Chain-explicit wire codec. Parsing does not validate scripts or consensus.
class ChainTransaction {
  final ChainDescriptor chain;
  final int version;
  final List<ChainTxInput> inputs;
  final List<ChainTxOutput> outputs;
  final int locktime;
  ChainTransaction({
    required this.chain,
    this.version = 2,
    required List<ChainTxInput> inputs,
    required List<ChainTxOutput> outputs,
    this.locktime = 0,
  }) : inputs = List.unmodifiable(inputs),
       outputs = List.unmodifiable(outputs) {
    if (version < -0x80000000 || version > 0x7fffffff) {
      throw RangeError.value(version);
    }
    chainU32(locktime);
    if (hasWitness && !supportsWitness) {
      throw UnsupportedChainCapability(chain.protocolId, 'segwit');
    }
  }
  bool get supportsWitness =>
      chain.family == ChainFamily.btc || chain.family == ChainFamily.ltc;
  bool get hasWitness => inputs.any((i) => i._witness.isNotEmpty);
  Uint8List serialize({bool includeWitness = true}) {
    final witness = hasWitness && includeWitness;
    return Uint8List.fromList([
      ...chainU32(version < 0 ? version + 0x100000000 : version),
      if (witness) ...[0, 1],
      ...chainCompactSize(inputs.length),
      for (final input in inputs) ...input.serialized,
      ...chainCompactSize(outputs.length),
      for (final output in outputs) ...output.serialized,
      if (witness)
        for (final input in inputs) ...[
          ...chainCompactSize(input._witness.length),
          for (final item in input._witness) ...chainVarBytes(item),
        ],
      ...chainU32(locktime),
    ]);
  }

  String toHex({bool includeWitness = true}) =>
      HEX.encode(serialize(includeWitness: includeWitness));
  factory ChainTransaction.fromHex(
    String hex, {
    required ChainDescriptor chain,
  }) => ChainTransaction.parse(HEX.decode(hex), chain: chain);
  factory ChainTransaction.parse(
    List<int> bytes, {
    required ChainDescriptor chain,
  }) {
    final r = _Reader(_bytes(bytes));
    final bits = r.integer(4).toInt();
    var count = r.count();
    var witness = false;
    var empty = false;
    if ((chain.family == ChainFamily.btc || chain.family == ChainFamily.ltc) &&
        count == 0) {
      final flag = r.byte();
      if (flag == 1) {
        witness = true;
        count = r.count();
      } else if (flag == 0) {
        empty = true;
      } else {
        throw TransactionFormatException('Unknown witness flag', r.offset - 1);
      }
    }
    final inputs = <ChainTxInput>[];
    for (var i = 0; i < count; i++) {
      inputs.add(
        ChainTxInput(
          previousTxId: r.read(32),
          outputIndex: r.integer(4).toInt(),
          scriptSig: r.varBytes(),
          sequence: r.integer(4).toInt(),
        ),
      );
    }
    final outputs = <ChainTxOutput>[];
    final outputCount = empty ? 0 : r.count();
    for (var i = 0; i < outputCount; i++) {
      outputs.add(
        ChainTxOutput(value: r.integer(8), scriptPubKey: r.varBytes()),
      );
    }
    if (witness) {
      for (var i = 0; i < inputs.length; i++) {
        final stackCount = r.count();
        inputs[i] = inputs[i].copyWith(
          witness: List.generate(stackCount, (_) => r.varBytes()),
        );
      }
      if (!inputs.any((i) => i._witness.isNotEmpty)) {
        throw TransactionFormatException('Superfluous witness marker');
      }
    }
    final locktime = r.integer(4).toInt();
    if (r.offset != bytes.length) {
      throw TransactionFormatException('Trailing transaction bytes', r.offset);
    }
    return ChainTransaction(
      chain: chain,
      version: bits > 0x7fffffff ? bits - 0x100000000 : bits,
      inputs: inputs,
      outputs: outputs,
      locktime: locktime,
    );
  }
  Uint8List get transactionHashBytes => chainHash256(serialize());
  Uint8List get witnessTransactionIdBytes => transactionHashBytes;
  Uint8List get transactionIdBytes {
    if (chain.family != ChainFamily.xpi) {
      return chainHash256(serialize(includeWitness: false));
    }
    final ins = _merkle(
      inputs
          .map(
            (i) => chainHash256([...i.outpointBytes, ...chainU32(i.sequence)]),
          )
          .toList(),
    );
    final outs = _merkle(
      outputs.map((o) => chainHash256(o.serialized)).toList(),
    );
    return chainHash256([
      ...chainU32(version < 0 ? version + 0x100000000 : version),
      ...ins.$1,
      ins.$2,
      ...outs.$1,
      outs.$2,
      ...chainU32(locktime),
    ]);
  }

  String get txid => HEX.encode(transactionIdBytes.reversed.toList());
  String get wtxid => HEX.encode(witnessTransactionIdBytes.reversed.toList());
  Uint8List get blockMerkleLeaf => chain.family == ChainFamily.xpi
      ? chainHash256([...transactionHashBytes, ...transactionIdBytes])
      : transactionIdBytes;
  ChainTransaction copyWith({
    List<ChainTxInput>? inputs,
    List<ChainTxOutput>? outputs,
  }) => ChainTransaction(
    chain: chain,
    version: version,
    inputs: inputs ?? this.inputs,
    outputs: outputs ?? this.outputs,
    locktime: locktime,
  );
}

(Uint8List, int) _merkle(List<Uint8List> leaves) {
  if (leaves.isEmpty) return (Uint8List(32), 0);
  var height = 1;
  while (leaves.length > 1) {
    if (leaves.length.isOdd) leaves.add(Uint8List(32));
    leaves = [
      for (var i = 0; i < leaves.length; i += 2)
        chainHash256([...leaves[i], ...leaves[i + 1]]),
    ];
    height++;
  }
  return (leaves.single, height);
}

class _Reader {
  final Uint8List bytes;
  int offset = 0;
  _Reader(this.bytes);
  Uint8List read(int length) {
    if (length < 0 || length > bytes.length - offset) {
      throw TransactionFormatException('Truncated transaction', offset);
    }
    final value = Uint8List.fromList(bytes.sublist(offset, offset + length));
    offset += length;
    return value;
  }

  int byte() => read(1).single;
  BigInt integer(int width) => read(
    width,
  ).reversed.fold(BigInt.zero, (n, b) => (n << 8) | BigInt.from(b));
  int count() {
    final prefix = byte();
    final value = prefix < 253
        ? BigInt.from(prefix)
        : integer(
            prefix == 253
                ? 2
                : prefix == 254
                ? 4
                : 8,
          );
    if ((prefix == 253 && value < BigInt.from(253)) ||
        (prefix == 254 && value <= BigInt.from(0xffff)) ||
        (prefix == 255 && value <= BigInt.from(0xffffffff))) {
      throw TransactionFormatException('Noncanonical CompactSize', offset);
    }
    if (value > BigInt.from(bytes.length - offset)) {
      throw TransactionFormatException('Count exceeds remaining bytes', offset);
    }
    return value.toInt();
  }

  Uint8List varBytes() => read(count());
}

/// Merkle root of raw/internal 32-byte hashes. Lotus pads an odd layer with
/// zero; Bitcoin-family chains repeat the last leaf. Empty trees return zero.
Uint8List chainMerkleRoot(
  List<Uint8List> leaves, {
  required ChainDescriptor chain,
}) {
  var layer = leaves.map((leaf) {
    if (leaf.length != 32) {
      throw ArgumentError('Merkle leaves must be 32 bytes');
    }
    return Uint8List.fromList(leaf);
  }).toList();
  if (layer.isEmpty) return Uint8List(32);
  while (layer.length > 1) {
    if (layer.length.isOdd) {
      layer.add(chain.family == ChainFamily.xpi ? Uint8List(32) : layer.last);
    }
    layer = [
      for (var i = 0; i < layer.length; i += 2)
        chainHash256([...layer[i], ...layer[i + 1]]),
    ];
  }
  return Uint8List.fromList(layer.single);
}
