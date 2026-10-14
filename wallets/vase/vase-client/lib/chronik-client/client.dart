import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:http/http.dart' as http;
import 'package:hex/hex.dart';
import 'package:lotus_dart/chronik.dart' as current;
import 'package:web_socket_channel/web_socket_channel.dart';

import 'chronik.pb.dart' as proto;
import 'client.types.dart';
import 'hex.dart';

/// Client to access a Chronik instance.Plain object, without any
/// connections. */
class ChronikClient {
  final String _url;
  final String _wsUrl;

  /// Create a new client. This just creates an object, without any connections.
  ///
  /// @param url Url of a Chronik instance, with schema and without trailing
  /// slash. E.g. https://chronik.be.cash/xec.
  ChronikClient(String url)
    : _url = url,
      _wsUrl = url.startsWith('https://')
          ? 'wss://${url.substring('https://'.length)}'
          : (url.startsWith('http://')
                ? 'ws://${url.substring('http://'.length)}'
                : throw Exception(
                    "url must start with 'https://' or 'http://', got: $url",
                  )) {
    if (url.endsWith('/')) {
      throw Exception("url cannot end with '/', got: $url");
    }
  }

  /// Broadcasts the `rawTx` on the network.
  /// If `skipSlpCheck` is false, it will be checked that the tx doesn't burn
  /// any SLP tokens before broadcasting.
  Future<BroadcastTxResponse> broadcastTx({
    dynamic rawTx,
    skipSlpCheck = false,
  }) async {
    final request = current.BroadcastTxRequest(
      rawTx: rawTx is String ? HEX.decode(rawTx) : rawTx as List<int>,
      skipTokenChecks: skipSlpCheck,
    );
    final data = await _post(
      url: _url,
      path: "/broadcast-tx",
      data: request.writeToBuffer(),
    );
    final broadcastResponse = current.BroadcastTxResponse.fromBuffer(data);
    return BroadcastTxResponse(txid: toHexRev(broadcastResponse.txid));
  }

  /// Broadcasts the `rawTxs` on the network, only if all of them are valid.
  /// If `skipSlpCheck` is false, it will be checked that the txs don't burn
  /// any SLP tokens before broadcasting.
  Future<BroadcastTxsResponse> broadcastTxs({
    dynamic rawTxs,
    skipSlpCheck = false,
  }) async {
    final request = proto.BroadcastTxsRequest.fromJson(
      jsonEncode({
        'rawTxs':
            (rawTxs as List)
                    .map((rawTx) => rawTx is String ? fromHex(rawTx) : rawTx)
                    .toList()
                as Uint8List,
        'skipSlpCheck': skipSlpCheck,
      }),
    );
    final data = await _post(
      url: _url,
      path: "/broadcast-txs",
      data: request.writeToBuffer(),
    );
    final broadcastResponse = proto.BroadcastTxsResponse.fromBuffer(data);
    return BroadcastTxsResponse(
      txids: broadcastResponse.txids.map(toHexRev).toList(),
    );
  }

  /// Fetch current info of the blockchain, such as tip hash and height. */
  Future<BlockchainInfo> blockchainInfo() async {
    final data = await _get(_url, '/blockchain-info');
    final blockchainInfo = proto.BlockchainInfo.fromBuffer(data);
    return convertToBlockchainInfo(blockchainInfo);
  }

  /// Fetch the block given hash or height. */
  Future<Block> block(dynamic hashOrHeight) async {
    final data = await _get(_url, '/block/$hashOrHeight');
    final block = proto.Block.fromBuffer(data);
    return convertToBlock(block);
  }

  /// Fetch block info of a range of blocks. `startHeight` and `endHeight` are
  /// inclusive ranges. */
  Future<List<BlockInfo>> blocks({
    required int startHeight,
    required int endHeight,
  }) async {
    final data = await _get(_url, '/blocks/$startHeight/$endHeight');
    final blocks = proto.Blocks.fromBuffer(data);
    return blocks.blocks.map(convertToBlockInfo).toList();
  }

  /// Fetch tx details given the txid. */
  Future<Tx> tx(String txid) async {
    final data = await _get(_url, '/tx/$txid');
    final tx = proto.Tx.fromBuffer(data);
    return convertToTx(tx);
  }

  /// Fetch token info and stats given the tokenId. */
  Future<Token> token(String tokenId) async {
    final data = await _get(_url, '/token/$tokenId');
    final token = proto.Token.fromBuffer(data);
    return convertToToken(token);
  }

  /// Validate the given outpoints: whether they are unspent, spent or
  /// never existed. */
  Future<List<UtxoState>> validateUtxos(List<proto.OutPoint> outpoints) async {
    final request = proto.ValidateUtxoRequest.fromJson(
      jsonEncode({'outpoints': outpoints.map(convertToOutPoint).toList()}),
    );
    final data = await _post(
      url: _url,
      path: "/validate-utxos",
      data: request.writeToBuffer(),
    );
    final validationStates = proto.ValidateUtxoResponse.fromBuffer(data);
    return validationStates.utxoStates.map(convertToUxtoState).toList();
  }

  /// Create object that allows fetching script history or UTXOs. */
  ScriptEndpoint script(String scriptType, String scriptPayload) {
    return ScriptEndpoint(
      url: _url,
      scriptType: scriptType,
      scriptPayload: scriptPayload,
    );
  }

  /// Open a WebSocket connection to listen for updates. */
  WsEndpoint ws(WsConfig config) {
    return WsEndpoint(wsUrl: '$_wsUrl/ws', config: config);
  }
}

/// Allows fetching script history and UTXOs. */
class ScriptEndpoint {
  final String url;
  final String scriptType;
  final String scriptPayload;

  ScriptEndpoint({
    required this.url,
    required this.scriptType,
    required this.scriptPayload,
  });

  /// Fetches the tx history of this script, in anti-chronological order.
  /// This means it's ordered by first-seen first. If the tx hasn't been seen
  /// by the indexer before, it's ordered by the block timestamp.
  /// @param page Page index of the tx history.
  /// @param pageSize Number of txs per page.
  Future<TxHistoryPage> history({int? page, int? pageSize}) async {
    final query = page != null && pageSize != null
        ? '?page=$page&page_size=$pageSize'
        : page != null
        ? '?page=$page'
        : pageSize != null
        ? '?page_size=$pageSize'
        : "";
    final data = await _get(
      url,
      '/script/$scriptType/$scriptPayload/history$query',
    );
    final historyPage = proto.TxHistoryPage.fromBuffer(data);
    return TxHistoryPage(
      txs: historyPage.txs.map(convertToTx).toList(),
      numPages: historyPage.numPages,
    );
  }

  /// Fetches the current UTXO set for this script.
  /// It is grouped by output script, in case a script type can match multiple
  /// different output scripts (e.g. Taproot on Lotus). */
  Future<List<ScriptUtxos>> utxos() async {
    final data = await _get(url, '/script/$scriptType/$scriptPayload/utxos');
    final result = current.ScriptUtxos.fromBuffer(data);
    return [
      ScriptUtxos(
        outputScript: toHex(result.script),
        // This wallet cannot preserve token commitments when constructing a spend.
        // Leave all token-bearing outputs untouched rather than burning tokens.
        utxos: result.utxos
            .where((utxo) => !utxo.hasToken())
            .map(
              (utxo) => Utxo(
                outpoint: OutPoint(
                  txid: toHexRev(utxo.outpoint.txid),
                  outIdx: utxo.outpoint.outIdx,
                ),
                blockHeight: utxo.blockHeight,
                isCoinbase: utxo.isCoinbase,
                value: utxo.sats.toString(),
                slpMeta: null,
                network: Network.XPI,
              ),
            )
            .toList(),
      ),
    ];
  }
}

/// Config for a WebSocket connection to Chronik.
class WsConfig {
  const WsConfig({
    this.onMessage,
    this.onConnect,
    this.onReconnect,
    this.onError,
    this.onEnd,
    this.autoReconnect,
  });

  /// Fired when a message is sent from the WebSocket.
  final void Function(SubscribeMsg)? onMessage;

  /// Fired when a connection has been (re)established.
  final void Function()? onConnect;

  /// Fired after a connection has been unexpectedly closed, and before a
  /// reconnection attempt is made. Only fired if `autoReconnect` is true.
  final void Function()? onReconnect;

  /// Fired when an error with the WebSocket occurs.
  final void Function(Object)? onError;

  /// Fired after a connection has been manually closed, or if `autoReconnect`
  /// is false, if the WebSocket disconnects for any reason.
  final void Function()? onEnd;

  /// Whether to automatically reconnect on disconnect, default true.
  final bool? autoReconnect;
}

/// WebSocket connection to Chronik.
class WsEndpoint {
  void Function(SubscribeMsg)? onMessage;
  void Function()? onConnect;
  void Function()? onReconnect;
  void Function(Object)? onError;
  void Function()? onEnd;
  bool autoReconnect;

  WebSocketChannel? _ws;
  final String _wsUrl;
  bool _manuallyClosed = false;
  bool _connected = false;
  Timer? _reconnectTimer;
  final List<Subscription> _subs = [];

  WsEndpoint({required String wsUrl, required WsConfig config})
    : _wsUrl = wsUrl,
      autoReconnect = config.autoReconnect ?? true {
    onMessage = config.onMessage;
    onConnect = config.onConnect;
    onReconnect = config.onReconnect;
    onError = config.onError;
    onEnd = config.onEnd;
    _connect();
  }

  Future<void> waitForOpen() async => await _ws?.ready;

  /// Subscribe with a 20-byte key hash for p2pkh. Repeated calls are idempotent.
  void subscribe(String scriptType, String scriptPayload) {
    if (_subs.any(
      (sub) =>
          sub.scriptType == scriptType && sub.scriptPayload == scriptPayload,
    )) {
      return;
    }
    _subs.add(
      Subscription(scriptType: scriptType, scriptPayload: scriptPayload),
    );
    if (_connected) {
      _subUnsub(
        isSubscribe: true,
        scriptType: scriptType,
        scriptPayload: scriptPayload,
      );
    }
  }

  void unsubscribe(String scriptType, String scriptPayload) {
    _subs.removeWhere(
      (sub) =>
          sub.scriptType == scriptType && sub.scriptPayload == scriptPayload,
    );
    if (_connected) {
      _subUnsub(
        isSubscribe: false,
        scriptType: scriptType,
        scriptPayload: scriptPayload,
      );
    }
  }

  Future<void> close() async {
    _manuallyClosed = true;
    _connected = false;
    _reconnectTimer?.cancel();
    await _ws?.sink.close();
  }

  Future<void> _connect() async {
    if (_manuallyClosed) return;
    final channel = WebSocketChannel.connect(Uri.parse(_wsUrl));
    _ws = channel;
    channel.stream.listen(
      (data) {
        try {
          _handleMsg(data as List<int>);
        } catch (error) {
          onError?.call(error);
        }
      },
      onError: (Object error) => onError?.call(error),
      onDone: () => _disconnected(channel),
    );
    try {
      await channel.ready;
      if (_manuallyClosed || _ws != channel) {
        await channel.sink.close();
        return;
      }
      _connected = true;
      for (final sub in _subs) {
        _subUnsub(
          isSubscribe: true,
          scriptType: sub.scriptType,
          scriptPayload: sub.scriptPayload,
        );
      }
      onConnect?.call();
    } catch (error) {
      onError?.call(error);
      _disconnected(channel);
    }
  }

  void _disconnected(WebSocketChannel channel) {
    if (_ws != channel) return;
    _ws = null;
    _connected = false;
    if (_manuallyClosed || !autoReconnect) {
      onEnd?.call();
      return;
    }
    // A failed endpoint must not trigger an immediate reconnect loop.
    _reconnectTimer = Timer(const Duration(seconds: 2), () {
      onReconnect?.call();
      _connect();
    });
  }

  void _subUnsub({
    required bool isSubscribe,
    required String scriptType,
    required String scriptPayload,
  }) {
    final message = current.WsSub(
      isUnsub: !isSubscribe,
      script: current.WsSubScript(
        scriptType: scriptType,
        payload: HEX.decode(scriptPayload),
      ),
    );
    _ws?.sink.add(message.writeToBuffer());
  }

  void _handleMsg(List<int> data) {
    final message = current.WsMsg.fromBuffer(data);
    if (message.hasError()) {
      onMessage?.call(
        MsgError(errorCode: '', msg: message.error.msg, isUserError: true),
      );
    } else if (message.hasTx()) {
      final txid = toHexRev(message.tx.txid);
      final type = message.tx.msgType;
      if (type == current.TxMsgType.TX_ADDED_TO_MEMPOOL) {
        onMessage?.call(MsgAddedToMempool(txid: txid));
      } else if (type == current.TxMsgType.TX_REMOVED_FROM_MEMPOOL) {
        onMessage?.call(MsgRemovedFromMempool(txid: txid));
      } else if (type == current.TxMsgType.TX_CONFIRMED ||
          type == current.TxMsgType.TX_FINALIZED) {
        onMessage?.call(MsgConfirmed(txid: txid));
      } else if (type == current.TxMsgType.TX_INVALIDATED) {
        onMessage?.call(MsgReorg(txid: txid));
      }
    } else if (message.hasBlock()) {
      final hash = toHexRev(message.block.blockHash);
      if (message.block.msgType == current.BlockMsgType.BLK_CONNECTED) {
        onMessage?.call(MsgBlockConnected(blockHash: hash));
      } else if (message.block.msgType ==
              current.BlockMsgType.BLK_DISCONNECTED ||
          message.block.msgType == current.BlockMsgType.BLK_INVALIDATED) {
        onMessage?.call(MsgBlockDisconnected(blockHash: hash));
      }
    }
  }
}

Future<Uint8List> _get(String url, String path) async {
  final response = await http.get(Uri.parse('$url$path'));
  ensureResponseErrorThrown(response, path);
  return response.bodyBytes;
}

Future<Uint8List> _post({
  required String url,
  required String path,
  required Uint8List data,
}) async {
  final response = await http.post(
    Uri.parse('$url$path'),
    body: data,
    headers: {"Content-Type": "application/x-protobuf"},
  );
  ensureResponseErrorThrown(response, path);
  return response.bodyBytes;
}

void ensureResponseErrorThrown(http.Response response, String path) {
  if (response.statusCode < 200 || response.statusCode >= 300) {
    String message;
    try {
      message = current.Error.fromBuffer(response.bodyBytes).msg;
    } catch (_) {
      message = 'Invalid error response';
    }
    throw current.ChronikException(
      response.statusCode,
      'Failed getting $path: $message',
    );
  }
}
