# Request ownership and adversarial review of full-scope draft1

Reviewed: `triage/astra-reconciliation-overlay-spec/INITIAL-DRAFT.md`. This note reviews the design only; it adds no protocol or production implementation. The independently prepared narrow relay request repair remains limited to the existing LIVE_MEMPOOL relay-epoch path.

## Compatibility with the narrow repair

The proposed FULL_MEMPOOL context must keep independent round/request ownership. The narrow repair uses the ordinary tracker only for requests actually announced and issued as synthetic(chain-epoch, short-ID) keys. That tracker intentionally has no pinned candidate root or full-scope request identifier, and ordinary transaction admission forgets those announcements across peers. Reusing it for FULL_MEMPOOL would lose the round's exact ownership and completion state when another route supplied the same transaction. The new scope must continue through its separately owned handler state, not the LIVE_MEMPOOL relay-epoch shortcut.

The existing private feature allocation is INVSHORT bit0, RECON bit1, HIGH_BANDWIDTH bit2. HIGH_BANDWIDTH means acceptance of sealed-header announcements and unsolicited transaction bodies; it does not establish full-scope reconciliation support. Advertise and require the new capability separately. NoBan must not substitute for negotiation, and permission to bypass ordinary announcement limits must not bypass round ownership or full-scope memory bounds.

## Decisions needed before implementation

1. **Authenticate each zoom response to its expected parent.** Matching an outstanding context/depth/mask alone is insufficient. Recombine the returned canonical child commitments using absolute depth, routing and singleton/empty rules, and require equality with the pinned expected parent digest. Specify exactly when full TxId/TxHash must accompany a singleton descriptor to make that recombination possible. Count/sketch fields remain hints unless their consistency is proven; they cannot prune a cryptographically mismatched child. This is especially important beyond the old16-bit terminal boundary.

2. **Define an exact request/response state machine.** Key each outstanding request by connection incarnation, direction, scope, context token and request identifier. Request IDs should not be reused during a context; cancel before wrap. State transitions must say which partial responses retain ownership, which fields are immutable, when a retry gets a new ID, and when late/duplicate packets are ignored. An ordinary body arriving by another route cannot clear this ownership implicitly.

3. **Specify completion per hint and per response.** A byte-limited message may return some candidates for one SID and none for another. The encoding needs explicit unresolved/partial/ambiguous/unavailable information, rather than a single Boolean implying every requested hint was fully represented. A mutable lookup index cannot certify that it enumerated every collider from an old pinned view. Treat its bodies as candidates and zoom if cryptographic reconstruction cannot establish completeness. Exact terminal identity lookup must remain available. Never consume a SID after the first matching body when another valid collider is in the same response.

4. **Separate equality, traversal completion and admission outcomes.** Receiving a transaction changes the live pool, not the local pinned generation. Define whether a resolved prefix means the two original pinned prefixes matched, a complete remote difference was enumerated, or a bounded reconstruction over the old local view succeeded. These are different claims. State where reconstruction evidence or a working persistent root lives and charge it to the retention budget; do not silently build another full unbounded set. Distinguish matched, fully attempted, policy-rejected and transport-unavailable outcomes. A same-TxId/different-TxHash mismatch may be irreconcilable under first-seen policy even when both transactions are valid; normal admission cannot be assumed to replace it. Repeating that prefix forever is not useful liveness.

5. **Check key domains before scheduling work.** Bind to the allowed current/previous validated relay domains before allocating caches or scheduling O(N) work. An arbitrary claimed epoch, fork or key must not cause a new global summary domain. A bounded unknown-domain status or waiting for chain alignment is preferable. Once bound, later requests cannot overwrite the context's key, root or prefix interpretation.

6. **Make unavailable responses non-amplifying.** Responses to unknown contexts must be bounded and must never elicit another status response. Charge malformed, oversized, duplicate, partial and cancelled work against explicit per-peer and global budgets. Disconnect or context eviction must cancel queued workers and release their retained objects, including bodies held by futures or reconstruction state. Permission flags should preserve operator choices without disabling these correctness invariants.

## Required request-path tests

Keep a real-peer wire test for more than4096 initial requests separate from the full-scope test. The narrow test already exercises a requested body beyond the old duplicate cap, incorrect peer/epoch, unrequested and expired requests, and two valid bodies forced to share one short ID in a response.

For FULL_MEMPOOL add focused cases for:

- A correct context with child descriptors that do not recombine to the requested parent.
- Reflected direction, stale connection, reused request ID, late partial completion and duplicated bodies.
- A pinned old generation whose SID index has since removed a member or acquired a collider.
- A byte limit reached halfway through a collider set or halfway through requested hints.
- Two simultaneous rounds naming the same SID; completion in one must not clear the other.
- A valid but currently inadmissible transaction, and the same TxId with another TxHash, without a false equality or endless hot retry.
- Current-pool admission during traversal while the pinned local root remains unchanged.
- Unknown epoch/key floods that schedule no full-root or full-summary work.

These tests complement canonical root, immutable snapshot and bounded-memory proofs. They do not authorize new full-scope code before the specification/review gates finish.

## Follow-up on review draft 2

Draft 2 addresses the initial request ownership, opportunistic collider response, pinned-view reconstruction and exact-identity fallback concerns. Two clarifications were sent to the specification owner:

- Section 3 keeps accepted rounds alive after sketch-domain retirement by using exact canonical zoom, while section 6 cancels contexts on key retirement. Select one explicit lifecycle policy.
- The canonical internal digest commits child digests and depth, not a numeric count directly. Changing a descriptor count while preserving the same greater-than-one structure need not change that digest. Treat counts as checked traversal/optimization metadata unless a separate proof authenticates them; terminal identity and canonical digest reconstruction remain authoritative. This affects claims about authenticated counts, not the validity of the underlying canonical commitment.

No production implementation or build was added by this review. The narrow request-tracker candidate still awaits its independent native gate.
