# Generic owned canonical arena: native validation passed

Exact source `a429917c018437d38f684c2a6bb5b839a0437157`, tree `4aca247a67d57f55f785b72d43b3ff4515619dce`, on canonical base `2cf83331`. No canonical pin or maintained series has been promoted by this gate.

Fresh isolated arm64 Ninja build uses native Chronik ON, MDBX ON, plugins OFF, wallet ON, jemalloc ON and Release `-O3` with assertions. All four normal targets linked: `lotusd`, `test_bitcoin`, `test_lotus_v2_block_assembler`, `test-avalanche`. Version check passed. Build concurrency was `-j10`. The existing measured Chronik-OFF cache and source were untouched.

| Executed check | Cases | Assertions | Result |
|---|---:|---:|---|
| mempool_overlay_tests | 19 | 40,040 | PASS |
| rpc_snapshot_read_tests | 5 | 1,090 | PASS |
| lotus_v2_tests | 8 | 137,117 | PASS |
| preconsensus_batch_tests | 12 | 2,960 | PASS |
| standalone block assembler integration | standalone | — | PASS |

Total: 44 Boost cases, 181,207 assertions, plus standalone block assembler. Its logged injected builder exceptions are expected test scenarios. The existing `lotus_v2_tests` selector includes small kernel microbenchmark cases; their printed throughput is not an endpoint benchmark or a causal speedup claim.

The first fresh build exposed a real Apple libc++ portability issue: `atomic<shared_ptr<T>>` is unsupported here. Production now uses the standard free atomic shared_ptr operations, acquire/release, matching existing daemon practice. Subsequent compile failures were two new test name qualifications. One runtime fixture incorrectly compared distinct CTransactionRef pointer identities; it now checks that the pinned leaf owns readable transaction bytes equal to the fixture after clear. Failed attempts and their original logs are preserved in numbered attempt directories. The final build is incremental after those repairs; its short duration must not be represented as the fresh build duration.

`RESULT.json` preserves executed commands, times and exit codes; `VALIDATION-RECEIPT.json` seals log hashes and counts. The compiler/runtime lease was explicitly drained and released after success. No additional benchmark, profile or node runtime was started.

This validates generic owned topology/hash-cache/body lifetimes and publication plumbing. It does not implement epoch reconciliation lifecycle, prove network convergence, establish an integrated retained-memory budget, or replace the mutable primary mempool with a CoW primary. See the adjacent primary-CoW source audit for the remaining architecture gap. Independent Astra source review approved ring ownership, paired generation and nonwaiting worker dispatch; the narrow portable atomic spelling was independently reviewed at exact a429/tree4aca and closed with no source blocker.
