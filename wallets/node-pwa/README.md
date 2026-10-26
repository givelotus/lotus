# Node PWA wallet

A browser wallet for your own node. It replaces bitcoin-qt: every screen is a
view over the node's ordinary wallet and node RPCs (`getbalances`,
`sendmany`, `listtransactions`, `getpeerinfo`, …), so the keys stay in the
node's wallet. It is not the Frank app and has no server of its own.

Design: [PWA and Qt-removal research](../../docs/lotus-v2/research/addendum-designs/P1-pwa-wallet-and-Q1-qt-removal.md)
(§2 is the app, §2.9 the parity checklist).
This directory implements phase 1: overview, send, receive, transactions,
wallets, peers, message signing/verification, mining, console and node information.

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

Node builds containing the PWA integration serve this app under `/wallet/`,
with browser sessions (`/auth/session`, an HttpOnly cookie and an
`X-CSRF-Token` header), `-walletpwadir=<dir>` for development, `-gui` and
`getwalletpwaurl` for login links. Point `-walletpwadir` at this directory's
`src/` and refresh the browser to review UI changes. A node with discovery
but no built-in PWA host can use the development server below.

## Mining and ChainConfig

The **Mining** page never starts mining automatically. A payout address may
be entered or generated in the selected node wallet. Regtest has explicit
**Mine 1 test block** and **Mine 101 test blocks** buttons using
`generatetoaddress`; this is node-side test generation, not GPU hashing.
The page rechecks that the node is on regtest before calling it.

Browser GPU mining is opt-in and requires WebGPU in a secure context
(HTTPS or localhost), a usable GPU adapter, and authoritative `getchainconfig` discovery
version 1. Nodes missing this endpoint show an explicit unsupported-node
screen; the app does not probe older RPCs to guess its configuration.
The daemon host must serve local `.wgsl` files. No shader code, script URL
or remote executable comes from the descriptor.

`lib/chainconfig.js` resolves one immutable configuration from the node:
network/genesis identity, address capabilities, currency atomic unit and RPC precision,
display policy, and mining algorithm/header/RPC contract. `ChainAdaptor`
caches one configuration per authenticated connection from one discovery
call; disconnect, logout and network changes invalidate it. Reconnect checks
the canonical network/genesis identity and clears cached wallet data. Amount entry and
RPC serialization retain the full node precision. The default two-decimal
display removes redundant zeroes only; nonzero atomic units are never hidden.

Supported algorithms are compiled into this bundle:

- `sha256d`: 80-byte header, 32-bit little-endian nonce at byte 76.
- `lotus-v2-blockid`: 134-byte header, 64-bit little-endian nonce at byte 42;
  domain-separated BLAKE3 body, work and block-ID hashes with the raw chain
  identity. This is not a single BLAKE3 hash of the serialized header.

The worker dispatches at most 1,024 nonces per batch. Its GPU digests are
checked against CPU reference hashes; the main thread also verifies winning
proofs before submission. The node supplies the complete serialized candidate
with `getrawunsolvedblock`, including coinbase and commitments. Only nonce
bytes change; `submitblock` remains authoritative. Candidate size is limited
to 32 MiB in this browser implementation. Stale tips are checked every five
seconds and before submission; templates refresh after 15 seconds. Stop,
leaving the page, hiding the tab, device loss or an error ends the session.
Resuming requires another explicit Start. One already submitted bounded GPU
batch or block-submission RPC may finish after Stop.

Counters report only completed GPU dispatches. Session hash rate includes
initialization, template refresh and submission time; it is not a benchmark
or a promise of economically viable mining.

Focused checks (no production node needed):

```sh
npm test
MINING_GPU=1 node --test test/unit/mining-hashes.test.js test/unit/mining-runtime.test.js
npx playwright test --config test/smoke/playwright.config.mjs ui-controls.spec.mjs
```

`test/smoke/mining-node-proof.mjs` is an explicit opt-in accepted-block proof
using a supplied binary, a fresh isolated regtest datadir, and owned ports.
It writes a receipt with binary hash, descriptor provenance and accepted tip.
Its audited historical-reference path requires
`NODE_PWA_MINING_ALLOW_REFERENCE=1` explicitly and does not enable mining
on older nodes in the public UI.

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

## Built-in Lotus V2 pool mining

The Mining page supports solo mining and the built-in Lotus V2 pool over the
existing authenticated node RPC connection. It never starts or resumes mining
automatically. Review the pool address, operator commission and PPLNS share
window, choose a native payout destination and worker name, then press Start.
Pool statistics and the PPLNS window live in node memory and clear on restart.
A share count or PPLNS weight is not an earned balance or a promised payout.

Native pool payouts require the node's explicit `address.nativehrp` and
`xpiaddr` in `address.acceptedformats`; the legacy default address format and
prefix remain independent. Selected-wallet payouts additionally require:
`wallet.native_receiving = {available: true, address_type: "native", format:
"xpiaddr", template: "keyhash"}`. The app calls
`getnewaddress("Pool mining", "native")` and verifies selected-wallet ownership
with native `getaddressinfo` before mining. Older nodes leave that provider
disabled. External native wallets are a separate explicit provider; the user
supplies an address they control. Native receiving ownership does not imply
that the ordinary wallet Send flow can spend native funds.

The browser uses the existing bounded WebGPU worker and native three-stage
PoW with CPU verification, searches only its assigned 24-bit nonce prefix,
submits exact decimal-string uint64 nonces and refreshes jobs/VarDiff after
shares and at most every five seconds. It stops on visibility, navigation,
wallet/connection changes, device/RPC errors and changed pool terms.

This is private-node integration. It does not grant remote browsers public
operator RPC access, implement a public pool gateway, or enable pooled XEC
mining. The daemon pool endpoint and native-wallet capability must be supplied
by an independently validated backend build.

Focused opt-in browser checks:

```sh
MINING_GPU=1 node --test --test-name-pattern='native GPU worker honors' test/unit/mining-runtime.test.js
MINING_UI=1 node --test test/unit/pool-ui.test.js
NODE_PWA_POOL_BINARY=/absolute/path/lotusd NODE_PWA_POOL_OUT=/persistent/evidence node test/smoke/pool-node-proof.mjs
```

The last command creates a fresh isolated regtest node and tests the real UI,
native wallet ownership, GPU pool shares, accepted block and operator
commission. It requires the combined discovery/native-receive/pool backend;
unit or mock UI success is not evidence that this integration passed.

## Notes

- Amounts are BigInt base units. Ticker and precision come from the
  authoritative `getchainconfig` response; amounts are sent as exact decimal
  strings and RPC replies are parsed without rounding (`lib/json.js`).
- Addresses are displayed exactly as returned by the node. Actual accepted
  formats, prefixes and destination types come from discovery. Address input
  validation still uses `validateaddress` for the entered address; discovery
  never probes a synthetic address or infers capabilities from a header size.
- Each visible tab keeps one `waitfornewblock 10000` call open, which
  occupies one of the node's RPC worker threads (`-rpcthreads`, default 4).
  Hidden tabs pause it.
- Receive-request history is kept in this browser's IndexedDB per node origin
  canonical chain identity and wallet; console history in localStorage (sensitive commands such as
  `walletpassphrase` are never stored).
- `node tools/icons.mjs` regenerates the PNG icons from the same geometry as
  `src/icons/icon.svg`.
