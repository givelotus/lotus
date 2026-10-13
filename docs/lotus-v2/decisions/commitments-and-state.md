# Hash commitments and authenticated state

Decision packet P02, October 9, 2026. **Recommended candidate**, not frozen or implemented. Refines D02/D13 and the commitment part of D14. Defines separate branch, ordered-vector and keyed-map commitments rather than one ambiguous “Merklix” API.

## Hash registry

`B3` is unkeyed BLAKE3 with exactly 32 output bytes. `H_name(x)=B3(ASCII(tag) || 00 || x)`. All tags are case-sensitive ASCII strings below. Prefix bytes such as `00` in node encodings are bytes, not characters. Integer encodings are P01 little-endian; where two hashes are ordered they are read as unsigned little-endian integers. No hash function accepts arbitrary C++ struct memory.

| name | Exact tag |
| --- | --- |
| branch | `Lotus/v2/branch` |
| txid | `Lotus/v2/txid` |
| txhash | `Lotus/v2/txhash` |
| sighash | `Lotus/v2/sighash` |
| spentoutputs | `Lotus/v2/spentoutputs` |
| owninput | `Lotus/v2/owninput` |
| outputs | `Lotus/v2/outputs` |
| output | `Lotus/v2/output` |
| txroot | `Lotus/v2/txroot` |
| outpointkey | `Lotus/v2/outpointkey` |
| utxo | `Lotus/v2/utxo` |
| state | `Lotus/v2/state` |
| blockid | `Lotus/v2/blockid` |
| merkleidx | `Lotus/v2/merkleidx` |

The BLAKE3 primitive follows its [specification](https://github.com/BLAKE3-team/BLAKE3-specs/blob/master/blake3.pdf); application tags and tree rules are Lotus choices. [P04](header-and-mining.md) specifies a recursive BlockID/PoW candidate and its additional headerbody/headerwork domains; final choice remains D12. Hash collision resistance is an assumption, not a theorem about these tags.

## Branch MAST: unordered membership

```text
Leaf(script) = H_branch(00 || Bytes(script))
BranchNode(a,b) = H_branch(01 || min(a,b) || max(a,b))
```

`min` and `max` compare the two 32-byte hashes as unsigned little-endian 256-bit integers: the last byte is the most significant. This is the same reading of a hash that P04 uses to compare a BlockID with its target, and the byte order of every integer in the transaction format and the VM.

Spend and mint invocations use the same leaf function. Consensus therefore does not distinguish a mint script from a spend script: any leaf of a tree can be proven in either kind of invocation. A design that needs both must keep them in **separate trees**. A token's mint scripts form the tree whose root is the token ID; rules that must run on every spend form a second tree that appears on outputs as a branch, and the mint scripts name that second root as a constant. A mint script placed in a tree that outputs use as a required branch could be offered to satisfy that branch. Consume siblings bottom-up, hashing once per sibling. Empty sibling vector means root=Leaf(script). A proof only asserts membership; it has no direction bits, method index, hidden leaf-count claim or hidden uniqueness claim. Consensus limits proof depth; no unverified tree metadata enlarges that bound.

For reproducible wallet construction, recommend: sort distinct leaf hashes as unsigned little-endian integers, ascending; split a list of n>1 at the greatest power of two less than n; recursively build and sort each child pair at hashing. This construction is a wallet convention, not a property enforceable from a single proof. An owner may commit another finite binary tree. Duplicated leaves or alternative shapes provide no independent authorization and receive no accounting discount.

### Storing data and Merkle roots in branches: three patterns

Outputs carry no separate state field. Contracts and protocols commit data or Merkle roots in `branches` and verify Merkle proofs against them (`MERKLEROOT_SORTED` `0xee`, `MERKLEROOT_INDEXED` `0xef`, `LEAFHASH` `0xea`, `NODEHASH` `0xed`) in three complementary ways:

1. **On a pruneable burn / `OP_RETURN` output (`flags = 0x02` native or `0x03` token, `paths = []`):**
   - Setting bit 1 (`0x02` `IS_BURN`) requires `path_count == 0` (`paths = []`) and `1 <= branch_count <= 16` pairwise distinct 32-byte entries in `branches` (up to 512 bytes of commitment hashes, Merkle roots, or topic/data words).
   - 100% of `value` on an `IS_BURN` output is permanently burned (included in `O_a`, never claimable by miners as fees; `value = 0` is also valid), and validators **never insert `IS_BURN` outputs into `UtxoRoot`** (`C17`), so they consume zero UTXO memory forever.
   - Scripts in the creating transaction can inspect an `IS_BURN` output `j` via `OUTPUTFLAGS(j)`, `OUTPUTVALUE(j)`, `OUTPUTTOKENID(j)`, `OUTPUTBRANCHCOUNT(j)`, and `OUTPUTBRANCH(j, k)`—and can verify Merkle proofs against `OUTPUTBRANCH(j, k)` using `MERKLEROOT_SORTED` or `MERKLEROOT_INDEXED`—making `IS_BURN` outputs ideal for Frank/Stamp topic broadcasts, burn-weighted votes, and verified on-chain data commitments.
2. **As a dedicated unexecuted data branch on a spendable coin (`branches = [CodeRoot, StateMerkleRoot]`, `paths = [[0]]`):**
   - Because `paths = [[0]]` requires only `branch[0]` (`CodeRoot`), `branch[1]` (`StateMerkleRoot`) is never executed as a script—it acts as a direct 32-byte state or Merkle-root register on the coin (or up to 15 registers `branch[1..15]`).
   - Methods in `CodeRoot` read the current root in $O(1)$ via `INPUTINDEX <1> UTXOBRANCH`, verify or update leaves using `MERKLEROOT_INDEXED` (`0xef`) or `MERKLEROOT_SORTED` (`0xee`), and require the successor output `j` to carry the updated root at `OUTPUTBRANCH(j, 1)` while `branch[0]` (`CodeRoot`) never changes.
3. **Inside the executing branch tree itself (`BranchNode(DataLeaf, M)`, the data-leaf convention):**
   - For the most compact 1-branch coin (45 bytes native / 77 bytes token, `branches = [root]`, `paths = [[0]]`), a contract places its state as one leaf beside the subtree `M` of its methods:
     ```text
     DataLeaf(values) = Leaf(data_script(values))      # pushes of the values, then RETURN
     root             = BranchNode(DataLeaf(values), M)   # M = root of the methods subtree
     ```
   - `M` never changes; `root` changes whenever `values` do. The data script ends in `RETURN` (`0x6a`) so that it can never be run as a method. The spender supplies the current `values` and `M` as witness arguments, and the method checks `BranchNode(Leaf(data_script(values)), M) == BRANCHROOT` using `LEAFHASH` and `NODEHASH`, then requires `BranchNode(Leaf(data_script(new_values)), M)` on the successor output with `OUTPUTCONTINUESBRANCH` (`0xcf`) or `OUTPUTEXCLUSIVEBRANCH` (`0xcb`). The cost is two leaf hashes and two node hashes per spend, whatever the number of methods, and a method's membership proof is one sibling longer than it would be without state.

Patterns 2 and 3 are compiler/application conventions recorded in the contract's ABI; pattern 1 (`IS_BURN` `0x02`/`0x03`) has consensus-enforced `path_count == 0` and UTXO pruning (`C05`, `C09`, `C17`).

## Block transaction vector: ordered, count-bound tree

Let transaction i, including the first coinbase, have the 64-byte leaf value `w_i = TxHash_i || TxID_i`. Define `T(xs)`:

```text
T([])  = H_txroot(02)
T([w]) = H_txroot(00 || w)
T(xs), n>1:
    k = greatest power of two strictly less than n
    return H_txroot(01 || T(xs[0:k]) || T(xs[k:n]))
TxRoot(xs) = H_txroot(03 || u32(n) || T(xs))
```

Each leaf commits to both identities of its transaction, TxHash first, as Lotus v1's block tree does. The TxHash fixes the complete bytes, witnesses included; the TxID lets a proof show that a transaction ID, and therefore its outpoints, is in a block by supplying the two 32-byte hashes, without the transaction or its witnesses. Children are ordered; no sorting, duplication or zero-padding occurs. Empty vector has a defined commitment for tools, but a block with no coinbase is invalid. Count is bounded before construction. This split strategy follows the ordered-tree principle in [RFC 6962 §2.1](https://www.rfc-editor.org/rfc/rfc6962#section-2.1); Lotus adds its own context and count wrapper and uses BLAKE3.

A transaction inclusion proof is `count:u32 || index:u32 || Vec(h32 siblings)` plus the transaction bytes, or the TxHash and TxID pair, being proved. A verifier given only the pair learns that the TxID is committed, not that the TxHash it was given corresponds to any particular witness bytes. Require `0 <= index < count`, count within the consensus block-transaction limit, and exact sibling consumption. Reconstruct recursively: for n=1 use the leaf; otherwise compute k, recurse into the child containing index, consume the next sibling from the bottom-up proof, and combine left/right according to index<k. Finally apply the count wrapper. No direction mask is serialized; count and index determine every direction. A proof API must clearly distinguish committed transaction membership from complete transaction/block validity.

## UTXO map: compact single-leaf-collapsed sparse binary tree

Use a 256-bit keyed sparse binary tree with single-leaf subtree collapsing as the normative `UtxoRoot` algorithm. Collapsing every single-leaf subtree to its leaf hash eliminates the 220+ redundant hashes between a leaf's deepest split (~depth 27 at $10^8$ coins) and depth 256: updating or proving a key hashes only `k` interior nodes where `k` is the depth of the deepest split with another occupied key (~27 BLAKE3 hashes instead of 256, an ~9.5× reduction). This commitment is strictly for block headers, RPC queries, snapshot verification, and optional transport-layer `ProvenTx` relay packages—never a VM opcode (`OP_UTXOPROOFVERIFY` is rejected; see [rationale](../rationale.md#2-op_utxoproofverify-in-script-global-utxo-state-proofs)).

```text
Outpoint = txid:h32 || output_index:u32
key = H_outpointkey(Outpoint)
Coin = Outpoint || Bytes(Output) || creation_height:u64
       || creation_parent_mtp:u64 || coinbase:u8
UtxoLeaf(key,coin) = H_utxo(00 || key || Bytes(Coin))
UtxoNode(d,l,r) = H_utxo(01 || u16(d) || l || r)       # d=0..255
EmptyRoot = H_utxo(02)
```

Key bit `d` is `bit(key, d) = (key[d//8] >> (d%8)) & 1`: bit `d` of the key read as an unsigned little-endian 256-bit integer, least significant bit first, in keeping with the byte-order convention used everywhere else. For a set of distinct `(key, coin)` entries inside the subtree at depth `d` (`0 <= d <= 256`), the subtree root `smt(entries, d)` is:

- **Empty subtree (`|entries| == 0`):** `EmptyRoot`.
- **Single-leaf subtree (`|entries| == 1`):** `UtxoLeaf(key, coin)` directly, regardless of depth `d` (all single-child levels from `d` to `256` are collapsed).
- **Multi-entry subtree (`|entries| >= 2`, `0 <= d < 256`):** Partition `entries` by `bit(key, d)` into `left` (bit `0`) and `right` (bit `1`), and return `UtxoNode(d, smt(left, d + 1), smt(right, d + 1))`.

`UtxoRoot` is `smt(all_entries, 0)`. Only spendable outputs (`(flags & 0x02) == 0`) are inserted into `UtxoRoot`; burn/commitment outputs (`(flags & 0x02) != 0`, which have `path_count == 0`) are pruned at transaction application and never enter `UtxoRoot` (`C17`). Coin's outpoint must derive its key, coinbase must be `0` or `1`, flags must be `0x00` or `0x01`, and its output must satisfy spendable output well-formedness (including `MAX_OUTPUT_BRANCHES = 16` and `MAX_OUTPUT_PATHS = 16`, which bounds every `Coin` record to $\le 867\text{ bytes}$). Height/time and coinbase flag are consensus metadata, not database hints. Inserting a different outpoint at an occupied hash key rejects; never overwrite or merge such entries.

The map root is independent of insertion order. Deletion removes the entry, which automatically collapses any ancestor node whose remaining subtree drops to a single entry. Duplicate-key snapshot entries reject even when identical. Pre/post roots alone do not establish that the intervening transaction set was valid.

### Canonical membership and absence proof

For a queried `Outpoint` with `query_key = H_outpointkey(Outpoint)`, encode:

```text
presence:u8 || [Bytes(Coin) if presence in (1, 2)] || bitmap:32bytes || siblings
```

In a single-leaf-collapsed tree, following `bit(query_key, d)` from `d = 0` terminates at the shallowest depth `k` (`0 <= k <= 256`) whose subtree has at most one entry. Because the parent at depth `k - 1` (when `k > 0`) had at least two entries while the queried child at depth `k` has at most one, the sibling at depth `k - 1` is guaranteed to be non-empty (`!= EmptyRoot`). Therefore:

- Bit `d` of `bitmap` (`0 <= d <= 255`, indexed least-significant-bit first within byte `d//8`) is `1` iff `d < k` and the sibling at depth `d` is non-empty (`!= EmptyRoot`). All bits `d >= k` MUST be `0`, and when `k > 0` bit `k - 1` is `1`.
- The terminal depth `k` is uniquely determined by `bitmap`: `k = 0` if `bitmap` is all zeros (which occurs only when the entire UTXO map has `0` or `1` entry), and `k = max_set_bit(bitmap) + 1` otherwise.
- `siblings` contains exactly `popcount(bitmap)` 32-byte hashes ordered from depth `d = k - 1` down to `0` (bottom-up from the terminal subtree to the root). An explicitly supplied `EmptyRoot` in `siblings`, or any trailing/truncated bytes, is noncanonical and rejects.

`presence` is `0`, `1`, or `2`, determining the terminal hash `acc` at depth `k`:

- **`presence = 1` (membership):** `Coin.Outpoint` MUST equal the queried `Outpoint`, and `acc = UtxoLeaf(query_key, Coin)`.
- **`presence = 0` (absence at an empty branch):** No `Coin` is serialized, and `acc = EmptyRoot`. (When `k > 0`, the sibling at depth `k - 1` must be an interior node rather than a single leaf, because a parent with `EmptyRoot` on one side and a single leaf on the other would have collapsed to that single leaf; implementations may additionally reject a single-leaf sibling if tagged, and root comparison binds `UtxoNode(k - 1, ...)` against `UtxoRoot`.)
- **`presence = 2` (absence by prefix collision with another single leaf):** `Coin.Outpoint` MUST differ from the queried `Outpoint`, `other_key = H_outpointkey(Coin.Outpoint)` MUST agree with `query_key` on all bits `0 .. k - 1` (`bit(other_key, d) == bit(query_key, d)` for every `0 <= d < k`), and `acc = UtxoLeaf(other_key, Coin)`.

For each depth `d = k - 1` down to `0`, let `sib = EmptyRoot` if bit `d` of `bitmap` is `0`, or consume the next 32-byte hash from `siblings` if bit `d` is `1` (rejecting if `sib == EmptyRoot`). Set `acc = UtxoNode(d, acc, sib)` when `bit(query_key, d) == 0`, or `UtxoNode(d, sib, acc)` when `bit(query_key, d) == 1`. After `k` steps (`d = 0`), require `acc == UtxoRoot`.

Verification performs only `k` node hashes (plus 1 leaf hash when `presence in (1, 2)`), which is about 27 hashes at $10^8$ coins (~1 KB proof). Absence (`presence = 0` or `2`) proves that `query_key` is unpopulated at `UtxoRoot` under the hash assumptions; it does not prove an outpoint was never created or spent at another root. Multiproofs and snapshot range proofs may be designed later as transport/RPC encodings reproducing the same root.

### Candidate input-proof relay package (not consensus)

A wallet may relay a transaction together with its coins and their membership proofs, so that a node holding recent headers and recent block deltas can validate it without a database lookup. The package is transport only: none of it enters TxID, TxHash, the signature message or a block, so it can change without a consensus change.

```text
ProvenTx  = Tx || anchor:h32 || UtxoRoot:h32 || Bytes(MonetaryState)
            || Vec(CoinProof)
CoinProof = Bytes(Coin) || bitmap:32bytes || siblings
```

`CoinProof` is the membership proof above with presence fixed at 1 and its byte omitted. There is exactly one per spend input, in input order; mint and coinbase inputs have none. `anchor` is a BlockID. The envelope fields are those of the full state root below, with height taken from the anchor header.

A node accepts the package only if: the anchor is on its best chain and at most `PROOF_WINDOW` blocks behind the tip (a node policy value, not chosen here); the envelope reproduces the anchor header's state_root; each Coin's Outpoint equals its input's outpoint and its proof reconstructs UtxoRoot; and no proved outpoint is spent by a block after the anchor or by a conflicting mempool transaction. The node must therefore retain, in memory, the outpoints spent and coins created by the last `PROOF_WINDOW` blocks. An input whose coin was created after the anchor, or by an unconfirmed transaction, is resolved from that retained data and its CoinProof slot is replaced by a zero-length marker to be specified with the encoding. Ordinary validation then runs on the supplied coins; `creation_height`, `creation_parent_mtp` and `coinbase` come from the proved Coin.

A TxID-based proof is not a substitute: a TxID with its transaction-tree path shows that an output was created, not that it is unspent, and since TxID is a flat hash it would require the whole creating transaction.

Limits of this candidate. Proof size is about one sibling per doubling of the coin set (about 27 siblings, near 1 KB per input, at 10^8 coins). A proof expires when its anchor leaves the window; any state-holding node can reissue it and need not be trusted. Checking a block's new state_root without state additionally needs the paths of every key the block inserts; because keys are hashes of outpoints these are scattered, so a block-level multiproof from the producer is required and is not designed here. Block producers need the coin set or a complete set of proofs.

## Full state root

A UTXO root alone omits the paper's stateful reward recurrence. Commit a versioned state envelope:

```text
StateRoot = H_state(00 || ChainID || height:u64
                    || UtxoRoot:h32 || Bytes(MonetaryState))
```

`MonetaryState` is a canonical record to be frozen with D10: it must contain every work-responsive reward recurrence value not uniquely derivable from authenticated headers/UTXOs (D11's protocol faucet is rejected, so no faucet state exists). This packet does not choose opaque daemon bytes as its encoding. The header's former `hashUtxoMerklixRoot` is therefore renamed **state_root**. RPCs must expose both the envelope and UTXO proofs so clients can connect a coin proof to the header root. Height must match the validated block context.

Header ancestry supplies validated time/target context; a standalone UTXO snapshot does not. Snapshot admission must check envelope, unique entries, canonical Coin encodings, root reconstruction, monetary record and selected chain context, and clearly state which historical transitions were actually verified. Retained undo must restore every field of the prior envelope.

## Coinbase and root dependency order

Choose ChainID and genesis parameters → construct coinbase using parent ID/height → derive TxID/TxHash → evaluate transitions and full state envelope → compute transaction/state roots → construct header → compute BlockID/PoW. The containing header hash is never embedded in its own coin records. In a non-genesis block, the parent's hash is already available. Genesis uses zero parent and an explicitly initialized monetary record.

## Acceptance obligations

Pin test vectors for empty/one/two/odd transaction trees, every proof direction, empty/single-leaf/multi-leaf/deleted compact state maps, all three proof presence modes (`0`, `1`, `2`), same map built in different orders, coin metadata changes and envelope restoration. Check both scalar and incremental implementations against the same vectors. This packet closes a candidate algorithm, not its MonetaryState dependencies.
