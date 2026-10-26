# Hash commitments and authenticated state

Decision packet P02. **Recommended candidate**, not frozen or implemented. Refines D02/D13 and the commitment part of D14. Defines separate branch, ordered-vector and keyed-map commitments rather than one ambiguous “Merklix” API.

## Hash registry

`B3` is unkeyed BLAKE3 with exactly 32 output bytes. `H_name(x)=B3(ASCII(tag) || 00 || x)`. All tags are case-sensitive ASCII strings below. Prefix bytes such as `00` in node encodings are bytes, not characters. Integer encodings are P01 little-endian; where two hashes are ordered they are read as unsigned little-endian integers. No hash function accepts arbitrary C++ struct memory.

| name | Exact tag |
| --- | --- |
| branch | `Lotus/v2/branch` |
| txid | `Lotus/v2/txid` |
| txhash | `Lotus/v2/txhash` |
| sighash | `Lotus/v2/sighash` |
| inputcore | `Lotus/v2/inputcore` |
| inputfull | `Lotus/v2/inputfull` |
| coinentry | `Lotus/v2/coinentry` |
| owninput | `Lotus/v2/owninput` |
| output | `Lotus/v2/output` |
| txroot | `Lotus/v2/txroot` |
| utxo | `Lotus/v2/utxo` |
| state | `Lotus/v2/state` |
| header/history | `Lotus/v2/header/history` |
| blockid | `Lotus/v2/blockid` |
| merkleidx | `Lotus/v2/merkleidx` |

The BLAKE3 primitive follows its [specification](https://github.com/BLAKE3-team/BLAKE3-specs/blob/master/blake3.pdf); application tags and tree rules are Lotus choices. Because `H_name(x)` is ordinary unkeyed `BLAKE3` over the ASCII prefix `tag || 0x00 || x` (`C08`), any script can compute and verify any domain-tagged hash (`H_txid`, `H_inputcore`, `H_output`, `H_coinentry`, `H_merkleidx`, etc.) in three instructions (`<"Lotus/v2/...\x00"> SWAP CAT BLAKE3`) without needing a dedicated opcode per domain tag. [P04](header-and-mining.md) specifies a recursive BlockID/PoW candidate and its additional headerbody/headerwork domains; final choice remains D12. Hash collision resistance is an assumption, not a theorem about these tags.

## Branch MAST: unordered membership

```text
Leaf(script) = H_branch(00 || Bytes(script))
BranchNode(a,b) = H_branch(01 || min(a,b) || max(a,b))
```

`min` and `max` compare the two 32-byte hashes as unsigned little-endian 256-bit integers: the last byte is the most significant. This is the same reading of a hash that P04 uses to compare a BlockID with its target, and the byte order of every integer in the transaction format and the VM.

Spend and mint invocations use the same leaf function. Consensus therefore does not distinguish a mint script from a spend script: any leaf of a tree can be proven in either kind of invocation. A design that needs both must keep them in **separate trees**. A token's mint scripts form the tree whose root is the token ID; rules that must run on every spend form a second tree that appears on outputs as a branch, and the mint scripts name that second root as a constant. A mint script placed in a tree that outputs use as a required branch could be offered to satisfy that branch. Consume siblings bottom-up, hashing once per sibling. Empty sibling vector means root=Leaf(script). A proof only asserts membership; it has no direction bits, method index, hidden leaf-count claim or hidden uniqueness claim. Consensus limits proof depth; no unverified tree metadata enlarges that bound.

For reproducible wallet construction, recommend: sort distinct leaf hashes as unsigned little-endian integers, ascending; split a list of n>1 at the greatest power of two less than n; recursively build and sort each child pair at hashing. This construction is a wallet convention, not a property enforceable from a single proof. An owner may commit another finite binary tree. Duplicated leaves or alternative shapes provide no independent authorization and receive no accounting discount.

### Storing data and Merkle roots in branches: three patterns

Outputs carry no separate state field. Contracts and protocols commit data or Merkle roots in `branches` and verify Merkle proofs against them (`MERKLEROOT_SORTED`, `MERKLEROOT_INDEXED`, `LEAFHASH`, `NODEHASH`) in three complementary ways:

1. **On a pruneable burn / `OP_RETURN` output (`flags = 0x02` native or `0x03` token, `paths = []`):**
   - Setting bit 1 (`0x02` `IS_BURN`) requires `path_count == 0` (`paths = []`) and `1 <= branch_count <= 16` pairwise distinct 32-byte entries in `branches` (up to 512 bytes of commitment hashes, Merkle roots, or topic/data words).
   - 100% of `value` on an `IS_BURN` output is permanently burned (included in `O_a`, never claimable by miners as fees; `value = 0` is also valid), and validators **never insert `IS_BURN` outputs into `UtxoRoot`** (`C17`), so they consume zero UTXO memory forever.
   - Scripts in the creating transaction can inspect an `IS_BURN` output `j` via `OUTPUTFLAGS(j)`, `OUTPUTVALUE(j)`, `OUTPUTTOKENID(j)`, `OUTPUTBRANCHCOUNT(j)`, and `OUTPUTBRANCH(j, k)`—and can verify Merkle proofs against `OUTPUTBRANCH(j, k)` using `MERKLEROOT_SORTED` or `MERKLEROOT_INDEXED`—making `IS_BURN` outputs ideal for Frank/Stamp topic broadcasts, burn-weighted votes, and verified on-chain data commitments.
2. **As a dedicated unexecuted data branch on a spendable coin (`branches = [CodeRoot, StateMerkleRoot]`, `paths = [[0]]`):**
   - Because `paths = [[0]]` requires only `branch[0]` (`CodeRoot`), `branch[1]` (`StateMerkleRoot`) is never executed as a script—it acts as a direct 32-byte state or Merkle-root register on the coin (or up to 15 registers `branch[1..15]`).
   - Methods in `CodeRoot` read the current root in $O(1)$ via `INPUTINDEX <1> UTXOBRANCH`, verify or update leaves using `MERKLEROOT_INDEXED` or `MERKLEROOT_SORTED`, and require the successor output `j` to carry the updated root at `OUTPUTBRANCH(j, 1)` while `branch[0]` (`CodeRoot`) never changes.
3. **Inside the executing branch tree itself (`BranchNode(DataLeaf, M)`, the data-leaf convention):**
   - For the most compact 1-branch coin (45 bytes native / 77 bytes token, `branches = [root]`, `paths = [[0]]`), a contract places its state as one leaf beside the subtree `M` of its methods:
     ```text
     DataLeaf(values) = Leaf(data_script(values))      # pushes of the values, then RETURN
     root             = BranchNode(DataLeaf(values), M)   # M = root of the methods subtree
     ```
   - `M` never changes; `root` changes whenever `values` do. The data script ends in `RETURN` so that it can never be run as a method. The spender supplies the current `values` and `M` as witness arguments, and the method checks `BranchNode(Leaf(data_script(values)), M) == BRANCHROOT` using `LEAFHASH` and `NODEHASH`, then requires `BranchNode(Leaf(data_script(new_values)), M)` on the successor output with `OUTPUTCONTINUESBRANCH` or `OUTPUTEXCLUSIVEBRANCH`. The cost is two leaf hashes and two node hashes per spend, whatever the number of methods, and a method's membership proof is one sibling longer than it would be without state.

Patterns 2 and 3 are compiler/application conventions recorded in the contract's ABI; pattern 1 (`IS_BURN` (`0x02`/`0x03`)) has consensus-enforced `path_count == 0` and UTXO pruning (`C05`, `C09`, `C17`).

## Indexed binary Merkle tree: transaction inputs, outputs, and coins (`IndexedTreeRoot`)

Following Lotus v1's Malfix design (`101-implement-malfix.patch`), transaction inputs, outputs, and resolved coins are committed via a canonical bottom-up indexed binary Merkle tree (`IndexedTreeRoot`) so that smart contracts can prove any individual input or output of a parent/injected transaction (`OUTPOINTTXID(i)`) in $O(\log N)$ space using `MERKLEROOT_INDEXED` (`0xc1`, `hash_alg = 0`) without pushing the entire parent transaction onto the stack.

For a vector of $n \ge 0$ 32-byte leaf hashes `L[0 .. n - 1]`:

```text
EmptyIndexedRoot         = H_merkleidx(02)
IndexedNode(s, l, r)     = H_merkleidx(01 || u16(s) || l || r)
Zero32                   = 00^32
```

- **Empty vector ($n == 0$):** `IndexedTreeRoot([]) = EmptyIndexedRoot`.
- **Single-element vector ($n == 1$):** `IndexedTreeRoot([L[0]]) = L[0]` directly (depth $k = 0$, zero siblings; a 1-input or 1-output vector performs zero interior tree node hashes beyond the leaf hash itself).
- **Multi-element vector ($n > 1$):** Build bottom-up by layer $s = 0, 1, \dots, \lceil \log_2(n) \rceil - 1$, starting from `cur = L[0 .. n - 1]`:
  1. At layer $s$, let $m = \text{len}(\text{cur})$. If $m$ is odd, append `Zero32 = 0x00^32` as the right sibling of the last element (`cur[m] = Zero32`, matching Lotus v1's CVE-2012-2459 mitigation rather than Bitcoin's vulnerable self-duplication).
  2. Set `next[j] = IndexedNode(s, cur[2j], cur[2j + 1])` for $0 \le j < \lceil m / 2 \rceil$, and advance `cur = next`.
  3. After $k = \lceil \log_2(n) \rceil$ layers, return the single remaining 32-byte root `cur[0]`.

Because layer index $s$ runs bottom-up from $0$ (leaves) to $k - 1$ (root), for any leaf index `idx in 0 .. n - 1`, at step $s = 0 \dots k - 1$, bit $s$ of `idx` (`(idx >> s) & 1`) is `0` when the node is the left child (`cur[2j]`) and `1` when the node is the right child (`cur[2j + 1]`). Consequently, `MERKLEROOT_INDEXED` (`0xc1`, `hash_alg = 0`) verifies any leaf `L[idx]` against `IndexedTreeRoot(L)` in a single instruction (`<L[idx]> <u16(idx)> <proof_bytes> <0> MERKLEROOT_INDEXED`), while the outer transaction header in `TxID` (`input_count:u16` and `output_count:u16` in [P01](encoding-and-signatures.md)) binds the exact vector lengths.

## Block transaction commitment: prefix-sharded Merklix `Subtree A` and top-level `CoinbaseLeaf`

Following the sharding architecture of [*Sharding Bitcoin Cash*](https://www.bitcoinabc.org/2018-09-06-sharding-bitcoin-cash/) (September 6, 2018), scaling block construction, mempool acceptance, and transaction commitment across horizontal CPU cores and processes requires **consistent key-prefix range partitioning** rather than positional array-index splitting.

Let transaction $i$ ($0 \le i < n$) have identity pair `(TxID_i, TxHash_i)`, with `vtx[0]` as the block's coinbase transaction and `vtx[1 .. n - 1]` as the block's non-coinbase transactions. All `TxID_i` in a block (or commitment vector) MUST be pairwise distinct. Define:

```text
TxLeaf(TxID, TxHash) = H_txroot(00 || TxID || TxHash)
TxNode(d, l, r)      = H_txroot(01 || u16(d) || l || r)       # d=0..255
EmptyTxRoot          = H_txroot(02)
```

Key bit `d` of `TxID` is `bit(TxID, d) = (TxID[d//8] >> (d%8)) & 1` (the exact same 256-bit little-endian bit order as `UtxoRoot`). For a set of distinct `(TxID, TxHash)` non-coinbase entries inside the subtree at depth `d` (`0 <= d <= 256`), the single-leaf-collapsed Merklix subtree root `tx_smt(entries, d)` is:

- **Empty subtree (`|entries| == 0`):** `EmptyTxRoot`.
- **Single-leaf subtree (`|entries| == 1`):** `TxLeaf(TxID, TxHash)` directly, regardless of depth `d` (all single-child levels from `d` to `256` are collapsed).
- **Multi-entry subtree (`|entries| >= 2`, `0 <= d < 256`):** Partition `entries` by `bit(TxID, d)` into `left` (bit `0`) and `right` (bit `1`), and return `TxNode(d, tx_smt(left, d + 1), tx_smt(right, d + 1))`.

The top-level block transaction commitment `TxRoot(xs)` is:

- **Empty vector ($n == 0$, tool primitive only):** `TxRoot([]) = EmptyTxRoot` (a block with no coinbase is invalid).
- **Non-empty vector ($n \ge 1$):** Let `CoinbaseLeaf = TxLeaf(TxID_0, TxHash_0)` and `SubtreeA = tx_smt(xs[1 .. n - 1], 0)`. Then:
  ```text
  TxRoot(xs) = H_txroot(03 || CoinbaseLeaf || SubtreeA)
  ```
  ```text
                   [ header.tx_root ]
                      /          \
        [ CoinbaseLeaf ]        [ Subtree A ]   <-- 256-bit Merklix tree of vtx[1..n-1] keyed by TxID
                                  /       \
                        [ Subtree B ]   [ Subtree C ]
                         (prefix 0...)   (prefix 1...)
  ```

Each leaf commits to both identities of its transaction (`TxID` first, then `TxHash`). `TxHash` fixes the complete witness bytes as the leaf value at key `TxID`, while `TxID` alone defines the 256-bit prefix path through `Subtree A`. Because `Subtree A` partitions strictly by the bits of `TxID`, any $2^k$ mempool/validation shards (where Shard $s \in [0, 2^k - 1]$ owns the $k$-bit `TxID` prefix $s$) can maintain their mempool subtrees and pre-compute `(TxSubtreeRoot[s], fee_sum[s], cost_sum[s])` **100% independently with zero cross-shard count synchronization**, and `Subtree A` is naturally ordered by ascending `TxID` (matching Canonical Transaction Ordering, CTOR, in block wire format `vtx[1 .. n - 1]` with two-phase outputs-then-inputs intra-block UTXO resolution per `C12`). On `getblocktemplate`, the coordinator aggregates the $2^k$ shard roots into `Subtree A` (32 bytes), constructs `vtx[0]`, and combines `CoinbaseLeaf` with `Subtree A` in **one single top-level hash ($O(1)$)** without re-entering any shard.

### Canonical transaction membership and absence proof

A transaction proof against `TxRoot` begins with a 1-byte selector `is_coinbase:u8`:

- **`is_coinbase = 1` (coinbase proof):** `01 || TxID_0:h32 || TxHash_0:h32 || SubtreeA:h32` (97 bytes). The verifier computes `CoinbaseLeaf = TxLeaf(TxID_0, TxHash_0)` and checks `H_txroot(03 || CoinbaseLeaf || SubtreeA) == TxRoot`.
- **`is_coinbase = 0` (non-coinbase Merklix proof in `Subtree A` for `query_txid:h32`):**
  ```text
  00 || CoinbaseLeaf:h32 || presence:u8 || [TxID:h32 || TxHash:h32 if presence in (1, 2)] || bitmap:32bytes || siblings
  ```
  where `presence` (`0` = empty branch absence, `1` = membership with `TxID == query_txid`, `2` = prefix-collision absence with a single leaf `TxID != query_txid` agreeing on bits `0 .. k - 1`), `bitmap` (32 bytes), and `siblings` (`popcount(bitmap)` 32-byte hashes ordered from depth `k - 1` down to `0`, none equal to `EmptyTxRoot`) reconstruct `SubtreeA` using `TxLeaf`, `TxNode`, and `EmptyTxRoot` by the exact same rules as `UtxoRoot` below, and the verifier checks `H_txroot(03 || CoinbaseLeaf || SubtreeA) == TxRoot`.

## UTXO map: compact single-leaf-collapsed sparse binary tree

Use a 256-bit keyed sparse binary tree with single-leaf subtree collapsing as the normative `UtxoRoot` algorithm. Collapsing every single-leaf subtree to its leaf hash eliminates the 220+ redundant hashes between a leaf's deepest split (~depth 27 at $10^8$ coins) and depth 256: updating or proving a key hashes only `k` interior nodes where `k` is the depth of the deepest split with another occupied key (~27 BLAKE3 hashes instead of 256, an ~9.5× reduction). This commitment is strictly for block headers, RPC queries, snapshot verification, and optional transport-layer `ProvenTx` relay packages—never a VM opcode (`OP_UTXOPROOFVERIFY` is rejected; see [rationale](../rationale.md#2-op_utxoproofverify-in-script-global-utxo-state-proofs)).

```text
Outpoint = txid:h32 || output_index:u32
OutpointKey(txid, output_index) = txid[0..28] || u32_le(u32_le(txid[28..32]) ^ output_index)
key = OutpointKey(txid, output_index)
Coin = Outpoint || Bytes(Output) || creation_height:u64
       || creation_parent_mtp:u64 || coinbase:u8
UtxoLeaf(key,coin) = H_utxo(00 || key || Bytes(Coin))
UtxoNode(d,l,r) = H_utxo(01 || u16(d) || l || r)       # d=0..255
EmptyRoot = H_utxo(02)
```

Preserving the first 28 bytes (224 bits) of `txid` and XORing the trailing 32-bit little-endian word `txid[28..32]` with `output_index` keeps all outputs of a single transaction co-located under the same 224-bit prefix in `UtxoRoot`, on the same horizontal shard as `txid` in `Subtree A`, and adjacent in B+Tree storage (`dbi_coins` and `dbi_smt_nodes`), while guaranteeing distinct 256-bit keys for distinct `output_index` values of the same `txid`.

Key bit `d` is `bit(key, d) = (key[d//8] >> (d%8)) & 1`: bit `d` of the key read as an unsigned little-endian 256-bit integer, least significant bit first, in keeping with the byte-order convention used everywhere else. For a set of distinct `(key, coin)` entries inside the subtree at depth `d` (`0 <= d <= 256`), the subtree root `smt(entries, d)` is:

- **Empty subtree (`|entries| == 0`):** `EmptyRoot`.
- **Single-leaf subtree (`|entries| == 1`):** `UtxoLeaf(key, coin)` directly, regardless of depth `d` (all single-child levels from `d` to `256` are collapsed).
- **Multi-entry subtree (`|entries| >= 2`, `0 <= d < 256`):** Partition `entries` by `bit(key, d)` into `left` (bit `0`) and `right` (bit `1`), and return `UtxoNode(d, smt(left, d + 1), smt(right, d + 1))`.

`UtxoRoot` is `smt(all_entries, 0)`. Only spendable outputs (`(flags & 0x02) == 0`) are inserted into `UtxoRoot`; burn/commitment outputs (`(flags & 0x02) != 0`, which have `path_count == 0`) are pruned at transaction application and never enter `UtxoRoot` (`C17`). Coin's outpoint must derive its key, coinbase must be `0` or `1`, flags must be `0x00` or `0x01`, and its output must satisfy spendable output well-formedness (including `MAX_OUTPUT_BRANCHES = 16` and `MAX_OUTPUT_PATHS = 16`, which bounds every `Coin` record to $\le 868\text{ bytes}$). Height/time and coinbase flag are consensus metadata, not database hints. Inserting a different outpoint at an occupied key rejects; never overwrite or merge such entries.

The map root is independent of insertion order. Deletion removes the entry, which automatically collapses any ancestor node whose remaining subtree drops to a single entry. Duplicate-key snapshot entries reject even when identical. Pre/post roots alone do not establish that the intervening transaction set was valid.

### Canonical membership and absence proof

For a queried `Outpoint = txid:h32 || output_index:u32` with `query_key = OutpointKey(txid, output_index)`, encode:

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
- **`presence = 2` (absence by prefix collision with another single leaf):** `Coin.Outpoint` MUST differ from the queried `Outpoint`, `other_key = OutpointKey(Coin.txid, Coin.output_index)` MUST agree with `query_key` on all bits `0 .. k - 1` (`bit(other_key, d) == bit(query_key, d)` for every `0 <= d < k`), and `acc = UtxoLeaf(other_key, Coin)`.

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

A TxID-based proof is not a substitute: a TxID with its transaction-tree path and output-tree path shows only that an output was created in some block, not that it remains unspent at the current tip.

Limits of this candidate. Proof size is about one sibling per doubling of the coin set (about 27 siblings, near 1 KB per input, at 10^8 coins). A proof expires when its anchor leaves the window; any state-holding node can reissue it and need not be trusted. Checking a block's new state_root without state additionally needs the paths of every key the block inserts; because all outputs of a transaction share a 224-bit `txid` prefix, outputs created by the same transaction share a single Merklix path down to depth 224 and are co-located on the shard owning `txid`'s prefix. Block producers need the coin set or a complete set of proofs.

## Full state root and canonical `MonetaryState` (`56B` at Genesis, `88B` at $h \ge 1$)

A UTXO root alone omits the protocol's stateful issuance, dynamic fee-burn recurrences, and historical header accumulator ([P05](resources-and-parameters.md), [P06](issuance-and-time.md), [Header History Tree](../header-history-tree.md)). Commit a versioned state envelope:

```text
CoreMonetaryState = bootstrap_reserve:u64     # R_n (remaining unissued bootstrap atoms, P06)
                    || tail_subsidy:u64       # T_n (current adaptive tail subsidy atoms, P06)
                    || prev_work:u256         # W_{n-1} (32-byte little-endian unsigned per-block work, P04/P06)
                    || ema_block_cost:u64     # E_n (rolling integer EMA of block cost units, P05)

MonetaryState(h)  = CoreMonetaryState                         (56 bytes at Genesis h = 0, where history_root == 0x00^32)
                  | CoreMonetaryState || history_root:h32     (88 bytes at every post-genesis height h >= 1)

StateRoot         = H_state(00 || ChainID || height:u64
                            || UtxoRoot:h32 || Bytes(MonetaryState(h)))
```

`CoreMonetaryState` is a canonical fixed-width **56-byte** record (`8 + 8 + 32 + 8 = 56` bytes). At Genesis ($h = 0$, `count == 0`, `history_root == 0x00^32`), `MonetaryState` is 56 bytes (`Bytes(MonetaryState) = 0x38 || CoreMonetaryState`, making the `StateRoot` preimage `130` bytes after the domain tag). At every post-genesis block ($h \ge 1$, `count = h >= 1`), the non-zero 32-byte `history_root` (`HeaderHistoryRoot` over blocks $0 \dots h - 1$) is appended, making `MonetaryState` **88 bytes** (`Bytes(MonetaryState) = 0x58 || CoreMonetaryState || history_root`, and the `StateRoot` preimage `162` bytes after the domain tag). It retains bootstrap/EMA continuation state, checked tail/work redundancy, and the authenticated header history root (D11 uses Avalanche coordination policy, so no faucet or treasury state exists):

1. `bootstrap_reserve:u64` ($R_n$): remaining unissued bootstrap reserve in native atoms; issuance step $n$ emits $B_n = \max(1, R_n \gg k_{\text{boot}})$ when $R_n > 0$ (or $0$ when $R_n = 0$) and updates $R_{n+1} = R_n - B_n$ ([P06](issuance-and-time.md)).
2. `tail_subsidy:u64` ($T_n$), checked cache of `F(authenticated_parent_work)`: issuance step $n$'s adaptive tail subsidy in native atoms (total issuance step $n$ subsidy entitlement is $S_n = B_n + T_n$); after accepting issuance step $n$ with per-block work $W_n$, updates to $T_{n+1} = \min(T_{\max}, \max(T_{\min}, \text{isqrt}(\lfloor T_g^2 W_n / W_g \rfloor)))$ ([P06](issuance-and-time.md)).
3. `prev_work:u256` ($W_{n-1}$), checked against the authenticated parent target: 32-byte unsigned little-endian per-block chainwork of the parent block (initialized at genesis to $W_{-1} > 0$ from the genesis target, updated to $W'_n = W_n$ after issuance step $n$).
4. `ema_block_cost:u64` ($E_n$): rolling integer exponential moving average of whole-block frozen accounting cost units $C_{\text{block}}$, updated after issuance step $n$ via $E_{n+1} = E_n - (E_n \gg w) + (C_{\text{block}} \gg w)$ and used to enforce issuance step $n$'s required fee-burn floor ([P05](resources-and-parameters.md)).

The header's former `hashUtxoMerklixRoot` is therefore renamed **state_root**. RPCs must expose both the 56-byte `MonetaryState` envelope and UTXO proofs so clients can connect a coin proof to the header's `state_root`. `height` must match the validated block context.

Header ancestry supplies validated time/target context; a standalone UTXO snapshot does not. Snapshot admission must check the envelope, unique entries, canonical `Coin` encodings, root reconstruction, the `MonetaryState` record and selected chain context, and clearly state which historical transitions were actually verified. Retained undo data must restore every field of the prior `MonetaryState` envelope on disconnect.

## Header History Merkle Tree (`HeaderHistoryFrontier` and `history_root`)

So that light clients, bridges, and FastSync / Snapshot verifiers can authenticate any historical block header at height $h < H$ against the current block header at height $H$ in $O(\log H)$ space and time, every post-genesis block ($H \ge 1$) commits to `history_root` inside `MonetaryState`: the root of an append-only binary Merkle mountain / carry-chain frontier over all prior canonical block hashes $(0, \text{BlockID}_0), (1, \text{BlockID}_1), \dots, (H-1, \text{BlockID}_{H-1})$.

### 1. Leaf and internal node hashes

With BLAKE3 domain tag `"Lotus/v2/header/history"` (`H_header_history(x) = BLAKE3("Lotus/v2/header/history" || 0x00 || x)`):

```text
HeaderLeafHash(ChainID, height, block_hash)
  = H_header_history(ChainID || 0x00 || u64_le(height) || block_hash:h32)

HeaderInternalHash(ChainID, level, left, right)
  = H_header_history(ChainID || 0x01 || u8(level) || left:h32 || right:h32)

NULL_HASH = 0x00^32
```

- `0x00` vs. `0x01` separates leaves from internal nodes (second-preimage resistance).
- `u64_le(height)` binds each block hash to its exact block height.
- `u8(level)` ($0 \le \text{level} < 64$) binds each internal node to its exact height in the binary tree ($2^{\text{level}}$ leaves per complete subtree).

### 2. Incremental frontier (`HeaderHistoryFrontier`) and $O(\text{ctz}(\text{count}+1))$ append

`HeaderHistoryFrontier` maintains:
- `count: u64` — the number of committed prior headers (at block height $H$, `count == H`).
- `peaks: [Hash256; 64]` — for each bit $k \in [0, 63]$, if `((count >> k) & 1) == 1`, `peaks[k]` holds the root of the complete binary subtree of $2^k$ headers at level $k$; otherwise `peaks[k] = NULL_HASH`.

Appending `(height = prev.count, block_hash)` to `prev` (`AppendHeaderToFrontier`):
1. Compute `carry = HeaderLeafHash(ChainID, prev.count, block_hash)`.
2. For $k = 0, 1, \dots, 63$:
   - If `((prev.count >> k) & 1) == 1`: merge `carry = HeaderInternalHash(ChainID, k, prev.peaks[k], carry)` and clear `next.peaks[k] = NULL_HASH`.
   - Else: store `next.peaks[k] = carry`, set `next.count = prev.count + 1`, and stop.

### 3. Root fold (`HeaderHistoryRoot`) and `MonetaryState` binding

Given `frontier` with `count` committed headers:
- **`count == 0` (Genesis, height $0$):** `HeaderHistoryRoot` is `NULL_HASH` (`0x00^32`), and `MonetaryStateHash` omits `history_root` when `history_root == NULL_HASH` so the Genesis block's `hashStateRoot` and PoW nonce remain unchanged.
- **`count > 0` (Every block at height $H \ge 1$):**
  Let $k_0 = \text{ctz}(\text{count})$ be the lowest set bit of `count` and $L = \lfloor \log_2(\text{count}) \rfloor = 63 - \text{clz}(\text{count})$ be the highest set bit of `count`:
  - If $k_0 == L$ (`count` is an exact power of two): return `frontier.peaks[L]` directly.
  - Otherwise ($k_0 < L$):
    1. Initialize `acc = HeaderInternalHash(ChainID, k_0, frontier.peaks[k_0], NULL_HASH)`.
    2. For $k = k_0 + 1 \dots L$:
       - If `((count >> k) & 1) == 1`: `acc = HeaderInternalHash(ChainID, k, frontier.peaks[k], acc)`.
       - Else: `acc = HeaderInternalHash(ChainID, k, acc, NULL_HASH)`.
    3. Return `acc` (which is cryptographically non-zero and appended to `MonetaryStateHash`).

### 4. $O(\log H)$ inclusion proofs (`HeaderInclusionProof`) and RPC verification

Full nodes maintain `HeaderHistoryTree` (persisted atomically at `<datadir>/blocks/header_history_v2.dat` with magic `"LV2HHT01"`), storing complete subtree roots `m_levels[k][i]` at every level $k \ge 0$ alongside the frontier so historical inclusion proofs at any `target_count` are constructed in $O(\log(\text{target\_count}))$ time and verified via `VerifyHeaderInclusionProof`:

- Reject if `total_count == 0` or `leaf_height >= total_count`.
- Let tree depth $D = \text{ctz}(\text{total\_count})$ when `total_count` is a power of two, and $D = 64 - \text{clz}(\text{total\_count})$ otherwise. Reject if `siblings.size() != D`.
- Start with `cur = HeaderLeafHash(ChainID, leaf_height, block_hash)`.
- For $k = 0 \dots D - 1$:
  - If `((leaf_height >> k) & 1) == 0` (left child): if the right child subtree does not exist (`(((leaf_height >> k) + 1) << k) >= total_count`) and `siblings[k] != NULL_HASH`, reject (canonical null-sibling check); then set `cur = HeaderInternalHash(ChainID, k, cur, siblings[k])`.
  - Else (right child): set `cur = HeaderInternalHash(ChainID, k, siblings[k], cur)`.
- Accept iff `cur == expected_root`.
- Exposed via RPCs `getheaderhistoryproof(height, [anchor_height_or_hash])` and `verifyheaderhistoryproof(proof_hex, [expected_root_or_anchor])`.

## Genesis and monetary indexing

Monetary equations use **issuance-step index `n >= 0`**, not header height: step `n` is block height `n + 1`. Genesis (height 0) initializes and commits `(R_0, T_0, W_-1, E_0)` unchanged. Here `W_-1` is genesis target work. Genesis does not run bootstrap decay, tail adjustment, EMA update or recurring fee deduction. Its coinbase has zero total native value; no genesis endowment or treasury allocation exists. Its exact output/commitment bytes remain a genesis-manifest input. Ordinary C17 output insertion/pruning still applies, including for zero-valued outputs.

Height 1 executes step 0 using the genesis state: `B_0 = max(1, R_0 >> k_boot)` when `R_0 > 0`, `S_0 = B_0 + T_0`, then commits `(R_1, T_1, W_0, E_1)` with height 1 in `StateRoot`. Height 2 executes step 1. In general the header at height `h` commits `(R_h, T_h, W_(h-1), E_h)` after initialization/transition. Thus the bootstrap conservation identity sums over steps `n >= 0` (heights 1 onward), and the initial 500,000 XPI is height 1's gross entitlement, before coinbase resource deductions. Disconnecting height 1 restores the exact genesis state. All target/lock/header-height rules continue to use actual height; this notation changes none of those fields.

## Coinbase and root dependency order

For non-genesis blocks ($h \ge 1$): insert parent block $h - 1$'s spendable coinbase outputs into the UTXO tree and apply block $h$'s non-coinbase transactions `vtx[1 .. n - 1]` in two-phase outputs-then-inputs CTOR order (`C12`, `C17`) → calculate resource charges and reduce the coinbase claim under P05 (`C16`, `C25`) → construct coinbase `vtx[0]` using parent ID/height and the parent's `MonetaryState` ($S_n = B_n + T_n$) → derive TxID/TxHash → evaluate transitions, total block cost $C_{\text{block}} = C_{\text{envelope}} + C(vtx[1..n-1]) + C(vtx[0])$, mandatory fee-burn floor against $E_n$, and the post-block 88-byte `MonetaryState` ($R_{n+1}, T_{n+1}, W_n, E_{n+1}, \text{HistoryRoot}_h$) → compute transaction/state roots → construct header → compute BlockID/PoW. Because block $h$'s own spendable coinbase outputs are inserted into `UtxoRoot` at height $h + 1$ (`C17`, delayed 1-block pipelining), `UtxoRoot` at height $h \ge 1$ is 100% invariant to block $h$'s coinbase transaction (enabling Snowstorm's $O(1)$ `SnapBlock` fast path), while the containing header hash is never embedded in its own coin records. Genesis (`height = 0`) has no prior block ($h - 1$) to pipeline from, so it uses zero parent (`parent_id = 00^32`), an explicitly initialized 56-byte `MonetaryState` ($R_0, T_0, W_{-1}, E_0$ with `history_root == 00^32` omitted), and inserts every spendable output (`(flags & 0x02) == 0`) of Block 0's coinbase directly into the Genesis `UtxoRoot` (with `creation_height = 0`, `creation_parent_mtp = 0`, `coinbase = 1`, spendable after coinbase maturity `C18`), while any unspendable Genesis timestamp/headline message uses an `IS_BURN` (`flags = 0x02`, `paths = []`) output that is excluded from `UtxoRoot`.

## Acceptance obligations

Pin test vectors for empty/one/two/odd transaction trees, every proof direction, empty/single-leaf/multi-leaf/deleted compact state maps, all three proof presence modes (`0`, `1`, `2`), same map built in different orders, coin metadata changes, 56-byte `MonetaryState` transitions and `StateRoot` envelope restoration. Check both scalar and incremental implementations against the same vectors. Initial genesis parameter values ($R_0, T_0, W_{-1}, E_0$) remain to be confirmed by simulation before genesis freeze.

The absolute tail preserves these 56 serialized bytes and the 134-byte header. Immutable genesis tail/work anchors and formula version 1 belong to the consensus profile identity; a snapshot cannot supply or reset them. Validate both cached fields against authenticated header work and the profile formula before accepting continuation state. See P06 for exact rounding and migration.

---

## References

1. **[Merkle 1987]** Ralph C. Merkle, *"A Digital Signature Based on a Conventional Encryption Function"*, in *Advances in Cryptology — CRYPTO '87*, Lecture Notes in Computer Science, vol. 293, pp. 369–378, Springer, 1988.
2. **[Vermorel, Séchet, Chancellor, & van der Wansem 2018]** Joannes Vermorel, Amaury Séchet, Shammah Chancellor, and Tomas van der Wansem, *"Canonical Transaction Ordering for Bitcoin"*, June 12, 2018.
3. **[Vermorel, Séchet, Chancellor, & Cox 2018]** Joannes Vermorel, Amaury Séchet, Shammah Chancellor, and Jason Cox, *"Merklix Tree for Bitcoin"*, July 2018.
4. **[Dahlberg, Pulls, & Peeters 2016]** Rasmus Dahlberg, Tobias Pulls, and Roel Peeters, *"Efficient Sparse Merkle Trees: Caching Strategies and Secure (Non-)Membership Proofs"*, in *Proceedings of the 21st Nordic Conference on Secure IT Systems (NordSec 2016)*, LNCS vol. 10014, pp. 199–215, 2016 (`IACR ePrint 2016/683`).
5. **[Crosby & Wallach 2009]** Scott A. Crosby and Dan S. Wallach, *"Efficient Data Structures for Tamper-Evident Logging"*, in *Proceedings of the 18th USENIX Security Symposium*, pp. 317–334, August 2009.
6. **[Todd 2012/2016]** Peter Todd, *"Merkle Mountain Ranges"*, OpenTimestamps / Bitcoin Core developer notes, 2012–2016.
7. **[O'Connor, Aumasson, Neves, & Wilcox-O'Hearn 2020]** Jack O'Connor, Jean-Philippe Aumasson, Samuel Neves, and Zooko Wilcox-O'Hearn, *"BLAKE3: One Function, Fast Everywhere"*, January 2020 (`https://github.com/BLAKE3-team/BLAKE3-specs`).
8. **[Nakamoto 2008]** Satoshi Nakamoto, *"Bitcoin: A Peer-to-Peer Electronic Cash System"*, October 2008 (`https://bitcoin.org/bitcoin.pdf`).
