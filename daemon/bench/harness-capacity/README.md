# Load-generator and RPC-concurrency attribution

Run from the canonical repository root. These tools reuse the registered `daemon/worktrees/grok-progression-source` checkout and frozen transaction/ingestion helpers. They create no additional source checkout. A host lock prevents simultaneous owned builds/benchmarks. Every fresh workload validates responses, distinct inventory and a measurement window of at least five seconds.

- `run.py`: compare generator processes at fixed concurrency; supports shared or native binaries through `--series` and `--build-receipt`.
- `sweep.py`: compare blocking/shared async-only binaries by RPC worker count, or use `--client-counts` to fix 16 server workers and vary balanced client concurrency. This preset is **shared ABC/eCash**, not V2.
- `--profile` on the sweep collects diagnostic node stacks and excludes their throughput from its summary.
- `analyze_profiles.py`: classify the 16 RPC executor threads in the diagnostic profiles. Its percentages include blocked/idle stacks, not CPU-time percentages.
- `pack_evidence.py`: archive raw evidence compactly and verify every member hash.

The native fixture-only acceleration is the existing frozen adapter. Install the pinned package into an isolated canonical directory, then pass that directory with `--fixture-hash-site`. Its compatibility checks run before preparation. Node validation is unchanged.

```sh
python3 -m pip install --only-binary=:all: --no-deps --target daemon/.local-artifact-archive/fixture-hash-site blake3==1.0.8
```

Use a clean source checkout and frozen build receipt matching the desired source; build/gate it before timing. Exact commands, flags, source trees, binary hashes, fixture hashes and historical tool versions for completed measurements are in `daemon/patch-intake/20261023/harness-capacity/evidence.tar.gz`. Reproducing an old measurement requires its recorded tool versions rather than silently substituting the newest wrapper.

See `daemon/patch-intake/20261023/harness-capacity/REPORT.md`, `SCOPE.json` and `TABLE.md`. Echo calibration measures payload transport only; do not label it validated TPS. Admission is also separate from all-peer propagation, block confirmation and finality.
