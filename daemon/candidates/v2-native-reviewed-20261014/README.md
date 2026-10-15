# Reviewed V2 native primitives — October 14, 2026

This 26-mailbox development series applies to Bitcoin ABC
`1fb7db17c176cdea8a2c60d887891589382ee4e3`. The source is
`/tmp/lotus-v2-native-slice-review`, commit `67cb95ce6`, final tree
`b0c32ae8ded2cdfa520bd91cf579d991c8dfa004`. The manifest records every
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
