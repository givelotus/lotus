# Daemon source stacks

Commits in the `daemon/` submodules are the source. There are no patch files to edit,
and `daemon/patches/` is not used to build or set up anything. Each submodule's pin
lives in `sources.json` and its ancestry in `stack-review.json`; `daemon_sources.py`
writes both, so don't hand-edit them.

## Where things live

| Tier | Checkout | Repository | Branch | Builds on |
|---|---|---|---|---|
| Shared engine (`ecashd`) | `daemon/ecashd` | `givelotus/bitcoin-abc` | `ecashd` | Bitcoin ABC (`upstream` remote) |
| Lotus V2 | `daemon/lotusd` | `givelotus/lotusd` | `main` | The `ecashd` tip |
| Lotus V1 | `daemon/lotusv1` | `givelotus/lotusd` | `lotusv1` | Its own ABC pin, independent of V2 |
| Doged, Core, BCHN | `daemon/doged`, `bitcoind`, `bitcoincashd` | `givelotus/<name>` | `master` | Upstream pins |

Snowstorm is a separate project on `snowstorm/*` branches of `lotusd`. It doesn't go
into either stack unless the owner says so.

## Which tier a change belongs in

- **`ecashd`:** no V2 types or rules, and it stays consensus- and P2P-compatible with
  stock Bitcoin ABC. A change that isn't compatible goes default-off or moves to V2.
- **V2:** anything Lotus-specific: consensus, VM, the native wire format, WebSocket-only
  peering, removals such as ZeroMQ and Qt.
- **Mixed:** split it. The mechanism goes in `ecashd`; the V2 adaptation stays in V2.
  Judge by the code, not the path or subject line.

Most moves to `ecashd` won't need a V2 change, but always restack and build V2 after one.

## Commands

Run from the repository root.

| Task | Command |
|---|---|
| Check everything, including that pins are branch tips | `make -C daemon source-verify` |
| See stack order | `make -C daemon source-plan SERIES=v2 PLAN_ARGS=--commits` |
| Fold `fixup!` commits, restack V2 | `make -C daemon autosquash SERIES=v2` |
| Record new stack tips as pins, restacking V2 | `make -C daemon sync SERIES=v2` |
| Publish | `make -C daemon sync SERIES=v2 PUSH=1` |
| Move a V2 commit down | `make -C daemon sink-to-ecash COMMIT=<sha>` |
| Rebase onto newer ABC | `make -C daemon rebase-upstream SERIES=v2 COMMIT=<sha or latest>` |
| Extract for upstream review | `make -C daemon extract-pr SERIES=ecash BRANCH=upstream/<topic> ONTO=upstream/master COMMITS="<sha>..."` |

After publishing, commit `daemon/sources.json`, `daemon/stack-review.json` and the changed
gitlinks in this repository. Publish source commits before the parent gitlinks.

## Making changes

- Check out the branch from the table in the existing submodule. Don't add worktrees
  or copy patch series unless you truly need isolation, and remove them afterwards.
- A fix to an earlier commit is `git commit --fixup <sha>`, folded with `autosquash`.
  Sync refuses unsquashed fixups. A distinct logical change is a new commit.
- `sink-to-ecash` restores everything if a cherry-pick conflicts. To resolve conflicts,
  cherry-pick by hand in `daemon/ecashd`, then run `sync`, which restacks V2.
- If `sync` or `rebase-upstream` stops on a conflict, resolve it, run `git rebase --continue`,
  then rerun the command. `rerere` is enabled, so repeated conflicts resolve themselves.
- Both tiers build each commit with all targets and run only that commit's new tests.
  Full suites run once, in a sweep after all current work has landed, and failures
  become labelled fixups.
- Performance tools ship in-tree (`src/bench/`, `contrib/bench/<feature>/`), with
  reproduction steps in the commit message.

## Commit identity

Author and committer are always `Shammah Chancellor <shammah.chancellor@notvalid.com>`,
with no Claude or other tool attribution. Messages explain the change to someone outside
this project, so no internal shorthand like "owner30" or checklist IDs.

## How `-s ours` bridges work

Stacks get rewritten, but published branches only fast-forward. Publishing adds
`git merge -s ours <previous published tip>`: same tree, with the old history as second
parent. That keeps old pins reachable and means nobody force-pushes or re-clones.

- Bridges exist only at a stack's tip, and `tip^1` is the top of the linear stack.
- Commit normally. If you commit on a bridged tip, `sync` moves that commit below a new bridge.
- Never run `git rebase` on a bridged tip by hand: it also replays the bridged history
  and stops on conflicts. Use the commands above, or first reset to the stack head.
- Read a stack with `git log --first-parent`. Never force-push `ecashd`, `main` or `lotusv1`.

Bridges make publishing rewrites safe. They don't reduce conflict work in a rebase or backport.

## Where evidence goes

- `daemon/stack-ledger.json`: what happened to each commit that lived outside the pins.
- `daemon/stack-topics.json`: stack commits grouped into reviewable topics.
- `daemon/audit/`: audit reports.
- `daemon/docs/evidence/`: raw benchmark and validation data.
- `~/repos/archive/`: retired checkouts and verified bundles. Nothing there is a working entrypoint.

Never overwrite evidence, published release tags or assets. Don't touch production nodes
or their data; a source change doesn't authorize a deployment.

The current reconciliation plan is `docs/plans/daemon-stack-reconciliation.md`.
