# Candidate structural checks

This small model checks the proposed byte framing, identity/signing inputs, tree/proof construction, header views and selected integer algorithms. It is **not** the planned reference parser/VM, a mined chain, a signature verifier, a full conformance suite or an independent consensus implementation. Assertions operate on locally constructed fixtures, not untrusted network inputs.

Run from the repository root in a disposable virtual environment:

```sh
python3 -m venv /path/to/spec-check-venv
/path/to/spec-check-venv/bin/python -m pip install -r docs/lotus-v2/tools/requirements.txt
/path/to/spec-check-venv/bin/python docs/lotus-v2/tools/spec_candidate_checks.py
```

The default command checks the saved [fixtures](../examples/candidate-smoke-vectors.json) and packet/source digests. `--write` explicitly regenerates them after reviewing a candidate change; it must not be used automatically to make a failing independent implementation pass. Run without Python optimization (`-O`) because assertions are the checks.

Coverage: all 41 currently unassigned success bytes (`215` assigned / `41` `OP_SUCCESS_N`) and instruction-boundary scanning (including skipped arms, ignored suffixes, push payloads and malformed push prefixes); 16/45/107/108-byte framing example; Merkleized 112-byte `TxID` / `TxHash` preimages over `IndexedTreeRoot` (`InputsRoot`, `FullInputsRoot`, `OutputsRoot`) and `CoinsRoot`; mint-input token ID framing; exact full-message (138B) and partial-mode (`OwnInputHash`/`OutputsRoot`/`OutputLeaf`, 150B) sighash input framing with 41-byte `SpendSelector`; `MERKLEROOT_SORTED` (`0xee`) and `MERKLEROOT_INDEXED` (`0xef`) root reconstruction across `hash_alg in 0..3` (and $O(\log N)$ parent-transaction input/output proof verification); 153 ordered-tree inclusion paths; compact single-leaf-collapsed sparse-tree insertion-order agreement, membership (`presence=1`) and nonmembership (`presence=0` empty branch and `presence=2` prefix-collision leaf) proof encoding/reconstruction; recursive-header 134/82/64-byte disclosures; fixed-point LOG at all positive representable powers of two and an integer monotonic sample; tail floor arithmetic; ASERT drift/clamping and compact-target cases. Fixture chain identity and parameter examples are not production constants.

All hashes are generated with the pinned BLAKE3 Python binding. A second implementation must independently verify them before they qualify as accepted conformance vectors. The OP_ONE transaction is a hash/framing fixture and asserts no signed-payment or block-validation result. The header fixture contains arbitrary state/size data and is not a valid block.

The success scanner is a structural model only. It does not validate outer witness limits or membership, execute ordinary scripts, or establish branch/accounting/budget correctness. Independent end-to-end cases remain required by the validation contract.
