# Mempool consistency policy — branch-first source handoff

Completed source is checked out on `daemon/v2` in the existing
`daemon/worktrees/merklix-slab-source` lane. The source Git branches and
`daemon/ecash-version` / `daemon/v2-version` pins are authoritative. The one
new shared commit is an ordinary Git commit; the legacy mailbox is an archival
export for the explicit replay checkpoint. No new migration layout is introduced.
The agreed maintenance workflow is `daemon/docs/adding-patches.md`.

| Ref | Exact source | Tree |
|---|---|---|
| `base/abc` (existing tag) | `1fb7db17c176cdea8a2c60d887891589382ee4e3` | Upstream base |
| `daemon/ecash` | `47765534500efe516e9306a6426d9c9ad9d216a4` | `55970688f7d135ce910a1cc11760887bfaf040c7` |
| `daemon/v2` | `a2af4764d116fa37fed463af1ffd3c6fb0514f76` | `f58bb4951d4431ab30f1b0363c7368f6969a5cb4` |

One new shared diagnostic-policy owner follows the previous 374 shared owners;
all 154 V2 owners replay unchanged. Total 529. Original528 mailbox bytes remain
unchanged; historical datasets retain their original527/528 labels. The active
archival order places V2 at global 376. `replay529.json` verifies every actual
mailbox and every intermediate tree against the authoritative source history.
`source-freeze.bundle` preserves both source branches and all 529 commits after
the immutable upstream prerequisite 1fb7db17. Bundle verification passed.

The BCHN04 port removes only the redundant transitive ancestor walk: existing
direct-parent entry-ID ordering proves transitive ordering by induction. The
checker already iterates parent-first. All other graph, coin, pointer, fee,
size and cached-memory assertions remain unchanged; see the mechanical exact
function audit in `checker-preservation.json`. Later V2 flag3 handling remains.

Node startup defaults `-checkmempool=0` on every network, including regtest.
The explicit option remains available. `-checkblockindex` still defaults 0 on
normal networks and 1 on regtest; the shared chainparams flag is unchanged.
Help text and `doc/mempool-consistency-checks.md` document the distinction.

Native fixtures retain explicit `check_ratio=1`; the functional framework now
explicitly passes `-checkmempool=1`, preserving its previous regtest checking.
The new policy test removes that framework override only to test actual startup
defaults, then explicitly enables checking for real admission and a post-reorg
pool containing the reaccepted transaction. Direct native tests exercise a 512
chain with repeated-parent inputs, a diamond, recursive removal, mined parents,
coin-view restoration, reaccept and default/override behavior on all networks.
No existing test assertions were removed, skipped or relaxed.

Validation: shared mempool/admission suites 34 cases PASS; final full unfiltered
native gate 1203 cases PASS; new functional policy/admission/invalidate/reconsider
test PASS on both the shared and final V2 layers. Build profile is Release,
wallet OFF, Chronik OFF, jemalloc OFF. Native validation intentionally checks 1.
The initial test-development failures and corrected runs are retained in logs.
The shared frozen binary was built before ordinary commit 477; its code matches
that commit while embedded version metadata may identifyca2-dirty. Final V2
was built from committed a2. Exact binary/config hashes are in the evidenceJSONs.

No new performance comparison is claimed. Prior check=1 and separate check=0
recovery results remain frozen under
`benchmark-results/20261022/fullscope-recovery-latency-diagnosis/`. Changing a
benchmark's effective checking option is a profile change, not code speedup.
A harness using the functional framework still checks 1 unless it explicitly
overrides that test default; future performance reports must record the option.

No push or publication attempted. All jobs drained. Both source/build lanes and
existing ignored databases are retained for branch-first maintenance and exact
recovery; no worktree, clone or unrelated configuration cleanup was performed.
