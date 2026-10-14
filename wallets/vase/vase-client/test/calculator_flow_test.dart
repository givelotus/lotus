import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import 'package:qr_flutter/qr_flutter.dart';
import 'package:lotus_dart/lotus.dart';
import 'package:vase/chronik-client/client.dart';
import 'package:vase/features/home/home_page.dart';
import 'package:vase/features/numpad/key_widget.dart';
import 'package:vase/features/numpad/numpad_model.dart';
import 'package:vase/features/numpad/numpad_view.dart';
import 'package:vase/features/send/send_model.dart';
import 'package:vase/features/send/send_page.dart';
import 'package:vase/features/request/request_page.dart';
import 'package:vase/features/wallet/wallet_model.dart';
import 'package:vase/wallet/keys.dart';
import 'package:vase/wallet/wallet.dart';

class _FixtureWallet implements Wallet {
  @override
  final Keys keys = Keys(
    null,
    null,
    HDPrivateKey.fromSeed('000102030405060708090a0b0c0d0e0f', NetworkType.MAIN),
    [KeyInfo(key: BCHPrivateKey.fromBigInt(BigInt.one), keyIndex: 0)],
  );
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _WalletModel extends WalletModel {
  _WalletModel()
    : super(ChronikClient('http://unused.invalid'), initialize: false);
  final fixture = _FixtureWallet();
  @override
  Wallet get wallet => fixture;
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late _WalletModel wallet;
  late SendModel send;
  String? copied;
  setUp(() {
    wallet = _WalletModel()
      ..balance = WalletBalance(balance: BigInt.from(20000000));
    send = SendModel();
    copied = null;
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(SystemChannels.platform, (call) async {
          if (call.method == 'Clipboard.setData') {
            copied = (call.arguments as Map)['text'] as String;
          }
          if (call.method == 'Clipboard.getData') return {'text': copied};
          return null;
        });
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(
          const MethodChannel('vibrate'),
          (_) async => false,
        );
  });
  tearDown(() {
    wallet.dispose();
    send.dispose();
  });

  Widget app(Widget child) => MultiProvider(
    providers: [
      ChangeNotifierProvider<WalletModel>.value(value: wallet),
      ChangeNotifierProvider<SendModel>.value(value: send),
    ],
    child: MaterialApp(home: child),
  );

  Future<void> key(WidgetTester tester, String label) async {
    await tester.tap(find.widgetWithText(KeyWidget, label));
    await tester.pump();
  }

  testWidgets(
    'draft survives rebuild, cancellation does not commit, reopen uses committed amount',
    (tester) async {
      send.setAmount(BigInt.from(1000001));
      await tester.pumpWidget(app(const SendPage()));
      await tester.tap(
        find
            .ancestor(
              of: find.text('1.000001 XPI'),
              matching: find.byType(InkWell),
            )
            .first,
      );
      await tester.pumpAndSettle();
      for (final label in ['+', '2']) {
        await key(tester, label);
      }
      expect(find.text('1.000001+2'), findsOneWidget);
      // Rebuilding the caller must not create another expression or event listener.
      wallet.notifyListeners();
      await tester.pump();
      expect(find.text('1.000001+2'), findsOneWidget);
      expect(send.amount, BigInt.from(1000001));
      Navigator.of(tester.element(find.byType(NumpadView))).pop();
      await tester.pumpAndSettle();
      expect(send.amount, BigInt.from(1000001));
      await tester.tap(
        find
            .ancestor(
              of: find.text('1.000001 XPI'),
              matching: find.byType(InkWell),
            )
            .first,
      );
      await tester.pumpAndSettle();
      expect(find.text('1.000001+2'), findsNothing);
      await key(tester, '+');
      await key(tester, '2');
      await tester.tap(find.text('Done'));
      await tester.pumpAndSettle();
      expect(send.amount, BigInt.from(3000001));
      expect(find.byType(NumpadView), findsNothing);
    },
  );

  testWidgets(
    'same-total expression changes update preview across rebuilds once',
    (tester) async {
      final draft = NumpadModel()..setExpression('1+1');
      addTearDown(draft.dispose);
      var events = 0;
      draft.addListener(() => events++);
      await tester.pumpWidget(
        app(
          ChangeNotifierProvider.value(
            value: draft,
            child: Scaffold(body: NumpadView(onAmountDone: (_) {})),
          ),
        ),
      );
      draft.setExpression('4/2');
      await tester.pump();
      expect(find.text('4/2'), findsOneWidget);
      expect(find.text('1+1'), findsNothing);
      wallet.notifyListeners();
      await tester.pump();
      await key(tester, '+');
      await key(tester, '1');
      expect(events, 3);
      expect(draft.amount, BigInt.from(3000000));
    },
  );

  testWidgets(
    'request amount has no send balance dependency and copy matches QR units',
    (tester) async {
      wallet.balance = WalletBalance(balance: BigInt.zero);
      send.setPayment('unchanged', BigInt.from(7));
      await tester.pumpWidget(app(const RequestPage()));
      await tester.tap(find.text('Set request amount'));
      await tester.pumpAndSettle();
      for (final label in ['1', '+', '2']) {
        await key(tester, label);
      }
      await tester.tap(find.text('Done'));
      await tester.pumpAndSettle();
      expect(find.byType(QrImageView), findsOneWidget);
      expect(find.text('3 XPI'), findsOneWidget);
      expect(send.amount, BigInt.from(7));
      expect(send.address, 'unchanged');
      await tester.tap(find.byIcon(Icons.copy));
      await tester.pump();
      final uri = Uri.parse(copied!);
      expect(uri.queryParameters['amount'], '3000000');
      expect(uri.toString(), startsWith('lotus_'));
    },
  );

  testWidgets('division by zero never transfers stale amount through Done', (
    tester,
  ) async {
    var completions = 0;
    final draft = NumpadModel()..setExpression('8/0');
    addTearDown(draft.dispose);
    await tester.pumpWidget(
      app(
        ChangeNotifierProvider.value(
          value: draft,
          child: Scaffold(body: NumpadView(onAmountDone: (_) => completions++)),
        ),
      ),
    );
    await tester.tap(find.text('Done'));
    await tester.pumpAndSettle();
    expect(completions, 0);
    expect(find.text('Cannot divide by zero'), findsOneWidget);
  });

  testWidgets(
    'paste replaces address and amount atomically, editor uses decimal XPI',
    (tester) async {
      send.setPayment('old-address', BigInt.from(99));
      var events = 0;
      send.addListener(() => events++);
      copied = '15h6MrWynwLTwhhYWNjw1RqCrhvKv3ZBsi?amount=249';
      await tester.pumpWidget(app(const SendPage()));
      await tester.tap(find.byIcon(Icons.paste));
      await tester.pumpAndSettle();
      expect(send.amount, BigInt.from(249));
      expect(send.address, '15h6MrWynwLTwhhYWNjw1RqCrhvKv3ZBsi');
      expect(events, 1);
      await tester.tap(
        find
            .ancestor(
              of: find.text('0.000249 XPI'),
              matching: find.byType(InkWell),
            )
            .first,
      );
      await tester.pumpAndSettle();
      expect(
        tester
            .widget<Text>(find.byKey(const ValueKey('calculator-expression')))
            .data,
        '0.000249',
      );
    },
  );

  testWidgets(
    'rapid Done taps commit one event, compact screen has no overflow',
    (tester) async {
      tester.view.physicalSize = const Size(390, 640);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      var completed = 0;
      final draft = NumpadModel()..setExpression('8-2');
      addTearDown(draft.dispose);
      await tester.pumpWidget(
        app(
          ChangeNotifierProvider.value(
            value: draft,
            child: Scaffold(body: NumpadView(onAmountDone: (_) => completed++)),
          ),
        ),
      );
      await tester.tap(find.text('Done'));
      await tester.tap(find.text('Done'));
      await tester.pumpAndSettle();
      expect(completed, 1);
      expect(tester.takeException(), isNull);
    },
  );

  for (final size in [const Size(390, 640), const Size(390, 844)]) {
    testWidgets('validation preserves calculator geometry at $size', (
      tester,
    ) async {
      tester.view.physicalSize = size;
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      final semantics = tester.ensureSemantics();
      try {
        final draft = NumpadModel()..setExpression('20');
        addTearDown(draft.dispose);
        await tester.pumpWidget(
          app(
            ChangeNotifierProvider.value(
              value: draft,
              child: Scaffold(body: NumpadView(onAmountDone: (_) {})),
            ),
          ),
        );
        final result = find.byKey(const ValueKey('calculator-result'));
        final expression = find.byKey(const ValueKey('calculator-expression'));
        final digit = find.widgetWithText(KeyWidget, '2');
        final done = find.widgetWithText(ElevatedButton, 'Done');
        final baseline = [
          result,
          expression,
          digit,
          done,
        ].map(tester.getCenter).toList();
        for (final input in ['20+', '20/0', '20', '20/3', '20']) {
          draft.setExpression(input);
          await tester.pumpAndSettle();
          final actual = [
            result,
            expression,
            digit,
            done,
          ].map(tester.getCenter).toList();
          for (var index = 0; index < baseline.length; index++) {
            // Text width can change, but vertical geometry must remain fixed.
            expect(
              actual[index].dy,
              closeTo(baseline[index].dy, 0.01),
              reason: input,
            );
          }
          final error = tester.widget<Text>(
            find.byKey(const ValueKey('calculator-error')),
          );
          expect(error.data, draft.error ?? '');
          expect(tester.takeException(), isNull);
        }
        draft.setExpression('20+');
        await tester.pumpAndSettle();
        expect(
          find.bySemanticsLabel('Complete the expression'),
          findsOneWidget,
        );
        expect(
          tester.getSemantics(find.text('Complete the expression')),
          matchesSemantics(
            label: 'Complete the expression',
            isLiveRegion: true,
            textDirection: TextDirection.ltr,
          ),
        );
      } finally {
        semantics.dispose();
      }
    });
  }

  testWidgets(
    'scan amount opens calculator in decimal units, then manual send clears prior payment',
    (tester) async {
      late ValueChanged<String?> scan;
      final router = GoRouter(
        routes: [
          GoRoute(
            path: '/',
            builder: (_, _) => HomePage(
              scannerBuilder: (callback) {
                scan = callback;
                return const ColoredBox(color: Colors.black);
              },
            ),
          ),
          GoRoute(path: '/send', builder: (_, _) => const SendPage()),
        ],
      );
      addTearDown(router.dispose);
      await tester.pumpWidget(
        MultiProvider(
          providers: [
            ChangeNotifierProvider<WalletModel>.value(value: wallet),
            ChangeNotifierProvider<SendModel>.value(value: send),
          ],
          child: MaterialApp.router(routerConfig: router),
        ),
      );
      scan('15h6MrWynwLTwhhYWNjw1RqCrhvKv3ZBsi?amount=1000001');
      await tester.pumpAndSettle();
      expect(send.amount, BigInt.from(1000001));
      await tester.tap(
        find
            .ancestor(
              of: find.text('1.000001 XPI'),
              matching: find.byType(InkWell),
            )
            .first,
      );
      await tester.pumpAndSettle();
      expect(
        tester
            .widget<Text>(find.byKey(const ValueKey('calculator-expression')))
            .data,
        '1.000001',
      );
      Navigator.of(tester.element(find.byType(NumpadView))).pop();
      await tester.pumpAndSettle();
      router.pop();
      await tester.pumpAndSettle();
      await tester.tap(find.byTooltip('Send'));
      await tester.pumpAndSettle();
      expect(send.amount, BigInt.zero);
      expect(send.address, isEmpty);
    },
  );
}
