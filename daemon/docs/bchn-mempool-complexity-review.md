# BCHN mempool and optional interfaces at current tip

Acceptance revision: `abd433abe04f74780744b9eac06731f3690ce68a`.
This is a source/history audit; native evidence for the separate diagnostic
candidate is recorded below. No production workspace or node is changed.

## Admission is not the old quadratic ancestor-statistics algorithm

`CTxMemPool::addUnchecked` (`src/txmempool.cpp`) inserts a transaction, indexes
its inputs, deduplicates direct parent TxIds, and updates direct parent/child
links. It does **not** walk all ancestors or update all descendant statistics.
`AcceptToMemoryPoolWorker` in `src/validation.cpp` applies input, fee, script,
sequence-lock and token checks without ancestor/descendant count/size limits.

This is not literal O(1) admission: input/script work depends on transaction
size; the modified-feerate and entry-id indices are ordered indices, and parent
sets/input maps also have ordered-container costs. For fixed-size transactions,
ordinary insertion has logarithmic index costs rather than work proportional
to chain depth. Claiming an O(1) patch or porting the old ABC chain-limit test
would misrepresent current BCHN.

Original upstream changes (all present in the acceptance revision):

- `086009e7f1c5e86694bc1ca5c345aca2258226bf` (2021-04-07): topological entry-id
  index and reorg clear/reaccept invariant.
- `0ce476c4a251daf9ec21953eb5042125bea99946` (2021-04-10): removal of quadratic
  ancestor/descendant fee statistics, with activation logic.
- `bf6e231626f0463c61602e2b815564aa913236ae` (2021-04-22): block removal and
  general mempool optimizations.
- `44150d7ed46b2e3f662d3e71650ce5006e3b3833` (2021-05-24): removal of unused
  ancestor/descendant limits and their arguments after activation.

## Removal and reorg

`CalculateDescendants` uses a visited set and pending set. A removal traverses
reachable descendants and direct graph edges, with ordered-set costs. It does
not independently traverse every descendant of every removed transaction.
`UpdateForRemoveFromMempool` severs direct links, and `removeUnchecked` removes
input indices. Work scales with removed transactions, incident edges and inputs.

`removeForBlock` uses `DisconnectedBlockTransactions::addNoLimit` to sort block
transactions before removing them. That helper uses salted hash maps and Kahn's
algorithm, deduplicating repeated parent inputs. Its topology work is expected
O(n + inputs + edges), excluding subsequent container/index costs. Reorg imports
the pool and reaccepts transactions topologically once after unwinding, rather
than recalculating transitive statistics after every disconnected block.
Repeated reorgs, repeated explicit RPC queries and repeated pressure evictions
can still cost repeated work; none of this proves a universal linear node bound.

## A real remaining quadratic diagnostic path

Original `CTxMemPool::check` computes the full ancestor set of **every** pool
entry. A length-n chain entails n(n-1)/2 ancestor visits, excluding set costs.
It then processes a retry queue in hashed TxId order, which can repeatedly
postpone children until their parents have been applied. This is diagnostic
work, not ancestor maintenance during normal admission. It is disabled by
`nCheckFrequency = 0` by default; explicit `-checkmempool` and regtest/test
settings can enable it.

The independent `04-topological-mempool-check.patch` traverses the existing ordered
`entry_id` index. Each direct parent already has an asserted smaller entry id;
that proves transitive ancestor order by induction. Parents are applied to the
check's scratch coin view before children, so both the transitive walk and
retry queue are redundant. It retains input existence, output index, parent and
child links, topological ordering, input-index pointers, fee/size totals, cached
memory and scratch-UTXO consistency checks. It changes neither admission policy
nor transaction selection. Per check, graph work is one transaction/input/edge
pass with existing lookup/set costs and transaction validation costs, rather
than all ancestor sets. Running a whole-pool check after each of n admissions
still entails at least quadratic total work; this patch does not claim otherwise.

The native regression fixture creates a 512-transaction chain with two inputs
sharing each parent, verifies the hashed index is not topological, checks the
whole pool, recursively removes half the chain, checks the retained prefix,
then removes the remainder and checks the empty pool. Existing tests cover
additional mempool shapes. This fixture validates preservation of correct
behavior; no failure-before/success-after claim is made for a performance-only
change.

## Other candidates

- **Mining:** assess separately against BCHN's current direct-parent counter,
  skipped-child set and fee-ordered queue implementation. The old Core package
  assembler assumptions are not a valid baseline. Preserve BCHN's CTOR,
  sigcheck, token/upgrade context, generated-size and time-limit behavior.
- **NNG:** not present. A source port needs independent event/message/lifecycle
  design and subscriber tests; it must not depend on mining or admission changes.
- **ZeroMQ:** independently disable with `-DBUILD_BITCOIN_ZMQ=OFF` today. The
  guarded init/shutdown code, publisher flags, notification classes and RPC
  integration then do not provide publishers. Complete source removal would be
  a deliberate compatibility/interface deletion, not a complexity fix. Retain
  build-disable unless a distinct removal submission is desired; NNG does not
  require deleting ZeroMQ.
- **Chronik:** absent from BCHN. ABC's Rust/C++ bridge, notifications, transaction
  types, build dependencies and database/API behavior need a substantial port.
  No clean application/build/runtime claim is made.
- **Finalized mempool ancestors:** ABC candidate 04 is not directly portable.
  BCHN finalizes **blocks** through `FinalizeBlockInternal`; it has neither
  Avalanche transaction-finalization semantics nor the matching callback/cache.
  Removing unconfirmed parents based on a borrowed callback would violate
  BCHN's consistent-mempool invariant without a separately designed mechanism.
- **Coinbase vanity height fix:** Lotus-specific consensus rules; not a BCHN
  patch. Likewise Lotus header, TxId, issuance and Taproot changes are irrelevant.

## Validation

The source candidate is commit `7044757349c66076c370330f6172010cc7ecc9f3`,
final tree `05ca138c5a926581de0006aad4b0450f5f5c5590`. Clean independent
`git am` replay on the exact base reproduces that tree. Native Apple arm64
CMake/Ninja `test_bitcoin` build and all 126 emitted `check-bitcoin` suites pass.
The complete `mempool_tests` suite also passes. No source instrumentation is in
the exported patch; the source was restored to the committed tree and rebuilt.

Temporary counters in the actual native implementations give:

| Pool size | Original entry visits | Original ancestor visits | Patched entry visits | Patched ancestor visits |
| --- | ---: | ---: | ---: | ---: |
| 512 | 512 | 130,816 | 512 | 0 |
| 256 after recursive removal | 256 | 32,640 | 256 | 0 |
| 0 | 0 | 0 | 0 | 0 |

Original counts exactly equal n(n-1)/2. The same fixture passes both versions:
this is removal of redundant diagnostic work, not a previously invalid block or
transaction. A preliminary unfiltered all-tests process was cancelled and
superseded by the official separated-suite `check-bitcoin` run; it is not a
successful full-run result. Timer tests intentionally sleep, so quiet periods
in their output do not indicate a failure.

Local evidence logs (2026-10-14):
`/tmp/lotus-bchn-mempool-check-build-20261014.log`,
`/tmp/lotus-bchn-mempool-check-native-tests-20261014.log`,
`/tmp/lotus-bchn-mempool-check-check-bitcoin-20261014.log`,
`/tmp/lotus-bchn-mempool-check-counter-{original,fixed}-20261014.log`, and
`/tmp/lotus-bchn-mempool-check-restored-test-20261014.log`.

Clean application, build, functional behavior and performance are separate
claims. No wall-clock speedup, successful full-chain sync, complete NNG/Chronik
port or new published release is claimed here.
