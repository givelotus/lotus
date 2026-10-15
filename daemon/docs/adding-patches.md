# Adding and updating daemon patches

Run commands below from the monorepo root. A patch is one ordinary Git commit,
exported with `git format-patch` and replayed with `git am`. Its commit body should
explain the problem, the chosen fix, dependencies and validation limits.

## Add a patch

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

The ABC shared-source provider is documented in [the Chronik guide](../chronik/README.md).
BCHN/Core adapter and verified-overlay tooling are still being validated in
isolated branches. Their final profile-manifest generation/replay commands will
be documented with integration; current compilation evidence is not permission
to enable an unfinished profile. Until then, use ordinary committed source
changes and metadata-preserving exports, with separate exact tree evidence for
both sides of the adapter.

See [patch metadata and provenance](patch-metadata.md) for historical recovery
and audit details, and [the support matrix](support-matrix.md) for selectable
features and validation scope.
