# Server dependency and data access audit — 2026-10-14

The single registration endpoint now uses `net/http` and an explicit pgx data
access layer. Gin, GORM, the GORM PostgreSQL adapter, and their unused dependency
graph are removed rather than upgraded into the new implementation. Push token,
wallet address, coordinate, transaction, JSON, and soft-delete semantics remain
supported. PostGIS is retained for the backend's intended nearby-user features;
notification delivery and occasional block-reward distributions are not
implemented by this change.

## Versions and evidence

| Component | Before | After |
| --- | --- | --- |
| HTTP routing | Gin 1.8.1 | Go standard `net/http` |
| Data access | GORM 1.24.2 / driver 1.4.5 / pgx v4.17.2 | pgx v5.11.0 |
| `.env` loading | godotenv 1.4.0 | godotenv 1.5.1 |
| Go module minimum | 1.19 | 1.26.0 |
| Verification toolchain | Installed Go 1.27.1 | Isolated Go 1.27.2 |
| Development database image | Unversioned `postgis/postgis` | `postgis/postgis:18-3.6`, immutable amd64 digest |
| Selected dependency graph | 87 modules | 16 modules, including graph-only/test/tool dependencies |

The two direct modules and five explicit indirect/runtime modules are current at
this audit's module queries. [`dependency-inventory-20261014.json`](dependency-inventory-20261014.json)
records normalized output from `GOTOOLCHAIN=local go list -m -u -json all` before and
after the change. It excludes machine-local cache paths and includes available
updates. Go's latest-module query works per module path; it is not a claim that
every differently named future major module is automatically supported.

Five modules remain at versions inherited through dependency manifests, outside
the server's imported package graph. `go get -u all` does not retain their upgrades
and `go mod tidy` removes explicit unused constraints:

| Upstream graph-only module | Selected | Available at audit |
| --- | --- | --- |
| `github.com/kr/pretty` | v0.3.0 | v0.3.1 |
| `github.com/stretchr/objx` | v0.1.0 | v0.8.0 |
| `github.com/stretchr/testify` | v1.11.1 | v1.12.1 |
| `golang.org/x/mod` | v0.41.0 | v0.42.0 |
| `golang.org/x/tools` | v0.51.0 | v0.52.0 |

These are recorded rather than described as upgraded or artificially added as
unused application dependencies. The optional Air development command is updated
to `github.com/air-verse/air@v1.67.4`, verified by a module query, but was not installed
or run.

Go 1.27.2 was downloaded from the official Go release endpoint into `/tmp`; its
Darwin arm64 archive SHA256 was verified as
`76812b213b1b2302c978d28fa52fa92d541704b9e7d9d5db8002c50e4018c4c5`.
Checks use that explicit Go binary with `GOTOOLCHAIN=local`. The globally installed
Go toolchain was not changed.

The selected Docker manifest is Linux amd64 with digest
`sha256:7e00e8c3539fdd43f513b98806c8204714dcd09dea683c259e333d7690317119`.
The upstream PostGIS image documentation identifies `18-3.6` as a supported
recommended new-installation image with PostGIS 3.6.4. The tag/digest was verified
through the registry manifest; the Docker image was not run. Real local SQL and
extension checks instead used PostgreSQL 18.6 with PostGIS 3.6.3. Existing database
volumes were not upgraded or touched.

Primary references:

- [Go HTTP routing](https://go.dev/blog/routing-enhancements) and [official downloads](https://go.dev/dl/).
- [pgx v5 project and driver guidance](https://github.com/jackc/pgx).
- [PostGIS image versions, architectures, and volume layout](https://github.com/postgis/docker-postgis).
- [PostgreSQL version and major-upgrade policy](https://www.postgresql.org/support/versioning/).
- [Air installation](https://github.com/air-verse/air#installation).

## Database compatibility

A separate temporary Go module ran the original GORM 1.24.2/PostgreSQL adapter
1.4.5 `AutoMigrate` and `Save` against an isolated PostgreSQL 18.6 cluster. Its
schema dump is retained in [`storage/testdata/legacy_schema.sql`](storage/testdata/legacy_schema.sql).
It confirms text keys, the composite address key, `numeric` coordinates,
`timestamptz` timestamp/soft-delete columns, the `locations_id_seq` bigserial
sequence, original foreign key names, and indexes.

That baseline also demonstrates two distinct behaviors: a soft-deleted user
registration fails a duplicate-key insert, and an ordinary repeated registration
overwrites `created_at` with Go's zero time. The new layer preserves the former
rejection, including full rollback, and deliberately fixes the latter timestamp
bug. It preserves existing stored timestamps and does not repair historical zero
values without provenance.

Real isolated PostgreSQL/PostGIS tests exercise both the generated legacy schema
and a fresh explicit schema. They verify repeatable additive migration, unchanged
legacy columns/defaults, PostGIS extension availability, existing records and
created timestamps, composite-key upserts, new location per request, preserved
sequence values, rollback after the third write fails, soft-deleted address/user
rejection, and request cancellation.

The explicit migration is a bootstrap, not a general-purpose schema migration
engine: it creates absent tables/indexes and `CREATE EXTENSION IF NOT EXISTS
postgis`, without `ALTER EXTENSION UPDATE` or rewriting existing columns/data.
Server startup never executes it. No GIS query, notification delivery, payout,
consensus change, or production deployment is introduced.

## Completed validation

Using the isolated official Go 1.27.2 binary, all of these passed:

```sh
GOTOOLCHAIN=local go test -race -count=1 ./...
GOTOOLCHAIN=local go vet ./...
GOTOOLCHAIN=local go build -o /tmp/lotus-vase-server-deps-20261014 .
GOTOOLCHAIN=local go build -o /tmp/lotus-vase-migrate-deps-20261014 ./migrate
docker compose config --quiet
```

Handler regressions preserve coordinate bounds/null handling, exact JSON field
names and status codes, unknown/trailing JSON binding behavior, Content-Type
behavior, request context cancellation/value propagation, method/path behavior,
CORS absence, and database/panic error redaction. The integration suite ran rather
than skipped, with temporary PostgreSQL clusters shut down by test cleanup. The
separate original-GORM baseline cluster was also stopped after its schema dump.
No existing database, local `.env`, production server, or tracked binary was used
or changed. Go binaries were compiled outside the repository; no real HTTP server,
notification, or payment service was started.
