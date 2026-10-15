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
visits O(n + m) graph elements for n transactions and m dependency edges.
`GetMemPoolParents`/`GetMemPoolChildren` look up `mapLinks`, a `std::map`,
so total expected selection work is O(n log n + m), rather than strictly
linear. Its CTOR sort is O(k log k) for k selected transactions. The stale source comment claiming
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

Independent `04-topological-mempool-check.patch` uses BCHN's existing
entry-ID topology to avoid redundant ancestor walks and dependency retries in
optional consistency checks. A 512-transaction native check visits 130,816
ancestors before and zero afterward, while checking the same 512 entries.
This does not accelerate normal admission: consistency checking is disabled
by default. See [the detailed mempool audit](bchn-mempool-complexity-review.md).

Independent default-OFF `10-nng-interface.patch` now ports the existing evolved
FlatBuffers pub/sub and request/reply interface, plus a separate original Tobias
legacy RPC endpoint including submission. The incompatible raw publisher is
superseded. Native macOS builds and unmodified public consumer/legacy fixture
checks pass; see [the compatibility matrix and validation limits](bchn-nng-flatbuffers.md).
ZeroMQ remains independently disableable using `BUILD_BITCOIN_ZMQ=OFF`; source
removal is a separate optional change.
Chronik is not present in BCHN and would require a substantial independent port.
ABC Avalanche-finalization pruning cannot be transplanted into a node without
that finalization model.

## Validation

Native macOS arm64 configuration and `bitcoind`, `bitcoin-cli`, `test_bitcoin`
builds pass with Qt, ZeroMQ, UPnP, NAT-PMP and manpages disabled. Both executable
version checks report BCHN 29.2.1. The final sibling regression fails two
membership assertions against the unchanged upstream assembler and passes after
the ready-backlog heap change. All native miner tests pass, and `check-bitcoin`
passes 126 separately scheduled suites plus the final aggregate target (127
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

## Composition validation

The current compatible FlatBuffers candidate10 composes with01,04,11 and12 at
the exact acceptance pin. All170 permitted raw application orders pass; all60
complete orders produce source tree `1c5fdb7c8018adbb386a099676fb4b8b80bab5e3`.
Grouping ordered11+12 as one source-removal feature yields64 feature-unit orders.
Patch12 correctly rejects application without11. These order checks prove source
application. The same complete tree separately passes a fresh native build, both
existing NNG consumers and all16 focused mining/mempool cases; see
[combined runtime validation](bchn-combined-features-validation.md). See [current composition evidence](evidence/bchn-compatible-combinations-20261014.json).

The older15-order/126-suite combined evidence at tree
`bf50633c2575549a6b621cff8e70142df901b2f7` used the rejected raw-payload publisher.
Its `interface_nng.py` and mining regtests remain historical evidence and do not
validate the current FlatBuffers consumers or current combined source.
See [historical combined evidence](evidence/bchn-combined-20261014.json).

Select `block-construction`, `mempool-check` and/or `nng` independently through
`feature-plan.py --target bchn --allow-experimental`. For example:

```sh
python3 daemon/scripts/feature-plan.py --target bchn \
  --features block-construction,mempool-check,nng,zeromq-on --allow-experimental
```

NNG explicitly requires protocol opt-in. All candidate dependencies are empty;
none requires another candidate. The default BCHN series remains base-only.
Historical 01/02 are not selectable at the current pin. Optional ZeroMQ source removal is now available as two ordered review patches:
11 changes the build default to OFF while retaining the implementation; 12 then
deletes the interface, source and dependency plumbing. Neither depends on NNG,
mining or mempool changes. This is a deliberate interface/dependency choice,
not a performance claim. See [the removal audit](bchn-zeromq-removal.md).

## Upstream submissions

Two independent merge requests target the audited master revision:

- [MR 2174: ready-child fee priority](https://gitlab.com/bitcoin-cash-node/bitcoin-cash-node/-/merge_requests/2174), source commit `640b8bd1c8e88107421a201828eaaf2b46802b28`.
- [MR 2175: topological consistency checking](https://gitlab.com/bitcoin-cash-node/bitcoin-cash-node/-/merge_requests/2175), source commit `cdc388c7f0ecf3562865143bb85ff03e14d31703`.

Each is one commit directly on `abd433abe04f74780744b9eac06731f3690ce68a`.
Submission exports preserve the implementation and add formatting of new hunks,
wrapped rationale and explicit test plans; mining also explicitly includes
`<algorithm>` in its test file. The focused native mining/mempool suites pass
after this cleanup. The maintained mailbox hashes and combination proofs above
remain scoped to their original exports; they are not claims of byte-identical
submission trees. Neither MR includes NNG or ZeroMQ changes. GitLab CI and
maintainer review remain separate from the local validation.

Initial fork pipelines [2948111374](https://gitlab.com/schancel/bitcoin-cash-node/-/pipelines/2948111374) and [2948111630](https://gitlab.com/schancel/bitcoin-cash-node/-/pipelines/2948111630) failed before creating any jobs. GitLab GraphQL reports: "The pipeline failed due to the user not being verified." This is account verification, not a compiled/test failure; upstream CI remains unvalidated until account verification and a rerun. Do not disable CI or alter the patches to hide this status.
