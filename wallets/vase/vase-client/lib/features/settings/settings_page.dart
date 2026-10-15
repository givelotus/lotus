import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_hooks/flutter_hooks.dart';
import 'package:go_router/go_router.dart';
import 'package:package_info_plus/package_info_plus.dart';
import 'package:provider/provider.dart';
import 'package:sentry_flutter/sentry_flutter.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:vase/config/constants.dart';
import 'package:vase/config/theme.dart';
import 'package:vase/features/wallet/wallet_model.dart';
import 'package:vase/features/settings/recovery_page.dart';
import 'package:vase/wallet/recovery_material.dart';

final packageInfoFuture = PackageInfo.fromPlatform();

class SettingsPage extends HookWidget {
  const SettingsPage({Key? key, this.onBack}) : super(key: key);

  final VoidCallback? onBack;

  @override
  Widget build(BuildContext context) {
    final wallet = context.watch<WalletModel>();
    final mnemonicWallet = isMnemonicMaterial(wallet.seed ?? '');
    final scrollController = useScrollController();
    final swipeStart = useRef<Offset?>(null);
    void dismiss() => onBack != null
        ? onBack!()
        : context.canPop()
        ? context.pop()
        : context.go('/');

    final showSeedTextController = useTextEditingController();
    final showPasswordTextController = useTextEditingController();

    void showSeedDialog() {
      showDialog(
        useSafeArea: false,
        context: context,
        builder: (context) {
          final walletModel = context.watch<WalletModel>();
          showSeedTextController.text = walletModel.seed ?? '';
          showPasswordTextController.text = walletModel.password ?? '';
          return Stack(
            children: [
              const IgnorePointer(
                child: Scaffold(backgroundColor: Colors.transparent),
              ),
              AlertDialog(
                title: showSeedTextController.text.isNotEmpty
                    ? const Text('Seed Phrase')
                    : null,
                content: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    if (showSeedTextController.text.isEmpty)
                      const Center(child: CircularProgressIndicator()),
                    if (showSeedTextController.text.isNotEmpty) ...[
                      Row(
                        children: [
                          Expanded(
                            child: TextField(
                              maxLines: null,
                              minLines: 2,
                              controller: showSeedTextController,
                              readOnly: true,
                              decoration: const InputDecoration(
                                border: OutlineInputBorder(),
                              ),
                            ),
                          ),
                          Container(
                            padding: const EdgeInsets.fromLTRB(6, 0, 6, 0),
                            child: OutlinedButton(
                              onPressed: () {
                                Clipboard.setData(
                                  ClipboardData(
                                    text: showSeedTextController.text,
                                  ),
                                );
                                ScaffoldMessenger.of(context).showSnackBar(
                                  const SnackBar(
                                    content: Text('Copied seed to Clipboard'),
                                    duration: Duration(seconds: 1),
                                  ),
                                );
                              },
                              child: const Icon(Icons.copy),
                            ),
                          ),
                        ],
                      ),
                      const Padding(
                        padding: EdgeInsets.fromLTRB(0, 12, 0, 12),
                        child: Text('Password (Optional)'),
                      ),
                      Row(
                        children: [
                          Expanded(
                            child: TextField(
                              maxLines: null,
                              minLines: 2,
                              controller: showPasswordTextController,
                              readOnly: true,
                              decoration: const InputDecoration(
                                border: OutlineInputBorder(),
                              ),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ],
                ),
              ),
            ],
          );
        },
      );
    }

    Future<void> Function() _launchUrl(String url) => () async {
      final uri = Uri.tryParse(url);
      if (uri == null) {
        Sentry.captureMessage('Invalid URL: $url');
        return;
      }

      if (!await canLaunchUrl(uri)) {
        Sentry.captureMessage('Could not launch $url');
        return;
      }

      await launchUrl(uri);
    };

    return Listener(
      // Observe without stealing the ListView's drag recognizer. Only a new
      // upward swipe at the bottom dismisses; scrolling to the bottom does not.
      onPointerDown: (event) {
        swipeStart.value =
            ModalRoute.of(context)?.isCurrent == true &&
                scrollController.hasClients &&
                scrollController.position.extentAfter <= 1
            ? event.position
            : null;
      },
      onPointerCancel: (_) => swipeStart.value = null,
      onPointerUp: (event) {
        final start = swipeStart.value;
        swipeStart.value = null;
        if (start == null || ModalRoute.of(context)?.isCurrent != true) return;
        final delta = event.position - start;
        if (delta.dy <= -64 && -delta.dy > delta.dx.abs() * 1.5) dismiss();
      },
      child: Scaffold(
        appBar: AppBar(
          backgroundColor: Colors.transparent,
          elevation: 0,
          leading: IconButton(
            splashRadius: AppTheme.splashRadius,
            onPressed: dismiss,
            icon: const Icon(Icons.navigate_before),
          ),
          title: const Text('Settings', style: TextStyle(fontSize: 20)),
          centerTitle: true,
        ),
        body: ListView(
          controller: scrollController,
          children: [
            const ListTile(
              title: Text(
                'Wallet',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
              ),
            ),
            if (mnemonicWallet)
              ListTile(
                title: const Text('Seed Phrase'),
                leading: const Icon(Icons.nature),
                trailing: const Icon(Icons.keyboard_arrow_right),
                onTap: () => showSeedDialog(),
              ),
            ListTile(
              title: const Text('Import wallet'),
              subtitle: const Text('BIP39 words or recovery shares'),
              leading: const Icon(Icons.upload),
              trailing: const Icon(Icons.keyboard_arrow_right),
              onTap: () => Navigator.of(context).push(
                MaterialPageRoute<void>(
                  builder: (_) => const RecoveryPage(initialRestore: true),
                ),
              ),
            ),
            ListTile(
              title: const Text('Recovery & backup'),
              leading: const Icon(Icons.shield_outlined),
              trailing: const Icon(Icons.keyboard_arrow_right),
              onTap: () => Navigator.of(context).push(
                MaterialPageRoute<void>(builder: (_) => const RecoveryPage()),
              ),
            ),
            const Divider(),
            const ListTile(
              title: Text(
                'More',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
              ),
            ),
            ListTile(
              title: const Text('Help'),
              leading: const Icon(Icons.help),
              trailing: const Icon(Icons.keyboard_arrow_right),
              enabled: false,
              subtitle: const Text('Temporarily unavailable'),
            ),
            ListTile(
              title: const Text('Website'),
              leading: const Icon(Icons.web),
              trailing: const Icon(Icons.keyboard_arrow_right),
              enabled: false,
              subtitle: const Text('Temporarily unavailable'),
            ),
            ListTile(
              title: const Text('Community'),
              leading: const Icon(Icons.group),
              trailing: const Icon(Icons.keyboard_arrow_right),
              onTap: _launchUrl('https://t.me/TheLotusNetwork'),
            ),
            ListTile(
              title: const Text('Version'),
              subtitle: FutureBuilder<PackageInfo>(
                future: packageInfoFuture,
                builder: (context, snapshot) {
                  if (snapshot.hasData) {
                    return Text('${snapshot.data?.version}');
                  }
                  return const SizedBox.shrink();
                },
              ),
              leading: const Icon(Icons.info),
            ),
          ],
        ),
      ),
    );
  }
}
