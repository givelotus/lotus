# Pinned in-process Chronik source

This candidate extracts one reviewed Bitcoin ABC Chronik tree and builds it
inside an ABC host through CMake. It keeps upstream Rust/C++, protobuf schemas,
and dependency versions unchanged. It does not introduce a runtime plugin ABI,
NNG dependency, or consensus/mempool/mining-policy change.

## Export

The initial pin is ABC `1fb7db17c176cdea8a2c60d887891589382ee4e3`.
Use an existing clone containing that committed source, or fetch it into a new
local clone. Sparse checkout can reduce checked-out files, but extraction also
needs the root Cargo workspace/lockfile, license, Rust CMake helper, and embedded
Python test framework. Fetching only `chronik/` is insufficient.

```sh
python3 daemon/scripts/export-chronik.py \
  --upstream /path/to/bitcoin-abc \
  --output /new/path/to/shared-chronik
```

The exporter reads committed Git objects, ignores working-tree edits, verifies
pinned trees and file hashes, then atomically creates a new output directory.
It refuses existing destinations. The output includes all 14 Chronik workspace
crates, original root Cargo inputs under `upstream-workspace/`, and a derived
Chronik-only workspace/lockfile. The lock retains 343 upstream packages rather
than 498; package identities, checksums and resolved dependency edges are
verified against upstream. No dependencies are upgraded.

`chronik-source.json` records every source-file hash and export provenance.
`source.json` pins its digest. CMake verifies these before staging sources under
the host's build directory; the exported tree is never patched in place. One
staged CMake adaptation makes Cargo tests use the extracted workspace root.

## Build the ABC proof

Apply `hosts/abc/0001-build-chronik-from-pinned-external-source.patch` with
`git am` in a new ABC clone at the pin, then configure:

```sh
rustup toolchain install 1.87.0 --profile minimal --component clippy
cmake -S /path/to/isolated/abc -B /path/to/isolated/abc/build -GNinja \
  -DBUILD_BITCOIN_QT=OFF -DBUILD_BITCOIN_ZMQ=OFF \
  -DBUILD_CHRONIK=ON -DBUILD_CHRONIK_PLUGINS=OFF \
  -DRust_TOOLCHAIN=1.87.0 -DPython_EXECUTABLE=/path/to/python3.13 \
  -DCHRONIK_SOURCE_DIR=/new/path/to/shared-chronik \
  -DCHRONIK_PROVIDER_MODULE=/path/to/lotus/daemon/chronik/cmake/ChronikProvider.cmake
PYO3_PYTHON=/path/to/python3.13 RUSTUP_TOOLCHAIN=1.87.0 \
  ninja -C /path/to/isolated/abc/build -j8 \
  bitcoind bitcoin-cli test_bitcoin check-crates protobuf-chronik
ninja -C /path/to/isolated/abc/build -j8 check-bitcoin
```

Rust 1.87 is the exact host's declared CMake minimum. With unchanged CXX1.0.138,
Rust1.93 Clippy rejects generated `automatically_derived` attributes. Pinning
this component to1.87 avoids source changes or suppressed diagnostics. Lotus's
separately validated1.93 release toolchain remains unchanged. Python3.13 avoids
PyO3's incompatibility with newer Python versions at this source pin.

The host adapter redirects C++ bridge tests and protobuf generation as well as
the actual indexer. The fallback without `CHRONIK_SOURCE_DIR` remains ABC's
in-tree build. No default Lotus/eCash/BCHN/Doged patch manifest selects this
candidate. Existing live nodes and published releases remain untouched.

## Host boundaries and publication

ABC remains the unchanged extraction proof. An optional exact-pin [Bitcoin Core
host profile](hosts/bitcoin-core/HOST.md) now has native macOS regtest evidence,
including witness storage, events and restart recovery. Other profiles require
independent reviewed adapters; CMake fails closed when their profile is absent.
Lotus and Doged retain their embedded forks. This does not enable Core Chronik
in default component releases or establish mainnet/cross-platform support.

A separate shared-source repository can later receive these deterministic
exports, with original licenses/provenance and exact export pins. This candidate
creates no external repository, changes no submodules, and publishes no package.
First review the extraction and ABC behavior, then adapt each host independently.
Mainnet synchronization, cross-platform builds and reproducible binaries are
separate validation requirements.
