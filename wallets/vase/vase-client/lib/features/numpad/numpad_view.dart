import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter_hooks/flutter_hooks.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import 'package:vase/config/colors.dart';
import 'package:vase/features/numpad/numpad.dart';
import 'package:vase/features/numpad/numpad_model.dart';
import 'package:vase/features/send/send_model.dart';
import 'package:vase/features/wallet/wallet_model.dart';
import 'package:vase/utils/currency.dart';

class NumpadView extends HookWidget {
  const NumpadView({
    Key? key,
    this.onDoneTap,
    this.onAmountDone,
    this.requireBalance = true,
  }) : super(key: key);

  final Function? onDoneTap;
  final ValueChanged<BigInt>? onAmountDone;
  final bool requireBalance;

  @override
  Widget build(BuildContext context) {
    final walletBalance = context.select<WalletModel, BigInt?>(
      (model) => model.balance?.balance,
    );
    final walletError = context.select<WalletModel, dynamic>(
      (model) => model.balance?.error,
    );
    final controller = useAnimationController(
      duration: const Duration(milliseconds: 200),
    );
    final finishing = useState(false);
    final height = MediaQuery.of(context).size.height;
    final width = MediaQuery.of(context).size.width;
    final scaleFactor = MediaQuery.of(context).textScaleFactor;
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          Expanded(
            child: Consumer<NumpadModel>(
              builder: (context, numpadModel, widget) {
                return AnimatedBuilder(
                  animation: controller,
                  builder: (context, child) {
                    return Transform.translate(
                      offset: Offset(10 * sin(controller.value * 5 * pi), 0),
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Flexible(
                            child: SingleChildScrollView(
                              scrollDirection: Axis.horizontal,
                              reverse: true,
                              child: Text(
                                numpadModel.expression,
                                key: const ValueKey('calculator-expression'),
                                style: const TextStyle(fontSize: 24),
                              ),
                            ),
                          ),
                          Expanded(
                            flex: 3,
                            child: FittedBox(
                              fit: BoxFit.scaleDown,
                              child: Text(
                                '${numpadModel.value} XPI',
                                key: const ValueKey('calculator-result'),
                                style: const TextStyle(
                                  fontSize: 64,
                                  fontWeight: FontWeight.w700,
                                ),
                              ),
                            ),
                          ),
                          if (numpadModel.error != null)
                            Flexible(
                              child: FittedBox(
                                fit: BoxFit.scaleDown,
                                child: Text(
                                  numpadModel.error!,
                                  key: const ValueKey('calculator-error'),
                                  style: const TextStyle(
                                    color: Colors.redAccent,
                                  ),
                                ),
                              ),
                            ),
                        ],
                      ),
                    );
                  },
                );
              },
            ),
          ),
          const SizedBox(height: 8),
          ConstrainedBox(
            constraints: BoxConstraints(maxHeight: height * 0.6),
            child: FittedBox(
              fit: BoxFit.scaleDown,
              child: Column(
                children: [
                  Container(
                    constraints: BoxConstraints(minHeight: 36 * scaleFactor),
                    width: 200,
                    child: TextButton(
                      style: TextButton.styleFrom(
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(40),
                        ),
                        foregroundColor: Colors.white,
                        backgroundColor: AppColors.lotusPurple1,
                        padding: const EdgeInsets.symmetric(
                          vertical: 8,
                          horizontal: 16,
                        ),
                      ),
                      onPressed: walletError != null
                          ? () {
                              final walletModel = context.read<WalletModel>();
                              walletModel.resetBalance();
                              walletModel.updateWallet();
                            }
                          : null,
                      child: walletBalance == null && walletError == null
                          ? SizedBox(
                              height: 16 * scaleFactor,
                              width: 16 * scaleFactor,
                              child: const CircularProgressIndicator(
                                strokeWidth: 2,
                              ),
                            )
                          : walletBalance == null
                          ? FittedBox(
                              child: Row(
                                children: [
                                  Text(
                                    '${walletError ?? 'Error fetching balance'}',
                                    textAlign: TextAlign.center,
                                    style: const TextStyle(
                                      fontSize: 16,
                                      color: Colors.white,
                                    ),
                                  ),
                                  const SizedBox(width: 8),
                                  const Icon(Icons.replay, size: 16),
                                ],
                              ),
                            )
                          : Text(
                              formatAmount(
                                amount: walletBalance,
                                maximumFractionDigits: 2,
                              ),
                              textAlign: TextAlign.center,
                              style: const TextStyle(
                                fontSize: 16,
                                color: Colors.white,
                              ),
                            ),
                    ),
                  ),
                  const SizedBox(height: 16),
                  SizedBox(
                    width: width,
                    child: NumpadWidget(controller: controller),
                  ),
                  const SizedBox(height: 32),
                  if (onDoneTap != null || onAmountDone != null)
                    SizedBox(
                      width: min(width, 200),
                      child: ElevatedButton(
                        style: ElevatedButton.styleFrom(
                          elevation: 0,
                          padding: const EdgeInsets.all(16),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(40),
                          ),
                        ),
                        child: const Text(
                          'Done',
                          style: TextStyle(
                            color: Colors.white,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                        onPressed: () async {
                          if (finishing.value) return;
                          finishing.value = true;
                          final amount = context.read<NumpadModel>().amount;
                          if (await isValid(
                            context,
                            controller,
                            requireBalance: requireBalance,
                            transfer: false,
                          )) {
                            if (!context.mounted || amount == null) return;
                            if (onAmountDone != null) {
                              onAmountDone!(amount);
                            } else {
                              context.read<SendModel>().setAmount(amount);
                              onDoneTap?.call();
                            }
                          } else if (context.mounted) {
                            finishing.value = false;
                          }
                        },
                      ),
                    )
                  else
                    SizedBox(
                      width: width,
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Expanded(
                            child: ElevatedButton(
                              style: ElevatedButton.styleFrom(
                                elevation: 0,
                                padding: const EdgeInsets.all(16),
                                shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(40),
                                ),
                              ),
                              child: const Text(
                                'Request',
                                style: TextStyle(
                                  color: Colors.white,
                                  fontWeight: FontWeight.w700,
                                ),
                              ),
                              onPressed: () async {
                                if (await isValid(
                                  context,
                                  controller,
                                  requireBalance: false,
                                  transfer: false,
                                )) {
                                  if (context.mounted) {
                                    context.push(
                                      '/request',
                                      extra: context.read<NumpadModel>().amount,
                                    );
                                  }
                                }
                              },
                            ),
                          ),
                          const SizedBox(width: 16),
                          Expanded(
                            child: ElevatedButton(
                              style: ElevatedButton.styleFrom(
                                elevation: 0,
                                padding: const EdgeInsets.all(16),
                                shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(40),
                                ),
                              ),
                              child: const Text(
                                'Send',
                                style: TextStyle(
                                  color: Colors.white,
                                  fontWeight: FontWeight.w700,
                                ),
                              ),
                              onPressed: () async {
                                if (await isValid(context, controller)) {
                                  if (context.mounted) context.push('/send');
                                }
                              },
                            ),
                          ),
                        ],
                      ),
                    ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

Future<bool> isValid(
  BuildContext ctx,
  AnimationController controller, {
  bool requireBalance = true,
  bool transfer = true,
}) async {
  final walletModel = ctx.read<WalletModel>();
  final numpadModel = ctx.read<NumpadModel>();
  final balance = walletModel.balance?.balance;
  final amount = numpadModel.amount;

  if (amount == null ||
      amount <= BigInt.zero ||
      (requireBalance && (balance == null || balance <= amount))) {
    controller.forward(from: 0);
    await HapticFeedback.heavyImpact();
    return false;
  }

  if (transfer) ctx.read<SendModel>().setAmount(amount);
  return true;
}

/// A fresh, route-scoped draft. Cancelling never mutates the sender or request.
Future<BigInt?> showAmountCalculator(
  BuildContext context, {
  required BigInt initialAmount,
  bool requireBalance = true,
}) {
  return showModalBottomSheet<BigInt>(
    context: context,
    isScrollControlled: true,
    builder: (sheetContext) => ChangeNotifierProvider(
      create: (_) => NumpadModel()..setValue(satsToLotus(initialAmount)),
      child: SizedBox(
        height: min(MediaQuery.sizeOf(sheetContext).height * 0.9, 720),
        child: NumpadView(
          requireBalance: requireBalance,
          onAmountDone: (amount) => Navigator.of(sheetContext).pop(amount),
        ),
      ),
    ),
  );
}
