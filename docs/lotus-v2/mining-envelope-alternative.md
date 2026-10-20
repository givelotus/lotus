# Optional SHA256D mining envelope — discussion alternative

Status: **unselected design alternative, 2026-10-20; provisional through testnet**.
The maintainer requested discussion of existing Bitcoin ASIC reuse, not a PoW
selection or implementation. [P04](decisions/header-and-mining.md)'s current
134-byte recursive BLAKE3 header, work hash and BlockID remain unchanged.
This document does not enable a second accepted header or an optional per-block
algorithm. Selection would require an explicit consensus/profile decision and
its own migration or new-chain plan; a local miner cannot opt into it today.

## 80 bytes for hashing, 80 bits of proposed search space

“80-bit header” in the discussion refers to two separate quantities: an
**80-byte mining envelope** and a potential **80-bit variable search space**.
Bitcoin serializes a header with widths 4/32/32/4/4/4 bytes. The following
alternative uses those same field positions, while changing some meanings.
[Bitcoin header reference](https://developer.bitcoin.org/reference/block_chain.html)

| Offset | Bytes | Proposed field | Meaning |
| --- | ---: | --- | --- |
| 0 | 4 | `rolling_version` | Search bits plus any fixed envelope bits; not a vote on validity rules |
| 4 | 32 | `prev_id` | Previous block identity under the separately selected BlockID rule |
| 36 | 32 | `extension_commitment` | Binds the canonical extension below; not necessarily a Bitcoin transaction Merkle root |
| 68 | 4 | `work_extra` | Additional search word in the former `nTime` position; not the consensus timestamp |
| 72 | 4 | `bits` | Compact target, contextually validated; not a free search word |
| 76 | 4 | `nonce` | Conventional 32-bit search word |

All fixed-width integers are unsigned little-endian. Hashes are raw digest
bytes; display reversal and controller word swapping are interface conversions,
not changes to the consensus byte string. The proposed work function is exactly
`SHA256(SHA256(envelope[0:80]))`. There is no Lotus prefix, suffix or extension
appended to that SHA256D input, and no BLAKE3 operation is added to the ASIC's
nonce loop. SHA256's ordinary internal padding still applies. The CPU computes
BLAKE3 commitments when constructing or checking jobs.

With 32 freely variable nonce bits, 32 freely variable `work_extra` bits and
16 freely variable `rolling_version` bits, one fixed extension/parent/target
has `2^80` distinct search inputs. A variant repurposing all 32 version-position
bits would have `2^96`. These are format capacities, not a promise that an S9
chip exposes an 80- or 96-bit hardware counter, or that a controller can drive
every combination at rated speed. The actual rolling mask, fixed bits and job
partitioning remain open. Work allocation must avoid duplicate ranges across
workers and reject returned changes outside the assigned mask.

## An explicit committed-extension candidate

A concrete example encoding makes missing-field and size tradeoffs reviewable;
it is not a new registered consensus encoding:

```
Extension = format:u16(1) || ChainID:h32 || rules_version:u32
            || actual_time:u48 || height:u64 || size:u64
            || tx_root:h32 || state_root:h32                    # 124 bytes

extension_commitment = BLAKE3(
    ASCII("Lotus/v2/mining-envelope/extension") || 00 || Extension)

Envelope = rolling_version:u32 || prev_id:h32
           || extension_commitment:h32 || work_extra:u32
           || bits:u32 || nonce:u32                             # 80 bytes
```

The format marker distinguishes the extension grammar. ChainID and the domain
separate chains and uses. `rules_version` carries the semantic header version
currently present in P04; freely rolled bits cannot replace it. The extension
retains the real 48-bit timestamp, explicit height and size, transaction root
and full state root. Parent linkage and target are directly in the envelope;
the larger search space replaces the current nonce. No current semantic header
field is silently omitted. BLAKE3 remains available for the native transaction,
state, branch and other internal commitments; the proposed exception is ASIC
PoW, not a wholesale conversion of the protocol to SHA256D.

If the complete candidate header is `Envelope || Extension`, it is **204 bytes**,
not 80. A candidate complete block could then be that header followed by the
existing transaction count and framed transactions. `size` must describe the
exact complete block encoding, including the extension, rather than just the
ASIC input. Extension framing/transport and any alternative placement still
need selection. The fixed widths avoid a hash self-reference: the extension
contains a size, not its own digest. A commitment-only disclosure is smaller
than full validation data; it does not make the extension dispensable.

For full acceptance, a validator must obtain the canonical extension, recompute
its commitment, enforce the selected ChainID/format/rules version, verify the
parent and derived height, check the real timestamp and expected target under
the selected chain rules, and validate size, transactions and state transition.
PoW-only success never establishes those facts. Using `work_extra` for entropy
must not weaken time validity: time/ASERT/MTP processing would use
`actual_time`, not the envelope word at offset 68. Changing the real timestamp
changes the commitment and requires a new job.

**Block identity remains open.** One candidate is `BlockID = SHA256D(Envelope)`,
so the work digest also identifies the envelope and its committed extension.
Another is a separately domain-separated BLAKE3 identity binding ChainID and
the entire envelope; SHA256D remains the independently checked PoW digest.
The latter requires careful separation of PoW comparison, accumulated work,
parent pointers and all ID-consuming protocols. Neither alternative is selected
here. The candidate target comparison would interpret the SHA256D digest as an
unsigned little-endian integer and retain a reviewed canonical compact target
and chainwork rule. Difficulty constants and existing BLAKE3 performance
calibration cannot simply be assumed appropriate after changing mining hardware.

## ASIC, firmware and pool compatibility are separate gates

[BIP310](https://bips.dev/310/) defines Stratum version-rolling negotiation,
including masks agreed between miner and pool. [BIP320](https://bips.dev/320/)
describes 16 general-use version bits, mask `0x1fffe000`. Its proposed
replacement, [BIP323](https://bips.dev/323/), is currently Draft and proposes
24 bits, mask `0x1fffffe0`. These documents do not prove that a particular S9
board, firmware or controller implements either mask or all search fields.
A Lotus-specific rolling allocation need not copy Bitcoin's signaling rules,
but must be supported by the chosen device interface.

The ASIC datapath may enumerate nonce and supported version variants, while
the controller supplies new work for `nTime`-position changes, new midstates
or fresh jobs. Which fields change in hardware versus controller software is
firmware/device-specific and must be measured. A controller may constrain the
former time field to plausible timestamps or increments, so repurposing it as
a fully independent 32-bit counter is an adapter/firmware requirement, not a
consequence of matching the 80-byte length. A model-specific source audit and
real-device test are required before any S9 support claim.

### Node-built jobs and focused controller adaptation

The intended division of work is **node-built commitments, miner-side header
search**. The node already constructs the native block template and its
transaction/state commitments. In this alternative, it would assemble the full
canonical extension, compute its commitment and supply a completed 80-byte work
envelope, with a job identifier, allowed rolling fields/ranges and share target.
The extension and full block template remain fixed for that job and available
at the node/pool for validation and complete-block submission. Providing them
to a mining client for inspection is possible; requiring that client to rebuild
them is not part of this architecture. Miners do not construct the coinbase,
transaction Merklix tree or extension to search that assigned job.

A controller or host adapter consumes this node-provided work, partitions the
permitted search space across devices, prepares whatever device-specific jobs
or midstates the chips require, and returns the solved rolling words/nonce
against the job ID. Exhausting a chip's 32-bit nonce range can require another
**chip work assignment**, without requiring a new node template, coinbase or
extension: the controller advances another permitted rolling field within the
same job. The distinction between node jobs and chip assignments matters.
The proposed 80- or 96-bit space is finite; coverage time is `2^b / H` seconds
for `b` independent assigned bits at aggregate rate `H` hashes/second, ignoring
overlap and overhead. No infinite-space or never-exhausted claim is made.
If the controller can use the expanded space efficiently, new node jobs would
normally follow parent, transaction/template, payout or real-timestamp changes,
rather than exhaustion of the 32-bit nonce alone. Restricted masks, partition
sizes, controller throughput and duplicate work can reduce useful coverage and
must be measured.

Existing Stratum **job construction** needs adaptation, not necessarily its
whole session or share-handling design. The original
[Stratum proxy implementation](https://github.com/slush0/stratum-mining-proxy/blob/master/mining_libs/jobs.py)
builds a coinbase from supplied parts and extranonces, hashes it, combines
SHA256D Merkle branches and inserts the result into the header; it also
constructs `nTime` in the controller. The proposed adapter replaces that
coinbase/extranonce/Merkle-root job generator with the completed node-provided
header and extension commitment. Stratum framing, session management, target
assignment and share-accounting concepts can be reused, with explicit job and
submission semantics for these rolling fields. Exact messages and negotiation
still need specification; an unmodified client cannot be assumed to interpret
the changed job correctly.

A Bitcoin-style SHA256 coinbase/Merkle wrapper is **not required** merely to
accommodate an unchanged client. Such a wrapper is an optional, distinct
compatibility alternative only if retaining that client's construction path
justifies it; it would require its own commitment and validation design.
The direct-commitment design requires no SHA256 preimage trick. Controller
adaptation is focused on job preparation, allowed-field scheduling and solution
reporting, but this scope does not prove every proprietary firmware change
trivial or every ASIC's field controls sufficient.

A proposed shared pool manager could retain templates and job assignments,
authenticate workers, set share targets, reject duplicate/stale/invalid shares
and submit complete blocks, with native browser-protocol and adapted Stratum
front ends feeding that same manager. Transport adapters must normalize the
same exact header bytes, job identity and allowed search ranges; using another
front end does not alter PoW or payout validation. This is a candidate
architecture, not a claim of implemented ASIC or browser/Stratum interoperability.
The node/pool must reconstruct the submitted envelope, verify mask, share/block
target and extension commitment, and run complete block validation. Real-device
controller throughput and end-to-end submission remain acceptance gates.

## Upgrade policy and mining economics

The maintainer prefers discussing height-driven upgrades rather than reserving
search bits for miner signaling. Under this alternative, rolled bits would not
activate or veto validity rules; any future height-based activation policy
would need its own explicit decision and review. This document introduces no
activation schedule and does not change P03 extension semantics. Bitcoin's
version-bit activation mechanisms were used, not merely proposed: Bitcoin
Core 0.13.1 shipped SegWit activation parameters using BIP9. That history neither
requires Lotus to copy the mechanism nor supplies a Lotus governance policy.
[Bitcoin Core release notes](https://bitcoincore.org/en/releases/0.13.1/)

The following are conditional design/economic considerations, not forecasts:

- Reusing existing SHA256 hardware could reduce the need for a bespoke miner
  ecosystem and give hardware owners another use for installed equipment.
  Competitive SHA256 ASIC participation would greatly reduce the practical
  competitive role of ordinary GPU/browser mining; demonstration or educational
  mining is a different objective from meaningful revenue or security share.
- A shared hash algorithm creates both a potential source of honest mining and
  a source of rapidly switchable external hashpower. Security depends on Lotus's
  sustained honest hashpower relative to available switching/rental capacity,
  opportunity costs, rewards and attack incentives. It does not inherit
  Bitcoin's security merely by using the same algorithm. Availability and price
  of attack capacity must be investigated, not presumed unlimited or negligible.
- Hardware supply, power costs, pool/controller dependence and operator scale
  affect concentration. Existing ASIC reuse does not make either decentralization
  or concentration inevitable. Evaluate sustained participation and geographic,
  ownership and pool concentration rather than counting compatible devices.
- Miners may value liquid markets to cover operating costs, which could create
  demand for exchange support. Listings and liquidity remain third-party business
  decisions; ASIC compatibility guarantees neither. Selling pressure, reliance
  on a few venues/pools and incentives to switch away are corresponding costs.
  No price appreciation or mining-profit claim follows from this design.

## Open decisions and acceptance gates

Reject the shortcuts “80 bytes means stock ASIC/Stratum compatibility,” “all
80 search bits are hardware counters,” “PoW validates an absent extension,”
and “shared SHA256 means automatic security.” Preserve P04 until an explicit
selection supersedes it. Before selection, require:

1. An exact selected envelope/extension grammar, rolling allocation, BlockID
   rule, complete-block layout, target/time treatment and chain/profile transition
   plan. Define every consumer affected by replacing current header IDs.
2. Independent byte and hash vectors, including SHA256D of exactly 80 bytes,
   extension/ChainID mutations, every field boundary, endianness, rolling-mask
   rejection, false target/height/time/size claims, missing/malformed extensions
   and complete-block validation. These vectors are required future evidence;
   none are asserted supplied or executed by this discussion document.
3. A CPU reference and independently checked controller/share reconstruction;
   real named ASIC/firmware measurements of sustained hashrate, job turnover,
   controller CPU/bandwidth, supported masks, stale/duplicate shares and recovery.
   Compare nonce-only, version-rolled and controller-driven extra-word changes.
4. Pool/adapter tests with full Lotus block submission and validation, including
   extension availability, stale jobs, malicious shares and competing workers.
   Test the actual chosen Stratum path, not just a synthetic SHA256 benchmark.
5. A comparative security and participation analysis against retaining BLAKE3,
   including external switching attacks, difficulty response, concentration,
   GPU/browser participation tradeoffs and development/operational costs.

This is a discussion record only: no daemon/miner source, consensus profile,
production node, genesis, header fixture or existing P04 hash vector is changed.
