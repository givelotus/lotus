# Vase

Vase is a Flutter wallet client with a Go HTTP server. The wallet opens directly into the QR scanner: balance at the top, settings and receive actions at the sides, and manual send at the bottom. A valid scan opens payment details; returning resumes the camera.

The scanner layout follows upstream commit `c35df3b4d712fba5cf04dbfd72f21e33584f1991`, before the `d06a7586` redesign. It uses the current wallet models, secure-storage handling, payment confirmation, and canonical Dart SDK rather than reverting those implementations.

## Client development

Validated tooling: Flutter 3.47.4 with Dart 3.13.3. Install Flutter, then run from `wallets/vase/vase-client`:

```sh
flutter pub get
flutter test
flutter analyze --no-fatal-infos --no-fatal-warnings
flutter build web --no-wasm-dry-run
```

Set `--dart-define=CHRONIK_URL=https://your-chronik-host` when running or building to choose a backend; the existing public endpoint remains the default. Backend availability and real payments are not exercised by the local tests.

The wallet uses the current SDK Chronik protobufs for UTXOs, single-transaction broadcast, and WebSocket notifications. The embedded client still contains unused historical block/history/token/batch APIs; those have not been migrated or verified.

The application and its primitive tests import `sdk/dart` through the `lotus_dart` path dependency. The historical `lib/lotus` source copy remains for reference, but is not the implementation used by the wallet or these tests.

Scanner widget tests inject a camera placeholder and a wallet model without storage or networking. To inspect that layout without accessing a camera, wallet storage, telemetry, or a live backend:

```sh
flutter run -d chrome --target=tool/scanner_preview.dart
```

The preview uses a flat camera placeholder and a fixed example balance. It does not initialize a real wallet.

Native Android/iOS builds require the Android SDK or full Xcode/CocoaPods installations. Passing widget tests and a web compiler build does not establish native camera behavior or validate a live payment. Existing analyzer notices in inherited code remain visible.

## Amount keypad correctness

Amounts use exact integer base units (1 XPI = 1,000,000 units). Decimal editing and payment/request values use canonical ASCII text; grouping and decimal separators are applied only for display. Ambiguous pasted separators, signs, exponents, and nonzero fractions smaller than a base unit are rejected instead of becoming zero or a different amount. Empty editing text becomes `0`.

| Input or operation | Previous behavior | Corrected behavior |
|---|---|---|
| Enter `1.000001` XPI | 1,000,000 base units | 1,000,001 base units |
| Enter `0.000249` XPI | 248 base units | 249 base units |
| Type `0.000001` on keypad | Last digit blocked by seven-character limit | One base unit can be entered |
| Display `1.005` XPI with two decimals | `1 XPI` | `1.01 XPI` |
| Edit 9,007,199,254,740,993 base units | Low digits lost through floating point | Exact `9007199254.740993` XPI |
| Clear amount or paste malformed text | Empty state could crash; invalid text could become zero | Clear produces `0`; malformed text leaves the prior value intact |

The keypad preserves all six fractional digits, trailing decimal/zero editing states, and up to 19 integer digits. Presentation rounds to the requested precision with ties away from zero; that rounded text is never used to construct a payment. The Done/Send path rejects zero amounts. Current mainnet wallet code contains no arithmetic-expression or fiat conversion engine; historical calculator operators are not reintroduced by these corrections.

Validation: the initial unchanged-code regression run failed 10 of 11 tests. The corrected wallet passes 59 Flutter tests, including 15 amount/keypad regressions; 12 amount/model tests also pass in headless Chrome to cover JavaScript precision. The production web build passes. Tests use mock wallet/haptics and do not access a real wallet, camera, storage, or broadcast a transaction.

## Server development

From `wallets/vase/vase-server`:

```sh
go test -race ./...
go vet ./...
go build -o /tmp/vase-server .
```

Use `.env.example` to configure a local `.env` before starting the server. Startup requires PostgreSQL with PostGIS. The server uses Go standard-library HTTP routing and pgx; its schema and registration API remain compatible with the previous GORM tables. Handler tests use injected persistence; isolated PostgreSQL/PostGIS tests cover fresh and existing schemas. See [server setup and compatibility checks](vase-server/README.md). Existing databases and services were not modified during validation.

## Licensing

The main body of Vase is GPLv3. The Lotus library code is MIT licensed and derives from [dartsv](https://github.com/twostack/dartsv). Its notices are preserved in the source copy and canonical SDK.

## Dependencies and existing-wallet upgrades

Dependencies were refreshed against official stable package releases on 2026-10-14, using Flutter 3.47.4/Dart 3.13.3. The complete [before/after inventory](vase-client/dependency-audit-20261014.json) records direct and transitive versions. Notable current versions include router 18.1.0, scanner 7.4.2, Sentry 10.0.0, package-info 10.2.2, location 10.0.2, protobuf 6.1.0 and PointyCastle 4.0.0. Unused direct dependencies were removed. Generated JSON and platform plugin registrations were refreshed.

| Retained version | Reason a newer version is not used |
|---|---|
| flutter_secure_storage 10.3.4 | Required transition for existing v6 Android cipher data; v11 removes those legacy algorithms before an unmigrated wallet can read them. |
| test 1.31.1 | Installed Flutter pins test_api 0.7.12; later test releases require newer test_api. |
| build_runner 2.16.1 | Later versions require analyzer 14 or build 5, incompatible with the Flutter test stack/current JSON generator. |

Other remaining transitive updates are bounded by Flutter or upstream package constraints; the inventory lists them explicitly. No overrides force incompatible versions. The latest published slide_to_confirm remains 1.1.0; it still compiles and its confirmation UI is retained.

Secure storage retains the original namespaces and keychain settings, enables backup migration and Windows legacy compatibility, and disables key deletion on storage errors. Failed reads leave the wallet unavailable instead of creating replacement keys. This upgrade must pass native tests with a known dummy wallet installed through the old signed application, upgraded without uninstalling, and checked for identical wallet identity after migration/restart. Android legacy cipher, Apple keychain and Windows legacy storage paths require separate checks. Mock tests cannot establish native migration correctness; downgrading the dependency does not reverse a completed storage-format migration. The [agent notes](AGENTS.md) describe the checks.

The updated native plugins require Android API 26/compile SDK 36, iOS 15 and macOS 12. Android build configuration follows the installed Flutter template and retains application identity and signing. Native builds and existing-wallet migration are not locally validated because the required native SDKs/tooling are absent. Web builds and camera-free tests do not establish native compatibility.

Validation after these dependency changes: 73 Flutter tests pass, full analyzer reports no errors with inherited notices visible, the JSON generator succeeds, and the production web build passes. The canonical SDK independently passes 42 tests plus JavaScript compilation and native OpenSSL signing interoperability checks. Go race tests, vet and builds pass, with PostgreSQL 18.6/PostGIS 3.6.3 compatibility tests using isolated fresh and original schemas. These checks do not access existing wallet storage or broadcast payments.

The remaining transitive gaps are traceable: analyzer/_fe_analyzer_shared/source_gen/test_core/test_api/package_config follow the Flutter test stack; build/build_config follow generator constraints; cli_util and coverage follow flutter_launcher_icons' cli_util 0.4 constraint; qr_flutter retains qr 3; Sentry retains jni below 1.1, which also bounds jni_flutter; Flutter pins material_color_utilities; flutter_secure_storage_darwin follows the deliberate v10 bridge. The full resolver inventory retains exact current/latest versions. CupertinoIcons 2.0.0 remains because Flutter widgets reference its font; removing it produced a missing-font compiler warning.

### Arithmetic amount entry

Send and Receive amount editors include addition, subtraction, multiplication,
division, clear, backspace and equals, with a live expression and XPI preview.
Calculations run left to right (`8 − 2 + 3 × 4 = 36`). Intermediate fractions
stay exact; Done requires a positive result exactly representable in six decimal
places. Division by zero, unfinished expressions and unrepresentable results
show an error instead of silently rounding a payment.

Closing the editor discards its draft. Done commits the amount once; reopening
starts from that amount. Receive requests can exceed your current balance and
remain separate from Send. QR codes and copied requests carry base-unit amounts.

### iOS simulator development

Use a dedicated simulator for wallet previews so existing app/keychain data stays
separate. With full Xcode installed, scope its developer directory to each command
instead of changing the system `xcode-select` setting:

```sh
cd wallets/vase/vase-client
DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer tool/with_xcode.sh flutter pub get
DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer tool/with_xcode.sh flutter build ios --simulator --debug --no-pub
```

Run `pub get` with the same developer directory: otherwise generated plugin
metadata can incorrectly report Swift Package Manager unavailable. The wrapper
also preserves that selection for Dart native build hooks, which filter ordinary
environment variables but forward PATH. It creates a temporary `xcrun` wrapper
and removes it after the command; it does not change system tool configuration.

Current Sentry requires SwiftPM; the app enables it in its project configuration.
All current iOS plugins support SwiftPM, and the old iOS CocoaPods integration
has been removed. The first build fetches native framework dependencies and may
take several minutes. Simulator builds do not need an Apple developer account;
signing/distribution and physical-device checks are separate. Xcode 27 / iOS 27
simulator builds pass; camera, push notifications and existing-wallet keychain
migration still require separate device checks.

For a local simulator preview, point the existing Chronik override at a running
local Lotus node (the simulator shares the Mac's loopback network):

```sh
tool/with_xcode.sh flutter build ios --simulator --debug --no-pub \
  --dart-define=CHRONIK_URL=http://127.0.0.1:19331
```

Use the port of your own isolated node. This changes the preview build only;
it does not provide an automatic fallback or change release defaults. A backend
balance error is displayed separately from failure to open wallet storage.
The iOS simulator has no physical camera, so scanner availability must be tested
on an actual device.

### Isolated funded wallet tests

The normal preview at port 19331 uses mainnet. Instant mining is available only
on regtest; do not switch an existing wallet to a different chain to manufacture
funds. `vase-client/tool/regtest_wallet_test.dart` exercises the actual wallet
signing/HTTP/WebSocket code with public fixture keys and no secure-storage access.
It requires a **fresh** regtest chain, checks the RPC chain and matching Chronik
genesis before mining, matures the coinbase, sends exactly 1.000001 XPI, verifies
raw bytes/merkleized TxIds and balances, confirms it, sends a reply, and runs
`verifychain`. These are test coins with no mainnet value.

From `wallets/vase/vase-client`, using your validated local Lotus binaries:

```sh
export VASE_REGTEST_DATADIR=$(mktemp -d /tmp/vase-regtest.XXXXXX)
/path/to/lotusd -datadir="$VASE_REGTEST_DATADIR" -regtest \
  -rpcport=22604 -port=22605 -listen=0 -connect=0 -dnsseed=0 \
  -avalanche=0 -chronik=1 -chronikbind=127.0.0.1:22331 -daemon
# Wait until this succeeds and reports chain=regtest:
/path/to/lotus-cli -datadir="$VASE_REGTEST_DATADIR" -regtest -rpcport=22604 getblockchaininfo
tool/with_xcode.sh flutter test --no-pub tool/regtest_wallet_test.dart
```

The test defaults to RPC 22604 and Chronik 22331; optional
`VASE_REGTEST_RPC_PORT`/`VASE_REGTEST_CHRONIK_PORT` overrides remain loopback-only.
It skips without the explicit datadir environment variable. Never point it at an
existing production datadir. Shut down only your test node using its exact
datadir, `-regtest -rpcport=22604 stop` when finished.

For manual payment-confirmation tests, build `tool/regtest_preview.dart` and
install it **only on a separate disposable simulator**, never over an existing
wallet preview. It uses the real Send screen and confirmation slider, an orange
REGTEST banner, public in-memory keys, and a fixed loopback Chronik on 22331.
It checks the Lotus regtest genesis and refuses other chains; it neither
initializes telemetry nor reads/writes wallet secure storage. It starts with a
1.000001-XPI payment to a second fixture key. Run the funded test above first.

```sh
tool/with_xcode.sh flutter build ios --simulator --debug --no-pub \
  --target=tool/regtest_preview.dart
# Install Runner.app only on the new dedicated test simulator's UDID.
```

The ordinary app remains `lib/main.dart`; build it with the mainnet Chronik URL
when updating Lotus Preview again. Do not distribute a fixture build.

### Backend lab

`tool/backend-lab.compose.yaml` runs isolated PostGIS and a registration server,
with loopback HTTP 28080 and database 25432. It never mounts an existing database.
Its password/token values are disposable test fixtures, not deployment secrets.
Set `VASE_LAB_BIN` to an absolute directory containing Linux `server` and
`migrate` binaries, then run Compose with a unique `-p` project name:

```sh
VASE_LAB_BIN=/absolute/lab/bin docker compose -p vase-my-lab \
  -f tool/backend-lab.compose.yaml up -d --wait database
VASE_LAB_BIN=/absolute/lab/bin docker compose -p vase-my-lab \
  -f tool/backend-lab.compose.yaml run --rm migrate
VASE_LAB_BIN=/absolute/lab/bin docker compose -p vase-my-lab \
  -f tool/backend-lab.compose.yaml up -d server
```

For the 2026-10-14 lab, server sources were extracted from the existing reviewed
notifications candidate `30da8ced` into a private temporary directory using
`git archive`, without changing its worktree or merging it into this branch.
Build both binaries from that extracted `wallets/vase/vase-server` directory
with `CGO_ENABLED=0 GOOS=linux GOARCH=arm64 go build` (use `.` for server and
`./migrate` for migrate). The tested Docker host is arm64; select the matching
Go architecture on another host. PostGIS uses the repository's pinned amd64
image through Docker emulation. Notifications stay disabled without provider
credentials. Flutter currently has no backend registration/push setup; a running
lab server alone does not establish native push delivery.
