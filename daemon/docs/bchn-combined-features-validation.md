# Combined BCHN feature validation

The exact BCHN base `abd433abe04f74780744b9eac06731f3690ce68a` plus patches
01 (ready-transaction priority), 04 (optional mempool consistency traversal),
10 (existing FlatBuffers NNG services), 11 (default ZeroMQ disable), then
12 (ZeroMQ source removal) builds and runs together on macOS arm64.

Combined source commit: `4c522d3682dc0f64a1327dfd8d517d722a917d26`.
Combined source tree: `1c5fdb7c8018adbb386a099676fb4b8b80bab5e3`.
[Machine-readable evidence](bchn-combined-features-evidence.json) records ordered
patch hashes, configuration, checks and persisted logs. This is separate from
standalone patch validation and from the broader application-order matrix.

The native daemon, CLI and test binary build with NNG ON after actual ZeroMQ
source deletion. Executable help, linked libraries and undefined symbols show
NNG present and ZeroMQ absent. No extra mining/mempool/consensus changes were made.

Both real compatibility suites pass: the unmodified public Rust consumer exercises
evolved pub/sub and RPC, and the original Tobias fixture exercises legacy RPC.
They cover templates and real solved-block submission, bootstrap, storage/undo,
spent coins, CashTokens, conflicts, reorgs, startup failures and orderly restart.
An additional test adapter adds a +123,456 sat selection-only fee delta and runs the
same existing suite: the template still reports its actual 1,000 sat transaction
fee and the reconstructed, solved block is accepted. This detects fee deltas leaking
into accounting without changing the implementation or its consumer.

The complete `miner_tests` and `mempool_tests` suites pass: 16 cases and 66,034
assertions, including ready-sibling priority under a constrained template, validity
and template-entry accounting, and the long-chain consistency check. The other
639 cases were deliberately not rerun. This establishes focused composition behavior,
not a complete platform/consensus certification or a performance measurement.

All builds and nodes use new isolated `/tmp/lotus-bchn-combined-*` paths. Existing
standalone NNG builds and production nodes/data/releases remain untouched.

To reproduce, replay the recorded five mailbox files in order, configure with the
recorded flags, and build `bitcoind bitcoin-cli test_bitcoin`. Run
`src/test/test_bitcoin --run_test=miner_tests,mempool_tests --report_level=detailed`
from the isolated source directory. Run both `interface_nng_compat.py` and
`interface_nng_legacy_rpc.py` with the new build's `test/config.ini`; explicitly
supply the existing consumer probe to the evolved test. The additional adapter
is included with evidence and uses `PYTHONPATH=<source>/test/functional` with the
same config and probe. Optional Python requirements and probe build instructions
remain in [the NNG compatibility documentation](bchn-nng-flatbuffers.md).
