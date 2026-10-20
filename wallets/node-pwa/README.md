# Node PWA wallet

A browser wallet for your own node. It replaces bitcoin-qt: every screen is a
view over the node's ordinary wallet and node RPCs (`getbalances`,
`sendmany`, `listtransactions`, `getpeerinfo`, …), so the keys stay in the
node's wallet. It is not the Frank app and has no server of its own.

Design: `docs/addendum-designs/P1-pwa-wallet-and-Q1-qt-removal.md` in the
`lotus-v2-addendum` repository (§2 is the app, §2.9 the parity checklist).
This directory implements phase 1: overview, send, receive, transactions,
wallets, peers, message signing/verification, console and node information.

The app is plain ES2022 modules with no build step: `src/` is exactly what the
browser runs. The only runtime dependencies are two vendored, hash-pinned files
in `src/vendor/` (htm 3.1.1's Preact standalone build, and nayuki's QR Code
generator 1.8.0); `VENDOR.json` records their origin, licence and sha256.

## Message signatures

Use **Sign / verify message** in the sidebar. Signing calls the selected
wallet's `signmessage` RPC; verification calls the node's `verifymessage`
RPC and needs no loaded wallet. Both implement the daemon's legacy compact
signature format for P2PKH addresses. Native V2 and script addresses are not
supported by these RPCs; the UI displays the daemon's errors rather than
creating a different signature scheme.

Messages retain their spaces and line breaks. Keys remain in the daemon. If
the selected wallet is locked, the UI requests a passphrase for a 60-second
unlock and relocks after the operation, including signing failures. It leaves
an already-unlocked wallet unlocked. Passphrases are cleared and never saved;
a relock failure is shown explicitly. Forms and signatures are not stored in
browser history or local storage.

## Status of the daemon side

The node is meant to serve this app itself under `/wallet/`, with browser
sessions (`/auth/session`, an HttpOnly cookie and an `X-CSRF-Token` header),
`-walletpwadir=<dir>` for development, `-gui` and `getwalletpwaurl` for
login links. **That daemon patch does not exist yet.** Until it does, use the
development server below, which plays the node's part.

## Development

Requirements: Node 22 or later, and a running node with RPC enabled. Tests
use Google Chrome through Playwright.

```sh
cd wallets/node-pwa
PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 npm ci   # dev dependency: @playwright/test only
```

Start a throwaway regtest node, for example:

```sh
mkdir -p /tmp/pwa-regtest
lotusd -regtest -datadir=/tmp/pwa-regtest -rpcport=18604 -port=18605 -listen=0 -keypool=5 -daemon
```

`-keypool=5` is only to make encrypted test wallets quick: creating an
encrypted wallet encrypts its whole keypool, which takes minutes with the
default 1000 keys on some builds.

Then run the dev server and open the printed URL:

```sh
npm run dev -- --datadir /tmp/pwa-regtest --chain regtest --rpcport 18604
# Wallet: http://127.0.0.1:18680/wallet/
```

The dev server (`tools/devserver.mjs`, Node stdlib only):

- serves `src/` (or `--root <dir>`) under `/wallet/` with the design's path
  rules, MIME table, CSP and other security headers, and `Cache-Control:
  no-store`, so edits show up on reload;
- forwards JSON-RPC `POST /` and `POST /wallet/<name>` to the node, adding
  Basic auth from the node's cookie file (re-read on every request, so node
  restarts are fine) or from `--rpcuser`/`--rpcpassword`;
- listens on 127.0.0.1 by default. Anyone who can reach it can use the
  node's RPC, so do not bind it elsewhere.

### Authentication modes

`index.html` carries `<meta name="node-pwa-auth" content="session">`, the
mode a node serving the app will use. `lib/session.js` implements both modes
behind one interface (`headers()`, `onUnauthorized()`, `status()`, login and
logout), and `lib/rpc.js` only ever asks it for headers, so the RPC layer is
the same in both:

- `--auth proxy` (default): the dev server rewrites the meta tag to `proxy`.
  The app sends no credentials and has no login screen; the proxy adds Basic
  auth.
- `--auth session`: the dev server emulates the planned daemon behaviour:
  one-time login tokens (printed as `Wallet: …/wallet/#/login/<token>`; press
  Enter for a new one, they expire after 120 s), password or pasted cookie-line
  login, `GET`/`POST /auth/session`, `POST /auth/logout`, the
  `nodewallet_<rpcport>` HttpOnly SameSite=Strict cookie, `X-CSRF-Token` and
  the Origin/Host policy. Sessions live in the server's memory, so restarting
  it logs everyone out, as a node restart will.

When the daemon serves the app, nothing in the app changes: the shipped
`index.html` already says `session`.

## Tests

```sh
npm test       # unit tests, node --test (no node or browser needed)
npm run lint   # tools/lint.mjs: no innerHTML/eval/new Function/inline handlers/remote URLs
```

Unit tests cover the lossless JSON parser, amounts, xpiaddr encode/decode
against every vector in `test/fixtures/xpiaddr_v2_vectors.json` (copied from
the V2 reference generator), payment URIs, the console parser, the RPC client
and batching with a mocked `fetch`, session auth, the poller (fake timers),
profile detection, routing, the vendored-file hashes, the packer and the dev
server's path, origin, token and session rules.

Smoke test (Playwright, headless Chrome, a fresh regtest node on free ports):

```sh
LOTUSD=/path/to/lotusd npm run smoke
```

It skips with a message when `LOTUSD` is unset. It starts `lotusd -regtest`
with a new datadir (under `NODE_PWA_SMOKE_TMP`, default the system temp
directory, removed afterwards unless `NODE_PWA_SMOKE_KEEP=1`), `-listen=0`
and `-keypool=5`, runs the dev server in-process, and checks:

1. proxy mode: the empty-wallet prompt; creating `w1` in the UI; mining
   101 blocks from the console to an address from the Receive view; console
   nested calls, `[index]` selection and history; the mature balance; a send
   with "subtract fee" through the confirm dialog; the transaction in the list
   and the details modal; a pasted payment URI filling amount and label;
   rejection of too many decimals; empty peers; the network on/off switch;
   unbanning and clearing bans; the node view;
2. an encrypted wallet: the passphrase prompt, a wrong passphrase, a
   successful send, and the wallet locked again afterwards;
3. session mode: a login link (and the token removed from the URL), the
   session surviving a reload, logout, single-use links, password login with
   the cookie line, the offline shell served by the service worker when the
   server is gone, and reconnection to the login screen after a restart;
4. the packed release bundle, extracted and served, with the service worker
   caching it under `node-pwa-<version>`.

`PW_CHANNEL=chromium` uses Playwright's own Chromium instead of the installed
Chrome (`npx playwright install chromium` first).

## Release bundle

```sh
npm run pack
# dist/node-pwa-0.1.0.tar.gz
# sha256 <hex>
```

`tools/pack.mjs` (Node stdlib only) writes `dist/node-pwa-<version>.tar.gz`
and a `.sha256` file in the `node-pwa-bundle/1` format the daemon embeds:

- every member sits under `node-pwa/`: all files of `src/`, plus a generated
  `BUNDLE.json` (`format`, `name`, `version` from `package.json`,
  `source_commit` from `git rev-parse HEAD`, and each file's sha256 and size),
  plus a `<file>.gz` beside every listed `.html .js .mjs .css .json
  .webmanifest .svg .txt` file;
- regular files only, sorted, ustar headers with mode 0644, uid/gid 0 and
  mtime `SOURCE_DATE_EPOCH` (default 0); every gzip stream has mtime 0 and
  OS byte 255;
- `sw.js` gets the version written into its `VERSION` constant, so the
  service worker precaches the files listed in `BUNDLE.json` into
  `node-pwa-<version>`.

It refuses to pack uncommitted changes under `src/` (pass `--allow-dirty` for
a throwaway build). The same commit packs to the same bytes as long as Node's
zlib is the same, so CI pins the Node version and packs twice to compare.

To embed it in a daemon build (once the daemon patch exists):

```sh
cmake -B build -DWALLET_PWA_BUNDLE=$PWD/dist/node-pwa-0.1.0.tar.gz \
      -DWALLET_PWA_BUNDLE_SHA256=$(cut -d' ' -f1 dist/node-pwa-0.1.0.tar.gz.sha256)
```

Configure fails if the hash does not match. Release builds take the bundle
from a GitHub release asset instead: `.github/workflows/node-pwa.yml` runs the
tests and lint, packs twice and compares, uploads the bundle as an artifact,
and on a `node-pwa-vX.Y.Z` tag publishes the tarball and its `.sha256`. The
daemon's pin (the depends recipe and `daemon/wallet-pwa-version`) is then
bumped by hand.

## Notes

- Amounts are BigInt base units. Ticker and decimals come from
  `getcurrencyinfo`; amounts are sent to the node as exact decimal strings and
  RPC replies are parsed without rounding (`lib/json.js`).
- Addresses are displayed exactly as the RPCs return them. On a Lotus V2 node
  (134-byte headers) the app probes whether the node accepts `xpi1…`
  addresses and, if so, checks typed addresses locally (`lib/xpiaddr.js`)
  before asking `validateaddress`, which stays authoritative. Current V2
  builds still return cashaddr, so the probe falls back to cashaddr.
- Each visible tab keeps one `waitfornewblock 10000` call open, which
  occupies one of the node's RPC worker threads (`-rpcthreads`, default 4).
  Hidden tabs pause it.
- Receive-request history is kept in this browser's IndexedDB per node origin
  and wallet; console history in localStorage (sensitive commands such as
  `walletpassphrase` are never stored).
- `node tools/icons.mjs` regenerates the PNG icons from the same geometry as
  `src/icons/icon.svg`.
