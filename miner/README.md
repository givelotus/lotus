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

## Dogecoin direct Scrypt mining

Select the chain explicitly with `--chain dogecoin` or `chain = "dogecoin"`
in a separate configuration file. The default remains Lotus. Dogecoin uses
an 80-byte header, a 32-bit little-endian nonce at byte 76, and
Scrypt(N=1024,r=1,p=1); Lotus retains its 160-byte layered SHA-256 format.
Both CLI and GUI use the selected backend; restart to change the chain.

```toml
chain = "dogecoin"
rpc_url = "http://127.0.0.1:22555"
rpc_user = "your-local-rpc-user"
rpc_password = "your-local-rpc-password"
rpc_poll_interval = 3
mine_to_address = "YOUR_DOGECOIN_ADDRESS"
gpu_index = 0
scrypt_work_size = 1024
```

This requires the rebased Doged node's `getrawunsolvedblock(address)` RPC
returning `{blockhex,target}` and `submitblock(blockhex)`. It is not a
Stratum pool client. It mines ordinary direct Scrypt blocks, not parent-chain
AuxPoW jobs or combined Litecoin/Dogecoin rewards. Payout validation and
coinbase construction belong to the node; the miner preserves its entire
serialized transaction body. AuxPoW-marked work is rejected rather than
mistakenly treating its parent proof as direct work. No live financial mining
is enabled by tests.

The embedded OpenCL kernel uses 128 KiB scratch per nonce. `scrypt_work_size`
is an independent power-of-two batch size from 256 to 4096 (32–512 MiB).
The default is 1024 (128 MiB); Lotus's intensity slider and `kernel_size`
never control this allocation. Device allocation failures are reported by
OpenCL. Each candidate is rehashed with an independent CPU implementation
before submission, including nonce zero and target equality. Identical
polled jobs retain nonce progress; fresh work starts a new nonce space.
After nonce exhaustion the miner waits for a different template from RPC.

Verification commands (from `miner/`):

```sh
cargo test --workspace
cargo clippy --workspace --all-targets -- -D warnings
cargo test -p lotus-miner-lib opencl_matches_cpu -- --ignored --nocapture
cargo test -p lotus-miner-lib opencl_batch_benchmark -- --ignored --nocapture
```

The bounded RPC integration test requires `DOGE_REGTEST_RPC_URL`,
`DOGE_REGTEST_RPC_USER`, `DOGE_REGTEST_RPC_PASSWORD`, and
`DOGE_REGTEST_PAYOUT`, pointing at an isolated regtest node with the new RPC.
It verifies the chain is regtest before requesting mining work:

```sh
cargo test -p lotus-miner-lib dogecoin_regtest_gpu_submit -- --ignored --nocapture
```

2026-10-14 validation on Apple M5 Max: all 256 GPU hashes matched the CPU
reference, which also matched Python `hashlib.scrypt`; nonzero headers and
near-maximum nonces are sampled at each supported benchmark batch size.
The real GPU/node RPC round trip mined and submitted isolated regtest height
22 after AuxPoW activation (height 21 before the test), accepted by the node.
These checks establish direct mining correctness on this device, not pool
compatibility, ASIC competitiveness, sustained profitability, or other GPUs.

Bounded warmed OpenCL measurements on that M5 Max (1,024 batches each,
including GPU buffer upload/readback, excluding compilation and CPU verification):

| Nonces/batch | Scratch | Hashes | Elapsed | Hashes/second |
| --- | --- | --- | --- | --- |
| 256 | 32 MiB | 262,144 | 3.64046 s | 72,008.5 |
| 1,024 | 128 MiB | 1,048,576 | 4.03905 s | 259,609.5 |
| 4,096 | 512 MiB | 4,194,304 | 4.42599 s | 947,652.6 |

These are short local measurements during concurrent development, not a
long-duration thermal test or an estimate of mining income. The kernel is a
correctness-first implementation; tuning for other devices remains unvalidated.
