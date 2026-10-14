import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:lotus_dart/utils/parse_uri.dart';
import 'package:provider/provider.dart';
import 'package:vase/features/send/qr_view.dart';
import 'package:vase/features/send/send_model.dart';
import 'package:vase/features/wallet/wallet_model.dart';
import 'package:vase/utils/currency.dart';

typedef ScannerBuilder = Widget Function(ValueChanged<String?> onScanResult);

/// The scanner is the starting point; payment details stay on their own route.
class HomePage extends StatefulWidget {
  const HomePage({super.key, this.scannerBuilder});

  final ScannerBuilder? scannerBuilder;

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  bool _detailsOpen = false;

  Future<void> _openPage(String path) async {
    if (_detailsOpen) return;
    setState(() => _detailsOpen = true);
    try {
      await context.push(path);
    } finally {
      if (mounted) setState(() => _detailsOpen = false);
    }
  }

  void _onScan(String? result) {
    if (_detailsOpen || result == null || result.trim().isEmpty) return;
    try {
      final payment = parseSendURI(result);
      if (payment.address.isEmpty || payment.amount < BigInt.zero) {
        throw const FormatException('Invalid payment');
      }
      final send = context.read<SendModel>();
      send.setAddress(payment.address);
      send.setAmount(payment.amount);
      _openPage('/send');
    } catch (_) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Unable to parse QR code')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final balance = context.select<WalletModel, BigInt?>(
      (wallet) => wallet.balance?.balance,
    );
    return Scaffold(
      body: Stack(
        fit: StackFit.expand,
        children: [
          // Unmount the camera while another page is open, then resume on return.
          if (!_detailsOpen)
            widget.scannerBuilder?.call(_onScan) ??
                QRView(onScanResult: _onScan)
          else
            const ColoredBox(color: Colors.black),
          Center(
            child: IgnorePointer(
              child: Container(
                width: MediaQuery.sizeOf(context).width * 0.8,
                height: MediaQuery.sizeOf(context).width * 0.8,
                decoration: BoxDecoration(
                  border: Border.all(color: Colors.green, width: 4),
                  borderRadius: BorderRadius.circular(10),
                ),
              ),
            ),
          ),
          SafeArea(
            child: Column(
              children: [
                Container(
                  margin: const EdgeInsets.all(16),
                  padding:
                      const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                  decoration: BoxDecoration(
                    color: Colors.black54,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Text(
                    balance == null
                        ? 'Loading balance…'
                        : formatAmount(amount: balance),
                    style: const TextStyle(color: Colors.white, fontSize: 24),
                  ),
                ),
                const Spacer(),
                Padding(
                  padding: const EdgeInsets.all(20),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children: [
                      IconButton(
                        tooltip: 'Settings',
                        icon: const Icon(Icons.settings),
                        iconSize: 48,
                        onPressed: () => _openPage('/settings'),
                      ),
                      IconButton(
                        tooltip: 'Send',
                        icon: const Icon(Icons.send),
                        iconSize: 80,
                        onPressed: () => _openPage('/send'),
                      ),
                      IconButton(
                        tooltip: 'Receive',
                        icon: const Icon(Icons.save_alt),
                        iconSize: 48,
                        onPressed: () => _openPage('/request'),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
