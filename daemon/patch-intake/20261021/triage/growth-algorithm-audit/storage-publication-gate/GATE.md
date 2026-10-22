# Generic owned canonical arena / publication gate

Source is prepared on latest `2cf83331`, independently of the unresolved epoch-cut design. Exact source/tree and targets are in SOURCE.json. No protocol lifecycle glue, new capability advertisement or old full-mempool wire experiment is included. No native build/test has run.

## Queue order and actual commands

N1 exclusively owns compilers and runtime scheduling. Its cross-peer Avalanche cohort has the next actual slot. This packet is held for Astra's actual CODE review; architectural approval alone does not release it. Use the existing native Chronik-ON configuration. Do not configure Rust Chronik or silently disable Chronik to avoid a build dependency. Compilation target names were read from source CMake, not inferred from historical V1 naming.

Once source review is released, the minimal normal link gate is:

```sh
cmake --build <BUILD> --target lotusd test_bitcoin test_lotus_v2_block_assembler -j10
<BUILD>/src/test/test_bitcoin --run_test=mempool_overlay_tests --report_level=detailed
<BUILD>/src/test/test_bitcoin --run_test=rpc_snapshot_read_tests --report_level=detailed
<BUILD>/src/test/test_bitcoin --run_test=lotus_v2_tests --report_level=detailed
<BUILD>/src/lotus_v2/test_lotus_v2_block_assembler
```

The exact binary paths must be confirmed against N1's existing build directory. Existing standalone header/commitment tests do not exercise the replacement arena, so they are not substitutes for linking test_bitcoin and the development-runtime block assembler.

After this gate, `test-avalanche --run_test=preconsensus_batch_tests` verifies that cumulative frozen overlay/finality behavior remains unchanged. Relevant existing sealed-header overlay tests may be run from v2_protocol_handler_tests; no new epoch-cut semantics are asserted.

## Prepared evidence

The arena suite independently compares roots against canonical BuildTxSubtreeA, retained old generations, a 255-bit common prefix, replacement/deletion/re-add, zero-allocation identity no-op, cold batch mutation without old-root hashing, changed-path hash-work counts, six concurrent cold readers, lifetime after reset, and worker exception/drain/reentrancy. Publication tests cover owned root/body lifetime across bulk clear, matched numeric-root generation and metadata-only sequence stability. Existing deferred overlay/mining tests ensure a relay pin does not flush UTXO/CTOR bookkeeping.

A source self-review fixed pending numeric deltas being cleared before later snapshot/template allocation could fail. Another source review found only unnecessary temporary vector allocation, now removed. These are source assessments, not executed test results.

## Claims still held

There is no performance, bounded-total-RSS or runtime correctness claim. Root exposure estimates and actual structural-node counts require native measurements. The historical snapshot publisher retains 1024 generations: adding canonical handles there may retain large old roots outside relay reservations during repeated clears/refills; Astra has been asked to review this actual lifetime concern before gate release. No default reservation/time values are frozen here.

The AB|D + learned C/new E => ABC|DE candidate ownership/vote reset behavior remains an independently revised specification task. Generic immutable roots are useful across cut variants; this packet does not implement that lifecycle or claim network convergence.
