#!/usr/bin/env bash
set -euo pipefail

WORKBENCH_PORT="${WORKBENCH_PORT:-32180}"
EXPLORER_PORT="${EXPLORER_PORT:-32181}"
BASE_URL="http://127.0.0.1:${WORKBENCH_PORT}"

if ! curl -sf "${BASE_URL}/api/overview" >/dev/null 2>&1; then
  echo "ERROR: Workbench server is not running at ${BASE_URL}." >&2
  echo "Run ./tools/testnet-quickstart/start-testnet.sh first." >&2
  exit 1
fi

echo "=== [1/5] Sending Native SQLite Wallet Payment ==="
curl -s -X POST "${BASE_URL}/api/send-tx" \
  -H "Content-Type: application/json" \
  -d '{"mode":"wallet_payment"}' | node -e '
    const d = JSON.parse(fs.readFileSync(0, "utf8"));
    if (!d.ok) { console.error(d); process.exit(1); }
    console.log("  txid      :", d.txid);
    console.log("  recipient :", d.recipient);
    console.log("  amount    :", d.amountXpi, "XPI");
  '

echo "=== [2/5] Sending V2 v7 64-Bit Arithmetic + Native Introspection Tx ==="
curl -s -X POST "${BASE_URL}/api/send-tx" \
  -H "Content-Type: application/json" \
  -d '{"mode":"v2_bigint"}' | node -e '
    const d = JSON.parse(fs.readFileSync(0, "utf8"));
    if (!d.ok) { console.error(d); process.exit(1); }
    console.log("  fundTxid  :", d.fundTxid);
    console.log("  spendTxid :", d.spendTxid);
    console.log("  script    :", d.description);
  '

echo "=== [3/5] Sending Compiled .lotus Hashlock Contract Funding & V2 v7 Spend ==="
curl -s -X POST "${BASE_URL}/api/send-tx" \
  -H "Content-Type: application/json" \
  -d '{"mode":"v2_contract_hashlock"}' | node -e '
    const d = JSON.parse(fs.readFileSync(0, "utf8"));
    if (!d.ok) { console.error(d); process.exit(1); }
    console.log("  contract  :", d.contractName);
    console.log("  rootHex   :", d.rootHex);
    console.log("  fundTxid  :", d.fundTxid);
    console.log("  spendTxid :", d.spendTxid);
  '

echo "=== [4/5] Sending V2 v7 Native Token Genesis Mint & Transfer ==="
curl -s -X POST "${BASE_URL}/api/send-tx" \
  -H "Content-Type: application/json" \
  -d '{"mode":"v2_token_mint_and_transfer"}' | node -e '
    const d = JSON.parse(fs.readFileSync(0, "utf8"));
    if (!d.ok) { console.error(d); process.exit(1); }
    console.log("  tokenIdHex   :", d.tokenIdHex);
    console.log("  mintTxid     :", d.mintTxid, "(minted:", d.mintedAmount, ")");
    console.log("  transferTxid :", d.transferTxid, "(splits:", d.transferSplits.join(" + "), ")");
  '

echo "=== [5/5] Running Atomic Batch Burst (testrawtxbatch + submitrawtxbatch) & Mining 1 Block ==="
curl -s -X POST "${BASE_URL}/api/burst" \
  -H "Content-Type: application/json" \
  -d '{"count":5,"mine":true}' | node -e '
    const d = JSON.parse(fs.readFileSync(0, "utf8"));
    if (!d.ok) { console.error(d); process.exit(1); }
    console.log("  batch count  :", d.count);
    console.log("  accepted     :", d.submitBatch?.accepted, "| rejected:", d.submitBatch?.rejected);
    console.log("  mined block  :", (d.minedBlocks || [])[0] || "none");
  '

echo ""
echo "Done! Inspect live in:"
echo "  Workbench UI : http://127.0.0.1:${WORKBENCH_PORT}"
echo "  Explorer V2  : http://127.0.0.1:${EXPLORER_PORT}"
