# Preparing a Lotus mainnet release

`daemon/scripts/prepare-release.py` assembles the daemon version, Arch recipes,
container inputs, optional fixed seeds/checkpoints, and a source-tree manifest
in one review candidate. Preparation never changes a running daemon, a datadir,
a published tag, a release asset, or a container registry.

The current baseline retains its 153 historical patches. The generator adds a
single **candidate-only** `999-release-metadata.patch` after the maintained
series. Subsequent preparations replace this generated tail; they do not append
one patch per version or rewrite historical patch 247. Future feature fixes can
use 248 onward. The generated patch comes from `git format-patch`, supports
`git am`, and uses a documented constant artifact epoch for reproducibility.

## One operation, one isolated candidate

Use an existing local ABC Git repository only as a read-only object source. It
must contain the exact commit in `daemon/bitcoin-abc-v1-version`:

```sh
python3 daemon/scripts/prepare-release.py \
  --upstream /tmp/rebase-latest-abc --version 11.6.1 \
  --candidate /tmp/lotus-release-11.6.1
```

The destination must not exist. The tool snapshots tracked content, including
local tracked edits, into a private Git clone; it excludes ignored daemon
workspaces and untracked files. It replays the exact series into a private object
database/index, generates metadata, verifies the result again, and promotes the
entire candidate with one directory rename. Failed preparation leaves no partial
candidate. Do not point the destination at an existing checkout or datadir.
Uncommitted *untracked* feature files must be tracked before preparing a candidate.

No mode flag means a read-only drift report. `--check` fails on drift. `--write`
updates an already isolated candidate with staged writes and rollback on ordinary
errors; it is not crash-atomic across files. Use `--candidate` for atomic visibility
of a complete directory. Preparation and replay are not compilation or consensus
validation.

The manifest records the exact upstream commit, every patch's SHA256, version,
and final source tree. Version changes update CMake, both Arch recipes, container
instructions, the release-version label, and the release strategy label when
present. Historical `lotusd-version` and `ecash-version` remain explicitly labeled
historical references, not additional release authorities.

## Network inputs

By default, existing network parameters remain unchanged. An existing
`daemon/release-network.json` is revalidated offline and reproduced. To refresh
seeds and/or checkpoints, add `--network-input /path/to/reviewed-input.json` to the
same candidate operation. Checkpoint RPC additionally requires
`--allow-network-rpc`. See [network input schema and verification](../NETWORK-RELEASE.md).

Reuse is deliberately selective: fixed seeds use the replayed
`contrib/seeds/generate-seeds.py`. The inherited `update-seeds.sh` starts/builds
nodes and commits changes, so it is not executed against an operational checkout.
`update-electrum-checkpoints.sh` queries eCash Electrum servers and modifies
Electrum application checkpoints; those are not Lotus daemon checkpoints.
The inherited `contrib/release/github-release.sh` still targets Bitcoin ABC API
endpoints and GUIX artifacts; the maintained GitHub workflow replaces that path.
Release-note archiving is left to explicit editorial review; the inherited
recipe reads ABC notes and is not blindly run as a Lotus release-note generator.

## Packaging and validation

The generated source archive is the replayed **daemon tree**, not a GitHub
monorepo tag tarball. Its top directory is `lotus-vVERSION/`; Arch and Docker
references use the same label. Arch recipes now use shared `contrib/aur/common`
inputs and current CMake flags. Their install hook preserves the service account
and blockchain on uninstall. Source tarballs are checked against release
`SHA256SUMS` during Arch preparation; the PKGBUILD cannot embed its own containing
archive's digest without a circular dependency. Copy the entire `contrib/aur`
directory when building, including `common`. Python 3.13 at
`/usr/bin/python3.13` and Rust 1.93.0 are required. Full Arch builds and Qt are
**not validated** by the binary release matrix.

Prepared containers consume the Ubuntu 24.04 Linux binary archive and use the
same distribution ABI. Release CI builds the image and runs daemon/CLI version
checks with networking disabled. That is a packaging/linkage check, not a
synchronized container-node test. No container image is pushed automatically.
Operators can build/push a reviewed image separately with the documented tag.

CI runs release-tool synthetic tests, builds daemon/CLI with Chronik, runs C++
and Rust checks, packages binaries plus COPYING and source, signs/rechecks macOS
bundled binaries, and checks packaged version output. With a manifest it verifies
reproducibility before compilation. Historical baseline builds without a
manifest export their actual replayed source and do not claim generated Arch or
container validation. All artifact-only dispatches leave releases unchanged.

Run local tooling checks with:

```sh
python3 -m unittest discover -s daemon/scripts -p test_prepare_release.py -v
python3 -m unittest discover -s daemon/tests -p test_prepare_network_release.py -v
```

Tests cover rejected inputs, read-only preparation, failed writes and candidate
rollback, deterministic archives, `git am` source-tree identity, network/genesis
scoping, checkpoint reorg/depth checks, and immutable tag publication preconditions.
No live node is contacted by these tests.

## Review and publication

Review the entire candidate diff, manifest, package recipes and selected network
evidence. Build/test it in a separate workspace and datadir. In particular, the
current mining/transaction-chain feature audit has identified correctness issues;
a metadata candidate does not resolve or waive those findings. Preserve any
existing release while fixes and behavioral checks remain outstanding.

Commit reviewed candidate changes and merge them normally. Run artifact-only CI
against that exact commit, then inspect/download checksums and packaged binaries:

```sh
gh workflow run release-daemon.yml --repo givelotus/lotus --ref REVIEW_BRANCH
```

After the same exact reviewed commit reaches `origin/main`, publication is an
explicit separate operation, requiring the successful artifact-only validation
run for that commit:

```sh
python3 daemon/scripts/prepare-release.py --upstream /path/to/isolated/abc \
  --publish --reviewed-commit FULL_40_CHARACTER_COMMIT --validation-run RUN_ID
```

This rechecks generated metadata, clean checkout, exact remote main, and CI
identity/success. It creates and pushes a **new** annotated tag; tag CI rebuilds,
checks, and publishes assets. Existing local or remote tags are refused, so this
operation cannot republish `v11.6.0`. Do not delete a tag to bypass this check.
A transport error may leave a local tag: reconcile the remote before retrying.
Publication is not deployment; replacing the production executable is separate.
