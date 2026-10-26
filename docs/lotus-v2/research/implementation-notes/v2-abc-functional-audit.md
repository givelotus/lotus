# Inherited ABC functional suite audit (2026-10-15)

After the startup repair, **seven inherited scripts and the bespoke SQLite script pass unchanged**. The earlier startup crashes and coherent rebuild reproduction remain below as historical evidence. Current inherited status: 7 pass, 0 observed failures, 284 not run out of 291 distinct scripts. The bespoke SQLite script also passes. These are legacy regtest subsystem checks, not native V2 protocol validation.

## Provenance and isolation

Native test checkout: `/private/tmp/lotus-v2-abc-functional-audit-20261015`, branch `audit/v2-abc-functional-20261015`, exact source `f1c8c92d87023c620819dfc4a6bd88a28c446d46`. Documentation checkout starts at monorepo `48a47753`. No maintained patch, native source, main checkout, production data, or release asset was modified.

Executed daemon: `/private/tmp/lotus-v2-daemon-runtime-staging-20261015/build-chronik-v2/src/lotusd`, SHA256 `6065e9fdd8db763a2d58fa87a7891e4cf03e317b940c5eef84b3328c3249cb54`. Runtime checkout HEAD observed during audit is `f1c8c92d87023c620819dfc4a6bd88a28c446d46`; the parent audit confirms the executable was built from exact source `40d66a7d93b268957ca6b20b703d321a00f522b1` before later driver components. Subsequent builds at f1c8c92d87 rebuilt focused test targets only. The binary therefore does not establish integration of the later driver source.

The existing generated config selects Lotus daemon/CLI names, wallet ON, Chronik ON, ZMQ OFF. CLI executable was absent at initial inspection. These selected tests use RPC, so no CLI rename or source workaround was applied.

Every invocation used a new `/private/tmp/lotus-v2-abc-functional-case-*` datadir and separate cache. `TEST_RUNNER_PORT_MIN=38000`, seeds 41–48, MAX_NODES 64: initial P2P base is `38000 + (64 * seed) % 2935`; RPC adds 3000 and Chronik adds 6000 (remaining framework port classes use further 3000 increments). Exact generated ports are retained in `port-and-isolation-evidence.json`. No 10604, 10605, or 8331. Framework config disables discovery, DNS/fixed seeds and automatic connections (`connect=0`); P2P test connections are local framework peers. Failed processes were cleaned by the framework; `cleanup.txt` confirms zero remaining audit child daemons. No external peers or existing chain data were used.

## Initial measured executions (before startup repair)

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

Initial inherited script counts: **0 pass, 7 blocked/failed launches, 284 not run** out of 291 inherited scripts. New V2 scripts: **0 pass, 1 blocked launch, 0 not run** out of 1. Counts are distinct top-level scripts, not runner parameter variants or individual assertions. Overall: 292 scripts, 8 attempted, 284 not run. No tests were removed, weakened, or skipped to obtain green status.

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

## Coherent rebuild retry

A fresh real clone at exact `f1c8c92d87023c620819dfc4a6bd88a28c446d46` built Debug/Chronik ON daemon, CLI and wallet tool successfully. Fresh daemon `/private/tmp/lotus-v2-abc-unit-audit-20261015/build-abc-audit/src/lotusd` SHA256 `a4b74599175e5ad42e9e1fca20e786e281d3b924bcf20bd8176653356009db8e` still crashes on `-version` (unit audit exit 139). The unchanged SQLite functional script was retried with this exact binary/config, seed 49, and another fresh datadir/cache. It again reports initialization exit `-11`; see `coherent-rebuild-wallet_sqlite_v2.log`. This rules out the earlier runtime checkout/binary provenance mismatch as a sufficient explanation. No further repeated functional startup attempts were useful. Totals above remain counts of distinct scripts; there were nine invocations including this retry.

The lock-debug ABI hypothesis remains unresolved; a fresh build alone did not fix startup. Native V2 harness success reported elsewhere must be scoped to its actual executable and arguments and does not establish inherited legacy startup.

## Successful retry after startup repair

The unit audit applied the exact startup fix as native commit `0fce47dc21c0` on `f1c8c92d87023c620819dfc4a6bd88a28c446d46` and rebuilt the daemon. The change makes Chronik C++ bridge compile definitions agree with Debug lock tracking. Exact original fix is `229c10aa384a78832b28352a015ad00281f0db04`. The unit agent confirmed that later local commits affect test fixtures only; the daemon was built at `0fce47dc21c0`.

Fixed daemon SHA256: `fb1926b5ee12b7e003fe9761307c26e1b03874d95513a3651592413b2b36fd4d`. Fixed CLI SHA256: `28c6d610ae72d44fd9e07e135fa5db60333885f316718ed4efb87b71c19c7616`. Both reside under `/private/tmp/lotus-v2-abc-unit-audit-20261015/build-abc-audit/src/`.

All eight scripts listed above pass unchanged against this executable, with new `fixed-*` datadirs/caches, explicit `TEST_RUNNER_PORT_MIN=38000`, seeds 60–67, and the same disabled external discovery/connect settings. Each script completed normal node shutdown and successful datadir cleanup. `fixed-runs.json` preserves exact commands, return codes and durations; `fixed-*.log` preserves test output. No assertions or expectations were edited.

**Current distinct-script totals:** inherited 7 pass / 0 observed fail / 284 not run; bespoke SQLite 1 pass / 0 fail / 0 not run. Overall 8 pass / 284 not run. Across historical and fixed attempts there were 17 invocations of eight scripts. Runner parameter variants remain unmeasured.

This bounded sample demonstrates useful retained inherited regression coverage: wallet creation, P2P version timestamps and compact block blocksonly behavior, mempool acceptance and reorg, block-directory configuration and reindex. SQLite tests exercise storage, encryption, backup/restore and rejection of incompatible wallet databases through inherited wallet RPCs. Native V2 chain execution, V2 commitments/VM and settlement-specific fixtures remain separate coverage gaps. The remaining inventory classifications are provisional, and the complete suite has not been run.

Follow-up gate 1 (coherent startup) and the eight-script repeat in gate 2 are now satisfied. No substantive inherited assertion failure was observed in this sample, so no upstream comparison or fixture weakening was needed. Remaining work is semantic review/migration of the inventory, explicit native V2 fixtures, and broader inherited execution.
