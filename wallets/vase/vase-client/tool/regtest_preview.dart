// Developer-only UI harness. Install only on a separate disposable simulator.
// Public fixture keys; refuses every chain except the Lotus regtest genesis.
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:hex/hex.dart';
import 'package:http/http.dart' as http;
import 'package:lotus_dart/chronik.dart' as proto;
import 'package:lotus_dart/lotus.dart';
import 'package:provider/provider.dart';
import 'package:vase/chronik-client/client.dart';
import 'package:vase/config/theme.dart';
import 'package:vase/features/home/wallet_pager.dart';
import 'package:vase/features/numpad/numpad_model.dart';
import 'package:vase/features/send/send_model.dart';
import 'package:vase/features/send/send_page.dart';
import 'package:vase/features/wallet/wallet_model.dart';
import 'package:vase/wallet/keys.dart';
import 'package:vase/wallet/wallet.dart';

const _endpoint = 'http://127.0.0.1:22331';
const _genesis =
    '106050de32db2a668422cc34aa0f96d739d4189b8e5d6e763deeca527bba9c9f';

class _FixtureModel extends WalletModel {
  _FixtureModel(super.chronik) : super(initialize: false);
  void updateBalance(WalletBalance value) {
    balance = value;
    notifyListeners();
  }

  @override
  Future<void> writeToDisk() async {} // No platform wallet storage in this harness.
  @override
  void setSeed(String newValue, {String password = ''}) =>
      throw UnsupportedError('Regtest preview uses fixed public fixture keys');
}

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  GoRouter.optionURLReflectsImperativeAPIs = true;
  try {
    final response = await http
        .get(Uri.parse('$_endpoint/block/0'))
        .timeout(const Duration(seconds: 5));
    final block = proto.Block.fromBuffer(response.bodyBytes);
    if (response.statusCode != 200 ||
        HEX.encode(block.blockInfo.hash.reversed.toList()) != _genesis) {
      throw StateError('Not the isolated Lotus regtest chain');
    }
    final keys = Keys(
      null,
      null,
      HDPrivateKey.fromSeed(
        '000102030405060708090a0b0c0d0e0f',
        NetworkType.MAIN,
      ),
      [
        KeyInfo(key: BCHPrivateKey.fromBigInt(BigInt.one), keyIndex: 0),
        KeyInfo(
          key: BCHPrivateKey.fromBigInt(BigInt.two),
          keyIndex: 1,
          isChange: true,
        ),
      ],
    );
    final client = ChronikClient(_endpoint);
    final wallet = Wallet(keys, network: NetworkType.MAIN, chronik: client);
    final model = _FixtureModel(client)..wallet = wallet;
    wallet.balanceUpdateHandler = model.updateBalance;
    await wallet.updateUtxosChronik();
    wallet.refreshBalanceLocal();
    model.initialized = true;
    final send = SendModel()
      ..setPayment(
        BCHPrivateKey.fromBigInt(
          BigInt.from(3),
        ).toAddress(networkType: NetworkType.MAIN).toXAddress(),
        BigInt.from(1000001),
      );
    final router = GoRouter(
      initialLocation: '/send',
      routes: [
        ...walletPageRoutes(),
        GoRoute(path: '/send', builder: (_, _) => const SendPage()),
      ],
    );
    runApp(
      MultiProvider(
        providers: [
          ChangeNotifierProvider<WalletModel>.value(value: model),
          ChangeNotifierProvider<SendModel>.value(value: send),
          ChangeNotifierProvider(create: (_) => NumpadModel()),
        ],
        child: MaterialApp.router(
          theme: AppTheme.lotusTheme,
          routerConfig: router,
          debugShowCheckedModeBanner: false,
          builder: (_, child) => Banner(
            message: 'REGTEST',
            location: BannerLocation.topEnd,
            color: Colors.orange,
            child: child!,
          ),
        ),
      ),
    );
  } catch (_) {
    runApp(
      const MaterialApp(
        home: Scaffold(
          body: Center(
            child: Text(
              'Regtest preview unavailable. Start the isolated test node.',
            ),
          ),
        ),
      ),
    );
  }
}
