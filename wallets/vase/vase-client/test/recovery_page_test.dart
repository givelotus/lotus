import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:vase/chronik-client/client.dart';
import 'package:vase/features/settings/recovery_page.dart';
import 'package:vase/features/wallet/wallet_model.dart';
import 'package:vase/wallet/recovery_material.dart';

const words =
    'abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about';
Uint8List random(int n) =>
    Uint8List.fromList(List.generate(n, (i) => (i * 13 + 9) & 255));

class BackupWallet extends WalletModel {
  BackupWallet()
    : super(ChronikClient('http://unused.invalid'), initialize: false);
  final imports = <({String material, String passphrase})>[];
  @override
  String get seed => words;
  @override
  String get password => 'Secret';
  @override
  bool get initialized => true;
  @override
  Future<void> setSeed(String value, {String password = ''}) async {
    imports.add((material: value, passphrase: password));
  }
}

Future<BackupWallet> mount(WidgetTester tester, {bool restore = true}) async {
  final wallet = BackupWallet();
  addTearDown(wallet.dispose);
  tester.view.physicalSize = const Size(800, 1600);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
  await tester.pumpWidget(
    ChangeNotifierProvider<WalletModel>.value(
      value: wallet,
      child: MaterialApp(home: RecoveryPage(initialRestore: restore)),
    ),
  );
  return wallet;
}

void main() {
  testWidgets(
    'BIP39 import preserves passphrase case and whitespace after confirmation',
    (tester) async {
      final wallet = await mount(tester);
      await tester.enterText(
        find.byKey(const ValueKey('recovery-input')),
        words.toUpperCase(),
      );
      await tester.enterText(
        find.byKey(const ValueKey('recovery-passphrase')),
        ' Secret ',
      );
      await tester.tap(find.widgetWithText(FilledButton, 'Restore'));
      await tester.pumpAndSettle();
      expect(wallet.imports, isEmpty);
      await tester.tap(find.widgetWithText(TextButton, 'Restore wallet'));
      await tester.pumpAndSettle();
      expect(wallet.imports.single, (material: words, passphrase: ' Secret '));
    },
  );
  testWidgets('all matching typed shares restore exact wallet material', (
    tester,
  ) async {
    final wallet = await mount(tester);
    final shares = backupWalletMaterial(words, 'Secret', randomBytes: random);
    await tester.enterText(
      find.byKey(const ValueKey('recovery-input')),
      shares.join('\n'),
    );
    await tester.tap(find.widgetWithText(FilledButton, 'Restore'));
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(TextButton, 'Restore wallet'));
    await tester.pumpAndSettle();
    expect(wallet.imports.single.passphrase, '');
    expect(
      walletSeedBytes(wallet.imports.single.material, ''),
      walletSeedBytes(words, 'Secret'),
    );
  });
  testWidgets('invalid or incomplete shares cannot replace the wallet', (
    tester,
  ) async {
    final wallet = await mount(tester);
    final share = backupWalletMaterial(words, '', randomBytes: random).first;
    await tester.enterText(find.byKey(const ValueKey('recovery-input')), share);
    await tester.tap(find.widgetWithText(FilledButton, 'Restore'));
    await tester.pumpAndSettle();
    expect(find.byKey(const ValueKey('recovery-error')), findsOneWidget);
    expect(find.text('Replace this wallet?'), findsNothing);
    expect(wallet.imports, isEmpty);
  });
  testWidgets('canceling restoration does not commit keys', (tester) async {
    final wallet = await mount(tester);
    await tester.enterText(find.byKey(const ValueKey('recovery-input')), words);
    await tester.tap(find.widgetWithText(FilledButton, 'Restore'));
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(TextButton, 'Cancel'));
    await tester.pumpAndSettle();
    expect(wallet.imports, isEmpty);
  });
  testWidgets(
    'backup needs explicit generation and verifies saved shares without import',
    (tester) async {
      final wallet = await mount(tester, restore: false);
      expect(find.byType(SelectableText), findsNothing);
      await tester.tap(
        find.widgetWithText(FilledButton, 'Generate recovery shares'),
      );
      await tester.pumpAndSettle();
      expect(find.byType(SelectableText), findsNWidgets(3));
      await tester.tap(find.text('Verify saved shares'));
      await tester.pumpAndSettle();
      final shares = backupWalletMaterial(words, 'Secret', randomBytes: random);
      await tester.enterText(
        find.byKey(const ValueKey('verify-shares')),
        shares.join('\n'),
      );
      await tester.tap(find.widgetWithText(TextButton, 'Verify'));
      await tester.pumpAndSettle();
      expect(find.byKey(const ValueKey('backup-verified')), findsOneWidget);
      expect(wallet.imports, isEmpty);
    },
  );
  testWidgets('backgrounding clears shown shares and import input', (
    tester,
  ) async {
    await mount(tester, restore: false);
    await tester.tap(
      find.widgetWithText(FilledButton, 'Generate recovery shares'),
    );
    await tester.pumpAndSettle();
    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.inactive);
    await tester.pumpAndSettle();
    expect(find.byType(SelectableText), findsNothing);
    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.resumed);
    await tester.tap(find.text('Restore'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byKey(const ValueKey('recovery-input')), words);
    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.inactive);
    await tester.pumpAndSettle();
    final input = tester.widget<TextField>(
      find.byKey(const ValueKey('recovery-input')),
    );
    expect(input.controller!.text, '');
    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.resumed);
  });
}
