# Lotus V2 peering candidate

Status: **proposed protocol, 2026-10-15; review required before networking implementation**. This document adds a peering design to the V2 candidate. It does not claim that `lotusd` currently speaks this protocol or that the development genesis is a usable network. Requirements below are normative within this proposal only. [Consensus](consensus.md), [P01–P06](decisions.md), and their unresolved parameters still determine validity. The implementation sequence and review gates are in [peering milestones](../plans/lotus-v2-peering-milestones.md).

The maintainer selected **ABC TCP peering first, QUIC second, new development network magic, P2P port 10605 and RPC port 10604**. All wire allocations, limits, handshake extensions, hash choices and QUIC details below are design proposals. These port defaults are the only network values selected by the maintainer here; they do not freeze D10–D14 or select a production launch profile.

## 1. Source baseline and compatibility findings

The inspected monorepo revision is `8914db5177d7b97fa7aa7d04172f71ead633775c`. Native source is the clean replay of 57 V2 patches, `000`–`056`, on Bitcoin ABC `1fb7db17c176cdea8a2c60d887891589382ee4e3`: commit `6a7849b1887bfe814c4e1679d7e01ffedb9a52d8`, tree `9a3e3e57aa6ee0c0430144ee1200ab9cbe48f6e7`, inspected at `/private/tmp/lotus-v2-audit-replay-20261015`. Paths in the following inventory refer to that exact native tree.

| Area | Reusable implementation | Required V2 work |
| --- | --- | --- |
| TCP framing and sockets | `src/net.h`, `src/net.cpp`: `V1TransportSerializer`, `V1TransportDeserializer`, `CConnman`, message queues, sockets and connection lifecycle | New magic; identity handshake; explicit local receive limits; no dispatch into legacy consensus objects |
| Commands and service discovery | `src/protocol.h`, `src/protocol.cpp`, `src/node/protocol_version.h`: 24-byte envelope, version 70017, command registry and inventory | Explicit V2 revision/capabilities; identify full transaction hashes; remove unsupported services |
| Peer maintenance | `src/addrman.*`, `src/net_processing.cpp`, `src/netbase.*`: address grouping, eviction, relay scheduling, ping/pong, proxy support | Separate address databases; V2 seeds absent by default; address hints are untrusted; preserve network diversity |
| Header/block download | `src/net_processing.cpp`, `src/headerssync.*`: locators, headers-first synchronization, in-flight tracking, timeouts and work presynchronization | 134-byte headers, BLAKE3 BlockID/work, V2 time/target rules and persistent V2 chain validation |
| Compact blocks | `src/blockencodings.*`, `src/shortidprocessor.h`: six-byte short IDs, prefilled transactions, missing-index requests, collision handling, full-block fallback | V2 headers and framed transactions, full TxHash cache keys, V2 ordered transaction root and validation, P05 resource bounds |
| Transaction relay | `src/net_processing.cpp`, `src/txrequest.*`, `src/txmempool.*`, `src/txorphanage.*` | Separate TxID conflict/outpoint identity from TxHash retrieval and rejection caches; V2 validation and cost-based policy |
| Avalanche | `src/avalanche/`, `src/net_processing.cpp` | Separate proof/payout/identity adaptation and D11 review; disabled and unadvertised in the initial profile |
| Native V2 primitives | `src/lotus_v2/header.*`, `transaction.*`, `commitment.*`, `block*`, `persistent_*`, `dev_genesis.*` | Connect the reviewed V2 validator and atomic chainstate to peer processing; these modules alone do not constitute a peering node |

At this revision `src/net.cpp` constructs only the V1 serializer/deserializer. A repository search for QUIC implementations and common QUIC library names found **no QUIC transport or dependency**. The relevant hit is `src/net_processing.cpp:6841`, which explicitly says QUIC is not implemented and explains why Avalanche responses still need application signatures. This is evidence about the inspected revision, not every ABC branch or future release. QUIC is new integration work in milestone 2.

Reuse is principally implementation and message choreography. An unmodified ABC or Lotus V1 peer cannot exchange V2 headers, transactions, block bodies or compact blocks. The native tree still contains upstream network settings in `src/kernel/chainparams.cpp`; renaming binaries and compiling V2 modules has not changed that fact.

## 2. Network identity and isolation (N01)

A development network has one explicit, versioned parameter artifact. It records independently selected ChainID, exact complete genesis bytes and BlockID, consensus parameter bytes/digest, network magic, ports, transport revision and enabled services. It also records source/build reproduction separately; build/compiler differences do not change protocol compatibility. The artifact format and actual consensus bytes require review before implementation. Compute the consensus profile digest over its canonical consensus parameter bytes, including ChainID but excluding the digest itself, genesis hash, transport settings and local policy. Proposed digest: `BLAKE3("Lotus/v2/p2p/profile\0" || parameter_bytes)`. No self-referential manifest hashing is permitted.

Proposed development TCP magic is the four literal bytes **`d7 6c 32 a9`**, named `LOTUS_V2_DEV_MAGIC_1`. This is an arbitrary candidate with non-text boundary bytes, distinct from the inspected ABC main/test/regtest magic and the V1 magic in `daemon/patches/v1/025-new-net-magic-for-main-test-and-regtest.patch`. It is not a globally registered value or a production choice. Review must check the final supported network inventory before allocation; an incompatible development reset uses a new profile/genesis and newly allocated magic.

Default P2P TCP port is **10605**; RPC is **10604**, bound to loopback with existing authenticated RPC controls. QUIC proposes UDP **10605** later. Sharing port numbers with V1 does not imply compatibility. Tests use separate datadirs and dynamically allocated loopback ports, never the live defaults. Bind failure must fail clearly, without changing ports silently or stopping an existing node.

Development mode requires an explicit V2 network/profile selection and separate data namespace, including block storage, chainstate, peer/address tables, bans and RPC cookie. It must refuse an existing V1/eCash datadir. Do not import upstream seeds, fixed peers, checkpoints, assumevalid, assumeutxo, minimum-chain-work or wallet prefixes. Initially use explicit loopback peers; no DNS seeds or public discovery bootstrap is selected here. Disk magic and storage schema also need distinct values before integration, but this proposal does not allocate them. The P2P magic is not authorization to reuse upstream disk identifiers.

The 4-byte magic rejects accidental cross-network messages early. ChainID, genesis BlockID and consensus profile digest are checked separately during handshake; none authenticates a peer. A malicious peer can repeat all of them. Peers still need full validation and eclipse-resistant connection selection. Address format and seeds remain D14 decisions.

## 3. TCP envelope and handshake (N02)

Retain ABC's envelope exactly:

```text
magic[4] || command[12] || payload_length:u32 || checksum[4] || payload
checksum = first four bytes of SHA256(SHA256(payload))
```

The command is ASCII with zero padding; reject nonzero bytes after its first zero and non-printable command bytes. Integer encoding is ABC little-endian, except inherited address fields such as network-order ports. New fields follow P01 little-endian/shortest CompactSize conventions. Check command and length before allocation. The checksum detects corruption; TCP remains unauthenticated and unencrypted. SHA256 here is an inherited transport checksum, outside V2 consensus hashing.

Proposed initial local message payload cap is **2 MiB for every command**, with tighter per-command limits below. After handshake, use the smaller advertised peer cap. This is a transport resource limit, not a maximum valid transaction or block size. It deliberately scopes the first development milestone to objects that fit both peers. P04 permits a u64 block size and P05 has no hard byte ceiling; section 6 records the resulting availability limitation and required future work. Replace the current `CMessageHeader::IsOversized` coupling to legacy `GetMaxBlockSize()` with this explicit V2 transport policy; do not change the 24-byte envelope.

Retain the version-70017 ABC `version` payload, including its existing optional-field rules and nonce/entropy handling; the initial V2 profile sends the complete modern form and requires version >=70017. This legacy number gates reused facilities only. It is not the V2 wire revision and cannot establish chain compatibility. User agent and starting height are untrusted diagnostics. Validate lengths, nonce self-connection and duplicate-version behavior as upstream does.

Add a required, exactly 118-byte `v2hello` payload:

```text
wire_revision:u16(1) || ChainID:h32 || genesis_id:h32 || profile_digest:h32
|| supported:u64 || required:u64 || receive_limit:u32
```

Proposed feature bits are `0x01` V2 framed objects, `0x02` full-TxHash relay and `0x04` compact profile 2. All three are mandatory in revision 1 (`required=0x07`, and all must be in `supported`). Unknown supported bits are ignored; unsupported required bits, missing mandatory bits, incompatible revisions or identity mismatch close the connection before relay. `receive_limit` must be in 1..16 MiB inclusive, with 2 MiB the proposed local default. Its meaning is payload bytes of one message, excluding the envelope. Each endpoint uses `min(local_receive_limit, peer_receive_limit)` as the active send/receive limit; changing limits requires reconnecting. Before hello, use the 2 MiB pre-handshake cap and a separate 118-byte hello cap. A later hello cannot authorize previously rejected bytes. Per-command count/byte bounds still apply even when the negotiated cap is larger. Full-block retrieval remains usable when a peer chooses not to request compact announcements.

Each endpoint sends `version` first. After receiving an acceptable `version`, it sends `v2hello` and may send `sendaddrv2`. It sends `verack` only after accepting the peer's `v2hello`; a peer's `verack` before its accepted `v2hello` rejects. The connection becomes active only after both hellos and both veracks. Before activation, accept only these handshake messages, with no allocation of transaction/block downloads or address relay. Duplicate hello, trailing hello bytes or application data before activation closes the connection. Both endpoints must complete this sequence within a proposed 10-second local handshake timeout.

After activation, reuse `sendheaders`, `sendcmpct`, `ping/pong`, `getaddr`, `addr/addrv2`, `inv`, `getdata`, `notfound` and `getheaders/headers` with the V2 payload meanings below. Unknown optional commands are ignored after envelope validation under the bounded-message budget. Unknown inventory types are ignored, never interpreted as another known type. Unknown consensus versions/flags still reject under C02; network negotiation cannot change that rule.

Advertise `NODE_NETWORK` or `NODE_NETWORK_LIMITED` only when the node actually provides the corresponding validated history; headers alone do not qualify. Preserve `NODE_BLOOM`, compact-filter, Avalanche and snapshot services as unavailable until separately implemented and reviewed. Initially ignore `feefilter` without advertising fee filtering: its upstream fee-per-kB interpretation cannot be reused for P05's fee-per-effective-cu policy. `mempool` enumeration, transaction package relay and Bloom-filter commands are outside revision 1. Disable their handlers explicitly.

## 4. Headers, complete objects and relay identifiers (N03)

Use P04's exact header and block layout, with raw hashes in digest order:

```text
Header = prev_id:h32 || bits:u32 || time:u48 || nonce:u64
         || version:u32(2) || size:u64 || height:u64
         || tx_root:h32 || state_root:h32                     # 134 bytes
Block  = Header || transaction_count:u32 || Bytes(Tx)[transaction_count]
```

`block` payload is exactly one complete Block. `tx` payload is exactly one complete P01 Tx; its envelope supplies the outer transaction frame. Every transaction inside a Block has its own shortest CompactSize byte-length prefix. No V1 metadata vector, 80/160-byte header, Bitcoin input/output encoding, witness marker or trailing extension is present. Reject trailing bytes. Preserve the validator's exact count, arithmetic, semantic and cost checks before allocation; do not deserialize into an upstream `CBlock` and convert afterward.

`headers` retains ABC's vector convention: `CS(count)` followed by `Header || CS(0)` for each item, with at most 2000 items. The zero is a required one-byte sentinel, not P04's u32 block transaction count. Thus one item is 135 bytes, and 2000 items fit the message cap. `getheaders` retains the upstream locator format (protocol version, CompactSize vector of locator hashes, stop hash), but every hash is a V2 BlockID. `getblocks` may reuse the same locators and bounded block-inventory response. Preserve upstream locator/count limits. Derive parent links, accumulated work and eligibility using V2 rules; a header's size, transaction root or state root remains an unverified claim until body validation.

| Inventory type | Hash meaning in negotiated revision 1 | Response |
| --- | --- | --- |
| `MSG_TX = 1` | P01 **TxHash**, committing to complete arguments/signatures | `tx`, subject to negotiated receive limit |
| `MSG_BLOCK = 2` | P04 BlockID | `block`, subject to negotiated receive limit |
| `MSG_CMPCT_BLOCK = 4` | P04 BlockID | `cmpctblock` profile 2, or full-block fallback |
| `MSG_AVA_PROOF = 0x20000001` | Avalanche `ProofId` | `avaproof` |
| `MSG_AVA_STAKE_CONTENDER = 0x20000004` | `StakeContenderId = H(prevblockhash, proofid)` (~25% staker share) | Derived locally in `StakeContenderCache` |
| `MSG_AVA_TREASURY_CONTENDER = 0x20000005` | `TreasuryContenderId = H(prevblockhash, script_hash)` (~25% treasury share) | `avatreasury` (`prevblockhash \|\| CScript`) |
| `MSG_AVA_MEMPOOL_BATCH = 0x20000006` | `MempoolBatchId` (pre-consensus epoch/bucket Merklix root) | `merklixsync` (`ReconScope::PRECONSENSUS_EPOCH`) |

`inv`, `getdata` and `notfound` retain `CS(count) || (type:u32 || hash:h32)[count]` and the upstream maximum 50,000 entries, also subject to the negotiated message cap. Split inventory announcements/requests into smaller complete batches when needed; never send a count whose payload exceeds that cap. A full-TxHash response must match the requested hash exactly. `MSG_TX` gets this changed meaning only after V2 identity negotiation; there is no legacy peer fallback or ambiguous TxID interpretation.

Use **TxID** for outpoints, dependency edges and the rule allowing at most one core transaction per block. Use **TxHash** for wire requests, recently received objects, compact matching, in-flight suppression and argument/signature-specific rejection caching. Distinct valid argument vectors can share a TxID and have different TxHashes. An invalid signature for one variant must not poison another variant's acceptance. Only a proved core-invalid result can be cached by TxID; unavailable inputs, temporary locks, insufficient local fees and policy refusal are not permanent core-invalid results.

The mempool may retain one fully validated representative per TxID under local replacement policy, while a bounded full-TxHash recent-object cache supports reconstruction. Receiving another variant does not bypass validation or require unlimited variant storage. For an unknown parent named by TxID in an orphan, revision 1 may wait for normal relay or chain synchronization; it does not reinterpret a TxHash `getdata` request as a parent-TxID query. A later explicit parent-discovery extension can improve this without changing identity semantics.

Every relayed transaction contains all witnesses and arguments. Stripped data is a commitment projection, not an executable or relayable transaction format. Run P01 signature modes, resolved-coin binding, P03 VM semantics, locks, asset accounting and P05 costs normally. A transport session or compact short ID never substitutes for these checks.

## 5. Transaction-free template block relay (`tmplblock`) and compact-block profile 2 (N04)

### 5.1 Transaction-free template block announcement (`tmplblock`) and Candidate Overlay Root Match Stage

As specified in the [bulk pre-consensus & mempool overlays plan](../plans/lotus-v2-bulk-preconsensus-and-mempool-overlays.md), because `TxRoot = H_txroot(0x03 || CoinbaseLeaf || SubtreeA)` separates `CoinbaseTx` (`vtx[0]`) from the `TxID`-keyed Merklix `SubtreeA` (`vtx[1..n-1]`) and `vtx[0]`'s outputs are pipelined into `UtxoRoot` in Block $h+1$, each finalized pre-consensus overlay snapshot $L_k$ (and the local speculative mempool overlay $L_{\text{spec}}$) already holds a pre-populated candidate `CBlock` (`cached_block`, with `vtx[1..n-1]` in CTOR order), `subtree_a_root`, and `utxo_root`.

When a miner finds valid PoW on a candidate block, it announces a ~284-byte transaction-free **`tmplblock`** message:

```text
tmplblock = Header (134 bytes) || Bytes(CoinbaseTx) (~150-250 bytes)
```

Receivers process `tmplblock` in a two-stage pipeline:
1. **Stage 1 — Candidate Overlay Root Match (`MatchCandidateOverlay`, $< 5\text{ }\mu\text{s}$):**
   - Verify the 134-byte `Header` PoW (`BlockID <= target`) and timestamp/size bounds **before** parsing `CoinbaseTx`, then parse `CoinbaseTx` ($\le 10\text{ KB}$) and compute `CoinbaseLeaf = H_txroot(0x00 || coinbase_txid || coinbase_txhash)`.
   - Test `H_txroot(0x03 || CoinbaseLeaf || L.subtree_a_root) == Header.tx_root` and `H_state(0x00 || ChainID || height || L.utxo_root || 0x38 || MonetaryState) == Header.state_root` against the local candidate ring buffer $\{L_k, L_{k-1}, L_{k-2}, L_0, L_{\text{spec}}\}$ (at most 5 BLAKE3 evaluations).
   - If a candidate overlay $L$ matches, slot `Header` and `vtx[0] = CoinbaseTx` into `L->cached_block` in $O(1)$, evaluate soft Avalanche parking policies (`StakingRewardsPolicy` `25%`, `TreasuryPolicy` `25%`, `PreConsensusPolicy`), relay `tmplblock`, and commit $L$'s pre-staged UTXO/SMT diff directly to `libmdbx` (`CommitFinalizedOverlay`).
2. **Stage 2 — Automatic `cmpctblock` / `block` Fallback:**
   - If no local candidate overlay matches `Header.tx_root` and `Header.state_root` (e.g., the node is in Tier 0 without a converged overlay, the miner included custom unfinalized transactions, or the node is catching up), the receiver immediately requests **`getdata(MSG_CMPCT_BLOCK, BlockID)`** (if at tip) or **`getdata(MSG_BLOCK, BlockID)`** (if behind tip).

### 5.2 Compact-block profile 2 fallback

Retain ABC's `sendcmpct` layout, `announce:u8 || version:u64`, with `announce` exactly 0 or 1. Propose **version 2 within the isolated Lotus V2 network**. It is not a claim of Bitcoin BIP152 witness-version-2 compatibility. Versions other than 2 are ignored without enabling compact relay. Do not emit unsolicited high-bandwidth compact blocks until the peer requests `sendcmpct(1,2)`; reuse upstream bounded peer selection/in-flight scheduling and near-tip applicability. Older history uses full blocks.

```text
cmpctblock = Header || nonce:u64
             || CS(short_count) || short_id:u48[short_count]
             || CS(prefilled_count) || Prefilled[prefilled_count]
Prefilled  = CS(delta_index) || Bytes(Tx)
getblocktxn = BlockID:h32 || CS(count) || CS(delta_index)[count]
blocktxn    = BlockID:h32 || CS(count) || Bytes(Tx)[count]
```

The compact nonce is fresh random relay entropy, separate from the header's mining nonce. Preserve the existing ABC key derivation and SipHash primitive: `key_material = SHA256(serialize(Header) || LE64(nonce))`; `k0=LE64(key_material[0:8])`, `k1=LE64(key_material[8:16])`. Compute `SipHash-2-4(k0,k1, TxHash[32]) & 0xffffffffffff` and encode the result as six little-endian bytes. Hash input is the full P01 **TxHash**, never TxID, raw SHA256d(transaction), or a signature digest. SHA256 and SipHash here are non-consensus compression mechanics; all header, transaction and state commitments remain P01/P02/P04 BLAKE3. Reusing this calculation avoids an unnecessary new hash domain or compact-key algorithm.

`delta_index[0]` is the first absolute index; each later absolute index is `previous + delta + 1`, with checked arithmetic. `N=short_count+prefilled_count` must be positive, fit P04's u32 transaction count, and satisfy conservative byte bounds implied by `Header.size` before any N-sized allocation. Prefilled indices are strictly increasing and below N. This profile requires coinbase prefilled at index 0 and permits additional prefilled transactions. Remaining short IDs fill the other positions in ascending order. The header commits exact complete block size, not compact payload size.

For `getblocktxn`, require a nonempty, bounded count and strictly increasing in-range indices. Serve only a known, available block and apply upstream near-tip/anti-amplification policy. Return exactly the requested complete transactions in request order. Permit one outstanding missing-index request per peer/BlockID, retaining the original list. A response's count, indices implied by request order, short-ID matches and prefilled positions must all agree. Unsolicited, late or mismatched responses cannot modify another reconstruction. If the response exceeds the negotiated cap, terminate that reconstruction without truncation and permit full-block fallback if it fits. Otherwise report temporary unavailability using `notfound(MSG_BLOCK, BlockID)` and the local diagnostic; the requester can try another connection with sufficient capacity. The original missing-index request must be cleared.

Reconstruction proceeds as follows:

1. Check header structure, parent/target/PoW eligibility and bounded compact framing. Reserve local download resources before allocating. An unavailable parent triggers header acquisition, not a permanent bad-block record.
2. Index validated mempool/recent complete transactions by full TxHash and short ID. A short ID with multiple possible complete transactions is ambiguous. Request every ambiguous or missing position; do not choose by TxID or silently attach local signatures. Duplicate compact short IDs may instead trigger immediate full-block fallback.
3. After missing transactions arrive, recompute each TxID and TxHash, reject duplicate TxIDs, recompute P02's ordered count-bound transaction root and exact P04 block size, and compare both with the header.
4. If locally matched candidates fail the root or size, discard that reconstruction and request the complete block once. Short-ID collision or a mempool variant is not proof that the announced header or peer is malicious. Do not permanently mark the BlockID invalid from a failed compact reconstruction.
5. Validate the complete transaction sequence, all signatures, coinbase, resources, monetary transition and state root through the same atomic V2 block-validation path as full-block download (or via $O(|B \triangle L_{\text{spec}}| \log N)$ Merklix symmetric diff against $L_{\text{spec}}$ when every transaction in $B \cap L_{\text{spec}}$ is already signature- and VM-verified). Only a completely retrieved and independently invalid body justifies a consensus-invalid result; use existing distinctions between malformed transport and invalid consensus data.

If compact encoding itself would exceed the negotiated cap, announce the BlockID with `inv` or `headers`; answer compact requests with full-block data when it fits, otherwise `notfound(MSG_BLOCK, BlockID)`. Never truncate a compact vector to fit. Full-block fallback is required for objects within the negotiated capacity; section 6 states the larger-object limitation.

## 6. Receive limits and larger-object follow-up (N05)

Milestone 1 retains the ABC u32 message length and whole-object messages. It does not add a mandatory chunk-transfer protocol. Send only complete objects fitting the negotiated cap. Answer an outstanding `getdata` for a locally unavailable, pruned or unservable object with `notfound` for its inventory ID. Clear the corresponding request and permit retry elsewhere. Log resource/size refusal separately from absence and consensus invalidity; do not insert the object's ID into a permanent-invalid cache. Mismatched compact capacity similarly falls back or reports unavailability as specified above.

The 16 MiB negotiation ceiling bounds this initial protocol profile's transport capability; it is explicitly **not** P05 consensus. Even an object larger than the cap may be valid. If every reachable peer refuses it, this first implementation cannot synchronize past that block. Compact reconstruction can reduce bytes sent but does not guarantee availability of arbitrarily large missing transactions or bodies. Therefore TCP milestone acceptance covers a named development workload within configured limits, never universal P05 object delivery or public-network readiness. Local import is useful for diagnostics but does not repair peer-to-peer availability.

Before claiming general network usability, separately review how to deliver and validate larger economically permitted objects: a justified transport-capacity envelope with bounded incremental parsing, or a request-driven chunk extension preserving exact P01/P04 bytes and u64 lengths. The ABC envelope itself cannot encode a payload above `2^32-1` bytes; such a use case requires a new framing/streaming design. Review requirements include bounded range requests, object ID and length binding, cancellation, malicious total/count handling, restart/resume, peak memory/disk and full-object verification. No chunk command names or feature bits are allocated in this revision. QUIC streams alone do not remove application record or validator memory limits.

Retain bounded per-peer/global download queues, progress timeouts and alternate-peer retries from upstream, adapting byte/cost accounting for V2. Tests must distinguish capacity refusal from invalidity and demonstrate clean recovery. Tune quotas from measured workloads before deployment; a peer's declared block size never authorizes allocating that many bytes.

## 7. Validation boundary, generalized Merklix set reconciliation, and Avalanche coordination (N06)

The [epoch reconciliation and voting draft](mempool-reconciliation.md) specifies
recovery into the working epoch (`AB|D -> ABC|DE`), pinned proposal-pair zoom,
fresh root-bound votes after revision and repeated reconciliation. Two independent
review rounds approved the core lifecycle. Actual clock-based epoch formation
and authoritative trace vectors remain unresolved; production promotion is
pending that contract. The earlier full-pool recovery review did not cover
these voting-epoch semantics.

TCP/QUIC, `tmplblock`, full/compact transfer and disk import must enter one V2 validation interface. Transport may reject malformed messages or refuse local resources, but cannot invent block entitlement, use upstream transaction hashes, relax a missing opcode implementation, choose an ASERT anchor, skip signatures, or reinterpret a state-root mismatch. Unknown VM operations must follow the reviewed V2 implementation and C02/P03 contract; no OP_DEFINE/OP_INVOKE is introduced.

Use greatest accumulated valid work under P04 and the explicitly chosen eligibility profile. Header work is not permission to mark an unvalidated state root trusted. Preserve bounded header presynchronization, reorg handling, download-stall recovery and distinct invalid/missing/context-ineligible results. Crash consistency and atomic undo must be established before peer-supplied blocks can change persistent state.

### Snapshot catch-up and optional history (N06a)

Maintainer direction, 2026-10-20: **“possibly never reaching genesis is
reasonable, but never being able to catch up is not.”** This is a required
operational property of the proposed synchronization design, subject to the
supported conditions below. It is not a claim that the current implementation
has demonstrated that property. It remains provisional through testnet.

After admission of an authenticated snapshot/bootstrap state, forward
validation MUST be able to close the outstanding validation backlog, reach
the live eligible chain tip and continue following it while new blocks arrive.
It MUST NOT wait for optional history to reach genesis. Snapshot admission
retains [P02's state-envelope and historical-validation
obligations](decisions/commitments-and-state.md): chain/profile binding,
canonical complete state, authenticated commitments and required header/time
context must be checked. An authenticated state commitment does not itself
prove every historical transition valid. Record and expose the actual verified
history boundary; catching up does not silently upgrade a snapshot's trust
status. This requirement introduces no new snapshot trust anchor, assumed-valid
history, finality rule, consensus rule or monetary parameter.

A supported synchronization profile MUST state its workload and resource
assumptions before claiming catch-up: transaction/block sizes and validation
cost distribution, sustained and burst arrivals, live-state size, supported
initial backlog/downtime, available CPU/RAM and sustained storage capacity and
I/O, network throughput/latency, and availability of an admissible bootstrap
and the post-bootstrap data needed for forward validation. Include competing
node services and maintenance in that resource budget. Transport support must
cover the profile's objects; N05's known large-object availability limitation
cannot be hidden by a snapshot or compact-transfer claim. There is no promise
for arbitrary hardware, arbitrarily sustained traffic, or unavailable required
forward data. Report an unmet assumption as capacity/availability failure,
not an invalid block or permission to skip validation.

Catch-up acceptance requires **measured positive headroom**: sustained validated
forward service must exceed newly arriving validation work over the declared
workload windows, including the specified bursts and competing work. Matching
the arrival rate only preserves existing lag. Measure backlog reduction and
time to catch up from the stated starting lag against a moving tip; record
validation work, bytes and elapsed time as well as heights, since equal-height
gaps need not have equal cost. Publish the measured margin, test duration,
queue/resource peaks and exact workload/hardware/network conditions. No
throughput target, universal catch-up deadline or new numerical constant is
selected here. A profile that can follow a stationary test chain but cannot
close lag under its supported continuing arrivals does not satisfy N06a.

Historical backfill towards genesis is optional, independently tracked and
lower priority than forward validation. Bound its retained bytes, staging
disk, memory, CPU/I/O service, network concurrency, outstanding requests and
retry queues. Scheduling must reserve or reclaim sufficient capacity for the
forward path to retain its measured headroom; a low-priority label alone is
insufficient. Pause, throttle or discard/re-request optional historical work
when its bounds are reached. Missing historical data may remain unavailable
indefinitely without stopping an otherwise supported forward sync, causing
unbounded retries/spool growth, or falsely reporting historical completeness.
Bounded history retention is separate from live-state size, which still needs
its own resource budget.

Reverse peeling and archive backfill are different operations. Reverse peeling
reconstructs/checks predecessor state and its verification boundary using
state/undo/proof obligations; fetching and authenticating old block bodies into
an archive does not accomplish that state verification. Neither an archived
body nor a checksum substitutes for undo, full validation or snapshot trust.
Concurrent historical verification must use independently managed historical
state/progress and preserve the active forward state and live tip. This
specification does not authorize rolling the active state backwards alongside
forward connection. Existing reverse-peel code must demonstrate that isolation
and its restart semantics before concurrent use is claimed safe.

#### Historical verification policy: root checks by default, full replay opt-in

Maintainer direction, 2026-10-20, **provisional before and through testnet**:
backwards synchronization should default to authenticated root-transition
verification; executing historical transactions and signatures should be a
separate opt-in verification track. Full historical replay and reaching genesis
are not prerequisites for forward catch-up. This is a proposed local
synchronization/assurance policy, not a relaxation of block consensus or an
assertion that a suitable proof protocol is already deployed.

Every newly connected forward block, including post-bootstrap catch-up blocks,
MUST still undergo the existing full transaction, script/signature, monetary,
state-transition and contextual validation rules. Selecting the historical
root-check track cannot disable those checks. Historical execution omitted by
the selected bootstrap policy must be disclosed rather than reported as having
passed. The assurance levels are distinct:

| Track | What it establishes | What it does not establish |
| --- | --- | --- |
| Archived body checked | Retrieved canonical bytes match the authenticated block/body commitments | Correct state updates, transaction authorization or monetary validity |
| Historical root transition checked | Under the selected proof contract, block-derived updates connect the authenticated predecessor and successor state commitments | Successful execution of omitted scripts/signatures or all monetary/transaction consensus rules |
| Historical full execution verified | The historical blocks passed the applicable full consensus execution with authenticated required context | Trust in any earlier bootstrap/history that this execution did not cover |

The root-transition proof contract remains to be specified and independently
validated. A proof that an arbitrary supplied update list changes root A into
root B is insufficient. It must bind the updates to the actual committed block
and account for required consumed coins, creation/nonmembership checks,
in-block dependencies and applicable delayed coinbase effects. Exact treatment
of expired-coin sweeps, deterministic sweep selection and completeness, omitted
or extra updates, and all required witnesses is still a design obligation.
Authentication covers the full `StateRoot` envelope and its non-UTXO components,
including `MonetaryState`, not just a pair of UTXO roots. Authenticating monetary
field values is different from executing and proving every rule governing their
change. The design must enumerate which checks it performs, which proof
establishes them and which omitted validity judgments depend on the admitted
bootstrap anchor; it must not claim authorization or supply validity merely
from root equality. No proof wire format is selected here.

The default remains conditional on an explicitly admitted authenticated
snapshot, chain identity and header ancestry with the required PoW/context
checks, plus any finalization anchor required by the chosen bootstrap profile.
PoW and state commitments alone do not cryptographically prove all past
transactions valid. Counting a majority of connected peer nodes is not a trust
proof: connections can be Sybils or eclipse the node. Any reliance on Avalanche
attestation must identify and satisfy the defined quorum, stake/proof,
finalization and bootstrap rules, with verifiable evidence; an informal claim
that most of the network accepts the chain cannot substitute for them. This
direction does not introduce a new trust anchor, define such a quorum, or claim
current attestations prove historical consensus execution.

Node status and any advertised assurance must retain the bootstrap provenance,
anchor identity and separate ranges/boundaries for body checks, root-transition
checks and full historical execution. Persist those distinctions through restart,
reorg and optional verification progress. Root checking MUST NOT set a
script-executed status such as `BLOCK_VALID_SCRIPTS`, advance a full-execution
watermark or erase the snapshot-derived provenance. Public RPC/service encoding
for these distinctions remains open; do not reuse an existing full-validation
claim to advertise a weaker track. An operator may enable full historical
execution later, subject to the same bounded low-priority scheduling. Any failure
must remain visible, not be relabeled successful by the weaker track; remediation
and invalid-history handling need an explicit implementation policy.

Acceptance tests must distinguish valid root updates containing unauthorized
historical spends from successful script execution; reject update/block
mismatches, missing/extra proof elements and unproven sweep completeness; cover
non-UTXO envelope tampering; and preserve separate provenance across restart.
Disabling full historical execution must leave mandatory forward validation
intact. These tests and proof completeness are open requirements, not evidence
that the existing reverse-peel implementation already meets this policy.

After downtime or restart, forward catch-up MUST resume from a consistent,
durable state under the supported profile. Persist and recover the active tip,
bootstrap identity and historical-verification/backfill progress distinctly;
retain atomic state/undo invariants and bounded, idempotent recovery work. If
required forward bodies have passed available retention, recovery needs an
available admissible bootstrap or another supported source under the same
trust contract; never invent missing history or reset verification status to
hide a gap. An indefinitely paused historical job must not prevent reopening
the node and resuming forward validation.

An optional block archive may retain older immutable bodies separately from
active validation state. The selected implementation direction is a filesystem
backend first, with explicit retention, durability and recovery semantics;
no S3 protocol/backend is mandated. Archive work inherits the bounds and
forward-priority requirements above. Any operator mode requiring successful
archival before local deletion must disclose its additional availability and
spool assumptions and safe failure behavior; it cannot both promise indefinite
archive outage tolerance and retain an unbounded required spool on bounded
local disk. Archive availability never establishes finality or authorizes
pruning required recovery data. Native logical horizon advancement and physical
body/undo reclamation require separate implementation evidence.

Required evidence before reporting this property implemented:

1. Admit the supported authenticated bootstrap and close a nonzero backlog
   while the eligible tip continues moving under the declared workload;
   demonstrate continuing tip tracking and measured positive headroom.
2. Exercise forward and historical work on the same node with a backlog larger
   than its historical quotas, slow/unavailable archive sources and competing
   services; verify bounded disk/memory/queues and preservation of forward
   progress. Treat historical data as unavailable for the entire run and
   specify indefinite waiting/retry bounds rather than inferring them from a
   short successful download.
3. Restart and interrupt the node during catch-up, during historical work and
   after progress; verify consistent active state, durable distinct progress
   boundaries, idempotent recovery and renewed catch-up after supported downtime.
4. For concurrent reverse peeling, compare live tip/state and forward results
   with a forward-only control, including restart partway through the peel.
   Verify predecessor-state authentication independently from archive retrieval.
5. Exercise missing required forward data and exceeded workload/resource
   assumptions: report the limitation explicitly, retain bounded recovery
   behavior and never claim complete history or synchronization falsely.

These are acceptance requirements, not completed test results. Existing
snapshot/reverse-peel primitives or successful small functional tests alone do
not establish sustained catch-up headroom, physical history reclamation,
indefinite historical-outage isolation or restart-safe concurrent operation.

### Generalized Merklix mempool reconciliation, `inv` queue deduplication, and Avalanche coordination (`Patches 023–041`)

Following the [bulk pre-consensus and mempool overlays specification](../plans/lotus-v2-bulk-preconsensus-and-mempool-overlays.md):
- **Generalized Merklix Set Reconciliation (`merklixsync`, `getmerklixbuck`, `merklixbuck`, `getshorttx`, `shorttx`):** Set reconciliation over `Subtree A` prefix buckets uses full 32-byte Merklix bucket roots paired with 16-byte $GF(2^{64})$ power-sum syndromes `(s1, s3)` over per-epoch keyed `SipHash-2-4(TxHash)` 64-bit `short_id`s, prefixed by a 1-byte `ReconScope` (`0x01 = PRECONSENSUS_EPOCH`, `0x02 = LIVE_MEMPOOL_SYNC`), and is handled by a dedicated, constructor-injected `V2PeerProtocolHandler` (`src/net/v2_protocol_handler.h/.cpp`). Every decoded candidate is gated by the **Strict 256-Bit Root-Verification Gate** (`recomputed_root_32B == peer_root_32B`) and full `MemPoolAccept` (`ProcessTransaction`) validation before `avalanche::Processor` can vote `0` (`ACCEPT`) on the candidate root.
- **`inv` Queue Deduplication & `getdata` Relay Tuning for 5-Second Epochs:** To allow incoming `inv` announcements from peers to populate `m_tx_inventory_known_filter` before flushing (suppressing redundant crossing `inv`s and batching announcements per TCP frame) without stalling 5-second pre-consensus epochs (`T_epoch = 5s`, `Stage 1 Ingest = 2.5s`), inbound `inv` trickling (`INBOUND_INVENTORY_BROADCAST_INTERVAL`) is tuned from `5s` to `500ms`, outbound `inv` relay uses a per-peer `150ms` queue window (`OUTBOUND_INVENTORY_BROADCAST_INTERVAL = 150ms`), non-preferred peer `getdata` delay (`nonpref_peer_delay`) is reduced from `2s` to `200ms`, `INVENTORY_BROADCAST_PER_SECOND` is raised from `7` to `250`, and `GETSHORTTX` (`shorttx`) serves any transaction in `CTxMemPool` belonging to an active `ReconScope` without waiting for `m_recently_announced_invs`.
- **Typed Avalanche Vote Items, Soft Coinbase Split (`50% Miner / 25% Staker / 25% Staker-Voted Treasury`), & Quorum / Relative-Stake Activation:** `avapoll` and `avaresponse` dispatch across `MSG_AVA_PROOF` (proofs), `MSG_BLOCK` (block finality/parking), `MSG_AVA_STAKE_CONTENDER` (`StakingRewardsPolicy`, ~25% staker coinbase share), `MSG_AVA_TREASURY_CONTENDER` (`TreasuryPolicy`, ~25% staker-voted treasury script share), and `MSG_AVA_MEMPOOL_BATCH` (`PreConsensusPolicy`, epoch/bucket Merklix roots) without altering deterministic consensus validity (`C16`) or removing application signatures over TCP/QUIC. Soft block-parking policies remain inactive during Genesis cold-start until `Processor::isQuorumEstablished()` is satisfied (minimum online Avalanche nodes, minimum connected stake ratio, and minimum staked coin fraction of live `MonetaryState.current_supply`, with zero block-height magic numbers).

## 8. QUIC milestone candidate (N07)

QUIC is the second milestone, after TCP has conformance and usable-development-chain evidence. Reuse the same application messages, object identities, validation interface and relay policies. QUIC supplies UDP-based reliable streams, flow control and path validation; TLS integration and application-protocol negotiation follow the primary specifications [RFC 9000](https://www.rfc-editor.org/rfc/rfc9000.html) and [RFC 9001](https://www.rfc-editor.org/rfc/rfc9001.html). The following mapping is a Lotus proposal, not behavior supplied by ABC.

- Use QUIC v1 with TLS 1.3, proposed ALPN `lotus-v2-dev/1` and UDP port 10605. ALPN is followed by the same ChainID/genesis/profile handshake. Do not tunnel arbitrary TCP bytes or reuse the 24-byte checksum envelope: application records are `command[12] || payload_length:u32 || payload`, with the same limits and codecs. TLS integrity replaces only the transport checksum.
- Client-initiated bidirectional stream 0 is the only control stream. Run version/hello/verack there. Carry control announcements, header synchronization, ping and addresses on it; allocate no bulk streams before activation. Every other stream is requester-initiated bidirectional and starts with exactly one existing `getdata` (one inventory item) or `getblocktxn` request. The responder sends one complete corresponding response record then FIN; requester sends FIN after its request. An object must fit the negotiated application receive limit, as on TCP; larger-object streaming remains N05 follow-up. Unsupported stream types or extra records reset that stream. Request/response association is the stream plus existing object IDs.
- Cap application bulk streams initially at 16 per connection, while retaining stricter object, bytes, queue and global quotas. Configure transport flow control from bounded receive buffers; give control traffic scheduling priority without assuming QUIC removes shared congestion or CPU contention. A lost bulk packet need not block a different stream, but all streams still share connection congestion control.
- Disable application 0-RTT initially. Require completed TLS and V2 identity negotiation before relay or stateful requests. Use library-provided Retry/address validation and anti-amplification protection; disable active migration initially, handling permitted NAT rebinding only after path validation. Do not invent cryptography, loss recovery or congestion control.
- Proposed development authentication is an explicitly configured peer certificate/public-key pin for test peers, with certificate possession checked by TLS. A pin authenticates that configured endpoint, not its advertised chain state. Public peer identity, certificate rotation/discovery and optional self-authenticated identities need a separate reviewed design before public QUIC rollout. An untrusted TCP advertisement cannot establish a trusted certificate pin.
- Initially configure QUIC endpoints explicitly; unchanged addr/addrv2 gossip continues to describe TCP endpoints only. Later transport-aware endpoint advertisements need their own allocation and tests. Preserve TCP fallback for configured endpoints that allow it, after bounded retries/backoff; a `require-quic` setting must not fall back. Do not claim downgrade protection for unauthenticated TCP discovery. The same remote endpoint over both transports does not count as two independent peers.

The QUIC library selection is open. Review maintained platform support, TLS integration, license, fuzzing, resource control, proxy behavior, deterministic tests, build/release dependencies and cancellation/shutdown before choosing an exact version. There is no assertion that existing SOCKS/Tor/I2P TCP support carries UDP QUIC; retain those routes on TCP. Milestone 2 requires loss/reordering/NAT/UDP-blocking tests and measurements against the working TCP baseline before default enablement.

## 9. Development-chain usability blockers and review decisions (N08)

The current `src/lotus_v2/dev_genesis.cpp` is an isolated construction fixture: header bits `0x1d00ffff`, time `0x010203040506`, nonce zero, size 134, empty transaction root, and monetary state reserve 9/tail 200/previous work 9/EMA 4. `dev_genesis.h` uses an all-zero fixture ChainID. Its comments explicitly say the function does not connect a block. These values do not demonstrate a mineable, accepted genesis or a chain that can fund the real coinbase/envelope resource charge. A header-only empty-transaction fixture is not P04's complete block with P01's first-and-only coinbase. The target encoded by `0x1d00ffff` yields work 4,295,032,833, not the fixture previous work 9. The current monetary profile's first subsidy is 202 atoms, while a minimal 101-byte legal coinbase plus the 134-byte header, four-byte count and one-byte transaction frame already requires 240 atoms of byte charge with no ordinary fees (242 for the minimal spendable-output form). The existing first-block entitlement therefore cannot fund that bare envelope. These are development-profile blockers, not permission to raise issuance silently. This proposal must not promote those constants to a network manifest.

Before a two-node testnet can be called usable, review a complete **development-only** parameter artifact and demonstrate genesis validation, exact initial state, target/work consistency, attainable test mining, realistic time eligibility, funded first-block coinbase/resource accounting, ordinary signed transactions, synchronization, restart and reorg. That artifact may select explicit test parameters after review; it must not silently choose mainnet issuance, ASERT anchor/half-life, initial work, ChainID, coinbase entitlement, maturity or seeds. D10–D14 stay open except for the maintainer's development port defaults.

The next review should accept or amend these concrete proposed choices: candidate magic; mandatory identity/profile handshake and its allocations; full-TxHash inventory; compact profile 2 with inherited SHA256/SipHash compression; receive-limit negotiation and the larger-object availability limitation; initial unsupported-service list; and the QUIC stream/authentication approach. Separately approve a usable development consensus/genesis profile. Until those reviews, networking implementation is a dependent task, not part of this document change.
