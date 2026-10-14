# Incomplete Dogecoin port: initial current-ABC segment

**Review candidate only: incomplete, unbuilt and not runnable.** This directory is outside `daemon/patches/` and is not selectable by setup, build or release workflows. It must not be used with any chain data: its partial adaptations do not implement a complete Dogecoin node or preserve complete ABC consensus.

The 23 mailbox patches preserve the initial adapted segment of Tobias's ABC-derived Dogecoin lineage on exact Bitcoin ABC base **`8c67fe1e85a602204a2ce65aa3b643469c2c3a1d`**, also stored in `base-version`. Original source is `doged-io/doged` **`9690833b8b6709b7a7837bc397f0d04bf3b885d1`**. These patches are byte-for-byte copies of the reviewed local exports, now retained in Git instead of relying on `/tmp` files.

This candidate is distinct from the pinned Doged reference which passes native builds, unit/regtest checks and bounded mainnet download through height 100. None of that runtime validation applies to this partial current-ABC port.

## Replay and metadata evidence

`series` fixes the application order. `manifest.json` records each original commit, adapted commit, patch checksum, intermediate source tree and replayed author/date/message digest. All **23 intermediate trees**, the final tree **`bf971ab0f83cf34656bb6671e8078463099d9ee0`**, and all adapted commit metadata have been verified through replay. The shared patch-maintenance verifier independently passes its per-tree and metadata checks.

Original author identity, author date including timezone, subjects and rationale remain intact. Seven adapted messages differ from their original source only in line endings or trailing blank lines; the manifest records those cases. New committers and committer dates are expected when replaying mailbox patches; original commit hashes are provenance, not identities of the new commits.

Recheck using an isolated ABC clone and the existing shared machinery, from the Lotus repository root:

```sh
git clone https://github.com/Bitcoin-ABC/bitcoin-abc.git /tmp/doged-initial-review
python3 daemon/scripts/patch-series.py /tmp/doged-initial-review \
  daemon/candidates/doged-on-current-abc-initial/series \
  --base 8c67fe1e85a602204a2ce65aa3b643469c2c3a1d --check \
  --provenance daemon/candidates/doged-on-current-abc-initial/manifest.json \
  --expect-tree bf971ab0f83cf34656bb6671e8078463099d9ee0
```

`--check` replays in a temporary clone without promoting changes to the supplied workspace. It verifies application and source/metadata preservation only; it does not compile, start a node or publish anything.

## Adaptation decisions

The original first 24 unmatched commits produce 23 adapted commits because original `e43f0aea5c` only reformats checkpoints and is superseded by the adapted checkpoint representation. It is intentionally omitted; no consensus change is omitted under that decision.

- Port conflicts preserve current pointer-based address-manager APIs and `ToStringAddrPort`, with Dogecoin port numbers. The upstream-deleted Electrum Docker fixture stays deleted.
- Checkpoints preserve original Dogecoin hashes using current `BlockHash::FromHex` and `ChainType` APIs. Fixed seed data comes from the Dogecoin lineage.
- Scrypt registration keeps current Script interpreter tests. Base-header hash separation removes the obsolete duplicate header-hash method as the original adaptation intended.
- Python Scrypt is added alongside current compact-size serialization. Removed eCash-only DAA implementations lose their corresponding algorithm-specific tests.
- Height-dependent maturity preserves current benchmark padding and fixtures; it adds the Dogecoin DigiShield predicate without restoring the removed unrelated Augusto predicate. The wallet-link fix adds only activation code and retains the current removal of the obsolete string-encoding translation unit.

The complete conflict-resolution rationale and reviewed categories are in [`daemon/docs/dogecoin-lineage.md`](../../docs/dogecoin-lineage.md) and its 414-entry inventory.

## Remaining dependency

The next original commit is **`a06e1c4c831a6f0bbd9b1e3983a0c6b8d4c4594a`**, “Unbreak avalanche tests.” Its 14-file proof-score-width change intersects modern upstream overflow protection and changed coordination/test APIs. The old implementation demonstrably overflows for large Dogecoin amounts; blindly restoring it is incorrect. The independent [optional proof-score repair](../doged-avalanche-proof-score/README.md) targets pinned Doged and is separate from this incomplete ABC port and from Chronik dependencies.

Remaining work includes safe numeric-width integration, historical Dogecoin DAA/subsidy rules, legacy Script behavior, full AuxPoW serialization/validation and disk access, network/genesis identity, and Chronik integration. The 273 unmatched commits with same-subject ABC counterparts require semantic delta review rather than wholesale replay. A complete port needs native builds and independent consensus, synchronization and indexer validation before becoming a maintained/selectable target. Avalanche quorum/finalization requires its own evidence.

Thirteen originally subject-only messages include a labelled maintenance explanation
added on 2026-10-14. Original author/date/subject and source payload bytes remain
unchanged. `manifest.json` retains pre-enrichment metadata hashes and records the
new digests; all 23 intermediate source trees are verified by replay. The added
prose is not presented as original author text or new behavioral validation.
