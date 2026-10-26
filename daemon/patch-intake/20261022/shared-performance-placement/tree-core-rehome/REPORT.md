# Shared persistent transaction-tree source checkpoint

The Merklix tree, lazy digest/MinHash, bounded payload accounting and immutable pin engine now execute in the shared overlay. The native companion retains authenticated full-membership protocol integration, native snapshot/state hooks, metrics, native tests and functional coverage.

Shared candidate `b49e8bdecc08165beb4b255b93ee0ed08806dce7` and native candidate `ef42f1ea59399923a57a9b813e3103c98cbcbc8d` contain 378 shared and 153 native purposes. All 531 commits replay with every intermediate tree verified. No fixup or merge commits remain. This adds one logical shared engine owner while preserving the native companion; it does not squash unrelated features.

The final complete tracked tree is `591fb5e702dda0c70a94a7123dc1012ad6e2eace`, byte-identical to the separately compiled/full-1203-tested adapter checkpoint01003. Compared with the previous canonical f58 tree, the sole source changes are two reviewed includes from header.h to commitment.h. Native consensus, codecs, domains, monetary/state-root rules and authenticated body validation remain intact.

The new shared prefix compiled 447 normal actions and passed the generic tree property suite (12 cases/15,315 assertions), complete overlay, miner, mempool and snapshot-RCU suites. Existing legacy positional roots, effective cost, fee/sigcheck accounting and eager/lazy UTXO behavior remain shared. The generic suite is split unchanged from its original native test file; the complete original native test file is retained at the native tip.

`OWNER-MAPPING.json` maps every native owner, and `HUNK-DESTINATIONS.json` records shared production/build/test destinations. `SELECTION.json` identifies retained native adapters. Backups and the verified source bundle preserve the prior source history. Conflict resolutions retain opaque transaction references/payload charging through native header conversion; later native monetary adaptation removes only its original shared accounting surfaces. The final native companion removes duplicate tree registration and duplicate payload charging introduced solely by relocation.

Canonical refs, pins, maintained mailboxes and manifests are deliberately unchanged at this completed source checkpoint, pending the parent-coordinated ecashd/lotusd naming transition. This is not a claim that canonical metadata promotion has occurred. No compiler, tests, rebase or runtime remains active. No further source group has started.
