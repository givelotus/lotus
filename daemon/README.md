# Lotus Daemon (`lotusd` & `lotus-cli` with In-Process Chronik)

This directory contains everything needed to pull upstream [`Bitcoin-ABC/bitcoin-abc`](https://github.com/Bitcoin-ABC/bitcoin-abc), automatically apply the Lotus patch series in order, and compile `lotusd` and `lotus-cli` with the **in-process Chronik indexer** (`-DBUILD_CHRONIK=ON`) enabled.

> **Don't want to compile from source?**
> Download prebuilt Linux (`x86_64`) and macOS (`arm64`) binaries directly from **[GitHub Releases](https://github.com/givelotus/lotus/releases)**.

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
  nng ninja openssl protobuf rust sqlite utf8proc
```

#### On Ubuntu / Debian (22.04 or 24.04)

Copy and paste:

```bash
sudo apt-get update
sudo apt-get install -y \
  build-essential cmake ninja-build pkg-config git python3 \
  libboost-all-dev libssl-dev libevent-dev libdb++-dev \
  libsqlite3-dev libjemalloc-dev libflatbuffers-dev flatbuffers-compiler \
  libprotobuf-dev protobuf-compiler libclang-dev libutf8proc-dev curl

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

---

### Step 3: Pull `bitcoin-abc` and Apply All Lotus Patches Automatically

From inside `lotus/daemon`, run:

```bash
make setup SERIES=v1
```

**What this command does for you:**
1. Clones `https://github.com/Bitcoin-ABC/bitcoin-abc.git` into `workspace-v1/`.
2. Checks out the exact pinned base commit from [`bitcoin-abc-version`](bitcoin-abc-version).
3. Reads [`patches/v1/series`](patches/v1/series) from top to bottom and applies all 153 Lotus patches (`000` through `247`) in order, committing each one cleanly into `workspace-v1/`.

*(Need to wipe `workspace-v1/` and re-apply all patches cleanly from scratch? Run `make setup SERIES=v1 RESET=1`.)*

---

### Step 4: Compile `lotusd` and `lotus-cli`

From inside `lotus/daemon`, run:

```bash
make build SERIES=v1
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

- **Re-apply all patches from scratch**:
  ```bash
  make setup SERIES=v1 RESET=1
  ```
- **Save edits made inside `workspace-v1/` as a new patch**:
  ```bash
  make mkpatch SERIES=v1 NAME=248-my-new-patch
  ```
- **Rebase the patch series onto a newer `bitcoin-abc` commit**:
  ```bash
  make refresh SERIES=v1 COMMIT=<new-bitcoin-abc-commit-sha>
  ```
