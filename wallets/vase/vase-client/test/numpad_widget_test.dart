import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:vase/chronik-client/client.dart';
import 'package:vase/features/numpad/key_widget.dart';
import 'package:vase/features/numpad/numpad.dart';
import 'package:vase/features/numpad/numpad_model.dart';
import 'package:vase/features/numpad/numpad_view.dart';
import 'package:vase/features/send/send_model.dart';
import 'package:vase/features/wallet/wallet_model.dart';
import 'package:vase/utils/currency.dart';
import 'package:vase/wallet/wallet.dart';

class CalculatorWallet extends WalletModel {
  CalculatorWallet() : super(ChronikClient('http://127.0.0.1:1'));
  @override
  Future<void> initializeModel() async {}
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUp(() {
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(
          const MethodChannel('vibrate'),
          (_) async => false,
        );
  });
  tearDown(() {
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(const MethodChannel('vibrate'), null);
  });

  testWidgets('actual keys enter a base unit and reject duplicate periods', (
    tester,
  ) async {
    final model = NumpadModel();
    final controller = AnimationController(
      vsync: tester,
      duration: const Duration(milliseconds: 200),
    );
    addTearDown(controller.dispose);
    addTearDown(model.dispose);
    await tester.pumpWidget(
      ChangeNotifierProvider.value(
        value: model,
        child: MaterialApp(
          home: Scaffold(
            body: Column(
              children: [
                Consumer<NumpadModel>(
                  builder: (_, model, __) => Text(
                    formatNumpadInput(model.items).join(),
                    key: const ValueKey('amount'),
                  ),
                ),
                NumpadWidget(controller: controller),
              ],
            ),
          ),
        ),
      ),
    );
    for (final key in '.000001'.split('')) {
      await tester.tap(find.widgetWithText(KeyWidget, key));
      await tester.pump();
    }
    expect(model.value, '0.000001');
    expect(
      tester.widget<Text>(find.byKey(const ValueKey('amount'))).data,
      '0.000001',
    );
    await tester.tap(find.widgetWithText(KeyWidget, '.'));
    await tester.pumpAndSettle();
    expect(model.value, '0.000001');
    for (var i = 0; i < 8; i++) {
      await tester.tap(find.widgetWithText(KeyWidget, '<'));
      await tester.pumpAndSettle();
    }
    expect(model.value, '0');
  });

  for (final input in ['1.000001', '0']) {
    testWidgets(
      'Done transfers exact positive units and rejects zero: $input',
      (tester) async {
        final wallet = CalculatorWallet()
          ..balance = WalletBalance(balance: BigInt.from(20000000));
        final model = NumpadModel()..setValue(input);
        final send = SendModel()..setAmount(BigInt.from(7));
        var completed = 0;
        addTearDown(wallet.dispose);
        addTearDown(model.dispose);
        addTearDown(send.dispose);
        await tester.pumpWidget(
          MultiProvider(
            providers: [
              ChangeNotifierProvider<WalletModel>.value(value: wallet),
              ChangeNotifierProvider<NumpadModel>.value(value: model),
              ChangeNotifierProvider<SendModel>.value(value: send),
            ],
            child: MaterialApp(
              home: Scaffold(body: NumpadView(onDoneTap: () => completed++)),
            ),
          ),
        );
        await tester.tap(find.text('Done'));
        await tester.pumpAndSettle();
        expect(completed, input == '0' ? 0 : 1);
        expect(
          send.amount,
          input == '0' ? BigInt.from(7) : BigInt.from(1000001),
        );
      },
    );
  }
}
