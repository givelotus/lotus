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

echo "=================================================================="
echo " Lotus V2 Contract Compiler -> On-Chain V2 v7 Deployment & Spend"
echo "=================================================================="

CONTRACT_PAYLOAD='{
  "contract": "Hashlock",
  "source": "contract Hashlock<digest: Bytes32> {\n  function reveal(preimage: Bytes32) {\n    require(sha256(preimage) == digest);\n  }\n}",
  "bindings": {
    "Hashlock": {
      "digest": "185f8db32271fe25f561a6fc938b2e264306ec304eda518007d1764826381969"
    }
  }
}'

echo "[1/3] Compiling Hashlock.lotus via tools/lotus-v2-compiler..."
curl -sf -X POST "${BASE_URL}/api/compile" \
  -H "Content-Type: application/json" \
  -d "${CONTRACT_PAYLOAD}" | node -e '
    const d = JSON.parse(fs.readFileSync(0, "utf8"));
    if (!d.ok) {
      console.error("Compilation failed:", d);
      process.exit(1);
    }
    const art = d.artifact;
    const branch = art.branches[0];
    console.log("  Contract Name    :", art.contractName);
    console.log("  Profile          :", art.profile);
    console.log("  Branch Name      :", branch.name);
    console.log("  ASM              :", branch.asm.join(" "));
    console.log("  Script Hex       :", branch.scriptHex);
    console.log("  Leaf Hash        :", branch.leafHash);
    console.log("  Root Commitment  :", art.commitments?.rootHex);
    console.log("  Locking Script   : 5220" + art.commitments?.rootHex);
  '

echo ""
echo "[2/3] Funding compiled V2 contract output & broadcasting V2 v7 witness spend..."
SPEND_TXID="$(curl -sf -X POST "${BASE_URL}/api/send-tx" \
  -H "Content-Type: application/json" \
  -d '{"mode":"v2_contract_hashlock"}' | node -e '
    const d = JSON.parse(fs.readFileSync(0, "utf8"));
    if (!d.ok) {
      console.error("Deploy/spend failed:", d);
      process.exit(1);
    }
    console.error("  Funding Txid     :", d.fundTxid);
    console.error("  V2 Spend Txid    :", d.spendTxid);
    console.error("  Preimage         :", d.preimageAscii);
    process.stdout.write(d.spendTxid);
  ')"

echo ""
echo "[3/3] Mining 1 block to confirm contract funding & spend on-chain..."
curl -sf -X POST "${BASE_URL}/api/mine" \
  -H "Content-Type: application/json" \
  -d '{"count":1}' | node -e '
    const d = JSON.parse(fs.readFileSync(0, "utf8"));
    console.log("  Confirmed Block  :", (d.blocks || [])[0]);
    console.log("  New Chain Height :", d.height);
  '

echo ""
echo "Contract transaction confirmed!"
echo "  Workbench Tx API : ${BASE_URL}/api/tx/${SPEND_TXID}"
echo "  Explorer V2 Tx   : http://127.0.0.1:${EXPLORER_PORT}/tx/${SPEND_TXID}"
