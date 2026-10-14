# [tooling] Make Lotus source pins and daemon workspaces reproducible

Status: unpublished draft for V1-01. Tier 3 because reset/checkout and source provenance affect preservation of work. Decision owner: project maintainer; worker/reviewer unassigned.

## Evidence

`daemon/scripts/setup.sh` selects `bitcoin-abc-version` for v1, while `daemon/Makefile` and historical comments describe `ecash-version`. V2 still starts directly from ABC; the accepted roadmap requires a validated-v1 foundation. eCash and v2 route to the same workspace. Setup permits recursive reset, force-updates a named checkout branch, and suppresses patch-commit failures. The inventory contains active no-diff placeholders and absent commented future filenames.

## Outcome and scope

Make pin meaning and checkout/build/data routing explicit before the rebase. Allowed boundary: `daemon/scripts`, Makefile, pin metadata, series manifests, provenance and execution documentation. Do not rebase Lotus consensus, delete existing workspaces, select a new network, or start live sync as part of this task.

## Proposed contract

Distinguish historical extraction base, modern candidate base, compatible reference and validated-v1 source. Validate series and required patch contents before mutations. Use separate v1/v2/upstream workspaces and output directories; reject accidental reuse or dirty destructive transitions. Fail visibly on patch/commit failures and leave a resumable record. Reset requires explicit disposition of existing work, never an implicit convenience step.

Prove behavior in disposable repositories: wrong/missing pins and placeholders fail before mutation; dirty work remains intact; repeated setup/resume is deterministic; each series routes to its own path; patch failure stops without claiming completion. Publish exact commands only after these tests. Do not replace a historical pin until its role and consumer are reconciled.

V2 routing may accept an explicit validated-v1 commit parameter but cannot invent its value before V1-06. Rollback restores previous tooling without changing preserved worktrees/data. Return tested source commit, fixture logs, routing table and unresolved pin decisions.
