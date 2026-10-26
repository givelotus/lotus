# Transaction commitment partition-allocation candidate

Source commit `f418debf52` on exact canonical `9f04419037a5527b498188c3a81f1cac259cc9c5`, tree `7583f771a117564eb92ed2f4627f3ad8eacd4087`.

This changes only recursive partition storage: one owned pointer array is partitioned in place and split into disjoint spans. It keeps canonical bit routing, leaf/node hashes, absolute depths, duplicate-check sorting and both public root APIs. It also keeps the original std::async launch condition (depth <4, size >=64, both children nonempty); this is **not** the rejected persistent-executor candidate.

Concurrency/lifetime: the asynchronous left branch captures its span descriptor by value. Left and right mutate distinct pointer slots; neither mutates the caller's identity objects. The pointer vector is owned by the enclosing public call. A right-branch exception destroys/joins the left future before unwinding to that owner, so no child can outlive the pointer array. Public calls sharing the same const identities have independent pointer arrays.

Production change is confined to `src/lotus_v2/commitment.cpp`. Prepared checks in the existing mempool overlay suite compare against its independent canonical arena at 0,1,2,63,64,65,255,256,1000 identities, uniform and long-common-prefix keys, plus a final-bit split. They cover input preservation, order independence, both public root APIs, duplicate failure behavior and overlapping public calls. Existing standalone commitment vectors remain untouched and need no new arena dependency.

Source whitespace check passed. **No compiler, native test or benchmark was run** while the protected profiling lane was active. This candidate has no measured performance claim. Next gate is the coordinator's source/lifetime review, then one matched fixed-large kernel A/B after runner drain/N1 authorization, alongside the focused existing oracle checks. Source object ownership and exact diff digest are in delivery.json; candidate.diff is an inspection artifact, not a maintained mailbox promotion.

Source preflight also qualified the test Hash type and checks caller input after overlapping calls. No compiler was run for that correction.

## Actual isolated gate after protected runner drain

N1 explicitly granted the serial compiler/runtime lease. All three small compiles and all executed checks passed; full drain/release was sent afterward. Both baseline9f044190 and candidatef418 passed21 independent canonical-root cohorts and672 overlapping root calls, duplicate rejection and valid reuse. The existing standalone commitment vector source compiled and passed on the candidate. The new permanent Boost test has **not yet** been built through the normal native target.

One fixed500,000-identity pair (at least3seconds per side) measured74.90964429ms/root before versus67.47366389ms/root after, about9.93% lower latency. Actual root matched `9ded22b18413318615cb68883d8b0137df2b447856c790a6beb72a366fbee5f9`. Before completed41 roots in3.07129542s; after45 in3.03631487s. Both used the same BLAKE3 static library, compiler flags, existing async strategy and system allocator. This is one kernel mechanism comparison on the current host, not daemon TPS or a universal speedup. No broad matrix or repeated tuning run was performed.

Executed commands, timings/load averages and raw outputs are preserved in isolated-result.json and named stdout/stderr logs; hashes include the produced local binaries. The binaries remain untracked local artifacts. Native Boost-case closure is the next bounded gate, coordinated with N1. No canonical pin/series promotion has occurred.

## Actual normal native closure

N1 built the normal daemon/core/commitment targets in17actions at `-j10` (6.47s), then ran the new span-partition oracle175 assertions, existing arena/block-root9 assertions, duplicate rejection4 assertions and standalone commitment vectors. All passed and the compiler/runtime slot was explicitly drained. Exact source/tree remains f418debf/14e035af. Normal receipts and preserved binary hashes are under `exports/transaction-partition-span-native-validated/`; that cache is Chronik OFF, so this is not a Chronik-ON claim for this distinct candidate. No further daemon throughput run was requested or performed.

Blame/source history proves the complete original walker, required public helpers and arena/test fixture arrive in original owner10 `c4d405c3f6e27b0dc83d81c46d6ef05a67fb6b8d`. This is a new independent optimization inserted immediately afterward, preserving the original owner's identity and metadata. The pure adapter changes only the two source files, adds missing standard includes where needed at earlier prefixes, is idempotent, and reproduces the exact tested endpoint. Earlier prefixes remain untouched. All-prefix source proof is separate from the actual endpoint native gate; it is not an all-prefix build claim.
