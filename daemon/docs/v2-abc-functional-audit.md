# Inherited ABC functional suite audit (2026-10-15)

The inherited suite has **no demonstrated passing test in this audit yet**. Seven inherited scripts and one bespoke SQLite script were attempted unchanged; all eight were blocked before assertions by the same candidate daemon startup segmentation fault. This is a shared executable startup failure, not evidence that eight test bodies fail or that all inherited tests are broken.

## Provenance and isolation

Native test checkout: `/private/tmp/lotus-v2-abc-functional-audit-20261015`, branch `audit/v2-abc-functional-20261015`, exact source `f1c8c92d87023c620819dfc4a6bd88a28c446d46`. Documentation checkout starts at monorepo `48a47753`. No maintained patch, native source, main checkout, production data, or release asset was modified.

Executed daemon: `/private/tmp/lotus-v2-daemon-runtime-staging-20261015/build-chronik-v2/src/lotusd`, SHA256 `6065e9fdd8db763a2d58fa87a7891e4cf03e317b940c5eef84b3328c3249cb54`. Runtime checkout HEAD observed during audit is `f1c8c92d87023c620819dfc4a6bd88a28c446d46`; the parent audit confirms the executable was built from exact source `40d66a7d93b268957ca6b20b703d321a00f522b1` before later driver components. Subsequent builds at f1c8c92d87 rebuilt focused test targets only. The binary therefore does not establish integration of the later driver source.

The existing generated config selects Lotus daemon/CLI names, wallet ON, Chronik ON, ZMQ OFF. CLI executable was absent at initial inspection. These selected tests use RPC, so no CLI rename or source workaround was applied.

Every invocation used a new `/private/tmp/lotus-v2-abc-functional-case-*` datadir and separate cache. `TEST_RUNNER_PORT_MIN=38000`, seeds 41–48, MAX_NODES 64: initial P2P base is `38000 + (64 * seed) % 2935`; RPC adds 3000 and Chronik adds 6000 (remaining framework port classes use further 3000 increments). Exact generated ports are retained in `port-and-isolation-evidence.json`. No 10604, 10605, or 8331. Framework config disables discovery, DNS/fixed seeds and automatic connections (`connect=0`); P2P test connections are local framework peers. Failed processes were cleaned by the framework; `cleanup.txt` confirms zero remaining audit child daemons. No external peers or existing chain data were used.

## Measured executions

| Script | Origin / purpose | Result |
| --- | --- | --- |
| p2p_compactblocks_blocksonly.py | inherited compact block relay | startup SIGSEGV, cache initialization |
| abc_p2p_version_timestamp.py | inherited P2P version handling | startup SIGSEGV |
| mempool_accept.py | inherited transaction acceptance | startup SIGSEGV |
| mempool_reorg.py | inherited reorg/mempool behavior | startup SIGSEGV |
| feature_blocksdir.py | inherited block storage path | startup SIGSEGV |
| feature_reindex.py | inherited reindex | startup SIGSEGV |
| wallet_createwallet.py | inherited wallet creation | startup SIGSEGV |
| wallet_sqlite_v2.py | new SQLite storage harness | startup SIGSEGV |

Inherited script counts: **0 pass, 7 blocked/failed launches, 284 not run** out of 291 inherited scripts. New V2 scripts: **0 pass, 1 blocked launch, 0 not run** out of 1. Counts are distinct top-level scripts, not runner parameter variants or individual assertions. Overall: 292 scripts, 8 attempted, 284 not run. No tests were removed, weakened, or skipped to obtain green status.

All observed launch failures report exit `-11`. Even `lotusd -version` crashes before reading chain fixtures. Sanitized macOS stack evidence in `startup-crash-stack.json` shows `ArgsManager::AddArg` → `UniqueLock` destructor → `LeaveCritical`/`pop_lock` → `CLockLocation` string destruction. Mixed lock-debug compilation is a hypothesis, not an established diagnosis. No upstream-base comparison was run: a coherent candidate executable must first start before fixture or upstream behavior comparisons are informative.

## Complete inventory and migration scope

`evidence/v2-abc-functional-audit/inventory.json` lists every one of the 292 top-level scripts, its provisional disposition, and measured status. Classification is conservative triage based on test names and subsystem ownership, **not a completed semantic review of every assertion**. No category certifies a passing test or authorizes dropping it.

| Provisional disposition | Scripts | Required work |
| --- | ---: | --- |
| Applicable inherited regression candidates | 120 | Review arguments/fixtures, execute unchanged on a coherent build |
| V2 migration/review: Avalanche, Chronik, token and related protocols | 69 | Identify retained ABC behavior versus replaced V2 semantics |
| V2 migration/review: chain, transaction, block and policy fixtures | 58 | Replace legacy serialization/PoW/transaction assumptions with explicit V2 fixtures |
| Wallet/SQLite migration | 38 | Review BDB paths, backup/restore, encryption and descriptor assumptions individually |
| Inapplicable to current build/isolation policy | 6 | ZMQ disabled; USDT unavailable; external bind tests outside this isolation audit |
| Newly added V2 scripts | 1 | Track separately from inherited regression evidence |

Inherited clean/cached regtest tests remain legacy execution unless their chain mode and fixtures explicitly select V2. A passing legacy P2P, wallet, mempool, reorg or storage test would establish that subsystem's exercised legacy path; it would not validate native V2 transaction commitments, VM execution, settlement/reorg ordering or epoch headers. The bespoke V2 harness is additional coverage and cannot substitute for running applicable inherited regression tests.

## Follow-up gates

1. Rebuild a coherent candidate daemon and record exact commit, flags, binary hash and `-version` success. Resolve the startup crash before increasing the script sample.
2. Repeat these eight unchanged scripts with fresh directories. Investigate each substantive failure separately; use exact upstream-base comparison where an inherited regression is suspected.
3. Review each inventory entry's fixtures and classify assertions precisely; retain useful generic RPC/P2P/storage/wallet checks while adapting chain-sensitive fixtures in separate reviewed changes.
4. Add explicit native V2 fixtures for handshake/compact block transport, accepted/rejected V2 mempool transactions, ordered disconnect/connect plus wallet/Chronik parity, and block/header storage/reindex restart. The present inherited scripts do not demonstrate those paths.
5. Expand execution only after the shared startup blocker is resolved. Publish pass/fail/not-run script and variant counts without conflating bespoke native harness results with inherited suite results.
