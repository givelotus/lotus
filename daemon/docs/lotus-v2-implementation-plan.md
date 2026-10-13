# Lotus v2 implementation: overlay on validated v1

Status: planned; no genesis launch authorized by this document. [Consensus](../../docs/lotus-v2/consensus.md) owns validity; [decisions](../../docs/lotus-v2/decisions.md) owns unresolved rules.

## Foundation contract

Start integration from the immutable source commit that passed V1-06, retaining the provenance of its pinned ABC foundation. V2 launches a separate chain with separate state. Existing `patches/v2/series` is a source collection, not the accepted application order: it currently targets ABC directly and contains stale consensus/issuance assumptions.

Specification work and an independent reference evaluator may proceed before V1-06. Production v2 daemon integration may not silently substitute an unvalidated historical workspace for that foundation. Continue v1 fixes independently; selectively forward-port shared fixes with both networks' regression gates.

## Component sequence

| ID | Deliverable | Prerequisites | Required proof |
| --- | --- | --- | --- |
| V2-00 | Close encoding/tree/path/signing/VM slice; parameter draft | D01–D04, D07; no heavy execution needed for initial review | Complete ordinary-payment semantics and explicit remaining feature blockers |
| V2-01 | Reference parser, assembler/evaluator, vector schema and payment example | Accepted V2-00 slice | Canonical bytes, script/transaction/block results and exact undo; independently checked signature/commitment outputs |
| V2-02 | New-chain daemon payment slice | V1-06, V2-01, minimum D12–D14 test-chain parameters | Fresh regtest genesis, signed payment, block/root agreement and disconnect restoration |
| V2-03 | Native assets and minting | D05 closed; V2-02 | Conservation/authorization, explicit mint contexts, asset-aware wallet/RPC |
| V2-04 | Complete VM/ABI and bounded covenant examples | D07–D08 closed; V2-03 | Every opcode specified/tested/costed, nested-loop cost bounds and input × output vault transition |
| V2-05 | Exact monetary transition and authenticated state | D10, D12–D13 closed (D11 faucet rejected); V2-02 | Integer issuance/target/state vectors, replay/reorg restoration, complete state-root/snapshot contract |
| V2-06 | Storage, cache, signature and mining optimization | Relevant scalar features and D09 equivalence obligations | Scalar equivalence, fault/restart tests, measured resource and performance evidence |
| V2-07 | Network, SDK, wallet/indexer and launch qualification | V2-03–V2-06; D14–D15 closed | Cross-component conformance, independent review, reproducible genesis/release, all launch blockers closed |

V2-04 and V2-05 may be separate workstreams after interfaces freeze; monetary state, cost schedule and state commitment are a shared integration boundary. Use exclusive file/semantic scope claims before actual parallel implementation. Do not put all features into one monolithic patch.

## Patch construction

For each feature: accepted requirements → scalar behavior/vector → daemon implementation → integration result → optional optimization. Preserve original patch/commit attribution, even when rewritten. Record apply/port/split/already-upstream/superseded/retired disposition and replacement commit. Old numeric slots do not decide architectural dependencies.

Avoid dual transaction/VM validity engines selected by a production runtime flag. Historical v1 activations and compatibility exceptions are removed or replaced explicitly on the v2 branch. Retain a disposition table for every inherited chain parameter, checkpoint, seed, address prefix, replay domain and database version. Regtest settings must not be mistaken for genesis-approved mainnet constants.

## Daemon-specific contracts

- **Persistence:** begin with the simplest correct atomic transition/undo implementation. RocksDB, RAM trie and write-behind are candidates. Define durable block/coin/undo/monetary checkpoints, recovery replay and corruption boundaries before asynchronous writes.
- **State queries/snapshots:** freeze the root algorithm in consensus. Separately define proof RPC schemas, snapshot completeness, root/chain selection trust, resource bounds, resumable import and atomic activation. State authentication does not replace historical validation.
- **Caching/batch signatures:** prove C20 equivalence; charge scalar costs even on hits. Any batch failure falls back to a deterministic scalar verdict. No architecture-specific CPU instruction is required by consensus.
- **Mempool/mining:** model spent dependencies; remove a transaction only when one of its inputs is consumed (C22a). Bound vertices, edges, bytes and expensive work. Preserve valid topological ordering and assess fee selection quality separately from speed.
- **Indexer/SDK:** expose core TxID and TxHash distinctly, native versus token values, path policies and state. Connect/disconnect notifications and wallet signing must follow exact consensus identities.
- **Transport/advisory voting:** feature negotiation, QUIC or advisory voting cannot change block validity, accepted target/work or resource limits. Existing protocols remain usable during implementation-only rollout.

## Genesis gate

Every D row must be closed, every C requirement mapped to evidence, all examples executable, all constants published, and the exact final candidate independently reviewed. Mine genesis only after parameters and serialization are frozen; do not retrofit consensus around a previously mined placeholder. Verify the resulting genesis from a second implementation/build.

Publish chain separation, genesis/parameter digests, source/build provenance, address/signature domain, node/wallet operational instructions and test results together. No existing Lotus v1 coins or databases silently migrate. No scheduled hardfork or mutable voting parameter compensates for unfinished genesis design, and the named extension points of P03 are room for later additions, not a place to defer genesis decisions.
