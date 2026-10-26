# P1: node PWA wallet (replaces bitcoin-qt) and Q1: removing Qt

Status: design, ready to implement. Scope: commits 2–4 of
`lotus-v2-optimizations/docs/plans/pwa-wallet-async-notifications-and-drop-qt-plan.md`.
Commit 1 of that plan (the async wallet notification queue, W1) is out of scope.
This design replaces that plan's commits 2–4 wherever the two disagree.

Fixed user decisions (not reopened here):

- The PWA replaces bitcoin-qt and talks only to the node's wallet RPCs. It is not the Frank app.
- The PWA source lives in `wallets/node-pwa/` in the monorepo `~/repos/lotus`. It is never a daemon patch file.
- The daemon build never reads that directory. Release builds embed a prebuilt bundle, given as a pinned tarball and its sha256 through a CMake option. Development uses `-walletpwadir=`.
- The daemon side is a small, generic, eCash-tier patch: `/wallet/*`, browser-safe RPC auth, `-gui`.
- Qt is deleted from the V2 tier now, and from the eCash tier only once the PWA reaches parity.
- Keep it simple.

---

## 0. What was verified and what was assumed

Verified by reading source at `lotus-v2-repaired-source` commit `3cf1891b91`. I read it with `git show`/`git grep`; nothing was checked out. Note that the branch head has since moved to `596537e978`, a rebased copy with the same subject. `3cf1891b91` is not an ancestor of it.

- **The HTTP server.** `src/httpserver.cpp` matches handlers by prefix, first match in registration order (`pathHandlers`, `DispatchRequest`). `-rpcallowip` is enforced for every non-public request before dispatch (`ClientAllowed`). `-publicbind` listeners reject everything except `/p2p/ws` and `/chronik`.
- **HTTPRequest's API.** `HTTPRequest` exposes `GetURI`, `GetPeer`, `GetRequestMethod` (`GET, POST, HEAD, PUT, OPTIONS`; no `DELETE`; unknown methods get 405), `IsTLS`, `GetHeader`, `WriteHeader`, `ReadBody` and `WriteReply`.
- **Reply compression.** `WriteReply` zstd-compresses (level 1) replies of at least `HTTP_ZSTD_MIN_REPLY_SIZE` when the client accepts zstd. It skips this when a `Content-Encoding` header has already been written (`MaybeCompressZstd`).
- **`/wallet/` is already taken.** `src/httprpc.cpp` `StartHTTPRPC` registers `"/"` (exact) and, with wallet support, `"/wallet/"` (prefix) for JSON-RPC. `/wallet/<name>` is the existing multi-wallet RPC endpoint. That handler accepts POST only; GET gets 405. So `/wallet/*` must be split by method (§1.2).
- **RPC auth.** Auth is `Authorization: Basic` only: `RPCAuthorized`, a 250 ms brute-force delay, `-rpcauth`, `-rpcwhitelist` (per `authUser`), and the cookie file (`GenerateAuthCookie`, user `__cookie__`, in `src/rpc/request.cpp`). CORS applies only with `-rpccorsdomain` (`checkCORS`).
- **Startup.** `src/init.cpp` `AppInitServers` runs `InitHTTPServer` → `StartRPC` → `StartHTTPRPC` → (REST) → `StartHTTPServer`. Nothing registers `-gui`. The only `-gui*`-like flags live in `src/qt/`.
- **Build.** CMake minimum is 3.25 and Python ≥ 3.10 is already `REQUIRED` at configure (top-level `CMakeLists.txt:53`). `check-devtools` exists in `contrib/devtools/CMakeLists.txt`.
- **RPCs the phase 1 PWA needs exist:** `getbalances, getwalletinfo, listtransactions, gettransaction, abandontransaction, sendmany, send, walletcreatefundedpsbt, getnewaddress, setlabel, listreceivedbyaddress, validateaddress, getaddressinfo, walletpassphrase, walletlock, createwallet, loadwallet, unloadwallet, listwallets, listwalletdir, getpeerinfo, listbanned, setban, clearbanned, disconnectnode, setnetworkactive, getnettotals, getblockchaininfo, getnetworkinfo, getmempoolinfo, uptime, getcurrencyinfo, getblockheader, waitfornewblock, help, estimatefee`.
- **Amounts.** `AmountFromValue` accepts strings, so the PWA can send exact decimal strings. Ticker and decimals come from `getcurrencyinfo` (`Currency::get()`; XEC, 2 decimals, at this tip).
- **Native V2 wallet.** `src/wallet/v2_*` is used only by the standalone tools and tests (`test_lotus_v2_wallet`, `lotus-v2-wallet-pilot`) and has no RPC. The PWA therefore uses the ordinary `CWallet` RPCs (SQLite wallet, `v2/033`), not the native V2 wallet.
- **Qt inventory.**
  - `src/qt/` has 355 files.
  - Options: `BUILD_QT`, `ENABLE_QRCODE`/`USE_QRCODE`, `ENABLE_BIP70`, `ENABLE_DBUS_NOTIFICATIONS`/`USE_DBUS`. All are consumed only by `src/qt` (checked by grep).
  - The `translate` and `osx-deploydir` targets are defined in `src/qt/CMakeLists.txt`.
  - Qt-only depends recipes: 15 (listed in §3). The original plan's "16" wrongly includes `cpython`/`native_cpython`. Those serve Chronik plugins (`BUILD_CPYTHON`) and stay. `protobuf` stays as well (Chronik's `test/CMakeLists.txt` uses it).
  - The full list of files outside `src/qt/` that reference Qt is in §3.
- **Patches touching Qt.** In the stack, only eCash-tier `6a796abd2b` touches `src/qt` (`guiutil.cpp`). `99c26c1c71` (`v2/033`) edits `depends/Makefile` and `packages.mk` next to the Qt lines. No V2-tier patch touches `src/qt`.
- **cashaddr users in Qt.** 19 `src/qt` files use cashaddr (matching the coordinator's L5 count). The identity hand-off patches 0001–0003 touch no Qt or depends file.
- **Hand-off patch 0029** (`additions-20261019/generic`) adds `-trustedproxy`. It resolves the client from PROXY headers and X-Forwarded-For (`HTTPConnectionInfo client`) and uses it for `-rpcallowip`. It does not interpret `X-Forwarded-Proto` for requests. It also adds `/livez`, `/readyz`, `/healthz` and `-httphealth`.
- **V2 address format:** `addendum/doc/standards/xpiaddr.md` (in `/private/tmp/build-zero-copy-slab/v2-identity/`, not `src/doc/standards/` as the task said). Addresses are `xpi1`/`txpi1`/`rxpi1`, 61-symbol body, 40-bit checksum, constants `K[hrp]`, uppercase for QR, and the `xpi:` URI scheme.
- **V2 identity patch 0001.** RPC ports 10604/11604/12604. Addresses are still cashaddr until L4.

Assumed, not verified:

- **Browser behaviour.**
  - Chrome, Firefox and Safari treat `http://127.0.0.1` and `http://localhost` as secure contexts: service workers, installability, and `Secure` cookies on localhost.
  - Chrome won't register a service worker on a page with a certificate error.
  - `connect-src 'self'` covers same-origin `ws:`/`wss:` (CSP3).
- **Vendored libraries.** `htm@3.1.1` ships `preact/standalone.module.js` (Preact plus hooks plus htm in one ES module). The nayuki QR Code generator JS (MIT) v1.8.0 is usable as an ES module after a two-line export wrapper. The implementer records the actual sha256 when vendoring.
- **depends.** A depends recipe can stage an unbuilt file (custom `extract_cmds`/`stage_cmds`). Verify against `depends/funcs.mk` when implementing.
- **Darwin Guix.** The darwin branches of `contrib/guix/libexec/build.sh`/`codesign.sh` are not used by Lotus (its Guix overlay is Linux-only, per `daemon/docs/guix-builds.md`).
- **Tier boundary.** The eCash/V2 boundary in the stack is between `fe649023c3` ("doc,contrib: P2P WebSocket guide…", last eCash-tier) and `aa4da8d41b` ("consensus: enforce base consensus rules from genesis…", first V2-tier). I inferred it from subjects; the `layer*-tip` tags in that repo are stale and not ancestors.

---

## 1. Daemon side (eCash tier, generic)

### 1.1 New files and options

New directory `src/walletpwa/`, built as static library `walletpwa`, linked into `server`. It is always built; there is no `#ifdef` and no off-switch at build time.

| File | Content |
|---|---|
| `src/walletpwa/assets.h` | `struct EmbeddedAsset { std::string_view path; std::string_view content_type; std::string_view etag; std::string_view body; std::string_view body_gzip; }` and `std::span<const EmbeddedAsset> EmbeddedBundle(); std::string_view EmbeddedBundleVersion();` |
| `src/walletpwa/serve.{h,cpp}` | Pure functions: `ServeAsset(span, path, headers)` returns a `{status, headers, body}` value; MIME table; path normalisation; ETag matching; encoding choice. No globals, so it is unit-testable. |
| `src/walletpwa/session.{h,cpp}` | Token store, session store, Origin/Host policy, cookie parsing |
| `src/walletpwa/http.{h,cpp}` | Glue to `HTTPRequest`: `StartWalletPwa()`, `StopWalletPwa()`, `bool MaybeServeWalletPwa(HTTPRequest*)`, `std::optional<std::string> AuthorizeWalletPwaSession(HTTPRequest*)` (returns `authUser`) |
| `src/walletpwa/launch.{h,cpp}` | `-gui`: mint a token, build the URL, open the browser |
| `src/walletpwa/rpc.cpp` | RPC `getwalletpwaurl` |
| `contrib/devtools/embed_wallet_pwa.py` | Bundle → generated C++ (stdlib only) |
| `contrib/devtools/test_embed_wallet_pwa.py` | unittest; added to `DEVTOOLS_TESTS_PYTHON` |
| `src/test/walletpwa_tests.cpp` | Unit tests (§1.9) |
| `test/functional/interface_wallet_pwa.py` | Functional test (§1.9) |
| `doc/wallet-pwa.md` | Operator documentation |

Runtime options, registered in `SetupServerArgs`, category RPC:

| Option | Default | Meaning |
|---|---|---|
| `-walletpwa` | `1` | Serve `/wallet/` and `/auth/*`. `0` returns 404 there, and browser sessions are refused. |
| `-walletpwadir=<dir>` | unset | Serve `/wallet/*` from this directory instead of the embedded bundle (development). |
| `-walletpwaorigin=<origin>` | none | Repeatable. Extra allowed browser origins, e.g. `https://node.example.org` (behind a proxy or a DNS name). The value must be `scheme://host[:port]` with no path. |
| `-gui` | `0` | After the HTTP server starts, open the wallet in the default browser with a one-time login token. Implies `-server=1` (soft set in `InitParameterInteraction`). It is a startup error with `-walletpwa=0`, or with no embedded bundle and no `-walletpwadir`. |

New RPC (category `util`): `getwalletpwaurl ( "base" )`.

- It mints a one-time token and returns `{"url": "<base>/wallet/#/login/<token>", "expires": <unix>}`.
- `base` defaults to `http://127.0.0.1:<rpcport>`.
- This is how a user logs in when the node runs as a service: `lotus-cli getwalletpwaurl` and open the result.
- The RPC errors if `-walletpwa=0`.

### 1.2 Routes

Every route is subject to the existing `-rpcallowip` check and is never served on `-publicbind` listeners. Both already hold, because both checks happen before dispatch.

| Method and path | Handler | Response |
|---|---|---|
| `GET /wallet` | walletpwa (exact) | `308 Location: /wallet/` |
| `GET /wallet/` | walletpwa | `index.html` |
| `GET /wallet/<path>` | walletpwa | The asset, or 404. There is no SPA fallback: the app uses hash routing. |
| `HEAD`, `PUT`, `OPTIONS` on `/wallet/*` | unchanged | Existing RPC handler behaviour (405) |
| `POST /wallet/<name>` | RPC (unchanged) | Multi-wallet JSON-RPC, now also accepting session auth |
| `POST /` | RPC (unchanged) | JSON-RPC, now also accepting session auth |
| `GET /auth/session` | walletpwa (exact) | Session status (§1.5) |
| `POST /auth/session` | walletpwa (exact) | Log in: token or password |
| `POST /auth/logout` | walletpwa (exact) | Log out |

The method split is wired into `StartHTTPRPC`, which is the only edit to `httprpc.cpp` routing:

```cpp
// in the "/" and "/wallet/" lambdas, before DelegateHTTPRequestAsync:
if (walletpwa::MaybeServeWalletPwa(req)) co_return true;   // GET under /wallet/ only
```

- `MaybeServeWalletPwa` returns true, after writing the reply, only for `GET` with a URI starting with `/wallet/`.
- If `!g_wallet_init_interface.HasWalletSupport()`, `StartHTTPRPC` still registers `"/wallet/"`, with a lambda that calls `MaybeServeWalletPwa` and otherwise replies 404. The node views then work with `-disablewallet`.
- `StartWalletPwa()` registers `/wallet` (exact), `/auth/session` (exact) and `/auth/logout` (exact). It is called from `AppInitServers` right after `StartHTTPRPC`; `StopWalletPwa()` runs from `StopHTTPRPC`'s caller.

Path rules for `<path>`:

- Strip the query string.
- Percent-decode once.
- Reject: empty segments, `.`/`..` segments, a backslash, NUL, a leading `/`, a total length over 256, and any segment starting with `.`.
- Map an empty path to `index.html`.

### 1.3 Assets: embedded bundle, development directory, headers

**Bundle format (the contract between `wallets/node-pwa` and the daemon), `node-pwa-bundle/1`:**

- A `.tar.gz` whose members all sit under `node-pwa/`.
- `node-pwa/BUNDLE.json` contains `{"format":1,"name":"node-pwa","version":"X.Y.Z","source_commit":"<40 hex>","files":{"<relpath>":{"sha256":"<hex>","size":N},...}}`.
- Every listed file is present.
- For each compressible type (`.html .js .mjs .css .json .webmanifest .svg .txt`), a `<relpath>.gz` is present too, made by the PWA packer (deterministic gzip, mtime 0). `.gz` files are not listed in `files`.
- No other members are allowed. Only regular files: no symlinks, no hard links, no devices.

**Embedding (CMake, in `src/walletpwa/CMakeLists.txt`):**

```cmake
set(WALLET_PWA_BUNDLE "" CACHE FILEPATH "Prebuilt node-pwa-*.tar.gz to embed (empty: none)")
set(WALLET_PWA_BUNDLE_SHA256 "" CACHE STRING "Required sha256 of WALLET_PWA_BUNDLE")
if(WALLET_PWA_BUNDLE)
  if(NOT WALLET_PWA_BUNDLE_SHA256 MATCHES "^[0-9a-f]{64}$")
    message(FATAL_ERROR "WALLET_PWA_BUNDLE_SHA256 must be 64 lowercase hex")
  endif()
  file(SHA256 "${WALLET_PWA_BUNDLE}" _h)
  if(NOT _h STREQUAL WALLET_PWA_BUNDLE_SHA256)
    message(FATAL_ERROR "WALLET_PWA_BUNDLE sha256 ${_h} != ${WALLET_PWA_BUNDLE_SHA256}")
  endif()
endif()
set(_gen "${CMAKE_CURRENT_BINARY_DIR}/wallet_pwa_bundle.cpp")
add_custom_command(OUTPUT "${_gen}"
  COMMAND "${Python_EXECUTABLE}" "${CMAKE_SOURCE_DIR}/contrib/devtools/embed_wallet_pwa.py"
          --bundle "${WALLET_PWA_BUNDLE}" --sha256 "${WALLET_PWA_BUNDLE_SHA256}" --out "${_gen}"
  DEPENDS "${CMAKE_SOURCE_DIR}/contrib/devtools/embed_wallet_pwa.py" ${WALLET_PWA_BUNDLE}
  VERBATIM)
add_library(walletpwa serve.cpp session.cpp http.cpp launch.cpp rpc.cpp "${_gen}")
target_link_libraries(walletpwa PUBLIC util univalue)
```

`src/CMakeLists.txt` gets `add_subdirectory(walletpwa)` and `target_link_libraries(server walletpwa)`.

`embed_wallet_pwa.py` (stdlib: `argparse, tarfile, gzip, hashlib, json`):

- With `--bundle ""`, it emits an empty table and an empty version string.
- Otherwise it:
  1. re-checks the sha256 (catches edits after configure);
  2. opens the tarball with `tarfile` and never extracts to disk;
  3. enforces the format rules above;
  4. checks each file's sha256 and size against `BUNDLE.json`;
  5. checks that each `.gz` decompresses to its file;
  6. caps the bundle at 32 MiB total.
- It emits members sorted by path, as `static constexpr unsigned char` arrays in hex. The output therefore depends only on the bundle bytes: no timestamps, no host paths. This keeps Guix builds reproducible.
- ETag is `"` + the first 32 hex characters of the file's sha256 + `"`. The gzip variant uses the same hash plus `-gz`.
- The daemon does no compression at build time, so the result doesn't depend on the zlib version.

**Serving rules (`ServeAsset`):**

- **Source.** With `-walletpwadir`, files are read from disk on every request:
  - The path is resolved with `fs::weakly_canonical`; it must stay under the canonical directory and be a regular file of at most 16 MiB.
  - No ETag, no gzip, `Cache-Control: no-store`.
  - Otherwise the embedded table is used.
- **No bundle and no dir.** `GET /wallet/` returns 404 with a fixed built-in HTML page: "This node was built without the wallet UI. Restart with -walletpwadir=<dir> or use a release build."
- **Encoding.** Use the gzip variant when it exists and `Accept-Encoding` lists `gzip` with q > 0. Then set `Content-Encoding: gzip`, which also stops `MaybeCompressZstd` from compressing again. Always set `Vary: Accept-Encoding`.
- **Conditional requests.** `If-None-Match` takes a comma list and `*`, with weak comparison. A match returns 304 with an empty body, the ETag and the cache headers.
- **Caching.** `Cache-Control: no-cache` on every embedded asset: revalidate every time (304 on loopback is cheap). There are no hashed filenames, so there is no immutable caching. The service worker gives offline use (§2.6).
- **MIME table:**

  | Extension | Content-Type |
  |---|---|
  | `.html` | `text/html; charset=utf-8` |
  | `.js`, `.mjs` | `text/javascript; charset=utf-8` |
  | `.css` | `text/css; charset=utf-8` |
  | `.json` | `application/json` |
  | `.webmanifest` | `application/manifest+json` |
  | `.svg` | `image/svg+xml` |
  | `.png` | `image/png` |
  | `.ico` | `image/x-icon` |
  | `.woff2` | `font/woff2` |
  | `.wasm` | `application/wasm` |
  | `.txt` | `text/plain; charset=utf-8` |
  | anything else | 404 |

- **Security headers on every `/wallet/*` response:**

  ```
  Content-Security-Policy: default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data: blob:;
      connect-src 'self'; manifest-src 'self'; worker-src 'self'; font-src 'self'; media-src 'self';
      form-action 'none'; frame-ancestors 'none'; base-uri 'none'
  X-Content-Type-Options: nosniff
  Referrer-Policy: no-referrer
  X-Frame-Options: DENY
  Cross-Origin-Opener-Policy: same-origin
  Cross-Origin-Resource-Policy: same-origin
  Permissions-Policy: camera=(self), microphone=(), geolocation=(), usb=(), hid=()
  ```

  Phase 3 QR scanning uses `camera`. WebHID, if added later, changes `hid=` in a later patch.

### 1.4 Small `httpserver` additions

These go on top of hand-off 0029. They are the only `httpserver.{h,cpp}` edits:

- `HTTPConnectionInfo` gets `bool tcp_peer_trusted`: `IsTrustedProxy(original TCP peer)`, set where 0029 resolves `client`. `HTTPRequestImpl` copies it in `DispatchRequest`.
- `std::string HTTPRequest::GetScheme() const`:
  - `"https"` if `IsTLS()`;
  - else, if `tcp_peer_trusted` and the right-most `X-Forwarded-Proto` value equals `https` (case-insensitive), `"https"`;
  - else `"http"`.

Everything else uses the existing API. `GetPeer()` is already the resolved client under 0029.

### 1.5 Browser authentication

**Login methods.** All three produce the same session.

1. **One-time token.** Minted by `-gui` or by `getwalletpwaurl`.
   - 32 random bytes from `GetStrongRandBytes`, as 64 hex characters.
   - Stored as `SHA256(token)` with an expiry of 120 s and the minting `authUser` (`__cookie__` for `-gui`; the caller's `authUser` for the RPC).
   - At most 16 outstanding; minting a new one evicts the oldest.
   - Single use. Compared in constant time against the stored hashes.
   - It travels in the URL fragment (`#/login/<token>`), so it never reaches the server in a request line, logs or `Referer`. The PWA POSTs it to `/auth/session`.
2. **Password.** The login form takes `user` and `password`: rpcuser/rpcpassword, an `-rpcauth` user, or the cookie file's `__cookie__:<hex>` (the form accepts the pasted cookie line and splits it at the first `:`).
   - Checked with the existing `RPCAuthorized` on the reconstructed `Basic` value. The function is reused and made non-static in `httprpc.{h,cpp}` as `bool CheckRPCCredentials(const std::string& user_colon_pass, std::string& authUser)`.
   - Failures sleep 250 ms, like RPC does.
3. Remote clients that are not browsers keep using `Authorization: Basic`, unchanged.

**`POST /auth/session` request rules:**

- Body: JSON `{"token":"…"}` or `{"user":"…","password":"…"}`, `Content-Type: application/json`, at most 4096 bytes.
- The request must pass the origin policy (below).
- If the request is not https (`GetScheme()`) and the client is not loopback (`!GetPeer().IsLocal()`), reply `403 {"error":"wallet sessions need HTTPS or a loopback connection"}`.

On success:

- Create a session:
  - 32 random bytes as the session id;
  - store `SHA256(id)` mapped to `{authUser, csrf (32 random bytes hex), created, last_used}`;
  - at most 64 sessions; evict the least recently used;
  - idle timeout 7 days, absolute 30 days;
  - kept in memory only, so a node restart logs everyone out.
- Reply `200` with:

  ```
  Set-Cookie: <name>=<id hex>; Path=/; HttpOnly; SameSite=Strict; Max-Age=2592000[; Secure]
  Cache-Control: no-store
  {"csrf":"<hex>","user":"<authUser>","expires":<unix>}
  ```

  - `Secure` is added when the scheme is https.
  - The cookie is named `nodewallet_<rpcport>`, so several nodes on one host don't collide (cookies are not port-scoped).
  - The `<rpcport>` in the name is the node's own `-rpcport`, not the Host port.

**Other `/auth/*` endpoints:**

- `GET /auth/session`, with a valid cookie and the origin policy satisfied (for GET, `Origin` may be absent, but `Host` must pass), returns `200 {"csrf","user","expires","pwa_version"}`. Otherwise it returns `401 {"error":"login required"}`. The PWA calls this on every load, so the CSRF token never needs storage. Cross-origin pages can't read the response because no CORS headers are sent.
- `POST /auth/logout` requires the cookie and CSRF and deletes the session. It replies 204 with `Set-Cookie: <name>=; Max-Age=0; Path=/`.

**Session auth on JSON-RPC (`POST /`, `POST /wallet/<name>`).** In `ProcessHTTPRequest[Async]`, where it now replies 401 for a missing `Authorization`:

```cpp
if (!authHeader.first) {
    if (auto user = walletpwa::AuthorizeWalletPwaSession(req)) { jreq.authUser = *user; /* continue as authorised */ }
    else { /* existing 401 path */ }
}
```

`AuthorizeWalletPwaSession` succeeds only if all of these hold:

- `-walletpwa=1`;
- the cookie maps to a live session (and `last_used` is updated);
- `Origin` is present and passes the origin policy;
- the header `X-CSRF-Token` equals the session's token (constant time);
- `Content-Type` is `application/json`.

On success the reply also carries `Cache-Control: no-store`. A request that has `Authorization` behaves exactly as today.

**Origin policy, the same for every `/auth/*` and session-authenticated request:**

1. `Host` must be:
   - a loopback literal (`127.0.0.0/8`, `[::1]`) or `localhost`, with any port. Any port allows `ssh -L` and other port forwards;
   - or the host:port of some `-walletpwaorigin`.

   Anything else is rejected. This is the DNS-rebinding defence.
2. When `Origin` is present (always for POST), it must equal `GetScheme() + "://" + Host`, after lower-casing and dropping a default port. With `-walletpwaorigin`, it must also be in that list or satisfy rule 1.

   Exact match means a page on `http://127.0.0.1:3000`, which is same-site, is refused for `:12604`.
3. Violations reply 403 and log at `BCLog::HTTP` debug level without values.

**Which RPCs a session may call.** Exactly what its `authUser` may call. `-rpcwhitelist` applies unchanged; `jreq.authUser` is set, so the existing whitelist code runs for singletons and batches. There is no separate allowlist:

- the console, which is phase 1, needs everything;
- bitcoin-qt's console also allows everything;
- operators who want a restricted browser user create an `-rpcauth` user with `-rpcwhitelist` and log in as that user.

`doc/wallet-pwa.md` documents this, including that `backupwallet`, `dumpwallet`, `importwallet` and `loadwallet` paths refer to the node's filesystem.

**Remote access over TLS.** Use the existing single port with TLS detection (`-tlscert`/`-tlskey`), `-rpcbind`, `-rpcallowip` and `-walletpwaorigin=https://name:port`.

- A generated, untrusted certificate works for RPC clients, but browsers won't register the service worker. The documentation therefore requires a browser-trusted certificate (ACME or an internal CA) or a TLS-terminating proxy.
- Plain-http sessions from non-loopback clients are refused (above).

**Behind `-trustedproxy`.**

- `GetPeer()` is the resolved client (0029), so the loopback test and `-rpcallowip` apply to the real client.
- `X-Forwarded-Proto` is believed only from a trusted TCP peer.
- The public name must be listed in `-walletpwaorigin`, because Host is the proxy's public name.
- The cookie gets `Secure` when the client-side scheme is https.
- The documentation's nginx example forwards `Host`, `X-Forwarded-For` and `X-Forwarded-Proto`.

**Never logged:** tokens, session ids, cookie values or CSRF tokens. Log lines name the `authUser` and the client address only.

### 1.6 `-gui`

Called right after `StartHTTPServer()` in `AppInitServers`, when `-gui`:

1. Mint a token for `__cookie__`, or for `-rpcuser` when a password is configured. The token stores the user name and never needs the password.
2. Build the URL `http://<host>:<rpcport>/wallet/#/login/<token>`:
   - `<host>` is `127.0.0.1`, unless every `-rpcbind` is non-loopback and not a wildcard. Then it is the first `-rpcbind` host, bracketed if IPv6.
   - Always http. The listener detects TLS and also serves plain HTTP, and loopback is a secure context.
3. Print `Wallet: <url>` to stdout, only when stdout is a TTY and not `-daemon`. Never write it to `debug.log`. Log `"Opening the wallet UI in the default browser"`.
4. Open the browser, without a shell:
   - **macOS:** `posix_spawnp` of `open <url>`.
   - **Linux and BSD:** `posix_spawnp` of `xdg-open <url>`, only if `DISPLAY` or `WAYLAND_DISPLAY` is set. Otherwise log "no desktop session; open the URL above or run `lotus-cli getwalletpwaurl`".
   - **Windows:** `ShellExecuteW(nullptr, L"open", wide_url, nullptr, nullptr, SW_SHOWNORMAL)`.
   - The child is not waited for synchronously: reap it with `waitpid(..., WNOHANG)` from a detached thread. A spawn failure is a log line, not a startup error.
5. The PWA shows the RPC warm-up message (`-28`) until the node is ready, which replaces Qt's splash screen.

`-gui` with `-daemon` works: the forked child opens the browser.

### 1.7 Threat model

- **Hostile website in the user's browser** (CSRF, cross-origin reads, DNS rebinding):
  - no CORS for session auth;
  - an exact `Origin` match and a `Host` allowlist;
  - a per-session CSRF header;
  - `SameSite=Strict` and `HttpOnly` cookies;
  - tokens only in URL fragments.
- **Other local web servers on 127.0.0.1** (same-site, different port):
  - `Origin` must equal the node's own origin;
  - a CSRF token they cannot read;
  - per-port cookie names.
- **Other local OS users.** They can reach the port, but logging in needs the 0600 cookie file, a password, or a token.
  - Accepted residual risk: the one-time token appears briefly in the `open`/`xdg-open` argv. It expires in 120 s and is consumed within about a second.
- **Network attackers on remote access.** Sessions are only created over TLS or loopback; `Secure` is set on https; forwarded headers are believed only from `-trustedproxy`.
- **Compromised PWA code** (XSS or a supply-chain attack) gets the session user's full RPC rights, the same as today's Qt console. Mitigations:
  - a strict CSP: no inline script, no `eval`, no remote origins;
  - two vendored, pinned runtime files and nothing fetched at runtime;
  - rendering only through htm's escaping templates, with a lint rule banning `innerHTML` (§2.8);
  - a pinned bundle sha256 in release builds;
  - an option for restricted `-rpcwhitelist` users.
- **Stolen session cookie:** HttpOnly, 7-day idle and 30-day absolute expiry, logout, and every node restart invalidates all sessions.
- **Malicious or compromised node:** out of scope. The node holds the keys.

### 1.8 Where the patches land (eCash tier)

Order inside the eCash tier:

```
… 0001–0028 (already in the stack: …, 6987165a5f public fallback, 40fc3cc8fa args, fe649023c3 doc)
… generic 0029–0034 (trusted proxy/health, test WS transport, async dials, TLS read, wakeup, doc)
… Lane 3 (metrics/logging), Lane 4 (client cert reload), Lane 7 (TLS identity): whatever has been integrated
→ E-PWA-1  http: serve the wallet PWA under /wallet/ with browser sessions and -gui
→ E-PWA-2  depends: pin the node PWA bundle and embed it in depends builds
```

**E-PWA-1** must come after 0029 (it uses the resolved client and `IsTrustedProxy`). Put it after all in-flight HTTP lanes, so it is the one that rebases, not them. Its `httpserver.cpp` diff is about 20 lines (§1.4), and its `httprpc.cpp` diff is about 40 lines (§1.2, §1.5). It is independent of W1.

**E-PWA-2:**

- Adds `depends/packages/wallet_pwa.mk`:
  - `$(package)_version=X.Y.Z`;
  - `$(package)_download_path=https://github.com/givelotus/lotus/releases/download/node-pwa-v$($(package)_version)`;
  - `$(package)_file_name=node-pwa-$($(package)_version).tar.gz`;
  - `$(package)_sha256_hash=…`;
  - `extract_cmds` verifies the hash and copies the file unchanged;
  - `stage_cmds` installs it to `$($(package)_staging_prefix_dir)/share/wallet-pwa/`.
- Adds `wallet_pwa_packages = wallet_pwa` in `packages.mk`, `NO_WALLET_PWA ?=` in `depends/Makefile` (included with the wallet packages), and a line in `depends/README.md`.
- `depends/toolchain.cmake.in` sets `WALLET_PWA_BUNDLE` and `WALLET_PWA_BUNDLE_SHA256` (CACHE) when that file exists. The sha256 is substituted from the recipe.

Guix builds go through depends, so they download the bundle outside the container with the normal sha256 check and embed it reproducibly. Bumping the PWA is a one-line, one-patch change.

Native release builds (monorepo `daemon/scripts/build.sh`) download the same URL, check the same sha256, and pass `-DWALLET_PWA_BUNDLE=… -DWALLET_PWA_BUNDLE_SHA256=…`. The pin is read from a new file, `daemon/wallet-pwa-version` (`version sha256`). This is a monorepo change, not a daemon patch.

### 1.9 Daemon tests

`src/test/walletpwa_tests.cpp`:

- **Paths:** traversal (`..`, `%2e%2e`, `%2f`, backslash, NUL, dot-files) is rejected; an empty path maps to `index.html`.
- **ETag:** `If-None-Match` with lists, weak tags and `*`.
- **Encoding:** gzip q=0 versus q=1, a missing `.gz`, `Vary`.
- **MIME table** and a 404 for unknown extensions.
- **Origin/Host matrix:**
  - accepted: loopback with any port, `localhost`, `[::1]`, configured origins;
  - rejected: a rebinding Host `evil.example:12604`, an Origin scheme mismatch, a different port between Origin and Host, a missing Origin on POST.
- **Tokens:** single use, expiry under `SetMockTime`, eviction at 16.
- **Sessions:** idle and absolute expiry, least-recently-used eviction at 64, CSRF mismatch.
- **Cookies:** parsing of several cookies and a per-port name.

`test/functional/interface_wallet_pwa.py` uses raw `http.client`, with no browser:

- Start with `-walletpwadir=<tmp>` containing `index.html` and `a.js`:
  - GET `/wallet` → 308;
  - `/wallet/` → 200 with CSP and `no-store`;
  - live edits show up without a restart;
  - `/wallet/../x` → 404.
- POST `/auth/session` with a bad password → 401 after the delay; with `__cookie__` from the cookie file → 200, a cookie and CSRF.
- RPC `getblockcount` via the cookie:
  - succeeds with `Origin` and CSRF;
  - fails (401) without CSRF, with a foreign Origin, or with `Host: evil.example`.
- `getwalletpwaurl` token: works once, the second use → 401, and it expires under mocktime.
- `-rpcwhitelist` is enforced for a session user (singleton and batch).
- `-walletpwa=0` → 404; `-gui` with `-walletpwa=0` → init error.
- With `-trustedproxy=127.0.0.1`:
  - `X-Forwarded-Proto: https` gives `Secure` on the cookie;
  - the same header from an untrusted peer is ignored.
- A non-loopback http session is refused. Simulated with `-trustedproxy` and `X-Forwarded-For: 203.0.113.9` without `X-Forwarded-Proto` → 403.
- A `-publicbind` listener → 404 for `/wallet/`.
- An embedded-bundle test runs only when the build has a bundle: `EmbeddedBundleVersion()` is exposed in `getwalletpwaurl`'s result as `"pwa_version"` and the test skips if it is empty. It checks `Content-Encoding: gzip`, the ETag and a 304.

`test_embed_wallet_pwa.py`:

- the generator is deterministic (same output twice from the same tarball, even with shuffled member order and mtimes);
- it rejects symlinks, `..`, unlisted files, a hash mismatch and a bad `.gz`;
- an empty bundle produces an empty table.

---

## 2. The app: `wallets/node-pwa/` (monorepo)

### 2.1 Technology (minimal, and why)

- **Plain ES2022 modules with no build step.** `src/` is exactly what the browser runs. Development is `lotusd -regtest -walletpwadir=$PWD/wallets/node-pwa/src` and a reload, matching the decision that the daemon never builds the UI.
- **Runtime dependencies: two vendored files, nothing from npm at runtime.**
  - `src/vendor/htm-preact-standalone.mjs` (htm 3.1.1 `preact/standalone.module.js`, MIT). It provides components, hooks and auto-escaping tagged templates without JSX or a compiler. Plain DOM code for ~20 screens would be larger and more bug-prone; React would need a build.
  - `src/vendor/qrcodegen.mjs` (nayuki QR Code generator 1.8.0, MIT): QR to SVG.
  - `src/vendor/VENDOR.json` records the upstream URL, version, license and sha256 of each file. A unit test checks those hashes.
- **Dev dependencies only:** `@playwright/test` (pinned exact version in `package-lock.json`) for the smoke test. Unit tests use Node's built-in `node --test` (Node ≥ 20). There is no lint toolchain beyond `node --check` and a small custom lint (§2.8).
- **Types:** JSDoc comments only, with no TypeScript compiler.
- **No CSS framework:** one `app.css` with CSS custom properties, light and dark via `prefers-color-scheme`, and tabular numerals for amounts.

### 2.2 Layout

```
wallets/node-pwa/
  README.md                 dev loop, pack, test, release
  package.json              scripts: test, lint, pack, smoke; "private": true
  package-lock.json
  src/
    index.html              <link rel=manifest>, <script type=module src=main.js>, no inline script/style
    app.css
    main.js                 boot: session → profile → router → poller
    sw.js                   service worker (§2.6)
    manifest.webmanifest
    icons/icon.svg icon-192.png icon-512.png maskable-512.png
    vendor/…                (§2.1)
    lib/
      rpc.js                JSON-RPC client (§2.3)
      json.js               lossless JSON parse (Decimal for non-safe numbers)
      session.js            /auth/* calls, login/logout, 401 handling
      poller.js             refresh loop + waitfornewblock long-poll (§2.4)
      profile.js            network/profile detection (§2.5)
      amount.js             BigInt fixed-point parse/format from getcurrencyinfo
      xpiaddr.js            xpi1 encode/decode per xpiaddr.md
      uri.js                ecash:/xpi: BIP21 parse/build
      consoleparse.js       console command-line parser
      store.js              tiny observable app state (no library)
      storage.js            localStorage/IndexedDB wrappers (try/catch, per-origin)
      csv.js                CSV export
    ui/                     shared components: Layout, Sidebar, StatusBar, Modal, AmountInput, AddressInput, Table, Toast, QR
    views/                  one module per screen: overview, send, receive, transactions, txdetail,
                            peers, console, nodeinfo, wallets, login, offline
  test/
    unit/*.test.js          node --test
    smoke/smoke.spec.js     Playwright against a regtest node
    fixtures/xpiaddr_v2_vectors.json   copied from the daemon's vector file
  tools/
    pack.mjs                deterministic bundle (§2.7)
    lint.mjs                bans innerHTML/insertAdjacentHTML/eval/new Function/inline handlers
```

Routing is hash-based (`#/overview`, `#/send`, `#/receive`, `#/transactions`, `#/tx/<txid>`, `#/peers`, `#/console`, `#/node`, `#/wallets`, `#/login[/<token>]`). The selected wallet is a query on the hash (`?w=<name>`) and is remembered in localStorage.

Layout: left sidebar navigation; top bar with the wallet picker, lock state, mask-values toggle (phase 2) and network badge; main pane; bottom status bar with sync progress, connection count, a network-active toggle and the node version.

### 2.3 RPC client

- **`rpc.call(method, params = [], {wallet, signal, timeoutMs = 60000})`:**
  - POSTs `{"jsonrpc":"1.0","id":n,"method","params"}` to `/` (no wallet) or `/wallet/${encodeURIComponent(name)}`;
  - headers `Content-Type: application/json` and `X-CSRF-Token`;
  - `credentials: 'same-origin'`;
  - `AbortController` timeout.
- **`rpc.batch(calls, {wallet})`:** one POST with an array. Results come back in input order, matched by `id`. Per-call errors return as `RpcError` objects without throwing the whole batch.
- **Errors:**
  - HTTP 401 → `session.expired()` → login view, keeping the current route for after login;
  - HTTP 403 → "not permitted for this user" (whitelist);
  - network failure → `store.node = 'offline'`, exponential backoff 1 s → 30 s, offline banner;
  - JSON-RPC `-28` → warm-up screen showing the message;
  - `-18`/`-19` (wallet not found or not specified) → wallet picker.
- **Parsing.** Responses go through `json.js`: integers within ±2^53 stay `Number`; every other number becomes `Decimal`, a string wrapper with `toString()` and `valueOf()`. Amounts are therefore never rounded.
- **Amounts sent** are decimal strings produced by `amount.js` (`AmountFromValue` accepts strings).
- **No secrets in JS.** The session cookie is HttpOnly; the CSRF token lives only in memory and is re-fetched by `GET /auth/session` on load.

### 2.4 Refresh and notifications

Phase 1 uses polling plus a long-poll; there is no new daemon endpoint.

- **Tick.** One batch to `/wallet/<sel>`, or to `/` with no wallet, every 5 s while `document.visibilityState === 'visible'` and every 30 s otherwise:
  - `getblockchaininfo`, `getnetworkinfo`, `getbalances`, `getwalletinfo`;
  - plus `getmempoolinfo` and `getnettotals` while their views are open.
  - `listtransactions "*" 50` is added only when `getwalletinfo.txcount` or the best block hash changed, or when unconfirmed transactions are shown.
- **Long-poll.** A separate loop calls `waitfornewblock 30000` and triggers an immediate tick when it returns a new hash. Its RPC timeout is 40 s, and it is restarted after errors with backoff.
- **No overlap.** Ticks don't overlap: a tick in flight suppresses the next.
- **Later.** A WebSocket event stream (`/wallet-events`, cookie-authenticated, fed by wallet notifications after W1) is a later, separate daemon patch. `poller.js` exposes `onChange(topic)` so it can be swapped in without touching views.

### 2.5 Network and profile detection

On login and after each reconnect:

1. `getblockchaininfo.chain` gives `main | test | regtest`.
2. `getcurrencyinfo` gives `ticker` and `decimals`, used everywhere. Nothing is hard-coded.
3. `getblockheader <bestblockhash> false`: header hex length 160 (80 bytes) → profile `ecash`; 268 (134 bytes) → profile `lotus-v2`; anything else → `generic`, which behaves like `ecash` for addresses.
4. Address format:
   - `ecash`: cashaddr, validated only by `validateaddress` (debounced 300 ms).
   - `lotus-v2`: encode a probe address for the chain's hrp (`xpi`/`txpi`/`rxpi`, root = 32 zero bytes) with `xpiaddr.js` and call `validateaddress` on it. `isvalid: true` → format `xpi`; otherwise `cashaddr` (a node from before L4).
5. Under the `xpi` format:
   - client-side decoding with the spec's exact rejection reasons gives instant typo feedback;
   - `wrong network` is reported when the hrp differs from the chain;
   - `validateaddress` remains authoritative.

What the profile switches on (V2 views):

- **Address and URI handling:** under `xpi`, QR codes are `XPI:` plus the uppercase address when there are no parameters, otherwise the lowercase `xpi:` URI. Cashaddr addresses already carry their prefix.
- **Header fields in Node info:** 134-byte V2 header fields, shown as whatever `getblockheader` returns.
- **Labels:** product name taken from `getnetworkinfo.subversion`.
- **Later V2-only views:** tokens and 3-branch outputs (phase 3).

### 2.6 Service worker and installability

- **Manifest:**
  - `id` `/wallet/`, `start_url` `/wallet/`, `scope` `/wallet/`;
  - `display` `standalone`;
  - `name` "Node Wallet", `short_name` "Wallet";
  - icons any and maskable;
  - `theme_color`/`background_color` from the CSS palette.

  It is chain-neutral because the same bundle serves eCash and Lotus. The window title shows `<client> · <chain>` at runtime. Each node origin (host:port) is a separate installable app with separate storage.
- **`sw.js`** is registered at `/wallet/sw.js` (default scope `/wallet/`). Its cache is `node-pwa-<version>`; the version is a constant written into `sw.js` by `pack.mjs`, or `dev` in `src/`.
  - On `install` it fetches `/wallet/BUNDLE.json` and precaches every listed file. In dev, it precaches the files listed in `PRECACHE` in `sw.js`.
  - The `fetch` handler only intercepts same-origin `GET` under `/wallet/`. It never touches `POST`, `/auth/*` or `/`.
  - Strategy: network first with a 3 s timeout, falling back to the cache. Successful responses update the cache.
  - The result: the shell opens when the node is down and shows the offline view with auto-reconnect.
  - On activate it deletes old caches. A new SW waits; the app shows "Update available, reload", then `postMessage('skipWaiting')`.
- **Install button:** the app listens for `beforeinstallprompt` and shows "Install app" in the sidebar. On Safari it shows a hint instead.

### 2.7 Packaging and release

- `npm run pack` runs `tools/pack.mjs` (Node stdlib only). It writes `dist/node-pwa-<version>.tar.gz`:
  - all files of `src/` except tests, plus generated `BUNDLE.json` and `.gz` siblings;
  - members sorted, `mtime=SOURCE_DATE_EPOCH` (default 0), uid/gid 0, mode 0644, ustar written by the script;
  - gzip via `zlib.gzipSync` with level 9 and mtime 0.
  - `version` comes from `package.json`; `source_commit` from `git rev-parse HEAD`.
- Monorepo CI (`.github/workflows/node-pwa.yml`):
  - `npm ci`, `npm test`, `npm run lint`;
  - pack twice and compare the sha256;
  - upload the artifact;
  - on tag `node-pwa-vX.Y.Z`, publish the tarball and its sha256 as a release asset.
  - The daemon pin (E-PWA-2 and `daemon/wallet-pwa-version`) is then bumped by hand.

### 2.8 Tests

- **Unit tests** (`node --test test/unit`):
  - `amount` round trips, rounding refusal and more than `decimals` digits;
  - `xpiaddr` against every valid and invalid vector, checking the exact reasons;
  - `uri` parsing and building for `ecash:` and `xpi:`;
  - the `json` lossless parser;
  - `consoleparse` (quoting, nested `cmd(arg)` and `[index]` as in Qt's `RPCParseCommandLine`, the JSON-or-string argument rule);
  - `rpc` batching and error mapping with a mocked `fetch`;
  - the `poller` no-overlap rule and backoff (fake timers);
  - `profile` detection from fixture RPC answers;
  - the vendored-file hashes.
- **Lint** (`tools/lint.mjs`): fail on `innerHTML`, `outerHTML`, `insertAdjacentHTML`, `document.write`, `eval`, `new Function`, `on*=` attributes in `index.html`, and any `http(s)://` URL in `src/` outside `vendor/` comments.
- **Smoke test** (`npm run smoke`, Playwright Chromium, headless):
  - `LOTUSD=/path/to/lotusd` (and `LOTUS_CLI`) are required; the test skips with a message if they are unset;
  - starts a fresh regtest datadir with `-walletpwadir=src` on free ports, and also runs against the packed bundle extracted to a temp dir;
  - gets a URL from `lotus-cli getwalletpwaurl` and opens it.
  - It asserts:
    1. the login succeeds and the hash token is cleared from the URL;
    2. the empty-wallet prompt appears; creating wallet `w1` through the UI works;
    3. in the console, `generatetoaddress 101 <getnewaddress>` (the address comes from the Receive view) runs and the overview shows a mature balance;
    4. Send to a second new address with "subtract fee" gives a txid, and the transaction appears in Transactions and in the details modal;
    5. Peers renders an empty table, and `setnetworkactive` toggles the status bar;
    6. the console shows `help` output and history works;
    7. after the node stops, a reload shows the offline shell (served by the SW), and after a restart it reconnects and goes to the login screen (sessions don't survive restarts).
  - CI runs the smoke test in the daemon release workflow, where a `lotusd` artifact exists. It runs locally per the README.

### 2.9 bitcoin-qt parity checklist

**Phase definitions:**

- **Phase 1:** the minimal app. It ships with E-PWA-1.
- **Phase 2:** the rest of everyday parity.
- **Phase 3:** remaining items, browser-native replacements, and items explicitly not ported.
- **Parity, the criterion for deleting Qt from the eCash tier,** is all of the following:
  - every row marked P1, P2, or P3-required is done;
  - every row marked "not ported" has its replacement documented in `doc/wallet-pwa.md`.

| bitcoin-qt (file) | PWA | Phase | RPCs |
|---|---|---|---|
| Overview: balances, recent transactions (`overviewpage`) | Overview | P1 | `getbalances` (incl. watch-only), `listtransactions "*" 10` |
| Send (`sendcoinsdialog`, `sendcoinsentry`): several recipients, label, amount, subtract fee, clear, confirm | Send | P1 | `validateaddress`, `walletcreatefundedpsbt` (fee preview only, if it errors show "fee calculated when sent"), `sendmany`, `gettransaction` for the actual fee |
| Send: unlock prompt (`askpassphrasedialog`, unlock mode) | Modal before send | P1 | `walletpassphrase <p> 60`, `walletlock` after |
| Send: paste or open a payment URI | Send field accepts URIs | P1 | — (`uri.js`) |
| Send: fee options (custom fee) | Send "fee rate" field | P2 | `settxfee`, `estimatefee`, `sendmany` options |
| Coin control (`coincontroldialog`) | Send → Inputs drawer | P2 | `listunspent`, `lockunspent`, `listlockunspent`, `send` with `inputs`/`change_address` |
| Receive form and history (`receivecoinsdialog`, `recentrequeststablemodel`) | Receive | P1 | `getnewaddress <label>`; request history in IndexedDB per origin and wallet; `listreceivedbyaddress 0 true` |
| Payment request with QR, copy URI/address, save image (`receiverequestdialog`, `qrimagewidget`) | Receive modal | P1 | — (qrcodegen SVG, download SVG/PNG) |
| Transactions list, filters, search (`transactionview`) | Transactions | P1 | `listtransactions "*" 100 <skip> true`, paged |
| Transaction details (`transactiondescdialog`) | Tx modal | P1 | `gettransaction <txid> true true` |
| Abandon transaction (context menu) | Tx modal action | P1 | `abandontransaction` |
| Export CSV (`csvmodelwriter`) | Transactions → Export | P2 | — (`csv.js` blob download) |
| Edit label (context menu, `editaddressdialog`) | Tx modal and address book | P2 | `setlabel` |
| Bump fee | not ported: ABC has no RBF | — | — |
| Sending/receiving address books (`addressbookpage`, `addresstablemodel`) | Address book view | P2 | `listlabels`, `getaddressesbylabel`, `setlabel`, `getaddressinfo` |
| Debug window → Information (`debugwindow`, `clientmodel`) | Node view | P1 | `getnetworkinfo`, `getblockchaininfo`, `getmempoolinfo`, `uptime`, `getmemoryinfo`; datadir shown via `getrpcinfo.logpath` |
| Debug window → Console (`rpcconsole`) | Console | P1 | Any RPC; wallet selector; history (localStorage, 100 entries); clear; font size; Qt's warning banner about scams |
| Debug window → Network traffic (`trafficgraphwidget`) | Node view graph (canvas) | P2 | `getnettotals` |
| Debug window → Peers, banned peers (`peertablemodel`, `bantablemodel`) | Peers | P1 | `getpeerinfo`, `listbanned`, `disconnectnode`, `setban add` (1 h/1 d/1 w/1 y), `setban remove`, `clearbanned` |
| Status bar: sync progress, connections, network active (`bitcoingui`, `modaloverlay`) | Status bar and sync overlay | P1 | `getblockchaininfo`, `getnetworkinfo`, `setnetworkactive` |
| Status bar: HD and encryption icons | Top bar badges | P1 | `getwalletinfo` |
| File → Create/Open/Close wallet (`createwalletdialog`, `walletcontroller`) | Wallets view and picker | P1 | `createwallet` (name, encrypt passphrase, disable private keys, blank, descriptors), `listwalletdir`, `loadwallet`, `unloadwallet`, `listwallets` |
| File → Close all wallets | Wallets view | P2 | `unloadwallet` × n |
| File → Backup wallet | Wallets view, path on the node host | P2 | `backupwallet <path>`, with a warning that the path is on the node's filesystem |
| File → Sign/Verify message (`signverifymessagedialog`) | Sign/Verify view | P2 | `signmessage`, `verifymessage` |
| File → Load PSBT | PSBT view (paste or upload base64) | P2 | `decodepsbt`, `analyzepsbt`, `walletprocesspsbt`, `finalizepsbt`, `sendrawtransaction` |
| File → Open URI (`openuridialog`) | Send view field | P1 | — |
| Settings → Encrypt wallet, change passphrase (`askpassphrasedialog`) | Wallets view | P2 | `encryptwallet`, `walletpassphrasechange` |
| Settings → Mask values | Top bar toggle (Ctrl+Shift+M) | P2 | — |
| Settings → Options: display unit (`bitcoinunits`) | Settings: ticker or base units | P2 | `getcurrencyinfo` |
| Options: third-party transaction URLs | Settings, local per origin | P3-required | — |
| Options: language (translations) | i18n with English only | P3 | — |
| Options: coin control on/off, spend unconfirmed change | Settings (local; the latter via `-spendzeroconfchange`) | P3-required (coin control toggle only) | — |
| Options: prune, dbcache, script threads, proxy, Tor, NAT-PMP, listen, "reset options", "open config file" | not ported: read-only display of current values in Node view (`getnetworkinfo` proxies and local addresses); changes via `lotusd.conf` (documented) | P3-required (read-only display) | `getnetworkinfo`, `getblockchaininfo.pruned` |
| Options: start on login, tray, minimize on close (`Window` tab) | not ported: OS or browser features (install app; service managers) | — | — |
| Intro/datadir chooser (`intro`), splash (`splashscreen`) | not ported: the node is already running; `-gui` plus the warm-up screen replace the splash | — | — |
| Notifications for incoming transactions (`notificator`, DBus) | Web Notifications on new incoming wallet transactions (from the poller) | P2 | — |
| Help → About, command-line options (`utilitydialog`, `helpmessagedialog`) | About view | P3-required | `getnetworkinfo`; `help` |
| File → Exit | "Stop node" with confirmation | P2 | `stop` |
| BIP70 payment requests (`paymentserver`, `paymentrequestplus`) | not ported: deprecated; plain URIs only | — | — |
| URI protocol handler (`paymentserver`) | `protocol_handlers` in the manifest for `web+xpi`/`web+ecash` (the bare schemes cannot be registered by web apps) | P3 | — |
| QR scan (not in Qt) | Camera scan via `BarcodeDetector` where available | P3 | — |
| Lotus V2 tokens and 3-branch outputs | V2-only view | P3 (needs V2 wallet RPCs that don't exist yet) | — |
| Hardware wallets (WebHID), WebGPU miner | Out of scope for parity; later, separate design | — | — |

---

## 3. Qt removal (Q1) in the V2 tier

### 3.1 Placement and order

- **Q1** is one patch, `build(v2): remove bitcoin-qt`.
- It goes at the V2 tip: after the existing V2 patches and the identity patches L1–L3, and **before L4** (xpi addresses through the node, which currently lists "Qt if built") and **L5** (cashaddr removal, which counts 19 Qt users).
- With Q1 first, L4 and L5 never touch `src/qt`.
- Q1 doesn't depend on E-PWA-1. The V2 tier may lose Qt before the PWA is complete, by user decision.
- Putting Q1 at the tip, rather than at the start of the V2 tier, avoids context conflicts with `v2/033` (`99c26c1c71`), which edits the `depends/Makefile` and `packages.mk` lines next to the Qt ones.

### 3.2 Exact changes

**Delete:**

- `src/qt/` (all 355 files).
- `share/qt/` (`Info.plist.cmake.in`, `extract_strings_qt.py`).
- `cmake/modules/FindQREncode.cmake`, `cmake/utils/translate.sh.in`.
- `contrib/qt/convert-prl-libs-to-cmake.pl`, `contrib/bitcoin-qt.pro`.
- `contrib/macdeploy/macdeployqtplus.py`, `contrib/macdeploy/detached-sig-apply.sh`, `contrib/macdeploy/detached-sig-create.sh`. Keep `extract-osx-sdk.sh`, `gen-sdk`, `LICENSE` and an edited `README.md`, because depends' macOS SDK flow uses them.
- `contrib/debian/bitcoin-qt.desktop`, `.install`, `.lintian-overrides`, `.manpages`, `.protocol`; `contrib/aur/bitcoin-abc-qt/`.
- `.tx/config`, `contrib/devtools/update-translations.py`, `doc/translation_process.md`, `doc/translation_strings_policy.md`.
- `arcanist/linter/Qt5Linter.php`.
- **depends recipes (15):** `qt.mk`, `qrencode.mk`, `expat.mk`, `fontconfig.mk`, `freetype.mk`, `libXau.mk`, `libxcb.mk`, `libxcb_util.mk`, `libxcb_util_image.mk`, `libxcb_util_keysyms.mk`, `libxcb_util_render.mk`, `libxcb_util_wm.mk`, `libxkbcommon.mk`, `xcb_proto.mk`, `xproto.mk`. Patch directories: `depends/patches/qt/`, `depends/patches/qrencode/`, `depends/patches/freetype/` (15 files together).
- **Keep:** `cpython.mk`, `native_cpython.mk` (Chronik plugins), `protobuf.mk`, `native_protobuf.mk` (Chronik), and `share/pixmaps/` (NSIS installer images).

**Edit:**

- `src/CMakeLists.txt`:
  - drop `QT` from the `deprecate_build_flag` loop;
  - remove `option(BUILD_QT …)`, `option(ENABLE_BIP70 …)`, `option(ENABLE_QRCODE …)`, `ENABLE_DBUS_NOTIFICATIONS` and its default block;
  - remove `-DBUILD_QT=OFF`, `-DENABLE_QRCODE=OFF` and `-DENABLE_BIP70=OFF` from `native_add_cmake_flags`;
  - remove the `if(BUILD_QT) add_subdirectory(qt) endif()` block.

  Passing `-DBUILD_QT=OFF` afterwards only produces CMake's "unused variable" warning, so the monorepo's `daemon/scripts/build.sh`, `components.json` and `guix-daemon.yml` keep working unchanged. Clean them up in a separate monorepo commit.
- `src/config/CMakeLists.txt`: remove the `USE_QRCODE` and `USE_DBUS` blocks.
- `src/config/bitcoin-config.h.cmake.in`: remove `ENABLE_BIP70`, `USE_QRCODE`, `USE_DBUS`.
- `depends/packages/packages.mk`: remove `qrencode_packages`, `qt_linux_packages`, `qt_darwin_packages`, `qt_mingw32_packages`.
- `depends/Makefile`: remove `NO_QT ?=`, `NO_QR ?=`, the `qrencode_packages_`/`qt_packages_` lines, and `$(qt_packages_)` from `packages +=`.
- `depends/README.md`: remove the `NO_QT`/`NO_QR` entries and the Qt build-dependency text.
- `contrib/guix/libexec/build.sh`:
  - remove `-DBUILD_QT=OFF -DENABLE_QRCODE=OFF -DENABLE_BIP70=OFF` from the source-package configure;
  - in the darwin case, replace the `osx-deploydir`/`osx_volname`/`unsigned-app`/`osx-zip` steps and the `.app` `find … bitcoin-qt` move with the plain `cmake --install` tarball, as the linux case does;
  - pass `NO_QT=1 NO_QR=1` nowhere (they no longer exist).

  The Lotus monorepo overlay `daemon/candidates/guix/000-lotus-guix-linux.patch` passes `NO_QT=1 NO_QR=1` to make; unknown make variables are harmless.
- `contrib/guix/libexec/codesign.sh`: remove the darwin `signapple apply dist/Bitcoin-Qt.app` branch. Darwin codesigning of a GUI app no longer applies; it should report "no macOS app to sign".
- `contrib/guix/symbol-check.py`: remove the `bitcoin-qt`-only allowances (xkb `V` version and the bitcoin-qt-only library lists); comment "bitcoind and bitcoin-qt" becomes "lotusd".
- `contrib/guix/README.md`, `contrib/README.md`, `contrib/macdeploy/README.md`: remove the Qt and app-bundle text.
- `PackageOptions.cmake`: remove `_nsis_bitcoin_qt`, `CPACK_NSIS_MUI_FINISHPAGE_RUN`, `CPACK_NSIS_INSTALLED_ICON_NAME`, the `CPACK_NSIS_MENU_LINKS` entry and the `CREATE/DELETE_ICONS_EXTRA` entries that name the Qt executable. `cmake/modules/NSIS.template.in`: remove `BITCOIN_GUI_NAME` and its uses.
- `contrib/CMakeLists.txt`: drop `"bitcoin-qt.pro"`.
- `contrib/debian/control`, `rules`, `README.md`, `copyright`: drop the `bitcoin-qt` package stanza and its references.
- `contrib/teamcity/build-configurations.yml`: remove `install-test-suite-bitcoin-qt` and the `build-without-qt` config (now the only build). `contrib/teamcity/run-tests-windows.ps1`: remove the Qt test invocation. `contrib/utils/install-dependencies-bookworm.sh`: remove the Qt, qrencode and X11 development packages.
- `.arclint` and `arcanist/__phutil_library_map__.php`: remove the Qt5 linter.
- `test/functional/test_framework/test_framework.py`: remove the `BUILDDIR/qt` `PATH` entry (around line 352).
- `test/lint/lint-circular-dependencies.sh`: remove the four `qt/…` expected cycles.
- `test/sanitizer_suppressions/lsan`: remove `leak:libQt5Widgets`. `test/sanitizer_suppressions/tsan`: remove `race:bitcoin-qt` and the three `src/qt/test/*` entries.
- **Comments only:** `src/bitcoind.cpp:148`, `src/clientversion.cpp:16`, `src/coins.h:623` and `src/node/README.md` stop mentioning bitcoin-qt.
- **Docs:** `doc/build-osx.md`, `doc/build-unix.md`, `doc/dependencies.md`, `doc/README.md`, `doc/README_windows.txt`, `doc/developer-notes.md`, `doc/files.md`, `doc/bitcoin-conf.md`, `doc/functional-tests.md`, `doc/unit-tests.md`, `doc/release-process.md`, `doc/man/README.md`, `doc/man/gen-manpages.sh`, `doc/JSON-RPC-interface.md`, `doc/doxygen/Doxyfile.cmake.in`: remove Qt instructions. Point to `doc/wallet-pwa.md` once E-PWA-1 is below in the stack; until then say "use `-walletpwadir` or `lotus-cli`". Historical `doc/release-notes/*` stays.
- **Kept deliberately** (separate cleanups if ever wanted):
  - `src/interfaces/node.h` and the related node, wallet and chain interfaces, which are also used by the wallet and tests;
  - `node/ui_interface`;
  - Electrum ABC's own Qt in `electrum/` (untouched monorepo component);
  - `share/rpcauth`.

**Validation for Q1:**

- configure and build the full tree with no Qt, qrencode or X11 installed;
- `grep -rI -E 'BUILD_QT|USE_QRCODE|ENABLE_BIP70|USE_DBUS|src/qt' src cmake CMakeLists.txt depends contrib/guix test` must be empty (excluding release notes);
- `ninja check` and the functional suite give the same results as before Q1 (the known `logargs` `/private` issue aside);
- `make -C depends NO_WALLET=… download` lists no removed package;
- the circular-dependency lint passes.

### 3.3 Later Qt removal from the eCash tier (criteria)

Delete Qt from the eCash tier, with the same patch content re-based onto that tier, only when all of these hold:

1. Every P1, P2 and P3-required row in §2.9 is implemented, and every "not ported" row is documented in `doc/wallet-pwa.md`.
2. The smoke test (§2.8) is extended to the P2 flows (coin control, encrypt/unlock, sign/verify, PSBT, address book, backup) and passes against an eCash-tier build. It runs in CI for at least one tagged eCash-tier release that embeds the bundle through E-PWA-2.
3. Guix builds of that eCash-tier release are reproducible with the bundle embedded.
4. No open bug against the PWA is marked as blocking parity.
5. The user signs off explicitly.

When those hold, the eCash-tier Qt deletion goes after E-PWA-2. V2's Q1 then shrinks to nothing on rebase and is dropped.

---

## 4. Patch-by-patch plan

| # | Tier / location | Title | Files | Depends on |
|---|---|---|---|---|
| E-PWA-1 | eCash, after hand-off 0029–0034 and any integrated Lane 3/4/7 HTTP patches | `http: serve the wallet PWA under /wallet/ with browser sessions and -gui` | new `src/walletpwa/*`, `contrib/devtools/embed_wallet_pwa.py` and its test, `contrib/devtools/CMakeLists.txt`, `src/CMakeLists.txt` (subdirectory and link), `src/httpserver.{h,cpp}` (§1.4), `src/httprpc.{h,cpp}` (§1.2, §1.5), `src/init.cpp` (arguments, `-gui` interaction, `StartWalletPwa`, launch), `src/rpc/register.h` (register `getwalletpwaurl`), `src/test/walletpwa_tests.cpp` and test `CMakeLists.txt`, `test/functional/interface_wallet_pwa.py` and test-runner list, `doc/wallet-pwa.md` | 0029 |
| E-PWA-2 | eCash, right after E-PWA-1 | `depends: pin the node PWA bundle and embed it in depends builds` | `depends/packages/wallet_pwa.mk`, `depends/packages/packages.mk`, `depends/Makefile`, `depends/README.md`, `depends/toolchain.cmake.in` | E-PWA-1, a published `node-pwa-v0.1.0` |
| Q1 | V2, at the V2 tip, after L1–L3 and before L4/L5 | `build(v2): remove bitcoin-qt` | §3.2 | — (independent of E-PWA) |
| M-1 | monorepo `~/repos/lotus` | `wallets/node-pwa: phase 1 app` | `wallets/node-pwa/**`, `.github/workflows/node-pwa.yml` | E-PWA-1, to run against |
| M-2 | monorepo | `daemon: embed the pinned node PWA in native release builds` | `daemon/wallet-pwa-version`, `daemon/scripts/build.sh`; clean up stale `-DBUILD_QT=OFF` in `components.json`, `guix-daemon.yml` and `build.sh` (V2 only) | E-PWA-1, a published bundle |
| M-3… | monorepo | Phase 2, then phase 3 rows of §2.9, one view per commit | `wallets/node-pwa/**` | M-1 |
| later | eCash | `wallet: stream wallet events over WebSocket` (optional; replaces polling) | `src/walletpwa/events.cpp` | W1, E-PWA-1 |
| later | eCash | Qt removal (§3.3) | as §3.2 on the eCash tier | parity |

Release order: E-PWA-1 → M-1 → tag `node-pwa-v0.1.0` → E-PWA-2 and M-2. Q1 can land at any time.

## 5. Open questions (few, explicit)

1. **Bundle hosting URL.** E-PWA-2 assumes GitHub release assets on `givelotus/lotus` with tag `node-pwa-vX.Y.Z`. Confirm, or name another host.
2. **Session lifetime** (7 days idle, 30 days absolute, in memory only, so a node restart logs everyone out). Confirm, or ask for persisted sessions (a 0600 file in the datadir holding only session hashes).

## Decisions (user, 2026-10-20)

1. Bundle hosting: GitHub releases of the monorepo, pinned by sha256. No
   release is to be made yet.
2. Sessions are in memory only: a node restart logs the browser out. The PWA
   keeps no wallet state of its own; the node holds everything. Browser
   storage is used only for per-browser conveniences (console history, theme,
   receive-request notes).
