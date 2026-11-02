import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import 'package:lotus_dart/bip39/bip39.dart';
import 'package:vase/features/wallet/wallet_model.dart';
import 'package:vase/wallet/recovery_material.dart';

class RecoveryPage extends StatefulWidget {
  const RecoveryPage({super.key, this.initialRestore = false});
  final bool initialRestore;
  @override
  State<RecoveryPage> createState() => _RecoveryPageState();
}

class _RecoveryPageState extends State<RecoveryPage>
    with WidgetsBindingObserver {
  final _input = TextEditingController();
  final _passphrase = TextEditingController();
  WalletModel? _wallet;
  String? _material;
  String? _password;
  List<String> _shares = [];
  bool _restore = false, _busy = false, _verified = false;
  String? _error;
  int _scheme = 1;
  static const _schemes = [(1, 1), (2, 3), (3, 5), (6, 10)];

  @override
  void initState() {
    super.initState();
    _restore = widget.initialRestore;
    WidgetsBinding.instance.addObserver(this);
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final next = context.read<WalletModel>();
    if (!identical(next, _wallet)) {
      _wallet?.removeListener(_walletChanged);
      _wallet = next;
      _wallet!.addListener(_walletChanged);
      _material = next.seed;
      _password = next.password;
    }
  }

  void _walletChanged() {
    if (_wallet!.seed == _material && _wallet!.password == _password) return;
    _material = _wallet!.seed;
    _password = _wallet!.password;
    _clearSecrets();
  }

  void _clearSecrets() {
    if (!mounted) return;
    setState(() {
      _shares = [];
      _verified = false;
      _error = null;
    });
    _input.clear();
    _passphrase.clear();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state != AppLifecycleState.resumed) _clearSecrets();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _wallet?.removeListener(_walletChanged);
    _input.dispose();
    _passphrase.dispose();
    _shares = [];
    super.dispose();
  }

  void _generate() {
    _clearSecrets();
    try {
      final material = _wallet!.seed;
      if (material == null || material.isEmpty || !_wallet!.initialized) {
        throw StateError('Wallet unavailable');
      }
      final scheme = _schemes[_scheme];
      final shares = backupWalletMaterial(
        material,
        _wallet!.password ?? '',
        threshold: scheme.$1,
        shareCount: scheme.$2,
      );
      setState(() => _shares = shares);
    } catch (_) {
      setState(
        () => _error =
            'Unable to create recovery shares. Existing wallet is unchanged.',
      );
    }
  }

  Future<void> _import() async {
    if (_busy) return;
    final text = _input.text.trim();
    String material, passphrase;
    try {
      if (text.toLowerCase().startsWith('fr1')) {
        material = materialFromShares(text.split(RegExp(r'\s+')));
        passphrase = '';
        if (_passphrase.text.isNotEmpty) {
          throw const FormatException(
            'Share backups already include the passphrase-derived seed',
          );
        }
      } else {
        material = text.toLowerCase().replaceAll(RegExp(r'\s+'), ' ');
        if (!Mnemonic().validateMnemonic(material))
          throw const FormatException('Invalid recovery words');
        passphrase = _passphrase.text; // Case and whitespace are significant.
      }
    } catch (_) {
      setState(
        () => _error =
            'Invalid recovery material. Use matching fr1 shares or valid BIP39 words. For shares, leave the passphrase empty.',
      );
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final confirmed = await showDialog<bool>(
        context: context,
        builder: (ctx) => AlertDialog(
          title: const Text('Replace this wallet?'),
          content: const Text(
            'Make sure you have a backup of the current wallet. This restores the wallet on this device.',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: const Text('Cancel'),
            ),
            TextButton(
              onPressed: () => Navigator.pop(ctx, true),
              child: const Text('Restore wallet'),
            ),
          ],
        ),
      );
      if (confirmed != true || !mounted) return;
      await _wallet!.setSeed(material, password: passphrase);
      if (!mounted) return;
      _clearSecrets();
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('Wallet restored')));
    } catch (_) {
      if (mounted)
        setState(
          () => _error = 'Unable to restore. Existing wallet was not replaced.',
        );
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _verify() async {
    final verified = await showDialog<bool>(
      context: context,
      builder: (_) => _VerifySharesDialog(
        verify: (text) {
          final restored = materialFromShares(
            text.trim().split(RegExp(r'\s+')),
          );
          final expected = walletSeedBytes(_material!, _password ?? '');
          final actual = walletSeedBytes(restored, '');
          try {
            var difference = actual.length ^ expected.length;
            for (var i = 0; i < actual.length && i < expected.length; i++) {
              difference |= actual[i] ^ expected[i];
            }
            return difference == 0;
          } finally {
            expected.fillRange(0, expected.length, 0);
            actual.fillRange(0, actual.length, 0);
          }
        },
      ),
    );
    if (!mounted || verified != true || _shares.isEmpty) return;
    setState(() {
      _verified = true;
      _error = null;
    });
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Recovery & backup')),
    body: ListView(
      padding: const EdgeInsets.all(16),
      children: [
        SegmentedButton<bool>(
          segments: const [
            ButtonSegment(value: false, label: Text('Back up')),
            ButtonSegment(value: true, label: Text('Restore')),
          ],
          selected: {_restore},
          onSelectionChanged: _busy
              ? null
              : (selection) {
                  _clearSecrets();
                  setState(() => _restore = selection.first);
                },
        ),
        const SizedBox(height: 24),
        if (!_restore) ...[
          const Text(
            'Split your wallet backup into recovery shares. Store them separately; anyone with enough shares can restore the wallet.',
          ),
          const SizedBox(height: 16),
          DropdownButtonFormField<int>(
            initialValue: _scheme,
            decoration: const InputDecoration(labelText: 'Recovery scheme'),
            items: [
              for (var i = 0; i < _schemes.length; i++)
                DropdownMenuItem(
                  value: i,
                  child: Text('${_schemes[i].$1} of ${_schemes[i].$2} shares'),
                ),
            ],
            onChanged: (value) {
              if (value != null) {
                _clearSecrets();
                setState(() => _scheme = value);
              }
            },
          ),
          const SizedBox(height: 16),
          FilledButton(
            onPressed: _generate,
            child: const Text('Generate recovery shares'),
          ),
          if (_shares.isNotEmpty) ...[
            const Text(
              'These shares restore your wallet keys. For BIP39 wallets, they include any passphrase’s effect. The original words cannot be reconstructed.',
            ),
            for (var i = 0; i < _shares.length; i++)
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Share ${i + 1} of ${_shares.length}'),
                      SelectableText(
                        _shares[i],
                        style: const TextStyle(fontFamily: 'monospace'),
                      ),
                      TextButton.icon(
                        onPressed: () =>
                            Clipboard.setData(ClipboardData(text: _shares[i])),
                        icon: const Icon(Icons.copy),
                        label: Text('Copy share ${i + 1}'),
                      ),
                    ],
                  ),
                ),
              ),
            OutlinedButton(
              onPressed: _verify,
              child: const Text('Verify saved shares'),
            ),
            if (_verified)
              const Text(
                'Saved shares verified',
                key: ValueKey('backup-verified'),
              ),
          ],
        ] else ...[
          const Text(
            'Paste BIP39 recovery words or matching fr1 recovery shares. Shares from different backups cannot be combined.',
          ),
          const SizedBox(height: 16),
          TextField(
            key: const ValueKey('recovery-input'),
            controller: _input,
            minLines: 4,
            maxLines: 8,
            autocorrect: false,
            enableSuggestions: false,
            enableIMEPersonalizedLearning: false,
            decoration: const InputDecoration(
              labelText: 'Recovery words or shares',
            ),
          ),
          const SizedBox(height: 16),
          TextField(
            key: const ValueKey('recovery-passphrase'),
            controller: _passphrase,
            obscureText: true,
            autocorrect: false,
            enableSuggestions: false,
            enableIMEPersonalizedLearning: false,
            decoration: const InputDecoration(
              labelText: 'BIP39 passphrase (optional; words only)',
            ),
          ),
          const SizedBox(height: 16),
          FilledButton(
            onPressed: _busy ? null : _import,
            child: Text(_busy ? 'Restoring…' : 'Restore'),
          ),
        ],
        if (_error != null)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 16),
            child: Text(_error!, key: const ValueKey('recovery-error')),
          ),
      ],
    ),
  );
}

class _VerifySharesDialog extends StatefulWidget {
  const _VerifySharesDialog({required this.verify});
  final bool Function(String) verify;
  @override
  State<_VerifySharesDialog> createState() => _VerifySharesDialogState();
}

class _VerifySharesDialogState extends State<_VerifySharesDialog>
    with WidgetsBindingObserver {
  final _input = TextEditingController();
  bool _invalid = false;
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state != AppLifecycleState.resumed) _input.clear();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _input.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AlertDialog(
    title: const Text('Verify your saved shares'),
    content: TextField(
      key: const ValueKey('verify-shares'),
      controller: _input,
      maxLines: 5,
      autocorrect: false,
      enableSuggestions: false,
      enableIMEPersonalizedLearning: false,
      decoration: InputDecoration(
        labelText: 'Paste enough saved fr1 shares',
        errorText: _invalid ? 'Shares do not restore this wallet' : null,
      ),
    ),
    actions: [
      TextButton(
        onPressed: () => Navigator.pop(context),
        child: const Text('Cancel'),
      ),
      TextButton(
        onPressed: () {
          try {
            if (widget.verify(_input.text)) {
              Navigator.pop(context, true);
              return;
            }
          } catch (_) {
            /* Public error only; never log recovery material. */
          }
          setState(() => _invalid = true);
        },
        child: const Text('Verify'),
      ),
    ],
  );
}
