import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';
import 'package:hex/hex.dart';
import 'package:test/test.dart';
import 'package:lotus_dart/encoding/base58check.dart' as base58;
import 'package:lotus_dart/encoding/utils.dart' as hashes;
import 'package:lotus_dart/src/multichain/chains.dart';
import 'package:lotus_dart/src/multichain/addresses.dart';
import 'package:lotus_dart/src/multichain/keys.dart';
import 'package:lotus_dart/src/multichain/hd.dart';

Uint8List bytes(String hex) => Uint8List.fromList(HEX.decode(hex));
void main() {
  final fixture =
      jsonDecode(File('test/fixtures/nakamoto-parity.json').readAsStringSync())
          as Map<String, dynamic>;
  final inputs = fixture['inputs'] as Map<String, dynamic>;
  test('canonical chain identity rejects aliases and unknown chains', () {
    expect(chains.length, 16);
    expect(() => getChain('ltc-mainnet'), throwsArgumentError);
    expect(() => getChain('doge-regtest'), throwsArgumentError);
  });
  for (final entry in fixture['chains'] as List) {
    final d = entry['descriptor'] as Map<String, dynamic>;
    final chain = getChain(d['protocolId'] as String);
    test(
      '${chain.protocolId}: exact descriptor, addresses, WIF, BIP32 parity',
      () {
        expect(chain.facts, d);
        expect(chain.family.name, d['family']);
        expect(chain.network.name, d['network']);
        for (final address in entry['addresses'] as List) {
          final script = bytes(address['scriptHex'] as String);
          final built = Address.fromScriptPubKey(script, chain: chain);
          for (final form in address['forms'] as List) {
            final encoding = AddressEncoding.values.byName(
              form['encoding'] as String,
            );
            expect(built.encode(encoding: encoding), form['text']);
            expect(
              Address.parse(form['text'] as String, chain: chain).scriptPubKey,
              script,
            );
          }
        }
        for (final compressed in [true, false]) {
          final key = ChainKey.fromBytes(
            bytes(inputs['privateKeyHex']),
            compressed: compressed,
          );
          final wif =
              entry[compressed ? 'wifCompressed' : 'wifUncompressed'] as String;
          expect(key.toWif(chain: chain), wif);
          expect(
            ChainKey.fromWif(wif, chain: chain).secretBytes,
            key.secretBytes,
          );
        }
        final key = ChainKey.fromBytes(bytes(inputs['privateKeyHex']));
        expect(HEX.encode(key.publicKey), inputs['publicKeyHex']);
        final hd = ChainHDKey.fromSeed(bytes(inputs['seedHex']));
        final expected = entry['hd'];
        expect(hd.serialize(chain: chain), expected['masterPrivate']);
        expect(hd.neuter().serialize(chain: chain), expected['masterPublic']);
        final derived = hd.derivePath(inputs['hdPath']);
        expect(derived.serialize(chain: chain), expected['derivedPrivate']);
        expect(
          derived.neuter().serialize(chain: chain),
          expected['derivedPublic'],
        );
        expect(
          ChainHDKey.parse(
            expected['derivedPrivate'],
            chain: chain,
          ).serialize(chain: chain),
          expected['derivedPrivate'],
        );
        expect(
          ChainHDKey.parse(
            expected['derivedPublic'],
            chain: chain,
          ).serialize(chain: chain),
          expected['derivedPublic'],
        );
        expect(
          hd.derive(17).neuter().serialize(chain: chain),
          hd.neuter().derive(17).serialize(chain: chain),
        );
      },
    );
  }
  test('strict private scalar, WIF network, HD and mutation rejection', () {
    final btc = getChain('btc-mainnet'), doge = getChain('doge-mainnet');
    expect(() => ChainKey.fromBytes(Uint8List(32)), throwsFormatException);
    expect(
      () => ChainKey.fromBytes(Uint8List.fromList(List.filled(32, 255))),
      throwsFormatException,
    );
    final secret = bytes(inputs['privateKeyHex']);
    final key = ChainKey.fromBytes(secret);
    secret.fillRange(0, 32, 0);
    final returned = key.secretBytes;
    returned.fillRange(0, 32, 0);
    expect(key.secretBytes.last, 1);
    expect(
      () => ChainKey.fromWif(key.toWif(chain: btc), chain: doge),
      throwsFormatException,
    );
    final hd = ChainHDKey.fromSeed(bytes(inputs['seedHex']));
    expect(() => hd.neuter().derive(0x80000000), throwsStateError);
    expect(() => hd.derivePath('m/01'), throwsFormatException);
    expect(() => hd.derivePath('m/2147483648'), throwsFormatException);
    expect(
      () => ChainHDKey.parse(hd.serialize(chain: btc), chain: doge),
      throwsFormatException,
    );
    final a = key.address(chain: btc);
    final script = a.scriptPubKey;
    script.fillRange(0, script.length, 0);
    expect(a.scriptPubKey.first, 0x76);
    expect(() => Address.parse(a.encode(), chain: doge), throwsFormatException);
    expect(
      () => key.address(chain: doge, type: AddressType.p2wpkh),
      throwsA(isA<UnsupportedChainCapability>()),
    );
  });
  test('address and extended keys reject noncanonical/off-curve points', () {
    final btc = getChain('btc-mainnet');
    final badPoints = [
      Uint8List.fromList([2, ...List.filled(32, 255)]),
      Uint8List.fromList([4, ...List.filled(64, 0)]),
    ];
    for (final point in badPoints) {
      expect(
        () => Address.fromPublicKey(point, chain: btc),
        throwsFormatException,
      );
    }
    final hd = ChainHDKey.fromSeed(bytes(inputs['seedHex']));
    final body = base58.decodeChecked(hd.neuter().serialize(chain: btc));
    body.setRange(45, 78, badPoints.first);
    final invalid = base58.encode([
      ...body,
      ...hashes.sha256Twice(body).take(4),
    ]);
    expect(() => ChainHDKey.parse(invalid, chain: btc), throwsFormatException);
    expect(
      () => (btc.facts['header'] as Map)['kind'] = 'other',
      throwsUnsupportedError,
    );
    expect(
      () => btc.identityProbes.first['kind'] = 'other',
      throwsUnsupportedError,
    );
  });
  test('BIP350 checksum distinction and explicit taproot output key', () {
    final chain = getChain('btc-mainnet');
    final script = Uint8List.fromList([
      0x51,
      32,
      ...bytes(inputs['publicKeyHex']).sublist(1),
    ]);
    final a = Address.fromScriptPubKey(script, chain: chain);
    expect(Address.parse(a.encode(), chain: chain).scriptPubKey, script);
    expect(
      () => a.encode(encoding: AddressEncoding.bech32),
      throwsA(isA<UnsupportedChainCapability>()),
    );
    expect(
      () => Address.fromPublicKey(
        bytes(inputs['publicKeyHex']),
        chain: chain,
        type: AddressType.p2tr,
      ),
      throwsA(isA<UnsupportedChainCapability>()),
    );
    expect(
      () => Address.parse(a.encode().replaceFirst('bc1', 'bC1'), chain: chain),
      throwsFormatException,
    );
  });
}
