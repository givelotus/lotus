# [bug] Lotus v1 sync requires an unofficial hotfix and manual intervention

Status: unpublished investigation draft. Proposed scope: V1-00/V1-02 diagnosis followed by separately accepted V1-04 fix. Tier 3: consensus compatibility and persisted state. Decision owner: project maintainer; execution/review owners unassigned.

## Summary

The user reports a nearly syncing v1 node that stops at a historical block and requires another repository's hotfix plus manual operation. A normal supported release should sync the intended running network unattended and recover supported existing stalled states.

## Reproduction and evidence

Exact command, binary/source revision, operating system, first rejected block/hash, rejection message, data-directory format, hotfix commit and manual steps are unknown. Do not invent them. Preserve the original stalled state before experiments. Redact wallets, credentials and private endpoints from shared logs.

Local leads: `docs/new-chain.md` mentions Ruth, height 927381 and `v8.3.3-hotfix`; `daemon/patches/v1/206-fix-broken-replay-protection-and-minerfund-outputs-8.patch` carries `2e59ea5cce092df68e04ef375818482bb936d605`. Neither is a verified cause of this report. The current live chain/reference must be identified by genesis and fixed-height hashes.

## Impact and expected behavior

New users cannot depend on ordinary initial sync; existing nodes may require undocumented persisted-state operations. The supported node must validate the intended history with deterministic rules and a documented, evidence-preserving recovery path.

## Investigation contract

On disposable copies, compare ordinary reference, pinned hotfix and candidate at the same boundary. Separate block-rule disagreement from activation/configuration, stored invalid/parked state, chain selection and database/index errors. Document exactly what each manual step changes. Return source identities, minimal historical fixture, before/after diagnostics and a bounded proposed repair. Do not reset the user's original data or broaden validation acceptance without a justified compatibility rule.

## Proposed fix acceptance

- Deterministic fail-before/pass-after regression at the observed boundary, with adjacent unaffected validity cases.
- Unattended clean historical sync through the boundary to matched fixed-height checkpoints.
- Supported stalled-state recovery, restart on each side, interrupted repair, block import/reindex and bounded disconnect/reconnect.
- No hidden consensus flags, blanket bypass or required unofficial binary.
- Versioned/idempotent metadata repair where needed, with rollback/data-preservation policy.
- Provenance and incident explanation integrated into maintained v1 sources; historical exception excluded from new v2 genesis rules.

If automatic recovery cannot be made safe, record the reason and seek acceptance of a normal supported recovery procedure before closing the release gate. The implementation shape remains NEEDS_SPECIFICATION until evidence identifies the failure.
