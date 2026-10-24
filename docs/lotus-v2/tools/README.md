# Candidate structural checks

This small model checks the proposed byte framing, identity/signing inputs, tree/proof construction, header views and selected integer algorithms. It is **not** the planned reference parser/VM, a mined chain, a signature verifier, a full conformance suite or an independent consensus implementation. Assertions operate on locally constructed fixtures, not untrusted network inputs.

Run from the repository root in a disposable virtual environment:

```sh
python3 -m venv /path/to/spec-check-venv
/path/to/spec-check-venv/bin/python -m pip install -r docs/lotus-v2/tools/requirements.txt
/path/to/spec-check-venv/bin/python docs/lotus-v2/tools/spec_candidate_checks.py
```

The default command checks the saved [fixtures](../examples/candidate-smoke-vectors.json) and packet/source digests. `--write` explicitly regenerates them after reviewing a candidate change; it must not be used automatically to make a failing independent implementation pass. Run without Python optimization (`-O`) because assertions are the checks.

Coverage: all 41 currently unassigned success bytes (`215` assigned / `41` `OP_SUCCESS_N`) and instruction-boundary scanning (including skipped arms, ignored suffixes, push payloads and malformed push prefixes); 16/45/107/108-byte framing example; Merkleized 112-byte `TxID` / `TxHash` preimages over `IndexedTreeRoot` (`InputsRoot`, `FullInputsRoot`, `OutputsRoot`) and `CoinsRoot`; mint-input token ID framing; exact full-message (138B) and partial-mode (`OwnInputHash`/`OutputsRoot`/`OutputLeaf`, 150B) sighash input framing with 41-byte `SpendSelector`; `MERKLEROOT_SORTED` and `MERKLEROOT_INDEXED` root reconstruction across `hash_alg in 0..3` (and $O(\log N)$ parent-transaction input/output proof verification); 153 ordered-tree inclusion paths; compact single-leaf-collapsed sparse-tree insertion-order agreement, membership (`presence=1`) and nonmembership (`presence=0` empty branch and `presence=2` prefix-collision leaf) proof encoding/reconstruction; canonical 56-byte `MonetaryState` and 130-byte `StateRoot` commitment; recursive-header 134/82/64-byte pure tagged BLAKE3 disclosures; fixed-point LOG at all positive representable powers of two and an integer monotonic sample; telescoping bootstrap reserve conservation ($\sum B_n = R_0$), candidate genesis scale (`1 XPI = 10^6 atoms`, $B_0 = T_0 = 250{,}000\text{ XPI}$, $R_0 = 2^{20} B_0$), additive subsidy $S_n = B_n + T_n$, and tail floor arithmetic; parabolic transaction cost $C_{\text{tx}}$, rolling `ema_block_cost` $E_n$, and parabolic block fee-burn floor; ASERT drift/clamping and compact-target cases. Fixture chain identity and parameter examples are not production constants.

All hashes are generated with the pinned BLAKE3 Python binding. A second implementation must independently verify them before they qualify as accepted conformance vectors. The OP_ONE transaction is a hash/framing fixture and asserts no signed-payment or block-validation result. The header fixture contains arbitrary state/size data and is not a valid block.

The success scanner is a structural model only. It does not validate outer witness limits or membership, execute ordinary scripts, or establish branch/accounting/budget correctness. Independent end-to-end cases remain required by the validation contract.

The opcode allocation is maintained in [opcodes.json](opcodes.json). The checker cross-checks every documented instruction name/byte, all 41 success bytes, and named inline byte annotations. The reorganized allocation changes OP_ONE and therefore its branch/token/transaction/hash fixtures; old draft bytecode is not compatible. The registry digest is recorded with the generator and packet digests.

October 14 regression fixtures additionally check 1,000-atoms/kB byte-fee boundaries, reward-funded coinbase/envelope charges (including no ordinary transactions), odd fees/token burns, exact/one-atom-over claims and insufficient entitlement, distinct enforcement costs with identical accounting EMA/state roots, and genesis initialization followed by height-1/height-2 reserve steps. These are arithmetic/commitment checks, not executed VM, complete block/undo or Avalanche integration tests.

Coinbase identity fixtures construct P01's optional opaque `CoinbaseData` field and check its canonical count/length boundaries, including 8192-byte acceptance and empty, multiple, oversized, non-shortest and truncated rejection. They retain the full field in both identity projections, compare parent/height/data mutations and identical sibling templates, and check parent/derived-height context and u32 overflow. Opcode-looking bytes are treated as data without invoking the script scanner. These checks model constructed inputs and supplied context; they do not parse complete transactions or validate blocks.
