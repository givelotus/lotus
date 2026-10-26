# Lotus V2 Testnet Quickstart Kit (`tools/testnet-quickstart`)

Turnkey local 3-node Lotus V2 regtest cluster with **embedded Chronik (`libmdbx`)**, **SQLite native wallets**, **V2 134-byte header & v7 transaction inspector**, **interactive Transaction & Atomic Batch Sender**, **Lotus V2 `.lotus` Contract Compiler Studio**, and **Explorer V2 (`explorer/v2`)**.

---

## 1. Prerequisites

- Built `lotusd` and `lotus-cli` binaries (either in `build/src/` or specified via `LOTUS_BIN_DIR=/path/to/build/src`).
- Node.js 20+ (`node` and `npm`).
- Dependencies installed in `tools/lotus-v2-compiler` and `explorer/v2`.

---

## 2. One-Command Startup

From the repository root:

```bash
./tools/testnet-quickstart/start-testnet.sh
```

What `start-testnet.sh` does automatically:
1. Cleans up any prior quickstart session via `stop-and-clean.sh`.
2. Launches **3 `lotusd -regtest` nodes** in a temporary `/private/tmp/lotus-v2-e2e-run-<pid>` directory on high ports (`32110`–`32132`) so it never collides with production or default testnet ports:
   - **Node 0**: RPC `127.0.0.1:32110`, P2P `32111`, Chronik `127.0.0.1:32112`
   - **Node 1**: RPC `127.0.0.1:32120`, P2P `32121`, Chronik `127.0.0.1:32122`
   - **Node 2**: RPC `127.0.0.1:32130`, P2P `32131`, Chronik `127.0.0.1:32132`
3. Creates native SQLite wallets (`wallet.sqlite`, application ID `0x4C563257`) on all 3 nodes and mines **105 blocks** so coinbase UTXOs are mature.
4. Starts the **Lotus V2 Testnet Workbench & API Server** on **`http://127.0.0.1:32180`**.
5. Starts the **Explorer V2 Server (`explorer/v2/server.mjs`)** on **`http://127.0.0.1:32181`**.
6. Seeds sample transactions (native SQLite wallet payment, V2 v7 64-bit arithmetic + introspection spend, compiled `Hashlock.lotus` contract spend, and V2 v7 native token genesis mint & transfer) and mines a block so both UIs are populated immediately.

---

## 3. Web Interfaces

| Interface | URL | Highlights |
|---|---|---|
| **Lotus V2 Workbench & Studio** | `http://127.0.0.1:32180` | Live 3-node cluster status, 134-byte V2 header inspector (`TxRoot`, `StateRoot`, `SubtreeA`), 50/25/25 coinbase split bar, 1-click Tx & Batch Burst sender, Block/Tx/UTXO inspector, and interactive `.lotus` Contract Compiler Studio |
| **Explorer V2 (`explorer/v2`)** | `http://127.0.0.1:32181` | Server-side rendered V2 block/tx/token/contract explorer backed by `/v2/explorer/v1/*` envelopes |

---

## 4. Companion CLI Scripts

### Send All Demo Transaction Types + Atomic Batch Burst
```bash
./tools/testnet-quickstart/send-demo-txs.sh
```
Broadcasts:
1. Native SQLite wallet payment (`sendtoaddress`)
2. V2 `version=7` 64-bit arithmetic + native introspection (`OP_INPUTFUNCTIONS` + `OP_TXOUTCOUNT`)
3. Compiled `Hashlock.lotus` V2 contract funding + `version=7` witness spend
4. V2 `version=7` native token genesis mint (`tokenId = prevout.txid` of `vin[0]`) + multi-output token transfer
5. Atomic batch validation (`testrawtxbatch`) and submission (`submitrawtxbatch`) + block confirmation

### Compile & Deploy a `.lotus` Contract On-Chain
```bash
./tools/testnet-quickstart/compile-and-deploy-contract.sh
```
Compiles `Hashlock.lotus` via `tools/lotus-v2-compiler`, prints its Tapscript V2 branch ASM, leaf hash, and root commitment (`0x5220 || root32`), funds it on Node 0, spends it using a V2 `version=7` witness stack, and mines a confirming block.

---

## 5. Teardown & Disk Hygiene

When finished, stop all nodes and servers and delete the temporary `/private/tmp/lotus-v2-e2e-run-*` data directory with a single command:

```bash
./tools/testnet-quickstart/stop-and-clean.sh
```
