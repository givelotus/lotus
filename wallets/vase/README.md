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

Use `.env.example` to configure a local `.env` before starting the server. Startup requires PostgreSQL; handler tests use injected persistence and do not exercise a database. Invalid user-information requests are rejected before persistence, and the three database writes are transactional.

## Licensing

The main body of Vase is GPLv3. The Lotus library code is MIT licensed and derives from [dartsv](https://github.com/twostack/dartsv). Its notices are preserved in the source copy and canonical SDK.
