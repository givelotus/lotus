# Reviewed plan: consolidate repairs and advance native processing

Status: reviewed and ready for bounded execution. PLAN-v1.md and REVIEW.md retain the original proposal and the corrections. User authorized autonomous execution on 2026-10-23.

## Outcomes and constraints

- One complete review purpose per resulting change: implementation plus its correctness/performance repairs, required tests, documentation and build wiring.
- Reduce patch/reviewer load without deleting work, hiding behavior changes or compressing a large subsystem into an unreviewable diff.
- Preserve all exact inputs, old refs and complete reachable source history in verified recovery storage before rewriting. Record base/head/tree hashes and separately preserve dirty parent work. Do not remove the source checkout or old refs.
- Use real Git commits in the one registered `daemon/worktrees/grok-progression-source` checkout. No additional worktree/clone, no archival mailbox edits, no changes to main/master/tags or permanent base-only submodule pins.
- Pure reorder/split/squash must preserve **both** final shared and native tracked trees exactly. Necessary context adapters get exact ownership/diff records. New behavior fixes are a separate, tested phase, never concealed as a tree-preserving move.

## 1. Freeze and account

INPUTS.json freezes shared d38c3820 (378 commits), native a3679647 (153 more) and native coroutine candidate 4d77f464. INVENTORY.json accounts for all 531 original source owners and their changed files. REPAIR-CANDIDATES.json records the 19 initial candidates and their unresolved mapping questions.

Create named immutable backup refs and a verified recovery bundle for these exact histories before execution. Preserve the parent repository's pre-existing dirty files without committing or overwriting them. Retain existing source bundles, candidate branches and historical benchmark receipts. Record artifact hashes and backup/push status.

Treat unmerged work explicitly:

- **Coroutine:** user requested retaining it. Preserve its tested native endpoint and derive/validate the matching shared implementation and native adapter as a separately identified integration, then freeze that new endpoint before further pure moves.
- **Atomic scalar readers/fee diagnostics:** preserve the existing candidate and its gates; integrate only with an explicit source/ownership decision and native consumer validation.
- **Queue-only capability restoration and fixture repairs:** inspect the unrelated peer-capability changes in old owner 377. Split/account for concerns. Any restoration that changes behavior needs its own reviewed diff and gates.
- **Shared coin views for eCash/snapblock:** preserve the inspected MDBX-plus-CoW-overlay follow-up; it is not already implemented by native coroutine wiring.

## 2. Complete the owner audit

Review every non-conversion commit, not just the first 19. Review the late logging tranche for prerequisites mixed with conversions. Use diffs, original source provenance, blame and actual callers/build registration—not titles or common filenames alone.

Give every source/test/build/config/doc hunk one disposition:

1. Fold into the earlier feature that introduced the defect, regression or incomplete wiring.
2. Split across actual owners, retaining all content.
3. Keep as an independent upstream correction or a distinct reviewable enhancement, with a reason.
4. Keep as a buildable implementation step of a larger feature where one huge diff would make review harder.
5. Preserve migration/benchmark-only evidence in the canonical task records; exclude it from a particular upstream PR without silently deleting it from the canonical source history.

Record confidence, dependency closure, exact old/new owner hashes, adapters and validation. An unresolved row stays retained; it is not dropped to meet a count. Report verified reductions per cohort and the remaining unresolved inventory.

## 3. Execute bounded history cohorts

Start on a new candidate branch rooted at the frozen native baseline, with a corresponding shared-boundary ref. Keep review inputs untouched. Use deterministic normal Git cherry-pick/rebase sequences; any rebase uses a noninteractive editor and disables updateRefs for preservation refs. The first cohort rebuilds the tail from original owner 85, amending only the newly copied owner at HEAD.

### Cohort A: HTTP response ownership

- Fold all four files of shared 98 (`221e907464`) into Beast owner 86 (`72bb32d88f`). It is one same-purpose body-ownership repair; existing lvalue callers remain valid.
- Rebase from original owner 85. Keep every other source owner and its content.
- At the old repair-98 position, require the new tree to equal original 98 exactly. Record every rewritten commit mapping.
- At original shared 378 require tree `2c6b9bc763382dd3236952d5c8c66efe77f10241`; at the full native endpoint require `a576cd04fc505e68069809d0bc00ec8ed96b4955`.
- Build/test the corrected Beast owner at its new position; run relevant HTTP tests and large plain/TLS/chunked keep-alive checks. Investigate a failure against original owner 86 before attributing it to the fold.

### Following cohorts, each reviewed before execution

- TLS/WebSocket correctness and matching tests: 101/102/111/113/116/124/126, with exact earliest-owner mapping and independent inherited repairs kept distinct.
- HTTP I/O regression repair 99: generic Beast changes plus explicit Chronik/WS consumer context adapters. Do not move future-only code into the earlier owner.
- Build/source registration, feature lint and test discovery: 38/49/87/162/163. Split by real source owner; no broad late build-fix commit.
- Queue completion and native Chronik capability/router work: 193/225/229, respecting actual consumers and the corrected API-vs-production-fix distinction.
- Snapshot/deferred-overlay/admission/reconciliation follow-ups discovered by the complete audit. Fold incomplete integration; retain distinct algorithms only when separately reviewable and justified.
- Logging: consolidate the complete runtime foundation and necessary encoders before consumers. Keep bulk call-site conversion last; separate formatting/runtime prerequisites from conversion scaffolding. Preserve every event, redaction and lifetime rule.

After each cohort: verify stable checkpoint and endpoint trees, check the owner ledger for omissions, run relevant correctness gates, export/preserve the candidate and record the verified commit-count reduction. Stop promotion on any unexplained tree difference. Resolve conflicts by explicit ownership; never restore an entire late file just to make a conflict disappear.

## 4. Arrange upstream submissions

Keep a small upstream-first prefix: currency/count/hash/other independent fixes, followed by the complete infrastructure dependencies needed for larger changes. Logging foundation belongs before its consumers. Asynchronous HTTP precedes Beast; coroutine integration follows its minimum **complete** admission/queue prerequisites. Allocator changes, slabs, ownership/CoW, batch preparation, mining and reconciliation follow dependency closure and increasing scope. Do not force a cosmetically simple order through placeholder APIs.

Prepare separate prerequisite-aware PR branches for independent optimizations, transports, metrics/logging, database/storage, Chronik and wallet/experimental protocol features. A PR description explains one concrete problem/result and relevant validation. Every commit in a submitted PR must build and pass its relevant tests. Tests/docs/build wiring accompany the introducing change. Preserve original authorship/provenance and the historical-to-new benchmark numbering map.

## 5. Validation policy

- Clean linear replay/graph verification for all resulting source commits.
- Incremental build and relevant tests at every materially changed logical owner; reuse evidence for unchanged trees only with exact identity and explicit status.
- Full shared and native endpoint gates. Native coroutine candidate's existing 1,209-case result applies only to its recorded tree; the baseline native endpoint has its separate evidence.
- Native/Rust Chronik, wallet and optional transports: validate affected configurations before promoting/submitting those feature groups. Record unrun Linux/x86_64/Guix/platform checks honestly; local arm64 success does not establish them.
- Benchmark with multiple generator processes, fixed workloads/configuration, sufficient distinct fixtures and at least three alternating samples where comparative performance is claimed. No builds, profiling or heavy archives during timing. Keep profiled runs out of throughput tables.
- Preserve ongoing behavioral tests. Do not add assertions merely proving a one-time textual conversion happened; do not weaken failing gates to complete the move.

## 6. Performance path: 100K immediate, 1M longer-term

After the first safe consolidation cohort and its gates, alternate bounded consolidation work with actual native performance investigation so history cleanup does not become an indefinite prerequisite.

1. Preserve the current native baseline: signed batch-200 admission about 36.8K TPS; echo transport about 1.63M transaction-sized items/s, which is **not validation**. Separate the shared legacy RPC studies from native results.
2. Profile native batch validation/admission and measure lock wait/hold, CPU, allocations/retirement, VM preparation and root construction. Check growth at increasing UTXO/mempool/transaction counts. Do not select a fix from the shared legacy profile alone.
3. Repair one evidenced bottleneck at a time on a separate functional candidate. Use immutable inputs and bounded persistent workers where useful; keep authoritative state/conflict/policy checks. Require correctness gates and a matched benchmark before adoption. Investigate repeated global scans and growth worse than n log n.
4. Verify generator headroom for each workload. Prefer the dedicated batch path for high-rate injection; measure individual RPCs as a separate interface. Extend fixture duration through explicit bounded disk/memory budgets rather than counting duplicates or shortening the timer.
5. Establish sustained validated admission at 100K TPS on the recorded consumer hardware, then separately demonstrate peer convergence and actual block processing with exact transaction/block inventories. Test representative keys, scripts, sizes and dependencies, not only the easiest fixture. Label cached/uncached validation and all disabled options.
6. No signature/consensus bypass, OP_TRUE substitution, changed fee rules, weakened limits or disabled assertions may be hidden as an optimization. Avalanche finality requires its own enabled/quorum tests; disabled-Avalanche admission cannot establish it.
7. Progress toward 1M from measured bottlenecks and scaling evidence. Report real results, remaining limits and reproducible source/binary/config identities; do not promise an unmeasured rate.

## Deliverables

Reviewed plan and updates; complete disposition/ownership ledger; preserved input refs/history/dirty work; two-tier source candidates and exports; checkpoint/tree proofs; per-owner/endpoint/platform test receipts; concise benchmark tables and historical mappings; small upstream-ready branches; one current START-HERE entry and append-only recovery checkpoints. No source or result may exist only in an external dirty checkout.
