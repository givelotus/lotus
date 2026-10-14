/// Chain-explicit Bitcoin-family primitives matching Frank's Nakamoto concepts.
///
/// This entry point is browser safe. Network clients remain separate imports:
/// `chronik.dart` supports browsers; `electrum.dart` requires `dart:io`.
/// Existing Lotus applications may continue importing `lotus.dart` unchanged.
library;

export 'src/multichain/chains.dart';
export 'src/multichain/addresses.dart';
export 'src/multichain/keys.dart';
export 'src/multichain/hd.dart';
export 'src/multichain/transaction.dart'
    show
        ChainTransaction,
        ChainTxInput,
        ChainTxOutput,
        TransactionFormatException,
        chainMerkleRoot;
export 'src/multichain/signing.dart';
export 'src/multichain/block.dart';
export 'src/multichain/curve.dart';
