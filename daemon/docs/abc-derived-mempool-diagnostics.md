# ABC-derived optional mempool diagnostic cleanup

The candidate mailboxes are under `daemon/candidates/mempool-diagnostics/`.
They remove only redundant transitive-ancestor verification from the optional
whole-pool consistency check. Each host already traverses its topological
entry-id index, so BCHN's retry-queue removal is neither copied nor needed.

## Preserved invariants and scope

For every transaction input pointing into the pool, the check asserts the
parent exists, its output exists, and its entry id is smaller than the child's.
It reconstructs direct parent/child sets from inputs and input-index pointers,
compares the stored graph links, applies inputs/outputs to a scratch coin view,
and verifies fee, transaction-size and dynamic-memory totals. These checks
remain byte-for-byte intact. The direct-edge id inequality is transitive, so
recomputing every complete ancestor set adds no ordering guarantee.

The chain check previously visits n(n-1)/2 ancestors, excluding set costs.
After removal, graph work scales with entries, inputs and direct edges, with
existing ordered-container and transaction-validation costs. This is not an
O(1) admission change. Mainnet defaults return before diagnostic work;
regtest/tests and explicit `-checkmempool` use it. Whole-pool checking after
every admission still accumulates at least quadratic work.

## Exact application and native checks

Acceptance pins and Lotus release-base details are in the candidate README.
All three independent mailboxes pass both temporary-index application and a
clean `git am` replay, reproducing the recorded source trees.

| Host | Source commit | Source tree | Full mempool suite cases |
| --- | --- | --- | --- |
| ecash | `966c113579022558ba28fba4e85ea068ee3ab59a` | `cde528599703a4b6ae6f57fbcd6c937508759eeb` | 10 |
| v1 | `189fe4553967539fb197128e767ab956ad0b0a15` | `d83b5f33bfd8458619a5236b321c663368c9d780` | 11 |
| doged | `c98d96d0586ed2fce746764a110f6aea6dc99ed2` | `f0582c134f4f0add068ffc6af6003cd3a78609f0` | 10 |

Native Apple arm64 CMake/Ninja builds of the test binaries pass with Chronik
OFF. ABC and Lotus build the exact independent candidate. Doged's raw pin
reproduces its known ambiguous large amount-literal compile failure; the native
validation tree additionally applies its existing two compatibility-series
mailboxes. The literal repair changes only the compression test and the other
mailbox adds a Chronik functional test. Their payloads remain separate and
unchanged; exact diagnostic application on raw Doged is verified independently.
The JSON evidence records the combined native validation tree separately.

The added fixture checks a 512-entry chain whose children each consume two
outputs from one parent, recursive removal to a 256-entry prefix, empty pool,
a diamond with two direct parents sharing an ancestor, partial diamond removal,
and topological reinsertion. It passes the original implementation too:
this is a diagnostic performance cleanup, not a valid-input bug reproduction.
Reinsertion unit coverage is not full chain-reorganization validation.

Temporary counters in the actual `CTxMemPool::check` implementation measured
identical counts on all three hosts:

| State | Entries | Original ancestor visits | Patched ancestor visits |
| --- | ---: | ---: | ---: |
| Full chain | 512 | 130,816 | 0 |
| Retained prefix | 256 | 32,640 | 0 |
| Diamond | 4 | 5 | 0 |
| Partly removed diamond | 2 | 1 | 0 |
| Reinserted chain | 512 | 130,816 | 0 |
| Empty pool | 0 | 0 | 0 |

The counters increment once inside the old ancestor-verification loop and print
one line after each completed check. They are not exported in any patch.
Exact committed source was restored, rebuilt, checked clean, and the full
mempool suite rerun successfully. These are traversal counts, not a wall-clock
speedup or test-suite throughput benchmark.

ABC mining 01/container-test 02 combinations give 11 successful independent
application orders (including this candidate alone). Doged compatibility
combinations likewise give 11 orders, all with order-independent resulting
trees. ABC finalized-ancestor 04 edits the now-deleted block: all 38 tested
orders including both encounter a source-context conflict. Its obsolete check
hunk must be removed in a separately reviewed adaptation; the original 04
mailbox is deliberately unchanged. This overlap is not a policy dependency.

## Reproduce and select

Use only a new isolated clone at the acceptance source. After applying the
host's mailbox with `git am`, configure and build:

```sh
cmake -S /path/to/isolated/source -B /path/to/isolated/source/build -GNinja \
  -DBUILD_BITCOIN_QT=OFF -DBUILD_ZMQ=OFF -DBUILD_CHRONIK=OFF \
  -DENABLE_UPNP=OFF -DENABLE_NATPMP=OFF -DBUILD_BITCOIN_BENCH=OFF
ninja -C /path/to/isolated/source/build -j8 test_bitcoin
/path/to/isolated/source/build/src/test/test_bitcoin \
  --run_test=mempool_tests --log_level=test_suite
```

Lotus uses `test_lotus` and additionally configures `-DBUILD_BITCOIN_NNG=OFF`.
The feature planner accepts `mempool-check` only with `--allow-experimental`
for `v1`, `ecash`, `doged`, and the already-existing BCHN candidate. It selects
no mining, chain-limit, Chronik, NNG or ZeroMQ patch as a dependency. Default
series and the Lotus release manifest stay unchanged; these candidates do not
change the 11.6.1 release source or its artifacts.

Ten feature-planner tests and all 18 patch-maintenance tests pass. The metadata
audit reports 196 real mail patches and four explicitly allowed placeholders.
No mainnet synchronization, complete functional suite, sanitizer run, full
C++ suite or whole-suite speedup is newly claimed for these candidates.

Machine-readable evidence:
`daemon/docs/evidence/abc-derived-mempool-diagnostics-20261014.json`.
Local build/test/counter logs:
`/tmp/lotus-diagnostic-{abc,lotus,doged}-{build,restored-build,restored-tests}.log`
and `/tmp/lotus-diagnostic-{abc,lotus,doged}-count-{original,fixed}.log`.
Doged's successful compatibility build log has the `build-fixed.log` suffix.
