# Header design from Lotus v1's useful properties

Decision packet P04, October 9, 2026. **Recommended candidate**, not frozen. Refines D12/D14. The maintainer clarified that v2 need not preserve a deployed ASIC interface, that the lucky-block pointer is not useful to the intended design, and that v1's recursive hashes were chosen to reveal useful header portions without Merkle-path overhead. Preserve that rationale while evaluating a new layout.

## Verified v1 source evidence

Historical patch `daemon/patches/v1/094-new-lotus-block-header.patch`, original commit `fb997e62174368720901d4af7a8b312f5970f68f`, introduces this layout. The local historical workspace's `src/primitives/block.h/.cpp` corroborates it; this is source evidence, not a new live-network test.

| V1 field | Bytes | Purpose |
| --- | ---: | --- |
| Previous block | 32 | Chain linkage |
| Compact target | 4 | Work target |
| Timestamp | 6 | **Unsigned 48-bit little-endian seconds**, not Bitcoin's 32-bit timestamp |
| Reserved | 2 | Required reserved value |
| Nonce | 8 | Larger search space, less frequent template/coinbase mutation |
| Header version | 1 | Versioned remainder |
| Advertised block size | 7 | Early size/context validation |
| Height | 4 | Header-committed height |
| Epoch/lucky-block pointer | 32 | Historical sparse-chain/epoch design |
| Transaction root | 32 | Transaction commitment |
| Extended metadata root | 32 | Metadata commitment |
| **Total** | **160** | Explicit wire serialization, not C++ struct size |

V1 hashes three groups using SHA256: body fields → work fields plus body hash → previous-block hash plus work hash. Its patch already contains functional cases at 2^32 and 2^48−1 seconds. Forty-eight bits spans roughly 8.9 million years of seconds. The earlier v2 draft's 32-bit timestamp was a regression, not an unsolved v1 limitation. Existing SetBlockTime masks six bytes; v2 encoders should reject out-of-range arguments rather than silently truncate them.

## Recommended field treatment

Remove the epoch/lucky-block pointer. Replace the old metadata commitment with the full state commitment described by P02. Retain explicit target, timestamp, height, size and the 64-bit nonce because each has a concrete validation/mining role. Do not retain unused reserved bytes as an implied post-genesis extension mechanism.

For the candidate, keep v1's six-byte timestamp (u48, unsigned little-endian seconds) and its 64-bit nonce, and use ordinary widths elsewhere: version u32, height/size u64. Forty-eight bits spans roughly 8.9 million years, so a wider timestamp buys nothing. A 64-bit nonce gives 2^64 attempts per template per timestamp second. No single mining device approaches that rate, so a pool that hands each worker its own template (for example a per-worker tag placed in a coinbase output as an extra branch root that no path uses, the role extranonce1 plays in Bitcoin pools) never exhausts it; a pool sharing one template among all workers would need more than about 18 EH/s in aggregate to do so. A wider nonce is therefore not needed. Neither format can prevent a miner choosing to mutate coinbase or timestamp for other reasons.

Recommend **recursive field groups**, not a Merkle leaf per header field. This preserves short ancestry/work disclosures. Mainnet selection still requires reference vectors and mining/tooling cost measurements; no deployed-ASIC compatibility constrains that selection.

## Concrete recursive candidate (134 bytes)

```text
Header = prev_id:h32 || bits:u32 || time:u48 || nonce:u64
         || version:u32(2) || size:u64 || height:u64
         || tx_root:h32 || state_root:h32

Body = version:u32 || size:u64 || height:u64 || tx_root:h32 || state_root:h32
BodyHash = H_headerbody(ChainID || Body)
Work = bits:u32 || time:u48 || nonce:u64 || BodyHash:h32
WorkHash = H_headerwork(Work)
BlockID = H_blockid(prev_id:h32 || WorkHash:h32)
```

Extend P02's registry with `headerbody = Lotus/v2/header/body` and `headerwork = Lotus/v2/header/work`. BlockID is proposed as the PoW digest as well as chain identity. This is a new BLAKE3-based PoW candidate, not wire/hash compatibility with v1. Each layer uses the application hash definition; do not substitute raw, double, keyed or derive-key BLAKE3.

Body is 84 bytes; explicit work fields are 18 bytes; previous ID is 32 bytes. A complete block is `Header || transaction_count:u32 || Bytes(Tx)[transaction_count]`. Every framed transaction must consume its frame exactly. Size is the exact encoded block length including header, counts and framing; height equals parent.height+1 (genesis zero); parent ID must match the selected parent; tx_root and state_root must match full validation. Validate all declared sizes against limits before allocating. Header-only size/root claims remain unverified until the body/state transition is checked.

Genesis has zero previous ID, selected initial target/time and a specified initial monetary state. Header version and ChainID are fixed by the chain's manifest. No unvalidated header field is trusted merely because its PoW passes.

### Useful partial disclosures

Given a trusted or independently validated BlockID:

| Claim disclosed | Bytes, excluding enclosing framing | Reconstruction |
| --- | ---: | --- |
| Previous ID only | 64 | prev_id + WorkHash |
| Previous ID, target, time and nonce | 82 | prev_id + 18 work bytes + BodyHash |
| Body fields including transaction/state roots | 134 | Complete header fields are needed for this layout |

The first two cases preserve the reason for v1's recursion. The layout does not make an isolated state-root proof smaller than the header. A UTXO proof additionally connects its map root to the full state envelope and that header's state_root. Proving a hash relationship does not prove the referenced chain's validity or work ancestry.

## Alternatives compared on the same candidate fields

| Design | Header bytes | Per-field disclosure | Tradeoff |
| --- | ---: | --- | --- |
| Flat `H_blockid(ChainID || Header)` | 134 | Supply header (134 bytes) and parse fixed offsets | Least hash-structure complexity; fixed prefixes can be precomputed when nonce is last |
| Recommended recursive groups | 134 | 64-byte linkage or 82-byte work disclosure | Preserves useful script/light-client boundary; more hash layers |
| Fully field-Merkleized template plus nonce | 134 | Three siblings for the eight template fields | General field proofs often exceed the complete header; useful only with demonstrated composability/reuse benefits |

For the Merkle alternative, a 32-byte field plus three 32-byte siblings plus the 8-byte nonce is already **136 bytes**, more than the whole 134-byte header, before its selector/framing. A compact header and a large transaction/state tree do not have the same proof economics. Do not select the Merkle alternative merely because state commitments themselves use a tree.

Nonce changes do not require recomputing body/transaction/state commitments in the recursive design. Flat hashing also permits prefix caching; recursive hashing has no assumed mining-speed advantage. Count compression work and benchmark actual implementations rather than comparing only the number of top-level hash calls. Separately measure timestamp changes, new transaction templates, pool job turnover, light-client/script verification and hardware implementation complexity.

## Target encoding and chainwork candidate

Interpret BlockID as an unsigned little-endian 256-bit integer; valid PoW requires `value <= T`. Compact target encoding uses unsigned exponent e (high byte) and 23-bit mantissa m (low bits); the sign bit must be zero. Decode T as `m >> (8*(3−e))` when e≤3 and `m << (8*(e−3))` otherwise. Reject zero, overflow beyond 256 bits and T>POW_LIMIT. Require canonical re-encoding: set e=ceil(bit_length(T)/8); set m=T<<[8*(3−e)] if e≤3, otherwise m=T>>[8*(e−3)]; if m has bit 23 set, shift m right by eight and increment e. Return (e<<24)|m. Decoding and re-encoding must reproduce bits.

Per-block chainwork is `floor(2^256/(T+1))`, with mathematical or sufficiently wide intermediates. Accumulate without wrapping. Prefer greatest accumulated work among fully valid eligible chains. At equal work retain the current valid tip; nodes may temporarily choose different equal-work tips. Advisory voting cannot override a strictly heavier eligible chain. The candidate ASERT arithmetic below fixes the algorithm and anchor. Half-life/powLimit and future-time eligibility values still need acceptance/calibration.

## ASERT arithmetic candidate

Reuse the bounded integer ASERT polynomial already present in the historical Lotus `src/pow/aserti32d.cpp`, with a **new fixed genesis anchor**. The historical implementation chooses the first post-genesis block as anchor; this candidate deliberately removes that bootstrap dependency for a new chain. V1 retains its historical rule.

Let T0 be the decoded canonical genesis target, t0 its timestamp, p the validated parent, τ=120 seconds and H>0 the half-life parameter. For every non-genesis candidate:

```text
drift = p.time - t0 - τ*p.height
E = trunc_toward_zero(65536*drift/H)
q = floor(E/65536)
f = E - 65536*q                         # 0..65535
factor = 65536 + floor((195766423245049*f
         + 971821376*f*f + 5127*f*f*f + 2^47)/2^48)
V = T0*factor
raw_target = floor(V * 2^(q-16))
clamped = min(POW_LIMIT, max(1, raw_target))
required_bits = CompactEncode(clamped)
```

This fixes the integer approximation itself, not just a real-valued exponential. Require block.bits=required_bits. Use the **decoded** target from those bits for PoW and work, since compact encoding can round the unclipped integer downward. Genesis uses its manifest's fixed target and is not passed through this non-genesis rule. An on-schedule parent's drift is zero, so block one and subsequent on-schedule blocks retain T0. There is no timestamp-triggered testnet minimum-difficulty exception; different development chains use explicit separate parameters.

Signed time/height drift uses at least signed 128-bit arithmetic; do not subtract u64 fields in unsigned arithmetic. V needs at most 273 bits when T0<2^256. Huge exponent values must **not** allocate exponentially sized integers: for a nonnegative shift, compare to POW_LIMIT before shifting (a shift ≥256 already saturates); for a negative shift with magnitude ≥bit_length(V), raw_target is zero. Remaining shifts/intermediates have bounded size. Round the exponent toward zero, then decompose it with floor division: those two operations are intentionally different for negative drift.

Test zero drift, exact ±H drift, negative fractional exponents, powLimit saturation, minimum target, compact rounding and very large time/height differences in independent implementations. Half-life 172800 seconds (two days) is the working value, carried from Lotus v1. A simple simulation (`tools/asert_sim.py`) supports it over shorter values: the gap between actual and target block time halves once per half-life after a hashrate shock, so two days recovers slowly (about 6.3 days to come within twice the target after 90% of hashrate leaves), but half-lives of six hours or less oscillate violently against profit-switching miners who react with a lag of hours, and one day does so under stronger switching. The model omits reward-difficulty coupling and timestamp manipulation, so the value is not yet a calibration.

## Timestamp eligibility candidate and open parameters

Width is independent of timestamp incentive design. Recommend the median rule: `time > MTP(parent)`, with MTP as defined in P01 (median of up to the last eleven ancestor timestamps including the parent). A timestamp may therefore be earlier than its parent's. This matters when a miner dates a block ahead of real time: under a nondecreasing-parent rule every later miner would have to copy that false time until the clock caught up, while under the median rule they can report the true time at once. A rule that consults the node's present time to choose between the two is not a consensus rule, because nodes validating later see a different present. The parent-derived DAA above uses signed drift and accepts decreasing timestamps. The current miner's timestamp does not select its own required target. That helps define the economic analysis but is not a truthfulness proof.

Distinguish deterministic header/transition validity from **temporary future-time eligibility**. A proposed network rule defers a header whose timestamp exceeds the node's current UTC plus a frozen FUTURE_SKEW_SECONDS; it does not mark the header permanently invalid or discard descendants as consensus-invalid. Reconsider when time advances. The implementation must document clock rollback, restart, eligibility of ancestor chains and timestamp overflow. Exact skew, clock source/assumptions and those operational semantics remain OPEN. Do not quietly call a local wall-clock predicate a pure function of chain history.

A selected future-time rule must be shared by the economic/network model and node tests. Until then, reference transition evaluation can implement the deterministic part with eligibility as an explicit external result, but cannot claim a complete production chain-selection implementation.

## Acceptance

Before closure: recompute v1 source layout/hashes and carry forward its timestamp fixtures; generate independent v2 full/partial hash vectors; measure hashing/pool/script costs; independently check the specified target/ASERT candidate; freeze time eligibility and genesis values. The 134-byte candidate is an explicit proposal for review, not a new silently assumed constant in daemon code.
