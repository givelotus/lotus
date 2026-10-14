// Regenerate the descriptor section from the independently exported Frank fixture.
// Run from sdk/dart: dart run tool/generate_nakamoto_chains.dart [--check]
import 'dart:convert';
import 'dart:io';

String literal(Object? value) {
  if (value == null) return 'null';
  if (value is String) {
    return "'${value.replaceAll(r'\', r'\\').replaceAll("'", r"\'").replaceAll(r'$', r'\$').replaceAll('\n', r'\n').replaceAll('\r', r'\r')}'";
  }
  if (value is List) return '[${value.map(literal).join(',')}]';
  if (value is Map) {
    return '{${value.entries.map((e) => '${literal(e.key)}:${literal(e.value)}').join(',')}}';
  }
  return '$value';
}

Future<void> main(List<String> args) async {
  if (args.any((a) => a != '--check')) {
    throw ArgumentError('Only --check is supported');
  }
  final fixture =
      jsonDecode(File('test/fixtures/nakamoto-parity.json').readAsStringSync())
          as Map;
  if (fixture['frankCommit'] != '8c9e38f46ee429826ff918df6eb79214a06af98c') {
    throw StateError('Review a new Frank pin before regenerating descriptors');
  }
  const start = '// BEGIN GENERATED NAKAMOTO DESCRIPTORS';
  const end = '// END GENERATED NAKAMOTO DESCRIPTORS';
  final output = StringBuffer('$start\nconst chains = <ChainDescriptor>[\n');
  for (final entry in fixture['chains'] as List) {
    final d = entry['descriptor'] as Map;
    final positional = [
      literal(d['protocolId']),
      'ChainFamily.${d['family']}',
      'NetworkKind.${d['network']}',
      for (final field in [
        'pubkeyHashVersion',
        'scriptHashVersion',
        'wifVersion',
        'hdPublicVersion',
        'hdPrivateVersion',
        'registeredSlip44',
      ])
        literal(d[field]),
    ];
    final named = [
      for (final field in ['bech32Hrp', 'cashaddrPrefix', 'lotusNetChar'])
        '$field:${literal(d[field])}',
      'facts:${literal(d)}',
    ];
    output.writeln('ChainDescriptor(${[...positional, ...named].join(',')}),');
  }
  output.write('];\n$end');
  final target = File('lib/src/multichain/chains.dart');
  final original = target.readAsStringSync();
  final updated = original.replaceRange(
    original.indexOf(start),
    original.indexOf(end) + end.length,
    output.toString(),
  );
  final formatter = await Process.start(Platform.resolvedExecutable, [
    'format',
    '--output=show',
    '--summary=none',
    '--stdin-name=lib/src/multichain/chains.dart',
  ]);
  formatter.stdin.write(updated);
  await formatter.stdin.close();
  final formatted = await utf8.decoder.bind(formatter.stdout).join();
  final errors = await utf8.decoder.bind(formatter.stderr).join();
  if (await formatter.exitCode != 0) {
    throw StateError('Formatting failed: $errors');
  }
  if (args.contains('--check')) {
    if (formatted != original) {
      throw StateError('Descriptor table differs; regenerate it');
    }
    stdout.writeln('All 16 pinned Nakamoto descriptors match');
  } else {
    target.writeAsStringSync(formatted);
  }
}
