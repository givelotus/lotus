# Pool job materialization (MR08)

Status: before-control reproduces the bug; unchanged functional regression passes on the compiled combined repair cohort.

The first pool job after a deferred nonempty mempool snapshot used its valid but empty mining-template stub. Calling `EnsureRoots()` computes roots for that empty selection; it does not populate the selection. The job consequently omitted pending transactions and their fees. The fix calls `EnsureMiningTemplate()` on the pinned snapshot before obtaining its template reference. Work stays demand-driven and outside the pool mutex and `cs_main`.

## Ownership

- Production fixup `87dbdfc3b0` belongs to `1ad901ac56`, the introducing native pool coordinator. Its template-read context already exists at that owner.
- Regression `c3eac61fc2` belongs to `8a185d4cad`, which introduces `mining_pool_native_payouts.py`. Keeping it there avoids introducing a test before its supporting native payout helpers exist.
- Source branch `work/pool-template-readiness-20261021`, worktree `/Users/shammah/repos/lotus-v2-pool-template-readiness`; base `a60bba6fac` (521), candidate head and tree are pinned in `delivery.json`.

## Reproducer and evidence

The native payout lifecycle test first confirms funding with 65 independent native outputs, submits 65 children paying 10,000 atoms each, and requests the first pool job without any intervening GBT. It checks the job reward includes 650,000 fees, then solves that exact job and checks its accepted block contains all 65 identities. Successful submission verifies transaction and state commitments, and the test checks the mempool empties. Existing native payout recognition, maturity and spendability checks remain.

On the preserved 521 daemon (`3e14b617...`), the first job paid 5,000,000,000 instead of 5,000,650,000. The test failed at that exact expected assertion (`control.log`). The later block-composition assertion was not reached on the control. The single fresh-node run took about one second; its processes are drained. Python compilation and diff whitespace checks pass. The identical functional test passes on combined source `2b61dded451755e175681f41a57281a5c0554e32` / tree `2b4fef46071b44cc8789a49553b3d112b4fd084e` (daemon SHA `339e5896…`) in about three seconds. The first job includes all fees, its solved block contains all 65 transactions, and inherited payout checks pass. `candidate.log` and `delivery.json` preserve the evidence. No performance claim; all owned processes drained.

No payout formula, operator commission, selection ordering, snapshot publication or consensus rule changes.
