# Harness capacity, RPC concurrency and native snapshot wiring

Exact source, binary and workload identities are in SCOPE.json. The worker-count A/B tests and lock profiles used shared ABC/eCash with legacy transactions. The native batch and native coroutine checks used Lotus V2. Their results must not be mixed.

## What was established

- **Generator limitation:** with the same node and 12 connections, four generator processes increased isolated `getmempoolinfo` throughput from 14,202 to 44,405 RPC/s, and `getblockchaininfo` from 14,046 to 43,164 RPC/s. These are medians of three alternating pairs. Exploratory admission comparisons also improved; JSON arrays did not. There is no universal correction factor for older benchmarks.
- **Coroutine tradeoff:** the shared-tier sweeps completed 36 RPC-worker samples and 24 client-concurrency samples, with three pairs per setting. At 64 clients and 16 RPC workers, `co_await` increased mixed read throughput by 42.3% and decreased individual admission throughput by 21.8%. At 128 clients the changes were +73.1% and −26.5%. TABLE.md contains every setting.
- **Wait attribution:** in one matched 64-client diagnostic pair, 57% of blocking RPC-worker samples were in future condition waits and 27% in admission-preparation locks. With `co_await`, future waits disappeared, workers were 46% idle and preparation-lock waits remained at 33%. Mempool-info ownership-lock waits accounted for 0.02%/0.06%. These are wall-stack sample shares, not CPU percentages or an exact attribution of the throughput difference. They do not describe native V2's different preparation path.

All measured windows lasted at least five seconds. RPC errors, exhausted fixtures, excessive start skew and incorrect exact source mempool inventory fail the run. Threads, connections, transaction construction and signing are warmed or completed outside the timer. Three nodes and the load generators share one host.

## Native V2 injection headroom

The existing native binary at `3cfb7031` has tree `a576cd04`, identical to review `a3679647`. Three signed batch-of-200 runs admitted **35,782 / 36,788 / 38,769 tx/s**, using 800,000 distinct presigned transactions per trial. These measure acceptance, not all-peer propagation, block confirmation or finality.

Three separate `echo` probes using the same transaction-sized payloads achieved **1,627,624 / 1,639,442 / 1,588,624 items/s**. Echo does no transaction validation. This is transport headroom, never accepted TPS. The client used about 0.52 CPU seconds per five-second admission run.

An initial slow fixture-preparation attempt was stopped before timing. A subsequent echo probe hit its ten-argument limit; wrapping the payloads in one array fixed the request. Neither failed attempt supplied a published TPS sample. Final native fixtures use pinned `blake3==1.0.8` for preparation, checked against 13 frozen-byte compatibility vectors and retaining the existing large-input fallback. Node validation is unchanged. Backend hashes are recorded. Interrupted generated runtime data remains in the canonical local artifact archive.

## Native coroutine candidate

The shared coroutine/owned-completion change was ported onto native review `a3679647`, retaining native transaction-ID results. Its new `SubmitRpcAdmission` entry passes the expected mempool pointer to the existing native snapshot-preparation API. The regression test holds `cs_main` on another thread: eligible native preparation finishes while authoritative commit correctly waits.

**All 1,209 native C++ tests pass.** A real 64-client HTTP integration run accepted 57,219 transactions in 5.0025 seconds, checked exact inventory and exited cleanly. That is one integration sample, not a comparative native speedup. Wallet, Rust Chronik, HTTP/2, WebTransport and jemalloc builds remain outside this profile.

Source review branch: `perf/native-async-rpc-20261023` in `givelotus/lotusd`. NATIVE-OWNERSHIP.json records exact compiled/final identities, every source owner, verified recovery bundles and endpoint tree equality. Development fixups were consolidated into two logical owner fixups, with the RPC result assertion kept in the feature that introduces the test. The existing 531-commit history and active source pins were not changed. Shared-tier replay and promotion remain separate work; this candidate is not claimed integrated into the active stack.

## eCash and snapblock follow-up

SHARED-COIN-VIEW-PORT.md records the inspected port: a pinned MDBX generation plus a persistent CoW dirty-coin overlay, coherent with the chain anchor and mempool view. It covers flush/reorg behavior, reader lifetime, reclamation and real consumer tests. **That shared UTXO view is not implemented by this coroutine candidate.** Native commitment and signature rules stay in the V2 adapter.

## Reproduction and preservation

Readable tools are in `daemon/bench/harness-capacity/`. The verified compressed evidence archive preserves raw inputs/results, source/binary/config/tool hashes, generated scripts, process CPU counters, diagnostic stacks and historical tool versions. TOOL-VERSIONS.json verifies the executed tool versions for successful comparisons. Source exports and recovery bundles are canonical. No extra source worktree or clone was created; all owned processes stopped.
