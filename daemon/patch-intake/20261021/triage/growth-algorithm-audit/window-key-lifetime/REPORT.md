# Incremental-window radix key lifetime repair

Confirmed source defect: `WindowEntry::getId()` returned a `Uint256RadixKey` by value, while `PassthroughAdapter::getId` declared `auto&&` and returned that temporary. Binding a returned reference does not extend the temporary beyond the return expression. The temporary is destroyed before `RadixTree::getId` copies the referenced key; that copy therefore reads a dangling reference. N1 reported Clang return-stack-address diagnostics from the actual native build. This is a correctness defect even if inlining makes an observed run appear successful.

Pure source fix `2995b4b215` (tree `874103e1b9f6e906bdefb65669920d078dd67752`) on exact base `2cf83331db74d3d13c6945fcce9fb99f12027339` is in `/Users/shammah/repos/lotus-v2-repair-work/recon-window-key-lifetime-source`. It replaces only this tree's passthrough adapter with `WindowEntryAdapter`, whose declared return type is `Uint256RadixKey` by value. RadixTree's existing by-value adapter wrapper then receives a live value. The unsafe member getter is removed.

This preserves the numeric key type, bit width, conversion, tree order, entry memory layout, membership and allocation behavior. Returning `const TxId&` instead would break the numeric radix API; storing another numeric key would add an unnecessary 32 bytes per entry. The generic upstream PassthroughAdapter is unchanged.

Causal owner: `c1828a84aa3fcb18ff37f489bd5d90e2665ca6d7`, subject `net: maintain a pinned incremental reconciliation window`, imported from the earlier b93 candidate. Source blame attributes WindowEntry and its passthrough alias to this commit. The delivery is a `fixup!` targeting that owner, independent of generic immutable storage and unresolved epoch lifecycle work.

Whitespace checks pass. No compiler, runtime, performance run or test was started by this audit. Existing independent selectors are `txrelay_tests/recon_window_pinned_index_matches_scan` and `txrelay_tests/recon_window_cap_follows_live_membership`; they compare randomized windows/epoch changes/pruning/old snapshots and live-filtered numeric cap/collisions against the scan oracle. N1 should compile the affected ordinary target and run those checks in its next authorized slot. No new test asserting a one-time textual conversion is added.

No claim attributes the earlier 500K convergence failure to this UB. The fixed cap/recent-window coverage issue remains independently established and unresolved by this local lifetime repair. Raw compiler-warning evidence is requested from N1 and will be recorded when supplied.
