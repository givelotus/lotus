# Daemon component releases

This is reviewable build/release infrastructure. No component release has been
published through it. Historical `v11.6.0` and `v11.6.1` tags/assets and their
workflow remain immutable. Namespaced tags do not require a major version bump;
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
| `bitcoin-abc` | `ecash` | 0.34.1 | stock | Existing in-process, explicit opt-in |
| `bchn` | `bchn` | 29.2.1 | stock | Port absent; selection rejected |
| `doged` | `doged` | 0.4.0 | maintained compatibility/test patches | Existing in-process, explicit opt-in |
| `bitcoin-core` | `bitcoin` | 32.99.0 | stock | Port absent; selection rejected |

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

Default stock-policy ABC/BCHN/Core profiles select no experimental policy patches;
only the generated build-label adapter changes their source. Doged's maintained
profile includes its existing build/test compatibility series. Custom features
require `--profile custom`; policy candidates additionally need
`--allow-experimental`. Chronik, NNG, mining and ZeroMQ remain independent. For example:

```sh
python3 daemon/scripts/component-release.py --component bitcoin-abc \
  --upstream /path/to/abc --version 1.0.0 --profile custom --features chronik \
  --candidate /tmp/abc-chronik-review
```

Chronik does not select mining/chain-limit/NNG/ZeroMQ-removal patches. BCHN NNG
selects the reviewed existing FlatBuffers compatibility port only with an explicit
custom profile and experimental opt-in. Its native macOS checks do not establish
Linux package validation; exact component artifact CI is required for publication.
BCHN/Core Chronik and Core NNG fail closed;
that is a temporary implementation boundary, not completion of the BTC Chronik goal.

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

Both macOS arm64 and Linux x86_64 jobs fetch only the exact upstream pin, replay
selected patches, verify manifests/archives, build native daemon/CLI and tests,
run C++ suites (Rust checks when Chronik is ON), bundle/sign macOS libraries,
check packaged native versions, and smoke the Linux container without networking.
Artifacts use the same component tag in filenames and carry COPYING, manifest,
release notes, actual compiler/tool versions, binary version output and checksums.
Source archives/checksums are deterministic for source identity; binary
reproducibility, synchronization and host-specific behavior require separate evidence.

After the final reviewed commit reaches `origin/main` and its exact component
artifact run passes, the separate publication operation verifies canonical origin
fetch/push URLs, exact clean commit, matching successful manual workflow, matching
component artifact manifest, and absence of the new tag:

```sh
python3 daemon/scripts/component-release.py --component bitcoin-core \
  --upstream /path/to/bitcoin --publish --reviewed-commit FULL_SHA \
  --validation-run RUN_ID
```

It creates/pushes one new annotated component tag. Tag CI rebuilds/tests both
platforms, independently downloads the expected component artifact from the
recorded validation run and compares its manifest bytes to current main, refuses
an existing release, and publishes component assets/checksums/notes. Manual runs
never publish; no container registry push or production deployment is implied.

## Build-label audit and Guix boundary

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

The experimental Guix workflow/wrapper remains separately scoped to Lotus and
unchanged. Its build-only overlay is not applied to ABC/BCHN/Doged/Core. Current
Guix `lotus-vVERSION` filenames are not component publication assets; adopting the
registry/archive names there requires coordinated wrapper/archive lookup work
and completed Guix validation. No binary reproducibility claim is added here.

## Bitcoin Core Chronik work remaining

The pinned Core source genuinely builds BTC `bitcoind`/`bitcoin-cli`, but contains
no Chronik CMake target/bridge. Modern ABC's Rust `TxMut` lacks Bitcoin witness
data, and Chronik's protobuf lacks witness/wtxid fields. A real Core integration
needs SegWit-aware transaction parsing/serialization, distinct txid/wtxid handling,
script indexing and native validation/storage/reorg/mempool adapters. Optional
in-process Chronik extracted from pinned ABC source is the current direction;
NNG is independent and is not its dependency. See the
[host-boundary audit](shared-chronik-source-and-hosts.md) for shared source/lifetime
obligations; its earlier standalone-NNG recommendation is historical and has
been superseded by the user's in-process direction.

## Optional extracted-source provider extension

The current implementation builds the host's embedded Chronik, whose complete
source is already in the exact source archive. The separate pinned extraction
candidate is not silently enabled by these release profiles. When integrated,
the component manifest must additionally identify provider revision/tree,
export-manifest SHA256, host-adapter patch hashes and chain profile. Its verified
exported sources and lockfile must be included in the offline source archive;
a remote pin alone is insufficient. `CHRONIK_SOURCE_DIR` and
`CHRONIK_PROVIDER_MODULE` must then resolve only to those verified local inputs.
Keep unsupported host profiles closed until their real bridge is validated.

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
