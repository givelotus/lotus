// Layout preview: no camera, storage initialization, telemetry, or live backend.
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import 'package:vase/chronik-client/client.dart';
import 'package:vase/config/theme.dart';
import 'package:vase/features/home/home_page.dart';
import 'package:vase/features/numpad/numpad_model.dart';
import 'package:vase/features/request/request_page.dart';
import 'package:vase/features/send/send_model.dart';
import 'package:vase/features/send/send_page.dart';
import 'package:vase/features/settings/settings_page.dart';
import 'package:vase/features/wallet/wallet_model.dart';
import 'package:vase/wallet/wallet.dart';

class PreviewWallet extends WalletModel {
  PreviewWallet() : super(ChronikClient('http://127.0.0.1:1')) {
    balance = WalletBalance(balance: BigInt.from(123000000));
  }

  @override
  Future<void> initializeModel() async {}
}

void main() {
  final router = GoRouter(
    routes: [
      GoRoute(
        path: '/',
        builder: (_, __) => HomePage(
          scannerBuilder: (_) => const ColoredBox(color: Color(0xff303438)),
        ),
      ),
      GoRoute(path: '/send', builder: (_, __) => const SendPage()),
      GoRoute(path: '/request', builder: (_, __) => const RequestPage()),
      GoRoute(path: '/settings', builder: (_, __) => const SettingsPage()),
    ],
  );
  runApp(
    MultiProvider(
      providers: [
        ChangeNotifierProvider<WalletModel>(create: (_) => PreviewWallet()),
        ChangeNotifierProvider(create: (_) => SendModel()),
        ChangeNotifierProvider(create: (_) => NumpadModel()),
      ],
      child: MaterialApp.router(
        debugShowCheckedModeBanner: false,
        theme: AppTheme.lotusTheme,
        routerConfig: router,
      ),
    ),
  );
}
