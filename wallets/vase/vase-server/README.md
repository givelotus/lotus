# Vase Server

The server registers a wallet's push token, XPI address, and coordinates through
`POST /userinfo`. HTTP routing uses Go's standard `net/http` package. The small
[`storage`](storage/) data access layer uses pgx v5 and explicit SQL transactions;
there is no ORM.

The intended backend roles are notifications, nearby-user discovery/chat using
PostGIS, and occasional block-reward-funded distributions to mobile wallet users.
Registration and an opt-in Chronik/FCM notification worker are implemented. Nearby
queries, chat, and distribution rules/signing/scheduling remain unimplemented.
The registration fields and PostGIS capability are retained for that work.

## Development setup

Use Go 1.26 or newer; the dependency update was checked with Go 1.27.2. Download
the [official Go release](https://go.dev/dl/), then run from this directory:

```sh
GOTOOLCHAIN=local go mod download
cp .env.example .env
```

Configure `DB_STRING` in your local `.env`, or supply it directly in the process
environment. An existing environment value takes precedence over `.env`.
`PORT` defaults to `8080`; the HTTP bind behavior remains all interfaces.

For a **new development database**, the Compose file selects
`postgis/postgis:18-3.6` with an immutable Linux amd64 image digest. The upstream
image currently supports amd64; other Docker hosts need emulation. It retains
PostGIS for future spatial queries. Start it and explicitly initialize the tables:

```sh
docker compose up -d
GOTOOLCHAIN=local go run ./migrate
GOTOOLCHAIN=local go run .
```

The migration creates missing registration tables/indexes and the PostGIS
extension in one transaction. It preserves existing columns, rows, timestamps,
serial sequence values, and installed PostGIS versions. Server startup never runs
migrations. An existing schema with different columns needs a separately reviewed
migration; this bootstrap does not change it automatically.

Do not use the new Compose image as an automatic major upgrade of an existing
PostgreSQL data directory. PostgreSQL major upgrades require a planned backup and
restore or `pg_upgrade`; PostgreSQL 18 images also changed their volume layout.
Preserve the existing database/volume and select its upgrade procedure separately.
See the [PostgreSQL upgrade policy](https://www.postgresql.org/support/versioning/)
and [PostGIS image documentation](https://github.com/postgis/docker-postgis).

Optional live reloading uses the current
[Air module](https://github.com/air-verse/air#installation):

```sh
GOTOOLCHAIN=local go install github.com/air-verse/air@v1.67.4
air
```

Air is a development tool, not a server module dependency. Its installation and
live reload were not exercised during the dependency audit.

## Registration API

```json
{"PushToken":"token","Address":"lotus_...","Longitude":100,"Latitude":40}
```

Valid registration returns HTTP 200 with `{"info": ...}`. Invalid JSON, empty
identity fields, absent/null coordinates, or out-of-range coordinates return 400.
A persistence failure returns 500 without database details. Unknown fields,
missing/non-JSON Content-Type, and trailing data after the first JSON object retain
the previous handler's binding behavior. No CORS headers or authentication flow
were added.

One transaction upserts the user and address and appends one location record per
request. Soft-deleted user/address keys remain rejected. A repeated registration
preserves `created_at` and advances `updated_at`; this fixes the old GORM handler's
accidental overwrite of `created_at` with a zero timestamp. Historical timestamps
already stored in the database are not rewritten.

## Verification

```sh
GOTOOLCHAIN=local go test -race -count=1 ./...
GOTOOLCHAIN=local go vet ./...
GOTOOLCHAIN=local go build -o /tmp/vase-server .
GOTOOLCHAIN=local go build -o /tmp/vase-migrate ./migrate
```

Integration tests find PostgreSQL `initdb`/`pg_ctl` through `PATH` or
`VASE_TEST_POSTGRES_BIN`. They create and stop their own temporary cluster using a
private Unix socket, without accepting a database DSN or connecting to an existing
database. PostGIS must be available to that PostgreSQL installation. These tests
skip when PostgreSQL binaries are absent or the process runs as root; they fail
if an available installation cannot create PostGIS.

The audit exercised PostgreSQL 18.6 and PostGIS 3.6.3 locally. The pinned Docker
image was inspected and Compose syntax checked; the Docker image itself was not
started. See [dependency audit](dependency-audit-20261014.md) for exact versions,
remaining upstream graph-only pins, compatibility evidence, and limitations.

## Chronik notifications (opt-in)

Run the additive migration before enabling notifications. Startup never migrates
an existing database. Configure the environment explicitly:

```sh
VASE_NOTIFICATIONS=fcm
CHRONIK_URL=http://127.0.0.1:8331
FCM_PROJECT_ID=your-firebase-project
FCM_CREDENTIALS_FILE=/absolute/private/path/service-account.json
```

An unset `VASE_NOTIFICATIONS` starts only the registration server. Unknown
providers, absent credentials, unavailable notification schema, and another
notification worker owning the same database fail startup. Credentials are read
only when enabled, never returned or logged. The service account must have FCM
send permission; enable the FCM HTTP v1 API in the project. See Firebase's
[HTTP v1 authentication documentation](https://firebase.google.com/docs/cloud-messaging/send/v1-api).
Provider success means a valid FCM acceptance response, never proof that a device
received or displayed a notification. There is no mock-success provider in the
server executable.

Register a genuine **FCM registration token**, a mainnet Lotus XAddress, and
coordinates with the existing `POST /userinfo`. With notifications enabled,
invalid XAddresses return 400. Registration remains additive: registering another
address retains earlier addresses. Remove an exact token/address pair through
`POST /notifications/unregister` with `{"PushToken":"...","Address":"..."}`;
success is an idempotent 204. This deletes that address registration while
preserving location history. Future polling also observes user/address soft
removal made by existing administration. The existing API has no account or
address-ownership authentication: token possession is its capability. Deploy it
behind suitable access control before exposing it to untrusted callers. An
already in-flight provider request cannot be recalled by unregistering.

One WebSocket connection shares each script subscription (Taproot by commitment), routes
transaction activity to all matching registrations, and unsubscribes when the
last registration disappears. Startup loads current active registrations;
committed HTTP changes wake reconciliation immediately, with five-second polling
for external changes. Binary protobuf subscriptions/messages follow the canonical
SDK schema. Mainnet modern and historical XAddress checksums are supported.
Mempool-add and confirmation messages trigger a bounded HTTP transaction lookup;
input/output locking scripts determine recipients, so a shared WebSocket message
is never broadcast to every device. The notification says **wallet activity**:
it can represent incoming payments, spends, or change and does not promise an
amount or confirmation state. Removed/finalized/invalidated events are ignored.

Disconnects, protocol errors, lookup failures, and queue errors trigger jittered
exponential reconnect (one second to one minute) and full resubscription. A
30-second heartbeat detects half-open connections. Cancellation closes the socket,
joins its reader and both workers, and then releases the database ownership
session. Loss of the ownership connection stops the server to prevent two active
workers. Only one enabled worker per database is supported; ordinary registration
replicas can leave notifications disabled and their changes are polled.

The outbox deduplicates `(token,address,TxId)` for seven days, so mempool and
confirmation events yield one activity notification per address/device. Jobs
survive process restart. Delivery is serial, retries with exponential delay, and
stops after 12 attempts, explicit FCM `UNREGISTERED`, or seven-day expiry. Retry
attempts and terminal status are recorded without provider response bodies/tokens
in logs. Rows contain timestamps, attempts and provider-acceptance state; expired
rows are pruned in batches. A crash after provider acceptance but before recording
it can cause duplicate sends: clients should deduplicate `data.event_id`. Multiple
addresses on one device may intentionally yield separate jobs for one transaction.
Disabled/deleted registrations are excluded at delivery time.

Resources are bounded to 10,000 active registrations, 100,000 retained outbox
rows, 64 KiB WebSocket frames, 8 MiB transaction responses, 16 KiB HTTP request
bodies, one reader and one delivery worker. Capacity exhaustion stops observation
and retries without silently claiming delivery. Database registration itself is
not globally capped; exceeding worker capacity requires administrative cleanup or
a separately reviewed scaling design.

Chronik WebSocket events have **no replay cursor**. Activity while disconnected,
between subscription changes, or before a failed lookup/enqueue may be missed.
The outbox makes successfully observed/enqueued delivery durable; it does not
provide historical catch-up or exactly-once push. Wallet startup must refresh
on-chain state independently. Notifications are hints, never the wallet ledger.
No real credentials, devices, production database, or mainnet node were used in
validation.

The current Flutter app has no active push permission/token acquisition or
backend registration flow. This server implementation does not claim working
native end-to-end delivery. Android needs Firebase configuration and a client FCM
integration; Apple additionally needs APNs credentials configured in Firebase and
native capabilities/permissions. Raw APNs device tokens are not FCM tokens.
Web requires Firebase web setup, user permission, VAPID configuration and a service
worker; generic Web Push subscriptions and direct APNs are unsupported. No paid
account or provider project is created by this implementation.

Go wire bindings are generated from `sdk/dart/proto/chronik.proto` (the canonical
shared schema), not a second handwritten protocol. Regenerate from this directory:

```sh
go install google.golang.org/protobuf/cmd/protoc-gen-go@v1.36.12
protoc -I ../../../sdk/dart/proto --go_out=. \
  --go_opt=Mchronik.proto=vase.givelotus.org/server/notifications/chronikpb \
  --go_opt=module=vase.givelotus.org/server \
  ../../../sdk/dart/proto/chronik.proto
```

Simulated Chronik/FCM tests cover shared subscriptions, reconnect/resubscribe,
unsubscribe, cancellation, script routing, address checksums, provider rejection,
and honest acceptance semantics. The isolated PostgreSQL test verifies outbox
uniqueness, persistent retries, delayed attempts, success dedupe and registration
removal. Tests never accept a production DSN or real push token.
