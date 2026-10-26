#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
BIN_DIR="${LOTUS_BIN_DIR:-}"
if [[ -z "${BIN_DIR}" ]]; then
  for cand in \
    "${REPO_ROOT}/build/src" \
    "/private/tmp/out-wt-integrated-040/src" \
    "/private/tmp/build-lotus-v2-stress/src" \
    "/private/tmp/build-lotus-v2-unified/src"; do
    if [[ -x "${cand}/lotusd" && -x "${cand}/lotus-cli" ]]; then
      BIN_DIR="${cand}"
      break
    fi
  done
fi

LOTUSD="${BIN_DIR}/lotusd"
LOTUS_CLI="${BIN_DIR}/lotus-cli"

if [[ ! -x "${LOTUSD}" || ! -x "${LOTUS_CLI}" ]]; then
  echo "ERROR: Could not find lotusd/lotus-cli in ${BIN_DIR}." >&2
  echo "Set LOTUS_BIN_DIR=/path/to/build/src and retry." >&2
  exit 1
fi

# Clean any previous quickstart session first
"${SCRIPT_DIR}/stop-and-clean.sh" >/dev/null 2>&1 || true

RUN_DIR="/private/tmp/lotus-v2-e2e-run-$$"
mkdir -p "${RUN_DIR}/node0" "${RUN_DIR}/node1" "${RUN_DIR}/node2"
echo "${RUN_DIR}" > /private/tmp/lotus-v2-e2e-run-current

RPC_USER="lotusv2"
RPC_PASS="lotusv2pass"
WORKBENCH_PORT="${WORKBENCH_PORT:-32180}"
EXPLORER_PORT="${EXPLORER_PORT:-32181}"

HAS_CHRONIK=0
if "${LOTUSD}" -help 2>&1 | grep -q "chronik="; then
  HAS_CHRONIK=1
fi

echo "=================================================================="
echo " Lotus V2 Local 3-Node Testnet + Chronik + Explorer + Workbench"
echo "=================================================================="
echo " Datadir   : ${RUN_DIR}"
echo " Binaries  : ${BIN_DIR} (embedded -chronik=${HAS_CHRONIK})"

# Launch 3 lotusd nodes with txindex (and embedded Chronik when compiled in)
for i in 0 1 2; do
  rpc_port=$((32110 + i * 10))
  p2p_port=$((32111 + i * 10))
  chronik_port=$((32112 + i * 10))
  extra_args=()
  if [[ "${i}" -gt 0 ]]; then
    extra_args+=("-connect=127.0.0.1:32111")
  fi
  if [[ "${HAS_CHRONIK}" -eq 1 ]]; then
    extra_args+=("-chronik=1" "-chronikbind=127.0.0.1:${chronik_port}")
  fi

  "${LOTUSD}" -regtest \
    -datadir="${RUN_DIR}/node${i}" \
    -pid="${RUN_DIR}/node${i}/lotusd.pid" \
    -rpcuser="${RPC_USER}" \
    -rpcpassword="${RPC_PASS}" \
    -rpcport="${rpc_port}" \
    -port="${p2p_port}" \
    -bind="127.0.0.1:${p2p_port}" \
    -txindex=1 \
    -acceptnonstdtxn=1 \
    -keypool=25 \
    -daemon \
    ${extra_args[@]+"${extra_args[@]}"} >/dev/null
done

cli_node() {
  local idx="$1"
  shift
  local rpc_port=$((32110 + idx * 10))
  "${LOTUS_CLI}" -regtest -datadir="${RUN_DIR}/node${idx}" -rpcport="${rpc_port}" -rpcuser="${RPC_USER}" -rpcpassword="${RPC_PASS}" "$@"
}

echo "[1/5] Waiting for 3 lotusd nodes to initialize RPC & SQLite wallets..."
for i in 0 1 2; do
  for _ in {1..100}; do
    if cli_node "${i}" getblockchaininfo >/dev/null 2>&1; then
      break
    fi
    sleep 0.2
  done
  cli_node "${i}" createwallet "node${i}" >/dev/null
done

echo "[2/5] Mining 115 initial regtest blocks on Node 0 to mature coinbase UTXOs..."
MINER_ADDR="$(cli_node 0 getnewaddress)"
cli_node 0 generatetoaddress 115 "${MINER_ADDR}" >/dev/null

# Wait for Node 1 and Node 2 to sync to height 115
for i in 1 2; do
  for _ in {1..50}; do
    h="$(cli_node "${i}" getblockcount 2>/dev/null || echo 0)"
    if [[ "${h}" -ge 115 ]]; then
      break
    fi
    sleep 0.2
  done
done

echo "[3/5] Starting Lotus V2 Workbench Server on http://127.0.0.1:${WORKBENCH_PORT} ..."
PORT="${WORKBENCH_PORT}" \
NODE0_RPC_PORT=32110 \
NODE1_RPC_PORT=32120 \
NODE2_RPC_PORT=32130 \
CHRONIK_PORT=32112 \
RPC_USER="${RPC_USER}" \
RPC_PASS="${RPC_PASS}" \
  node "${SCRIPT_DIR}/workbench-server.mjs" >"${RUN_DIR}/workbench.log" 2>&1 &
echo $! > "${RUN_DIR}/workbench.pid"

for _ in {1..40}; do
  if curl -sf "http://127.0.0.1:${WORKBENCH_PORT}/api/overview" >/dev/null 2>&1; then
    break
  fi
  sleep 0.2
done

echo "[4/5] Starting Explorer V2 Server (explorer/v2) on http://127.0.0.1:${EXPLORER_PORT} ..."
node "${REPO_ROOT}/explorer/v2/server.mjs" \
  --port "${EXPLORER_PORT}" \
  --api "http://127.0.0.1:${WORKBENCH_PORT}" >"${RUN_DIR}/explorer.log" 2>&1 &
echo $! > "${RUN_DIR}/explorer.pid"

for _ in {1..40}; do
  if curl -sf "http://127.0.0.1:${EXPLORER_PORT}/v2/explorer/v1/status" >/dev/null 2>&1; then
    break
  fi
  sleep 0.2
done

echo "[5/5] Seeding sample V2 transactions (Wallet, V2 BigInt, Compiled Hashlock, V2 Token Mint/Transfer)..."
for mode in wallet_payment v2_bigint v2_contract_hashlock v2_token_mint_and_transfer; do
  curl -sf -X POST "http://127.0.0.1:${WORKBENCH_PORT}/api/send-tx" \
    -H "Content-Type: application/json" \
    -d "{\"mode\":\"${mode}\"}" >/dev/null
done
curl -sf -X POST "http://127.0.0.1:${WORKBENCH_PORT}/api/mine" \
  -H "Content-Type: application/json" \
  -d '{"count":1}' >/dev/null

# Also send a couple of unconfirmed transactions so the mempool has live entries
curl -sf -X POST "http://127.0.0.1:${WORKBENCH_PORT}/api/send-tx" \
  -H "Content-Type: application/json" \
  -d '{"mode":"wallet_payment"}' >/dev/null
curl -sf -X POST "http://127.0.0.1:${WORKBENCH_PORT}/api/send-tx" \
  -H "Content-Type: application/json" \
  -d '{"mode":"v2_bigint"}' >/dev/null

HEIGHT="$(cli_node 0 getblockcount)"
BEST_HASH="$(cli_node 0 getbestblockhash)"

cat <<EOF

==================================================================
 Lotus V2 Testnet Stack is UP and Synchronized!
==================================================================
 Chain Tip      : regtest height #${HEIGHT} (${BEST_HASH})
 Node 0         : RPC 127.0.0.1:32110 | P2P 32111 | Chronik 127.0.0.1:32112
 Node 1         : RPC 127.0.0.1:32120 | P2P 32121 | Chronik 127.0.0.1:32122
 Node 2         : RPC 127.0.0.1:32130 | P2P 32131 | Chronik 127.0.0.1:32132

 Interactive Workbench UI (Blocks, Txs, Token & Contract Studio):
   -> http://127.0.0.1:${WORKBENCH_PORT}

 Explorer V2 App (explorer/v2 SSR + /api/explorer/v1/*):
   -> http://127.0.0.1:${EXPLORER_PORT}

 Companion Demo Scripts:
   -> ./tools/testnet-quickstart/send-demo-txs.sh
   -> ./tools/testnet-quickstart/compile-and-deploy-contract.sh

 Stop All Processes & Clean Up Temporary Datadir:
   -> ./tools/testnet-quickstart/stop-and-clean.sh
==================================================================
EOF
