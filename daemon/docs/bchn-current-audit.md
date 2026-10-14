# Current BCHN candidate audit

The acceptance base is GitLab `bitcoin-cash-node/bitcoin-cash-node` master
`abd433abe04f74780744b9eac06731f3690ce68a` (29.2.1), resolved from both
HEAD and refs/heads/master on 2026-10-14. Subsequent validation uses that exact
commit, never a moving master reference. Earlier v28 results are historical.

## What current BCHN already implements

The current daemon does not maintain transitive ancestor statistics on admission.
`CTxMemPool::addUnchecked` indexes inputs, deduplicates direct parent TxIds and
updates direct parent/child links. Historical commit `0ce476c4a251` removed
ancestor/descendant statistics in April 2021; `44150d7ed46` removed ancestor
limits in May 2021. Reorg handling reconstructs topological order. Therefore
an unchecked-container test is not a missing chain-limit policy fix, and neither
an O(1) admission claim nor an O(n²) admission claim follows from the old patch.
Input hashing, signature validation, ordered indexes and input count still cost
work; constant time per arbitrary transaction is not claimed.

The current `BlockAssembler::addTxs` already visits its fee index and handles
missing direct parents using a count. Every successfully selected parent visits
its direct children once. Each skipped transaction enters the FIFO backlog at
most once. Ignoring hash collisions and per-transaction validation, selection
has expected O(n + m) work for n transactions and m dependency edges. Its CTOR
sort is O(k log k) for k selected transactions. The stale source comment claiming
ancestor-package feerates does not match the implementation: below-minimum-fee
parents prevent inclusion of their paying children. Existing tests explicitly
require this policy. It must not be silently replaced with CPFP.

## Scoped improvements

A ready heap is useful to prioritize newly eligible siblings by modified feerate
under limited block capacity, rather than arbitrary FIFO child iteration order.
That is a fee-selection behavior improvement, not proof of a speedup over BCHN's
already nonquadratic scheduler. Preserve BCHN ABLA resource limits, virtual-size
fee comparison, topology tie breaks, time budget, finality and termination
heuristics. The native before/after reproduction below validates this change.

Separate workers are examining the optional NNG transport and diagnostic
mempool-check traversal. ZeroMQ is already independently disableable using
`BUILD_BITCOIN_ZMQ=OFF`; source removal must remain a separate optional change.
Chronik is not present in BCHN and would require a substantial independent port.
ABC Avalanche-finalization pruning cannot be transplanted into a node without
that finalization model.

## Validation

Native macOS arm64 configuration and `bitcoind`, `bitcoin-cli`, `test_bitcoin`
builds pass with Qt, ZeroMQ, UPnP, NAT-PMP and manpages disabled. Both executable
version checks report BCHN 29.2.1. The final sibling regression fails two
membership assertions against the unchanged upstream assembler and passes after
the ready-backlog heap change. All native miner tests pass, and `check-bitcoin`
passes 125 separately scheduled suites plus the final aggregate target (127
Ninja steps). Isolated `mining_basic.py` and `mining_prioritisetransaction.py`
regtests pass, covering template/submission and fee-delta behavior.

The single mailbox replays with `git am` on the exact acceptance base to tree
`87c828255f2809bf1ffb671ec065c993fa517ec1`, identical to the tested source.
The new patch is independently selected by `block-construction`; default setup
remains base-only. The historical broken transitive-package patch is retained
for provenance and is no longer selected. No wall-clock comparison, mainnet
synchronization or reproducible binary claim is made. See
[evidence](evidence/bchn-current-20261014.json) for patch hash and log paths.
Production nodes/data and published releases are untouched.

## Review application

The feature planner reports patch files and dependencies; `make build` does not
apply experimental patches. Use a new checkout and the pinned SHA, then apply
only the independently selected mailboxes with `git am`:

```sh
git clone https://gitlab.com/bitcoin-cash-node/bitcoin-cash-node.git /tmp/bchn-review
git -C /tmp/bchn-review checkout --detach abd433abe04f74780744b9eac06731f3690ce68a
git -C /tmp/bchn-review am "$PWD/daemon/patches/bchn/01-prioritize-ready-transactions.patch"
cmake -S /tmp/bchn-review -B /tmp/bchn-review-build -GNinja \
  -DBUILD_BITCOIN_QT=OFF -DBUILD_BITCOIN_ZMQ=OFF -DENABLE_MAN=OFF \
  -DENABLE_UPNP=OFF -DENABLE_NATPMP=OFF
ninja -C /tmp/bchn-review-build bitcoind bitcoin-cli test_bitcoin check-bitcoin
```

These commands assume the current directory is the Lotus monorepo. Use fresh
paths rather than resetting an existing node workspace. The feature planner's
`--check-workspace` mode verifies clean application using a temporary index,
without applying patches to the source checkout.
