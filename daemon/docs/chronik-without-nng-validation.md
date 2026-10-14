# Native Chronik build without NNG

Validated on 2026-10-14 using an independent build directory. This checks the
Chronik-enabled, NNG-disabled V1 combination; it introduces no source changes.

| Item | Observed value |
| --- | --- |
| V1 source commit | `6590d92300ba588325628ab7c1a166e392947cff` |
| Source tree | `e0d4f9c0219739b6774864858c582a8144a443d9` |
| Source checkout | `/tmp/rebase-latest-abc` |
| Independent build | `/tmp/lotus-v1-chronik-without-nng-build` |
| Host | macOS 26.6, Apple arm64 |
| Rust | 1.93.0 |
| Python | `/opt/homebrew/bin/python3.13`, version 3.13.16 |
| Enabled | `BUILD_CHRONIK=ON` |
| Disabled | `BUILD_BITCOIN_NNG=OFF`, Qt, ZeroMQ, Chronik plugins |

## Commands and results

```sh
PYO3_PYTHON=/opt/homebrew/bin/python3.13 cmake \
  -S /tmp/rebase-latest-abc \
  -B /tmp/lotus-v1-chronik-without-nng-build -GNinja \
  -DBUILD_CHRONIK=ON -DBUILD_BITCOIN_NNG=OFF \
  -DBUILD_BITCOIN_QT=OFF -DBUILD_BITCOIN_ZMQ=OFF \
  -DENABLE_UPNP=OFF -DENABLE_NATPMP=OFF \
  -DPython_EXECUTABLE=/opt/homebrew/bin/python3.13 \
  -DRust_TOOLCHAIN=1.93.0

PYO3_PYTHON=/opt/homebrew/bin/python3.13 ninja \
  -C /tmp/lotus-v1-chronik-without-nng-build -j12 lotusd lotus-cli
```

Configuration and all 327 build steps passed. The generated
`src/config/bitcoin-config.h` defines `ENABLE_CHRONIK` and leaves `ENABLE_NNG`
undefined. Full daemon build commands contain no NNG interface sources,
`libnng` library paths, or `-lnng` option.

Both binaries are arm64 Mach-O executables. Executing their version commands
succeeded:

```text
Lotus version v11.6.0-6590d92300ba
Lotus RPC client version v11.6.0-6590d92300ba
```

`lotusd -help` exposes Chronik options and no NNG option. `otool -L` on both
binaries contains no NNG dynamic dependency, and `nm -u` on the daemon contains
no NNG function imports. The daemon directly links libevent, Berkeley DB, and
macOS system/C++ libraries; the CLI links libevent and macOS system/C++ libraries.

## Scope and preserved state

This is native compile/link and executable-startup evidence. No node was
started, no blocks were mined, and no data directory was accessed for node
operation. It does not establish network behavior or portability to older
macOS releases. The existing Chronik-plus-NNG validation remains separate;
its full C++/Rust suites were not repeated for this compile-only combination.

The linker warns that some Rust native dependency objects target macOS 26.5
while the link deployment target is 26.0. The binaries execute on the tested
26.6 host; compatibility with 26.0 has not been demonstrated. Configuration
also reports that the inherited UPNP/NATPMP flags are unused, and linking
reports duplicate static libraries. None caused a failed build.

The original `/tmp/rebase-latest-abc/build/CMakeCache.txt` retained SHA256
`6a68fe69a7058b4e2c44f84494f9f65aa0b64a1bfab1e2de4c3985e1bd961527`
before and after the independent build. The source checkout remained clean.
The production workspace, daemon, chain data, and release assets were untouched.

Local evidence logs (not repository artifacts):

- `/tmp/lotus-v1-chronik-without-nng-configure-20261014.log`
- `/tmp/lotus-v1-chronik-without-nng-build-20261014.log`
- `/tmp/lotus-v1-chronik-without-nng-commands-20261014.log`
- `/tmp/lotus-v1-chronik-without-nng-daemon-version-20261014.log`
- `/tmp/lotus-v1-chronik-without-nng-cli-version-20261014.log`
- `/tmp/lotus-v1-chronik-without-nng-help-20261014.log`
- `/tmp/lotus-v1-chronik-without-nng-links-20261014.log`
- `/tmp/lotus-v1-chronik-without-nng-symbols-20261014.log`
