import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:vase/features/home/home_page.dart';
import 'package:vase/features/request/request_page.dart';
import 'package:vase/features/settings/settings_page.dart';

const _paths = ['/settings', '/', '/request'];

/// These mutually exclusive routes share a page key so URL changes preserve the
/// pager, its controller, and the state of the wallet's adjacent screens.
List<RouteBase> walletPageRoutes({ScannerBuilder? scannerBuilder}) => [
  for (final path in _paths)
    GoRoute(
      path: path,
      pageBuilder: (_, state) => NoTransitionPage<void>(
        key: const ValueKey('wallet-pager'),
        child: WalletPager(
          location: state.uri.path,
          scannerBuilder: scannerBuilder,
          initialRequestAmount: state.extra is BigInt
              ? state.extra as BigInt
              : null,
        ),
      ),
    ),
];

class WalletPager extends StatefulWidget {
  const WalletPager({
    super.key,
    required this.location,
    this.scannerBuilder,
    this.initialRequestAmount,
  });

  final String location;
  final ScannerBuilder? scannerBuilder;
  final BigInt? initialRequestAmount;

  @override
  State<WalletPager> createState() => _WalletPagerState();
}

class _WalletPagerState extends State<WalletPager> {
  late final PageController _controller;
  late int _index;
  int? _routeTarget;

  @override
  void initState() {
    super.initState();
    _index = _paths.indexOf(widget.location);
    _controller = PageController(initialPage: _index);
  }

  @override
  void didUpdateWidget(WalletPager oldWidget) {
    super.didUpdateWidget(oldWidget);
    final target = _paths.indexOf(widget.location);
    if (target == _index && _routeTarget == null) return;
    _routeTarget = target;
    // Route updates arrive during build. Move the controller after layout.
    WidgetsBinding.instance.addPostFrameCallback((_) async {
      if (!mounted || _paths[target] != widget.location) return;
      await _controller.animateToPage(
        target,
        duration: const Duration(milliseconds: 280),
        curve: Curves.easeInOut,
      );
      if (mounted && _routeTarget == target) _routeTarget = null;
    });
  }

  void _pageChanged(int index) {
    setState(() => _index = index);
    // A route-driven transition may cross the scanner; don't replace the
    // requested URL with that intermediate page.
    if (_routeTarget != null) return;
    if (widget.location != _paths[index]) context.go(_paths[index]);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => PopScope<void>(
    canPop: _index == 1,
    onPopInvokedWithResult: (didPop, _) {
      if (!didPop && _index != 1) context.go('/');
    },
    child: PageView(
      key: const ValueKey('wallet-pages'),
      controller: _controller,
      onPageChanged: _pageChanged,
      children: [
        _KeptPage(child: SettingsPage(onBack: () => context.go('/'))),
        HomePage(
          active: _index == 1,
          scannerBuilder: widget.scannerBuilder,
          onSettings: () => context.go('/settings'),
          onReceive: () => context.go('/request'),
        ),
        _KeptPage(
          child: RequestPage(
            onBack: () => context.go('/'),
            initialAmount: widget.initialRequestAmount,
          ),
        ),
      ],
    ),
  );
}

// Preserve drafts and scroll position while moving between adjacent pages.
class _KeptPage extends StatefulWidget {
  const _KeptPage({required this.child});
  final Widget child;
  @override
  State<_KeptPage> createState() => _KeptPageState();
}

class _KeptPageState extends State<_KeptPage>
    with AutomaticKeepAliveClientMixin {
  @override
  bool get wantKeepAlive => true;
  @override
  Widget build(BuildContext context) {
    super.build(context);
    return widget.child;
  }
}
