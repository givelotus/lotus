# Implementation Plan: Unified `Boost.Beast` HTTP/WebSocket Server, `/chronik/*` Single-Port Delegation, and `/p2p/ws` Encrypted/Compressed P2P Transport

**Target Baseline:** Existing eCash `bitcoind` (`daemon/patches/ecash/`, layered right after `ecash/054` before the `v2/` patch stack, so both eCash `bitcoind` and Lotus V2 inherit it cleanly).

---

## Architectural Overview

1. **Replace `libevent` (`evhttp`) in `src/httpserver.cpp` with `Boost.Beast` (`<boost/beast/http.hpp>`, `<boost/beast/websocket.hpp>`, `<boost/beast/ssl.hpp>`)** running on the existing `Boost.Asio` C++20 `co_await` coroutine pool (`HTTPCoroutinePool`), while keeping the public `HTTPRequest`, `RegisterHTTPHandler`, `RegisterHTTPAsyncHandler`, and `HTTPEvent` signatures in `src/httpserver.h` **100% source-compatible** so zero existing RPC/REST handlers (`src/httprpc.cpp`, `src/rest.cpp`) break.
2. **Auto-Detect TLS vs. Plain HTTP/WS on the Same Port (`boost::beast::async_detect_ssl`):**
   - Each bound RPC/HTTP port (`-rpcport`, default `8332` in eCash / `10604` in Lotus V2) peeks at the first bytes of each incoming TCP connection via `boost::beast::async_detect_ssl`.
   - If the client sends a TLS `ClientHello` (`https://` or `wss://`), the connection is wrapped in `boost::beast::ssl_stream` using either `-tlscert` / `-tlskey` or an auto-generated in-memory ECDSA P-256 self-signed certificate (`-tlsephemeral=1`, default enabled).
   - If the client sends plain ASCII (`http://` or `ws://`, e.g., localhost or behind a TLS-terminating Kubernetes Ingress / Cloudflare / Alchemy Load Balancer), it runs directly over `boost::beast::tcp_stream`.
   - Optional permissive mTLS (`-tlsmutual=1`): sets `boost::asio::ssl::verify_peer` (without `verify_fail_if_no_peer_cert` on the port, enforcing peer cert presence or `v2hello` signature specifically on `/p2p/ws`).
3. **Delegate `/chronik/*` (HTTP + `/chronik/ws` WebSocket) on the Main RPC Port to Chronik (`hyper`/`axum`):**
   - Chronik keeps its existing secondary port (`-chronikbind`, default `127.0.0.1:8321`), AND `src/httpserver.cpp` registers a built-in prefix route `/chronik` (exempt from `-rpcuser`/`-rpcpassword` basic auth, configurable via `-chronikpubliconrpcport=1`, default `1` when `-chronik=1`).
   - Regular HTTP requests to `/chronik/<subpath>` strip the `/chronik` prefix and asynchronously proxy over a pooled loopback `boost::asio::ip::tcp::socket` to Chronik's bound `SocketAddr` (`127.0.0.1:8321`).
   - WebSocket upgrade requests to `/chronik/ws` upgrade the client via `boost::beast::websocket::stream` (or raw TCP splice after `101 Switching Protocols`) and bidirectionally pump frames between the client socket and `127.0.0.1:8321/ws`.
   - When built with `-DBUILD_CHRONIK=OFF` or run with `-chronik=0`, `/chronik/*` simply returns `404 Not Found` with zero compile-time dependency on Rust/Chronik.
4. **Additive P2P over WebSockets on `/p2p/ws` with Streaming `zstd` + Prebaked Dictionary (`p2p-zstd-v1`) Alongside Existing Raw TCP P2P:**
   - **Normal TCP P2P (`-port=8333`, `CConnman::ListenSocket`, `CConnman::AcceptConnection`, `CConnman::ConnectNode("ip:port")`) remains 100% intact, unmodified, and enabled by default.** A single node simultaneously accepts legacy raw TCP peers on port `8333` and WebSocket peers on `/p2p/ws`, relaying blocks and transactions seamlessly across both transports.
   - Inbound requests to `GET /p2p/ws` with `Upgrade: websocket` on the HTTP port negotiate **streaming `libzstd` compression with a prebaked P2P/Script dictionary (`Sec-WebSocket-Protocol: p2p-zstd-v1`)** (with automatic fallback to raw streaming `p2p-zstd` or RFC 7692 `permessage-deflate` for generic WebSocket clients) and hand the upgraded connection to `CConnman` via a local `socketpair(AF_UNIX, SOCK_STREAM, 0)` bridge.
   - Using `ZSTD_CCtx_refCDict` + `ZSTD_compressStream2(..., ZSTD_e_flush)` on a persistent per-peer `ZSTD_CCtx` gives immediate high compression on the very first small packet (via the prebaked dictionary of P2P headers, `inv`/`ava` prefixes, P2PKH/P2SH/CashToken/Lotus V2 `TMPL_SCRIPT` templates, and sequence/version boilerplate) **and** maintains a live 128 KB sliding window across consecutive P2P messages at 500+ MB/s (`< 3 us` latency per message).
   - Every Bitcoin/Lotus P2P message flows through the existing 24-byte `CMessageHeader || payload` wire format inside binary WebSocket frames (`ws.binary(true)`), so `V1TransportDeserializer`, `V1TransportSerializer`, `CNode`, and `src/net_processing.cpp` require **zero modifications**.
   - Outbound peers use normal raw TCP when given `"ip:port"` or `"host:port"`, and use the WebSocket dialer when prefixed with `ws://` or `wss://` (`-addnode=wss://node.example.com:443/p2p/ws` or `-connect=ws://...`), setting **TLS SNI (`SSL_set_tlsext_host_name`)** and the HTTP **`Host:`** header so standard Kubernetes Ingresses, Cloudflare tunnels, and L7 load balancers route P2P traffic identically to normal web traffic.

---

## 5-Commit Atomic Implementation Sequence

Implement this as 4 sequential, self-contained commits on top of the eCash `bitcoind` tree (`daemon/patches/ecash/`), plus a 5th commit in `daemon/patches/v2/` for Lotus V2. Every commit must compile cleanly (`ninja bitcoind test_bitcoin`) and pass `test_bitcoin` and `httpserver_tests`.

---

### Commit 1: `http: replace libevent evhttp with Boost.Beast HTTP/1.1 + async_detect_ssl + zstd server`

#### Files to Modify
- `cmake/modules/FindZstd.cmake` (new file following `cmake/modules/FindJemalloc.cmake`):
  - Uses `include(BrewHelper)` (`find_brew_prefix(_Zstd_BREW_HINT zstd)`) and `include(ExternalLibraryHelper)` (`find_component(Zstd zstd NAMES zstd HINTS "${_Zstd_BREW_HINT}" ...)`), exposing `Zstd::zstd`. On a developer's machine CMake uses its standard default library resolution; in an isolated Guix/`depends` build, `CMAKE_FIND_ROOT_PATH` resolves `Zstd::zstd` to the static `libzstd.a` built in `depends/`.
- `src/CMakeLists.txt`:
  - Link `OpenSSL::SSL`, `OpenSSL::Crypto`, and `Zstd::zstd` (`find_package(Zstd REQUIRED)` + `target_compile_definitions(server PRIVATE HAVE_ZSTD=1)`) to `server`.
- `depends/packages/zstd.mk` & `depends/packages/packages.mk`:
  - Add `zstd` to `packages` in `depends/packages/packages.mk` and create `depends/packages/zstd.mk` (pinned tarball + `sha256_hash`, building `$(MAKE) -C lib libzstd.a` and staging `$(MAKE) -C lib DESTDIR=$($(package)_staging_dir) PREFIX=$(host_prefix) install-static install-includes`) so isolated Guix release builds compile and statically link `libzstd.a`.
- `src/httpserver.h`
- `src/httpserver.cpp`
- `src/httprpc.cpp`
- `src/init.cpp` (register CLI args `-tlscert`, `-tlskey`, `-tlsephemeral`, `-tlsmutual`)
- `src/test/httpserver_tests.cpp`

#### Exact Implementation Steps
1. **`HTTPEvent` Timer Replacement (`src/httpserver.h`, `src/httpserver.cpp`, `src/httprpc.cpp`):**
   - `EventBase()` and `HTTPEvent` are only used by `HTTPRPCTimer` in `src/httprpc.cpp:48-76`.
   - Replace `HTTPEvent`'s internal `struct event *ev` with a `boost::asio::steady_timer` running on `g_work_queue->GetExecutor()` (keep `EventBase()` returning a non-null dummy token or `reinterpret_cast<struct event_base*>(1)` so `assert(eventBase)` in `src/httprpc.cpp:947` still passes without changing `httprpc.cpp` callers, or update `HTTPRPCTimer` to use `GetHTTPThreadPoolExecutor()`).
2. **`HTTPRequest` Backing Store & HTTP `zstd` Compression (`src/httpserver.h`, `src/httpserver.cpp`):**
   - Replace `struct evhttp_request *req` inside `HTTPRequest` with an opaque `struct HTTPRequestImpl`:
     ```cpp
     struct HTTPRequestImpl {
         boost::beast::http::request<boost::beast::http::string_body> beast_req;
         boost::beast::http::response<boost::beast::http::string_body> beast_res;
         CService peer_address;
         bool is_tls{false};
         bool has_valid_client_cert{false};
         std::string client_cert_fingerprint_hex;
         std::function<void(boost::beast::http::response<boost::beast::http::string_body>&&)> send_reply_fn;
     };
     ```
   - Implement all existing `HTTPRequest` methods against `HTTPRequestImpl`:
     - `GetURI()`: returns `std::string(m_impl->beast_req.target())`.
     - `GetPeer()`: returns `m_impl->peer_address`.
     - `GetRequestMethod()`: maps `http::verb::get -> GET`, `post -> POST`, `head -> HEAD`, `put -> PUT`, `options -> OPTIONS`, else `UNKNOWN`.
     - `GetHeader(hdr)`: looks up `hdr` case-insensitively in `m_impl->beast_req` (`m_impl->beast_req.find(hdr)`).
     - `ReadBody()`: if `beast_req[http::field::content_encoding] == "zstd"`, decompress with `ZSTD_decompress` (bounded to `max_body_size`); then move and clear `m_impl->beast_req.body()`.
     - `WriteHeader(hdr, value)`: calls `m_impl->beast_res.set(hdr, value)`.
     - `WriteReply(nStatus, strReply)`:
       - If `strReply.size() >= 512`, `beast_res.find(http::field::content_encoding) == beast_res.end()`, and `beast_req[http::field::accept_encoding]` contains `"zstd"`, compress `strReply` via `ZSTD_compress(..., level = 1)` and set `beast_res.set(http::field::content_encoding, "zstd")`.
       - Set `m_impl->beast_res.result(static_cast<unsigned>(nStatus))`, assign `m_impl->beast_res.body()`, call `m_impl->beast_res.prepare_payload()`, and invoke `m_impl->send_reply_fn(std::move(m_impl->beast_res))`.
3. **RFC 3986 Query Parameter Parser (`GetQueryParameterFromUri` in `src/httpserver.cpp`):**
   - Keep `GetQueryParameterFromUri(const char *uri, const std::string &key)` passing all cases in `src/test/httpserver_tests.cpp` (validate `%` hex escapes so a trailing or non-hex `%` throws `std::runtime_error("URI parsing failed, it likely contained RFC 3986 invalid characters")` exactly as tested in `httpserver_tests.cpp:43-48`).
4. **`Boost.Beast` Listener + `async_detect_ssl` Session Coroutine (`src/httpserver.cpp`):**
   - Create an `ssl::context g_ssl_ctx{ssl::context::tlsv12}` (supporting TLS 1.2 and TLS 1.3):
     - If `-tlscert` and `-tlskey` are set, load them via `use_certificate_chain_file` / `use_private_key_file`.
     - Otherwise, generate or load `<datadir>/node_tls_key.pem` and `<datadir>/node_tls_cert.pem` (EC P-256 key via `EVP_EC_gen("P-256")` and self-signed `X509` cert valid for 10 years) and load into `g_ssl_ctx`.
     - If `-tlsmutual=1`, set `g_ssl_ctx.set_verify_mode(ssl::verify_peer)` with a verify callback that accepts self-signed peer node certs and records their SHA-256 fingerprint in `client_cert_fingerprint_hex`.
   - Bind `tcp::acceptor`s on all `(host, port)` pairs produced by `HTTPBindAddresses()`.
   - For each accepted `tcp::socket`:
     - Spawn a coroutine `HandleConnection(tcp::socket sock, CService peer, Config &config)`:
       1. Set socket timeout (`DEFAULT_HTTP_SERVER_TIMEOUT` via `beast::get_lowest_layer(stream).expires_after(...)`).
       2. Call `bool is_tls = co_await boost::beast::async_detect_ssl(tcp_stream, flat_buffer, boost::asio::use_awaitable);`
       3. If `is_tls`, wrap in `boost::beast::ssl_stream<boost::beast::tcp_stream>` and `co_await ssl_stream.async_handshake(ssl::stream_base::server, flat_buffer.data(), use_awaitable)` (consuming buffered bytes).
       4. Loop over HTTP/1.1 Keep-Alive requests using `http::request_parser<http::string_body>` with `header_limit(MAX_HEADERS_SIZE)` and `body_limit(MIN_SUPPORTED_BODY_SIZE + 2 * config.GetMaxBlockSize())`:
          - Check `boost::beast::websocket::is_upgrade(req)`: if true, dispatch to registered WebSocket handlers (Commit 2 & Commit 3).
          - Otherwise check `ClientAllowed(peer)` (for non-public paths) and dispatch to `pathHandlers` via `g_work_queue`, awaiting the reply and writing it via `http::async_write`.

---

### Commit 2: `http: delegate /chronik/* and /chronik/ws on main RPC port to Chronik server`

#### Files to Modify
- `src/httpserver.h`
- `src/httpserver.cpp`
- `src/init.cpp`
- `chronik/chronik-cpp/chronik.cpp` (or `src/httpserver.cpp` via `-chronikbind` / default Chronik port `8321`)
- `test/functional/chronik_rpc_port_proxy.py` (new test)

#### Exact Implementation Steps
1. **Public Prefix Whitelist on Main RPC Port (`src/httpserver.h`, `src/httpserver.cpp`):**
   - Add `void RegisterPublicHTTPPrefix(const std::string &prefix);` (or a `bool allowPublicAccess` flag on `HTTPPathHandler`) so requests matching `/chronik` and `/p2p/ws` bypass `ClientAllowed(peer)` IP subnet rejection when `-chronikpubliconrpcport=1` (default `1`) is enabled, while `/` and `/wallet/*` continue to strictly enforce `ClientAllowed(peer)` and RPC Basic/Auth credentials.
2. **Async HTTP Proxy Handler for `/chronik` (`src/httpserver.cpp`):**
   - Register a prefix handler for `"/chronik"` (`exactMatch = false`):
     - Compute target URI: strip `"/chronik"` prefix (if empty, use `"/"`).
     - Connect asynchronously to Chronik's local listener (`127.0.0.1:8321`, or the first `SocketAddr` configured by `-chronikbind`) via `boost::beast::tcp_stream`.
     - Forward method (`GET`, `POST`, `OPTIONS`), target URI, headers (`Content-Type`, `Accept`, `Origin`, `X-Forwarded-For`), and body using `boost::beast::http::async_write`.
     - Read the response with `boost::beast::http::async_read` (using `http::string_body`), copy status code and response headers (`Content-Type`, `Access-Control-Allow-*`) into `HTTPRequest`, and call `req->WriteReply(status, body)` (which also automatically applies `Content-Encoding: zstd` if the client requested `Accept-Encoding: zstd`!).
3. **Async WebSocket Proxy for `/chronik/ws` (`src/httpserver.cpp`):**
   - When `boost::beast::websocket::is_upgrade(req)` is true and `req.target()` starts with `"/chronik/ws"`:
     - Upgrade the incoming client stream (`tcp_stream` or `ssl_stream`) using `boost::beast::websocket::stream`.
     - Open an outbound `boost::beast::websocket::stream<boost::beast::tcp_stream>` to `127.0.0.1:8321/ws`.
     - Run two concurrent coroutines (`client_to_chronik` and `chronik_to_client`) forwarding binary/text WebSocket frames until either side closes.

---

### Commit 3: `net: add WebSocket P2P transport (/p2p/ws) with streaming zstd and prebaked P2P dictionary`

#### Files to Modify
- `src/net_zstd_dict.h` (new file: static prebaked P2P/Script dictionary + RAII `P2PZstdStream` wrapper)
- `src/httpserver.h`
- `src/httpserver.cpp`
- `src/net.h`
- `src/net.cpp`
- `src/test/net_tests.cpp`

#### Exact Implementation Steps
1. **Prebaked P2P + Script Dictionary & Streaming `zstd` Context (`src/net_zstd_dict.h`):**
   - Define `inline constexpr uint8_t P2P_ZSTD_DICT_V1[]` (~8–16 KB deterministic byte array) containing:
     - **P2P Framing & Command Headers:** Network magic sequences (`\xe3\xe1\xf3\xe8`, `\xf0\xb5\xf2\xf4`, `\xda\xb5\xbf\xfa`), 12-byte zero-padded command names (`"version\0\0\0\0\0"`, `"verack\0\0\0\0\0\0"`, `"sendheaders\0"`, `"sendcmpct\0\0\0"`, `"sendaddrv2\0\0"`, `"feefilter\0\0\0"`, `"inv\0\0\0\0\0\0\0\0\0"`, `"getdata\0\0\0\0\0"`, `"notfound\0\0\0\0"`, `"tx\0\0\0\0\0\0\0\0\0\0"`, `"headers\0\0\0\0\0"`, `"cmpctblock\0\0"`, `"getblocktxn\0"`, `"blocktxn\0\0\0\0"`, `"avapoll\0\0\0\0\0"`, `"avaresponse\0"`, `"avaproof\0\0\0\0"`, `"ping\0\0\0\0\0\0\0\0"`, `"pong\0\0\0\0\0\0\0\0"`), and common `CInv` 4-byte type tags (`\x01\x00\x00\x00`, `\x02\x00\x00\x00`, `\x04\x00\x00\x00`, `\x00\x00\x00\x02`).
     - **Transaction & Script Templates:** Standard transaction version/sequence/locktime bytes (`\x02\x00\x00\x00`, `\x01\x00\x00\x00`, `\xff\xff\xff\xff`, `\xfe\xff\xff\xff`, `\x00\x00\x00\x00`), P2PKH (`\x19\x76\xa9\x14`, `\x88\xac`), P2SH (`\x17\xa9\x14`, `\x87`), CashToken prefix (`\xef`), and Lotus V2 Taproot / `TMPL_SCRIPT` covenant sequences (`\x22\x51\x20`, `\x50`, `\x62`, `\x6d`, `\xeb`, `\xec`, `\xed`, `\xdf`, `\xde`, `\xbd`, `\xac`).
   - Initialize singleton `const ZSTD_CDict *GetP2PZstdCDict(int level = 1)` and `const ZSTD_DDict *GetP2PZstdDDict()` once on first call via `ZSTD_createCDict(P2P_ZSTD_DICT_V1, sizeof(P2P_ZSTD_DICT_V1), level)` and `ZSTD_createDDict(P2P_ZSTD_DICT_V1, sizeof(P2P_ZSTD_DICT_V1))`.
   - Implement `class P2PZstdSession`:
     - Owns `ZSTD_CCtx *m_cctx` and `ZSTD_DCtx *m_dctx`, calling `ZSTD_CCtx_refCDict(m_cctx, GetP2PZstdCDict())` and `ZSTD_DCtx_refDDict(m_dctx, GetP2PZstdDDict())` when `use_dict == true` (`p2p-zstd-v1`).
     - `CompressFrame(Span<const uint8_t> in, std::vector<uint8_t> &out)`: calls `ZSTD_compressStream2(m_cctx, &out_buf, &in_buf, ZSTD_e_flush)` so the sliding window stays warm across all subsequent P2P messages on that connection!
     - `DecompressFrame(Span<const uint8_t> in, std::vector<uint8_t> &out)`: calls `ZSTD_decompressStream(m_dctx, &out_buf, &in_buf)`.
2. **Inbound `/p2p/ws` Endpoint & `socketpair` Bridge in `src/httpserver.cpp`:**
   - `CConnman` in `src/net.cpp` interacts with every peer strictly through `std::shared_ptr<Sock> m_sock` (`m_sock->Send(...)`, `m_sock->Recv(...)`, and `m_sock->Get()` for `poll()`/`select()`) plus `V1TransportSerializer` / `V1TransportDeserializer`.
   - Register a WebSocket upgrade handler at `/p2p/ws`:
     - Inspect `req[http::field::sec_websocket_protocol]`:
       - If it contains `"p2p-zstd-v1"`, respond with `Sec-WebSocket-Protocol: p2p-zstd-v1` and enable `P2PZstdSession(/*use_dict=*/true)` on the pump coroutines (leaving `permessage_deflate` disabled so we don't double-compress).
       - Else if it contains `"p2p-zstd"`, respond with `Sec-WebSocket-Protocol: p2p-zstd` and enable `P2PZstdSession(/*use_dict=*/false)`.
       - Otherwise, enable `boost::beast::websocket::permessage_deflate` (`pmd.server_enable = true; pmd.client_enable = true; ws.set_option(pmd);`) as a standard RFC 7692 fallback.
     - Call `ws.binary(true); co_await ws.async_accept(req, boost::asio::use_awaitable);`
     - Create `int sv[2]; socketpair(AF_UNIX, SOCK_STREAM, 0, sv);`
     - Hand `sv[0]` + the peer's real `CAddress` (from the TCP connection or `X-Forwarded-For` when behind a trusted local proxy) to `CConnman::AcceptWebSocketPeer(SOCKET fd, const CAddress &addr, bool is_tls, const std::string &peer_cert_fp)`.
     - Spawn two coroutines pumping bytes between `sv[1]` and `ws`:
       - `sv[1] -> ws`: reads available P2P wire bytes from `sv[1]` (up to 256 KB per batch), runs `zstd_session.CompressFrame(...)` (if `zstd` negotiated), and writes as a single binary WebSocket frame via `ws.async_write`.
       - `ws -> sv[1]`: reads each binary WebSocket frame via `ws.async_read`, runs `zstd_session.DecompressFrame(...)` (if `zstd` negotiated), and writes the raw P2P bytes to `sv[1]`.

---

### Commit 4: `net: support outbound wss:// and ws:// domain:port P2P connections and BIP155 ADDRv2 advertisement`

#### Files to Modify
- `src/netaddress.h`
- `src/netaddress.cpp`
- `src/net.h`
- `src/net.cpp`
- `src/net_processing.cpp`
- `src/init.cpp`
- `test/functional/p2p_websocket_tls.py` (new end-to-end functional test)

#### Exact Implementation Steps
1. **Backward-Compatible Return-Path Advertisement via BIP155 `ADDRv2` (`src/netaddress.h`, `src/netaddress.cpp`, `src/net_processing.cpp`):**
   - Legacy `addr` (BIP155 `Encoding::V1`) only supports fixed 16-byte IPv4/IPv6 addresses (`V1_SERIALIZATION_SIZE = 16`), so a `domain:port` return path cannot be sent in `ADDRv1` messages.
   - However, BIP155 `ADDRv2` (`src/netaddress.h:305-344`) supports variable-length addresses up to `MAX_ADDRV2_SIZE = 512` bytes, and unpatched `ADDRv2` nodes are Already Required by BIP155 (`SetNetFromBIP155Network` in `src/netaddress.h:337`) to **silently ignore** unrecognized BIP155 network IDs without banning or disconnecting!
   - Therefore:
     1. Add `NET_WSS` (before `NET_MAX`) to `enum Network` and `WSS_DOMAIN = 0x10` to `enum BIP155Network : uint8_t` in `src/netaddress.h` (with `ADDR_WSS_MAX_SIZE = 253`, the maximum DNS FQDN length).
     2. In `CNetAddr` (`src/netaddress.h` / `src/netaddress.cpp`), allow `m_addr` to store the ASCII lowercase FQDN bytes when `m_net == NET_WSS`, and implement `ToStringAddr()` returning the domain string.
     3. In `SerializeV1Array` (`src/netaddress.h:349`), serialize `NET_WSS` as all-zeros (`0.0.0.0`, non-routable) and in `src/net_processing.cpp` (where `PushAddress` checks `peer->m_wants_addrv2`), **only relay `NET_WSS` addresses to peers that negotiated `sendaddrv2` (`m_wants_addrv2 == true`)**, identically to how `NET_TORV3`, `NET_I2P`, and `NET_CJDNS` are already gated in `src/net_processing.cpp`!
     4. Add `-externaldomain=<domain[:port]>` in `src/init.cpp` which registers a `NET_WSS` local service address via `AddLocal(CService(wss_netaddr, port), LOCAL_MANUAL)`.
     - **Result:**
       - Legacy `ADDRv1` peers never receive `domain:port`.
       - Unpatched `ADDRv2` peers silently skip `BIP155Network::WSS_DOMAIN (0x10)` per BIP155 rules.
       - Upgraded peers store `NET_WSS` in `AddrMan`, gossip it to other `ADDRv2` peers, and dial it via `wss://<domain>:<port>/p2p/ws`!
2. **Strictly Additive Outbound WebSocket Dialer (`CConnman::ConnectWebSocketNode` in `src/net.cpp`):**
   - Keep `CConnman::ConnectNode` for normal `NET_IPV4` / `NET_IPV6` `"ip:port"` peers 100% unchanged so existing TCP P2P behavior, DNS seeds, and `addr` gossip are completely unaffected.
   - When `ConnectNode` is given a `CAddress` with `GetNetwork() == NET_WSS` OR a string starting with `ws://` or `wss://` (e.g., `wss://node.example.com:443/p2p/ws` or `ws://127.0.0.1:8332/p2p/ws`), dispatch to `CConnman::ConnectWebSocketNode`:
     1. Parse scheme (`ws` vs `wss`), `domain`, `port` (default `80` for `ws`, `443` for `wss`), and `target` (default `"/p2p/ws"`).
     2. Resolve `domain:port` via `boost::asio::ip::tcp::resolver` on the `Boost.Asio` IO context.
     3. If `wss://`, wrap in `boost::beast::ssl_stream<boost::beast::tcp_stream>`, set **TLS SNI** via `SSL_set_tlsext_host_name(ssl_stream.native_handle(), domain.c_str())`, and run `async_handshake(ssl::stream_base::client)`.
     4. Wrap in `boost::beast::websocket::stream`, set `ws.binary(true)`, attach a decorator setting `req.set(http::field::sec_websocket_protocol, "p2p-zstd-v1, p2p-zstd")`, and pass a `websocket::response_type res` to `ws.async_handshake(res, host_header, target)` (with `Host: <domain>:<port>`).
     5. Inspect `res[http::field::sec_websocket_protocol]`: if `"p2p-zstd-v1"`, enable `P2PZstdSession(/*use_dict=*/true)`; else if `"p2p-zstd"`, enable `P2PZstdSession(/*use_dict=*/false)`;Create `socketpair(AF_UNIX, SOCK_STREAM, 0, sv)`, pump `sv[1] <-> ws` on the `Boost.Asio` coroutine pool, and pass `std::make_unique<Sock>(sv[0])` into `CNode` creation inside `CConnman::ConnectNode`!
3. **End-to-End Hybrid TCP + WebSocket + `zstd` Dictionary Verification (`test/functional/p2p_websocket_tls.py`):**
   - Start a 3-node network (`Node 0`, `Node 1`, `Node 2`):
     - `Node 0` is configured with `-externaldomain=localhost:<node0_rpcport>`.
     - `Node 1` connects to `Node 0` over **`wss://localhost:<node0_rpcport>/p2p/ws`** (WebSocket + TLS + `p2p-zstd-v1` prebaked dictionary streaming compression).
     - `Node 2` connects to `Node 0` over **normal raw TCP P2P (`127.0.0.1:<node0_p2pport>`)**.
   - Verify:
     1. JSON-RPC (`getblockchaininfo`) works over both `http://` and `https://` on `Node 0`'s RPC port (`async_detect_ssl`), including `Accept-Encoding: zstd` (`Content-Encoding: zstd`).
     2. `/chronik/blockchain-info` and `/chronik/ws` work on `Node 0`'s main RPC port.
     3. `Node 0` advertises its `NET_WSS` (`localhost:<node0_rpcport>`) address via `addrv2` without breaking `ADDRv1` peers.
     4. Transactions broadcast on `Node 1` (WSS `/p2p/ws` with `p2p-zstd-v1`) relay through `Node 0` to `Node 2` (normal TCP P2P), and blocks mined on `Node 2` (normal TCP P2P) relay through `Node 0` to `Node 1` (WSS `/p2p/ws`).

---

### Commit 5 (Lotus V2-Only Final Patch in `daemon/patches/v2/`): `v2: remove legacy raw TCP P2P listener and use /p2p/ws exclusively`

> **Note:** Commits 1–4 live in `daemon/patches/ecash/` (upstream-compatible with eCash ABC, keeping raw TCP P2P and `/p2p/ws` side-by-side). Commit 5 is layered at the very end of `daemon/patches/v2/` for **Lotus (`lotusd`)**, where we do not want legacy raw TCP P2P sockets at all.

#### Files to Modify
- `src/net.cpp`
- `src/init.cpp`
- `src/chainparams.cpp`

#### Exact Implementation Steps
1. **Remove Raw TCP P2P Socket Listener (`src/init.cpp`, `src/net.cpp`):**
   - In `AppInitMain` (`src/init.cpp`) and `CConnman::InitBinds` (`src/net.cpp`), skip binding raw TCP P2P `vhListenSocket` listeners (`BindListenPort`). Inbound P2P connections are accepted exclusively via `/p2p/ws` on the unified `Boost.Beast` HTTP/TLS port (`10604` mainnet / `11604` testnet / `12604` regtest).
   - In `CConnman::ThreadSocketHandler` (`src/net.cpp`), skip the `vhListenSocket` accept loop (all inbound WebSocket peers arrive via `CConnman::AcceptWebSocketPeer` from `/p2p/ws`).
2. **Default All Outbound P2P Connections to `/p2p/ws` (`src/net.cpp`):**
   - In `CConnman::ConnectNode`, route all outbound peer connections (`ip:port` and `domain:port` alike) through `ConnectWebSocketNode` (`wss://<host>:<port>/p2p/ws` with `async_detect_ssl` fallback to `ws://` on regtest/local loopback if `-tlsephemeral=0`), so every Lotus node communicates exclusively over WebSocket `/p2p/ws` on a single unified port per daemon.

---

## Isolated Worktree, 2-Node Regtest WebSocket Test & A/B Benchmark Plan

To execute this cleanly in parallel without interfering with any ongoing patch rebasing in `daemon/workspace-v2` or other worktrees:

### Phase 1: Isolated Worktree & Baseline Binary Capture (`evhttp` + `Boost.Asio` Coroutine Pool)

1. **Create Dedicated Worktree at `ecash-optimizations-tip` (`8ea9ea122a`):**
   ```bash
   git -C /Users/shammah/repos/lotus-v2-optimizations/daemon/workspace-v2 \
     worktree add -b feat/beast-http-ws-p2p /private/tmp/wt-beast-http-p2p ecash-optimizations-tip
   ```
   - **Strict Isolation Rule:** Only modify files inside `/private/tmp/wt-beast-http-p2p` and build inside `/private/tmp/build-beast-http-p2p`. Never touch `/Users/shammah/repos/lotus-v2-optimizations/daemon/workspace-v2` or run `git gc` / `git worktree prune`.
2. **Configure & Build Baseline (`evhttp` + `HTTPCoroutinePool` from `ecash/012`–`013`) First:**
   ```bash
   cmake -GNinja -B /private/tmp/build-beast-http-p2p -S /private/tmp/wt-beast-http-p2p \
     -DCMAKE_BUILD_TYPE=Release \
     -DBUILD_BITCOIN_WALLET=ON \
     -DBUILD_BITCOIN_QT=OFF \
     -DBUILD_BITCOIN_ZMQ=OFF \
     -DBUILD_CHRONIK=OFF \
     -DENABLE_UPNP=OFF \
     -DENABLE_NATPMP=OFF
   ninja -C /private/tmp/build-beast-http-p2p bitcoind test_bitcoin
   cp /private/tmp/build-beast-http-p2p/src/bitcoind /private/tmp/bitcoind-baseline-evhttp-asio
   ```
   - Saving `/private/tmp/bitcoind-baseline-evhttp-asio` before touching `src/httpserver.cpp` gives an exact apples-to-apples binary for benchmarking the existing `evhttp` + `Boost.Asio` `HTTPCoroutinePool` implementation against the new `Boost.Beast` + `HTTPCoroutinePool` implementation, AND pre-compiles 98% of the object files in `/private/tmp/build-beast-http-p2p` so subsequent `ninja` rebuilds after editing `src/httpserver.cpp` and `src/net.cpp` take `< 5 seconds`!

---

### Phase 2: 2-Node Regtest WebSocket P2P Verification (`wss://` + `p2p-zstd-v1` vs. Raw TCP)

Write and run `/private/tmp/wt-beast-http-p2p/test/functional/p2p_websocket_regtest_bench.py` (or standalone Python harness) that launches two regtest `bitcoind` nodes from `/private/tmp/build-beast-http-p2p/src/bitcoind`:

1. **Node Setup:**
   - **Node 0:** `-regtest -server=1 -rpcport=18443 -port=18444 -tlsephemeral=1 -externaldomain=localhost:18443`
   - **Node 1:** `-regtest -server=1 -rpcport=18445 -port=18446 -tlsephemeral=1 -addnode=wss://localhost:18443/p2p/ws`
2. **Functional Assertions:**
   - Verify `getpeerinfo` on both nodes shows the peer connected over `/p2p/ws` with `tls=true` and `compression="p2p-zstd-v1"`.
   - Verify `Node 0`'s single port `18443` responds to:
     - Plain `http://127.0.0.1:18443/` JSON-RPC (`getblockchaininfo`)
     - Encrypted `https://127.0.0.1:18443/` JSON-RPC (`getblockchaininfo` with `-k`)
     - `Accept-Encoding: zstd` JSON-RPC (`getblock` with verbosity 2), verifying `Content-Encoding: zstd` header and valid `zstd` decompression
     - WebSocket P2P upgrade at `wss://localhost:18443/p2p/ws`
   - Mine 101 blocks on Node 0; verify Node 1 syncs to height 101 over `wss://localhost:18443/p2p/ws`.
   - Broadcast 500 transactions on Node 1; verify all 500 enter Node 0's mempool, mine 1 block on Node 0, and verify both nodes reach height 102 with empty mempools.
3. **P2P Bandwidth & Latency Comparison (`wss://` + `p2p-zstd-v1` vs. Legacy Raw TCP):**
   - Run the exact same 500-tx + 10-block relay workload between:
     - **Pair A:** 2 nodes connected via `wss://localhost:18443/p2p/ws` (`p2p-zstd-v1` prebaked dictionary + streaming `ZSTD_e_flush`)
     - **Pair B:** 2 nodes connected via legacy raw TCP (`127.0.0.1:18444`)
   - Query `getnettotals` (`totalbytesrecv`, `totalbytessent`) and measure wall-clock sync time for both pairs to quantify the exact bandwidth reduction (%) and relay latency.

---

### Phase 3: A/B HTTP Server Benchmark (`Boost.Beast` vs. `evhttp` + `Boost.Asio` Coroutine Tasks)

Run an automated Python/asyncio (or `wrk` / multi-threaded keep-alive socket) benchmark script `/private/tmp/bench_http_ab.py` against:
- **Target A (Baseline):** `/private/tmp/bitcoind-baseline-evhttp-asio` (`libevent` `evhttp` + `Boost.Asio` `HTTPCoroutinePool` async task pool from `ecash/012`–`013`)
- **Target B (New - Plain HTTP):** `/private/tmp/build-beast-http-p2p/src/bitcoind` (`Boost.Beast` HTTP/1.1 Keep-Alive + `HTTPCoroutinePool`)
- **Target C (New - HTTPS TLS 1.3):** `/private/tmp/build-beast-http-p2p/src/bitcoind` over `https://` (`async_detect_ssl` + `ssl_stream`)
- **Target D (New - HTTP + `zstd`):** `/private/tmp/build-beast-http-p2p/src/bitcoind` with `Accept-Encoding: zstd`

Measure at concurrency levels **`c = 1`**, **`c = 16`**, and **`c = 64`** (10,000 requests per run over HTTP/1.1 Keep-Alive connections):

| Workload | Description | Metrics Collected |
| :--- | :--- | :--- |
| **1. Small Fast-Path RPC (`getblockchaininfo`)** | Measures pure HTTP parser + `HTTPCoroutinePool` dispatch + response serialization overhead (`~400 B` body) | Throughput (`req/s`), `p50` latency (`us`), `p99` latency (`us`) |
| **2. Large Payload RPC (`getblock` w/ 1,000 txs, verbosity=2)** | Measures large JSON body allocation, socket write throughput, and `Content-Encoding: zstd` wire compression (`~500 KB` uncompressed $\rightarrow$ `zstd`) | Throughput (`req/s`), `MB/s` wire bandwidth, `p50`/`p99` latency (`ms`) |
| **3. JSON-RPC Batch (`[getblockhash x 50]`)** | Measures parallel `co_await` batch fan-out on `HTTPCoroutinePool` under `Boost.Beast` vs `evhttp` | Throughput (`batches/s`), `p50`/`p99` latency (`us`) |
| **4. Pipelined / Mixed RPC + P2P Load** | Concurrent `getrawmempool` RPCs on port `18443` while `/p2p/ws` is actively syncing blocks on the same port | RPC `p99` tail latency under P2P load |



