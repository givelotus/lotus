# Daemon stack reconciliation

Status: proposed 2026-11-01, owner decisions recorded at the end. Nothing here has
been executed.

Goal: every `ecashd` and Lotus V2 commit lives on one named branch, the tooling
and agent docs point at those branches, nothing is lost or duplicated, each
change is audited, and the `ecashd` tier is ready to measure and send to Bitcoin ABC.

## End state

| Repository | Branch | Holds | How it moves |
|---|---|---|---|
| `givelotus/bitcoin-abc` | `ecashd` (new, default) | ABC base + shared stack + bridge | Fast-forward only |
| `givelotus/bitcoin-abc` | `master` | Exact mirror of `Bitcoin-ABC/bitcoin-abc` `master` | Fast-forward only, after one reset |
| `givelotus/bitcoin-abc` | `upstream/<topic>` | One clean extract per ABC submission | Disposable |
| `givelotus/lotusd` | `main` | `ecashd` tip + V2 stack + bridge | Fast-forward only |
| `givelotus/lotusd` | `lotusv1` | V1 maintenance | Unchanged |
| `givelotus/lotusd` | `snowstorm/*` | Draft PRs for the Snowstorm project | Rebased as needed |

Every other 2026 `perf/*`, `consolidation/*` and `archive/perf-review*` branch is
deleted once the ledger accounts for it (phase 3). The all-refs bundles stay in
`~/repos/archive/branches/`.

### How `-s ours` bridges work here

Both `ecashd` and V2 are linear stacks that get rewritten, and each publishes as a
bridge on top: `git merge -s ours <previous published tip>`, with the tree unchanged.

- **What this gives us:** published branches only fast-forward, every old pin stays
  reachable, and no one needs to force-push or re-clone after a stack is rewritten.
- **What it doesn't:** conflict work in a rebase or backport is the same as before.
  It only makes publishing the result cheap and safe.
- **Rebases:** always start from the linear stack (`tip^1`), never the bridge.
- **Layering:** `tip^1` is the stack head, `tip^2` is the previous published tip, and
  V2 sits on `ecashd`'s published tip.

## What was found (2026-11-01)

Verified by fetching and comparing refs:

- **`bitcoin-abc`:** `master` (`73ed9c43`) has the same tree as the pin
  (`d38c3820`) plus a bridge over older published ABC history. It has no PRs.
- **`lotusd`:** `main` (`ef42f1ea`) and the pin (`a3679647`) differ by 529
  commits each way. Their trees differ only by the 6-line HTTP repair in
  `src/httpserver.cpp`, which `main` lacks.
- **Stack sizes:** `ecashd` is 378 commits above ABC `1fb7db17`; V2 is 153 above
  `ecashd`. ABC `master` has since moved 139 commits, to `c694c36d`.
- **Patch files:** `daemon/patches/{ecash,v2}` are frozen exports last touched
  10-22. Setup doesn't use them. `CLAUDE.md`, `AGENTS.md` and
  `daemon/docs/adding-patches.md` still describe that workflow.
- **Commits missing from both pins:**

| Group | Commits (approx.) | Source |
|---|---|---|
| Lock removal, radix indices, relay batching | 29 | `lotusd` `snowstorm/merklix-snowball` (see below) |
| 10-23 perf (executor, inventory, radix, script reuse) | 12 | Same branch, also on `perf/*` |
| Header history tree, `verifytxoutproof` binding | 7 | Same branch |
| Snowball, miniblocks, fraud proofs | 11 | Same branch |
| Fixups for commits already in the stack | about 20 listed | `perf/*` on both repos |
| `rpc: isolate bounded commit owner` | 1 | `perf/async-rpc-*` |

Tier placement in this table comes from subjects and file paths, so phase 3 has
to confirm it against the diffs.

That branch was first read from a stale `origin/archive/merklix-snowball-20261024` tracking
ref. The remote branch had already been deleted, so its tip `71a6f793` was held only by the
10-25 bundle and local objects. It was re-published on 2026-11-01 as `snowstorm/merklix-snowball`.

### Tooling defects

1. **Rebasing across a bridge breaks.** Reproduced in a scratch repo with plain
   git: `git rebase --onto new old HEAD` over a `-s ours` bridge replays the
   second-parent history too, and stops on a conflict. From reading the code,
   `autosquash`, `rebase-upstream` and `_cascade_children` rebase that way, though
   the tool commands themselves haven't been run against a bridge. `sink-to-ecash`
   cherry-picks instead, but it also needs to take its commit range from the stack head.
2. **The bridge targets the wrong commit.** `sync` bridges the old pin, not the
   remote branch tip. On `lotusd` those differ, so the push would not fast-forward.
3. **`sync --push` can force-push.** Without `--bridge-ours`, it uses `--force-with-lease`.
4. **`verify` doesn't check branches.** A pin can be off its named branch and
   still pass, which is how `lotusd` drifted.
5. **Branch default is wrong for the new layout.** `DEFAULT_BRANCHES['ecash']` is
   `master`, and `sources.json` records no branch for `ecash` or `v2`.
6. **Test gap.** `daemon/scripts/tests/test_daemon_sources.py` tests bridging, and
   separately tests `autosquash`, `sink-to-ecash` and `rebase-upstream`, but never
   a rebase operation after a bridge, which is why defect 1 went unnoticed.

### Lock-removal commits were never gated

These commits are authored by `Canonical patch progression` and dated 10-23 and
10-24. The preserved checklist
(`~/repos/archive/evidence/lotus-historical/daemon/patch-intake/20261023/PERFORMANCE-WAVES-TODO.md`)
marks the matching designs "reviewed; unimplemented", with specific unresolved concerns:

| Commit | Checklist item | Concern to check |
|---|---|---|
| `952db7eb` `TxRelayIndex` radix snapshots | W2-2 | Publication lifecycle; an atomic `shared_ptr` alone isn't lock-free; competes with W1-8 |
| `ac31d9dc` `mapNextTx` radix map | W2-3 | Duplicate/conflict semantics, parent/child behaviour |
| `77d48070` live radix indices | W2-4 | Entry metadata isn't synchronized by lifetime retention; clear and re-admission |
| `d650d95b` unbroadcast flag | W2-6 | Flag/count/log coherence across removal and re-admission |
| `39c96054` retained wire bytes | W2-8 | All construction and serialization paths; memory cost |
| `96b33269` shared broadcast payloads | W2-9 | Transports, checksums, compression, async send lifetime |
| `a5b49518` batched admission relay | W2-10 | Callback/error order; atomic versus individual semantics |
| `d9e932b6` sharded execution cache | W3-6 | Coherent coin provider is a separate prerequisite |
| `e91e089f`, `447c4aac` `cs_main` decoupling | W3-8 | Authoritative indexes, ordered outbound, teardown |

They may well be right, but they get audited before landing, not after (phase 4c).

## Rules for the whole effort

- **Reuse checkouts:** work in `daemon/ecashd` and `daemon/lotusd`. Add a
  worktree only for real isolation and remove it afterwards.
- **No patch files:** commits are the source.
- **Compile-only until the sweep:** each commit builds all targets and runs only
  its own new tests. One full sweep follows integration; failures become labelled fixups.
- **eCash compatibility:** the `ecashd` tier stays consensus- and P2P-compatible
  with stock ABC, or the feature is default-off or moves to V2.
- **No compatibility shims** for unreleased `ecashd` or V2 behaviour.
- **Owner approval required:** resetting `master`, changing a default branch,
  deleting remote branches, opening or closing PRs, and any ABC submission.

## Phase 0: Safety snapshot

1. Tag current tips of both repos as `archive/pre-reconcile-20261101/<branch>`,
   including every `perf/*` and `consolidation/*` branch.
2. Verify `daemon-lotusd-all-refs.bundle` still lists
   `archive/merklix-snowball-20261024`, and create the equivalent check for `bitcoin-abc`.
3. **Unpushed Snowstorm code:** the `snowstorm-spec` branch in
   `~/repos/lotus-snowstorm-spec/daemon/lotusd` (`4cb465f6`, 14 commits, about 15,400
   lines above the pin) is on no remote and in no bundle, and lives only in that
   worktree's module storage. Push it to `lotusd` as `snowstorm/implementation`
   before anything else.

Done when every remote head has a tag and a bundle entry, and no daemon commit
exists only locally.

## Phase 1: Tooling and agent docs

Fix the tools first, so the rest of the plan uses them.

1. **Named branches:** add `branch` to all `sources.json` entries, with `ecashd`
   for `ecash`.
2. **`stack_head()`:** returns `tip^1` when the tip is a bridge. Every rebase
   operation starts there. Refuse a bridge anywhere but the tip.
3. **Publishing:** `sync --push` bridges the remote branch tip when it isn't an
   ancestor, then pushes fast-forward only. Remove the force path.
4. **`verify`:** fail unless the pin equals the remote branch tip, the tree
   matches, and no fixups remain.
5. **Child stacks:** V2 sits on the published `ecashd` tip. The scratch test showed
   `--onto` rebases correctly past a parent's bridge. Each tier holds at most one
   bridge in its own range, at its tip.
6. **`extract-pr`:** extract onto current ABC `master`, into `upstream/<topic>`.
7. **Tests:** extend `daemon/scripts/tests/test_daemon_sources.py` to cover all of
   the above, starting with a failing test for rebase operations after a bridge.
8. **Docs:**
   - Add `daemon/AGENTS.md` with `CLAUDE.md` pointing at it. Agents working in
     the submodules pick it up from the parent directory, so no agent file goes
     into a stack headed upstream.
   - It covers the branch table, tier rule, invariants, the command for each
     task, fixup and compile-only rules, and where evidence goes.
   - Rewrite `daemon/docs/adding-patches.md` around commits.
   - Move historical sections out of the 609-line root `CLAUDE.md`/`AGENTS.md`
     into `docs/`, leaving current instructions.
9. **Retire patch exports:** archive `daemon/patches/{ecash,v2}` after checking
   every consumer, including the `stack-review.json` manifest hashes. Other series
   stay until their release tooling is checked.

Done when the tests pass and a fresh agent can answer "where does this commit go
and how do I publish it" from `daemon/AGENTS.md` alone.

## Phase 2: Normalize branches, with no content change

1. Create `bitcoin-abc` `ecashd` from `master`, with the same tree as the pin. Make it default.
2. Bridge the `lotusd` pin over `main`'s tip and fast-forward `main`, which brings
   the HTTP repair.
3. The V2 pin sits on `d38c3820`, while the `ecashd` tip is the bridge `73ed9c43`.
   Rebase V2 onto `73ed9c43` (same trees, new SHAs), bridge over `main`'s tip from
   step 2, and fast-forward `main` again.
4. Reset `bitcoin-abc` `master` to mirror ABC (one owner-approved force-push;
   its old tip remains an ancestor of `ecashd`).
5. Update pins and run `source-verify`.

Done when pins equal branch tips, with trees unchanged from today:
`2c6b9bc7` and `a576cd04`.

## Phase 3: Ledger

Create `daemon/stack-ledger.json`, with one row per commit on any 2026 branch
outside the pins, including local refs and intake candidates.

Each row gets one disposition: `in-stack`, `integrate:<tier>`, `fold:<target>`,
`pr:<branch>`, `superseded:<commit>` or `drop:<reason>`.

Also:
- Update the waves checklist in the ledger: implemented by which commit, or still
  open. Open items (for example W1-8, W1-9, W1-12, W2-7, W2-11, most of W3) stay
  as backlog; this plan doesn't implement them.
- Compare the `perf/*` fixups against the merklix branch, since neither has been
  checked for equivalent changes.
- Recommend a disposition for `givelotus/lotus` PRs #24, #25 and #26. #26 targets
  the retired `lotus-v2-optimizations` and its machinery looks superseded;
  #24 and #25 add MDBX as patch files. PRs #19 and #20 aren't part of this.

Done when no source commit lacks a row. Only then delete the retired branches.

## Phase 4: Integrate

One fixup or commit at a time, with `make -C daemon sync` at each checkpoint:

Each stack rewrite here also applies the commit identity and message rules in
phase 8, so SHAs only churn once.

a. **Fixups and async RPC:** fold each fixup into its parent (`ecashd` tier first),
   then restack V2. Some parents are known to be slightly broken without their
   fixup, so build each folded commit.
b. **10-23 perf work:** shared part into `ecashd`, native adapters into V2. Most
   have gates recorded in the checklist; those gates predate the new base.
c. **Lock removal:** split into shared and V2 commits, because some commits with
   no V2 paths are still V2 logic (for example 65-byte Schnorr). Each mechanism
   gets the phase 6 audit before landing, along with the table above.
d. **Header history:** V2 only, as its own topic, merged into `main` after audit.
   It changes what `MonetaryState` commits to, which is fine pre-release.
   `docs/lotus-v2/header-history-tree.md` already says "implemented", which only
   becomes true on the pins at this step.
e. **Snowstorm, as draft PRs that aren't merged by this plan:**
   - `lotusd`: the 11 merklix-branch commits as `snowstorm/merklix-snowball`, and
     the 14 unpushed commits as `snowstorm/implementation`. These are separate
     lines, so the PRs stay separate.
   - `givelotus/lotus`: the 25-commit `snowstorm-spec` branch plus its five
     uncommitted files (committed as they are). It moves `daemon/lotusd` and
     `sources.json`, so its pins need updating after phase 2. Its worktree goes away
     once the PR holds everything.
   - Further Snowstorm spec and simulation work is its own project.

Done when the ledger has no `integrate` or `fold` rows left.

## Phase 5: Move V2 work down

For each V2 commit that touches shared code, classify it:

- **Shared:** no V2 types or rules; moves down with `sink-to-ecash`.
- **Mixed:** split; the mechanism moves down, and the adapter stays as a V2 commit.
- **V2 only:** stays.

Starting candidates (by touched paths; to be confirmed against the diffs):

| Commit | Why it's a candidate |
|---|---|
| `de7f8c45` `mempool(v2): avoid repeated parent and overlay work` | Mostly `txmempool`, `net_processing` |
| `55ebe055` `memoize exact BIP340 verification` | Sigcache mechanism under `script/` |
| `d1f3dc16`, `f89567be` native crypto warm-up | Possibly mixed: `validation`, `node/` |
| `09cee0bd` pinned mempool snapshot reconciliation | No V2 paths, but it's new P2P, so default-off if moved |
| `92799cd0` compressed block frame cache | Labelled V2 only; `ecashd` compresses too, so re-check |
| `c7e77d66` BIP30 skip | Check the shared part only |

Then re-order `ecashd` so topics are contiguous and independent ones come first.
Group the 378 commits into topics (`logging` 106, `net` 50, `test` 42, `chronik`
28, `metrics` 18, `http` 16 and so on) in `daemon/stack-topics.json`. A topic is
the review and audit unit, the "PR".

Many moves won't need a V2 change. Always restack and build V2 after a move; where the
moved mechanism does need adapting, make that small change as a V2 commit (or a fixup
to the V2 commit it corrects) before moving on.

Done when no V2 commit changes only shared behaviour, V2 builds on the final
`ecashd` with all adaptations in place, and every commit belongs to a topic.

## Phase 6: Current ABC, sweep, and audit

1. `make -C daemon rebase-upstream SERIES=ecash COMMIT=latest` onto current ABC,
   then restack V2, so everything below tests the code that gets submitted. Doged
   and Chronik provider pins are separate and don't move with this.
2. One full sweep: unit, functional and Rust on both tiers. Fix as labelled fixups.
3. Sanitizers and fuzzing: TSan on lock-removal topics, ASan/UBSan across the
   stack, and existing fuzz targets on changed parsers.
4. Audit each topic, using a fresh reviewer given the code rather than a conclusion:
   - **Correctness:** lock scope, memory ordering, object lifetime, teardown,
     reorg and re-admission paths, regression tests that fail without the change.
   - **Consensus and P2P:** no `ecashd` consensus change; compatible with stock ABC.
   - **Security:** untrusted input bounds, memory and CPU exhaustion, decompression
     limits, removed or raised limits, delay bypasses, RPC/HTTP/WebTransport
     exposure, secrets in logs, on-disk durability.
   - **Prior concerns:** the matching waves review, answered explicitly.
5. Each topic gets `daemon/audit/<topic>.md`, with exact commits, verdict
   (`pass`, `fix`, `hold`), and independently verified findings. Fixes go in as
   labelled fixups. A `hold` removes the topic from the stack (the ledger records it).

Depth differs by topic:

- **Deep, multi-agent:** lock removal, audited first (phase 4c runs this ahead of
  landing). Results decide whether anything else needs the same depth.
- **Lighter pass:** everything else, which has had substantial prior review. Check
  it against that evidence and the checklist above, and escalate only on a finding
  or where the prior review predates a meaningful change.

Done when every topic has `pass`.

## Phase 7: Perf sweep and graphs

**Precondition:** no sweep runs until phases 4–6 are complete. All fixups are folded,
all perf patches are in `ecashd`, V2 is adapted and builds, and audit fixes are in. Earlier
numbers don't count, because every later rewrite would invalidate them. If a later
change touches a measured commit, re-run the affected points.

Reuse `daemon/bench/commit-regressions` (`run.py`, `progression.py`), which already
records build receipts and keeps failed samples as N/A, plus `daemon/bench/workloads`
and in-tree `contrib/bench/*`.

- **Commits:** ABC base anchor, then each performance topic's tip cumulatively, ending
  at the `ecashd` tip and the V2 tip. Upstream candidates also get measured alone on
  ABC, since that's what a reviewer would apply.
- **Workloads:** RPC and P2P mempool admission, relay completion across peers,
  block validation, serving a block to many peers, concurrent RPC reads, Chronik
  reads, with latency percentiles alongside throughput.
- **Method:** the existing rules. Matched source, binary and config identity, at
  least three alternating isolated pairs, nothing building during timed runs.
- **Hardware:** the M5 Max only. Charts show relative improvement against the ABC
  anchor rather than absolute rates, and label the machine. The ARMv8 SHA-256
  commit will show up as a step in hash-bound runs, so call that out rather than
  crediting later commits with it, and measure across it.
- **Claims:** microbenchmark rates aren't daemon TPS, and nothing here measures
  block-confirmed or Avalanche-finalized TPS unless a workload actually does.
- **Regressions:** investigate; a topic that doesn't pay for itself goes back to the ledger.
- **Output:** reproduction steps in-tree, raw JSON under `daemon/docs/evidence/`,
  and a page of per-commit progression and per-topic impact charts, each point
  linked to its commit.

Done when each chart regenerates from raw data and each adopted performance topic
has a measured result, positive or not.

## Phase 8: Upstream to ABC

ABC reviews through Phabricator (`reviews.bitcoinabc.org`, Arcanist, stacked diffs).

1. Per topic, in order: `extract-pr` to `upstream/<topic>`, build and test alone on
   current ABC, attach audit summary and benchmark results.
2. Commit identity and messages, applied across both stacks during phase 4:
   - Author and committer are always `Shammah Chancellor
     <shammah.chancellor@notvalid.com>`, with no Claude or other attribution. A scan
     found no attribution trailers on either pinned stack. This normalizes 24 `ecashd`
     commits using another address, three placeholder identities, and the
     `Canonical patch progression` commits on the merklix branch.
   - Reword internal review shorthand such as "owner30" and "later27". Up to 48
     pinned commits are affected (a broad pattern match, to be reviewed by hand).
   - Write the six missing `ecashd` message bodies.
   - If ABC's process turns out to require a reachable address, handle that at
     submission for the affected batch.
3. Start with small independent commits already at the bottom of the stack (for
   example `a49f42c8`, `785b0370`, `d7bf80c3`, `93d2d476`, `645df9a7`), since they
   establish credibility and need the least review. MDBX and native Chronik come
   later and are worth discussing with ABC developers before submitting.
4. When upstream lands a commit, `rebase-upstream` drops it from the stack and the
   tooling publishes the next bridge.

Submission of each batch is an owner approval. Done means the first batch is
submitted, and the queue for the rest is recorded in `daemon/stack-topics.json`.

## Order

```
0 snapshot → 1 tooling/docs → 2 normalize → 3 ledger → 4 integrate → 5 move down
           → 6 rebase, sweep, audit → 7 perf sweep → 8 upstream
```

Phases 0–3 are low risk and leave code unchanged. Phase 4c and phase 6 are the bulk
of the work. Phase 7 is gated on phases 4–6 being finished, so the charts measure the
final commits.

## Owner decisions

Decided 2026-11-01:

1. **`-s ours`:** applies to both `ecashd` and V2.
2. **Snowstorm:** the monorepo `snowstorm-spec` branch also becomes a PR.
3. **Header history tree:** merge into V2 `main` after audit.
4. **Commit identity:** everything uses `shammah.chancellor@notvalid.com`, with no
   Claude or other attribution.
5. **Benchmarks:** M5 Max only, reporting relative improvements.
6. **Audit:** deep multi-agent audit on lock removal first; other topics get a lighter pass.

7. **Start:** approved, including pushing the unpushed Snowstorm commits to the public
   `lotusd` repository (phase 0).

## Status, 2026-11-01

Local only unless stated. Nothing below is published.

| Phase | State |
|---|---|
| 0 Snapshot | Done |
| 1 Tooling and docs | Done |
| 2 Normalize | Done, except resetting `bitcoin-abc` `master` and its default branch, which need owner approval |
| 3 Ledger | `daemon/stack-ledger.json` written. Retired branches aren't deleted |
| 4 Integrate | a, b, c, d done on local `ecashd` and `main`, with the exclusions in `daemon/audit/integration-*.md`. e done as draft PRs |
| 5 Move down | Not started. All `ecashd` commits still need identity normalized before publishing |
| 6 ABC rebase, sweep, audit | Not started |
| 7 Perf sweep | Not started; requires phases 4 to 6 |
| 8 Upstream | Not started; first batch needs owner approval |

Recommended for `givelotus/lotus` PRs: close #26, which targets a retired branch and is
superseded by `daemon_sources.py`. Close #24 and #25 only after their MDBX patch files are
ported to commits on the stacks or recorded as dropped.
