/// Electrum JSON-RPC over TCP/TLS (Dart VM and Flutter mobile/desktop).
library;

import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:hex/hex.dart';
import 'encoding/utils.dart';

class ElectrumException implements Exception {
  final Object? error;
  ElectrumException(this.error);
  @override
  String toString() => 'ElectrumException: $error';
}

/// Explicit connection lifecycle; no automatic retries of broadcasts.
class ElectrumClient {
  final Socket _socket;
  final Duration timeout;
  final _pending = <int, Completer<Object?>>{};
  final _notifications = StreamController<Map<String, dynamic>>.broadcast();
  late final StreamSubscription<String> _subscription;
  int _nextId = 0;
  bool _closed = false;

  ElectrumClient._(this._socket, this.timeout) {
    _subscription = _socket
        .cast<List<int>>()
        .transform(utf8.decoder)
        .transform(const LineSplitter())
        .listen(
          _receive,
          onError: _fail,
          onDone: () => _fail(StateError('Electrum disconnected')),
        );
  }
  static Future<ElectrumClient> connect(
    String host,
    int port, {
    bool tls = true,
    Duration timeout = const Duration(seconds: 30),
  }) async {
    final socket =
        tls
            ? await SecureSocket.connect(host, port, timeout: timeout)
            : await Socket.connect(host, port, timeout: timeout);
    return ElectrumClient._(socket, timeout);
  }

  /// Subscription notifications, including method and params.
  Stream<Map<String, dynamic>> get notifications => _notifications.stream;
  void _receive(String line) {
    try {
      final msg = jsonDecode(line) as Map<String, dynamic>;
      final id = msg['id'];
      if (id == null && msg['method'] is String) {
        _notifications.add(msg);
      } else {
        final completer = _pending.remove(id);
        if (completer == null) return;
        if (msg['error'] != null) {
          completer.completeError(ElectrumException(msg['error']));
        } else {
          completer.complete(msg['result']);
        }
      }
    } catch (error) {
      _fail(FormatException('Invalid Electrum message: $error'));
    }
  }

  void _fail(Object error) {
    if (_closed) return;
    _closed = true;
    for (final completer in _pending.values) {
      completer.completeError(error);
    }
    _pending.clear();
    _socket.destroy();
    _notifications.close();
  }

  Future<Object?> request(
    String method, [
    List<Object?> params = const [],
  ]) async {
    if (_closed) throw StateError('Electrum client is closed');
    final id = _nextId++;
    final completer = Completer<Object?>();
    _pending[id] = completer;
    try {
      _socket.write(
        '${jsonEncode({'jsonrpc': '2.0', 'id': id, 'method': method, 'params': params})}\n',
      );
      return await completer.future.timeout(timeout);
    } finally {
      _pending.remove(id);
    }
  }

  /// Electrum uses reversed single-SHA256(scriptPubKey), not an address or TxId.
  static String scriptHash(List<int> script) =>
      HEX.encode(sha256(script).reversed.toList());
  Future<Object?> version() => request('server.version', ['lotus_dart', '1.4']);
  Future<Object?> balance(String hash) =>
      request('blockchain.scripthash.get_balance', [hash]);
  Future<Object?> history(String hash) =>
      request('blockchain.scripthash.get_history', [hash]);
  Future<Object?> listUnspent(String hash) =>
      request('blockchain.scripthash.listunspent', [hash]);
  Future<Object?> subscribeScript(String hash) =>
      request('blockchain.scripthash.subscribe', [hash]);
  Future<Object?> subscribeHeaders() => request('blockchain.headers.subscribe');
  Future<Object?> transaction(String txid) =>
      request('blockchain.transaction.get', [txid]);
  Future<Object?> broadcast(String rawTx) =>
      request('blockchain.transaction.broadcast', [rawTx]);
  Future<void> close() async {
    _fail(StateError('Electrum client closed'));
    await _subscription.cancel();
  }
}
