# Optional ABC-derived mempool diagnostic patches

These three independent git-format-patch files remove redundant ancestor walks
from `CTxMemPool::check`. They do not modify admission, block selection, chain
limits, consensus, Chronik or default checking frequency. Normal mainnet checking
is disabled; test/regtest or explicit `-checkmempool` configurations benefit.

Each source already traverses `mapTx.get<entry_id>()` and asserts every direct
parent's id is smaller than its child's. Induction proves the same inequality
for every ancestor. The old additional traversal visits n(n-1)/2 ancestors on a
chain; deleting it preserves direct graph, scratch UTXO, input-pointer, fee/size
and memory assertions. Unlike BCHN MR !2175, no retry queue needs replacing.
Full checks after each insertion still do aggregate quadratic work.

| Directory | Acceptance source |
| --- | --- |
| `ecash` | Bitcoin ABC `1fb7db17c176cdea8a2c60d887891589382ee4e3` |
| `v1` | Lotus's 153 maintained patches plus generated release metadata on ABC `8c67fe1e85`; base tree `2f67d96795f6c3e6236fbb189838bc28e420a97e` |
| `doged` | Doged `9690833b8b6709b7a7837bc397f0d04bf3b885d1` |

None is included in a default executable series. In particular the Lotus
release manifest and 153+999 source tree remain unchanged. Inspect the opt-in
plan (the planner checks application only; it does not build or apply):

```sh
python3 daemon/scripts/feature-plan.py --target ecash --features mempool-check \
  --allow-experimental --check-workspace /path/to/clean/pinned/abc
```

In a new isolated checkout at the appropriate acceptance source, apply exactly
one directory's mailbox using `git am`. Never use the production workspaces for
this review. Doged's existing Apple arm64 literal-compatibility patch is needed
to compile its upstream test suite; it is separate from this diagnostic patch.

ABC mining 01 and container-test 02 apply independently in either order with
this patch. All Doged compatibility-series combinations/orders apply. ABC
finalized-ancestor candidate 04 edits the ancestor-check block this patch deletes:
combining them needs an explicitly reviewed context adaptation (remove 04's
now-obsolete `CTxMemPool::check` hunk). Neither feature depends on the other;
this known source overlap must not be described as clean raw application. The
submitted 04 mailbox is left unchanged.

Each mailbox includes a native 512-entry repeated-parent-input chain, retained
prefix and empty-pool checks after recursive removal, a diamond, and topological
reinsertion. Reinsertion unit coverage does not establish a full chain reorg.
See `daemon/docs/abc-derived-mempool-diagnostics.md` for measured and native
validation evidence and its limitations.
