import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import 'package:vase/chronik-client/client.dart';
import 'package:vase/config/theme.dart';
import 'package:vase/features/home/home_page.dart';
import 'package:vase/features/send/send_model.dart';
import 'package:vase/features/wallet/wallet_model.dart';
import 'package:vase/wallet/wallet.dart';

class TestWalletModel extends WalletModel {
  TestWalletModel() : super(ChronikClient('http://localhost:8080'));

  @override
  Future<void> initializeModel() async {}
}

void main() {
  late TestWalletModel wallet;
  late SendModel send;
  late GoRouter router;
  late ValueChanged<String?> scan;

  setUpAll(() async {
    final font = FontLoader('Brandon')
      ..addFont(rootBundle.load('assets/fonts/Brandon-Regular.otf'));
    await font.load();
    final icons = FontLoader('MaterialIcons')
      ..addFont(rootBundle.load('fonts/MaterialIcons-Regular.otf'));
    await icons.load();
  });

  setUp(() {
    wallet = TestWalletModel();
    send = SendModel();
    router = GoRouter(
      routes: [
        GoRoute(
          path: '/',
          builder: (_, __) => HomePage(
            scannerBuilder: (onScan) {
              scan = onScan;
              return const ColoredBox(
                key: ValueKey('scanner'),
                color: Colors.black,
              );
            },
          ),
        ),
        for (final route in ['send', 'settings', 'request'])
          GoRoute(
            path: '/$route',
            builder: (context, _) => Scaffold(
              body: Text('$route details'),
              floatingActionButton: FloatingActionButton(
                onPressed: () => context.pop(),
                child: const Icon(Icons.arrow_back),
              ),
            ),
          ),
      ],
    );
  });

  tearDown(() {
    router.dispose();
    wallet.dispose();
    send.dispose();
  });

  Future<void> launch(WidgetTester tester) async {
    await tester.pumpWidget(
      MultiProvider(
        providers: [
          ChangeNotifierProvider<WalletModel>.value(value: wallet),
          ChangeNotifierProvider<SendModel>.value(value: send),
        ],
        child: RepaintBoundary(
          key: const ValueKey('preview'),
          child: MaterialApp.router(
            debugShowCheckedModeBanner: false,
            routerConfig: router,
            theme: AppTheme.lotusTheme,
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
  }

  testWidgets('opens directly into scanner with original quick actions', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(390, 844);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    wallet.balance = WalletBalance(balance: BigInt.from(123000000));
    await launch(tester);
    expect(find.byKey(const ValueKey('scanner')), findsOneWidget);
    expect(find.text('123 XPI'), findsOneWidget);
    expect(find.byTooltip('Settings'), findsOneWidget);
    expect(find.byTooltip('Send'), findsOneWidget);
    expect(find.byTooltip('Receive'), findsOneWidget);
    expect(find.byType(BottomNavigationBar), findsNothing);
  });

  testWidgets('scan opens details once and resumes camera after return', (
    tester,
  ) async {
    await launch(tester);
    final onScan = scan;
    const address = '15h6MrWynwLTwhhYWNjw1RqCrhvKv3ZBsi';
    onScan('$address?amount=12345');
    onScan('$address?amount=67890');
    await tester.pumpAndSettle();
    expect(send.address, address);
    expect(send.amount, BigInt.from(12345));
    expect(find.text('send details'), findsOneWidget);
    expect(find.byKey(const ValueKey('scanner')), findsNothing);
    await tester.tap(find.byIcon(Icons.arrow_back));
    await tester.pumpAndSettle();
    expect(find.byKey(const ValueKey('scanner')), findsOneWidget);
    expect(router.canPop(), isFalse);
  });

  testWidgets(
    'null, empty, invalid and negative scans keep payment untouched',
    (tester) async {
      await launch(tester);
      scan(null);
      scan('');
      scan('not-an-address');
      scan('15h6MrWynwLTwhhYWNjw1RqCrhvKv3ZBsi?amount=-1');
      await tester.pump();
      expect(send.address, isEmpty);
      expect(send.amount, BigInt.zero);
      expect(find.byKey(const ValueKey('scanner')), findsOneWidget);
      expect(router.canPop(), isFalse);
    },
  );

  testWidgets('manual send, settings and receive return to scanner', (
    tester,
  ) async {
    await launch(tester);
    for (final action in ['Send', 'Settings', 'Receive']) {
      await tester.tap(find.byTooltip(action));
      await tester.pumpAndSettle();
      expect(find.byKey(const ValueKey('scanner')), findsNothing);
      await tester.tap(find.byIcon(Icons.arrow_back));
      await tester.pumpAndSettle();
      expect(find.byKey(const ValueKey('scanner')), findsOneWidget);
    }
  });
}
