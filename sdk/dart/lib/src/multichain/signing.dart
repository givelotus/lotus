import 'dart:typed_data';
import '../../encoding/utils.dart' as crypto;
import 'chains.dart';
import 'curve.dart';
import 'keys.dart';
import 'transaction.dart';

enum SighashAlgorithm { legacy, bip143, forkId }

enum SimpleSpendType { p2pkh, p2wpkh }

/// Restricted digest API: custom scripts, Taproot, CashTokens and
/// SIGHASH_LOTUS are deliberately outside this implementation.
Uint8List transactionSignatureHash(
  ChainTransaction tx,
  int inputIndex, {
  required SighashAlgorithm algorithm,
  required int hashType,
  required List<int> scriptCode,
  BigInt? amount,
  bool replayProtection = false,
  bool commitUtxos = false,
}) {
  if (inputIndex < 0 || inputIndex >= tx.inputs.length) {
    throw RangeError.index(inputIndex, tx.inputs);
  }
  final base = hashType & 0x1f;
  if (![1, 2, 3].contains(base) ||
      hashType < 0 ||
      hashType > 255 ||
      (hashType & 0x20) != 0) {
    throw UnsupportedChainCapability(
      tx.chain.protocolId,
      'sighash type $hashType',
    );
  }
  if (commitUtxos) {
    throw UnsupportedChainCapability(
      tx.chain.protocolId,
      'CashTokens SIGHASH_UTXOS',
    );
  }
  final forkFamily = [
    ChainFamily.bch,
    ChainFamily.xec,
    ChainFamily.xpi,
  ].contains(tx.chain.family);
  if ((algorithm == SighashAlgorithm.forkId &&
          (!forkFamily || (hashType & 0x40) == 0)) ||
      (algorithm != SighashAlgorithm.forkId && (hashType & 0x40) != 0) ||
      (algorithm == SighashAlgorithm.bip143 && !tx.supportsWitness) ||
      (algorithm == SighashAlgorithm.legacy && forkFamily)) {
    throw UnsupportedChainCapability(
      tx.chain.protocolId,
      'selected sighash algorithm',
    );
  }
  if (replayProtection &&
      (tx.chain.family != ChainFamily.xpi ||
          algorithm != SighashAlgorithm.forkId)) {
    throw UnsupportedChainCapability(
      tx.chain.protocolId,
      'Ruth replay protection',
    );
  }
  // Restrict to standard P2PKH scriptCode. A general script API would need
  // execution-context OP_CODESEPARATOR and FindAndDelete semantics.
  if (!_isP2pkh(scriptCode)) {
    throw UnsupportedChainCapability(tx.chain.protocolId, 'custom scriptCode');
  }
  final anyone = (hashType & 0x80) != 0;
  final input = tx.inputs[inputIndex];
  final version = chainU32(
    tx.version < 0 ? tx.version + 0x100000000 : tx.version,
  );
  if (algorithm == SighashAlgorithm.legacy) {
    if (base == 3 && inputIndex >= tx.outputs.length) {
      return Uint8List.fromList([1, ...List.filled(31, 0)]);
    }
    final indexes = anyone
        ? [inputIndex]
        : List.generate(tx.inputs.length, (i) => i);
    final outputCount = base == 2
        ? 0
        : base == 3
        ? inputIndex + 1
        : tx.outputs.length;
    return chainHash256([
      ...version,
      ...chainCompactSize(indexes.length),
      for (final i in indexes) ...[
        ...tx.inputs[i].outpointBytes,
        ...chainVarBytes(i == inputIndex ? scriptCode : []),
        ...chainU32(i != inputIndex && base != 1 ? 0 : tx.inputs[i].sequence),
      ],
      ...chainCompactSize(outputCount),
      for (var i = 0; i < outputCount; i++) ...[
        if (base == 3 && i != inputIndex) ...[
          ...List.filled(8, 255),
          0,
        ] else
          ...tx.outputs[i].serialized,
      ],
      ...chainU32(tx.locktime),
      ...chainU32(hashType),
    ]);
  }
  if (amount == null) {
    throw ArgumentError('BIP143/forkId requires the spent output amount');
  }
  final zero = List.filled(32, 0);
  final prevouts = anyone
      ? zero
      : chainHash256([for (final i in tx.inputs) ...i.outpointBytes]);
  final sequences = anyone || base != 1
      ? zero
      : chainHash256([for (final i in tx.inputs) ...chainU32(i.sequence)]);
  final outputHash = base == 1
      ? chainHash256([for (final o in tx.outputs) ...o.serialized])
      : base == 3 && inputIndex < tx.outputs.length
      ? chainHash256(tx.outputs[inputIndex].serialized)
      : zero;
  var committedType = BigInt.from(hashType);
  if (replayProtection) {
    final fork = (committedType >> 8) & BigInt.from(0xffffff);
    committedType =
        ((BigInt.from(0xff0000) | (fork ^ BigInt.from(0xdead))) << 8) |
        (committedType & BigInt.from(255));
  }
  return chainHash256([
    ...version,
    ...prevouts,
    ...sequences,
    ...input.outpointBytes,
    ...chainVarBytes(scriptCode),
    ...chainUintLE(amount, 8),
    ...chainU32(input.sequence),
    ...outputHash,
    ...chainU32(tx.locktime),
    ...chainUintLE(committedType, 4),
  ]);
}

bool _isP2pkh(List<int> script) =>
    script.length == 25 &&
    script[0] == 0x76 &&
    script[1] == 0xa9 &&
    script[2] == 20 &&
    script[23] == 0x88 &&
    script[24] == 0xac;
bool _same(List<int> a, List<int> b) =>
    a.length == b.length &&
    List.generate(a.length, (i) => a[i] == b[i]).every((v) => v);
List<int> _push(List<int> bytes) {
  if (bytes.length > 75) throw ArgumentError('Only short pushes supported');
  return [bytes.length, ...bytes];
}

/// Signs exactly one standard input and returns a new transaction. No UTXO
/// discovery, reservation or broadcast is performed. Verify chain/UTXO facts
/// independently before signing; this method cannot establish their truth.
ChainTransaction signTransactionInput(
  ChainTransaction tx,
  int inputIndex, {
  required ChainKey key,
  required ChainTxOutput spentOutput,
  required SimpleSpendType spendType,
  required SighashAlgorithm algorithm,
  required int hashType,
  bool replayProtection = false,
}) {
  final publicKey = key.publicKey;
  final hash = crypto.ripemd160(crypto.sha256(publicKey));
  final p2pkh = [0x76, 0xa9, 20, ...hash, 0x88, 0xac];
  if (spendType == SimpleSpendType.p2wpkh) {
    if (!tx.supportsWitness ||
        publicKey.length != 33 ||
        algorithm != SighashAlgorithm.bip143 ||
        !_same(spentOutput.scriptPubKey, [0, 20, ...hash])) {
      throw UnsupportedChainCapability(
        tx.chain.protocolId,
        'P2WPKH spend/key/algorithm',
      );
    }
  } else if (!_same(spentOutput.scriptPubKey, p2pkh) ||
      algorithm == SighashAlgorithm.bip143) {
    throw UnsupportedChainCapability(
      tx.chain.protocolId,
      'P2PKH spend/key/algorithm',
    );
  }
  final digest = transactionSignatureHash(
    tx,
    inputIndex,
    algorithm: algorithm,
    hashType: hashType,
    scriptCode: p2pkh,
    amount: spentOutput.value,
    replayProtection: replayProtection,
  );
  final signature = [...signEcdsa(digest, key.secretBytes), hashType];
  final inputs = [...tx.inputs];
  inputs[inputIndex] = inputs[inputIndex].copyWith(
    scriptSig: spendType == SimpleSpendType.p2pkh
        ? [..._push(signature), ..._push(publicKey)]
        : [],
    witness: spendType == SimpleSpendType.p2wpkh ? [signature, publicKey] : [],
  );
  return tx.copyWith(inputs: inputs);
}
