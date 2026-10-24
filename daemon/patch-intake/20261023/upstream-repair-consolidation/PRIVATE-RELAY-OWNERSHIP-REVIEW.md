# Shared private-relay regression exposed by owner-prefix gate

This is a new finding, not a passing consolidation gate. Do not promote pipeline history yet.

The modified admission owner268 e13f3740 compiles after moving its timer instrumentation to the later metrics owner, but common units fail `v2_protocol_handler_tests/single_tx_relays_wait_for_the_relay_tick` twice (pushed0, expected16). Announcement count remains16. Its outbound production logic is unchanged by the new incoming queue/body-budget patches.

The test is introduced by fixed-relay-tick owner bf8fe3b30d56db7f223bc5017ecf2b62f84aa41f. It calls SetHighBandwidthShortTxPeer directly. At this point real production requires `peer->m_txrelay_features & TXRELAY_HIGH_BANDWIDTH`; setting the handler flag does not simulate that wire negotiation. The native test already uses a real SENDINVSHORT offer. Port that fixture precondition to its introducing shared relay-tick owner without reducing counts/known-inventory assertions.

Late shared RPC owner a789badba6b4f79db95044d22694037fccd8d054 has unrelated networking rollback hunks: it removes TXRELAY_HIGH_BANDWIDTH, rewrites OurTxRelayFeatures to always offer short IDs, removes remote capability assignment to the private handler, and replaces explicit negotiated capability gating with BIP152 high-bandwidth/NoBan/local-handler tests. It also removes private-negotiation regression tests. Exact committed diffs are saved in RPC-OWNER-PRIVATE-RELAY-ROLLBACK.diff. These are not RPC batching prerequisites.

Native consensus owner cdbd81dca9a7629a10d8179a4754b8763f140346 restores explicit private capability negotiation and SENDINVSHORT fixture preconditions. Thus the native endpoint passes, but final shared behavior is different and the intermediate test is broken. Do not use a final passing test as evidence that the earlier owner is correct.

Proposed repair cohort, not yet executed:

1. Preserve current rewritten history/dirty work (input and final-fold verified bundles already retained); retain all old refs.
2. Enumerate each networking/test hunk in the RPC owner against its parent and the native restore. Separate actual RPC dispatch/admission changes from unrelated capability rollback. Do not restore whole later files or port V2-only rules into eCash.
3. Remove the unrelated rollbacks from the RPC owner. Keep the earlier shared feature and safety regressions. Move the fixed-relay-tick test negotiation precondition into bf8fe3b30d. Keep native wire/consensus adapters explicit; remove only duplicate native restoration hunks once shared provides them.
4. This intentionally changes the shared endpoint to restore a previously implemented shared feature. Project and review its exact expected diff separately from pure folds. Require full native endpoint tracked tree to remain exactly490828237d36596fcbc39a7e4597e5d7b78f772f if all moved hunks were already restored there. Any other change fails the move and needs a separate reviewed behavior diff.
5. Gate relay-tick owner, admission owner268, late shared RPC owner, full shared and native boundaries. Keep 16 pushed transactions, known-ID exclusion, permission/non-negotiating-peer cases and explicit remote-capability tests. No assertion weakening or bypass.
6. Compose ownership from PIPELINE-FINAL-COMPOSED-OWNERSHIP through the new mapping, including the networking hunks that move out of native consensus into shared. Preserve source/benchmark identities; 21.9% timing remains pre-body-budget64176, not a claim about a new shared endpoint.

Self-review: classify this as an explicit shared behavior restoration plus source-owner repair, not a tree-preserving shared reorder. Existing native success is useful only because its exact source tree already contains the intended capability behavior. Audit all other rollback hunks in this RPC commit (txrelay index, tests, headers) before concluding the issue is fully accounted for.

## Concrete shared projection

Temporary-index checks against b14362f3 succeeded without changing the active source checkout. Reversing exactly the six-path RPC rollback projects tree299b2c0e1b78ec04336b48fcd78d17a4b92555e6. Correcting the two remaining fixed-tick fixtures (permissions and single-transaction; the burst fixture is already restored) to real SENDINVSHORT offers projects expected shared tree7657f2a7ec047b6c0b553abb2edfdec8d744888d. The exact expected shared repair diff is PRIVATE-RELAY-EXPECTED-SHARED-REPAIR.diff; this remains a reviewed projection, not applied or compiled. Private-negotiation regression tests must be restored, not replaced by relaxed counts.
