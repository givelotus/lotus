# Candidate structural checks

This small model checks the proposed byte framing, identity/signing inputs, tree/proof construction, header views and selected integer algorithms. It is **not** the planned reference parser/VM, a mined chain, a signature verifier, a full conformance suite or an independent consensus implementation. Assertions operate on locally constructed fixtures, not untrusted network inputs.

Run from the repository root in a disposable virtual environment:

```sh
python3 -m venv /path/to/spec-check-venv
/path/to/spec-check-venv/bin/python -m pip install -r docs/lotus-v2/tools/requirements.txt
/path/to/spec-check-venv/bin/python docs/lotus-v2/tools/spec_candidate_checks.py
```

The default command checks the saved [fixtures](../examples/candidate-smoke-vectors.json) and packet/source digests. `--write` explicitly regenerates them after reviewing a candidate change; it must not be used automatically to make a failing independent implementation pass. Run without Python optimization (`-O`) because assertions are the checks.

Coverage: 22/45/113/118-byte framing example; exact full-message input framing; 153 ordered-tree inclusion paths; sparse-tree insertion-order agreement, membership and nonmembership proof encoding/reconstruction; recursive-header 144/92/64-byte disclosures; fixed-point LOG at all positive representable powers of two and an integer monotonic sample; tail floor arithmetic; ASERT drift/clamping and compact-target cases. Fixture chain identity and parameter examples are not production constants.

All hashes are generated with the pinned BLAKE3 Python binding. A second implementation must independently verify them before they qualify as accepted conformance vectors. The OP_ONE transaction is a hash/framing fixture and asserts no signed-payment or block-validation result. The header fixture contains arbitrary state/size data and is not a valid block.
