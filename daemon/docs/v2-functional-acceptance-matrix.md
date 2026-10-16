# Exact-source V2 functional acceptance matrix

Prepared 2026-10-15 from native commit
`09e36f683003db0cc487fd59ed54622bb1f02195`, tree
`7006c765d8000c37da5b3bfcdf0811fd672b512a`, and monorepo base `6fc3862d`.
This is a read-only scheduling and coverage audit. It launches no test or node
and establishes no new passing result. Production workspaces, chain data,
release assets, source and tests are untouched.

The [complete machine-readable inventory](evidence/v2-functional-acceptance-09e36f6830-inventory.json)
classifies every registered path and preserves each registered parameter variant,
source SHA256, purpose, literal options, skip guards and concrete source lines
supporting its fixture/dependency assessment. The registration authority is the
pinned `test/functional/test_runner.py`, whose SHA256 is also recorded.

## Counts and existing evidence

The runner discovers top-level `*.py` files, excluding `combine_logs.py`,
`create_cache.py` and `test_runner.py`. At this pin it registers **292 functional
scripts: 291 inherited ABC scripts and one bespoke SQLite storage script**.
`TEST_PARAMS` expands these to **319 invocations**. The default runner's runtime
cutoff is 40 seconds; a default invocation is therefore not the whole suite.
Explicit selections bypass that cutoff; `--extended` includes all normal tests.

The runner separately accepts **25 `setup_scripts/*.py` paths** when explicitly
selected. Twenty-one have a `__main__` entrypoint and coordinate external client
runs over IPC. Four are helper modules (`__init__.py`, `ipc.py`, `pathmagic.py`,
`setup_framework.py`); they are discoverable names, not standalone acceptance
tests. These 25 paths are included in the JSON, outside the 292-script totals.

| Scheduling category | Scripts | Registered invocations | Required disposition |
| --- | ---: | ---: | --- |
| Valid inherited daemon regression | 158 | 179 | Execute unchanged against the retained V1/ABC control path. |
| Requires upstream network fixtures or assumptions | 125 | 128 | Execute unchanged on the retained path; investigate fixture/protocol mismatches before deciding an adaptation is required. |
| Environment or external dependencies | 8 | 11 | Supply and record the required environment; otherwise retain an explicit blocked/not-run result. |
| V2-specific coverage tracked separately | 1 | 1 | Run SQLite storage unchanged; scope its result to wallet storage. |
| External-client setup registrations | 25 | 25 selectable paths | Run 21 only with their matching JS/TS consumers; retain four helpers as inventory, without manufacturing test passes. |

At this exact native pin, this audit records **0 passed, 0 failed and 292 not-run
functional scripts / 319 not-run invocations**. Those counts describe the
absence of execution in this audit, not a failing product verdict. No cutoff,
missing feature, timeout, category assignment or exit 77 is counted as a pass.

[Earlier inherited functional evidence](v2-abc-functional-audit.md) remains
**7 inherited scripts passed unchanged / 284 inherited scripts not run**, plus
one passing bespoke SQLite script. That executable was built at startup-fix
source `0fce47dc21c0`, SHA256
`fb1926b5ee12b7e003fe9761307c26e1b03874d95513a3651592413b2b36fd4d`.
Its results are historical evidence, not execution of the current pin. Registered
parameter variants were not measured there.

[Earlier full unit evidence](v2-abc-unit-audit.md) records default Boost
147/147, separately registered upgrade runners 147/147 and Avalanche 11/11 at
native audit `4d6bfea595`, with preceding failures and reviewed fixture repairs
retained. Crypto, PoW, UniValue and LevelDB evidence is also scoped there. Those
results must be repeated on the final exact executable/source. The upgrade
runners differ in their runner name/logger settings; they do not independently
force an activation scenario.

## What the classifications mean

The 158 inherited regression scripts exercise retained configuration, startup,
RPC, network, mempool, wallet and storage behavior. Their use of inherited
regtest blocks or transactions does not make them worthless: they are useful
regression coverage for the code that still handles those objects. It also does
not make their results native V2 chain evidence. Wallet creation/encryption,
mempool persistence/reorg, pruning, reindex and block transport remain required
regression work even when they are expensive or exercise legacy objects.

The 125 fixture-sensitive scripts check concrete chain rules, activation times,
script rules, monetary/address expectations, inherited proof/quorum behavior,
or legacy Chronik contracts. This category is a review and attribution gate,
not an exclusion list. Run them unchanged against the intended retained legacy
regtest mode first. For a failure, retain the precise rejection/expectation and
compare the same test with the exact upstream base in a separate controlled
build where necessary. A source-justified Lotus fixture correction requires its
own review and preserves the original failure evidence. Do not rewrite an
assertion just to make a batch green or silently call it unsupported.

Examples of concrete source assumptions retained in the JSON:

- `abc-minimaldata.py` tests pre/post-activation MINIMALDATA acceptance;
  `feature_dersig.py` expects regtest BIP66 activation at height 1251;
  `feature_tx_version.py` distinguishes Wellington rules.
- `chronik_block.py` asserts an inherited genesis size of 285 bytes, a
  5,000,000,000-satoshi coinbase, reversed protobuf hash bytes and legacy
  `/block` behavior. These are unrelated to the native 134-byte header,
  merkleized identities and `/v2/explorer/v1` contract.
- Inherited `abc_*avalanche*`, proof, contender, parking and finalization tests
  use eCash proof/quorum and staking fixtures. Passing them does not establish
  the native V2 observer's funded quorum, parking or finality semantics.
- `p2p_addrv2_relay.py` tests BIP155 address messages; its name does not mean
  Lotus V2. `chronik_token_slp_mint_vault.py` tests SLP V2 mint vaults, not native
  V2 mint selectors. ALP/SLP tests cannot replace native asset event/burn tests.

Every registered source was parsed and inspected for its docstrings, calls,
imports, skip guards and literal options. The inventory is not an independent
proof of every assertion's semantic suitability. Each result still needs its
actual executed chain mode, fixture scope and feature configuration recorded.

## Environment and resource lanes

| Registered scripts | Requirement / remaining work |
| --- | --- |
| `interface_usdt_net.py`, `interface_usdt_utxocache.py`, `interface_usdt_validation.py` | Linux, compiled tracepoints, Python BCC and BPF permissions. macOS cannot satisfy these gates. Use a dedicated isolated Linux job. |
| `feature_bind_port_discover.py`, `feature_bind_port_externalip.py`, `feature_bind_extra.py` | Tests intentionally alter listener/interface binding. Review the actual bind arguments and use an isolated network namespace/container or equivalent approved test host. |
| `rpc_bind.py` base and `--nonloopback` | Linux socket inspection and a non-loopback interface; base also runs non-loopback cases. `--ipv4`/`--ipv6` remain Linux-specific loopback subsets. They do not replace the base/non-loopback variants. |
| `interface_zmq.py` | `BUILD_ZMQ=ON` and Python pyzmq. Earlier candidate config was ZMQ OFF. Build and run a separate same-source feature configuration if the final primary build keeps it OFF. |
| Chronik plugin scripts and setup consumers | `BUILD_CHRONIK_PLUGINS=ON`, compatible Python/PyO3 and plugin fixtures; plugin guards are recorded per script. Chronik ON alone is insufficient. |
| Wallet, CLI and wallet-tool scripts/variants | Wallet ON and the correct configured `lotusd`, `lotus-cli`, wallet-tool paths. Missing tools are blocked dependencies, not successful skips. |
| The 21 setup entrypoints | Matching Chronik client, eCash library/Agora or other JS/TS consumer, its dependency installation/build and IPC lifecycle. Running the Python setup alone is not a completed client test. |

Long tests remain mandatory work. `feature_pruning.py` explicitly warns of 4 GB
of disk use and 30 minutes to two hours. Reserve at least 8 GiB of dedicated free
space and a separate three-hour wall-clock allowance, one script at a time;
retain timeout/disk exhaustion as an operational failure or unrun gate.
`feature_dbcrash.py` intentionally crashes/restarts three of four nodes and has
480-second RPC timeouts. It belongs in a separate crash/recovery batch, not an
omitted category. `wallet_pruning.py`, `feature_assumeutxo.py` and
`wallet_assumeutxo.py` also have dedicated resource lanes in the inventory.
The disk/time allowances are proposed job budgets, not measured bounds on this
candidate. Review available resources with the integration owner before these
runs.

Default framework configuration disables discovery, DNS/fixed seeds, NAT-PMP
and automatic peer connections and binds Chronik to loopback. It also defaults
`avalanchepreconsensusmining=0`. Individual scripts can override defaults. The
framework port base can be changed with `TEST_RUNNER_PORT_MIN`; with MAX_NODES
64 and PORT_RANGE 3000, its initial class base is
`PORT_MIN + class_offset + (64 * seed) % 2935`, with availability retries.
Use a unique temporary root/cache and reserved seeds; record actual listener
ports. Some tests, including `rpc_bind.py`, use explicit fixed ports such as
32171/32172, so the framework port setting alone is not complete isolation.

## Proposed final gates and commands

These commands are proposals for the integration owner. They have **not** been
executed by this audit. Coordinate the coherent build and costly/resource lanes
before launching them; do not build or run concurrently against an active
mutable build directory. All test homes/caches must be freshly named and all
connections confined to their approved test environment.

1. Freeze the exact native checkout/build source and capture build flags,
   generated test config, binary SHA256, startup output and complete unit-runner
   discovery. Use the owner's existing coherent exact-source build or a new
   isolated build; never reuse a binary solely because its filename matches.

   ```sh
   git -C /private/tmp/lotus-v2-native-integration-20261015 rev-parse HEAD
   git -C /private/tmp/lotus-v2-native-integration-20261015 status --short
   cmake --build /private/tmp/lotus-v2-final-acceptance-09e36f6830/build \
     --target lotusd lotus-cli bitcoin-wallet -- -j2
   cmake --build /private/tmp/lotus-v2-final-acceptance-09e36f6830/build \
     --target check-bitcoin check-bitcoin-upgrade-activated check-avalanche \
     check-pow check-secp256k1 check-univalue check-leveldb -- -j2
   ```

   The proposed build path must be configured by the owner before use; it is
   not evidence of an existing directory. Confirm target names from that exact
   build's target inventory before invocation. Preserve per-suite results and
   nonzero aggregate exits. A build/run timeout leaves the affected suites
   explicitly incomplete. Record Rust 1.93.0, Python <=3.13 for PyO3, Chronik,
   wallet, plugin and ZMQ selections. Repeat Rust DB/indexer/HTTP/service tests
   on this exact source as a separate gate, not as part of inherited Boost counts.

2. Repeat the previous small sample unchanged on the exact pin, including its
   registered variants. The following explicit eight-script selection bypasses
   the runtime cutoff and has at most two concurrent scripts:

   ```sh
   TEST_RUNNER_PORT_MIN=38000 /opt/homebrew/bin/python3.13 \
     /private/tmp/lotus-v2-final-acceptance-09e36f6830/build/test/functional/test_runner.py \
     --jobs=2 --failfast --timeout-factor=2 \
     --tmpdirprefix=/private/tmp/lotus-v2-final-functional-smoke-09e36f6830 \
     --cachedir=/private/tmp/lotus-v2-final-functional-smoke-cache-09e36f6830 \
     --junitoutput=/private/tmp/lotus-v2-final-functional-smoke-09e36f6830.xml \
     p2p_compactblocks_blocksonly.py abc_p2p_version_timestamp.py \
     mempool_accept.py mempool_reorg.py feature_blocksdir.py feature_reindex.py \
     wallet_createwallet.py wallet_sqlite_v2.py
   ```

   Invoke the build-directory runner link generated by `test/CMakeLists.txt`:
   its relative `test/config.ini` selects the build, then SRCDIR selects the
   source scripts. Before running, verify that generated config selects the
   exact intended build/daemon/CLI/tool; do not assume a `--configfile`
   pass-through replaces the runner's initial config. The factor of two follows
   the project's own Debug-build functional target; keep it recorded alongside
   the outer job budget. Record separate script and expanded-variant results;
   this selection contains ten registered invocations because createwallet has
   `--usecli` and `--descriptors` variants.

3. Execute the other eligible inherited scripts in explicit batches of at most
   eight scripts, two jobs, separate fresh cache/root/JUnit files and a
   30-minute outer job budget. Feed the next batch from the JSON's
   `legacy_control_path`, then `fixture_sensitive_legacy` lanes. An explicit
   script selection runs all its registered variants. Stop on substantive
   failures, attribute them, and resume the remaining inventory only after
   recording the outcome. Never use the 40-second default cutoff as a final
   completion criterion. Resource-lane scripts use their separate budgets;
   do not remove them from the final denominator.

   Select a reviewable next batch without executing anything:

   ```sh
   python3 - <<'PY'
   import json
   from pathlib import Path
   inventory = json.loads(Path(
       'daemon/docs/evidence/v2-functional-acceptance-09e36f6830-inventory.json'
   ).read_text())
   lane = 'legacy_control_path'  # then fixture_sensitive_legacy
   eligible = [t['script'] for t in inventory['tests']
               if t['registration_kind'] == 'functional_test'
               and t['recommended_batch'] == lane]
   print('\n'.join(eligible[:8]))
   PY
   ```

   Supply those explicit names to the same runner command with a newly named
   root/cache/JUnit file. Track completed scripts/variants separately in new
   execution evidence so later batches advance beyond the first eight. The
   owner/job supervisor must enforce the outer budget and clean up only that
   batch's recorded temporary child PIDs/homes on timeout. Preserve logs before
   cleanup. A timeout is not an assertion failure attribution and not a pass.

4. Complete long-resource, Linux tracepoint/network and feature-matrix lanes,
   and paired external client runs. Use one long-resource or interface job at a
   time. Record exit 77 as skipped/blocked with the observed reason; run the
   compatible feature/host job before claiming that gate passed. The exact
   final result must enumerate every one of 319 registered functional
   invocations, plus separately counted paired client tests.

5. Run native V2 acceptance alongside inherited regression. No ordinary
   inherited script selects the native V2 development protocol. The SQLite
   script explicitly disclaims native chain validation. Require exact-source
   native header/TxID/TxHash/VM/monetary tests, peer transport and accepted/rejected
   pool tests, persistent reorg/recovery, native producer and Chronik sync tests,
   Rust schema-3 DB/HTTP/query/service tests, and actual isolated explorer
   screen/token/restart/reorg process evidence. A native block or native asset
   fixture is not supplied by an ALP/SLP or legacy block test.

   [Explorer integration](v2-explorer-integration.md) and
   [observer process evidence](v2-node-observer-acceptance.md) give existing
   commands/source pins and their limitations. Their earlier-source successes
   must not be silently promoted to this pin. The native observer harness is:

   ```sh
   /opt/homebrew/bin/python3.13 \
     /private/tmp/lotus-v2-native-integration-20261015/src/lotus_v2/node_avalanche_test/check_node.py \
     --node /private/tmp/lotus-v2-final-acceptance-09e36f6830/build/src/lotusd \
     --manifest DEVELOPMENT_MANIFEST \
     --evidence /private/tmp/lotus-v2-final-observer-09e36f6830 \
     --binary-source 09e36f683003db0cc487fd59ed54622bb1f02195
   ```

   `DEVELOPMENT_MANIFEST` must be the owner's authenticated retained fixture,
   with its actual path/hash recorded. This harness does not establish funded
   quorum, finality, parking, conflicting-fork recovery, separate-machine
   operation or native explorer screens; those remain explicit separate gates.

## Acceptance reporting

Publish exact source/build hashes, commands, platform/features, every script and
variant's pass/fail/skip/timeout/not-run status, and links to retained logs.
Preserve the initial 291 inherited denominator even if source-specific fixture
review later authorizes an adaptation. Track original and adapted results
separately. Keep native V2, SQLite storage, inherited legacy, external-client,
unit, and process counts distinct.

Current gaps are the exact-pin unit rerun, all exact-pin functional invocations,
all registered parameter variants at the final source, eight environment-gated
scripts, paired client setups, and the separate native V2 process milestones
not established by the earlier observer/explorer reports. The inventory and
this matrix make those gaps reviewable; they do not declare private-testnet or
release acceptance complete.
