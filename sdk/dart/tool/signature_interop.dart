import 'dart:convert';
import 'dart:io';
import 'package:hex/hex.dart';
import 'package:lotus_dart/lotus.dart';

/// Offline interoperability vectors. Key 1 is a public test key, never a wallet.
void main(List<String> args) {
  if (args.length == 2 && args.first == 'verify') {
    final document = jsonDecode(File(args[1]).readAsStringSync()) as Map;
    final key = BCHPublicKey.fromHex(document['publicKey'] as String);
    final signatures = document['signatures'] as List;
    for (final item in signatures) {
      final sig = BCHSignature.fromDER(item['der'] as String, publicKey: key);
      if (!sig.verify(item['digest'] as String) || sig.verify('00' * 32)) {
        throw StateError('Independent signature verification failed');
      }
    }
    print('Dart verified ${signatures.length} OpenSSL-generated signatures');
    return;
  }
  if (args.isNotEmpty) throw ArgumentError('Use no args or verify FILE');
  final key = BCHPrivateKey.fromBigInt(BigInt.one);
  final signatures = <Map<String, String>>[];
  for (var i = 0; i < 512; i++) {
    final digest = HEX.encode(sha256([i & 255, i >> 8]));
    final signer = BCHSignature.fromPrivateKey(key);
    final der = signer.sign(digest, forCompact: true);
    signatures.add({
      'digest': digest,
      'der': der,
      'compact': HEX.encode(signer.toCompact()),
      'r': signer.rHex!,
      's': signer.sHex!,
    });
  }
  final fixture =
      jsonDecode(
            File('test/fixtures/legacy_forkid_digest.json').readAsStringSync(),
          )
          as Map;
  final digest = fixture['digest'] as String;
  final signer = BCHSignature.fromPrivateKey(key);
  signatures.add({
    'digest': digest,
    'der': signer.sign(digest, forCompact: true),
    'compact': HEX.encode(signer.toCompact()),
    'r': signer.rHex!,
    's': signer.sHex!,
  });
  print(
    jsonEncode({'publicKey': key.publicKey!.toHex(), 'signatures': signatures}),
  );
}
