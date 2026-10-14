import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';
import 'package:hex/hex.dart';
import 'package:test/test.dart';
import 'package:lotus_dart/src/multichain/chains.dart';
import 'package:lotus_dart/src/multichain/transaction.dart';
import 'package:lotus_dart/src/multichain/signing.dart';
import 'package:lotus_dart/src/multichain/block.dart';
import 'package:lotus_dart/src/multichain/keys.dart';
import 'package:lotus_dart/src/multichain/curve.dart';
import 'package:lotus_dart/encoding/utils.dart' as crypto;

void main() {
  final fixtures =
      jsonDecode(File('test/fixtures/nakamoto-parity.json').readAsStringSync())
          as Map<String, dynamic>;
  ChainDescriptor chainFor(String family) =>
      getChain('${family == 'ltc' ? 'litecoin' : family}-mainnet');
  for (final fixture in fixtures['transactions'] as List) {
    final chain = chainFor(fixture['family'] as String);
    test(
      'Nakamoto ${fixture['family']} ${fixture['name']} wire, hashes and digests',
      () {
        final tx = ChainTransaction.fromHex(
          fixture['rawHex'] as String,
          chain: chain,
        );
        expect(tx.toHex(), fixture['rawHex']);
        expect(tx.txid, fixture['txid']);
        expect(tx.wtxid, fixture['hash']);
        final parsed = fixture['parsed'];
        expect(tx.version, parsed['version']);
        expect(tx.locktime, parsed['locktime']);
        for (var i = 0; i < tx.outputs.length; i++) {
          expect(
            tx.outputs[i].value,
            BigInt.parse(parsed['outputs'][i]['value'] as String),
          );
          expect(
            HEX.encode(tx.outputs[i].scriptPubKey),
            parsed['outputs'][i]['scriptPubKeyHex'],
          );
        }
        for (final vector in fixture['sighashes'] as List) {
          final algorithm = switch (vector['algorithm']) {
            'legacy' => SighashAlgorithm.legacy,
            'bip143' => SighashAlgorithm.bip143,
            'forkid' => SighashAlgorithm.forkId,
            _ => null,
          };
          // Explicit unsupported Lotus special digest and historical legacy-XPI.
          if (algorithm == null ||
              (chain.family == ChainFamily.xpi &&
                  algorithm == SighashAlgorithm.legacy)) {
            continue;
          }
          final digest = transactionSignatureHash(
            tx,
            vector['inputIndex'] as int,
            algorithm: algorithm,
            hashType: vector['hashType'] as int,
            scriptCode: HEX.decode(vector['scriptCodeHex'] as String),
            amount: BigInt.parse(vector['amount'] as String),
          );
          expect(HEX.encode(digest), vector['digestHex']);
          expect(
            verifyEcdsa(
              Uint8List.fromList(
                HEX.decode(vector['signatureDerHex'] as String),
              ),
              digest,
              Uint8List.fromList(
                HEX.decode(fixtures['inputs']['publicKeyHex'] as String),
              ),
            ),
            isTrue,
          );
        }
      },
    );
  }
  for (final fixture in fixtures['headers'] as List) {
    test('Nakamoto ${fixture['family']} base-header bytes/hash', () {
      final header = ChainBlockHeader.fromHex(
        fixture['rawHex'] as String,
        chain: chainFor(fixture['family'] as String),
      );
      expect(header.hash, fixture['hash']);
      expect(HEX.encode(header.bytes), fixture['rawHex']);
      expect(
        () => ChainBlockHeader(
          header.bytes,
          chain: getChain(
            header.chain.family == ChainFamily.xpi
                ? 'btc-mainnet'
                : 'xpi-mainnet',
          ),
        ),
        throwsFormatException,
      );
    });
  }
  for (final fixture in fixtures['signedTransactions'] as List) {
    if (fixture['algorithm'] == 'lotus' ||
        (fixture['family'] == 'xpi' && fixture['algorithm'] == 'legacy')) {
      continue;
    }
    test(
      'Nakamoto exact signed bytes ${fixture['family']} ${fixture['kind']} ${fixture['algorithm']} replay=${fixture['replayProtection']}',
      () {
        final tx = ChainTransaction.fromHex(
          fixture['unsignedRawHex'] as String,
          chain: chainFor(fixture['family'] as String),
        );
        final key = ChainKey.fromBytes(
          Uint8List.fromList(HEX.decode(fixture['privateKeyHex'] as String)),
        );
        final algorithm = switch (fixture['algorithm']) {
          'legacy' => SighashAlgorithm.legacy,
          'bip143' => SighashAlgorithm.bip143,
          _ => SighashAlgorithm.forkId,
        };
        final type = fixture['kind'] == 'p2wpkh'
            ? SimpleSpendType.p2wpkh
            : SimpleSpendType.p2pkh;
        ChainTransaction sign(ChainTransaction current, int index) =>
            signTransactionInput(
              current,
              index,
              key: key,
              spentOutput: ChainTxOutput(
                value: BigInt.parse(fixture['spent'][index]['value'] as String),
                scriptPubKey: HEX.decode(
                  fixture['spent'][index]['scriptPubKeyHex'] as String,
                ),
              ),
              spendType: type,
              algorithm: algorithm,
              hashType: fixture['hashType'] as int,
              replayProtection: fixture['replayProtection'] as bool,
            );
        final one = sign(tx, fixture['signInput']['index'] as int);
        expect(one.toHex(), fixture['signInput']['rawHex']);
        var all = tx;
        for (final assignment in fixture['assignments'] as List) {
          all = sign(all, assignment['inputIndex'] as int);
        }
        expect(all.toHex(), fixture['signAll']['rawHex']);
        expect(all.txid, fixture['signAll']['txid']);
        expect(all.wtxid, fixture['signAll']['hash']);
      },
    );
  }
  for (final fixture in fixtures['merkle'] as List) {
    test('Nakamoto Merkle root ${fixture['family']}', () {
      expect(
        HEX.encode(
          chainMerkleRoot(
            (fixture['leavesInternalHex'] as List)
                .map((v) => Uint8List.fromList(HEX.decode(v as String)))
                .toList(),
            chain: chainFor(fixture['family'] as String),
          ),
        ),
        fixture['rootInternalHex'],
      );
    });
  }
  test('chain Merkle odd partner rule and immutable leaves', () {
    final leaves = [
      Uint8List.fromList(List.filled(32, 1)),
      Uint8List.fromList(List.filled(32, 2)),
      Uint8List.fromList(List.filled(32, 3)),
    ];
    final left = chainHash256([...leaves[0], ...leaves[1]]);
    final btc = chainMerkleRoot(leaves, chain: getChain('btc-mainnet'));
    final xpi = chainMerkleRoot(leaves, chain: getChain('xpi-mainnet'));
    expect(
      btc,
      chainHash256([
        ...left,
        ...chainHash256([...leaves[2], ...leaves[2]]),
      ]),
    );
    expect(
      xpi,
      chainHash256([
        ...left,
        ...chainHash256([...leaves[2], ...List.filled(32, 0)]),
      ]),
    );
    expect(leaves.length, 3);
    expect(
      chainMerkleRoot([], chain: getChain('xpi-mainnet')),
      List.filled(32, 0),
    );
    expect(
      () => chainMerkleRoot([Uint8List(31)], chain: getChain('btc-mainnet')),
      throwsArgumentError,
    );
  });
  test('BIP143 official native-P2WPKH digest', () {
    // Public-domain vector: https://github.com/bitcoin/bips/blob/master/bip-0143.mediawiki#native-p2wpkh
    final tx = ChainTransaction.fromHex(
      '0100000002fff7f7881a8099afa6940d42d1e7f6362bec38171ea3edf433541db4e4ad969f0000000000eeffffffef51e1b804cc89d182d279655c3aa89e815b1b309fe287d9b2b55d57b90ec68a0100000000ffffffff02202cb206000000001976a9148280b37df378db99f66f85c95a783a76ac7a6d5988ac9093510d000000001976a9143bde42dbee7e4dbe6a21b2d50ce2f0167faa815988ac11000000',
      chain: getChain('btc-mainnet'),
    );
    expect(
      HEX.encode(
        transactionSignatureHash(
          tx,
          1,
          algorithm: SighashAlgorithm.bip143,
          hashType: 1,
          scriptCode: HEX.decode(
            '76a9141d0f172a0ecb48aee1be1f2687d2963ae33f71a188ac',
          ),
          amount: BigInt.from(600000000),
        ),
      ),
      'c37af31116d1b27caf68aae9e3ac82f1477929014d5b917657d0eb49478cb670',
    );
  });
  test('uint64 exact values, defensive bytes and malformed wire', () {
    final rawInput = List<int>.filled(32, 1);
    final input = ChainTxInput(previousTxId: rawInput, outputIndex: 0);
    rawInput[0] = 2;
    expect(input.previousTxId.first, 1);
    input.previousTxId[0] = 3;
    expect(input.previousTxId.first, 1);
    final value = (BigInt.one << 64) - BigInt.one;
    final tx = ChainTransaction(
      chain: getChain('btc-mainnet'),
      inputs: [input],
      outputs: [ChainTxOutput(value: value, scriptPubKey: [])],
    );
    final bytes = tx.serialize();
    expect(
      ChainTransaction.parse(bytes, chain: tx.chain).outputs.single.value,
      value,
    );
    for (var i = 0; i < bytes.length; i++) {
      expect(
        () => ChainTransaction.parse(bytes.sublist(0, i), chain: tx.chain),
        throwsA(isA<TransactionFormatException>()),
      );
    }
    expect(
      () => ChainTransaction.parse([...bytes, 0], chain: tx.chain),
      throwsA(isA<TransactionFormatException>()),
    );
    expect(
      () => ChainTransaction.parse([
        ...bytes.take(4),
        253,
        1,
        0,
        ...bytes.skip(5),
      ], chain: tx.chain),
      throwsA(isA<TransactionFormatException>()),
    );
    expect(
      () => ChainTxOutput(value: BigInt.one << 64, scriptPubKey: []),
      throwsRangeError,
    );
  });
  test('witness flags, superfluous markers and bounded counts fail closed', () {
    final chain = getChain('btc-mainnet');
    final tx = ChainTransaction(
      chain: chain,
      inputs: [ChainTxInput(previousTxId: List.filled(32, 1), outputIndex: 0)],
      outputs: [],
    );
    final legacy = tx.serialize();
    expect(
      () => ChainTransaction.parse([
        ...legacy.take(4),
        0,
        2,
        ...legacy.skip(4),
      ], chain: chain),
      throwsA(isA<TransactionFormatException>()),
    );
    expect(
      () => ChainTransaction.parse([
        ...legacy.take(4),
        0,
        1,
        ...legacy.skip(4).take(legacy.length - 8),
        0,
        ...legacy.skip(legacy.length - 4),
      ], chain: chain),
      throwsA(isA<TransactionFormatException>()),
    );
    expect(
      () => ChainTransaction.parse([
        2,
        0,
        0,
        0,
        255,
        ...List.filled(8, 255),
      ], chain: chain),
      throwsA(isA<TransactionFormatException>()),
    );
    final witness = tx.copyWith(
      inputs: [
        tx.inputs.single.copyWith(witness: [[]]),
      ],
    );
    expect(
      ChainTransaction.parse(
        witness.serialize(),
        chain: chain,
      ).inputs.single.witness.single,
      isEmpty,
    );
    expect(witness.txid, tx.txid);
    expect(witness.wtxid, isNot(tx.wtxid));
  });
  test('legacy SINGLE bug is distinct from BIP143 out-of-range SINGLE', () {
    final tx = ChainTransaction(
      chain: getChain('btc-mainnet'),
      inputs: [ChainTxInput(previousTxId: List.filled(32, 1), outputIndex: 0)],
      outputs: [],
    );
    final script = [0x76, 0xa9, 20, ...List.filled(20, 0), 0x88, 0xac];
    final legacy = transactionSignatureHash(
      tx,
      0,
      algorithm: SighashAlgorithm.legacy,
      hashType: 3,
      scriptCode: script,
    );
    expect(legacy, [1, ...List.filled(31, 0)]);
    expect(
      transactionSignatureHash(
        tx,
        0,
        algorithm: SighashAlgorithm.bip143,
        hashType: 3,
        scriptCode: script,
        amount: BigInt.one,
      ),
      isNot(legacy),
    );
  });
  test(
    'signed P2PKH on all six chains and P2WPKH BTC/LTC verify independently',
    () {
      final key = ChainKey.fromBytes(
        Uint8List.fromList([...List.filled(31, 0), 1]),
      );
      final hash = crypto.ripemd160(crypto.sha256(key.publicKey));
      for (final family in ChainFamily.values) {
        final chain = chainFor(family.name);
        for (final witness in [
          false,
          if ([ChainFamily.btc, ChainFamily.ltc].contains(family)) true,
        ]) {
          final script = witness
              ? [0, 20, ...hash]
              : [0x76, 0xa9, 20, ...hash, 0x88, 0xac];
          final spent = ChainTxOutput(
            value: BigInt.from(10000),
            scriptPubKey: script,
          );
          final tx = ChainTransaction(
            chain: chain,
            inputs: [
              ChainTxInput(previousTxId: List.filled(32, 7), outputIndex: 0),
            ],
            outputs: [
              ChainTxOutput(value: BigInt.from(9000), scriptPubKey: script),
            ],
          );
          final fork = [
            ChainFamily.bch,
            ChainFamily.xec,
            ChainFamily.xpi,
          ].contains(family);
          final algorithm = witness
              ? SighashAlgorithm.bip143
              : fork
              ? SighashAlgorithm.forkId
              : SighashAlgorithm.legacy;
          final hashType = fork ? 0x41 : 1;
          final signed = signTransactionInput(
            tx,
            0,
            key: key,
            spentOutput: spent,
            spendType: witness ? SimpleSpendType.p2wpkh : SimpleSpendType.p2pkh,
            algorithm: algorithm,
            hashType: hashType,
          );
          final stack = signed.inputs.single.witness;
          final sig = witness
              ? stack.first
              : signed.inputs.single.scriptSig.sublist(
                  1,
                  1 + signed.inputs.single.scriptSig.first,
                );
          final digest = transactionSignatureHash(
            tx,
            0,
            algorithm: algorithm,
            hashType: hashType,
            scriptCode: [0x76, 0xa9, 20, ...hash, 0x88, 0xac],
            amount: spent.value,
          );
          expect(sig.last, hashType);
          expect(
            verifyEcdsa(
              Uint8List.fromList(sig.sublist(0, sig.length - 1)),
              digest,
              key.publicKey,
            ),
            isTrue,
          );
          expect(tx.inputs.single.scriptSig, isEmpty);
          expect(
            ChainTransaction.parse(signed.serialize(), chain: chain).txid,
            signed.txid,
          );
        }
      }
    },
  );
  test('unsupported algorithms and spends fail explicitly', () {
    final tx = ChainTransaction(
      chain: getChain('bch-mainnet'),
      inputs: [ChainTxInput(previousTxId: List.filled(32, 1), outputIndex: 0)],
      outputs: [],
    );
    final script = [0x76, 0xa9, 20, ...List.filled(20, 0), 0x88, 0xac];
    expect(
      () => transactionSignatureHash(
        tx,
        0,
        algorithm: SighashAlgorithm.forkId,
        hashType: 0x61,
        scriptCode: script,
        amount: BigInt.one,
      ),
      throwsA(isA<UnsupportedChainCapability>()),
    );
    expect(
      () => transactionSignatureHash(
        tx,
        0,
        algorithm: SighashAlgorithm.forkId,
        hashType: 0x41,
        scriptCode: script,
        amount: BigInt.one,
        commitUtxos: true,
      ),
      throwsA(isA<UnsupportedChainCapability>()),
    );
    expect(
      () => transactionSignatureHash(
        tx,
        0,
        algorithm: SighashAlgorithm.forkId,
        hashType: 0x41,
        scriptCode: [0x51],
        amount: BigInt.one,
      ),
      throwsA(isA<UnsupportedChainCapability>()),
    );
    expect(
      () => ChainTransaction(
        chain: tx.chain,
        inputs: [
          tx.inputs.single.copyWith(
            witness: [
              [1],
            ],
          ),
        ],
        outputs: [],
      ),
      throwsA(isA<UnsupportedChainCapability>()),
    );
  });
}
