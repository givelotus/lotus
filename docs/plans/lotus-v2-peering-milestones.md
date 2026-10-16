# Lotus V2 peering implementation milestones

Status: **implementation plan for review, 2026-10-15**. The [peering candidate](../lotus-v2/peering.md) is the protocol contract proposed here. The maintainer selected ABC TCP first, QUIC second, new development netmagic and Lotus port defaults P2P **10605**, RPC **10604**. This plan authorizes no node launch, production parameter freeze or network-code implementation before the specification review gate.

Baseline: monorepo `8914db5177d7b97fa7aa7d04172f71ead633775c`; native ABC `1fb7db17c176cdea8a2c60d887891589382ee4e3` plus 57 patches `000`–`056`, native commit `6a7849b1887bfe814c4e1679d7e01ffedb9a52d8`, tree `9a3e3e57aa6ee0c0430144ee1200ab9cbe48f6e7`. All work belongs on the V2 development branch and isolated replay/build trees. Chronik stays off for these milestones. Preserve V1 workspaces, nodes, data, main checkout, tags and releases.

## Review gate before implementation

1. Review N01–N08 in the peering candidate, specifically message layouts, identity negotiation, full TxHash retrieval, compact reconstruction, the P05 transport-size mismatch and scoped receive-limit negotiation. Record accepted allocations and unresolved changes in a follow-up review; do not silently edit P01–P06 to make a network test pass.
2. Review the concrete [separate development profile proposal](../lotus-v2/development-profile.md), including its reproducible complete genesis, first-block budget and test-only cost schedule. The current fixture's time `0x010203040506`, bits `0x1d00ffff`, previous work 9 and header-only empty body do not establish a usable network. Derive and test valid complete genesis/first-block examples, including resource charges, with separately selected test parameters. Preserve D10–D14 mainnet choices as open; the selected port defaults do not resolve them.
3. Reconcile native validator/chainstate conformance findings from the separate compiler/native audit. Require one deterministic validation path, atomic persistent state/undo and explicit unsupported-stage failures. Network parsing must not be added ahead of a validator that can safely reject and connect peer-supplied blocks.

The specification can be reviewed now. A runnable development-network claim must wait for gates 2 and 3 as well as the TCP acceptance below. No existing passing fixture, compiler test or native primitive build is sufficient evidence of network readiness.

## Milestone 1 — Existing ABC TCP protocol adapted to V2

| Step | Deliverable and code boundary | Acceptance evidence |
| --- | --- | --- |
| TCP-01: isolate identity | Explicit V2 development selection; new reviewed magic; separate datadir/disk schema/address tables; defaults 10605/10604; no inherited seeds/checkpoints/snapshots | Startup rejects wrong-profile/existing V1 data; wrong magic disconnects before dispatch; port conflict fails safely; tests use temporary loopback ports |
| TCP-02: codecs and handshake | Reuse `src/net.*` framing and `src/protocol.*`; add reviewed `v2hello`; dedicated 134-byte header and P01/P04 object codecs; no legacy object conversion | Independent byte vectors, split/coalesced TCP reads, truncated/trailing/noncanonical lengths, oversized frame rejection, identity mismatch and premature/duplicate handshake tests |
| TCP-03: validated full blocks | Adapt headers/locators/in-flight scheduling and work presync; route complete block data through V2 chainstate/undo | Two isolated nodes sync a mined development chain; wrong PoW/target/height/size/root/signature/coinbase reject at intended stage; restart, fork/reorg and missing-parent recovery preserve roots/state |
| TCP-04: receive limits | Negotiate local payload caps; replace legacy block-size-dependent transport limits; preserve whole-object framing | Exact-cap and over-cap cases, asymmetric peer caps, count/length overflow, temporary unavailability and alternate-peer recovery; resource refusal never poisons consensus validity; explicitly report larger-object synchronization limits |
| TCP-05: full transaction relay | TxHash request/cache identity; TxID outpoints/conflicts; V2 fees/costs, orphan and recent-object bounds | Signed compiler payment and token fixture relay; wrong signature variant followed by valid same-TxID variant; absent inputs/temporary locks; duplicate and competing variants; no unbounded cache growth |
| TCP-06: compact blocks | Profile 2 with framed complete transactions, TxHash short IDs, missing-index requests and full-block fallback | Empty mempool, complete/partial overlap, multiple prefilled entries, injected short-ID collisions, same-TxID/different-arguments, bad signatures, request-index overflow/mismatch, duplicate TxIDs, root/size failure and valid full-block recovery |
| TCP-07: peer lifecycle | Address relay, eviction/diversity, connection limits, cancellation and diagnostics; unsupported service handlers disabled | Three-node propagation; slow/malicious peer isolation; reorg during download; no external bootstrap contacts; refusal/invalidity visible separately; clean shutdown/restart with transfers active |

Deliver TCP changes as separate reviewable mailboxes in the V2 series. Record exact base/series/tree and independent replay. Before integration, run targeted unit/fuzz/functional checks and the native build with Chronik OFF; repeat required existing conformance checks when shared serialization or validation changes. Keep port defaults distinct from test-selected ports, and inspect active listeners before any later authorized run.

The milestone is accepted only when complete V2 transactions and blocks pass between isolated nodes, full/compact paths within negotiated capacity yield identical bytes and state, rejected data leaves state unchanged, and independent restart/reorg checks pass. It must report actual chain height, exact parameter artifact, commands, source tree and tests. Do not infer public-network readiness, performance superiority or mainnet parameter approval.

A separate N05 follow-up must resolve delivery of valid objects beyond negotiated limits before general-network claims. A streaming/chunk extension is a research and protocol-review dependency, not a prerequisite for the scoped first TCP milestone. It must preserve P05 validity, bound allocations and handle the existing u32 envelope ceiling explicitly.

## Milestone 2 — QUIC transport with the same V2 application protocol

The inspected ABC source has no QUIC implementation. `src/net_processing.cpp:6841` contains a comment describing QUIC as unimplemented; `src/net.cpp` creates V1 TCP framing objects. Record this source finding in implementation review so no task assumes a hidden reusable QUIC backend.

| Step | Deliverable | Acceptance evidence |
| --- | --- | --- |
| QUIC-01: transport design review | Select a maintained QUIC/TLS library and pinned dependency; approve N07 ALPN, stream mapping, limits and explicit development certificate pins | Dependency/license/platform review, reproducible builds, unsupported-platform behavior, tests for handshake identity and certificate possession |
| QUIC-02: adapter | UDP 10605 default, independent temporary test ports, control stream and request/response bulk streams, bounded queues/flow control | Same codec vectors and application validation outcomes as TCP; early data disabled; pre-handshake stream/data refusal; malformed records, stream resets and shutdown cancellation |
| QUIC-03: network behavior | Retry/address validation, tested NAT rebinding policy, explicit endpoint configuration, TCP fallback policy and route compatibility | Loss, reorder, latency, MTU, UDP blocking, amplification and stream-flood tests; pinned peer mismatch fails; `require-quic` never downgrades; proxy routes retain TCP |
| QUIC-04: integration and measurements | Mixed TCP/QUIC nodes relay and synchronize the same development chain; peer accounting prevents counting duplicate transports as independent peers | Full/compact parity within negotiated limits; reorg/restart; CPU/memory/bandwidth/latency under named workloads; evidence before enabling by default |

Public QUIC discovery/authentication and any removal of Avalanche application signatures require separate review. TLS encrypting a connection does not establish stake authority, consensus validity or independence from another peer. Preserve the working TCP transport throughout milestone 2.

## Milestone 1.5 — Progressive Merklix Mempool Overlays, `tmplblock` Relay, and Avalanche Bulk Pre-Consensus (`Patches 023–034`)

Following the consolidated baseline (`000`–`021`) and Merklix sharding upgrade (`022`), the [bulk pre-consensus and mempool overlays plan](lotus-v2-bulk-preconsensus-and-mempool-overlays.md) specifies a **6-stage, 12-commit incremental implementation sequence (`Patches 023–034`)** that decouples each subsystem into an independently testable patch:

- **Stage A (`023`–`025`): Pure Offline Overlay & Syndrome Primitives:**
  - `023`: In-memory persistent `TxOverlayArena` & `UtxoOverlayArena` (`MempoolOverlayLayer` $L_0 \dots L_k$, sort-merge batch path-copying, by-value `libmdbx` clean sibling/coin copy + `ResetReadTxn()`, in-place epoch folding).
  - `024`: $GF(2^{64})$ power-sum syndromes `(s1, s3)` + per-epoch keyed `SipHash-2-4(TxHash)` 64-bit `short_id` helper.
  - `025`: `DiskStateStore::CommitFinalizedOverlay` direct sorted batch commit to `libmdbx`.
- **Stage B (`026`–`027`): Local Speculative Mempool Overlays & $O(1)$ Block Assembly (Tier 0):**
  - `026`: Attach `MerklixOverlayManager` to `CTxMemPool` (`addUnchecked`, `removeUnchecked`, `ConnectBlockReset`) maintaining $L_0$ and live $L_{\text{spec}}$ + pre-populated `cached_block`.
  - `027`: Overhaul `BlockAssembler::CreateNewBlock` (`src/node/miner.cpp`) to slot `vtx[0] = coinbaseRef` into `overlay->cached_block` and compute `hashMerkleRoot` and `hashStateRoot` in 2 BLAKE3 hashes ($< 2\text{ }\mu\text{s}$).
- **Stage C (`028`): Transaction-Free Block Relay (`tmplblock`) & Candidate Root Match Stage:**
  - `028`: Add `NetMsgType::TMPLBLOCK` (`Header || CoinbaseTx`, ~284 bytes), Stage 1 `MatchCandidateOverlay` (`{L_k, L_{k-1}, L_{k-2}, L_0, L_spec}`), `ConnectMatchedOverlayBlock`, and Stage 2 automatic fallback to `getdata(MSG_CMPCT_BLOCK / MSG_BLOCK)`.
- **Stage D (`029`): Generalized P2P Merklix Mempool Reconciliation:**
  - `029`: Add `merklixsync`, `getmerklixbuck`, `merklixbuck`, `getshorttx`, `shorttx` (`ReconScope`) and `PendingCandidateTracker`, verified standalone in Tier 0 live mempool sync (`ReconScope::LIVE_MEMPOOL_SYNC`).
- **Stage E (`030`–`031`): Avalanche Block Parking, Staking Rewards (`25%`), and Staker-Voted Treasury (`25%`):**
  - `030`: Restore `ParkBlock`/`UnparkBlock` in `ConnectTip` and `avaresponse`, and enable `StakingRewardsPolicy` (`STAKER_REWARD_RATIO = 25%` via `MSG_AVA_STAKE_CONTENDER`).
  - `031`: Add `MSG_AVA_TREASURY_CONTENDER`, `NetMsgType::AVATREASURY`, `TreasuryContenderCache`, `TreasuryPolicy` (`TREASURY_REWARD_RATIO = 25%`), and the `50% Miner / 25% Staker / 25% Treasury` coinbase split in `BuildV2CoinbaseTx`.
- **Stage F (`032`–`034`): Avalanche Bulk Mempool Batch Voting (`MSG_AVA_MEMPOOL_BATCH`) & Causal Epoch Pipeline:**
  - `032`: Add `MSG_AVA_MEMPOOL_BATCH` (`0x20000006`) and `MempoolBatchVoteItem` to `AnyVoteItem`, wiring `avapoll`/`avaresponse` to `PendingCandidateTracker` and `CommitFinalizedEpoch(e, R*)`.
  - `033`: Enable the 3-stage `Ingest -> Mature -> Vote` logical epoch clock, `AbortStaleEpochsBelow(M)` cumulative jump $L_{N-1} \to L_M$, `finalized-tx-conflict` in `MemPoolAccept::PreChecks`, and `PreConsensusPolicy` in `ConnectTip`.
  - `034`: Retire superseded per-tx `finalizedTxs` (`RadixTree`) and legacy `BlockAssembler` per-tx poll loop.
- **Stage G1 (`035`–`036`, Upstreamable ABC): C++20 `Boost.Asio` Coroutine HTTP/RPC Engine (see [`lotus-v2-rpc-coroutines-and-lockfree-snapshots.md`](./lotus-v2-rpc-coroutines-and-lockfree-snapshots.md)):**
  - `035`: Replace the 4-thread blocking `WorkQueue<HTTPClosure>` in `src/httpserver.cpp` with a header-only C++20 `boost::asio::thread_pool` + `boost::asio::awaitable` coroutine dispatcher and optional `CRPCCommand::AsyncActor`.
  - `036`: Convert OS-thread-parking `waitfornewblock`, `waitforblock`, `waitforblockheight`, and `getblocktemplate` `longpollid` (`wait_until`) to non-blocking `co_await` on `AsyncBlockChangeWaiter`.
- **Stage G2 (`037`–`038`, Lotus V2): Lock-Free RCU `ChainAndMempoolSnapshot` & True $O(1)$ `getblocktemplate` (see [`lotus-v2-rpc-coroutines-and-lockfree-snapshots.md`](./lotus-v2-rpc-coroutines-and-lockfree-snapshots.md)):**
  - `037`: Add `ChainAndMempoolSnapshot`, `SnapshotPublisher` (`std::atomic<std::shared_ptr<const ChainAndMempoolSnapshot>>`), and `ScopedMdbxReadTxn` (`MDBX_TXN_RDONLY`) so read RPCs (`getblockchaininfo`, `getblockheader`, `gettxout`, `getmempoolinfo`, `getrawmempool`) run with zero `cs_main` or `mempool.cs` locks.
  - `038`: Eliminate the legacy $O(N)$ `EncodeHexTx(tx)` loop in `getblocktemplate` (`src/rpc/mining.cpp:1115–1137`), returning $O(1)$ V2 overlay commitment fields (`overlay_id`, `subtree_a_root`, `utxo_root`, `stateroot`, and `50/25/25` `coinbasetxn`) in $< 5\text{ }\mu\text{s}$ and pairing with `submittemplateblock(header_hex, coinbase_tx_hex)`.


## Follow-on milestones — commitment-based state sync and hostile suppliers

Maintainer request (2026-10-15): implement these after the existing V2 chain and
local testnet work. They are important long-term synchronization capabilities,
not prerequisites for the first working network. No snapshot protocol, proof
encoding, default mode or Avalanche policy is selected by this plan.

The primary threat here is **availability after selecting a tip and state root**:
peers repeatedly send invalid UTXO subtrees or stall to prevent a new node from
finishing synchronization. The proposed mode uses the enclosing PoW/Avalanche tip
selection policy; specifying and implementing that policy remains separate. This
plan does not claim that the current V2 runtime already implements Avalanche.

### STATE-01: opt-in state bootstrap and historical backfill

Provide an explicit, non-default mode that imports state authenticated to the
selected header commitment and can then obtain earlier chain data in the
background. Expose the exact selected BlockID/height/root and profile, source
policy and current verification status. Review whether explicit supplier nodes
are required or merely configurable; no implicit trusted supplier list is added.
Snapshots must bind the complete required state, including coin metadata and the
monetary envelope committed by the header, rather than UTXO values alone.

Historical blocks may be downloaded backwards from the selected tip. Execution
validation still follows parent-to-child dependencies from an authenticated
starting state, with separate progress reporting. This is a secondary assurance
track; it must not obscure the primary hostile-supplier availability goal.
Persist verified state-import progress and provide explicit interruption,
selected-root change and restart behavior without mixing roots or generations.

### STATE-02: authenticated subtrees from multiple suppliers

Use the existing authenticated UTXO tree commitment as the anchor. Review a
bounded manifest/proof format that authenticates subtree hashes and key/prefix
coverage to that fixed root, so request identity is independent of a supplier.
It must detect omitted ranges, overlapping coverage, duplicate leaves and
noncanonical encodings as well as changed coins. Do not silently change tree
ordering, header roots or P02 proof formats to implement transport.

Verify each bounded response before admitting it to the imported state. Retain
verified subtrees across retries and restart; invalid responses cannot erase
valid progress. Split requests among peers, cap outstanding work and proof
processing, enforce fixed deadlines, and retry stalled or corrupt ranges with
alternate suppliers. Peer rotation/reconnection must not reset global admission
budgets or earn unlimited retries. A peer must not indefinitely own a range.
Local capacity refusal remains operational and is not evidence of poisoned data.

Multiple suppliers improve availability; their agreement is not the proof.
Every accepted chunk must independently authenticate to the selected root.
Resource bounds must include decoding, verification, queued bytes, disk writes
and restart bookkeeping, with fair scheduling for honest responses during spam.
Selection of a different tip must explicitly reconcile or retire the old import;
reuse is permitted only where authenticated subtree hashes remain identical.

### STATE-03: verifiable poison evidence and relay research

Investigate compact evidence of a malformed response, invalid subtree or invalid
claimed transition. Separate evidence about bytes from attribution to a supplier:
an independently invalid payload alone does not prove which peer sent it. Review
whether signed response commitments or another attribution mechanism is needed
before any transferable accusation can affect peer selection. Do not add a
broadcast message or automatic peer punishment until evidence encoding, verifier
cost, replay scope, attribution and false-accusation resistance are specified.

A timeout, unavailable subtree, local resource limit or unverifiable allegation
is not a cryptographic poison proof. Evidence must identify the exact chain,
selected root, requested subtree and offending claim, and recipients must verify
it independently under bounded work. Proof gossip must itself resist flooding.
Do not promise that every failure has a succinct transferable proof.

### Acceptance evidence

Demonstrate sync completion and continued verified progress with honest suppliers
available while hostile peers send corrupt proofs/subtrees, withhold ranges,
trickle bytes, reconnect and equivocate. Test mixed-root responses, malformed
coverage, oversized/computationally expensive proofs, exhaustion and restart.
Measure completion time, wasted bandwidth, verification CPU, peak retained memory
and disk use under named hardware, chain-growth and adversarial-load conditions.
State the honest-connectivity and resource assumptions; full eclipse or saturated
resources cannot be treated as a successful availability test.

Also measure sustained validation/import throughput against new-chain arrival
rate. A fast initial snapshot alone does not establish that a node can keep up or
finish historical backfill. The milestone must report which operating envelope
allows catch-up and continued operation, rather than only a small static-fixture
success. These requirements remain deferred while baseline node integration is
completed.

## Required adversarial corpus and handoff

Use independent serializers/reference fixtures for the 134-byte header, P01 TxID/TxHash, ordered block root, complete block framing, compact selector and receive-limit negotiation. Include valid baselines before each negative mutation. Exercise 252/253 CompactSize boundaries, exact limits, overflow and truncation, with no allocation based solely on an untrusted count. Compact tests must force collisions deterministically rather than wait for random collisions. Compare full-block fallback against independently validated bytes.

Transport tests must cover late responses after timeout/reorg, wrong peer/BlockID, half-open connections, repeated variant spam, unavailable/pruned bodies and failure midway through persistent commit. Measure peak memory/disk usage and fairness during the largest supported object retrieval; P05's absence of a consensus byte cap does not eliminate local resource constraints. Prove refusal is recoverable and does not permanently reject a valid header or transaction.

Each handoff records changed source paths, protocol revision, parameter/genesis artifact digest, exact replay tree, test commands/results, known limits and remaining decisions. Preserve per-milestone acceptance: working TCP does not imply working QUIC, isolated development synchronization does not imply V1 interoperability, and either transport says nothing about finalized D10–D14 production parameters.

This documentation-only change must run `docs/lotus-v2/tools/spec_candidate_checks.py` using the existing isolated compiler-review Python environment. That checker verifies existing candidate fixtures/registry consistency; it does **not** validate this new peering protocol or implement its tests.
