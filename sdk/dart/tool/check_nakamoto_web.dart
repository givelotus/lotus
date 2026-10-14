import 'dart:typed_data';

import 'package:hex/hex.dart';
import 'package:lotus_dart/nakamoto.dart';

/// Compile with dart2js and execute with Node to exercise browser-safe integer
/// and checksum operations. No sockets, wallet storage or broadcasts are used.
void main() {
  Uint8List hex(String value) => Uint8List.fromList(HEX.decode(value));
  final key = ChainKey.fromBytes(Uint8List(32)..[31] = 1);
  for (final chain in chains) {
    final address = key.address(chain: chain);
    final text = address.encode();
    if (Address.parse(text, chain: chain).encode() != text) {
      throw StateError('Address round trip failed: ${chain.protocolId}');
    }
    if (ChainKey.fromWif(
          key.toWif(chain: chain),
          chain: chain,
        ).secretBytes[31] !=
        1) {
      throw StateError('WIF round trip failed: ${chain.protocolId}');
    }
    final amount = BigInt.parse('18446744073709551615');
    final transaction = ChainTransaction(
      chain: chain,
      inputs: [ChainTxInput(previousTxId: Uint8List(32), outputIndex: 0)],
      outputs: [
        ChainTxOutput(value: amount, scriptPubKey: address.scriptPubKey),
      ],
    );
    final parsed = ChainTransaction.parse(
      transaction.serialize(),
      chain: chain,
    );
    if (parsed.outputs.single.value != amount ||
        parsed.txid != transaction.txid) {
      throw StateError('Exact uint64 round trip failed: ${chain.protocolId}');
    }
  }
  final bitcoin = getChain('btc-mainnet');
  final witness = Address.fromScriptPubKey(
    hex('001400112233445566778899aabbccddeeff00112233'),
    chain: bitcoin,
  );
  if (witness.encode() != 'bc1qqqgjyv6y24n80zye42aueh0wluqpzg3ndy2ehs') {
    throw StateError('Nakamoto Bech32 fixture mismatch');
  }
  final derived = ChainHDKey.fromSeed(
    hex('000102030405060708090a0b0c0d0e0f'),
  ).derivePath("m/0'/1/2'/2/1000000000").serialize(chain: bitcoin);
  if (derived !=
      'xprvA41z7zogVVwxVSgdKUHDy1SKmdb533PjDz7J6N6mV6uS3ze1ai8FHa8kmHScGpWmj4WggLyQjgPie1rFSruoUihUZREPSL39UNdE3BBDu76') {
    throw StateError('Nakamoto BIP32 fixture mismatch');
  }
  final schnorr = signSchnorrBip340(
    Uint8List(32),
    Uint8List(32)..[31] = 3,
    auxRand: Uint8List(32),
  );
  if (HEX.encode(schnorr) !=
      'e907831f80848d1069a5371b402410364bdf1c5f8307b0084c55f1ce2dca821525f66a4a85ea8b71e482a74f382d2ce5ebeee8fdb2172f477df4900d310536c0') {
    throw StateError('Official BIP340 fixture mismatch');
  }
  print(
    'Nakamoto browser smoke: ${chains.length} networks, exact uint64 amounts',
  );
}
