import 'package:flutter_test/flutter_test.dart';
import 'package:vase/wallet/vault.dart';

VaultUtxo coin(int amount, int key, String txid) => VaultUtxo(
      VaultOutpoint(txid, 0, BigInt.from(amount), 1),
      key,
    );

void main() {
  test('vault keeps amounts ordered and totals multiple outputs', () {
    final vault = Vault([coin(20, 0, 'a'), coin(5, 1, 'b'), coin(20, 0, 'c')]);
    expect(vault.keys.toList(), [BigInt.from(5), BigInt.from(20)]);
    expect(vault.calculateBalance(), BigInt.from(45));
    expect(vault.popAt(BigInt.from(20))?.outpoint.transactionId, 'c');
    expect(vault.calculateBalance(), BigInt.from(25));
  });

  test('removing last output leaves empty bucket safe to pop', () {
    final vault = Vault([coin(20, 0, 'a')]);
    vault.removeByKeyIndex(0);
    expect(vault.calculateBalance(), BigInt.zero);
    expect(vault.popAt(BigInt.from(20)), isNull);
    expect(vault.popAt(BigInt.from(20)), isNull);
  });
}
