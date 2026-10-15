# Lotus Daemon (`lotusd` & `lotus-cli` with In-Process Chronik)

This directory builds Lotus V1 mainnet on pinned Bitcoin ABC `8c67fe1e85`. It contains everything needed to pull upstream [`Bitcoin-ABC/bitcoin-abc`](https://github.com/Bitcoin-ABC/bitcoin-abc), automatically apply the Lotus patch series in order, and compile `lotusd` and `lotus-cli` with the **in-process Chronik indexer** (`-DBUILD_CHRONIK=ON`) enabled.

> **Don't want to compile from source?**
> Download prebuilt Linux (`x86_64`) and macOS (`arm64`) binaries directly from **[GitHub Releases](https://github.com/givelotus/lotus/releases)**.

For contributors: [adding and updating patches](docs/adding-patches.md).

---

## Step-by-Step Build Guide (Copy & Paste)

### Step 1: Clone This Repository

```bash
git clone https://github.com/givelotus/lotus.git
cd lotus/daemon
```

---

### Step 2: Install Build Dependencies

#### On macOS (Apple Silicon / Homebrew)

Copy and paste:

```bash
brew install berkeley-db boost cmake flatbuffers jemalloc libevent \
  nng ninja openssl protobuf python@3.13 rust sqlite utf8proc
export LOTUS_BUILD_PYTHON="$(brew --prefix python@3.13)/bin/python3.13"
```

Chronik uses PyO3 bindings that support Python through 3.13. Select the same interpreter for CMake and Rust; the default Homebrew Python may be newer.

#### On Ubuntu 24.04 (release build platform)

Copy and paste:

```bash
sudo apt-get update
sudo apt-get install -y \
  build-essential cmake ninja-build pkg-config git python3 python3-dev \
  libboost-all-dev libssl-dev libevent-dev libdb++-dev \
  libsqlite3-dev libjemalloc-dev libflatbuffers-dev flatbuffers-compiler \
  libprotobuf-dev protobuf-compiler libclang-dev libutf8proc-dev curl
export LOTUS_BUILD_PYTHON=/usr/bin/python3

# Install the Rust compiler (required for the in-process Chronik indexer):
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
source "$HOME/.cargo/env"

# Build & install libnng (required for Lotus NNG pub/sub interface):
git clone --depth 1 --branch v1.9.0 https://github.com/nanomsg/nng.git /tmp/nng
cmake -S /tmp/nng -B /tmp/nng/build -GNinja \
  -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_SHARED_LIBS=OFF \
  -DNNG_TESTS=OFF \
  -DNNG_TOOLS=OFF \
  -DCMAKE_POSITION_INDEPENDENT_CODE=ON
sudo cmake --build /tmp/nng/build --target install
```

Ubuntu 24.04's Python 3.12 is within Chronik's supported range. CI explicitly selects Python 3.13. On other distributions, select a Python 3.10–3.13 interpreter with development headers; those distributions are not covered by the release workflow.

---

### Step 3: Pull `bitcoin-abc` and Apply All Lotus Patches Automatically

From inside `lotus/daemon`, run:

```bash
make setup SERIES=v1
```

**What this command does for you:**
1. Clones `https://github.com/Bitcoin-ABC/bitcoin-abc.git` into `workspace-v1/`.
2. Checks out the exact pinned base commit from [`bitcoin-abc-v1-version`](bitcoin-abc-v1-version) for V1.
3. Reads [`patches/v1/series`](patches/v1/series) from top to bottom and applies all 153 Lotus patches (`000` through `247`) in order, committing each one cleanly into `workspace-v1/`.

Existing workspaces are preserved. To replay from scratch, use a separate
monorepo checkout or move an unused workspace aside first. Never move or reset
the source/build directory of a running daemon. `RESET=1` is refused.

---

### Step 4: Compile `lotusd` and `lotus-cli`

From inside `lotus/daemon`, run:

```bash
PYO3_PYTHON="$LOTUS_BUILD_PYTHON" SERIES=v1 scripts/build.sh \
  -DPython_EXECUTABLE="$LOTUS_BUILD_PYTHON"
```

**What this command does for you:**
- Configures CMake + Ninja inside `workspace-v1/build/` with `-DBUILD_CHRONIK=ON` enabled by default.
- Compiles the Rust `chronik-bridge` / `bitcoinsuite` crates and links them directly into `lotusd`.
- Produces the finished binaries at:
  - `workspace-v1/build/src/lotusd`
  - `workspace-v1/build/src/lotus-cli`

Check that your build succeeded:

```bash
./workspace-v1/build/src/lotusd --version
./workspace-v1/build/src/lotus-cli --version
```

---

## Step 5: Run `lotusd` (with Chronik Enabled)

To start `lotusd` in the background with the in-process Chronik indexer turned on:

```bash
./workspace-v1/build/src/lotusd -chronik=1 -daemon
```

Or use the helper target (which also raises `ulimit -n 65536` automatically):

```bash
make run SERIES=v1 ARGS="-chronik=1 -daemon"
```

### Default Mainnet Ports
| Service | Default Port / Bind | Flag to Override |
|---|---|---|
| **P2P Network** | `10605` | `-port=<port>` |
| **JSON-RPC** | `127.0.0.1:10604` | `-rpcport=<port>` |
| **Chronik HTTP & WebSocket** | `127.0.0.1:8331` | `-chronikbind=<ip:port>` |

### Useful Commands While Running

```bash
# Check sync progress via RPC:
./workspace-v1/build/src/lotus-cli getblockchaininfo

# Query Chronik's live protobuf endpoint:
curl -s http://127.0.0.1:8331/blockchain-info | xxd

# Stop lotusd cleanly:
./workspace-v1/build/src/lotus-cli stop
```

---

## Developer Reference: Modifying or Rebasing Patches

- **Validate replay without changing a workspace**:
  ```bash
  python3 scripts/patch-series.py /tmp/isolated-abc patches/v1/series \
    --base "$(head -1 bitcoin-abc-v1-version)" --check \
    --provenance patches/v1/metadata-provenance.json
  ```
- **Export a committed change inside an isolated workspace**: commit the intended
  change with its rationale first, then:
  ```bash
  make mkpatch SERIES=v1 NAME=248-my-new-patch
  ```
- **Rebase onto a newer Bitcoin ABC commit**: use an isolated workspace, then run:
  ```bash
  make refresh SERIES=v1 COMMIT=UPSTREAM_COMMIT_SHA
  ```
  The helper updates `bitcoin-abc-v1-version` and reapplies the mainnet series. Resolve conflicts, export one patch per series entry, and verify replay and protocol compatibility before replacing release artifacts.

Independent options can be inspected with `make features SERIES=v1
FEATURES=chronik,nng-off` and passed to `make build` using the same variables.
Chronik does not select mining or policy patches. See the
[support audit](docs/support-matrix.md) for implemented features and experimental
candidates.

Prepare an entire release candidate in a new directory with:

```sh
make prepare-release UPSTREAM=/tmp/isolated-abc VERSION=11.6.1 \
  CANDIDATE=/tmp/lotus-release-11.6.1
```

This prepares reviewable source, packaging and release metadata without
publishing. Network changes require explicit verified inputs. See
[release preparation](docs/release-preparation.md) for validation and the separate
publication command.
