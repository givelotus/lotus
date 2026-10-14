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
