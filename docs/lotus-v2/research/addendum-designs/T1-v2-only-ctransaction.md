# T1 — Transaction versions in Lotus V2: the legacy bridge (primary) and v7-only (alternative)

This is a design only. Nothing here was built, run or committed. Section 0
separates what was read in the source from what is assumed.

The user's final decision is the **legacy bridge** (Design A):

- v1/v2 transactions stay valid. They use the legacy format, txid,
  interpreter and sighash, and they spend and create only legacy coins.
- A v7 transaction can spend legacy P2PKH and P2SH coins through narrow,
  native template rules.
- v7 transactions create only V2 coins.

The earlier direction, **v7-only + leaf versions** (Design B), is kept as the
written alternative. The file name dates from the original brief ("V2-only
CTransaction").

---

## 0. Baseline, method, verified vs assumed

**Source read:** read-only `git show` / `git grep` / `git blame` at commit
`056a85acb0` of `/Users/shammah/repos/lotus-v2-addendum`. Nothing was checked
out, built or modified; this file is the only write.

**Tier boundary:**

- The eCash tier tip is `fe649023c3`. The V2 tier starts at `aa4da8d41b`
  (`v2/001`).
- Series files: `/Users/shammah/repos/lotus-v2-stack-repair/daemon/patches/{ecash,v2}/series`
  (108 + 64 lines). The V2 series ends at `063`.
- Commits after `cf4534ba38` (`v2/063`) are addendum work not yet in the
  series, so they are cited by hash.

**Patch attribution** (from blame and subjects):

| Hash | Patch or tier |
|---|---|
| `efe84d831e` | v2/031 (CTransaction → v7 wire) |
| `377ddd518a` | v2/032 (native state/monetary/script rules) |
| `99c26c1c71` | v2/033 (wallet) |
| `84a4fbb6d6` | v2/034 (functional fixtures) |
| `ff453606ae` | v2/035 (chronik-bridge) |
| `2b6456ec68` | v2/036 (miner) |
| `9fb1565150` | v2/040 (rpc) |
| `a3665460ea` | v2/045 (native identities/serialization) |
| `5891e31fe9` | v2/051 (BIP30 skip) |
| `3a31b90fd8` | v2/056 (mining pool) |
| `f61b0e8d64` | v2/062 (placeholder genesis) |
| `52bea1842b`, `16bc33fd75`, `7bf1c1002e`, `c597186e10`, `b12a25312a` | Addendum |
| `fe7ae5f9da`, `219ba2acd3` | In the repo, but not series entries by subject |
| `0a052c7a09` | eCash-tier Merklix overlay (introduced `CTxOut::ToV2Output`/`BranchLeaf` there) |
| `f839f1a3b8` | eCash-tier "authenticate and install eCash UTXO state" (introduced the legacy state-coin encoding) |
| `b44e0d3870`, `fddb00fc8c`, `e614433d1a`, `4dc94d1036`, `f76e0c6310`, `05ef30bbc8` | Upstream |

### Verified in source

**Transaction shapes and identities**

- Three shapes decode and get a TxId today (`transaction.h:450-463`,
  `466-610`):
  - (1) pure v7 wire;
  - (2) "wrapped v7": raw version `0x80000007`/`0xC0000007`, legacy
    `CTxIn`/`CTxOut` bytes, `nVersion=7`;
  - (3) legacy `nVersion` 1/2.
- Shapes 2 and 3 get V2-style identities through implicit mappings, and the
  version is XORed into byte 0 of the id (`transaction.cpp:384-396`). The flat
  fallback digest (`400-446`) is used when the mapping fails.
- The eCash tier's TxId equals TxHash, which equals the SHA256d of the legacy
  serialization (`fe649023c3:src/primitives/transaction.cpp:172-178`). So a
  "legacy txid" is well defined and needs no V2 machinery.

**Where shapes 2 and 3 are refused or accepted**

- Only RPC refuses shapes 2 and 3: `rpc/mempool.cpp:49-59`
  (`bad-txns-non-v7-format`, `-allowlegacytx`, `LOTUS_ALLOW_LEGACY_TX`).
- `-allowlegacytx` is not registered in `init.cpp`, and no test passes it.
- P2P, blocks (`tx_verify.cpp:58-63` allows 1/2/7) and the in-process
  `CWallet` (`wallet.cpp:2086-2126`, legacy `::SignTransaction`) all accept or
  produce these shapes.

**Implicit output and input mappings**

- `CTxOut::ToV2Output` (`transaction.cpp:140-198`) maps any legacy
  `scriptPubKey` to a V2 output. It tries V2 decode, then OP_RETURN + V2
  decode, then falls back to `branches={BranchLeaf(script)}` (an unversioned
  V0 leaf, so legacy bytes would run on the renumbered V2 VM).
- `CTxIn::ToV2Input` (`28-83`) turns `scriptSig` into witness[0].script.

**Coins and the V2 state**

- `Coin` (`coins.h:33-55`) stores `uint32_t nHeightAndIsCoinBase =
  (height << 1) | coinbase`, plus C17a `nFeePerOutput`/`nExpirationHeight`.
  It is serialized as `VARINT(nHeightAndIsCoinBase)` +
  `TxOutCompression(out)` (`coins.h:95-104`).
- `TxOutCompression` (`compressor.h:96-121`) already has two encodings: a V2
  tag and legacy `ScriptCompression`.
- The V2 state (sparse Merkle UTXO set, MDBX `disk_state`, fast sync) already
  has a **legacy coin representation**:
  - `lotus::v2::Output::legacy_script` (`lotus_v2/output.h:37`);
  - `EncodeCoin` writes `0x80 || value u64 || CompactSize(len) || script`
    for it (`lotus_v2/sparse_state.cpp:107-131`);
  - `DecodeCoinBytes` reads it back (`163-173`);
  - `UtxoLeaf` commits it (`214-...`);
  - `lotus_v2/legacy_coin.h` converts between it and `CTxOut`.
  All of this came from eCash tier `f839f1a3b8` and is used by
  `ecash_state_sync_tests`/`native_state_sync_tests`.
- `EncodeOutput` refuses legacy outputs: "legacy state output is not a V2
  transaction output" (`lotus_v2/output.cpp:77`).

**V2 signing**

- V2 signatures are BIP340 over a 32-byte x-only key. 64 bytes means mode 0;
  65 bytes ending in `0x01`/`0x02` means mode 1/2 (`signing.cpp:560-579`).
- `SigningMessage(prepared, input, witness, mode)` (`signing.cpp:459-529`):
  - mode 0 = chain_id, txid (witness-free) and coins_root;
  - mode 1 = own-input hash and all outputs;
  - mode 2 = own-input hash and the same-index output.
- Every message contains the invocation selector `(1, input, branch_index,
  leaf_hash)` (`384-390`).
- Coins enter coins_root as `CoinEntryLeaf(OutputBytes(coin))` (`354-358`).

**Placeholder genesis** (`chainparams.cpp:89-134`, v2/062)

- The second transaction is `nVersion=7` with `nFlags=1`, no witnesses, and
  a P2PK `scriptPubKey` output.
- Its output has empty `vBranches`, so it serializes through the wrapped path
  (`transaction.h:466-473`, `598-610`).
- The coinbase output is an implicit V0 leaf over the P2PK bytes.
- Regtest genesis is coinbase-only (`chainparams.cpp:69-82`).

**Python framework**

- Python `CTransaction()` defaults to `nVersion = 1` (`messages.py:439`).
- MiniWallet (`wallet.py:62-447`) builds legacy txs that pay
  `ADDRESS_ECREG_P2SH_OP_TRUE` or raw P2PK.
- There is **no V2 MiniWallet class** in `test_framework/`. Native builders
  live inside `lotus_v2_native_e2e.py:105-192` and
  `lotus_v2_loopback_tps_stress.py:55-110`.

**Miner fund**

- The miner fund check is consensus code (`minerfund.cpp:71-87`). It accepts
  a legacy `scriptPubKey` via `ExtractDestination`, or a V2 output equal to
  the implicit mapping of `GetScriptForDestination(dest)`.

### Assumed, not verified

- Which script flags the V2 node currently applies to v1/v2 inputs. I assume
  `GetBlockScriptFlags` returns the eCash mandatory set; not traced.
- (Now verified, §2.0.) Every transaction's outputs, legacy ones included,
  enter the V2 state through `ToV2Output`, as V0-leaf V2 outputs
  (`primitives/block.cpp:587`, `612`, `731`, `935`, `1163-1214`;
  `validation.cpp:2999`).
- That functional tests outside the `v2/034` set currently pass. Many submit
  legacy txs through `sendrawtransaction`, which is refused today.
- How the xpi1 address format (`v2/063`) represents legacy destinations.
- The VARINT byte-count claims below come from the Bitcoin VARINT definition,
  not from measuring this tree.

---

## 1. The two designs side by side

### 1.1 Design A — legacy bridge (primary, user-decided)

**Transaction formats**

- **Three formats, each with its own identity.** Versions 1 and 2 use the
  legacy format: legacy TxId = TxHash = SHA256d(serialization), the legacy
  interpreter and the legacy FORKID sighash. Version 7 uses the V2 format with
  structural V2 identities.
- Any other raw version is a decode failure, `bad-txns-version`.
- The wrapped form (`0x80000007`) and the flat fallback ID are deleted.

**Coins**

- Every coin carries a **legacy-created bit**.
- A v1/v2 transaction may spend only legacy coins and creates only legacy
  coins.
- A v7 transaction creates only V2 coins.

**v7 spends of legacy coins**

- A v7 transaction may spend a legacy coin only if its `scriptPubKey` is
  exactly P2PKH or P2SH:
  - **P2PKH:** the node checks `HASH160(pubkey)` natively, then a V2
    `CHECKSIG` (BIP340, V2 message, V2 modes).
  - **P2SH:** the node checks `HASH160(redeem script)` natively, then runs
    the redeem script on the **legacy interpreter byte-for-byte**. A checker
    verifies legacy `CHECKSIG`-family signatures against the V2 message.
- Every other legacy script is unspendable by v7.

**Coinbase**

- A v1/v2 coinbase is allowed only where the per-network consensus parameter
  `allowLegacyCoinbase` is true. It is true on regtest and false on mainnet
  and testnet.
- The coinbase's version sets its coins' legacy bit, as for any transaction.
- **Mainnet and testnet therefore have no legacy coins.** v1/v2 transactions
  are valid there but can never find a coin to spend, so the bridge is inert
  outside regtest.
- See §2.0 for the reasons and for how a coinbase version is selected.

### 1.2 Design B — v7-only + leaf versions (alternative)

- Only v7 is valid anywhere.
- Legacy *scripts* survive as branch leaves that commit to a leaf version: 0
  = V2 VM, 1 = the legacy interpreter with V2-message signatures, 2–255 =
  unconditional success.
- There are no legacy coins.
- Tests build v7 natively. A test-only `CTransactionLegacy` exists only for
  upstream interpreter vectors.
- Section 9 gives its full specification.

### 1.3 Comparison

| | **A: legacy bridge** | **B: v7-only + leaf versions** |
|---|---|---|
| **Consensus surface** | Two tx grammars and two id schemes. Legacy interpreter + legacy sighash for v1/v2. Direction rules (bit). Two v7 template rules (P2PKH native, P2SH legacy-interpreter with V2-message checker). Legacy and v7 coinbases | One grammar, one id scheme. Leaf-version dispatch. Legacy interpreter reachable only through V1 leaves with the V2-message checker. A cost table for legacy opcodes inside V2 invocations |
| **Code to maintain** | Legacy serialization, `SignatureHash`, `PrecomputedTransactionData`, legacy standardness, legacy `CWallet` signing, Python legacy classes; all stay. Hybrid fields go away (variant representation). New: coin bit, two template rules, legacy coin wire in the V2 signer | Legacy serialization/sighash/standardness leave the node; legacy wallet signing is rewritten as V1-leaf witnesses; Python legacy classes are rewritten. New: leaf versions in codec/hash/signer, V1-leaf evaluator, cost table |
| **Test impact** | Small. Chained legacy C++/Python tests run unchanged once their coins are legacy (legacy coinbases). Changes only where tests rely on the hybrid shape, the implicit mapping, `bad-txns-non-v7-format` or `bad-txns-v2-identity`. New bridge tests | Large. About 50 C++ test files and about 170 functional tests build or fund legacy txs and must be ported to v7 builders. Interpreter vectors move to a test-only type. Many fixture hashes are regenerated |
| **ID handling** | Legacy: SHA256d. v7: structural V2. No fallback, no XOR, no wrapped form. Both namespaces share `COutPoint` (different hash functions; collision probability negligible). Legacy chains keep their TxIds | One id function; constructor throws on non-encodable input. Spend TxIds unchanged, TxHashes change (+1 witness byte) |
| **Hardware wallets** | Existing eCash-style firmware (legacy FORKID sighash, ECDSA/Schnorr) keeps working for v1/v2 spends of legacy coins. A v7 spend of a legacy coin needs the V2 message: BIP340 for P2PKH, legacy sig encoding over the V2 message for P2SH. That is new firmware either way | All spends need V2-message firmware, including legacy-shaped scripts. No legacy signing remains usable |
| **Long-term cost** | Legacy format is consensus forever. The user's earlier objection (a), "two formats forever", applies but is narrowed: legacy coins never mix with V2 coins except through the one-way bridge | One format. Legacy interpreter semantics survive as an opt-in leaf type |

Recorded history of alternatives:

- **Legacy→V2 transaction adapter** (the original T1 brief): rejected.
  Converting A changes A's TxId, so a B that spends A breaks.
- **(a) Keep v1/v2 valid, spendable only by v7:** rejected in the first
  review ("two formats forever"). The second review revived a narrower form,
  which is Design A: legacy↔legacy plus a one-way template bridge.
- **(b) v7 outputs compatible with legacy as a single-branch P2SH-like hash:**
  this is Design B's V1 leaf.
- **HASH160 opcode** for P2PKH in V2 scripts: deferred. Design A checks hash160
  natively. An EXT2 HASH160 opcode is an optional later addition for V2
  scripts that must check legacy addresses (Q9).

### 1.4 Legacy VM or V2 VM for v7 spends of legacy coins

| | Legacy (eCash) interpreter | V2 VM / native check |
|---|---|---|
| P2PKH | Possible (`DUP HASH160 … CHECKSIG` with a V2-message checker) | **Chosen.** A fixed native hash160 check plus V2 `CHECKSIG`. No legacy bytecode runs. Wallets sign exactly like a native V2 key spend (BIP340, 64/65-byte) |
| P2SH | **Chosen.** Runs existing redeem scripts (legacy bytecode) byte-for-byte. Reuses the interpreter that v1/v2 transactions need anyway. One meaning per coin | Unsafe. The coin commits only to `hash160(redeem)`; running those bytes on the renumbered V2 VM gives the same coin a second, possibly weaker, meaning, which is a theft risk |
| Wallet signing | Legacy signature encoding (DER or 64-byte Schnorr) + sighash byte, over the V2 message (§2.4) | BIP340 64/65-byte over the V2 message |

The wallet impact is the same in kind for both: any v7 spend signs the V2
message. Only the signature encoding differs. The rule is therefore
standardized per template:

- P2PKH always uses the V2 encoding.
- P2SH always uses the legacy encoding plus a fixed hashtype→mode map.

---

## 2. Design A specification

### 2.0 Source of legacy coins

**The problem.** Design A has three rules:

- legacy transactions spend only legacy coins;
- v7 creates only V2 coins;
- nothing migrates backward.

Under those rules a chain whose coinbases are all v7 never contains a legacy
coin, so no v1/v2 transaction can ever be valid. The inherited test suite
mines a coinbase and spends it with v1/v2 transactions:

- functional tests use `create_coinbase`, `generatetoaddress`, MiniWallet and
  chained legacy transactions;
- C++ tests use `TestChain100Setup`, `m_coinbase_txns` and
  `CreateValidMempoolTransaction`.

That suite is the reason legacy support is kept at all. It must therefore run
**unchanged**, which means it needs legacy coinbases.

**Does the V2 coinbase have to be v7?** Each candidate blocker was checked at
`056a85acb0`:

| Candidate blocker | Finding | Blocks a legacy coinbase? |
|---|---|---|
| Header transaction root (`primitives/block.cpp:889-909`, `ComputeV2TxRootFromSubtreeA`; checked at `validation.cpp:4463`) | The coinbase leaf hashes `GetId() ‖ GetHash()`. A legacy coinbase supplies SHA256d for both | No |
| State root (`primitives/block.cpp:925-945` coinbase coins, `575-620`/`722-740`/`1163-1214` other transactions; `validation.cpp:2990-3005`, `4845-4857`) | Every transaction's outputs, legacy ones included, enter the SMT through `ToV2Output()`. So **the state commitment already covers legacy coins**, but as V0-leaf V2 outputs, without a legacy marker. Design A switches legacy-transaction outputs to `LegacyStateOutput` (the 0x80 encoding, `sparse_state.cpp:111-118`), so the commitment then distinguishes them | No (encoding change) |
| Coinbase height and uniqueness (`validation.cpp:7090-7111` with its BIP34 `scriptSig` branch; `4334-4352` BIP30 for non-v7 coinbases; `tx_check.cpp:117-121` legacy coinbase length) | The legacy branches already exist and are reachable today | No |
| Miner output conversion (`node/miner.cpp:273-282`) | Converts every coinbase output to V2 form with `ToV2Output` | Producer only: make it conditional on the coinbase version |
| Miner fund (`minerfund.cpp:71-87`, consensus) | Accepts a legacy `scriptPubKey` via `ExtractDestination`, so it works for a legacy coinbase | No |
| Treasury (`avalanche/treasury.cpp:735-748`, a parking policy compared by `scriptPubKey ==`) and staking rewards (`node/miner.cpp:239-247`) | Winners are legacy scripts (`treasury.cpp:239-249`), and a legacy coinbase holds them as they are. Only the v7 coinbase needs an explicit V2 encoding (Q6) | No |
| HAS_STATE (`tx_check.cpp:35-52`) | Already rejects legacy-created HAS_STATE outputs. Unrepresentable after T1-02 | No |
| Coinbase-context commitment `CheckCoinbaseContext` (`validation.cpp:7091-7101`) | Applies to v7 coinbases only. Legacy coinbases use BIP34 + BIP30 | No |
| Monetary state, C17a expiry (`block.cpp:580-605`) | Work on output values and spendability, not on the format | No |

**Conclusion: nothing forces the coinbase to be v7.** The only consensus
change needed is one per-network parameter.

**Options considered:**

| Option | Assessment |
|---|---|
| **(1) Legacy or v7 coinbase; the coin bit follows the creating transaction's version** | **Adopted, with a per-network gate.** No special case: the coinbase is "any transaction" for the bit. Nothing breaks (table above) |
| (2) Legacy transactions may spend template-type V2 coins (P2PKH/P2SH-like) with the legacy sighash, mirroring the bridge | **Fallback only. Needs the user's explicit approval**, because it is a backward migration (V2→legacy), which the user ruled out. It would also give V2 coins a legacy-sighash meaning |
| (3) Move inherited legacy tests to v7 and keep legacy support only for … | **Rejected by the user.** Without those tests nothing on the V2 chain needs legacy support, so it would be pointless |

**Adopted rule (user decision):**

**(a) Consensus.** `Consensus::Params::allowLegacyCoinbase`:

| Network | Value |
|---|---|
| regtest | `true` |
| mainnet, testnet | `false` |

- A coinbase with `nVersion ∈ {1,2}` is valid iff the parameter is true;
  otherwise `bad-cb-version`.
- With it true, legacy coinbases follow the legacy rules (BIP34 + BIP30,
  `bad-cb-length`).
- Their outputs get `legacy=1` through the same `AddCoins` rule as every other
  transaction (A3).
- Consequence: **mainnet and testnet have no legacy coins.** v1/v2
  transactions and the v7 bridge are consensus-defined there but can never be
  exercised.

**(b) Selection.**

- `BlockAssembler::Options::coinbase_version` takes `{1, 2, 7}` (default 7).
- An optional `coinbase_version` argument is added to `generatetoaddress`,
  `generatetodescriptor` and `generateblock`, and to `getblocktemplate` as the
  template-request key `"coinbase_version"`, which affects the returned
  `coinbasetxn`.
- The argument's default comes from the startup arg `-coinbaseversion=<1|2|7>`.
  It is regtest-only: init fails if it is set on another network. Its default
  is 7.
- Requests for 1 or 2 on a network with `allowLegacyCoinbase=false` fail with
  `RPC_INVALID_PARAMETER` before mining.
- A legacy coinbase's outputs come from the payout script as they are. A v7
  coinbase requires a V2 payout (`OutputForDestination`).

**Framework default:** the test framework passes `-coinbaseversion=2` to every
regtest node (`test_node.py` default args). The default is chosen from counts
at `056a85acb0` (`git grep` heuristics, approximate):

| Suite | Tests that mine/create coinbases and spend with legacy txs | Tests that do so with v7 txs |
|---|---|---|
| Functional | 147 of 237 | 3 (`lotus_v2_loopback_tps_stress.py`, `lotus_v2_native_e2e.py`, `p2p_v2_fast_sync_and_reverse_peel.py`) |
| C++ (`TestChain100Setup`/`coinbaseKey`/`CreateValidMempoolTransaction`) | 36 files | 8 files with native coinbases or transactions |

- The other 87 functional tests mine without spending.
- The three V2 functional tests pass `-coinbaseversion=7` (or the RPC
  argument).
- C++ `TestChain100Setup` builds `BlockAssembler` with `coinbase_version=2`
  by default. V2 unit tests request 7 explicitly.

**(c) Python `create_coinbase`** (`blocktools.py:120-154`). It already builds
an `nVersion=1` coinbase with a BIP34 `script_BIP34_coinbase_height`
`scriptSig` (`167-174`), a null prevout and legacy outputs. Regtest accepts
such blocks today and will continue to:

- versions 1, 2 and 7 are allowed (`tx_verify.cpp:58-63`);
- the BIP34 branch exists (`validation.cpp:7103-7111`);
- the legacy coinbase length rule exists (`tx_check.cpp:117-121`);
- `create_block` leaves `hashStateRoot` null, which `validation.cpp:4850-4857`
  accepts when `fPowAllowMinDifficultyBlocks` is set and `-strictstateroot`
  is not. That is true on regtest, and on testnet too (pre-existing, R9).

Under Design A, such a coinbase is legal through `allowLegacyCoinbase`, and
its outputs are legacy coins. One thing must change at the same time:
**Python must compute the legacy txid as SHA256d** (today it mirrors the C++
version-XORed V2 id). Otherwise `calc_merkle_root` disagrees with the node.
This is part of T1-02.

**(d) Code sites.**

- `node/miner.cpp:273-282`: the `ToV2Output` loop is applied only for
  `coinbase_version == 7`. The legacy `scriptSig`/`vCoinbaseData`
  double-write at `223-226` and `287-292` is split by version.
- The state-coin builders listed in the table above use `LegacyStateOutput`
  for v1/v2 transactions and `ToV2Output` (the V2 body) for v7.

### 2.1 Consensus rules

Notation: `legacy(coin)` means the coin's legacy-created bit.

| # | Rule | Reject reason |
|---|---|---|
| A1 | A raw version other than 1, 2 or 7 does not decode | `bad-txns-version` (decode failure) |
| A2 | A v1/v2 input must spend a coin with `legacy(coin)` set | `bad-txns-legacy-spends-v2-coin` |
| A3 | Outputs of a v1/v2 transaction (coinbase included) are created with `legacy=1` | (rule of `AddCoins`) |
| A4 | Outputs of a v7 transaction (coinbase included) are created with `legacy=0`. A v7 output cannot hold a legacy script: the type has no field for it (§2.8) | — |
| A5 | A v7 input (`nFlags=1`) spending a coin with `legacy(coin)` set must have `nPathIndex == 0` and exactly one witness with no siblings. The coin's `scriptPubKey` must be exactly P2PKH (`76 a9 14 <20> 88 ac`, 25 bytes) or P2SH (`a9 14 <20> 87`, 23 bytes) | `bad-txns-v2-legacy-coin-template` (other script) / `bad-txns-v2-legacy-coin-witness` (shape) |
| A6 | P2PKH bridge (§2.3) | `bad-txns-v2-legacy-p2pkh` (hash), script error `SIG_*` (signature) |
| A7 | P2SH bridge (§2.4) | `bad-txns-v2-legacy-p2sh-hash` (hash); otherwise the legacy `ScriptError` |
| A8 | A v7 mint (`nFlags=3`) never refers to a coin, so A5 does not apply. A V2 spend of a V2 coin is unchanged | — |
| A9 | Coinbase: a v1/v2 coinbase is valid only if `allowLegacyCoinbase` (§2.0). It must start its `scriptSig` with `CScript() << nHeight` (BIP34, `validation.cpp:7103-7111`, existing branch), and BIP30 checks apply to it (`4339-4352`, existing). A v7 coinbase keeps `CheckCoinbaseContext` and the BIP30 skip. The miner fund (`minerfund.cpp`) accepts a legacy-script output in a legacy coinbase, or an explicit V2 destination output in a v7 coinbase | `bad-cb-version`, `bad-cb-height`, `bad-txns-BIP30`, `bad-cb-minerfund` |

### 2.2 The legacy-created coin bit

**In-memory layout and serialization.** The field is
`Coin::nHeightAndIsCoinBase = (height << 2) | (legacy << 1) | coinbase`:

- New accessors: `IsLegacy()`, plus `GetHeight() = >> 2`. The constructor
  gains `bool fLegacy`.
- Heights must be `< 2^30`, which is asserted. That is about 2,000 years at
  1-minute blocks.
- The struct size is unchanged, and spend-time checks read the bit with no
  extra lookup.

**VARINT size cost.** `VARINT` stores 7 bits per byte, so shifting by one more
bit adds one byte only where the value crosses a 7-bit group boundary:

- That happens for heights in roughly [2^5,2^6), [2^12,2^13), [2^19,2^20) and
  [2^26,2^27).
- For about 524k–1.05M blocks (roughly 1–2 years) every coin is one byte
  larger in the LevelDB chainstate and undo files. Outside those bands the
  size is unchanged.
- So "zero extra bytes" holds for most heights, not all.

**Where the bit is checked:**

- **Consistency:** the bit must agree with the stored output representation.
  A legacy coin holds a legacy `CTxOut` (§2.8) and compresses through
  `ScriptCompression`; a V2 coin compresses through the V2 tag. `Coin` decode
  fails if they disagree.
- **Undo data:** `CTxUndo` stores `Coin`, so it carries the bit
  automatically. Disconnect restores it.

**V2 state commitment.** No new field is needed:

- A legacy coin is recorded with `lotus::v2::Output::legacy_script` and
  encoded by the existing `EncodeCoin` 0x80 discriminator
  (`sparse_state.cpp:111-118`).
- So `UtxoLeaf`, the state root, `disk_state` (MDBX), fast-sync shards and
  snapshot transfer already distinguish legacy coins.
- `ConnectBlock`/`DisconnectBlock` must build state coins with
  `LegacyStateOutput(out)` for legacy coins (`legacy_coin.h:8-14`) and with
  `ToV2Output()` only for V2 coins.

**Expiry and fees.** C17a expiry applies identically:

- `fee_per_output` for a legacy transaction comes from its fee and its
  spendable (non-OP_RETURN) outputs.
- The cleaning crew may sweep expired legacy coins.

**Formats and migration.** The coin DB format changes, as does the state
content of legacy-tx outputs. The placeholder chain resets, `-reindex` is
required, and there is no migration.

### 2.3 P2PKH bridge (v7 input spending a legacy P2PKH coin)

**Witness** (the v7 wire is unchanged):

- `nFlags=1`, `nPathIndex=0`, `vWitnesses.size()==1`.
- `w.script` is empty, `w.siblings` is empty.
- `w.arguments == [sig, pubkey]`, in exactly this order (the `scriptSig`
  push order), as follows:

| Argument | Contents |
|---|---|
| `sig` | V2 encoding: 64 bytes (mode 0), or 65 bytes whose last byte is `0x01` or `0x02` (modes 1, 2) |
| `pubkey` | 33-byte compressed SEC: `0x02`/`0x03` ‖ x |

- Uncompressed 65-byte keys are not accepted (Q3). Such coins remain
  spendable by v1/v2.

**Check**, natively in `CScriptCheck` with no VM program:

1. `RIPEMD160(SHA256(pubkey)) == scriptPubKey[3..23]`, else
   `bad-txns-v2-legacy-p2pkh`.
2. `msg = SigningMessage(prepared, nIn, 0, mode)`, with the legacy-coin
   preparation rules of §2.5.
3. `VerifyBip340Signature(xonly = pubkey[1..33], sig, msg)` must be `Valid`.
   This goes through `BatchSigCollector::Add` like any V2 BIP340 signature.
   - BIP340 x-only keys mean the signer uses `d` or `-d` according to the
     parity of P. This is the standard behaviour of `secp256k1_keypair`, so
     wallets sign exactly as for a native V2 key.

**Cost:** the cost of one V2 `CHECKSIG`, plus the V2 structural byte cost of
the witness, plus a fixed HASH160 charge. The charge is a new
`VmCostProfile` constant, equal to the cost of SHA256 over 33 bytes plus a
RIPEMD160 block.

### 2.4 P2SH bridge (v7 input spending a legacy P2SH coin)

**Witness:**

- `nFlags=1`, `nPathIndex=0`, `vWitnesses.size()==1`, no siblings.
- `w.script` = the redeem script.
- `w.arguments` = the pushes that would precede the redeem script in a legacy
  `scriptSig`, bottom of the stack first.

**Size limits:**

- Redeem script ≤ `MAX_SCRIPT_ELEMENT_SIZE` (520), the limit a legacy push
  would have.
- Each argument ≤ 520.
- Argument count ≤ the V2 profile `max_arguments`.

**Check:**

1. `RIPEMD160(SHA256(w.script)) == scriptPubKey[2..22]`, else
   `bad-txns-v2-legacy-p2sh-hash`.
2. Synthesize
   `scriptSig' = MinimalPush(arguments[0]) ‖ … ‖ MinimalPush(arguments[n-1]) ‖ MinimalPush(w.script)`.
   Then call the **unchanged**
   `VerifyScript(scriptSig', coin.scriptPubKey, LEGACY_FLAGS, LegacyBridgeSignatureChecker(...), metrics, &err)`.
   - `LEGACY_FLAGS` is exactly the flag set the V2 node applies to v1/v2
     inputs at the same height (`GetBlockScriptFlags`; Q4 if it changes over
     time).
   - This runs the full legacy P2SH evaluation byte-for-byte: hash160 again,
     redeem-script evaluation, `CLEANSTACK`, `SIGPUSHONLY`, and the
     `INPUT_SIGCHECKS` density rule against `|scriptSig'|`.
   - The only difference from a v1/v2 spend of the same coin is the
     signature checker.
3. `LegacyBridgeSignatureChecker : BaseSignatureChecker` behaves as follows:

| Method | Behaviour |
|---|---|
| `CheckSig(sig‖t, pubkey, scriptCode, flags)` | Signature encodings are the legacy ones: ECDSA DER or 64-byte eCash Schnorr, plus the trailing hashtype byte `t`, with 33/65-byte keys. `t` must have FORKID and maps to a V2 mode (table below). The message is `SigningMessage(prepared, nIn, 0, mode)`. `scriptCode` and `OP_CODESEPARATOR` do not change the message, because the selector commits to the redeem script (§2.5). Verification uses the existing legacy verifiers and the `BatchSigCollector` legacy items (`signing.h:150-157`). This one method covers `CHECKSIG`, `CHECKSIGVERIFY`, `CHECKMULTISIG(VERIFY)` and Schnorr multisig |
| `VerifySignature`/`CheckDataSig` | Unchanged; the message is the stack data. `CHECKDATASIG(VERIFY)` gives the same result on both paths |
| `CheckLockTime(n)` | The same comparison as legacy, using `nLockTime = lock >> 8` from the v7 lock. The lock type must agree with `n`'s height/time class. The input sequence must not be FINAL |
| `CheckSequence(n)` | BIP68 on the v7 input sequence. There is no `nVersion >= 2` gate, because v7 always qualifies |

Hashtype to mode:

| `t` | V2 mode |
|---|---|
| `0x41` ALL\|FORKID | 0 |
| `0xC1` ALL\|FORKID\|ANYONECANPAY | 1 |
| `0xC3` SINGLE\|FORKID\|ANYONECANPAY | 2 |
| anything else | `SCRIPT_ERR_SIG_HASHTYPE` |

**Cost:**

- SigChecks from `metrics.nSigChecks` are charged as V2 `CHECKSIG` costs and
  added to the block resource cost. Legacy v1/v2 inputs are charged the same
  way (§2.6).
- The legacy interpreter's own limits (opcount, stack size, the 520-byte
  element limit, 64-bit integers) bound the remaining execution.

**Same-result property.** For any redeem script, args and flags, the result is
identical on both paths whenever no signature opcode reaches a signature
check. With signatures, each path's result is the same function of
"signature valid for this path's message". The tests in §6 rely on this
property.

### 2.5 V2 signing message for legacy coins

`PreparedSigningContext::PrepareChecked` (`signing.cpp:~250-457`) accepts
`ResolvedCoins` whose entries may be legacy (`Output::legacy_script`). Three
things are defined for them.

**1. Coin wire.**

```
LegacyCoinWire = 0x80 || value:u64le || CompactSize(|script|) || script
```

- This is the same byte string as `EncodeCoin`'s output segment
  (`sparse_state.cpp:111-118`).
- `CoinEntryLeaf(LegacyCoinWire)` goes into coins_root (mode 0), and
  `OwnInputHashFromCoinWire` uses it for modes 1 and 2.
- `OutputBytes` keeps refusing legacy outputs for *transaction* outputs
  (`output.cpp:77`). Only the coin-wire path gains the legacy case.

**2. Selector leaf.** `invocation.selector` is
`(1, input_index, branch_index=0, legacy_leaf)`, where:

```
legacy_leaf = TaggedHash("Lotus/v2/branch",
                         0x03 || CompactSize(|coin_script|) || coin_script
                              || CompactSize(|w.script|) || w.script)
```

- Prefix `0x03` is distinct from leaf `0x00`, node `0x01` and Design B's
  `0x02`, so no V2 branch leaf can collide with it.
- `legacy_leaf` commits to both the template (P2PKH vs P2SH, and the hash)
  and the redeem script.
- A signature for a bridge spend can therefore never verify as a native V2
  spend, or as a different redeem script.

**3. Membership check.** For legacy coins, the V2 branch-membership check
(`372-382`) is replaced by rule A5 and the hash160 check of §2.3/§2.4.

The fast paths are disabled for any transaction that has a legacy-coin input:
`TxIsAllAutomaticSuccess`, `InputIsPureMode0Checksig`, and the 45-byte batch
path at `validation.cpp:371`.

### 2.6 Limits, costs and fees for v1/v2 transactions on the V2 chain

| Item | Rule |
|---|---|
| Inputs/outputs | The V2 cap of 256/256 applies to **all** versions. `tx_check.cpp:26-33` drops its `nVersion == 7` guard. This keeps block cost and memory bounds uniform |
| Size | `MAX_TX_SIZE` / `MIN_TX_SIZE` unchanged, for all versions |
| SigChecks | The eCash per-tx sigcheck limit still applies to v1/v2. Each legacy sigcheck counts as one V2 `CHECKSIG` toward the V2 block resource cost (`lotus_v2/block_cost`, v2/009), the same as bridge sigchecks |
| Fees | The same fee-rate rules by serialized size (fee hysteresis controller, minimum relay fee). Fee burn and miner split are unchanged (monetary rules operate on fees, not formats) |
| Expiry | C17a lifespan and rent apply identically (§2.2) |
| Tokens/state | A legacy output cannot express token, state or burn flags, so v1/v2 cannot create or move V2 tokens. `bad-txns-legacy-state-output` (`tx_check.cpp:35-52`) is deleted because the case is unrepresentable |

### 2.7 Mempool and RPC

- Delete `IsDisallowedNonV7Tx`, `bad-txns-non-v7-format`, `-allowlegacytx`
  and `LOTUS_ALLOW_LEGACY_TX` (`rpc/mempool.cpp:49-59` and the three call
  sites).
- `sendrawtransaction`, `testmempoolaccept`, `submitpackage` and P2P accept
  v1/v2 and v7, subject to consensus (A1–A9) and policy:
  - v1/v2 use the existing legacy `IsStandardTx` (`policy.cpp:70-140`),
    version 1/2 only.
  - v7 uses the V2 standardness of the `is_v2_native_tx` path
    (`validation.cpp:1116-1128`, `1296-1305`), now selected by version, not
    by inspecting `nFlags`.
  - Bridge inputs are standard.
- Package rules (`rpc_packages`, 1p1c) treat mixed packages normally: a
  legacy parent with a v7 child that spends it through the bridge is valid.
- Decode failures report their reason: `DecodeHexTx(…, std::string *error)`
  (`core_read.cpp:196-214`) gives `"TX decode failed: bad-txns-version"`.

### 2.8 `CTransaction` representation (recommendation)

**Recommended:** one `CTransaction` class with a version tag and per-element
variants. It has no union of legacy and V2 fields:

```cpp
struct LegacyTxIn { CScript scriptSig; };
struct V2TxIn     { uint8_t nFlags; uint8_t nPathIndex;
                    std::vector<lotus::v2::BranchWitness> vWitnesses;
                    std::vector<uint8_t> vCoinbaseData; };   // empty <=> no coinbase data
class CTxIn  { public: COutPoint prevout; uint32_t nSequence;
               std::variant<LegacyTxIn, V2TxIn> body;
               bool IsLegacy() const; const LegacyTxIn &Legacy() const; const V2TxIn &V2() const; };

struct V2TxOutBody { uint8_t nFlags; uint256 tokenId, stateRoot;
                     std::vector<lotus::v2::Hash32> vBranches; std::vector<std::vector<uint8_t>> vPaths; };
class CTxOut { public: Amount nValue;
               std::variant<CScript /*legacy scriptPubKey*/, V2TxOutBody> body;
               bool IsLegacy() const; const CScript &LegacyScript() const; const V2TxOutBody &V2() const; };

class CTransaction {   // invariant: nVersion in {1,2} <=> every vin/vout IsLegacy(); nVersion == 7 <=> none is
    const uint32_t nVersion;  const Span<const CTxIn> vin;  const Span<const CTxOut> vout;
    const uint64_t nLock;     // v1/v2: nLockTime (low 32 bits); v7: V2 lock (value << 8 | type)
    uint32_t nLockTime() const;   // legacy view for IsFinalTx/CLTV
    TxId GetId() const; TxHash GetHash() const; // legacy: SHA256d (equal); v7: structural V2
    ...
};
```

- **Removed:**
  - `nFlags == 0` "auto-infer"; `fHasCoinbaseData`; `fHasV2Lock`/`nV2Lock`
    duplicates;
  - `HasStructuralV2Identity`, the cross-representation `operator==`, and the
    synthetic `scriptPubKey` projection for V2 outputs (replaced by
    `OutputScript()` for display/indexing only);
  - `AdaptLegacy*`, and `MIN_VERSION`/`MAX_VERSION` (replaced by
    `IsValidVersion(v)`).
- **The invariant is enforced at construction.** The decoder dispatches on
  version, and the `CMutableTransaction` → `CTransaction` constructor throws
  `ios_base::failure` on mixing or on a v7 identity failure.
- **`CMutableTransaction` defaults to `nVersion = 2`**, the eCash behaviour.
  Its inputs and outputs start legacy, so upstream-shaped test code builds
  legacy transactions unchanged. A v7 transaction is built explicitly
  (`CMutableTransaction::V7()` or `FromV2Transaction`).
- **Coins hold a `CTxOut`**, whose variant agrees with the coin bit
  (§2.2).
- **Rejected:** two classes behind `CTransactionRef`
  (`std::variant<CTransactionLegacy, CTransactionV7>`). It would touch every
  `CBlock::vtx`, mempool entry, relay and index consumer for little gain over
  a tagged representation.
- **Rejected:** keeping today's union of fields. That is the hybrid this
  design removes.

### 2.9 Serialization and identities

**Wire format.** `UnserializeTransaction` reads `u32 version`:

| Version | Grammar |
|---|---|
| 1 or 2 | Legacy grammar `(vin[prevout, scriptSig, seq], vout[value, script], nLockTime)`, the eCash code |
| 7 | v7 grammar, unchanged |
| anything else | throw `bad-txns-version` |

- Delete the wrapped decode and encode (`transaction.h:449-462`, `598-610`),
  the "pure v2" heuristics (`466-473`) and the `ToV2Input` fallbacks inside
  the encoder (`487-575`).
- Prefer making the primitives v7 codec delegate to
  `lotus_v2/transaction.cpp`. The grammar is implemented twice today.

**Identity:**

- Legacy transactions: `SerializeHash` (SHA256d), with TxId = TxHash, exactly
  the eCash code.
- v7: `ComputeTransactionIdentities`, keeping the `InitHashes` fast path.
- Delete the `nVersion` XOR (`transaction.cpp:393-396`, and
  `validation.cpp:3636-3645`) and the flat fallback (`400-446`).
- `BlockMerkleRoot` uses each transaction's own TxId/TxHash. A legacy
  transaction supplies SHA256d for both.

**Legacy sighash.** `SignatureHash` and `PrecomputedTransactionData` stay,
used only for v1/v2 inputs. `FillPrecomputedData` now selects on
`nVersion != 7` instead of `nFlags` (`transaction.cpp:926-944`).

**Null transaction.** `NULL_TRANSACTION_WIRE` (`transaction.cpp:656`)
becomes legitimately "version 1, empty". It is unchanged.

### 2.10 Coinbase producers and genesis

**Coinbase producers.** `BlockAssembler::CreateNewBlock`
(`node/miner.cpp:215-291`), `mining_pool.cpp:472-537` and
`rpc/mining.cpp:1267-1317` build the coinbase version given by
`Options::coinbase_version` (§2.0). The format is chosen explicitly, not
inferred from the payout:

| Version | Coinbase built |
|---|---|
| 1 or 2 (regtest only) | Null prevout, `scriptSig = CScript() << nHeight << OP_0 [+ extra nonce]`, legacy outputs. Miner-fund, staking and treasury outputs are legacy scripts |
| 7 | Today's v7 coinbase, with explicit V2 outputs. The payout must be a V2 output; the miner fund uses `OutputForDestination` (explicit V2 encoding of the fund destination; Q6) |

The `scriptSig` → `vCoinbaseData` copy goes away; each format writes only its
own field.

The mining pool (`mining_pool.cpp`) always builds v7 coinbases, because a
pool is a mainnet feature.

**Genesis** (`chainparams.cpp:89-134`):

- **Coinbase:** remains v7. Its output is written explicitly as a V0-leaf V2
  output over the same P2PK bytes, which reproduces today's implicit result
  byte for byte. It is unspendable by design.
- **Easter-egg transaction:** becomes a plain **v1 legacy transaction**.
  - `nVersion = 1`, input `4a5e1e4b…a33b:0`.
  - `scriptSig = CScript() << "Satoshi's genesis coins, spent at last. Returned to sender."`.
  - Output: 50 XPI to Satoshi's P2PK script, `nLockTime = 0`.
  - It is a Bitcoin-format transaction spending Bitcoin's genesis coinbase,
    with a SHA256d TxId. Genesis transactions are still not validated or
    added to the coin set (`chainparams.cpp:96-98`).
- **Mainnet/testnet:** tx2's bytes change from the wrapped `0x80000007` form
  to version 1, and its TxId changes, so the merkle root and block hash
  change. Re-mine both. Today's nonces 7,612,265,698 and 166,335,650 imply
  about 2^32 attempts at `0x1d00ffff`. Then update:
  - `MAINNET_GENESIS_NONCE`/`TESTNET_GENESIS_NONCE`;
  - the asserts at `chainparams.cpp:271-276` and their testnet equivalents;
  - `lotus_v2_genesis_tests.cpp`.
  Record the mining command in the commit message, as v2/062 did.
- **Regtest:** coinbase-only, with an explicit V0-leaf output. It stays
  **byte-identical**, and so do the regtest fixture hashes.

### 2.11 Legacy-dependent code under Design A

| Subsystem | Disposition |
|---|---|
| Script interpreter | Unchanged eCash interpreter. Used by v1/v2 inputs (legacy checker) and P2SH bridge inputs (`LegacyBridgeSignatureChecker`). The `VerifyScript` call in `CScriptCheck` (`validation.cpp:3770`) is now selected by "legacy input or P2SH bridge", not by `nFlags==0` |
| `script/sign.cpp` | Legacy signing unchanged for v1/v2. New `BridgeSignatureCreator` (in `script/bridge_sign.{h,cpp}`) produces P2PKH bridge witnesses (BIP340 over the V2 message) and P2SH bridge witnesses (legacy `SignStep` with the V2 message and the hashtype map) |
| `CWallet` | Stays a legacy wallet: it receives via legacy coinbases and legacy txs and sends v1/v2. New RPC `migratetov2 "address_or_output" [amount]` sweeps chosen P2PKH/P2SH (multisig) coins into a v7 transaction that pays a V2 output, using `BridgeSignatureCreator`. Native V2 receiving stays with `lotus::v2::wallet` (Q7). Fee estimation adds dummy bridge witness sizes |
| Policy | Legacy `IsStandardTx` for v1/v2; V2 standardness for v7; bridge inputs standard; version selection by `nVersion` |
| RPC decoders (`core_write.cpp:240-300`) | Legacy JSON for v1/v2, unchanged. v7 JSON: `vin[].witnesses[{script, siblings, arguments}]` and `kind`; `vout[]` V2 fields. Bridge inputs add `"spends": "legacy-p2pkh"/"legacy-p2sh"`. `ConstructTransaction` builds legacy (`createrawtransaction` default version 2) unless `version=7` is passed, in which case outputs must be V2 destinations |
| `rpc/v2vm.cpp` | `DecodeV7` keeps rejecting non-v7. Simulation and test RPCs learn the bridge rules |
| `lotus-tx`, PSBT, BIP37 | Unchanged for legacy transactions. PSBT and BIP37 do not apply to v7 (they report "unsupported" for v7) |
| Chronik native (`chronik_bridge.cpp`) | `BridgeTxInputScript` (`103-122`): legacy inputs give `scriptSig`; v7 inputs give witness[0].script (bridge P2SH: the redeem script). `.version = tx.nVersion` (`183`) is now accurate. `lookup_spent_coins` (`447-466`) must not rebuild-and-hash a legacy-shaped transaction: for v1/v2 its SHA256d is correct; for v7 it must decode the raw v7 bytes or take the TxId from the caller (coordinate with C1 §1 item 2). Expose the coin's legacy bit in UTXO and spent-coin records (`is_legacy`) |
| Chronik Rust | The legacy `Tx` model fits v1/v2 unchanged. The V2 records (`lotus_v2.rs`) are unchanged for v7. Add `is_legacy` to the UTXO proto |
| Python framework | Legacy `CTransaction`/`CTxIn`/`CTxOut` unchanged in behaviour (§2.12). v7 types split out |

### 2.12 Test-framework impact under Design A

**Python** (`messages.py`):

- Split by version.
  - `CTransaction` (legacy: `nVersion` 1/2, legacy grammar, SHA256d id) is
    unchanged apart from deleting its wrapped-v7 branches (`523-538`,
    `597-610`).
  - New `CTransactionV7`/`CTxInV7`/`CTxOutV7` come from the existing v7
    branches (`455-522`, `540-596`), using `lotus_v2_compute_tx_identities`
    without the version argument.
  - `FromHex` dispatches on the first four bytes.
- New `test_framework/v7tx.py` promotes builders from
  `lotus_v2_native_e2e.py` and `lotus_v2_loopback_tps_stress.py`.
- New helpers:
  - `lotus_v2_signing_message(tx, spent_coins, i, w, mode)`, ported from
    `signing.cpp:459-529` and covering legacy coin wire and `legacy_leaf`;
  - `sign_bridge_p2pkh(key, …, mode)`;
  - `sign_bridge_p2sh(keys, redeem, …, hashtype)`.

**MiniWallet:** unchanged (legacy). Its coins come from legacy coinbases
because its address is a legacy P2SH-OP_TRUE (§2.10). `v7tx.MiniWalletV7`
covers native tests.

**C++:**

- `TestChain100Setup` (`setup_common.cpp:309-430`) is unchanged. Its P2PK
  `coinbaseKey` payout produces legacy coinbases, and
  `CreateValidMempoolTransaction` builds `nVersion=2` transactions by default.
- New `test/util/bridge_builder.{h,cpp}` provides bridge spends.

---

## 3. Inventory of legacy fields and legacy-version code in the V2 tier

`A:` gives the Design A disposition. The patch is named where it is
identifiable (§0).

### 3.1 Primitives (`src/primitives/transaction.{h,cpp}`)

| Location | What | Introduced | A: |
|---|---|---|---|
| `h:74-79` | `CTxIn` = `scriptSig` + V2 fields side by side (`nFlags` 0 = auto-infer) | upstream + v2/031 | variant (§2.8) |
| `h:126-128` | `CTxIn` legacy `SERIALIZE_METHODS` | upstream | keep for legacy body |
| `h:138-153` | Two-regime `CTxIn::operator==` | v2/031 | default `==` on variant |
| `h:165-178` | `CTxOut` = `scriptPubKey` + V2 fields | upstream + v2/031, `7bf1c1002e` | variant |
| `h:204-228` | Cross-representation `CTxOut::operator==` | v2/031 | default `==` |
| `h:449-462` | Wrapped and legacy decode, coinbase from `scriptSig` | v2/045 | delete wrapped; legacy decode by version |
| `h:466-473`, `598-610` | "Pure v2" heuristic, wrapped encode | v2/031, v2/045 | delete |
| `h:487-575` | Encoder fallbacks via `ToV2Input`, lock from `nLockTime` | v2/031 | delete |
| `h:715-725` | `nLockTime`+`fHasV2Lock`+`nV2Lock`; `MIN/MAX_VERSION = 1..7` | v2/031 | single `nLock`; `IsValidVersion` |
| `h:778-786` | `HasStructuralV2Identity` | `52bea1842b` | delete |
| `h:810-812` | `IsCoinBase` accepts null prevout or `nFlags==2` | v2/031 | per format |
| `h:1039-1042` | `AdaptLegacy*ToV7` | v2/031, v2/045 | delete |
| `cpp:28-120` | `ToV2Input`/`FromV2Input` with `scriptSig` inference | v2/031 | lossless copy of `V2TxIn` |
| `cpp:140-198` | `ToV2Output` implicit mapping (V0 leaf fallback) | `0a052c7a09` (eCash) adapted by v2/031 | V2 bodies only; legacy outputs never map (the state uses `LegacyStateOutput`) |
| `cpp:200-228` | `PopulateV2ScriptPubKeyWire` synthetic script (the 45-byte form embeds the value) | v2/031 | becomes `OutputScript()` for display only |
| `cpp:253-300` | `AdaptLegacy*` bodies | v2/045 | delete |
| `cpp:379-447` | Version XOR and flat fallback | v2/031, `52bea1842b` | delete |
| `cpp:449-479` | Id getters thread `nVersion` | v2/031 | dispatch by version |
| `cpp:481-608` | `InitHashes` v7 fast path; fallback | v2/031, `219ba2acd3` | keep fast path; legacy = SHA256d |
| `cpp:636-654`, `740-747` | Long-script accounting | upstream | per variant |
| `cpp:656`, `851-859` | Null tx wire (version 1) / null tx via the wrapped path | upstream/v2/031 | legacy null tx |
| `cpp:926-944` | `FillPrecomputedData` selects on `nFlags` | v2/031 | select on version |

### 3.2 Consensus (`src/consensus/`)

| Location | What | Introduced | A: |
|---|---|---|---|
| `tx_check.cpp:26-33` | Caps only for v7 | `52bea1842b` | all versions |
| `tx_check.cpp:35-52` | `bad-txns-legacy-state-output` | `16bc33fd75` | delete (unrepresentable) |
| `tx_check.cpp:100-107` | Coinbase HAS_STATE only for v7 | `7bf1c1002e` | keep (v7 only by type) |
| `tx_check.cpp:109-121` | Coinbase: `nFlags==2` vs legacy `scriptSig` length | v2/031 | dispatch by version |
| `tx_check.cpp:137-150` | Mint/spend same-prevout allowance, unreachable (the decoder rejects repeats, `h:365-381`) | v2/031 | simplify to "no repeated prevout" |
| `tx_check.cpp:182-200` | `bad-txns-v2-identity` | `52bea1842b` | delete |
| `tx_verify.cpp:20-38` | `IsFinalTx` on a truncated `nLockTime` with the 500M threshold | upstream | legacy: unchanged; v7: R6 |
| `tx_verify.cpp:58-63` | Versions 1/2/7 | v2/032 | decode-time (A1) |
| `tx_verify.cpp:114` | BIP68 only for `nVersion >= 2` | `b44e0d3870` | unchanged (v1 legacy keeps no-BIP68) |
| `tx_verify.cpp` `CheckTxInputs` | — | — | add A2 (legacy spends legacy) |

### 3.3 Validation (`src/validation.cpp`)

| Location | What | Introduced | A: |
|---|---|---|---|
| `195-201`, `569-573` | BIP68 shortcut for v7 spends (assumes FINAL; the decoder permits otherwise) | v2/032 | unchanged by T1; R5 |
| `340` | Post-check no-op for non-v7 | `c597186e10` | keep |
| `371-...` | Batched v7 fast path on 45-byte coin form | v2/032 | disable if any input is legacy |
| `1116-1128`, `1296-1305` | `is_v2_native_tx` picks standardness by `nFlags` | v2/032, `fe7ae5f9da` | select by version |
| `3577-3612` | OP_TRUE fast path reads the synthetic `scriptPubKey` | v2/032 | read `V2()` body |
| `3636-3645` | `nVersion` XOR in known ids | v2/032 | delete |
| `3770-3779` | `VerifyScript(scriptSig, scriptPubKey)` for `nFlags==0` | `fddb00fc8c` | legacy inputs + P2SH bridge |
| `3893` | No deferral for v7 | `c597186e10` | keep |
| `4334-4352` | BIP30 skip for v7 coinbases | v2/051 | keep; legacy coinbases do BIP30 |
| `7090-7111` | Coinbase height: `CheckCoinbaseContext` vs BIP34 | v2/032 | dispatch by version (A9) |
| `AddCoins`/`UpdateCoins`/`DisconnectBlock`, state-coin construction | — | — | set and restore the legacy bit; `LegacyStateOutput` for legacy coins |

### 3.4 Coinbase producers, monetary rules, coins, genesis

| Location | What | Introduced | A: |
|---|---|---|---|
| `coins.h:33-55`, `95-104` | `nHeightAndIsCoinBase` | upstream | add the legacy bit (§2.2) |
| `compressor.h:96-121` | Dual `TxOutCompression` | v2/031 | dispatch by variant; check against the bit |
| `lotus_v2/sparse_state.cpp:107-191` | Legacy coin 0x80 encoding | `f839f1a3b8` (eCash) | reuse as is |
| `lotus_v2/legacy_coin.h:8-23` | `LegacyStateOutput`/`LegacyTxOutput` | `f839f1a3b8` | used by ConnectBlock/undo |
| `kernel/chainparams.cpp:28-67` | Genesis builder writes `scriptSig`+`vCoinbaseData` | v2/032 | v7 coinbase writes `vCoinbaseData` only |
| `kernel/chainparams.cpp:89-134`, `266-277` | Placeholder genesis, nonces, asserts | v2/062 | §2.10 |
| `node/miner.cpp:215-291` | v7 coinbase with legacy payout script | v2/036, `4dc94d1036` | format follows payout |
| `node/mining_pool.cpp:472-537` | Same pattern | v2/056 | same |
| `rpc/mining.cpp:1267-1317` | Same pattern | v2/040 | same |
| `minerfund.cpp:71-87` | Consensus match via the implicit mapping | v2/032 | legacy match for legacy coinbases; explicit V2 encoding for v7 |
| `avalanche/treasury.cpp:241` | Treasury scripts | v2/043 | follow coinbase format |

### 3.5 Policy, interpreter, signing, wallet, RPC, utilities

| Location | What | Introduced | A: |
|---|---|---|---|
| `policy/policy.cpp:74-78` | Version standardness 1/2/7 | v2/032 | legacy path: 1/2 |
| `script/interpreter.cpp:1471`, `1629`, `1748`, `1794-1910` | Legacy sighash, BIP68 gate, `VerifyScript` | upstream | keep |
| `script/sign.cpp:110-487` | Legacy signing | upstream | keep; add the bridge creator |
| `wallet/wallet.cpp:2086-2126`, `spend.cpp:745/969/1078`, `transaction.cpp:11-15` | `CWallet` legacy signing; today it produces the wrapped shape (default `nVersion` 7) | upstream | produce v2 legacy; add `migratetov2` |
| `rpc/mempool.cpp:49-59`, `113-117`, `1460-1470`, `1776-1786` | Non-v7 refusal | v2/040 | delete |
| `rpc/v2vm.cpp:73-90` | `DecodeV7` | `b12a25312a` | keep |
| `core_write.cpp:240-300`; `core_read.cpp:196-214` | JSON; decode reason swallowed | upstream, `7bf1c1002e` | §2.11; return the reason |
| `rpc/rawtransaction.cpp:1331` etc. | PSBT `nVersion=2` | upstream | keep (legacy) |
| `bitcoin-tx.cpp:249-250` | `MIN/MAX_VERSION` | `e614433d1a` | `IsValidVersion` |
| `common/bloom.cpp:156-161` | `scriptSig` parsing | upstream | legacy only |

### 3.6 Chronik and the Python framework

| Location | What | Introduced | A: |
|---|---|---|---|
| `chronik-cpp/chronik_bridge.cpp:103-122`, `183`, `447-466` | Input-script projection, version, legacy-shaped TxId recompute | v2/035 | §2.11 |
| `chronik-bridge/src/ffi.rs:77,101`; `bitcoinsuite-core/src/tx/tx.rs` | Legacy `Tx` model | upstream | keep; add `is_legacy` |
| `messages.py:380-610`, `741`, `860-1006` | Hybrid Python transaction, implicit mapping, ids with version | upstream + v2/034 | split by version; delete wrapped/implicit |
| `wallet.py:62-447` | Legacy MiniWallet | upstream | keep |

---

## 4. Design A commit plan (V2 tier)

These commits land after the coordinator's next integration, on one rebased
tip, appended after the last V2 entry. Placeholders `T1-01…` become the next
series numbers. The eCash tier is not changed.

Every commit builds and passes the full `test_lotus` and functional suites;
commits that need fixture updates carry them. The file lists are the expected
touch set.

**T1-01 `test(v2): pin transaction identities, genesis and coin encodings before the bridge`**
- Files: `src/test/t1_baseline_tests.cpp` (new), `src/test/CMakeLists.txt`.
- Golden values:
  - TxId/TxHash for pure-v7 fixtures;
  - regtest genesis hash and merkle root;
  - legacy `CMutableTransaction` SHA256d (from eCash test vectors);
  - `EncodeCoin` bytes for a legacy coin;
  - the `Coin` serialization of a sample coin.
- Later commits update these goldens only where the plan says so.

**T1-02 `primitives(v2): version-tagged transactions without hybrid fields`**
- Files: `primitives/transaction.{h,cpp}`, `primitives/v2_outputs.h` (new:
  `V0LeafOutput`, `OpTrueOutput`, `DataOutput`, `OutputForDestination`),
  `compressor.h`, `core_memusage.h`; mechanical reader migration across `src/`
  (`.scriptSig` → `.Legacy().scriptSig`, `.vWitnesses` → `.V2().vWitnesses`,
  and so on).
- Semantics:
  - §2.8 layout; §2.9 decoder dispatch (A1); legacy SHA256d ids.
  - The XOR, flat fallback, wrapped form, `HasStructuralV2Identity`,
    `bad-txns-v2-identity` and `AdaptLegacy*` are deleted.
  - `CMutableTransaction` defaults to `nVersion=2`.
- Tests:
  - `transaction_tests`: replace `1595-1611` with decoder tests. Raw versions
    0/3/0x80000007/0xC0000007 give `bad-txns-version`; v1/v2 round-trip with
    SHA256d ids; a v7 empty-vin `CMutableTransaction` → `MakeTransactionRef`
    throws.
  - Delete `AdaptLegacy` tests (`lotus_v2_tests.cpp:1459-1495`); rebuild
    `mempool_overlay_tests.cpp:1292,1324` with `FromV2Transaction`.
  - Mixing legacy and V2 inputs in one transaction throws.
- Python `messages.py`: the legacy transaction id becomes SHA256d (drop the
  version XOR from `lotus_v2_compute_tx_identities`). It must land in this
  commit, otherwise `calc_merkle_root` of Python-built blocks disagrees with
  the node.
- Fixtures changed here: tests that relied on default `nVersion=7` plus a
  `scriptSig` now produce v2 legacy, and their expected ids switch to SHA256d.
  This must happen together with T1-03/T1-04 for coin direction. Until T1-04,
  the implicit V2 state mapping of legacy outputs is replaced by
  `LegacyStateOutput` right here, so that the state root stays well defined.

**T1-03 `coins(v2): record whether a coin was created by a legacy transaction`**
- Files: `coins.h`, `coins.cpp`, `undo.h`, `validation.cpp`
  (`AddCoins`/`UpdateCoins`/`DisconnectBlock`/state-coin construction),
  `txdb.cpp` (format version bump), `lotus_v2/disk_state.cpp` (consistency
  assertion), `kernel/coinstats.cpp` (hash includes the bit through `Coin`
  serialization).
- Semantics: §2.2; the coin bit must agree with the `CTxOut` variant on
  decode.
- Tests (`coins_tests`, new `coin_legacy_bit_tests.cpp`):
  - The bit round-trips through `Coin` serialization, undo, the
    `CCoinsViewDB` flush and reload, and `DisconnectBlock`.
  - VARINT sizes at heights 63/64, 4095/4096 and 2^19 match §2.2.
  - Height ≥ 2^30 asserts.
  - The state root of a block with legacy outputs equals the root computed
    from `EncodeCoin` 0x80 records.
  - A bit/representation mismatch fails to load.
  - fast-sync shards (`fast_sync_shard_tests`) carry legacy coins.

**T1-04 `consensus(v2): legacy transactions spend and create only legacy coins`**
- Files: `consensus/tx_verify.cpp` (A2 in `CheckTxInputs`),
  `consensus/tx_check.cpp` (caps for all versions; delete the legacy-state
  rule; coinbase dispatch), `validation.cpp` (A9 dispatch; standardness by
  version), `minerfund.cpp`, `avalanche/treasury.cpp`.
- Tests (`tx_verify_bridge_tests.cpp` new, `miner_tests`, `minerfund_tests`):
  - A v2 transaction spending a V2 coin → `bad-txns-legacy-spends-v2-coin`, in
    both mempool and block.
  - v1/v2 outputs carry the legacy bit.
  - v7 outputs do not carry it.
  - Legacy coinbase with BIP34 height accepted, wrong height →
    `bad-cb-height`.
  - Legacy coinbase BIP30 duplicate rejected.
  - Miner fund satisfied by legacy (legacy coinbase) and by V2 (v7 coinbase)
    outputs.
  - The 257-input legacy transaction is rejected.

This commit also adds `Consensus::Params::allowLegacyCoinbase`
(`consensus/params.h`, `kernel/chainparams.cpp`: regtest true, main/test
false). Its rule is `bad-cb-version` (§2.0a). Tests:
- A legacy coinbase on regtest is accepted, with its outputs legacy.
- The same block under mainnet params is rejected with `bad-cb-version`
  (`ChainTestingSetup` with main params and a mined test block, or a unit
  call to `ContextualCheckBlock`).
- A Python-built `create_coinbase` (v1) block is accepted on regtest
  (functional `feature_block`, `p2p_invalid_block`, unchanged).

**T1-05 `mining(v2): select the coinbase version for regtest block generation`**
- Files: `node/miner.{h,cpp}` (`Options::coinbase_version`; the
  `273-282` conversion only for 7), `node/mining_pool.cpp` (always 7),
  `rpc/mining.cpp` (`coinbase_version` argument on `generatetoaddress`,
  `generatetodescriptor`, `generateblock` and the `getblocktemplate` request
  key; default from the arg), `init.cpp`/`node/miner.cpp`
  (`-coinbaseversion`, regtest-only), `test/util/setup_common.cpp`
  (`TestChain100Setup` uses 2), `test/util/mining.cpp`,
  `test/functional/test_framework/test_node.py` (`-coinbaseversion=2`), and
  the three V2 functional tests (`-coinbaseversion=7`).
- Tests:
  - `miner_tests`: version 2 gives a legacy coinbase with legacy outputs and
    the legacy bit on its coins; version 7 gives a v7 coinbase with V2
    outputs.
  - `-coinbaseversion=2` on mainnet params fails init.
  - Functional `mining_basic` and `rpc_generateblock`:
    - each RPC with `coinbase_version` 2 and 7;
    - the default follows `-coinbaseversion`;
    - version 2 is refused with `RPC_INVALID_PARAMETER` when
      `allowLegacyCoinbase` is false (exercised by a unit test of the RPC
      helper with main params);
    - `getblocktemplate` `coinbasetxn` has the requested version.
  - `TestChain100Setup` chains run unchanged.

**T1-06 `consensus(v2): let v7 spend legacy P2PKH coins with a V2 signature`**
- Files: `lotus_v2/signing.{h,cpp}` (legacy coin wire, `legacy_leaf`
  selector, preparation with legacy resolved coins), `lotus_v2/commitment.{h,cpp}`
  (`LegacyBridgeLeaf`), `validation.cpp` (`CScriptCheck` A5/A6, fast-path
  exclusions), `lotus_v2/vm.{h,cpp}` cost constant, `script/bridge_sign.{h,cpp}`
  (new: P2PKH creator).
- Tests (`v2_legacy_bridge_tests.cpp`, new):
  - Valid in modes 0/1/2.
  - Wrong pubkey hash → `bad-txns-v2-legacy-p2pkh`.
  - Wrong key (valid hash, signature by another key) → signature failure.
  - Signature made for mode 0 but labelled mode 1, and vice versa → failure.
  - 65-byte signature with a trailing `0x03` → encoding failure.
  - Uncompressed key → `bad-txns-v2-legacy-coin-witness`.
  - Path index 1, two witnesses, non-empty script or siblings, three
    arguments → `bad-txns-v2-legacy-coin-witness`.
  - Signature replay onto a native V2 spend of the same key fails (selector
    differs).
  - A V2 signature over the same message verifies through the batch collector
    with the per-input bisection.
  - Cost accounting matches the constant.

**T1-07 `consensus(v2): let v7 spend legacy P2SH coins on the legacy interpreter`**
- Files: `validation.cpp` (A7: synthesized `scriptSig'`, `VerifyScript` with
  `LegacyBridgeSignatureChecker`), `script/bridge_checker.{h,cpp}` (new),
  `script/bridge_sign.{h,cpp}` (P2SH creator via `SignStep`).
- Tests (continuing `v2_legacy_bridge_tests.cpp`):
  - 2-of-3 multisig P2SH valid with `0x41`/`0xC1`/`0xC3`.
  - Hashtype `0x01` (no FORKID) and `0x42` (NONE) → `SIG_HASHTYPE`.
  - Wrong redeem hash → `bad-txns-v2-legacy-p2sh-hash`.
  - Wrong key → `EVAL_FALSE`/`NULLFAIL`.
  - A legacy-sighash signature (as a v1/v2 spend would make) rejected in v7.
  - Non-template coins (P2PK, bare multisig, OP_TRUE, P2SH-like with an extra
    opcode) → `bad-txns-v2-legacy-coin-template`.
  - **Same-result property:** for every non-signature case in
    `data/script_tests.json` that is a P2SH redeem script, and for a
    hash-puzzle/CLTV/CSV/CHECKDATASIG suite, the v2 legacy spend and the v7
    bridge spend give identical success/error codes.
  - Signature redeem scripts, each signed for its own path, both succeed.
  - `INPUT_SIGCHECKS` density applies to the synthesized `scriptSig'`.

**T1-08 `chain(v2): keep the genesis easter egg as a v1 legacy transaction`**
- Files: `kernel/chainparams.cpp` (§2.10; re-mined nonces and asserts),
  `src/test/lotus_v2_genesis_tests.cpp`, docs mentioning the genesis hash.
- Tests:
  - Genesis tests check the PoW, the v1 tx2 (SHA256d id, Bitcoin outpoint)
    and the explicit V0-leaf coinbase output.
  - The regtest hash is unchanged (T1-01 golden).

**T1-09 `policy(v2): relay and accept legacy and v7 transactions`**
- Files: `rpc/mempool.cpp` (delete the refusal), `core_read.{h,cpp}`
  (`DecodeHexTx` error), `rpc/rawtransaction.cpp` (decode messages),
  `policy/policy.cpp` (version standardness), `validation.cpp` (standardness
  by version; bridge inputs standard), `init.cpp` (nothing to unregister;
  confirm).
- Tests:
  - `txvalidation_tests`: v1/v2 accepted into the mempool; v3 decode-rejected.
  - Functional `mempool_accept`/`rpc_rawtransaction`/`rpc_packages`:
    `sendrawtransaction` and `testmempoolaccept` accept legacy; a raw version
    3 gives `TX decode failed: bad-txns-version`; a legacy parent plus a v7
    bridge child package is accepted; a v2 spend of a V2 coin gives
    `bad-txns-legacy-spends-v2-coin`.

**T1-10 `wallet(v2): sign legacy transactions explicitly and migrate legacy coins to V2`**
- Files: `wallet/spend.cpp` (`nVersion=2`), `wallet/rpcwallet.cpp`
  (`migratetov2`), `wallet/wallet.cpp`, `script/bridge_sign.*` integration,
  dummy-signer sizes.
- Tests:
  - `wallet_tests`: created transactions are v2.
  - Functional `wallet_migrate_v2.py` (new): P2PKH and 2-of-2 P2SH wallet
    coins swept to a V2 output; fee within the estimate.

**T1-11 `chronik(v2): index legacy and v7 transactions by their own identities`**
- Files: `chronik-cpp/chronik_bridge.cpp`, the `chronik-bridge` FFI, the
  `chronik-proto` UTXO `is_legacy`, `chronik-http/electrum.rs` (version from
  the transaction).
- Tests:
  - Functional `chronik_tx`/`chronik_script_utxos` (legacy, unchanged
    expectations; `is_legacy=true`).
  - New `chronik_v2_bridge.py`: the bridge spend is indexed with its spent
    legacy coin and `spends: legacy-p2pkh`.
  - `lookup_spent_coins` returns the correct ids for v1/v2/v7 broadcasts.

**T1-12 `test(v2): split Python transactions by version and add bridge signers`**
- Files: `test_framework/messages.py`, `test_framework/v7tx.py` (new),
  `test_framework/script.py` (`lotus_v2_signing_message`, `legacy_leaf`),
  `test_framework/blocktools.py` (legacy and v7 coinbases),
  `lotus_v2_native_e2e.py`, `lotus_v2_loopback_tps_stress.py` (import the
  promoted helpers).
- Tests:
  - Framework unit tests: Python `lotus_v2_signing_message` matches C++ over
    vectors emitted by `v2_legacy_bridge_tests`. The vectors are checked into
    `src/test/data/v2_legacy_bridge.json` and read by both.
  - Legacy `CTransaction` round-trip and SHA256d unchanged.

**T1-13 `test(v2): functional coverage of the legacy bridge and chained legacy transactions`**
- New `feature_v2_legacy_bridge.py`: a full migration.
  1. Mine legacy coinbases to P2PKH and to 2-of-3 P2SH.
  2. Build a 25-deep chain of v1/v2 legacy transactions from them (MiniWallet
     and `create_self_transfer_chain`, unchanged), relayed and mined.
  3. Spend the chain tips with v7 transactions in each mode (P2PKH bridge,
     P2SH bridge), creating V2 outputs.
  4. Spend those V2 outputs natively.
  5. Assert:
     - legacy-to-legacy and legacy-to-v7 valid;
     - v7-to-legacy impossible (a v2 spending a V2 coin is rejected);
     - a non-template legacy coin is unspendable by v7 but spendable by v2;
     - reorg across the bridge block restores legacy coins with their bit
       (`gettxout`, Chronik `is_legacy`);
     - restart (coin DB reload) preserves the bits;
     - `gettxoutsetinfo` hash stable across restart.
- Update tests that asserted the removed behaviour:
  - `feature_tx_version.py`: `OK_VERSIONS=[1,2,7]` stays; `BAD_VERSIONS`
    becomes decode failures; `0x80000007` moves to the bad list.
  - Any test asserting `bad-txns-non-v7-format`.
  - `rpc_getblockstats.json` only if legacy coinbases change sizes or ids
    (expected: regenerate once).

**T1-14 `lint(v2): forbid hybrid transaction fields`**
- `test/lint/lint-v2-tx-hybrid.py`:
  - no `nFlags == 0`;
  - no `AdaptLegacy`, `0x80000000U` wrapped-version or `HasStructuralV2Identity`
    tokens in `src/`;
  - no direct `.scriptSig`/`.scriptPubKey` access without `Legacy()`
    (`OutputScript()` is allowed).
- Doc updates: `doc/` and this design's status line.

Ordering notes:

- T1-02 is the large mechanical commit. Its reader migration is scripted and
  reviewable separately (`git show --stat` per directory).
- T1-03 and T1-04 could be merged if the intermediate state (bit recorded but
  not enforced) is not wanted.
- T1-06/T1-07 depend on T1-03.
- T1-08 depends on T1-02 (version-1 tx2).
- Chronik (T1-11) should be coordinated with C1 before it lands.

## 5. Risks (Design A)

- **R1 Consensus surface.** Two grammars, two id schemes and two signature
  regimes stay forever. Legacy `SignatureHash` and the interpreter remain
  consensus-critical for v1/v2 and for P2SH bridge inputs. Mitigation: no new
  legacy features, and the same-result tests in T1-07.
- **R2 Representation churn and performance.** Variant `CTxIn`/`CTxOut`
  change `sizeof` and the slab slot fit (`transaction.cpp:676-...`
  `STORAGE_SLOT_SIZES`). Benchmark `chained_tx`, mempool stress and
  `lotus_v2_loopback_tps_stress` before and after T1-02. Keep the `InitHashes`
  v7 fast path.
- **R3 Regtest-only legacy coins.** With `allowLegacyCoinbase` false on
  mainnet and testnet, the legacy paths and the bridge are consensus code that
  production networks never exercise. Their only coverage is the regtest
  suite, so keep T1-06, T1-07 and T1-13 in the default test run.
- **R4 P2SH bridge = legacy interpreter on v7 inputs.** Its DoS profile is the
  legacy one (sigchecks, opcount), charged to the V2 block cost through
  sigchecks only. That is acceptable because v1/v2 inputs have the same
  profile. Re-check if V2 block cost weights are tuned later.
- **R5 Pre-existing BIP68 shortcut** (found while reading, not caused by T1).
  - `validation.cpp:195-201` and `569-573` return empty lock points for v7
    spends, assuming FINAL sequences.
  - The decoder accepts relative-lock sequences, and `ConnectBlock`'s
    `SequenceLocks` (`3214`, `4612`) enforces BIP68 for version ≥ 2.
  - The mempool may therefore accept transactions that blocks reject. Report
    this as a separate fix. Bridge inputs must not widen it: T1-07 tests a CSV
    redeem script through the bridge in both mempool and block.
- **R6 Pre-existing lock semantics.**
  - `nLockTime = uint32_t(lock >> 8)` truncates the 56-bit V2 lock value.
  - `IsFinalTx` uses the 500M threshold rather than the V2 lock type.
  - The bridge `CheckLockTime` (§2.4) uses the type byte. V2-level finality is
    otherwise unchanged by T1 (Q8).
- **R7 Chronik and wallet ownership overlap** with C1 (Chronik) and P1/W1
  (wallet). Agree on ownership of `chronik_bridge.cpp:447-466` and `CWallet`
  before T1-10/T1-11.
- **R8 VARINT size bands.** One extra byte per coin at certain heights
  (§2.2). Negligible, but not zero as first stated.
- **R9 Pre-existing: testnet accepts a null `hashStateRoot`.**
  `validation.cpp:4850-4857` skips the state-root check when the root is null
  and `fPowAllowMinDifficultyBlocks` is set. That is regtest and, presumably,
  testnet. This is not caused by T1; report it separately.

## 6. Test matrix (Design A)

| Requirement | Where |
|---|---|
| P2PKH legacy coin spent by v7: valid / wrong hash / wrong key / wrong mode / non-template rejected | T1-06 unit tests; T1-13 functional |
| P2SH legacy coin spent by v7: valid / wrong hash / wrong key / wrong hashtype→mode / non-template rejected | T1-07 unit tests; T1-13 |
| The same coins spent by v1/v2, unchanged | T1-04, T1-07 (legacy control cases), T1-13 |
| The same P2SH redeem script gives the same result on both paths | T1-07 same-result suite |
| Coin bit round-trips through coin DB, undo, reorg, restart, state commitment, fast sync | T1-03 unit tests; T1-13 reorg/restart |
| Chained legacy transactions unchanged | `TestChain100Setup`-based unit tests after T1-02/05; T1-13 25-deep chain; existing MiniWallet functional tests |
| Mempool/RPC acceptance | T1-09 |
| Legacy coinbase gated by `allowLegacyCoinbase`; `coinbase_version` RPC args and `-coinbaseversion` default; Python `create_coinbase` (v1) blocks accepted on regtest | T1-04, T1-05 |
| Full legacy-to-v7 migration | T1-13 `feature_v2_legacy_bridge.py`; T1-10 `wallet_migrate_v2.py` |
| Python/C++ signing-message parity | T1-12 shared JSON vectors |

---

## 7. Open questions (Design A)

1. **Q1 (decided)** Legacy coinbases are regtest-only via
   `allowLegacyCoinbase`. Mainnet and testnet have no legacy coins, so the
   bridge is exercised only on regtest. Option (2) of §2.0, legacy spends of
   template V2 coins, remains a fallback that needs the user's approval.
2. **Q2 Bridge error names.** Confirm `bad-txns-legacy-spends-v2-coin`,
   `bad-txns-v2-legacy-coin-template`, `bad-txns-v2-legacy-coin-witness`,
   `bad-txns-v2-legacy-p2pkh` and `bad-txns-v2-legacy-p2sh-hash`.
3. **Q3 Uncompressed P2PKH keys through the bridge.** Rejected here; such
   coins remain spendable by v1/v2. Should they be accepted (x-only of the
   65-byte key)?
4. **Q4 P2SH bridge flags.** Pin `LEGACY_FLAGS` as a constant, or follow
   `GetBlockScriptFlags` at the spending height (this design)?
5. **Q5 Hashtype map.** Only `0x41`/`0xC1`/`0xC3` → modes 0/1/2. Should
   `NONE` or non-ACP `SINGLE` get V2 modes later?
6. **Q6 Miner-fund destination in v7 coinbases.** The explicit V2 encoding of
   a fund destination: which template (V2 key leaf from the destination's
   key, or xpi1)?
7. **Q7 `CWallet` scope.** Legacy wallet plus `migratetov2` (this design), or
   native V2 receiving in `CWallet` as well?
8. **Q8 V2 lock finality** (R6): fix it separately, or within T1?
9. **Q9 HASH160 opcode.** A later EXT2 opcode for V2 scripts that check
   legacy addresses: in scope for O1's opcode registry?
10. **Q10 V2 MiniWallet.** The coordinator referred to a "V2 MiniWallet
    (patch v2/034)". None exists in `test_framework/` at `056a85acb0`. T1-12
    builds `MiniWalletV7` from the per-test helpers unless a newer one exists.

---

## 8. Verified vs assumed (summary)

- **Verified:** every `file:line` in §2.1–§3.6, the coin layout, the legacy
  state-coin encoding, the V2 signature encoding and modes, the eCash SHA256d
  id, the genesis tx2 wrapped serialization, and the absence of a V2
  MiniWallet class.
- **Verified in §2.0:** the coinbase blocker audit (tx root, state root,
  BIP34/BIP30, miner fund, treasury, HAS_STATE), Python `create_coinbase`
  being v1/BIP34, and null state roots being accepted on regtest.
- **Assumed:** see §0. The main ones:
  - the script flags applied to v1/v2 inputs today;
  - the pass status of functional tests outside `v2/034`;
  - the xpi1 representation of legacy destinations;
  - the test counts, which come from `git grep` heuristics.

---

## 9. Design B — v7-only + leaf versions (alternative, full specification)

Kept so the comparison in §1.3 can be checked.

**B1 Rule.**
- Only raw version 7 decodes, so v1/v2 and wrapped forms do not.
  `bad-txns-version` is the decode reason.
- `-allowlegacytx`, `bad-txns-non-v7-format`, `bad-txns-v2-identity` and
  `bad-txns-legacy-state-output` are deleted.
- The legacy `VerifyScript` path, BIP34 coinbase and BIP30 loop are deleted.
- `CTransaction` construction throws on a non-encodable transaction. There is
  no fallback id.

**B2 Leaf hashing.**
- `LeafHash(0, s) = TaggedHash(branch, 0x00 || CompactSize || s)`: today's
  bytes.
- `LeafHash(v≥1, s) = TaggedHash(branch, 0x02 || v || CompactSize || s)`.
- Node prefix `0x01` is unchanged.
- LEAFHASH opcode `0xbe` stays V0.

**B3 Reveal.**
- `BranchWitness.leaf_version` is a byte before `script` in every spend
  witness. Mints are V0 and not encoded.
- TxIds are unchanged, TxHashes change.
- The alternative is input `flags=4` "versioned spend".

**B4 Dispatch:**

| Version | Behaviour |
|---|---|
| V0 | V2 VM |
| V1 | `EvalLegacyLeaf` |
| V2–255 | Success after membership; policy-nonstandard |

Fast paths require V0. Effects only from V0.

**B5 V1 execution:**
- **Initial stack:** the arguments; no P2SH layer.
- **Limits:**
  - script ≤ min(10,000, `max_script_bytes`);
  - each argument ≤ 520.
- **Flags:** `STRICTENC|DERSIG|LOW_S|NULLFAIL|MINIMALDATA|MINIMALIF|CLTV|CSV|FORKID|SCHNORR_MULTISIG|ENFORCE_SIGCHECKS`.
- **Clean stack:** checked by the caller.
- **OP_CODESEPARATOR:** fails.
- **Checker:** the legacy sig encoding plus a hashtype map (`0x41/0xC1/0xC3` →
  modes 0/1/2) over `SigningMessage`. The selector leaf commits to the
  version.
- **Cost:**
  - script bytes × structural cost;
  - a per-opcode base cost;
  - sigchecks × CHECKSIG cost;
  - per-byte hash costs.

**B6 Implicit mapping.** `ToV2Output` inference is deleted. Explicit
constructors replace it:
- `LegacyLeafOutput` (V1), `OpTrueOutput`, `V0LeafOutput`, `DataOutput`,
  `OutputForDestination` (→ V1 leaf).
- The miner fund compares against `OutputForDestination`.

**B7 Types.**
- V2-only `CTxIn`/`CTxOut`/`CTransaction` (static `nVersion = 7`, single
  `nLock`, no `scriptSig`/`scriptPubKey`, `OutputScript()` derived).
- A test-only `CTransactionLegacy` in `src/test/util`, used only for upstream
  interpreter vectors and never converted.

**B8 Wallet.**
- `LegacyLeafSignatureCreator`; IsMine by branch root (`LeafHash(1, script)`).
- PSBT, `lotus-tx` and BIP37 are removed or ported.

**B9 Genesis.**
- Mainnet/testnet: the coinbase output and tx2 become V1-leaf P2PK. Tx2's
  witness reveals the P2PK script with the message as its argument.
- Re-mine.
- Regtest stays byte-identical via an explicit V0 leaf.

**B10 Tests.**
- About 50 C++ files and about 170 functional tests are ported to a
  `V7TxBuilder` and a v7 MiniWallet (OP_TRUE V0, V1 P2PK, BIP340).
- Interpreter vectors move to `CTransactionLegacy`.
- Legacy-format vectors (`tx_valid`/`tx_invalid`/`sighash.json`) are deleted
  from the V2 tier.
- Legacy-only functional tests are dropped: `feature_tx_version`,
  `abc-replay-protection`, `abc-segwit-recovery`,
  `abc-mempool-coherence-on-activations`.
- Functional test counts from a `git grep` heuristic at `056a85acb0`: 98 build
  transactions directly, 31 use only MiniWallet, 43 use only wallet RPCs.

**B11 Commit sketch.**
1. Pin goldens.
2. Leaf versions.
3. V1 evaluator.
4. Explicit outputs.
5. Genesis.
6. C++ builder and migration.
7. `CTransactionLegacy` for interpreter vectors.
8. Python v7 framework.
9. Functional migration (4 batches).
10. Wallet V1 leaves.
11. RPC decoders.
12. Chronik.
13. v7-only enforcement.
14. Type cleanup.
15. Lint.

**B12 Risks and open questions specific to B.**
- Wire churn for every spend's TxHash.
- The legacy-opcode cost table must be benchmarked (DoS).
- IsMine misses multi-branch outputs.
- The leaf-hash preimage form, reveal encoding and CODESEPARATOR policy need
  decisions.
- Mint leaf versions.
- A versioned LEAFHASH opcode.
