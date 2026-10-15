# Lotus V2 private testnet: gap, ownership and API plan

Status: implementation plan, not runtime acceptance evidence. Audit performed without starting nodes. Integration owner approves and records exact source outcomes before claiming completion.

## Source boundary and current behavior

Monorepo audit source: `c92e749cc15f4ec722d3e3f1f74e3b9d629bd562`. Native audit source: `c605e6e9f12d9fa80a50103d40973531dcdceb95`, 173 ordered mailboxes 000–172 on ABC `1fb7db17`. Record full ABC object ID from the selector in implementation evidence. This plan was prepared in a new isolated worktree rooted at `8914db51`, fast-forwarded to the monorepo audit source.

`tools/lotus-v2-devnet/controller.py` creates a signed Payment transaction and passes its wire directly to `mineblock`. This exercises signing and block validation but does not demonstrate transaction broadcast, dependency admission, or remote mining from a mempool. Native `development_node_command.cpp` owns the local command dispatcher and TCP peers. `DevelopmentRuntime` owns durable state and bounded candidate/reorg execution. `peer::Session`, `Transport`, and `TcpStream` already supply negotiated framing, resource limits and explicit numeric endpoints. `peer_codec.h` inventory type 1 already denotes TxHash; transaction relay routing/admission remains to be implemented.

The deliverable is real native nodes on separate machines, with one wallet originating, another node relaying, and a third mining the relayed transaction, followed by restart and competing-branch recovery. Standalone unit APIs supplement this acceptance test.

## Ownership and merge order

| Owner | Exclusive files or boundary | Integration contract |
| --- | --- | --- |
| Absolute-paper owner | Separate LaTeX worktree `main.tex` / `README` | Absolute-tail definition reviewed against implementation |
| Monetary implementation owner | Python monetary reference/tests; native `monetary.*` and direct monetary tests | Shared absolute-tail vectors; root integrates profile changes |
| Pool owner | New native transaction-pool module and its tests | Admission, dependency graph, conflicts, limits, template snapshot, reconciliation |
| Relay owner | New transaction relay module/tests; coordinated additions to `peer_codec.*` | Existing inventory identity, bounded requests, canonical transaction bodies, admission callback |
| Wallet owner | `src/wallet/v2_*` wallet/client/provider changes and tests | Submit/status contract, persisted pending wire, rebroadcast, restart/reorg states |
| Profile/controller owner | `tools/lotus-v2-devnet/` setup, schema, controller and process tests | Explicit remote endpoints, profile provenance, reproducible three-node scenario |
| Root integrator | `development_runtime.*`, `development_node_command.cpp`, CMake targets, mailbox export/series/provenance and final evidence | Authoritative transition hooks, stable coin lookup, node dispatch, mining pool snapshot |
| Avalanche/PoW owner | Explicitly assigned upstream dependency analysis and adapter files/tests | Preserve pinned defaults; real V2 identity/state integration before claiming Avalanche support |

No two owners edit runtime/dispatcher/CMake or export mailboxes concurrently. Agree headers first, implement against them, then root integrates monetary/profile identity, runtime hooks, pool, relay, wallet and orchestration in dependency order. Parameter choices stay open; use the current tested profile until an explicit absolute-tail migration is specified. Neither exploratory changes nor acceptance tests touch main, existing data, releases or production ports.

## Absolute-tail invariants

Bind immutable genesis tail/work anchors to ChainProfile, manifest and consensus profile digest. Derive entitlement directly from authenticated parent-header work, never from previous cached tail or a parent-as-genesis fallback. The existing 56-byte MonetaryState may retain redundant fields temporarily only if validation rejects cached tail values inconsistent with derivation. Current toy test anchors 200/9 and real manifest anchors 1m/2 are distinct: migrate each explicitly and regenerate corresponding vectors/profile bindings rather than conflating them. Root owns profile/header integration; monetary implementation owner supplies derivation and boundary tests; separate absolute-paper owner owns LaTeX. Avalanche audit owner owns only its new `docs/plans/lotus-v2-avalanche-integration.md` during the initial read-only audit.

## Native API contracts

Pool admission accepts canonical full transaction wire plus origin, current chain anchor and explicit budget. Return distinct accepted, duplicate, conflicting, missing-parent, invalid, capacity-refused, stale-context and operational-error results. Compute both TxId and TxHash; index spends by Outpoint/TxId while inventory and wire retrieval use TxHash. A different witness/serialization sharing TxId needs a deterministic explicit policy rather than accidental duplicate treatment.

Use `CheckOrdinaryWithLookup` and its existing `CoinLookup` boundary. Lookup sees one stable active context: accepted ancestor outputs first, active `DevelopmentRuntime::ReadCoin` second, with a spent index rejecting conflicts. Never copy the full UTXO map. Missing parents are not consensus-invalid. Bound transaction bytes, total bytes, entries, graph edges, ancestors/descendants, validation work and optional orphan bytes/count/expiry separately. Reject replacement initially unless a documented replacement rule is implemented. Admission publishes graph/effects atomically after validation and context recheck. Never classify StorageError/Inconclusive as invalid.

Mining asks the pool for a bounded deterministic parent-before-child snapshot bound to the current tip/context generation, passes it through existing `BuildTemplate`, and validates final block commitments normally. Pool acceptance is not full block validity: `CheckOrdinaryWithLookup` explicitly excludes transaction-wide P05 L(tx), parabolic block burn, ordering and state commitments. A bounded assembler skip/retry policy must prevent one individually admissible transaction from blocking all templates.

Runtime currently provides `Tick.context_changed`, `Snapshot.context_generation`, and reorg progress but no committed transaction transition stream. Add a bounded authoritative transition receipt/cursor containing old/new anchors and connected/disconnected block IDs, with paged body reads through existing runtime facades. Publish only after durable authoritative transition acknowledgement; rollback/restoration must resolve to the final authoritative state. Suspend pool admission/template production while execution is recovering/paused or authority is unknown. On final transition remove mined transactions/conflicting descendants, reconsider surviving entries and detached ordinary transactions in dependency order, and discard stale coin snapshots. If receipts are unavailable after restart, reconstruct from persisted active history and revalidate persisted transactions before relay. Generation changes alone cannot identify what to resurrect.

Relay uses negotiated `inv`/`getdata`/`tx` semantics over existing TCP transport. Preserve existing inventory type 1=TxHash. Extend Session/router command authorization consistently; no parallel transport or wallet-to-miner shortcut. Maintain bounded per-peer/global known inventories, outstanding requests, deadlines, retry counts, received body bytes and validation work. Validate canonical body/advertised identity before pool admission; advertise only accepted transactions. Missing-parent handling requests bounded dependencies or returns a retriable missing-parent result. Avoid inventory loops, unsolicited allocation and peer punishment for local capacity/storage failures. Capability/profile negotiation must make incompatible peers fail clearly.

Local commands should expose `submittransaction` (canonical wire, expected anchor, identities/admission outcome), `transactionstatus` (unknown/pending/confirmed/conflicted/rejected, anchor and optional block), and bounded mempool status. Dispatcher owns exact JSON names/limits and stable error codes. Wallet broadcast saves wire and TxId/TxHash before submission; distinguishes local acceptance from propagation and confirmation. Restart reloads pending payments and rechecks/rebroadcasts idempotently. Reorg can move confirmed back to pending or conflicted; do not infer confirmation solely from submission success. Existing `NodePaymentChainProvider` only exchanges `walletcontext` and needs a separate submission/status adapter.

## Pinned ABC Avalanche and PoW

Do not invent fresh numerical defaults. Record exact pinned ABC definitions, V2 overrides and their reasons in the profile manifest. Upstream `avalanche::Processor` directly depends on `ChainstateManager`, `CTxMemPool`, `CConnman`, scheduler, stake/proof validation and legacy inventory/state types; merely compiling it or flipping a flag does not integrate V2. Identify concrete V2 adapters for transaction/block identities, proof coin lookup and signatures, peer polling/authentication, finality/conflict decisions and restart behavior. Preserve PoW chain selection authority and document interaction with finalization/parking. Test actual eligible proofs/quorum and vote transitions if Avalanche is part of acceptance. An unsupported adapter must remain a reported gap, not be represented as a working default. Avoid importing eCash miner-fund policy into V2.

## Profile and acceptance gates

A reproducible profile pins genesis wire/ID, chain ID, profile digest, monetary/absolute-tail parameters, PoW/ASERT configuration, Avalanche mode/parameters, transaction/VM rules, binaries/source/patch digests and local resource limits. Explicit migration changes identity/digest and declares whether existing data must be recreated. Setup must reject accidental reuse under incompatible profiles. Provide separate per-machine data/wallet directories and explicit bind/connect numeric addresses, remote reachability instructions and bounded retries. Local command secrets stay local; TCP peers exchange public transaction/block data. Chronik is OFF. Use explicitly allocated nonproduction ports, never 10604/10605/8331.

Required evidence, with source hashes and commands:

1. Absolute-tail paper/spec/Python/native vectors agree at transition, saturation/rounding, zero/large work, fee/burn and supply boundaries; no arbitrary parameter selection hidden in fixtures.
2. Native pool tests cover parent/child and diamond dependencies, duplicate identities, conflicting spends, maturity/lock changes, invalid VM, byte/graph/work caps, stale anchor and storage/inconclusive failures.
3. Relay tests exercise genuine TCP framing/admission, split/trickled frames, malformed identity/body, missing parents, backpressure, bounded requests, duplicates and peer disconnect/reconnect.
4. Three actual native processes: A originates and submits; B learns through TCP and relays; C has no direct A transaction path and mines using its pool. All agree on TxId/TxHash, block ID, active coin changes and wallet status. Controller may command mining, but supplies no transaction wire to the miner.
5. Restart node and wallet with pending and confirmed payments; validate persisted chain/profile identity, pending reconstruction/rebroadcast and no duplicate spend.
6. Mine a competing heavier branch, reconnect peers, observe committed disconnect/connect recovery; detached valid transactions return to pool, conflicting descendants do not, wallet status follows active history, and restarted nodes converge. Include interrupted recovery and recovery failure/restoration.
7. Repeat documented three-machine setup with explicit addresses; record platform/binary/profile digests and measured results. Loopback process tests establish a reproducible baseline but cannot prove cross-machine reachability.

Only completed gates justify “usable private testnet.” Record unsupported functionality and failed checks directly; no publication, tags or release asset changes are part of this work.
