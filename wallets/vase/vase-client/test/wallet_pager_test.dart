import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import 'package:lotus_dart/lotus.dart';
import 'package:vase/wallet/keys.dart';
import 'package:vase/chronik-client/client.dart';
import 'package:vase/config/theme.dart';
import 'package:vase/features/home/wallet_pager.dart';
import 'package:vase/features/contacts/contacts_model.dart';
import 'package:vase/features/contacts/contacts_page.dart';
import 'secure_storage_test.dart' show MemoryStorage;
import 'package:vase/features/send/send_model.dart';
import 'package:vase/features/wallet/wallet_model.dart';
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
  final _fixture = _FixtureWallet();
  @override
  Wallet get wallet => _fixture;
}

void main() {
  late WalletModel wallet;
  late SendModel send;
  late GoRouter router;
  late ValueChanged<String?> scan;

  Future<void> launch(WidgetTester tester, {String location = '/'}) async {
    wallet = _WalletModel()..balance = WalletBalance(balance: BigInt.zero);
    send = SendModel();
    final contacts = ContactsModel(storage: MemoryStorage({}));
    await contacts.load();
    addTearDown(contacts.dispose);
    router = GoRouter(
      initialLocation: location,
      routes: [
        ...walletPageRoutes(
          contactsBuilder: (back) =>
              ContactsPage(onBack: back, model: contacts),
          scannerBuilder: (onScan) {
            scan = onScan;
            return const ColoredBox(
              key: ValueKey('scanner'),
              color: Colors.black,
            );
          },
        ),
        GoRoute(
          path: '/send',
          builder: (context, _) => Scaffold(
            body: const Text('Payment details'),
            floatingActionButton: IconButton(
              onPressed: () => context.pop(),
              icon: const Icon(Icons.arrow_back),
            ),
          ),
        ),
      ],
    );
    addTearDown(() {
      router.dispose();
      wallet.dispose();
      send.dispose();
    });
    await tester.pumpWidget(
      MultiProvider(
        providers: [
          ChangeNotifierProvider<WalletModel>.value(value: wallet),
          ChangeNotifierProvider<SendModel>.value(value: send),
        ],
        child: MaterialApp.router(
          routerConfig: router,
          theme: AppTheme.lotusTheme,
        ),
      ),
    );
    await tester.pumpAndSettle();
  }

  String location() => router.routeInformationProvider.value.uri.path;

  testWidgets('historical horizontal pages update URLs and pause scanner', (
    tester,
  ) async {
    await launch(tester);
    expect(location(), '/');
    expect(find.byKey(const ValueKey('scanner')), findsOneWidget);
    final oldScan = scan;
    await tester.drag(
      find.byKey(const ValueKey('wallet-pages')),
      const Offset(650, 0),
    );
    await tester.pumpAndSettle();
    expect(location(), '/contacts');
    expect(find.byKey(const ValueKey('scanner')), findsNothing);
    oldScan('15h6MrWynwLTwhhYWNjw1RqCrhvKv3ZBsi?amount=12345');
    await tester.pumpAndSettle();
    expect(location(), '/contacts');
    expect(send.amount, BigInt.zero);
    await tester.drag(
      find.byKey(const ValueKey('wallet-pages')),
      const Offset(-650, 0),
    );
    await tester.pumpAndSettle();
    expect(location(), '/');
    expect(find.byKey(const ValueKey('scanner')), findsOneWidget);
    await tester.drag(
      find.byKey(const ValueKey('wallet-pages')),
      const Offset(-650, 0),
    );
    await tester.pumpAndSettle();
    expect(location(), '/request');
    expect(find.byKey(const ValueKey('scanner')), findsNothing);
  });

  for (final path in ['/contacts', '/request']) {
    testWidgets('direct $path link and Back select the matching page', (
      tester,
    ) async {
      await launch(tester, location: path);
      expect(location(), path);
      expect(find.byKey(const ValueKey('scanner')), findsNothing);
      await tester.tap(find.byIcon(Icons.navigate_before));
      await tester.pumpAndSettle();
      expect(location(), '/');
      expect(find.byKey(const ValueKey('scanner')), findsOneWidget);
    });
  }

  testWidgets('buttons and external route changes retain one pager', (
    tester,
  ) async {
    await launch(tester);
    final pager = tester.state(find.byType(WalletPager));
    await tester.tap(find.byTooltip('Contacts'));
    await tester.pumpAndSettle();
    expect(location(), '/contacts');
    router.go('/request');
    await tester.pumpAndSettle();
    expect(location(), '/request');
    expect(tester.state(find.byType(WalletPager)), same(pager));
    router.go('/');
    await tester.pumpAndSettle();
    expect(find.byKey(const ValueKey('scanner')), findsOneWidget);
    await tester.tap(find.byTooltip('Receive'));
    await tester.pumpAndSettle();
    expect(location(), '/request');
  });

  testWidgets(
    'platform back returns to scanner and browser navigation selects pages',
    (tester) async {
      await launch(tester, location: '/contacts');
      await tester.binding.handlePopRoute();
      await tester.pumpAndSettle();
      expect(location(), '/');
      await router.routeInformationProvider.didPushRouteInformation(
        RouteInformation(uri: Uri.parse('/request')),
      );
      await tester.pumpAndSettle();
      expect(find.text('Request'), findsOneWidget);
      expect(find.byKey(const ValueKey('scanner')), findsNothing);
      await router.routeInformationProvider.didPushRouteInformation(
        RouteInformation(uri: Uri.parse('/')),
      );
      await tester.pumpAndSettle();
      expect(find.byKey(const ValueKey('scanner')), findsOneWidget);
    },
  );

  testWidgets('a new route cancels an in-flight page transition', (
    tester,
  ) async {
    await launch(tester, location: '/contacts');
    router.go('/request');
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 130));
    router.go('/');
    await tester.pumpAndSettle();
    expect(location(), '/');
    expect(find.byKey(const ValueKey('scanner')), findsOneWidget);
    await tester.drag(
      find.byKey(const ValueKey('wallet-pages')),
      const Offset(-650, 0),
    );
    await tester.pumpAndSettle();
    expect(location(), '/request');
  });

  testWidgets('pulling down opens Settings and Back resumes the scanner', (
    tester,
  ) async {
    await launch(tester);
    await tester.drag(
      find.byKey(const ValueKey('scanner')),
      const Offset(0, 180),
    );
    await tester.pumpAndSettle();
    expect(find.text('Settings'), findsOneWidget);
    expect(find.byKey(const ValueKey('scanner')), findsNothing);
    await tester.tap(find.byIcon(Icons.navigate_before));
    await tester.pumpAndSettle();
    expect(find.byKey(const ValueKey('scanner')), findsOneWidget);
  });

  testWidgets(
    'Settings direct link returns to scanner without a previous route',
    (tester) async {
      await launch(tester, location: '/settings');
      expect(find.text('Settings'), findsOneWidget);
      await tester.tap(find.byIcon(Icons.navigate_before));
      await tester.pumpAndSettle();
      expect(location(), '/');
      expect(find.byKey(const ValueKey('scanner')), findsOneWidget);
    },
  );

  testWidgets('payment route returns to scanner without duplicate scan', (
    tester,
  ) async {
    await launch(tester);
    final callback = scan;
    callback('15h6MrWynwLTwhhYWNjw1RqCrhvKv3ZBsi?amount=12345');
    callback('15h6MrWynwLTwhhYWNjw1RqCrhvKv3ZBsi?amount=67890');
    await tester.pumpAndSettle();
    expect(find.text('Payment details'), findsOneWidget);
    expect(send.amount, BigInt.from(12345));
    expect(find.byKey(const ValueKey('scanner')), findsNothing);
    await tester.tap(find.byIcon(Icons.arrow_back));
    await tester.pumpAndSettle();
    expect(location(), '/');
    expect(find.byKey(const ValueKey('scanner')), findsOneWidget);
  });
}
