# Miner maintenance

- Keep miner work scoped to this subtree and its dedicated build workflow. The
  current upstream import is `givelotus/lotus-gpu-miner` commit
  `fe049e72ee8481625f72533f7b45727b7a97ba9f`; fetching upstream on 2026-10-14
  found no newer master commit.
- `rust-toolchain.toml` pins Rust 1.99.0 for this component. Do not change the
  global default toolchain or the daemon's separately validated Rust version.
- Preserve Lotus's 160-byte header, layered SHA-256 hashing, metadata/body
  serialization, and `getrawunsolvedblock`/`submitblock` interface. CPU tests
  include the mainnet genesis header obtained by read-only RPC.
- Embed the OpenCL kernel in the Rust library. Installed CLI/GUI executables
  must work without the source checkout or a particular working directory.
- `python3 scripts/package.py` builds native CLI and GUI archives; macOS includes
  an ad-hoc signed `.app`. `--cli-only` omits the GUI. Python 3.12+ runs the
  extraction smoke check, `python3 scripts/check-package.py`. It only invokes
  `--help`, which exits before configuration writes, GPU setup, UI or RPC.
- Preserve dependency author/license metadata and notices in packages. A few
  upstream crates omit license texts: documented supplements come from release
  source; otherwise include the declared standard license and full published
  crate source to preserve notices. Never silently omit unknown licenses.
- Local 2026-10-14 validation used Rust 1.99.0, Apple clang 21, macOS arm64:
  CLI+GUI release builds, workspace tests (5 CPU tests), and Clippy with warnings
  denied passed. The separate compile-only OpenCL test passed on Apple M5 Max.
  Full archive extraction, CLI/GUI `--help`, checksum, and `.app` signature
  checks passed. No live mining, block submission or GUI interaction was tested.
  Linux and macOS Intel builds are provided by `build-miner.yml`; do not claim
  they passed before CI does. Docker is installed locally but its daemon is off.
- Keep the existing GUI API for this reversible toolchain/package repair.
  Upgrading its old eframe major version is separate work. The old `block`
  dependency emits a future-compatibility notice on Rust 1.99, but compiles.
