# Lotus patch strategy

Current roadmap, October 9, 2026. The previous strategy is preserved in [the historical archive](archive/patch-strategy-2026-10-08.md); its status labels and build sequence are superseded.

1. Establish the running v1 chain/reference and diagnose the historical sync obstruction.
2. Reconcile source pins, safe workspace routing and patch provenance.
3. Port compatible v1 behavior onto the recorded modern ABC candidate; integrate the supported sync/recovery fix and qualify a release.
4. Pin that validated-v1 source commit, then construct a v2 overlay for a separate new chain.
5. Prepare independently useful upstream patches on their own pinned bases.

See the [v1 implementation plan](lotus-v1-implementation-plan.md), [v2 implementation plan](lotus-v2-implementation-plan.md), [upstream plan](lotus-upstream-plan.md), [feature provenance](feature-provenance.md) and [validation results](lotus-validation-results.md).

The [inventory](../patches/inventory.csv) is the current source-evidence snapshot. Existing `series` files describe what tooling currently attempts, not a verified target architecture. Their historical `DONE`/placeholder/comment labels are not evidence of application or tests. Keep one logical purpose per patch; multiple patches may legitimately modify the same file in dependency order.

Do not run old reset/rebase commands as a substitute for V1-01. In particular, setup and Makefile descriptions disagree, upstream/v2 workspaces overlap, and v2 does not yet derive from a validated-v1 pin. No production runtime flag may silently substitute a different issuance schedule to make inherited tests pass.
