# Submodule migration: base-only scaffold

The active migration uses `daemon/sources.json` and exact gitlinks in `.gitmodules`.
`make -C daemon setup SERIES=all` initializes sources only. It never applies a
mailbox, rebases a stack, changes a published source branch, or resets local work.
Use `make -C daemon status` and `make -C daemon source-verify` to check repository
URLs, gitlinks, HEADs and exact trees.

Review the proposed order with `make -C daemon source-plan SERIES=v2`;
`PLAN_ARGS=--commits` lists the individual inputs and `PLAN_ARGS=--json` exports
the full plan. Shared eCash changes target `daemon/ecashd` in
`givelotus/bitcoin-abc`. After review, that exact shared tip is fetched into
`daemon/lotusd` as the parent of the Lotus-only commits. The native stage must
not replay the shared list again. Cross-repository branch updates require
explicit coordination; `rebase.updateRefs` cannot update another repository.

The six source paths are `daemon/ecashd`, `daemon/lotusd`, `daemon/lotusv1`,
`daemon/doged`, `daemon/bitcoincashd` and `daemon/bitcoind`. Builds resolve these
paths and use `daemon/.build/<series>` instead of writing inside the submodules.
Build/run and historical replay/release entrypoints are gated until the relevant
stack is reviewed and promoted. No new stack application command is enabled in
this phase.

Dogecoin has three distinct identities: the original Doged export source,
the historical ABC replay base, and the pinned current ABC master used as the
new replay target. Its 174 exported changes plus retained fixes are pending
review and replay on that new target; the original Doged history stays preserved.

The reviewed source reference has all 378 shared eCash commits; the historical
mailbox export has 377. This is informational archival lag. Normal source
initialization and builds do not read or require patch-series files. V1's generated local release-metadata variant is
also explicitly distinguished from the published source reference. All old
source histories, patch inputs and benchmark identities remain preserved.

Private source clones require credentials with read access to the private
`givelotus` repositories. The optional authenticated source-layout CI job uses
`DAEMON_REPOS_TOKEN`; the ordinary layout tests do not fetch private sources.

## Historical workspace workflow (retained for provenance)

The workflow below describes the pre-submodule manager. Its mutation commands
are disabled by the scaffold guard; it is not the current setup procedure.

# Adding and updating daemon patches

Run commands below from the monorepo root. A patch is one ordinary Git commit,
exported with `git format-patch` and replayed with `git am`. Its commit body should
explain the problem, the chosen fix, dependencies and validation limits.

## Mechanistic Branch-First Workflow (`daemon/scripts/lotus-git.py`)

Subdaemon stacks (`daemon/ecash`, `daemon/v2`, `daemon/v1`, `daemon/doged`,
`daemon/bchn`, `daemon/bitcoin`) are maintained directly as Git branches with
their tip SHAs pinned in `daemon/*-version`—no `.patch` file generation is
needed during normal development:

```sh
# 1. Inspect branch, base, and pin status across all subdaemons:
make -C daemon status

# 2. Initialize workspace Git refs (rebase.updateRefs=true, rebase.autoSquash=true,
#    rerere.enabled=true, base/abc, daemon/ecash, and daemon/v2):
make -C daemon init SERIES=v2

# 3. Iterate using ordinary Git commits (and --fixup commits) in the workspace:
cd daemon/workspace-v2
git add path/to/changed/file
# Either create a new feature commit:
git commit -m "subsystem: describe the change"
# Or create a fixup targeting an earlier commit (by SHA or :/subject-substring):
git commit --fixup <earlier-sha>
cd ../..

# 3b. Non-interactively autosquash all fixup! commits and update daemon/ecash + daemon/v2:
make -C daemon autosquash SERIES=v2

# 4a. If a new commit is chain-agnostic and belongs in the eCash base tier (daemon/ecash),
#     sink it down onto daemon/ecash and replay daemon/v2 on top automatically:
make -C daemon sink-to-ecash COMMIT=HEAD

# 4b. Pin the updated branch SHAs in daemon/*-version and push daemon/* branches:
make -C daemon sync SERIES=v2 PUSH=1

# 5. Extract selected commit(s) onto a clean branch off base/abc for an upstream PR:
make -C daemon extract-pr SERIES=ecash BRANCH=pr/my-feature COMMITS="<sha1> <sha2>"

# 6. Rebase the entire two-tier stack (daemon/ecash -> daemon/v2) onto a new upstream commit:
make -C daemon rebase-upstream SERIES=v2 COMMIT=<sha-or-latest>
```

- **When to use `git commit --fixup <sha>`:** Any time a bugfix, compiler warning fix, test fix, or review refinement belongs to an earlier commit in `base/abc..daemon/ecash` or `daemon/ecash..daemon/v2`. Follow with `make -C daemon autosquash SERIES=v2` (which runs `GIT_SEQUENCE_EDITOR=true git rebase -i --autosquash --update-refs` without opening an interactive editor).
- `make -C daemon sync` verifies linear history and refuses if any unsquashed `fixup!` or `squash!` commits remain.
- If legacy `.patch` files are ever needed for external archival, pass `PATCHES=1` (`make -C daemon sync SERIES=v2 PATCHES=1`).

---

## Legacy Single-Patch Export (`mkpatch`)

Work in a separate monorepo checkout so setup cannot change a running node's
source workspace:

```sh
git worktree add -b my-daemon-change /tmp/lotus-my-daemon-change HEAD
cd /tmp/lotus-my-daemon-change
make -C daemon setup SERIES=ecash
cd daemon/workspace-ecash
# Edit source and run the relevant native tests.
git add path/to/changed/file
git commit
cd ../..
make -C daemon mkpatch SERIES=ecash NAME=05-describe-the-change
```

Replace `ecash` with `v1`, `bchn` or `doged` as appropriate. These are the four
series currently supported by `mkpatch`; Bitcoin Core uses the explicit export
command below. Numbering determines filenames; the `series` manifest determines
application order. Never renumber historical patches merely to close gaps.

The helper exports committed HEAD, retaining its subject, body, author and author
date. It refuses dirty source workspaces, merge commits and existing output
files. It does **not** edit the manifest or commit the monorepo changes.

For a maintained default patch, add its filename to `daemon/patches/<series>/series`
in dependency order. For an optional experiment, keep the default manifest
unchanged and create a separate candidate manifest beside the patch. A reference
series such as eCash or BCHN defaults to upstream alone; silently enabling a new
candidate would change that contract. If the patch depends on another candidate,
apply and commit that dependency first and list both in the candidate manifest.

For another patch destination, export explicitly into a new file:

```sh
# Run inside the isolated source repository; choose an unused destination.
(set -C; git -c format.signature= format-patch --stdout --binary --full-index \
  --no-stat -1 HEAD > /tmp/my-new-patch.patch)
```

Review the exported diff and metadata, then place it in its intended candidate
or host-adapter directory. Do not apply source patches with plain `patch` if you
want to retain their commit metadata.

## Check the complete stack

Record the implementation's source-tree hash with `git rev-parse 'HEAD^{tree}'`.
Replay the proposed manifest against its exact pinned base:

```sh
python3 daemon/scripts/patch-series.py /path/to/isolated/source \
  /absolute/path/to/candidate/series --base FULL_UPSTREAM_SHA --check \
  --expect-tree REVIEWED_IMPLEMENTATION_TREE_SHA
python3 daemon/scripts/check-patch-metadata.py
```

`--check` replays in isolation and leaves the supplied source workspace unchanged.
Matching trees proves the exported stack reproduces the implementation. It does
not prove compilation or behavior: run the affected native tests, build the
selected features, and record what passed against the exact base and tree.
Review and commit the patch, manifest and evidence together in the monorepo.

## Refresh a daemon base

In an isolated Lotus checkout, `make refresh` can resolve the selected
workspace's remote default branch and replay its maintained patch series onto
that immutable tip. It advances the selector file only after the full series
applies successfully:

```sh
make -C daemon refresh SERIES=v1 COMMIT=latest
make -C daemon refresh SERIES=bchn COMMIT=latest
make -C daemon refresh SERIES=bitcoin COMMIT=latest
```

Use `SERIES=ecash` or `SERIES=doged-reference` for those reference stacks.
`COMMIT=<sha-or-tag>` continues to select a specific reviewed upstream revision.
The command does not resolve conflicts, edit patch contents, build, or claim
behavioral compatibility; it leaves the replayed candidate workspace for an
LLM or maintainer to repair and validate. If replay fails, the current selector
stays unchanged and the exact resolved upstream SHA is printed for follow-up.
It does not update component release manifests or the separate shared-Chronik
provider pin. The maintained Dogecoin
on-ABC series is intentionally rejected by this generic refresh because its
per-patch provenance manifest must be regenerated with its new base.

For a shared Chronik refresh, update its independent ABC provider pin and
regenerate the export/lockfile manifests as a separate review candidate, then
rebase and test each host adapter. Do not treat refreshing a node's ABC base as
an automatic Chronik-provider upgrade.

## Change an existing patch

In an isolated source checkout, use interactive rebase to edit the corresponding
commit and replay its descendants. Keep one linear commit per executable manifest
entry. Export the complete resulting stack into a **new** review directory:

```sh
python3 daemon/scripts/export-patch-series.py /path/to/isolated/source \
  /absolute/path/to/series --base FULL_UPSTREAM_SHA \
  --output-dir /tmp/lotus-reviewed-patch-stack
```

Replay that candidate with the tree check above before installing reviewed files.
For message-only changes, every intermediate source tree must stay identical;
update applicable provenance metadata alongside the envelopes. For intentional
source changes, preserve prior evidence as history and record the new trees and
validation rather than relabeling old results.

For V1, `999-release-metadata.patch` is generated release preparation output.
Keep protocol fixes separate from it, and regenerate the complete release
candidate using [release preparation](release-preparation.md). Exporting a patch
alone neither updates packaging nor publishes a release. Existing published tags
and assets are immutable.

## Shared Chronik host adapters

There are two stacks: node-side patches against the exact daemon pin, and
Chronik-side overlays against the exact shared source export. Keep each host's
changes independent of NNG and unrelated policy features. Never modify the
verified pristine export in place; use a separate copy for development.

The ABC shared-source provider and optional [Bitcoin Core](../chronik/hosts/bitcoin-core/HOST.md)
and [BCHN](../chronik/hosts/bchn/README.md) adapters are documented with exact
pins, offline overlay manifests and build/regtest commands. The node-side mailbox
and Chronik-side source overlays are separate commits; the CMake provider verifies
both before compiling. Keep profiles outside default patch series. The component
release builder does not yet package or select the BCHN/Core overlays, so these
native candidates cannot be selected for a component release yet.

See [patch metadata and provenance](patch-metadata.md) for historical recovery
and audit details, and [the support matrix](support-matrix.md) for selectable
features and validation scope.
