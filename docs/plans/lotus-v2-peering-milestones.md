# Lotus V2 peering implementation milestones

Status: **implementation plan for review, 2026-10-15**. The [peering candidate](../lotus-v2/peering.md) is the protocol contract proposed here. The maintainer selected ABC TCP first, QUIC second, new development netmagic and Lotus port defaults P2P **10605**, RPC **10604**. This plan authorizes no node launch, production parameter freeze or network-code implementation before the specification review gate.

Baseline: monorepo `8914db5177d7b97fa7aa7d04172f71ead633775c`; native ABC `1fb7db17c176cdea8a2c60d887891589382ee4e3` plus 57 patches `000`–`056`, native commit `6a7849b1887bfe814c4e1679d7e01ffedb9a52d8`, tree `9a3e3e57aa6ee0c0430144ee1200ab9cbe48f6e7`. All work belongs on the V2 development branch and isolated replay/build trees. Chronik stays off for these milestones. Preserve V1 workspaces, nodes, data, main checkout, tags and releases.

## Review gate before implementation

1. Review N01–N08 in the peering candidate, specifically message layouts, identity negotiation, full TxHash retrieval, compact reconstruction, the P05 transport-size mismatch and scoped receive-limit negotiation. Record accepted allocations and unresolved changes in a follow-up review; do not silently edit P01–P06 to make a network test pass.
2. Review an explicit development consensus/genesis artifact. The current fixture's time `0x010203040506`, bits `0x1d00ffff`, previous work 9 and header-only empty body do not establish a usable network. Derive and test valid complete genesis/first-block examples, including resource charges, with separately selected test parameters. Preserve D10–D14 mainnet choices as open; the selected port defaults do not resolve them.
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

## Required adversarial corpus and handoff

Use independent serializers/reference fixtures for the 134-byte header, P01 TxID/TxHash, ordered block root, complete block framing, compact selector and receive-limit negotiation. Include valid baselines before each negative mutation. Exercise 252/253 CompactSize boundaries, exact limits, overflow and truncation, with no allocation based solely on an untrusted count. Compact tests must force collisions deterministically rather than wait for random collisions. Compare full-block fallback against independently validated bytes.

Transport tests must cover late responses after timeout/reorg, wrong peer/BlockID, half-open connections, repeated variant spam, unavailable/pruned bodies and failure midway through persistent commit. Measure peak memory/disk usage and fairness during the largest supported object retrieval; P05's absence of a consensus byte cap does not eliminate local resource constraints. Prove refusal is recoverable and does not permanently reject a valid header or transaction.

Each handoff records changed source paths, protocol revision, parameter/genesis artifact digest, exact replay tree, test commands/results, known limits and remaining decisions. Preserve per-milestone acceptance: working TCP does not imply working QUIC, isolated development synchronization does not imply V1 interoperability, and either transport says nothing about finalized D10–D14 production parameters.

This documentation-only change must run `docs/lotus-v2/tools/spec_candidate_checks.py` using the existing isolated compiler-review Python environment. That checker verifies existing candidate fixtures/registry consistency; it does **not** validate this new peering protocol or implement its tests.
