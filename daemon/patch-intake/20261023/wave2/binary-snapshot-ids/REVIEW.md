# W2-5 binary mempool snapshot edges — read-only review

Reviewed shared `fec2cab9ce9d8f2ba2bb451ce2bdcdc3a7897830` through Git object reads in existing canonical source repository. Native override audit uses preserved native `a8e0eefd3e8f90120229cf7d12ed4100ddec8726`; implementation must additionally inspect the exact native candidate allocated by root. No source/current-checkout changes, new worktree, build/test/benchmark or remote actions. This report is uncommitted for root staging. W2-6/7 are outside scope.

## Small independent change

Change `node::MempoolEntrySnapshot::{depends,spentby}` from `vector<string>` to `vector<TxId>`. Capture IDs directly, keep topology joins binary, and call `ToString()` only when producing RPC/REST JSON. This is generic shared-engine data representation work; no native consensus dependency or public schema change is needed. It can be independently implemented/tested after lane allocation. Do not bundle graph algorithm, graph-publication, admission, lock-scope or snapshot-memory-reuse changes.

## Producers, propagation and consumers

All shared references below use the fixed shared revision.

| Surface | Current behavior and required edit |
|---|---|
| `src/node/snapshot.h:43–56` | Struct defines two string vectors. Replace with `vector<TxId>`, retaining names/default empty state. Header already exposes TxId via existing includes; explicitly verify include sufficiency rather than add native headers |
| `MakeMempoolEntrySnapshot`, `src/node/snapshot.cpp:176–207` | Sole real shared edge producer. Parents use `set<string>`/`ToString` to deduplicate/sort; children iterate live unique child set and stringify. Reserve vector capacity and copy `GetId()` directly. Parents/children are already unique TxId-sorted sets (`src/kernel/mempool_entry.h:30–39,68–73`), so direct iteration preserves unique edge semantics without temporary set/string allocations |
| `CaptureMempoolEntriesLocked`, `snapshot.cpp:210–243` | Full capture or changed-leaf remove/reinsert makes immutable snapshots. No field-specific adaptation needed. Preserve delta marking/publication and locking: `CTxMemPool::UpdateChild/UpdateParent`, `src/txmempool.cpp:1256–1274`, mark affected entry IDs |
| `ImmutableMempoolEntry`, `snapshot.h:108–133` | Takes whole entry by value/move into const leaf. Implicit entry copy/move owns vectors automatically; no serializer/custom ABI or manual allocation size requires a new field adapter. Slab leaf size is obtained through `sizeof`, while vector element allocations remain ordinary vectors |
| `EnsureMempoolVectors`, `snapshot.cpp:333–349` | Copies complete leaf entry into lazy vector then sorts entries by TxId. Binary edge vectors copy automatically; no extra materialization/string conversion. Historical leaf contents remain immutable |
| `GetMiningTemplate`, `snapshot.cpp:480–515` | Topological fallback uses `unordered_map<string,size_t>`, stringifies entry TxId, then looks up string parents. Replace with `unordered_map<TxId,size_t,SaltedTxIdHasher>`, `entry.txid` and binary parent keys. Keep missing count, absent-parent behavior, selection priorities, fitter checks and CTOR sorting unchanged. Optional `reserve` is routine but do not rewrite scheduling |
| `entrySnapshotToJSON`, `src/rpc/mempool.cpp:447–471` | Change loops to `const TxId&` and emit `dep.ToString()` / `child.ToString()`. Preserve array types, member names and order. Keep conversions at this boundary |
| RPC routes | `MempoolToJSON:487–507` is verbose getrawmempool; `getmempoolentry:746–768` uses same adapter. REST `src/rest.cpp:709` calls verbose MempoolToJSON and inherits adapter. Nonverbose mempool output already uses binary snapshot txids and remains unchanged |
| Locked live RPC adapter | `entryToJSON`, `rpc/mempool.cpp:410–444`, separately builds JSON from live entries for ancestor/descendant verbose paths (`:657,:731`). Leave its string output/dedup untouched. It is a useful independent comparison oracle, not another snapshot-edge producer |
| JSON descriptions | `MempoolEntryDescription`, `rpc/mempool.cpp:372–407`, declares depends/spentby as arrays of `STR_HEX`. Keep unchanged; no new binary wire/protobuf/storage format |
| Test/default construction | `snapshot_rcu_tests.cpp:47` and `txrelay_tests.cpp:699` default-construct entries without explicit edges. Empty `vector<TxId>` preserves behavior. Existing historical test at `snapshot_rcu_tests.cpp:297–344` asserts edge **counts only**; strengthen it to exact binary IDs without weakening current checks |

`git grep` for member accesses found no additional shared depends/spentby consumers beyond producer, mining fallback and JSON adapter. Generic copies described above are intentional propagation, not extra conversion sites. `CloneChainStateOnly` copies chain fields and later capture initializes mempool state; it does not manually copy edge fields. `MiningTemplateSnapshot` custom copy/assignment (`snapshot.cpp:379–404`) does not contain MempoolEntrySnapshot edges and needs no change. No tracked serialized binary snapshot schema uses these member fields.

## Ordering detail and regression risk

Preserve current output ordering, not just sets. At this shared revision, `TxId` ordering delegates to numeric most-significant little-endian-word/byte comparison (`src/uint256.h:52–78`), while `GetHex` reverses raw bytes into fixed-length hex (`src/uint256.cpp:10–15`). Thus TxId order matches lexicographic canonical 64-character displayed hex at this revision. Existing parent/child sets already use this comparator. Direct set iteration therefore preserves both parent string-set order and child-set order exactly. Do not replace it with raw `memcmp`/byte order or entry-ID order. Add an explicit adversarial ID-order fixture so future comparator refactors cannot quietly reorder JSON.

Native baseline has additional string consumers; a shared-only type change must not be described as fully native-integrated until these overrides are adapted:

- Native `MakeMempoolEntrySnapshot`, `src/node/snapshot.cpp:140–172`, stringifies parents and children and explicitly string-sorts spentby. Change to binary IDs; preserve its displayed order at JSON boundary if comparator differs on the final native chain.
- Native incremental vector path `:299–357` declares `vector<pair<TxId,string>> parent_spentby_updates`, stringifies child IDs, then inserts with `upper_bound`. Change pair to `pair<TxId,TxId>` and use exact chosen binary order consistently. Preserve existing uniqueness/merge behavior; do not fix unrelated duplicate handling here.
- Native mining fallback already has a binary locations map but reparses string parent IDs using `TxId(uint256S(parent))` (`:672–685`); remove parsing and use parent directly.
- Native snapshot JSON adapter is the corresponding override in `src/rpc/mempool.cpp`; convert IDs at output boundary. Whole-entry copies/reuse/count checks (`native snapshot.cpp:387–405`) remain automatic.

Historical native owner commits touching these files include `fc2b9c7e90` (RPC adaptation), `f796c4dee8` (native snapshot metadata), and `a8e0eefd3e` (persistent Merklix snapshots). Keep generic field/type/producer/mining/JSON work in shared; replay/adapt only these native override hunks atop its exact resulting tip. No new native feature commit should duplicate shared conversion logic. Root must apply the active source review gates; this report does not authorize stack replay or relocation.

## Implementation and meaningful validation plan

One small shared source commit can atomically update the header, sole producer, mining map and JSON adapter plus focused tests. Compile affected daemon/unit targets with zero new warnings, then run affected snapshot, RPC mempool and snapshot mining tests. Check source search confirms no topology `.ToString()` or hex reparsing remains for these fields. Do not add tests that merely assert the vector element type; prove behavior:

1. Extend the historical lazy snapshot chain test to compare each `depends/spentby` to exact parent/child `TxId` values after writer mutation/clear, preserving current count/fee/unbroadcast assertions. Include fork/diamond and two inputs from one parent to ensure one parent edge rather than input multiplicity.
2. Add RPC parity fixture with several parents and several children, IDs ordered differently by raw bytes versus displayed hex, leading-zero IDs where controllable, and graph mutation/removal. Assert arrays remain lowercase 64-character strings, exact sorted order and unchanged duplicates/empties. Compare verbose getrawmempool and getmempoolentry; relevant REST behavior can use existing `interface_rest.py:467–468` plus focused coverage if needed.
3. Exercise mining **fallback**, not only the CTOR all-fit shortcut: parent below child priority, fork/diamond, resource limit excludes a parent and therefore its descendant; assert same selected transaction identities/order, fees and sigcheck totals. Use existing snapshot mining fixtures and disable/defeat all-fit precondition explicitly. Missing-parent behavior is preserved, not redefined.
4. Run existing `snapshot_rcu_tests`, affected `rpc_snapshot_mining_tests`/`rpc_snapshot_read_tests`/`rpc_rawtransaction_tests` suites as registered, and targeted functional `mempool_packages.py`; `mempool_expiry.py` and `interface_rest.py` supply additional edge consumer regressions when host availability permits. Existing package functional checks compare immediate ancestor/descendant arrays (`test/functional/mempool_packages.py:64–87`). Tests have not been run by this read-only lane.
5. After shared review, adapt native override hunks in a separately owned native lane on exact shared tip and run native snapshot/RPC/mining gates, including append-only delta parent spentby updates and native fallback parsing removal. Root owns lane/recovery/checkpoint decisions.

No benchmark claim is justified by this review. The concrete intended effect is removing hex allocation/storage and binary↔hex round trips from internal snapshot graph capture/mining while preserving public JSON byte representation and historical snapshot semantics.
