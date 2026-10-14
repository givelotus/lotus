# Lotus Guix build candidate

This work is isolated from published releases and the maintained 153-entry V1
series. The existing native release workflow stays in place until independent
Guix builds pass and their archives match. No Gitian installation is used here.

## Inputs and design

Reuse the actual `contrib/guix` machinery in pinned Bitcoin ABC
`8c67fe1e85a602204a2ce65aa3b643469c2c3a1d`, after the maintained V1 patches.
The underlying Guix time-machine revision is
`c5eee3336cc1d10a3cc1c97fde2809c3451624d3`. Its manifest supplies GCC 14,
Clang 18, Python 3.11 and Linux cross-toolchains. Existing hash-checked depends
recipes supply Python 3.12.7, NNG 1.5.2 and Flatbuffers 2.0.0.

The separate mailbox patch in `daemon/candidates/guix` repairs an inherited
missing `endif` in `depends/Makefile`, explicitly passes the depends toolchain
to NNG/Flatbuffers, selects the validated Rust 1.93.0 instead of upstream
1.87.0, and builds headless Lotus daemon and CLI. C++ suites, security checks,
and symbol checks precede packaging. Archives contain upstream COPYING.

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
`LOTUS_CHRONIK=OFF` and `LOTUS_NNG=OFF`. Both default to ON.

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

Initial CI proved Ubuntu's packaged Guix installs and its daemon is reachable,
and exposed the inherited depends parser failure. Subsequent candidate runs
are still pending; there is no successful Guix Lotus binary or reproducibility
claim yet. Record exact successful run IDs and artifact hashes here before
promoting this path into a release workflow.
