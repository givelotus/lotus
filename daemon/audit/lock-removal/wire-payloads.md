# Audit: retained wire bytes and shared network payloads

Repository: `daemon/lotusd`. Commits: `39c96054f6`, `96b3326973`, `4ff6454942`.

**Scope limits.**

- The named ref `origin/archive/merklix-snowball-20261024` does not exist in this clone. The commits were audited by hash; they are reachable from `origin/snowstorm/rateless-fountain`.
- This is a static review only. Nothing was compiled or run, so "confirmed" means traced line by line through the code at that commit, not reproduced.
- All `file:line` references are at the commit under discussion.

| Commit | Verdict | Tier | Main reason |
|---|---|---|---|
| `39c96054f6` retain wire bytes | **fix** | mixed | "Canonical" is false for V7 outputs with the top value bit set. Memory cost is unmeasured and silently changes limits. |
| `96b3326973` shared payloads | **pass** (minor cleanups) | shared | Send paths, lifetime and framing are correct. The checksum store is dead code and the send path has no test. |
| `4ff6454942` deferred index, direct format | **fix** | shared, but split it | A late index add can resurrect a removed txid. Four unrelated changes, no tests. |

---

## 39c96054f6: retain immutable wire bytes on CTransaction

**Tier: mixed.**

- The retention code (`Offsets`, `Place`, `Serialize`, accessors) uses no V2 types and changes no wire bytes. It is safe on the legacy grammar, because that decode is injective (see "Checked and correct").
- Move to the V2 tier, or rewrite:
  - The test uses `lotus::v2::BranchWitness`/`Output` and a version 7 fixture. A shared-tier test needs a legacy fixture, with the V7 case kept in the V2 tier.
  - The RPC hunk sits on `lotus::v2::RunParallelSigningWork`. It is also unrelated to the subject and should be its own commit.
- `m_wire_data` is absent from `daemon/ecashd` HEAD, and `ecashd` uses its own decoder executor at this site.

### Confirmed defects

**F1. Retained bytes differ from re-serialization, and two different wires share one TxId and TxHash. Severity: High. The root cause predates this commit (`8eed51051f`); this commit is what breaks the "canonical" claim.**

Code path:

- `primitives/transaction.h:425` reads `out.value` as a raw u64, with no range check.
- `primitives/transaction.cpp:161` does `out.nValue = static_cast<int64_t>(o.value) * SATOSHI`, so any value >= 2^63 becomes negative.
- `primitives/transaction.h:546` and `primitives/transaction.cpp:104` clamp with `std::max<int64_t>(0, nValue / SATOSHI)`. Re-serialization and `ToV2Output()` therefore both produce value 0.
- `Valid()` in `lotus_v2/output.cpp:76` has no value check, so `EncodeOutput` accepts this at decode time.

Consequences:

- A wire T' with value `0xFFFF…` retains those attacker bytes (`transaction.cpp:705`), while `SerializeTransaction` on the same object would emit value 0. This is the one non-injective field in either grammar.
- Through the slow identity path (`transaction.cpp:459`, `ComputeTxIdentities` over `ToV2Transaction()`), T' gets **the same TxId, TxHash and outputs root** as the honest T with value 0.
- The fast path (`transaction.cpp:422`) hashes the raw value through `scriptPubKey`, so fast and slow identities disagree for T'. They also disagree with `CMutableTransaction::GetId()`, which is always slow. T therefore has to take the slow path: any witness with siblings, more than one witness, a coinbase, more than 16 inputs or outputs, or any non-simple output.

Failure scenarios, given a T with a zero-value output on the slow path:

1. **Reject poisoning.** A peer sends T' in a `tx` message. `bad-txns-vout-negative` causes `ProcessInvalidTx` to run `m_recent_rejects.insert(txid)` (`net_processing.cpp:5638-5668`). The node then refuses to download the honest T until the tip changes.
2. **Compact-block poisoning.**
   - The same path stores T' in `vExtraTxnForCompact` (`net_processing.cpp:5672`, `maybe_add_extra_compact_tx=true` at `:5873`).
   - `blockencodings.cpp:126` matches it by `GetHash()`, so a compact block containing T reconstructs with T'. The merkle root still passes.
   - `FillBlock` returns `READ_STATUS_CHECKBLOCK_FAILED` (`blockencodings.cpp:198`). The handler removes the request and calls `ProcessBlock` (`net_processing.cpp:~8215`), and that attempt is lost.
3. **Mutated full block.** A peer can serve a block with an unchanged header hash that fails `CheckBlock` with `BLOCK_CONSENSUS`, not `BLOCK_MUTATED`.

Limits on the damage:

- **Not a permanent chain split.** `ProcessNewBlock` runs `CheckBlock` before `AcceptBlock` and does not mark the index failed (`validation.cpp:8975-8989`). Recovery is a re-download, so block delay is the effect in scenarios 2 and 3.
- T' is rejected by `CheckTransactionCommon` (`consensus/tx_check.cpp:~46`) before mempool or disk on the paths traced: `tx` handling, `CheckBlock`, and `HandleShortTx` as far as admission. I found no path that relays or stores these bytes.

Suggested fix:

- In `UnserializeTransaction`, throw if `out.value > INT64_MAX`. Prefer the same bound as consensus for non-token outputs, or at least make this one injective.
- Remove the clamp in `ToV2Output` and in the serializer, so a lossy mapping cannot exist.
- Add a `DEBUG_ASSERT`-style check in `Place` that the retained bytes equal `SerializeTransaction` output.
- Add a regression test: value `0x8000000000000000` must fail decode, and T and T' must never share an identity. This changes consensus decode behaviour for values that are already invalid, so it needs consensus review.

**F2. Retention silently changes byte-budgeted limits. Severity: Medium.**

`GetStorageSize` (`transaction.cpp:627`) now includes the wire bytes and feeds `RecursiveDynamicUsage` (`core_memusage.h:47`). Two consequences:

- Mempool entries (`kernel/mempool_entry.h:109`) count more per transaction, so `-maxmempool` holds fewer transactions with no notice.
- The compact extra-pool gate `RecursiveDynamicUsage(*ptx) < 100000` (`net_processing.cpp:5672`) now passes only transactions of roughly half the former size.

Estimated cost (struct sizes computed by hand, about 136 B for `CTxIn` and 160 B for `CTxOut`, not measured):

| Transaction | Wire | Storage before | Storage after |
|---|---|---|---|
| Legacy 1-in-2-out | 226 B | about 456 B | about 682 B (+50%) |
| Legacy 2-in-2-out | 374 B | about 592 B | about 966 B (+63%) |

- Nothing is freed in exchange. Long scripts are held in the slab tail and in the wire. V7 witnesses, branches and paths are held in heap vectors and in the wire.
- `CBlock` memory grows the same way, and transactions above about 4 KiB total move from slab to heap. A cached block is then held in `BlockMessageCache` as well.
- W2-8 asked for the memory trade-off to be audited; the commit has no measurement.

Fix: measure it, then either raise or rescale the budgets deliberately, or remove the duplicated fields.

### Suspicions and low-severity notes

- **Dead field, implicit size invariant (Low).**
  - `Layout::serialize_size` (`transaction.cpp:708`) is never read. `m_serialize_size` is recomputed in `InitHashes` (`:454`, `:465`).
  - The retained span length and `GetStorageSize()`, which is used for deallocation in the owned path, both depend on that recomputed size equalling `wire.bytes.size()`.
  - I could not find a violation: compact sizes are canonical and all V7 fields are fixed width or round-trip. The fast-path total matches the wire layout.
  - But a future mismatch would truncate the span and free to the wrong slab class. Add an assert.
- **Constructor exception leak (Low, appears unreachable, predates this commit).**
  - If `InitHashes` throws inside `CTransaction(const Layout &)` (`transaction.cpp:731`), the placed `CTxIn`/`CTxOut` are not destroyed and their heap vectors leak.
  - I compared `UnserializeTransaction` with `ComputeTransactionIdentities`, `InputWire` and `Valid`, and found every failure condition already rejected at decode. Non-simple outputs fail through an empty `scriptPubKey`. So no wire input appears to reach this.
  - The same applies to `MakeTransactionRef(wire)` outside the `try` at `rpc/mempool.cpp:1272`.
- **Scratch growth (Low).** `decode_one` uses the thread-local `TransactionScratchBuffer` (`rpc/mempool.cpp:~1249`), which never shrinks. One huge hex element keeps that capacity on each worker thread. RPC-authenticated only.

### Checked and correct

- **Non-canonical encodings, other than F1.**
  - `ReadCompactSize` rejects non-canonical forms (`serialize.h:469-487`).
  - Legacy `Amount` round-trips raw. Legacy TxId is `SHA256d` of re-serialization, equal to the wire.
  - All other V7 fields are stored and re-emitted exactly. Path indices fit in `u8`, since both limits are 16.
- **Constructors and placement.**
  - Mutable path: `SerializeWire` runs `CheckV7TransactionFields` first, so bytes match fields. This includes the V7 output with an empty `scriptPubKey`.
  - Default and `MakeTransactionRef()` have no wire and use `SerializeToScratch`.
  - There is no copy, move or mutation: copying is deleted and the fields are const.
  - `wire.bytes` may alias the scratch buffer, but nothing in `Place` writes to it.
- **Hashing.** No identity is hashed from retained bytes except through F1's fast path. `SizeComputer` stays special-cased, and other streams only need `write`.
- **A peer cannot pin its receive buffer.** `memcpy` gives every transaction its own allocation, and `TransactionWire` spans only live during the synchronous build, including `DecodeShortTxResponse`.
  - Retention by peers is limited by existing count-bounded pools.
  - The orphan size cap is implied by `test/orphanage_tests.cpp:181`, but I did not locate its implementation at this commit. Not determined.
- **RPC hunk.** `get_str` on a non-string inside a worker is captured and rethrown by `ParallelRangeExecutor`, so there is no `terminate`. Hex, empty and trailing-byte handling matches `DecodeHexTx`.

### Tests

The new test (`test/transaction_tests.cpp:2373`) fails without the change, at minimum by not compiling. It covers only canonical round trips, so it cannot detect F1. Nothing tests the RPC decode rewrite.

---

## 96b3326973: share pre-serialized payloads

**Tier: shared.**

- No V2 types, and bytes on the wire are unchanged.
- The one-line `P2PV2TransportSerializer` hunk (`net.cpp:1165`) has no target on `ecashd` HEAD; drop it when porting there.

### Findings (none block)

- **Dead store (Low).** `net.cpp:1196` writes `msg.m_checksum` on a message that dies in `PushMessage`. `NewPoWValidBlock` copies from `lazy_ser` (`net_processing.cpp:3721`, `:3737`) without a checksum, so each V1 peer still hashes the shared payload. Fix: compute the checksum once when building the lazy message or inside the first `Copy()`, and delete the store. On P2P-V2 there is no checksum at all.
- **`Copy()` mutates through `const` (Low, API hazard).**
  - `net.h:170` and `:179` write a `mutable` member, and `Copy()` is called through `shared_future::get()`, a type that implies safe concurrent reads.
  - Today there is only one caller thread (`ForEachNode` under `cs_main`, on a function-local future), so there is no race.
  - Also, changing `data` after the first `Copy()` makes `Payload()` return stale bytes. No such caller exists.
  - Fix: make the conversion explicit, or move `data` into a `shared_ptr` when the message is built. That also removes the extra copy that `make_shared(data)` makes while `data` stays alive.
- **`.data` is empty on copied messages (Low).** Production has no such reader: seeder and `ReceiveMsgFrom` (`test/util/net.cpp:90`) use messages that were never `Copy()`d. A future test passing a `Copy()` would silently send nothing.

### W2-9 concerns, answered

| Concern | Answer |
|---|---|
| Copy users | Only two production `Copy()` sites plus `PushBlockMessage` (`net_processing.cpp:4586`). All use `Payload()` afterwards. |
| Checksums | The V1 serializer hashes `Payload()`; precomputed checksums are still honoured. |
| Transports | V1 and P2P-V2 use `Payload` / `PayloadSize`. `SocketSendData` uses `CSendChunk::data()/size()`, with `nSendOffset` and `nSendSize` unchanged. |
| WebSocket, zstd, QUIC | `WebSocketSock::Send` (`net_websocket_sock.cpp`) takes `const` bytes and copies or compresses them into per-peer buffers. `QuicPeerSock::Send` (`net_quic/quic_peer_sock.cpp:392`) copies into `m_assembling`. No `const_cast` in those files, so the shared buffer is never masked or mutated. |
| Encryption | Per-peer TLS sits below `Sock::Send`, on the copies. Only plaintext is shared. There is no per-peer payload encryption in `net.cpp`/`net.h`. |
| Async lifetime | The chunk holds a `shared_ptr` until fully sent and erased. The send layers do not retain pointers after returning. |
| Pinning | A stalled peer can hold an evicted block outside the `BlockMessageCache` byte bound, but `fPauseSend` still applies per peer (`nSendSize` counts the full size). Total memory is never above the previous per-peer copies, so this is an improvement. |
| Size limits | Unchanged; there is no send-side limit and `uint32_t` length was already there. |

### Tests and what I could not determine

- `precomputed_checksum_is_used` (`test/net_tests.cpp:2462`) fails without the change. No test sends a shared chunk through `SocketSendData`, covers partial sends, or runs across WebSocket framing or cache eviction. Add one.
- **Could not determine:** whether every test using `vSendMsg` chunks compiles against `CSendChunk`, because nothing was built. `outbound_chunks.assign(...)` (`test/v2_protocol_handler_tests.cpp:1537`) relies on the implicit conversion and looks valid.

---

## 4ff6454942: deferred index, direct getrawmempool

**Tier: shared.** No V2 types or rules in the hunks, but the commit bundles four changes and only two are in its subject.

Split into:

1. Relay index deferral.
2. Direct `getrawmempool` formatting. This depends on `m_tx_tree`, `forEachTopChildBorrowed` and `setRawArrayStr`, which are absent from `ecashd` HEAD.
3. RCU re-entrancy (`rcu.h`).
4. Early relay in `submitrawtxbatch`.

### Confirmed defects

**F3. A deferred add can run after the removal and resurrect the txid. Severity: Low to Medium.**

- `DrainRelayQueue` calls `AddTxIdBatch` (`net_processing.cpp:4610`) up to a relay tick after admission, with no mempool check.
- If the transaction was mined, evicted or conflicted in that window, `Remove` runs first and the later `AddUnlocked` reinserts it (`net/txrelay_index.cpp:229`, `:312`).
- During an epoch rebuild, `RecordEpochChange(txid, true)` replays that stale add into the new epoch.
- Result: a stale short-id entry until the next epoch, wrong `known` partitioning for that id, and wasted requests. It clears when the epoch rotates. The old `AddBatch` had the same ordering problem but only for a very short window.
- Fix: drop the deferred add (see F4) or check mempool membership in the drain.

**F4. The deferral does not remove the work it claims to. Severity: Low (performance).**

- `TransactionsAddedToMempoolBatch` already adds these txids (`net_processing.cpp:907`).
- `AddTxIdBatch` lacks `AddBatch`'s lock-free "already present" pre-check, so it always takes `m_mutex` and walks N entries, now on the message-handler thread during relay.
- The commit moves cost from the RPC thread to the thread that serves all peers. No measurement is included.
- Our own announcements are not affected: the add happens before the announcement loop and before the `targets.empty()` return.
- **Not determined:** whether the validation signal always fires before the drain for batches over 64, where the RPC skips the sync. Either way one of the two adds is redundant.

### Suspicions and low-severity notes

- **Live read not cached (Low).**
  - `FormatMempoolTxIdsJsonArray` (`node/snapshot.cpp:934`, `:964`) reads the live `m_tx_tree` when `entry_tree` is null.
  - Unlike `EnsureMempoolTxIds`, it does not cache, so two calls on one snapshot can differ, and `txids` can drift further from the snapshot's `mempool_sequence` (`rpc/mempool.cpp:~525`).
  - The live read itself predates this commit. **Not determined:** how often `entry_tree` is null in practice.
- **Raw arrays look empty to in-process callers (Low, predates this commit).**
  - `setRawArrayStr` leaves `values` empty. `size()` returns 0 and `write(n>0)` prints `[]`, because the raw branch requires `prettyIndent == 0` (`univalue/lib/univalue_write.cpp:102`).
  - No production path hits this: the RPC reply uses `write()`, `bitcoin-cli` re-parses, there is no Qt in this tree, and `rest.cpp:709` is verbose only.
  - It is also why `RPCResult::MatchesType` no longer inspects these elements.
  - A unit test or tool calling `MempoolToJSON` at 4096 or more entries would see an empty array.
- **RCU re-entrancy (Low, design).** The semantics are right: the inner lock is a no-op under the outer one, and cleanups run only at the outermost release. But it removes the `assert(!isLocked())` guard that caught accidental nesting, changes shared infrastructure outside the subject, and has no test (`rcu.h:63-67`; `test/rcu_tests.cpp` has no nesting case).
- **Early relay ordering (Low).** Relay now happens before result formatting (`rpc/mempool.cpp:1808-1819`). If formatting throws, the client sees an error for transactions already relayed; they were already in the mempool anyway.

### Checked and correct

- **Early relay is equivalent to the old gate.**
  - `AcceptRawTxBatch` returns an invalid state on every per-transaction failure and never emits `MempoolTx` results, so a valid state with full results or all-fast means all accepted.
  - Rejected batches do not relay.
  - `relayed_early` prevents a double relay.
- **Direct format is byte-identical to the previous raw output.**
  - Quoted reversed hex, comma placement (`total*67-1`), same shard order as `EnsureMempoolTxIds`, and `[]` when empty.
  - The array remains valid inside the `mempool_sequence` wrapper.
  - The compact JSON matches `UniValue` output.
- **Other.** `needs_index` defaults to false for the single-transaction path. The executor falls back inline when busy, and `forEachTopChildBorrowed` holds its own RCU lock in each worker.

### Tests

None. Removing any part of this commit would leave every test passing. Needed:

- A remove-before-drain index test.
- `getrawmempool` JSON equality on both sides of 4096 entries.
- An RCU nesting test.
