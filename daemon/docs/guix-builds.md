# Lotus Guix build candidate

This work is isolated from published releases and the maintained 153-entry V1
series. The existing native release workflow stays in place until independent
Guix builds pass and their archives match. No Gitian installation is used here.

## Inputs and design

Reuse the actual `contrib/guix` machinery in pinned Bitcoin ABC
`8c67fe1e85a602204a2ce65aa3b643469c2c3a1d`, after the maintained V1 patches.
The CI bootstrap manager and daemon are separately pinned by
`daemon/guix-bootstrap-version` to authenticated canonical Guix commit
`d7dde9c16032d3f6f970135c52d52120e7ba0e75` (2026-10-08). Ubuntu's packaged
1.4.0 client/daemon is only the initial bootstrap. CI upgrades the root profile
and explicitly points its ephemeral service at the new daemon, because merely
running time-machine left `/usr/bin/guix substitute` active and both first
workers failed after compiling the toolchain. GNU documents the foreign-distro
root-profile upgrade and its July 2026 substitute/pull fixes in the
[official advisory](https://guix.gnu.org/en/blog/2026/guix-substitute-pull-vulnerabilities/).
The initial OS package and official substitutes remain trusted bootstrap
inputs; this is not a source-only bootstrap claim.

The underlying Guix time-machine revision is
`c5eee3336cc1d10a3cc1c97fde2809c3451624d3`, fetched from the project's
[canonical Codeberg repository](https://lists.gnu.org/r/guix-devel/2025-05/msg00279.html).
The obsolete Savannah URL returned HTTP 500 in the actual CI attempt; the
revision pin and Guix authentication remain unchanged. Its manifest supplies GCC 14,
Clang 18, Python 3.11 and Linux cross-toolchains. Existing hash-checked depends
recipes supply NNG 1.5.2 and Flatbuffers 2.0.0. Chronik plugins remain OFF,
matching native defaults; the manifest's Python 3.11 supplies build scripts. The
existing CPython 3.12.7 recipe remains available for optional plugin work but is
not built or linked by this configuration.

The separate mailbox patch in `daemon/candidates/guix` repairs an inherited
missing `endif` in `depends/Makefile`, explicitly passes the depends toolchain
to NNG/Flatbuffers, selects the validated Rust 1.93.0 instead of upstream
1.87.0, and builds headless Lotus daemon and CLI while retaining built-in wallet RPC
support through the existing Berkeley DB and SQLite depends recipes. C++ suites, security checks,
and symbol checks precede packaging. Archives contain upstream COPYING and a brief usage README. Source archives
use deterministic git archive and include the depends recipes omitted by
upstream CPack packaging. Filenames and top-level directories use
`lotus-vVERSION`, matching native release naming. Reproducing binaries still
uses the recorded clean Git commit and Guix recipe; a standalone source-tarball
build without Git metadata is not claimed bitwise equivalent.

Chronik and NNG use separate ON/OFF switches and do not select mining or policy
patches. No consensus changes are introduced by this overlay. The wrapper
records the input and adapted commits, trees, features and source epoch.
The source archive includes the adaptations, so it is a different source tree
from the native candidate before these build repairs are integrated.

The upstream implementation downloads a SHA256-pinned Rustup 1.28.2 bootstrap,
and Rustup downloads the versioned binary Rust toolchain. Cargo dependencies
are locked by Cargo.lock. Network access inside the build container remains
enabled, as in this upstream revision. This is therefore not a claim that the
Rust compiler was bootstrapped from source or that all network inputs were
prefetched into Guix fixed-output derivations. Guix substitutes remain subject
to the installer's configured signing keys and trust policy.

## Run on a dedicated Linux builder

Install Guix and its daemon using the upstream `contrib/guix/INSTALL.md`
instructions. Do not run setup against an existing production workspace.
Create a separate source clone and replay the maintained patches there, then:

```sh
JOBS=2 daemon/scripts/guix-build.sh /path/to/clean/lotus-source /new/build-a
JOBS=2 daemon/scripts/guix-build.sh /path/to/clean/lotus-source /new/build-b
(cd /new/build-a/output && sha256sum -c SHA256SUMS)
(cd /new/build-b/output && sha256sum -c SHA256SUMS)
diff -u /new/build-a/output/SHA256SUMS /new/build-b/output/SHA256SUMS
```

The build directory must not exist, and the input source must have no tracked
modifications. The wrapper clones it, applies the mailbox with a deterministic
committer date, and never changes the input checkout. Optional selectors:
`FEATURES=chronik,nng-off` uses the same feature planner as native builds.
The low-level `LOTUS_CHRONIK` and `LOTUS_NNG` ON/OFF switches also remain
available; both default to ON and explicit FEATURES takes precedence. Policy
patch selection and unsupported build options fail closed. ZeroMQ remains OFF.

`guix-daemon.yml` uses two independent ephemeral Ubuntu runners and compares
archive SHA256 hashes. It only uploads CI artifacts; it cannot publish a GitHub
release. The temporary branch push trigger allows testing the candidate before
integrating a default-branch manual workflow. Do not infer success from a
reproducible source archive: the two binary archive builds must finish and
match too.

## Platform and validation boundaries

The candidate deliberately rejects hosts other than `x86_64-linux-gnu`.
Upstream's Guix script explicitly marks ARM macOS cross-compilation as TODO.
Intel macOS additionally needs a separately supplied, appropriately licensed
Xcode SDK. No Apple SDK is included, uploaded, or implied by Linux validation.
Native macOS release builds remain the current path.

The initial tooling runs use source tree
`e0d4f9c0219739b6774864858c582a8144a443d9`, which temporarily restored the
upstream block assembler. That source has been superseded by work to repair and
retain Lotus's custom assembler. These running jobs remain useful for Guix
toolchain/build diagnosis. They use wallet-OFF; final builds retain the native
release's wallet-ON setting. They cannot validate or publish the final custom
assembler. Final binary comparisons must replay the corrected V1 series and
record its new source provenance.

Initial CI proved Ubuntu's packaged Guix installs and its daemon is reachable,
and exposed the inherited depends parser failure and obsolete Savannah channel
URL (HTTP 500 after all depends source hashes passed). The next attempt built pinned Guix and the custom Linux toolchain, then a
substitute subprocess failed with a TLS write/push error during final environment
creation. CI now provisions the same FHS container environment in a separate
step with three bounded attempts, preserving its store between transient
failures. Subsequent candidate runs
are still pending; there is no successful Guix Lotus binary or reproducibility
claim yet. Record exact successful run IDs and artifact hashes here before
promoting this path into a release workflow.

## Tooling attempt evidence

- [38591918734](https://github.com/givelotus/lotus/actions/runs/38591918734):
  Ubuntu Guix installation and daemon access passed; depends parsing exposed the
  missing `endif`. Explicit Bash pipefail now prevents `tee` from masking the
  build command's failure.
- [38592500393](https://github.com/givelotus/lotus/actions/runs/38592500393):
  depends source hashes passed; obsolete Savannah channel fetching failed with
  HTTP 500. The unchanged revision was independently fetched from Codeberg.
- [38593484610](https://github.com/givelotus/lotus/actions/runs/38593484610),
  source branch commit `d4b7fd6d`: worker a built pinned Guix and the custom GCC
  14.3/glibc 2.31 toolchain, then its substitute subprocess failed with a TLS
  push/write error at 16:55 UTC. No Lotus compilation or binary archive passed
  on that worker. Worker b likewise built the toolchain and then reported that the substitute
  subprocess died. Both workers stopped before compiling Lotus.

These attempts use the superseded source and wallet-OFF configuration described
above. They are build-tooling evidence, not release readiness evidence.

The next isolated attempt uses the independently verified corrected custom
assembler from review commits `236f6870` and `48a85cda`: all153 patches replay
to source `0b7939e926b8353ad09d8edc47f355ddacc30502`, tree
`73e9db8356d5f9e617f40d4d9228209e117b08f0`. This source is copied only to the
Guix candidate branch; its main-branch promotion remains separate. The next
attempt also upgrades the actual daemon/helper, retains wallet support, and
disables unused plugin/CPython builds. Binary validation remains pending.

Bootstrap upgrade attempt `38609545611` authenticated and installed the pinned
`d7dde9c1` client and daemon. Its first readiness check caught Ubuntu's builder
group spelling (`_guixbuild`, not the shell installer's `guixbuild`); the service
override now preserves that existing distro group. No Lotus source compilation
was reached on that failed worker.
