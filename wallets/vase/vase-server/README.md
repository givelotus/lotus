# Vase Server

The server registers a wallet's push token, XPI address, and coordinates through
`POST /userinfo`. HTTP routing uses Go's standard `net/http` package. The small
[`storage`](storage/) data access layer uses pgx v5 and explicit SQL transactions;
there is no ORM.

The intended backend roles are notifications, nearby-user discovery/chat using
PostGIS, and occasional block-reward-funded distributions to mobile wallet users.
Only registration is implemented here. Notification providers, nearby queries,
chat, and distribution rules/signing/scheduling remain undecided or unimplemented.
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
