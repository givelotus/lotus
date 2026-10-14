import 'package:lotus_dart/bip39/bip39.dart';
import 'package:test/test.dart';

void main() {
  const phrase =
      'abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about';
  test('BIP39 ASCII reference seed survives normalization dependency update', () {
    expect(
      Mnemonic().toSeedHex(phrase, 'TREZOR'),
      'c55257c360c07c72029aebc1b53c05ed0362ada38ead3e3e9efa3708e53495531f09a6987599d18264c1e1c92f2cf141630c7a3c4ab7c81b2f001698e7463b04',
    );
  });
  test(
    'NFKD composed and compatibility passphrases match independent PBKDF2 vectors',
    () {
      // Expected bytes computed with Python unicodedata.normalize + hashlib.pbkdf2_hmac.
      expect(
        Mnemonic().toSeedHex(phrase, 'é'),
        'f37f8652bf7004d4bd4ba7702e70e647f54965758656423dde58d64fa725c1e8be1b0416864e10f714c0730e46f9676079b4fd4f72fcf0c09a120ae65589c091',
      );
      expect(
        Mnemonic().toSeedHex(phrase, 'e\u0301'),
        'f37f8652bf7004d4bd4ba7702e70e647f54965758656423dde58d64fa725c1e8be1b0416864e10f714c0730e46f9676079b4fd4f72fcf0c09a120ae65589c091',
      );
      expect(
        Mnemonic().toSeedHex(phrase, '㍍ガバヴァぱばぐゞちぢ十人十色'),
        'ba553eedefe76e67e2602dc20184c564010859faada929a090dd2c57aacb204ceefd15404ab50ef3e8dbeae5195aeae64b0def4d2eead1cdc728a33ced520ffd',
      );
    },
  );
}
