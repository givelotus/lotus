# Daemon component releases

Namespaced component tags build both supported release targets and publish a
GitHub Release from those same-run artifacts. A pushed component tag is the
publication trigger; no component release has yet been published through it.
Historical `v11.6.0` and `v11.6.1` tags/assets and their workflow remain
immutable. Namespaced tags do not require a major version bump;
for example, a future reviewed maintenance candidate can use `lotusd-v11.6.2`.
Preparing an example version does not schedule or authorize that release.

`daemon/components.json` is the common registry for source pins, native targets,
base build flags, toolchains and component names. The distribution release is
`<component>-v<distributor-version>`; its manifest separately records the upstream
native version, immutable source pin, distributor patch revision, source tree,
normalized archive/build commit, patch hashes, selected features, toolchain
requirements and source archive checksum. A new patch revision needs a new
distributor version before publication because tags are immutable. Native upstream
versions are not bumped to impersonate a newer official upstream release.

| Component | Existing series | Native version at current pin | Default profile | Chronik |
|---|---|---|---|---|
| `lotusd` | `v1` | Prepared Lotus numeric version | maintained | Existing in-process, ON |
| `bitcoin-abc` | `ecash` | 0.34.1 | provider only | Shared Chronik source provider; no network release |
| `bchn` | `bchn` | 29.2.1 | custom Chronik host | In-process ABC Chronik with BCHN adapter |
| `doged` | `doged` | 0.34.1 at ABC `1fb7db17` | maintained 174-patch Dogecoin port | Existing in-process, ON |
| `bitcoin-core` | `bitcoin` | 32.99.0 | custom Chronik host | In-process ABC Chronik with Core adapter |

ABC/BCHN/Doged/Core pins currently represent development snapshots, not assertions
that upstream released those exact commits as stable versions. A future stable
channel must pin and verify an actual upstream release tag/commit separately.
The source registry distinguishes ABC's XEC `bitcoind`, BCHN's BCH `bitcoind`, and
Bitcoin Core's BTC `bitcoind`; executable names alone are not component identities.

## One preparation operation

```sh
python3 daemon/scripts/component-release.py --component bitcoin-core \
  --upstream /path/to/read-only/bitcoin-git --version 1.0.0 --patch-revision 1 \
  --candidate /tmp/bitcoin-core-review

python3 daemon/scripts/component-release.py --component lotusd \
  --upstream /path/to/read-only/abc-git --version 12.0.0 --patch-revision 1 \
  --candidate /tmp/lotusd-review
```

These are distributor-version examples. The candidate destination must be new.
The existing atomic snapshot implementation copies tracked content/local tracked
edits and promotes the complete candidate with one rename. It never copies
ignored workspaces/datadirs or modifies the object-source checkout. Stage new
files before snapshotting. Failure leaves no partially visible candidate.

Each candidate contains `daemon/releases/COMPONENT/{manifest.json,
source-metadata.patch,NOTES.md,Dockerfile}`. The historical Lotus CLI remains
backward compatible; both entry points share replay, snapshot and write helpers.
For Lotus, the component operation delegates version, Arch, container and verified
seed/checkpoint preparation to the existing generator, using namespaced asset URLs.
It accepts the same `--network-input` and explicit `--allow-network-rpc` safeguards.
Absent verified input, network parameters stay unchanged. Other components reject
network-input changes rather than silently importing Lotus chain parameters.

Lotus retains exactly 153 maintained patches, then its replaceable generated
`999-release-metadata.patch` in `v1/series`. The component's generated build-label
adapter follows separately, outside the maintained manifest. Maintained authors,
dates, messages and source patches are preserved. The adapter only scopes build
labels; it is not a consensus change. Source construction verifies native `git am`
replay, retains its complete history on local `replayed-patches`, then selects the
fixed-epoch source commit used by both archives and binary build labels.

Default stock-policy profiles select no experimental policy patches;
only the generated build-label adapter changes their source. Doged's maintained
profile includes its existing build/test compatibility series. Custom features
require `--profile custom`; policy candidates additionally need
`--allow-experimental`. Chronik, NNG, mining and ZeroMQ remain independent. For example:

```sh
python3 daemon/scripts/component-release.py --component bchn \
  --upstream /path/to/bchn --version 29.2.1 --patch-revision 1 \
  --profile custom --features chronik --candidate /tmp/bchn-chronik-review
```

Chronik does not select mining/chain-limit/NNG/ZeroMQ-removal patches. BCHN NNG
selects the reviewed existing FlatBuffers compatibility port only with an explicit
custom profile and experimental opt-in. Its native macOS checks do not establish
Linux package validation; exact component artifact CI is required for publication.
BCHN/Core Chronik host adapters are selected as explicit features. Their
manifests pin the host profile and ABC provider export; release CI exports that
source, verifies the host profile, applies the adapter and runs fresh regtest
behavior checks before packaging. ABC remains the provider and is not a network
release target. The tag workflow refuses manifests without Chronik enabled.

## Validation and publication

Component macOS builds select Xcode16.4 on macos-15. The pinned Bitcoin Core
source requires Xcode command-line tools16.2 or newer; the initial macos-14
AppleClang15 runner failed its aggregate CTAD check. The updated macOS
artifact job passes. Historical Lotus release CI and assets are unchanged.


Commit the reviewed candidate normally, then run artifact-only CI for its exact
commit. The new workflow reads only the requested component's reviewed manifest:

```sh
gh workflow run release-components.yml --repo givelotus/lotus \
  --ref REVIEW_BRANCH -f component=bitcoin-core
```

The macOS arm64 job and the component-specific Linux job fetch only the exact
upstream pin, replay selected patches, verify manifests/archives, build daemon/CLI
and tests, run C++ suites (Rust checks when Chronik is ON), check packaged versions,
and smoke the Linux container without networking. Lotus Linux uses two independent
Guix builders and a byte-for-byte archive comparison; BCHN, Doged and Bitcoin Core
use their native Linux build jobs. macOS libraries are bundled and signed natively.
Artifacts use the same component tag in filenames and carry COPYING, manifest,
release notes, actual compiler/tool versions, binary version output and checksums.
Source archives/checksums are deterministic for source identity; binary
reproducibility, synchronization and host-specific behavior require separate evidence.

For Lotus, the matched Guix Linux archive also produces an amd64 `.deb` and
x86-64 `.rpm`. Release CI verifies install, daemon/CLI version output and package
removal in Ubuntu 24.04, Debian 12 and Fedora 44 containers while checking that
pre-existing node-data directories survive. These packages install binaries and
documentation only; package metadata and container tests are not included in
the independent Guix binary comparison. Other daemon components continue to
publish their native Linux archives until their Guix build paths are validated.

After the reviewed manifest and all required source changes reach `origin/main`,
create and push its exact component tag (for example `bchn-v29.2.2`). The
tag workflow verifies manifest/tag identity, confirms the tagged commit is
reachable from `main`, and refuses a release unless the manifest explicitly
builds Chronik. It builds/tests Linux x86_64 and macOS arm64, smoke-tests the
Linux container, checks both same-run artifact sets and checksums, then publishes
those artifacts, source archive, notes and manifest as one GitHub Release. A
`workflow_dispatch` run remains artifact-only. Existing tags/releases are never
overwritten; use a new distributor version for changes. No container registry
push or production deployment is implied. Lotus releases additionally publish a
`*-guix-source.tar.gz` archive for the exact build-overlay tree beside the normal
component source archive.

`component-release.py --publish` remains an optional stricter preflight helper:
it can require a successful artifact-only run before creating the tag. Direct
tag pushes use the same build/test gates and publish only after those gates pass.

## Current tag readiness

The legacy `v*` workflow remains for Lotus V1. The component workflow publishes
only `lotusd-v*`, `bchn-v*`, `doged-v*`, and `bitcoin-core-v*`. Bitcoin ABC is
the pinned source provider for the BCHN/Core Chronik adapters and is deliberately
excluded from network release tags. Prepared candidates are `lotusd-v11.6.1`,
`bchn-v29.2.1`, `doged-v0.4.1`, and `bitcoin-core-v32.99.0`; tags are immutable,
so use a new distributor version if a candidate changes. No component release
has been published by this workflow. Run artifact-only CI first; successful
artifact-only runs are a useful preflight, but tag CI itself remains the final
publication gate.

## Build-label audit and Guix release path

No production monorepo build consumer derives component versions from `git describe`.
All actual executable consumers in the pinned source trees were inventoried in
[evidence](evidence/component-git-describe-audit-20261014.json). Generated source
adapters scope daemon build-info and inherited Guix/shell release helpers to the
appropriate native tag pattern; Electrum's helper uses its own version pattern.
Core's CMake `GenerateBuildInfo.cmake` is covered. `clientversion.cpp` consumes that
header, otherwise native CMake version plus source hash/export-subst commit; it
never reads monorepo component tags. Vendored secp256k1's already scoped ABI-review
helper is not a release-build consumer and must run against its own library history.
Build materialization uses a private repository with no inherited tags, so old
monorepo `v11` or unrelated Vase/miner tags cannot select native release identity.

The Guix workflow/wrapper is scoped to Lotus. Its build-only overlay is not applied
to ABC/BCHN/Doged/Core. The Lotus tag release calls the workflow with the exact
component manifest, compares two independent binaries, and stages the verified
`lotusd-vVERSION` archive using the same asset naming scheme as the other targets.
The earlier `v11.6.0` run establishes reproducibility for that source only; each
new Lotus tag must pass its own Guix build before publication. The validated Guix
workflow runs directly on hosted Linux runners and does not need a Docker socket.

## Optional BCHN and Bitcoin Core Chronik hosts

The pinned ABC Chronik source now has separately hashed, offline host overlays
for BCHN `abd433abe04f74780744b9eac06731f3690ce68a` and Bitcoin Core
`f13ae519de94394314cd63a27924b0998ac65d45`. Their native patches adapt each
node's block/undo storage and validation lifecycle while keeping Chronik inside
the daemon. They are independent of NNG and mining or mempool policy patches.

Both candidates build and pass fresh macOS regtest behavior. Core covers native
witness bytes/IDs, XOR block and undo storage, reorg/restart/crash recovery and
shutdown. BCHN covers full-script history, opaque CashTokens bytes, spent coins,
conflicts, reorg/restart and WebSocket events; it does not claim semantic
token indexing. Exact limits and commands are in the [Core](../chronik/hosts/bitcoin-core/HOST.md)
and [BCHN](../chronik/hosts/bchn/README.md) host records.

The host profiles have passed local macOS regtest checks. Tag CI additionally
builds both Linux x86_64 and macOS arm64 from the exact manifest, runs each
host's fresh regtest behavior suite and publishes the verified ABC Chronik export
alongside the node source and binaries. Successful tag CI is required before
publication; local host tests do not establish Linux/Windows, mainnet sync,
long-running load or reproducible binary behavior.

## Shared-source provider packaging

The CMake provider verifies the exact pinned Chronik export, native host inputs,
ordered source mailboxes and resulting source hashes before building in a private
copy. BCHN/Core releases include a separate deterministic Chronik source-export
archive and its checksum alongside the node source archive. The reviewed manifest
records the export digest, host profile and adapter hash, and artifact CI checks
them against the pinned provider before building.

## Component-specific Rust selection

Lotus retains its validated Rust 1.93.0 pin. ABC at `1fb7db17` independently uses
1.87.0, the minimum required by its
[CMake Rust helper](https://github.com/Bitcoin-ABC/bitcoin-abc/blob/1fb7db17c176cdea8a2c60d887891589382ee4e3/cmake/modules/RustHelper.cmake).
The older Cargo workspace MSRV 1.80.0 is not the complete host-build requirement.
Strict bridge Clippy fails with 21 generated attribute errors on 1.93 and passes
on 1.87; ABC core's 48 unit and 58 doc tests pass on 1.87. No source bridge
attributes are rewritten to accommodate a different compiler.

CI installs the selected component toolchain, rather than applying Lotus's pin
to every daemon. Existing prepared ABC manifests must be regenerated/reviewed;
source trees and archive hashes stay unchanged when only this toolchain metadata
changes. The independent extracted 14-crate provider build is separate evidence,
not a claim that the full native root workspace was checked here. See
[guard/toolchain evidence](evidence/component-release-guard-rust-20261014.json).
