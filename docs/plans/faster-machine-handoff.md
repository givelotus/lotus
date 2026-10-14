# Faster-machine execution handoff

Status: preparation only. Start with V1-00/V1-01; do not start by applying all v2 patches.

The [implementation entry contracts](implementation-entry.md) bound the first workspace-tooling and independent reference-tool units. The [review handoff](../lotus-v2/review-notes.md) summarizes the candidate choices and outstanding production decisions.

## Transfer and preserve

Transfer the Lotus repository with full commit identities, local documentation/skill changes and original patch files. Record the outer repository HEAD and dirty-diff digest, nested workspace HEADs and dirty/untracked work separately; the outer Git history does not preserve a nested checkout automatically. Preserve stalled-node data with the daemon stopped or a consistent snapshot. Store wallets/credentials separately and never include them in test artifacts.

Required inputs: exact stalled binary/config/logs; candidate hotfix repository/ref/commit and commands; observed reference-node release and genesis/fixed-height hashes; compiler/dependency requirements; available disk/RAM; desired supported operating systems. Missing values are intake questions, not guessed defaults. Keep the old machine/data intact until the transfer is verified.

## Initial session

1. Read the v1 plan, local work packets and current provenance ledger. Inspect all existing worktrees/claims and preserve incomplete work.
2. Verify source and patch digests; pin the reference and target-chain identity. Inspect actual setup/build routing before any mutating command.
3. Complete V1-01 using disposable tooling fixtures. No `RESET=1`, branch overwrite or cleanup against valuable workspaces.
4. Reproduce the sync boundary using a consistent copy and pinned reference. Produce the V1-02 fixture and diagnosis before selecting the repair.
5. Port v1 behavior in bounded patches, integrate the fix, then run full historical sync/recovery and release qualification.
6. Record validated-v1 commit. Only then initialize the production v2 overlay; independent spec/reference work may have proceeded earlier.

## Workspace contract

Separate reference-v1, candidate-v1, candidate-v2 and upstream checkouts, build directories and data directories. Record process/resource identity and recovery ownership using the imported factory workflow. No worker shares an active daemon data directory. Estimate disk for reference, clean sync, preserved stalled copy, reindex and artifacts before allocating; do not infer requirements from the obsolete 1.2M-height notes.

Exact shell commands belong in the tested V1-01 handoff after tooling is reconciled. Existing Makefile examples are evidence to audit, not an execution recipe. Each completed stage returns immutable revisions, commands, expected/observed results, log/fixture hashes, limitations and the next dependency-ready stage.
