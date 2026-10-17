# Lotus V2 Portal — The Dispatch ($10/mo Paid Newsletter), Browser WebGPU Miner & Mining Pool Dashboard

Self-contained web application (`web/lotus-v2-portal/`) and standalone/proxy pool server (`server.py`) for **Lotus V2 (P04 Tagged BLAKE3)**:

## Features

1. **Section 1 — The Lotus V2 Dispatch ($10/month Paid Newsletter):**
   - Deep-dive architectural issues on **Key-Addressed Merklix Trees**, **247-Byte SealedHeaders & Pre-Consensus (100k+ TPS)**, and **The 50/25/25 Monetary & Governance Architecture**.
   - **3 Ways to Unlock Subscriber Access:**
     1. **"Mine Your Subscription" (1-Click Browser WebGPU / Worker Miner):** Hash 2-stage Tagged BLAKE3 (`WorkHash` -> `BlockID`) under `worker = "sub:<email_or_id>"`. Every accepted share credits `$2.50` toward the `$10.00` monthly subscription and unlocks immediate reading access while mining.
     2. **Pay in Lotus V2 (Native Covenant / Direct Payment):** Displays a Lotus V2 subscription covenant vault address + 1-click payment verifier (`POST /api/newsletter/unlock-covenant`).
     3. **Card / Fiat ($10/mo Checkout Flow):** Instant checkout modal (`POST /api/newsletter/unlock-card`).

2. **Section 2 — Live Browser WebGPU (`WGSL`) + Web Worker Miner & Pool Dashboard:**
   - `public/miner-webgpu.js`: Zero-dependency WebGPU `@compute @workgroup_size(256)` compute shader porting `miner/kernels/lotus_v2.cl` (`b3_g`, `b3_compress`, 2-stage `WorkHash` -> `BlockID`) with `atomicAdd(&hits.count, 1u)` (4-byte readback when no share is found) and ~3ms per-frame auto-tuning.
   - `public/miner-worker.js`: Pre-packed 32-bit word Web Worker CPU/SIMD fallback with 100% bit-for-bit P04 test vector parity.
   - Real-time gauges for Local Browser Hashrate, Compute Backend, Active `job_id` & `BodyHash`, Accepted Shares, Worker `vardiff` Target, Pool Total Hashrate, PPLNS Reward Split (50% Miner / 25% Staker / 25% Treasury), and Recent Blocks Found.

## Quickstart & Automated Tests

```bash
# Run P04 test vector parity & End-to-End SSE/Submit/Newsletter/PPLNS tests
npm test

# Start the portal server (default port 37180; never uses reserved ports 10604/10605/8331)
python3 server.py --port 37180
```
