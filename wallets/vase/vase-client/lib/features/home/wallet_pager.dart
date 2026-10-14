import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:vase/features/home/home_page.dart';
import 'package:vase/features/contacts/contacts_page.dart';
import 'package:vase/features/request/request_page.dart';
import 'package:vase/features/settings/settings_page.dart';

const _paths = ['/contacts', '/', '/request'];

/// These mutually exclusive routes share a page key so URL changes preserve the
/// pager, its controller, and the state of the wallet's adjacent screens.
List<RouteBase> walletPageRoutes({
  ScannerBuilder? scannerBuilder,
  Widget Function(VoidCallback)? contactsBuilder,
}) => [
  for (final path in _paths)
    GoRoute(
      path: path,
      pageBuilder: (_, state) => NoTransitionPage<void>(
        key: const ValueKey('wallet-pager'),
        child: WalletPager(
          location: state.uri.path,
          scannerBuilder: scannerBuilder,
          contactsBuilder: contactsBuilder,
          initialRequestAmount: state.extra is BigInt
              ? state.extra as BigInt
              : null,
        ),
      ),
    ),
  GoRoute(
    path: '/settings',
    pageBuilder: (context, state) => CustomTransitionPage<void>(
      key: state.pageKey,
      child: SettingsPage(
        onBack: () => context.canPop() ? context.pop() : context.go('/'),
      ),
      transitionsBuilder: (_, animation, _, child) => SlideTransition(
        position: Tween(
          begin: const Offset(0, -1),
          end: Offset.zero,
        ).animate(CurvedAnimation(parent: animation, curve: Curves.easeInOut)),
        child: child,
      ),
    ),
  ),
];

class WalletPager extends StatefulWidget {
  const WalletPager({
    super.key,
    required this.location,
    this.scannerBuilder,
    this.contactsBuilder,
    this.initialRequestAmount,
  });

  final String location;
  final ScannerBuilder? scannerBuilder;
  final Widget Function(VoidCallback)? contactsBuilder;
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
        _KeptPage(
          child:
              widget.contactsBuilder?.call(() => context.go('/')) ??
              ContactsPage(onBack: () => context.go('/')),
        ),
        HomePage(
          active: _index == 1,
          scannerBuilder: widget.scannerBuilder,
          onContacts: () => context.go('/contacts'),
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
