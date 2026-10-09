# Hash commitments and authenticated state

Decision packet P02, October 9, 2026. **Recommended candidate**, not frozen or implemented. Refines D02/D13 and the commitment part of D14. Defines separate branch, ordered-vector and keyed-map commitments rather than one ambiguous “Merklix” API.

## Hash registry

`B3` is unkeyed BLAKE3 with exactly 32 output bytes. `H_name(x)=B3(ASCII(tag) || 00 || x)`. All tags are case-sensitive ASCII strings below. Prefix bytes such as `00` in node encodings are bytes, not characters. Integer encodings are P01 little-endian; hash comparisons use digest bytes. No hash function accepts arbitrary C++ struct memory.

| name | Exact tag |
| --- | --- |
| branch | `Lotus/v2/branch` |
| txid | `Lotus/v2/txid` |
| witnessid | `Lotus/v2/witnessid` |
| token | `Lotus/v2/token` |
| sighash | `Lotus/v2/sighash` |
| authplan | `Lotus/v2/authplan` |
| spentoutputs | `Lotus/v2/spentoutputs` |
| txroot | `Lotus/v2/txroot` |
| outpointkey | `Lotus/v2/outpointkey` |
| utxo | `Lotus/v2/utxo` |
| state | `Lotus/v2/state` |
| blockid | `Lotus/v2/blockid` |

The BLAKE3 primitive follows its [specification](https://github.com/BLAKE3-team/BLAKE3-specs/blob/master/blake3.pdf); application tags and tree rules are Lotus choices. [P04](header-and-mining.md) specifies a recursive BlockID/PoW candidate and its additional headerbody/headerwork domains; final choice remains D12. Hash collision resistance is an assumption, not a theorem about these tags.

## Branch MAST: unordered membership

```text
Leaf(script) = H_branch(00 || Bytes(script))
BranchNode(a,b) = H_branch(01 || min(a,b) || max(a,b))
```

Consume siblings bottom-up, hashing once per sibling. Empty sibling vector means root=Leaf(script). A proof only asserts membership; it has no direction bits, method index, hidden leaf-count claim or hidden uniqueness claim. Consensus limits proof depth; no unverified tree metadata enlarges that bound.

For reproducible wallet construction, recommend: sort distinct leaf hashes lexicographically; split a list of n>1 at the greatest power of two less than n; recursively build and sort each child pair at hashing. This construction is a wallet convention, not a property enforceable from a single proof. An owner may commit another finite binary tree. Duplicated leaves or alternative shapes provide no independent authorization and receive no accounting discount.

## Block transaction vector: ordered, count-bound tree

Let transaction i have WitnessID `w_i`, including the first coinbase. Define `T(xs)`:

```text
T([])  = H_txroot(02)
T([w]) = H_txroot(00 || w)
T(xs), n>1:
    k = greatest power of two strictly less than n
    return H_txroot(01 || T(xs[0:k]) || T(xs[k:n]))
TxRoot(xs) = H_txroot(03 || u32(n) || T(xs))
```

Children are ordered; no sorting, duplication or zero-padding occurs. Empty vector has a defined commitment for tools, but a block with no coinbase is invalid. Count is bounded before construction. This split strategy follows the ordered-tree principle in [RFC 6962 §2.1](https://www.rfc-editor.org/rfc/rfc6962#section-2.1); Lotus adds its own context and count wrapper and uses BLAKE3.

A transaction inclusion proof is `count:u32 || index:u32 || Vec(h32 siblings)` plus the transaction bytes or WitnessID being proved. Require `0 <= index < count`, count within the consensus block-transaction limit, and exact sibling consumption. Reconstruct recursively: for n=1 use the leaf; otherwise compute k, recurse into the child containing index, consume the next sibling from the bottom-up proof, and combine left/right according to index<k. Finally apply the count wrapper. No direction mask is serialized; count and index determine every direction. A proof API must clearly distinguish committed transaction membership from complete transaction/block validity.

## UTXO map: fixed-depth sparse binary tree

Recommend a 256-bit keyed sparse tree as the initial normative root algorithm. This is deliberately independent of whether a daemon stores it in a compressed trie, database or cache. A Crit-Bit tree is not automatically interchangeable with this root algorithm. The cost is up to 256 node hashes per changed key before shared-path optimization, which must be benchmarked under D08 before adopting the design.

```text
Outpoint = txid:h32 || output_index:u32
key = H_outpointkey(Outpoint)
Coin = Outpoint || Bytes(Output) || creation_height:u64
       || creation_parent_mtp:u64 || coinbase:u8
UtxoLeaf(key,coin) = H_utxo(00 || key || Bytes(Coin))
UtxoNode(d,l,r) = H_utxo(01 || u16(d) || l || r)       # d=0..255
Empty[256] = H_utxo(02 || u16(256))
Empty[d] = UtxoNode(d,Empty[d+1],Empty[d+1])           # descending d
```

Key bit d is `(key[d//8] >> (7-(d%8))) & 1`: most significant bit first. At depth 256 an occupied key stores exactly one Coin. Depth d has left child for bit zero and right for one. Root is at depth zero. Coin's outpoint must derive its key, coinbase must be 0 or 1, flags must be valid, and its output must satisfy ordinary output well-formedness. Height/time and coinbase flag are consensus metadata, not database hints. Inserting a different outpoint at an occupied hash key rejects; never overwrite or merge such entries.

Map root is independent of insertion order. Deletion replaces the leaf with Empty[256]. Updates recompute ancestor nodes; implementations may compress storage but must reproduce all implied hashes. Duplicate-key snapshot entries reject even when identical. Pre/post roots alone do not establish that the intervening transaction set was valid.

### Canonical membership and absence proof

For a queried Outpoint, encode:

```text
presence:u8 || [Bytes(Coin) if presence=1] || bitmap:32bytes || siblings
```

Presence is exactly 0 or 1. Bitmap bit j, indexed least-significant-bit first within byte `j//8`, describes the sibling j steps above the leaf (j=0..255). If zero use `Empty[256-j]`; if one consume one h32 from `siblings` in increasing j order. Siblings has exactly `popcount(bitmap)` entries and no separate count. An explicitly supplied default sibling is noncanonical and rejects.

Start at the occupied leaf hash for presence=1 or Empty[256] for absence. At step j combine at depth `d=255-j` using key bit d for left/right direction and the indicated sibling. After exactly 256 steps compare the expected map root. Present Coin must match the queried Outpoint. Truncated or extra sibling bytes reject. Absence proves that this key is empty at this root, under the hash assumptions; it does not prove an outpoint was never created or spent at another root.

This defines a bounded single-key proof (maximum 8192 sibling bytes plus framing/Coin), not an efficient multiproof. Multiproofs and snapshot range proofs may be designed later as transport/RPC encodings reproducing the same root. Their parsers still need independent resource bounds. Do not require these proofs in transaction witnesses unless a separate transaction-format decision explicitly does so.

## Full state root

A UTXO root alone omits the paper's stateful reward recurrence. Commit a versioned state envelope:

```text
StateRoot = H_state(00 || ChainID || height:u64
                    || UtxoRoot:h32 || Bytes(MonetaryState))
```

`MonetaryState` is a canonical record to be frozen with D10/D11: it must contain every recurrence/faucet value not uniquely derivable from authenticated headers/UTXOs. This packet does not choose opaque daemon bytes as its encoding. The header's former `hashUtxoMerklixRoot` is therefore renamed **state_root**. RPCs must expose both the envelope and UTXO proofs so clients can connect a coin proof to the header root. Height must match the validated block context.

Header ancestry supplies validated time/target context; a standalone UTXO snapshot does not. Snapshot admission must check envelope, unique entries, canonical Coin encodings, root reconstruction, monetary record and selected chain context, and clearly state which historical transitions were actually verified. Retained undo must restore every field of the prior envelope.

## Coinbase and root dependency order

Choose ChainID and genesis parameters → construct coinbase using parent ID/height → derive TxID/WitnessID → evaluate transitions and full state envelope → compute transaction/state roots → construct header → compute BlockID/PoW. The containing header hash is never embedded in its own coin records. In a non-genesis block, the parent's hash is already available. Genesis uses zero parent and an explicitly initialized monetary record.

## Acceptance obligations

Pin test vectors for empty/one/two/odd transaction trees, every proof direction, empty/occupied/deleted state maps, same map built in different orders, coin metadata changes and envelope restoration. Check both scalar and compressed implementations against the same vectors. Calibrate the 256-level map cost before freezing it; choose an alternative before genesis if the measured budget is unacceptable. This packet closes a candidate algorithm, not its performance or MonetaryState dependencies.
