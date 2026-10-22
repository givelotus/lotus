# Full-membership Manager: lead source review

Reviewed actual integration from `650aeb5959` through `6dc6afa90ef4d03abcae61d708566b8deeffc7ed` in `/Users/shammah/repos/lotus-v2-authoritative-relay-requests`. No builds or runtime tests by this lane. Scope is complete permissionless reconciliation, not epoch consensus or a primary storage rewrite.

The complete-prefix design is implemented: connection-owned context/request IDs, negotiated scope5, one immutable full-pool capture shared among peers, absolute canonical prefix proofs, bounded DFS, complete <=64-body pages, LIMIT-driven deeper expansion, one response per request, and ordinary admission after one topological ordering of recovered bodies. Discovery completion and live admission are counted separately. A same-TxId/different-TxHash remote candidate is reconstructed exactly but does not force local replacement.

Concrete findings and repairs:

- The stale cache itself counted against replacement allocation even after other owners released it. A sufficiently large otherwise affordable generation could never replace it. The replacement path now drops its cache reference before budgeting; active serving/fetching references preserve their original snapshots.
- Repeated SENDINVSHORT capability disable/enable could erase `queued_charge` while its bytes still occupied the connection's send queue. The repaired path retains connection accounting across disable and releases it only after the queue actually drains or the connection disappears. A regression exercises renegotiation before drain.
- Protocol review found that requiring the current block tip to equal the captured anchor indefinitely restarted paced transfers. Anchor metadata now does not invalidate immutable transport snapshots on ordinary chain progress; transaction admission uses current authoritative state.
- Equal-digest skips now compare the known exact local count, rejecting inconsistent advertised counts rather than silently reporting the declared count covered.
- The initial64MiB PAGE scratch reservation was concretely insufficient: vector headers behind empty arguments plus identity-projection copies can exceed97MiB for a sub2MiB frame. An allocation-free grammar walk now precedes ordinary decoding; the independent overlay reviewer must close its grammar/peak-memory bound before build release. Increasing a guessed constant alone was not accepted.

Final source release: `d7d273f5420532dd923a44de95e29283fd75ef30`, tree `94ff44ff94b836d615a89474c21f99ed1f86276c`, parent `2446653f0e3c3ec495b3fe0260f2676b9023cec0`. Protocol review closed at `6dc6afa90e`; the remaining narrow repair releases owned state before best-effort cancellation, preventing notification allocation failure from retaining pins. Resource review closed at `8b011e5cfc` after checking the scanner's allocating grammar and phase-derived peak bound. The lead verified all nine feature paths byte-identical between that reviewed endpoint and the composed `d7d273f542` candidate. No source blocker remains.

N1 was explicitly released for compilation and the aged10k/no-stake/no-Avalanche network gate. No execution result is asserted here. Source review does not supersede the earlier failed10k reconnect evidence or establish500k performance.
