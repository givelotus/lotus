# Private V2 explorer integration

The native explorer candidate is integrated at `86201398e3df61605c2eb2d09c201ce774013e7f`. Its Chronik-enabled `lotusd` build completed successfully. Binary SHA256 is `8c6c2d0ed9fc490b8cdb8900f01564ca6902c5d7dbe269eae8d0becefe27ae32`. The build retains macOS dependency deployment-target warnings; other platforms are unverified.

The independently reviewed frontend is integrated at monorepo `39ac976c`, from candidate `dc9236e4`. Its 18 tests cover route/status validation, bounded response reads, snapshot retries, and real loopback proxy forwarding and timeouts. It uses Chronik HTTP through a bounded same-origin development proxy. See [frontend instructions](../../explorer/v2/README.md).

Native exact-frame production and synchronization tests passed 2/2. The Rust candidate at `a22ab390d8828fe3fe05a2e2a5d7adc95ca35c42` passed DB 23/23, HTTP 18/18, indexer 14/14 and service/CXX bridge 6/6. Rust tests use real RocksDB and HTTP service instances with synthetic DTO fixtures; they do not establish consensus acceptance of those fixtures. Native fixtures and the actual daemon integration supply separate gates.

The native node now opens schema 3 in `chronik-v2-explorer-v1` under its explicit development home, preserving previous `chronik-v2` index files. This is a fresh index build, not a schema migration. Existing chain state is authoritative. No production data is changed.

[Retained integration evidence](evidence/v2-explorer-integration-20261015) includes native test/build output, Rust service results and binary provenance. Full daemon build output is retained locally at `/private/tmp/lotus-v2-explorer-integrated-build-20261015.log`.

The same combined binary also passed the actual Avalanche observer process harness, including genesis/unknown-block policy observations, two observer peers, IBD gates and malformed private credential rejection. Temporary nodes were cleaned; public traces are retained under `observer-process`. This does not establish funded quorum or explorer HTTP behavior.

Actual native explorer screen, token lifecycle, restart and reorg acceptance are still pending. The native candidate is now recorded through maintained patch 300, with all 301 intermediate trees verified in a fresh replay; see [replay evidence](evidence/v2-series-replay-300.json). This report is not private-testnet completion evidence.
