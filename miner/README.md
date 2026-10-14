# Lotus GPU Miner

A solo miner for Lotus (XPI) using OpenCL and a local `lotusd` JSON-RPC server.
The CLI and optional desktop GUI share the same mining library. They use Lotus's
160-byte block headers and `getrawunsolvedblock`/`submitblock` RPCs.

## Build

Install [Rust with rustup](https://rustup.rs/) and your platform's native C/C++
build tools. Run commands from `miner/`. The scoped `rust-toolchain.toml` selects
Rust **1.99.0**, the current stable release on October 14, 2026; it does not change
the daemon's toolchain. `Cargo.lock` pins dependency versions.

- **macOS:** install Xcode Command Line Tools (`xcode-select --install`). Linking
  uses Apple's system OpenCL framework. OpenCL is deprecated on macOS; supported
  devices depend on the installed OS/hardware.
- **Linux (Debian/Ubuntu):** install `build-essential pkg-config
  ocl-icd-opencl-dev libssl-dev`, plus your GPU vendor's OpenCL ICD/runtime. The
  optional GUI also needs `libx11-dev libxcb-shape0-dev libxcb-xfixes0-dev
  libxkbcommon-dev libwayland-dev libgl1-mesa-dev`.
- **Windows:** install the MSVC Rust toolchain, Visual Studio C++ build tools,
  and your GPU vendor's OpenCL SDK/runtime. Windows packaging is not implemented.

```sh
cargo build --locked --release -p lotus-miner-cli
cargo build --locked --release -p lotus-miner-gui   # optional desktop GUI
cargo test --locked --workspace
```

The binaries are `target/release/lotus-miner-cli` and
`target/release/lotus-miner-gui` (with `.exe` on Windows). The mining kernel is
embedded in the library, so the executable works from any directory.

## Configure and run

Run a synced mainnet `lotusd` with JSON-RPC enabled. Its default RPC port is
**10604** (10605 is the peer-to-peer port). Copy `config.example.toml` to
`~/.lotus-miner/config.toml`, set your own `lotus_` payout address and the RPC
credentials configured on your node, then run:

```sh
./target/release/lotus-miner-cli --config "$HOME/.lotus-miner/config.toml"
./target/release/lotus-miner-cli --help
```

Command-line settings override the TOML file. The miner supports HTTP Basic
RPC credentials; it does not currently read the node's cookie file. GPU indices
count devices across all OpenCL platforms, starting at zero. `kernel_size` is
a base-two exponent for the OpenCL work size; lower it if your driver cannot
allocate or run the default workload.

## Package the CLI and desktop GUI

On native macOS or GNU/Linux, Python 3 and the build prerequisites above are
sufficient:

```sh
python3 scripts/package.py
```

This builds with `--locked --release` and creates
`dist/lotus-miner-0.3.0-<host>.tar.gz` plus a SHA-256 checksum. macOS
includes an ad-hoc signed `Lotus GPU Miner.app`; Linux includes
`bin/lotus-miner-gui`. Use `python3 scripts/package.py --cli-only` to omit
the desktop GUI. The archive also contains `bin/lotus-miner-cli`,
configuration/documentation, the miner license,
dependency license texts and author metadata, `DEPENDENCIES.json`, and
toolchain build information. Crates that omit dedicated license files include
their declared standard license and complete published source to preserve
notices. Extract it and run `bin/lotus-miner-cli --help` from any directory.
No source-tree or external kernel files are required. The archive remains
native to its build host; Linux glibc/OpenSSL and the OpenCL loader/driver are
system dependencies, and macOS uses system frameworks. Build on the oldest
Linux distribution you intend to support. GPU vendor runtimes are not bundled.
Unknown licenses without supplied texts stop packaging. The macOS app is not
notarized; downloaded builds require the normal macOS approval for unsigned
software. Only system frameworks are linked on macOS; no private dynamic
libraries are required. Python 3.12+ can verify extraction, signatures, checksums
and both binaries from a separate directory without starting mining:

```sh
python3 scripts/check-package.py
```

`.github/workflows/build-miner.yml` provides manual/PR checks and native archive
artifacts for Linux x86_64 and macOS arm64/x86_64. It does not publish a release.

## Validation and provenance

This subtree was imported from `givelotus/lotus-gpu-miner`, upstream commit
`fe049e72ee8481625f72533f7b45727b7a97ba9f` (June 7, 2023), still upstream's
latest `master` at review on October 14, 2026. Local changes update the scoped
Rust toolchain, refresh compatible dependencies, fix a current-Rust compilation
error in the old CLI author macro, and repair packaging. The GUI framework
remains on its existing API; a major UI framework migration is separate work.

Tests cover Lotus hashing (including the live mainnet genesis header), preserving
header/body metadata boundaries, target byte order, and malformed RPC jobs. To
check OpenCL kernel compilation without mining or contacting a node, use:

```sh
cargo test --locked -p lotus-miner-lib compile_embedded_kernel -- --ignored --nocapture
```

This optional test needs an OpenCL device. On October 14, 2026, the CLI and GUI
release builds, five CPU tests, Clippy
with warnings denied, OpenCL kernel compilation on Apple M5 Max, and extracted
macOS arm64 archive checks passed. Linux and macOS Intel builds await CI.
Passing compilation and CPU tests alone does not establish GPU hashrate,
successful live block submission, or
support for every vendor driver. No live mining is performed by the tests.
