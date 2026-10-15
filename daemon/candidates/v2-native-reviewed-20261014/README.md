# Reviewed V2 native primitives — October 14, 2026

This 32-mailbox development series applies to Bitcoin ABC
`1fb7db17c176cdea8a2c60d887891589382ee4e3`. The source is
`/tmp/lotus-v2-native-slice-review`, commit `33563a734`, final tree
`f3fd01ed1d52e21a48dd746e4c1a5a3bb9d2fb5f`. The manifest records every
intermediate tree, mailbox digest, and source author/date. Patches 000–014 retain
the earlier worker packet's bytes. Six later mailboxes have explicitly labelled
review explanations added to their messages; their source diffs are unchanged.

These are isolated libraries and tests. Applying the series does not make the
daemon accept V2 transactions or blocks. Production workspaces and releases are
untouched.

## Included work

- 000–008: previously reviewed development foundations, custom miner scheduler,
  header primitives and output framing.
- 009–014: branch/indexed/ordered commitments, scalar sparse UTXO reference,
  868-byte Coin bound, transaction/coinbase framing, identities and signing.
- 015–017: review corrections for maximum-count proof arithmetic, the witness
  argument ceiling, and prepared signing commitments.
- 018–019: incremental in-memory UTXO tree and safe ownership during leaf collapse.
- 020–025: bounded native VM, differential runner, invocation context, static
  accounting, composed invocation cap, signing reuse and stack operations.

The incremental tree updates affected paths and caches hashes. It retains the
scalar tree as an oracle. It has no on-disk durability, chainstate wiring, or block
undo machinery. Reinsert-after-delete tests establish root restoration in memory.

The VM implements a subset of assigned P03 instructions and fails explicitly for
unsupported execution. P05 coefficients and limits are supplied explicitly; test
prices are illustrative. Signing commitments and mint count are prepared once
per invocation, then reused by its instructions. Sharing that preparation across
all transaction invocations remains an integration task. Resolved coins and mint
deltas still require validation by the outer transaction/state layer.

## Ordinary transaction and expanded VM slice

Patches 026–027 add byte/string and checked numeric/logical operations, an opcode
inventory, and independent arithmetic vectors. The inventory accounts for all
215 assigned bytes: 94 pushes, 12 control operations, 77 other implemented
operations and 32 unsupported operations that reject when executed. Root ran
900 independent byte vectors, 2,117 independent arithmetic vectors, 363
Python/native execution comparisons and 494 static-cost comparisons.

Patch 028 adds a standalone ordinary-transaction validator over an explicit
in-memory UTXO view. It resolves spends once, checks duplicate outpoints,
locks/maturity, checked native/token sums, exact positive mint coverage and
both fee floors, and executes every selected witness. Application stages effects
and changes the view only after success. Tests include signed compiler mint and
transfer transactions, altered resolved Coins, missing/extra/failing branches,
inflation, underfees, duplicate spends and mint-context coin access. Both workers'
Debug/Release tests and root's fresh combined Release VM/validator tests pass.

This validator excludes transaction-wide P05 resource derivation, block burn,
coinbase, ordering, persistent state and network integration. It does not turn
these modules into a full V2 daemon. Prepared signing is still repeated across
invocations; that performance issue remains an integration obligation.

Reproduce the additional native check by configuring `src/lotus_v2/ordinary_test`
with the same CMake compiler/OpenSSL/secp256k1 settings used below. The scripts
`vm_test/differential_bytes.py` and `differential_numeric.py` take the native runner
path; `check_opcode_coverage.py` takes the spec opcode JSON and runner paths.

## Review and validation

Root review reproduced the uint32 maximum-count proof failure before fixing it,
then reran header, commitment and scalar sparse checks in Debug and Release.
Worker audit found the argument-limit bypass and repeated whole-transaction
signing work; both have separate fixes and Debug/Release tests. Root reran the
Release transaction/output and signing tests.

The incremental tree passes deterministic scalar comparisons for 96 insertions,
reverse deletion/reinsertion, reverse insertion order, and 240 mixed updates,
including membership/absence proofs and sibling order. The worker ran AddressSanitizer
and Release; root reran Release on the combined source after the ownership fix.

The VM passes worker Debug/Release checks and a fresh root Release build with
warnings treated as errors. Root independently ran 298 Python/native execution
comparisons and 477 static-charge comparisons against the updated Python reference.
The spec now explicitly applies the invocation cap after composing the charge;
checked-u128 intermediate overflow still rejects, even inside a zero-count loop.
Skipped BREAK is an ordinary unexecuted instruction, subject to structural decoding.

The root-built compiler fixture harness also executes the signed Payment example
and all five token-gallery invocations: two for mint and three for transfer.
It rejects an unauthorized issuer signature, a newly signed transfer that removes
the mandatory rules path, and a mint script reading a nonexistent coin. These are
invocation checks, not complete transaction/block verdicts.

Existing six miner tests passed on the integrated 000–014 source. Later patches
add isolated modules and tests, not daemon mining behavior. Whole upstream suites,
Chronik, live V2 networking and a mined/accepted V2 block remain unverified.

## Reproduce the focused checks

Apply `series` in order with `git am --keep-non-patch` in an isolated checkout of
the exact base. Compare every resulting tree and mailbox SHA-256 with
`manifest.json`. Source commit IDs may differ after mailbox replay; trees must match.

```sh
cmake --build BUILD --target check-lotus-v2-header check-lotus-v2-commitment \
  check-lotus-v2-sparse-state check-lotus-v2-incremental-utxo
cmake -S src/lotus_v2/output_test -B OUTPUT_BUILD -DCMAKE_BUILD_TYPE=Release
cmake --build OUTPUT_BUILD
ctest --test-dir OUTPUT_BUILD --output-on-failure
cmake -S src/lotus_v2/signing_test -B SIGNING_BUILD \
  -DLOTUS_SECP_LIBRARY=/absolute/path/to/libsecp256k1.a
cmake --build SIGNING_BUILD
ctest --test-dir SIGNING_BUILD --output-on-failure
cmake -S src/lotus_v2/vm_test -B VM_BUILD -DCMAKE_BUILD_TYPE=Release \
  -DLOTUS_SECP_LIBRARY=/absolute/path/to/libsecp256k1.a
cmake --build VM_BUILD
ctest --test-dir VM_BUILD --output-on-failure
python src/lotus_v2/vm_test/differential.py MONOREPO/tools/lotus-v2-reference VM_BUILD/lotus_v2_vm_runner
python src/lotus_v2/vm_test/differential_cost.py MONOREPO/tools/lotus-v2-reference VM_BUILD/lotus_v2_vm_runner
```

The VM build requires OpenSSL Crypto. The Python interpreter needs the reference
package's `requirements-vm.txt`; it is an independent test dependency, not a daemon
runtime dependency. Compiler/native fixture commands are in the compiler README.

## Root review and integration of 029–030 (October 14, 2026)

Two candidates were reviewed against the spec, replayed, rebuilt independently,
and appended without changing any mailbox byte. The original packets are kept in
[`../v2-monetary-20261014/`](../v2-monetary-20261014/README.md) and
[`../v2-vm-context-proofs-20261014/`](../v2-vm-context-proofs-20261014/PROVENANCE.md).
Applying all 31 mailboxes to ABC `1fb7db17` gives final tree
`c3925f143830827a7289bf6dead09811983fbaa6`, and 028 still lands on
`f3fd01ed`. Patch 029 alone lands on the candidate tree `88e74840`. Patch 030
on 028 lands on `c71e4259`. On 029 it lands on `c3925f14`, which is exactly
the union of the two reviewed trees, because their files do not overlap.

**029 monetary arithmetic (P05/P06/C16).**
- *Formula check:* each formula matches the spec. This includes coinbase
  `overhead_bytes = 134 + 4 + Σ prefix` from `resources-and-parameters.md`,
  the half-fee split rounded up, the telescoping bootstrap, the clamped tail
  `isqrt(T²·W/W_prev)` bounded by U384, and the EMA. The
  spendable-supply-delta identity was checked algebraically.
- *Boost dependency:* ABC already uses Boost headers (`src/CMakeLists.txt`),
  and `depends/packages/boost.mk` (1.81) stages the full header tree.
  `boost/multiprecision/cpp_int.hpp` is header-only, so this adds no new
  library. For now only the standalone harness locates Boost. Daemon
  integration must link the existing Boost headers target.
- *Root tests:* Debug with ASan and UBSan, plus Release, pass CTest and the
  packet's 300-vector differential. Root also ran an extra differential
  ([`root_differential.py`](../v2-monetary-20261014/root_differential.py), seed `0x5EED2026`) of 20,000 vectors
  biased toward accepted cases, including 64-bit reserve and work values:
  19,396 accepted, 604 rejected, 0 mismatches, in both configurations.
- *Harness weaknesses (not consensus):* the packet differential compares only
  `ERR` for 274 of 300 vectors, without checking the rejection reason. Also,
  `--vectors` reads negative `enforce` values into `uint64_t`.
- Rule failures are reported by throwing `std::invalid_argument`, so block
  integration must catch them and map them to validation state.

**030 VM context introspection and Merkle proofs.**
- *Semantics checked against the P03 table:* c0/c1 framing, ordering and the
  four algorithms; c8 = 7 (fixed transaction version); cc/cd/ce/cf; d2–d5;
  d8–dc; e3–e7; e9 exclusive branch (both conditions); ea continuation
  (spend-only, exact paths and branches with `k` replaced); f0; and the
  f3/f4 lock checks, including mint rejection for CSV. The prose at
  `vm-semantics.md` lines 253 and 290 calls OUTPUTCONTINUESBRANCH `cf`. The
  table and both engines use `ea`; `cf` is CHAINID. This is a spec typo and
  was left unedited, to avoid changing the pinned P03 digest.
- *Merkle P05 cost:* steps are `min(cap, floor(bound(proof)/32))`, with a cap
  of 64 for sorted and 256 for indexed proofs. The proof bound comes from the
  correct pop position (the second pop) for both opcodes. Tagged nodes are
  charged as 96-byte BLAKE3 preimages. Actual sizes are branch 16+1+64 = 81
  bytes and merkleidx 19+1+2+64 = 86 bytes, so this is a safe upper bound.
  Root probes confirmed a literal selector 0 costs 129 per step and selectors
  1–3 cost 97 (uniform test schedule). A non-constant selector is charged the
  maximum of all four step costs (129). The spec says
  `max(C_blake3, C_hash256)`, which here would be 97 and would under-charge
  algorithm 0. The implementation is the safer choice, so the spec text should
  be amended before the freeze. The Python reference `vm_cost.py` has no Merkle
  step charge, and `differential_cost.py` produces no c0/c1 scripts, so Merkle
  charges have no independent cost oracle yet.
- *Authenticated field-size bounds:* the hints in `VmCostProfile.field_sizes`
  (db/dc/e6/e7) are supplied by the caller. They are only checked to be
  `≤ max_element_bytes`. Nothing checks them against the transaction, or checks
  at runtime that a pushed field fits its bound, so an integrator passing
  smaller-than-actual hints would under-charge. The ordinary validator
  currently passes no hints and falls back to MAX_ELEMENT_BYTES, which is
  safe. Path reads (db/e6) ignore a constant index and charge the maximum.
  That over-charges compared with the P05 table and is a cost divergence to
  resolve. Before wiring hints into validation, derive them from
  `VmExecutionContext` or reject hints smaller than the actual field.
- *Root tests (Debug with ASan and UBSan, plus Release):* CTest passes, and all
  differentials agree in both configurations: 363 core cases, 900 byte vectors,
  2,117 arithmetic vectors, 494 P05 charges and 684 Merkle vectors. Coverage is
  94 push, 12 control, 103 implemented and 6 unsupported opcodes (b0–b4, bd).

**Combined Release run on `c3925f14`:** the vm, ordinary, monetary, signing and
output CTests all pass. The compiler native token checker verifies the signed
mint, transfer and the new two-input merge fixture, including all VM
rejections. These are still module results. No V2 block is parsed, connected
or accepted, and monetary state is not persisted or undone.

**031 root follow-up: authenticated field-size hints.** Root authored this
patch in response to the 030 finding. When a cost profile and an execution
context are both present, a non-empty hint is rejected before charging if it
is smaller than the authenticated field. Complete-output hints need one entry
per output (e7) or per input (dc), each covering its encoded output or
resolved coin. Path hints (db/e6) must cover the widest path. Empty hints
still fall back to MAX_ELEMENT_BYTES, and context-free charging is unchanged.
New tests cover exact, wider, absent, short and mis-sized hints. A mutation
that disables the check makes them fail. On tree
`04b5d3c167ead1b0a1d8187821f72333ac6bded9`, Debug (ASan/UBSan) and Release
VM core tests pass. The Release differentials (363/494/684/900/2,117), the
ordinary-validator CTest and the native token mint/transfer/merge fixtures
also pass. Exact replay of all 32 mailboxes from ABC `1fb7db17` reproduces
this tree. Still open: path reads ignore a constant index (an over-charge),
the Merkle cost model has no Python reference, and the spec's
`max(C_blake3, C_hash256)` text needs a decision.
