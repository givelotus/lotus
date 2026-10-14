/// Chronik HTTP/protobuf support for Lotus mainnet.
library;

import 'package:hex/hex.dart';
import 'package:http/http.dart' as http;
import 'src/chronik/chronik.pb.dart' as pb;
export 'src/chronik/chronik.pb.dart';

/// A non-successful Chronik response.
class ChronikException implements Exception {
  final int statusCode;
  final String message;
  ChronikException(this.statusCode, this.message);
  @override
  String toString() => 'ChronikException($statusCode): $message';
}

/// A Lotus Chronik client. Hashes in protobuf messages are little endian;
/// path parameters and [broadcast] results use conventional display hex.
/// Transactions retain their server-provided Lotus merkleized TxId.
class ChronikClient {
  final Uri _base;
  final http.Client _http;
  final bool _ownsHttp;
  final Duration timeout;

  ChronikClient(
    String url, {
    http.Client? client,
    this.timeout = const Duration(seconds: 30),
  }) : _base = Uri.parse(url.endsWith('/') ? url : '$url/'),
       _http = client ?? http.Client(),
       _ownsHttp = client == null {
    if (!['http', 'https'].contains(_base.scheme) ||
        _base.host.isEmpty ||
        _base.hasQuery ||
        _base.hasFragment) {
      throw ArgumentError.value(url, 'url', 'Expected HTTP(S) base URL');
    }
  }

  Future<List<int>> _request(String path, {List<int>? body}) async {
    final headers = {
      'accept': 'application/x-protobuf',
      if (body != null) 'content-type': 'application/x-protobuf',
    };
    final uri = _base.resolve(path);
    final response = await (body == null
            ? _http.get(uri, headers: headers)
            : _http.post(uri, headers: headers, body: body))
        .timeout(timeout);
    if (response.statusCode < 200 || response.statusCode >= 300) {
      String message;
      try {
        message = pb.Error.fromBuffer(response.bodyBytes).msg;
      } catch (_) {
        message = 'Invalid error response';
      }
      throw ChronikException(response.statusCode, message);
    }
    return response.bodyBytes;
  }

  static String _hex(String value, [int? bytes]) {
    if (!RegExp(r'^(?:[a-fA-F0-9]{2})+$').hasMatch(value) ||
        (bytes != null && value.length != bytes * 2)) {
      throw ArgumentError.value(value, 'hex', 'Invalid hexadecimal payload');
    }
    return value.toLowerCase();
  }

  Future<pb.BlockchainInfo> blockchainInfo() async =>
      pb.BlockchainInfo.fromBuffer(await _request('blockchain-info'));
  Future<pb.Tx> tx(String txid) async =>
      pb.Tx.fromBuffer(await _request('tx/${_hex(txid, 32)}'));
  Future<pb.TxHistoryPage> blockTxs(int height, {int page = 0}) async {
    if (height < 0 || page < 0) throw ArgumentError('Negative height or page');
    return pb.TxHistoryPage.fromBuffer(
      await _request('block-txs/$height?page=$page'),
    );
  }

  Future<List<int>> rawTx(String txid) async =>
      pb.RawTx.fromBuffer(await _request('raw-tx/${_hex(txid, 32)}')).rawTx;
  Future<pb.BlockHeader> blockHeader(String hashOrHeight) async {
    if (!RegExp(r'^(0|[1-9][0-9]*)$').hasMatch(hashOrHeight)) {
      _hex(hashOrHeight, 32);
    }
    final header = pb.BlockHeader.fromBuffer(
      await _request('block-header/$hashOrHeight'),
    );
    if (header.rawHeader.length != 160) {
      throw FormatException('Expected 160-byte Lotus header');
    }
    return header;
  }

  Future<pb.ScriptUtxos> scriptUtxos(String type, String payload) async {
    if (!['p2pkh', 'p2sh', 'p2pk', 'p2tr', 'other'].contains(type)) {
      throw ArgumentError.value(type, 'type', 'Unknown script type');
    }
    return pb.ScriptUtxos.fromBuffer(
      await _request('script/$type/${_hex(payload)}/utxos'),
    );
  }

  Future<String> broadcast(List<int> rawTx) async {
    final result = pb.BroadcastTxResponse.fromBuffer(
      await _request(
        'broadcast-tx',
        body: pb.BroadcastTxRequest(rawTx: rawTx).writeToBuffer(),
      ),
    );
    return HEX.encode(result.txid.reversed.toList());
  }

  void close() {
    if (_ownsHttp) _http.close();
  }
}
