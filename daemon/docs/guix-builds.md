# Reproducible Lotus Guix Linux builds

Two independent ephemeral Linux builders produced **byte-identical binary,
debug and source archives** in [run 38672796277](https://github.com/givelotus/lotus/actions/runs/38672796277).
Both completed all 156 C++ check targets, security/symbol checks, and runtime
checks of the extracted daemon, wallet RPC and Chronik. This validates the
explicit source below; it does not publish a release or switch native release CI.

## Exact successful inputs

| Input | Revision or value |
|---|---|
| Monorepo CI ref | `fb1fd86be3912ad089aaee40b85e1f5bc7c3ebfe` |
| Bitcoin ABC base | `8c67fe1e85a602204a2ce65aa3b643469c2c3a1d` |
| Maintained 153-patch source commit in CI | `0bfb677f1da7ad9759518cec245051d5f3fff2bf` |
| Maintained source tree | `73e9db8356d5f9e617f40d4d9228209e117b08f0` |
| Source plus explicit Guix overlay commit | `8b8c7dd668593da16b63f84b11dd5f99476f75fa` |
| Source plus overlay tree | `9a702074ecec997c101cc5e5cdadc68c94a6a757` |
| Source date epoch | `1791962988` |
| Bootstrap Guix client/daemon | `d7dde9c16032d3f6f970135c52d52120e7ba0e75` |
| Compiler environment Guix | `c5eee3336cc1d10a3cc1c97fde2809c3451624d3` |
| Compiler / target libc | GCC 14.3.0 / glibc 2.31 |
| Rust / Python / Clang | 1.93.0 / 3.11.14 / 18 |
| Validated features | Chronik ON, NNG ON, wallet ON; Qt/ZeroMQ/plugins OFF |

The local corrected-series commit `0b7939e926b8353ad09d8edc47f355ddacc30502`
has the same maintained tree; CI replay records its own committer identity.
The separate mailbox under `daemon/candidates/guix` changes build scripts and
dependency compatibility only. It retains the corrected custom mining scheduler.
No consensus, activation, NNG schema or wallet source changes are introduced.

These SHA256 values match on both builders, including the full debug archive:

```text
32bf80c421cb5469b11ff6a6bee32333fddb2c0aa85c1f4e559c712516e80d4a  src/lotus-v11.6.0-source.tar.gz
ea3dce1121c826fd9be32a4fdcfeffa6ebe61421588472d440d162c579ec76b2  x86_64-linux-gnu/lotus-v11.6.0-x86_64-linux-gnu-debug.tar.gz
0b7c3ecd099547605d1ab850bcdbfdca2edc513e485138902855a4140abba5e5  x86_64-linux-gnu/lotus-v11.6.0-x86_64-linux-gnu.tar.gz
```

[Replica a artifacts](https://github.com/givelotus/lotus/actions/runs/38672796277/artifacts/11950524131)
and [replica b artifacts](https://github.com/givelotus/lotus/actions/runs/38672796277/artifacts/11950371672)
contain archives, exact `inputs.txt`, bootstrap channels and full build logs.
The comparison job checks every archive's checksum before comparing manifests.
CI artifact ZIPs also contain runtime logs and therefore are not expected to
have identical ZIP hashes; the three release archives above are identical.

## What was exercised

Both Guix builds compile `lotusd`, `lotus-cli`, `test_lotus`, and all 156
`check-bitcoin` targets. Security and symbol checks pass before packaging.
The archive also retains upstream's headless wallet utility and consensus
library, together with COPYING and a feature-aware README.

Each builder extracts the resulting archive and starts only its own fresh,
disconnected mainnet datadir. Version commands and dynamic library resolution
pass. `verifychain 4 0` succeeds at genesis; a blank watch-only wallet is created,
inspected and unloaded, with private keys disabled. Chronik matches RPC's
160-byte genesis header, merkleized TxId and exact raw transaction bytes. The
node then stops. This is a genesis packaging smoke test, not a new Guix-binary
mainnet synchronization claim.

Downloaded ELF inspection confirms an x86-64 PIE with the conventional
`/lib64/ld-linux-x86-64.so.2` interpreter and no Guix RPATH. `lotusd` dynamically
requires only libgcc_s and system glibc libraries; other dependencies, including
libstdc++, are linked statically. Its highest recorded GLIBC requirement is 2.30.
Runtime checks used Ubuntu 24.04; older distribution runtime coverage remains
separate from the checked glibc 2.31 build baseline.

An independent [native GNU14 probe](https://github.com/givelotus/lotus/actions/runs/38649187619)
also passed daemon/CLI/C++ builds, Rust tests/Clippy and all 156 C++ checks with
these dependency repairs. The actual Guix jobs build Chronik and execute C++
checks; they do not claim a separate Guix `check-crates` run.

## GitHub Actions and release integration

The reproducibility workflow runs on two ordinary ephemeral `ubuntu-24.04` GitHub
Actions runners. Each runner installs the pinned Guix client/daemon and uses Guix's
own isolated build users and build environments. It does not need Docker, a Docker
socket, privileged containers, or access to a developer machine. The workflow
uploads validation artifacts and compares the release archives; it does not publish
a GitHub release.

The component release workflow now calls this workflow for Lotus. Both replicas
materialize the exact reviewed component manifest/tag source, build the tagged
version, and compare binary/debug/source hashes. Only the verified replica is
uploaded as `lotusd-x86_64-linux-gnu`; the release job cannot publish unless that
workflow succeeds. It also includes the exact Guix-adapted source archive and
records both source identities in build info. BCHN, Doged and Bitcoin Core retain
their native Linux build jobs because no Guix build path has been validated for
those projects. The manual component dispatch remains artifact-only.

After the two Guix release archives match, the reusable workflow generates an
amd64 `.deb` and x86-64 `.rpm` from the verified archive and adds package hashes
to build info. Clean-container install, version, removal and data-preservation
smokes run on Ubuntu 24.04, Debian 12 and Fedora 44. The packages install only
the daemon, CLI and documentation; they do not create a service or touch chain
data. Package metadata/container tests are release checks, but the package file
bytes themselves are not covered by the independent Guix binary reproducibility
comparison.

The earlier reproducibility run validated the maintained V1 `v11.6.0` source.
It is evidence for the Guix machinery, not for the `v11.6.1` component package;
the new tag-bound workflow is the check for that exact candidate. Neither flow
needs a Docker socket for Guix. Container smoke runs separately on the hosted
runner after Guix produces the release archive.

## Run on a dedicated Linux builder

Install Guix and its daemon using upstream `contrib/guix/INSTALL.md`. Create a
separate clean source clone and replay the maintained V1 patches there. The
wrapper refuses an existing output directory or tracked source modifications,
clones the input, and applies the explicit candidate mailbox in isolation:

```sh
JOBS=2 daemon/scripts/guix-build.sh /path/to/clean/lotus-source /new/build-a
JOBS=2 daemon/scripts/guix-build.sh /path/to/clean/lotus-source /new/build-b
(cd /new/build-a/output && sha256sum -c SHA256SUMS)
(cd /new/build-b/output && sha256sum -c SHA256SUMS)
diff -u /new/build-a/output/SHA256SUMS /new/build-b/output/SHA256SUMS
```

`FEATURES=chronik,nng-off` uses the existing feature planner; low-level
`LOTUS_CHRONIK` and `LOTUS_NNG` ON/OFF switches are also available. These options
remain independent and never select mining or policy patches. Both ON is the
Guix configuration validated above; other combinations need their own Guix
binary checks. ZeroMQ remains OFF.

The manual `guix-daemon.yml` workflow uses two independent ephemeral Linux
runners, performs the fast dependency/configuration preflight, retains logs and
compares archives. It has read-only repository permissions and artifact uploads,
with no release publication step or tag trigger. The isolated test branch used
a temporary push trigger to test before default-branch workflow registration;
that trigger is absent from the integration candidate. After registration:

```sh
gh workflow run guix-daemon.yml --ref REVIEWED_BRANCH
```

Preserve the exact source commit, overlay, pins and feature values in each
candidate. Source archives are deterministic Git archives and include depends
recipes omitted by upstream CPack. Reproduction uses recorded clean Git inputs;
a standalone source-tarball build without Git metadata is not claimed bitwise
equivalent.

## Build compatibility and trust

This reuses ABC's existing Guix machinery rather than Gitian. Actual cold builds
found the inherited depends parser error and obsolete Savannah channel URL.
The compiler revision is unchanged; it is fetched from Guix's
[canonical Codeberg repository](https://lists.gnu.org/r/guix-devel/2025-05/msg00279.html).
The separately pinned modern bootstrap client/daemon avoids the distro's old
substitute helper and includes the
[July 2026 Guix substitute/pull fixes](https://guix.gnu.org/en/blog/2026/guix-substitute-pull-vulnerabilities/).
Initial OS packages and configured official substitutes remain trusted inputs;
this is not a source-only bootstrap claim.

NNG and FlatBuffers receive explicit target toolchain/prefix arguments. Native
protoc/flatc and secp generators must retain the native toolchain: neither the
shell nor GNU make may export target `CMAKE_TOOLCHAIN_FILE` into their builds.
The actual depends Makefile has an early environment regression gate, and both
native generator versions are checked under Cargo's library environment.

Original dependency archive versions and hashes are retained. Compiler fixes
backport exact original upstream mailboxes: FlatBuffers
`20aad0c41e1252b04c72111c3eb221280a9c2009`, and Boost.Math
`f51e1b985de4d739a9f40d8c2b90debd419da267` plus
`b3a21bcbcbd95c23da594ff53c3a48e38f0ff9f3`. All existing intmath tests remain.

Rust uses SHA256-pinned Rustup 1.28.2, then the versioned binary Rust 1.93.0
toolchain; Cargo dependencies are locked. Network access remains enabled as in
upstream. This does not claim a source-bootstrapped Rust compiler or prefetching
all network inputs into Guix fixed-output derivations. Guix substitutes retain
the installer's configured signing-key trust policy.

## Promotion and platform limits

The Guix overlay remains an explicit build-only patch, separate from the
component's maintained patch series. Release metadata records the component
source tree; build info and the additional adapted-source archive record the
overlay result. Do not fold the overlay into the consensus patch series or apply
it twice. The workflow does not retag existing versions or modify working
nodes/data.

Only `x86_64-linux-gnu` is enabled. Upstream explicitly marks ARM macOS cross
compilation TODO; Intel macOS additionally requires a separately supplied,
appropriately licensed Xcode SDK. No Apple SDK is committed or uploaded. Native
macOS release builds remain in place. The Doged candidate at ABC `33ae885a`
inherits ABC's `contrib/guix` machinery and passes native macOS build, unit, and
selected functional checks, but that exact Doged candidate has not been built
or compared in Guix. Doged's current release manifest still selects historical
source `9690833b`. Bitcoin Core `f13ae519` also contains upstream Guix build
machinery, but its recipe has not been adapted and validated with the component
manifest, Chronik settings, and release packager. No BCHN Guix release path has
been validated at its current pin; do not infer that BCHN lacks a recipe from
this audit. Keep those components on their native Linux jobs until each exact
release candidate passes its own Guix build, packaging, and behavior checks.
Lotus validation does not transfer across daemons.
