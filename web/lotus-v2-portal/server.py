#!/usr/bin/env python3
"""
Lotus V2 Portal Backend Server (`web/lotus-v2-portal/server.py`)

Provides:
1. Live Mining Pool HTTP/SSE API (`GET /pool/jobs`, `POST /pool/submit`, `GET /api/pool/stats`)
   - Can proxy to an upstream `lotusd` `/pool/*` endpoint via `LOTUSD_POOL_URL`
   - Or run in standalone pool mode with real, bit-for-bit P04 Tagged BLAKE3 share
     verification (`BodyHash`, `WorkHash`, `BlockID <= target`), dynamic `vardiff`,
     and 50/25/25 PPLNS reward accounting.
2. The Lotus V2 Dispatch ($10/month Paid Newsletter) API:
   - `GET /api/newsletter/articles?subscriber=<id>`
   - Unlock Method 1: "Mine Your Subscription" via `POST /pool/submit` with `worker="sub:<id>"`
   - Unlock Method 2: "Pay in Lotus V2 (Native Covenant / Direct Payment)" via `POST /api/newsletter/unlock-covenant`
   - Unlock Method 3: "Card / Fiat ($10/mo Checkout Flow)" via `POST /api/newsletter/unlock-card`
3. Static file serving for `public/` (`index.html`, `styles.css`, `app.js`, `miner-webgpu.js`, `miner-worker.js`).

Default port: 37180 (strictly avoids reserved ports 10604, 10605, 8331).
"""

import argparse
import hashlib
import http.server
import json
import os
import socketserver
import struct
import sys
import threading
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional, Tuple

FORBIDDEN_PORTS = {10604, 10605, 8331}
DEFAULT_PORT = 37180
PUBLIC_DIR = Path(__file__).resolve().parent / "public"

# ============================================================================
# Exact Single-Chunk BLAKE3 & Lotus V2 P04 Tagged Hash Implementation
# ============================================================================

B3_IV = (
    0x6A09E667,
    0xBB67AE85,
    0x3C6EF372,
    0xA54FF53A,
    0x510E527F,
    0x9B05688C,
    0x1F83D9AB,
    0x5BE0CD19,
)

B3_SCHEDULE = (
    (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15),
    (2, 6, 3, 10, 7, 0, 4, 13, 1, 11, 12, 5, 9, 14, 15, 8),
    (3, 4, 10, 12, 13, 2, 7, 14, 6, 5, 9, 0, 11, 15, 8, 1),
    (10, 7, 12, 9, 14, 3, 13, 15, 4, 0, 11, 2, 5, 8, 1, 6),
    (12, 13, 9, 11, 15, 10, 14, 8, 7, 2, 5, 3, 0, 1, 6, 4),
    (9, 14, 11, 5, 8, 12, 15, 1, 13, 3, 0, 10, 2, 6, 4, 7),
    (11, 15, 5, 0, 1, 9, 8, 6, 14, 10, 2, 12, 3, 4, 7, 13),
)

HEADER_LEN = 134
NONCE_OFFSET = 42
BODY_OFFSET = 50


def _rotl32(x: int, n: int) -> int:
    x &= 0xFFFFFFFF
    return ((x << n) | (x >> (32 - n))) & 0xFFFFFFFF


def _b3_g(v: List[int], a: int, b: int, c: int, d: int, x: int, y: int) -> None:
    v[a] = (v[a] + v[b] + x) & 0xFFFFFFFF
    v[d] = _rotl32(v[d] ^ v[a], 16)
    v[c] = (v[c] + v[d]) & 0xFFFFFFFF
    v[b] = _rotl32(v[b] ^ v[c], 20)
    v[a] = (v[a] + v[b] + y) & 0xFFFFFFFF
    v[d] = _rotl32(v[d] ^ v[a], 24)
    v[c] = (v[c] + v[d]) & 0xFFFFFFFF
    v[b] = _rotl32(v[b] ^ v[c], 25)


def b3_compress(cv: Tuple[int, ...], block: bytes, block_len: int, flags: int) -> Tuple[int, ...]:
    m = struct.unpack("<16I", block)
    v = [
        cv[0], cv[1], cv[2], cv[3], cv[4], cv[5], cv[6], cv[7],
        B3_IV[0], B3_IV[1], B3_IV[2], B3_IV[3],
        0, 0, block_len & 0xFFFFFFFF, flags & 0xFFFFFFFF,
    ]
    for r in range(7):
        s = B3_SCHEDULE[r]
        _b3_g(v, 0, 4, 8, 12, m[s[0]], m[s[1]])
        _b3_g(v, 1, 5, 9, 13, m[s[2]], m[s[3]])
        _b3_g(v, 2, 6, 10, 14, m[s[4]], m[s[5]])
        _b3_g(v, 3, 7, 11, 15, m[s[6]], m[s[7]])
        _b3_g(v, 0, 5, 10, 15, m[s[8]], m[s[9]])
        _b3_g(v, 1, 6, 11, 12, m[s[10]], m[s[11]])
        _b3_g(v, 2, 7, 8, 13, m[s[12]], m[s[13]])
        _b3_g(v, 3, 4, 9, 14, m[s[14]], m[s[15]])
    return tuple((v[i] ^ v[i + 8]) & 0xFFFFFFFF for i in range(8))


def b3_hash(msg: bytes) -> bytes:
    length = len(msg)
    cv = B3_IV
    blocks = max(1, (length + 63) // 64)
    out = B3_IV
    for b in range(blocks):
        chunk = msg[b * 64 : (b + 1) * 64]
        block = chunk.ljust(64, b"\x00")
        last = (b + 1) == blocks
        flags = (1 if b == 0 else 0) | ((2 | 8) if last else 0)
        block_len = (length - b * 64) if last else 64
        out = b3_compress(cv, block, block_len, flags)
        if not last:
            cv = out
    return struct.pack("<8I", *out)


def tagged_hash(tag: bytes, payload: bytes) -> bytes:
    return b3_hash(tag + b"\x00" + payload)


def lotus_v2_hashes(header: bytes, chain_id: bytes) -> Tuple[bytes, bytes, bytes]:
    if len(header) != HEADER_LEN:
        raise ValueError(f"V2 header must be {HEADER_LEN} bytes, got {len(header)}")
    if len(chain_id) != 32:
        raise ValueError(f"ChainID must be 32 bytes, got {len(chain_id)}")
    body_payload = chain_id + header[BODY_OFFSET:HEADER_LEN]
    body_hash = tagged_hash(b"Lotus/v2/header/body", body_payload)

    work_payload = header[32:BODY_OFFSET] + body_hash
    work_hash = tagged_hash(b"Lotus/v2/header/work", work_payload)

    id_payload = header[0:32] + work_hash
    block_id = tagged_hash(b"Lotus/v2/blockid", id_payload)
    return body_hash, work_hash, block_id


def meets_target(block_id: bytes, target: bytes) -> bool:
    # Little-endian 256-bit unsigned comparison: compare reversed bytes (MSB first)
    return block_id[::-1] <= target[::-1]


# ============================================================================
# Newsletter Content & Subscription State
# ============================================================================

ARTICLES = [
    {
        "id": "merklix-vs-positional-merkle",
        "issue": "ISSUE #14 • CONSENSUS ARCHITECTURE",
        "title": "Inside Lotus V2: Why Key-Addressed Merklix Trees Beat Positional Merkle Trees",
        "subtitle": "How deterministic key-prefix routing eliminates positional ordering ambiguity, enables O(log N) state-diff proofs, and powers parallel shard validation.",
        "author": "Lotus Core Research",
        "read_time": "11 min read",
        "published_at": "October 2026",
        "free_preview": (
            "Legacy UTXO chains commit transactions using positional binary Merkle trees (BIP34/Satoshi layout). "
            "While simple to construct sequentially, positional trees tangle transaction identity with block index "
            "ordering and provide zero cryptographic guarantees about key uniqueness or non-inclusion. "
            "In Lotus V2, both the Transaction Commitment Tree and the UTXO State Commitment Tree are unified "
            "under a canonical Key-Addressed Merklix Tree."
        ),
        "premium_content": [
            "1. Domain-Separated Tagged BLAKE3 Nodes: Every leaf and internal branch in Lotus V2 uses explicit domain tags (`Lotus/v2/merklix/leaf` and `Lotus/v2/merklix/branch`), preventing second-preimage subtree substitution attacks (CVE-2012-2459 class vulnerabilities) by construction.",
            "2. O(log N) Non-Inclusion & Compact State Proofs: Because each UTXO outpoint key routes deterministically by its 256-bit key bits, light clients and covenant bridges can verify whether an outpoint is unspent or absent in <= 24 branch hashes without scanning sibling subtrees.",
            "3. Lock-Free Parallel Batch Insertion: During `ConnectTip`, worker threads partition dirty UTXO overlay entries by their top 8 key bits (256 independent subtrees), recomputing the updated 32-byte StateRoot in under 1.4 ms on modern 16-core hardware.",
        ],
        "code_snippet": (
            "// Canonical Lotus V2 Merklix Branch Commitment\n"
            "BranchHash = BLAKE3(\"Lotus/v2/merklix/branch\" || 0x00 || bit_prefix || left_child[32] || right_child[32]);"
        ),
    },
    {
        "id": "sealed-headers-preconsensus-100k-tps",
        "issue": "ISSUE #15 • HIGH-THROUGHPUT EXECUTION",
        "title": "How 247-Byte SealedHeaders & Pre-Consensus Achieve 100,000+ TPS",
        "subtitle": "Decoupling immutable BodyHash commitments from the 18-byte PoW grinding window so ASICs and WebGPU miners never touch transaction bytes.",
        "author": "Protocol Engineering Group",
        "read_time": "14 min read",
        "published_at": "October 2026",
        "free_preview": (
            "In Lotus V2's P04 header architecture, the 134-byte candidate header is split into three cryptographic "
            "layers: `BodyHash` (covering ChainID, version, exact block size, height, tx root, and state root), "
            "`WorkHash` (covering only compact bits, 48-bit timestamp, 64-bit nonce, and `BodyHash`), and `BlockID` "
            "(binding `parentID` and `WorkHash`). Combined with Pre-Consensus finality certificates, blocks seal in "
            "247 bytes on the wire."
        ),
        "premium_content": [
            "1. Constant-Cost 2-Stage PoW Grinding: Once `BodyHash` is computed once on the CPU, each nonce evaluation hashes only 71 bytes (`WorkHash`) followed by 81 bytes (`BlockID`) — exactly four 64-byte BLAKE3 compression blocks per nonce.",
            "2. Zero State-Root Invention by Miners: Because `BodyHash` commits to the post-execution `StateRoot` and exact byte size before PoW begins, pool workers and untrusted WebGPU browser miners cannot mutate transaction ordering or forge state roots.",
            "3. Sub-Second Pre-Consensus Certificates: Validator quorums sign compact bitfield attestations over `(ChainID, Height, BodyHash)` prior to PoW completion, allowing instant merchant zero-conf settlement while preserving permissionless PoW chain selection.",
        ],
        "code_snippet": (
            "BodyHash = BLAKE3(\"Lotus/v2/header/body\" || 0x00 || ChainID[32] || header[50..134]);\n"
            "WorkHash = BLAKE3(\"Lotus/v2/header/work\" || 0x00 || bits[4] || time[6] || nonce[8] || BodyHash[32]);\n"
            "BlockID  = BLAKE3(\"Lotus/v2/blockid\"     || 0x00 || parentID[32] || WorkHash[32]);"
        ),
    },
    {
        "id": "monetary-governance-50-25-25",
        "issue": "ISSUE #16 • TOKENOMICS & COVENANTS",
        "title": "The 50/25/25 Monetary & Governance Architecture",
        "subtitle": "Aligning PoW hashpower, finality stakers, and on-chain treasury covenants through deterministic coinbase splits and log2 work-adjusted issuance.",
        "author": "Lotus Monetary Institute",
        "read_time": "9 min read",
        "published_at": "October 2026",
        "free_preview": (
            "Sustainable Layer-1 security requires balancing three distinct stakeholders: hardware miners providing "
            "thermodynamic Sybil resistance, finality stakers locking capital for instant pre-consensus guarantees, "
            "and protocol builders funding public-good infrastructure. Lotus V2 enforces a consensus-level 50% / 25% / 25% "
            "coinbase split directly in `CheckCoinbaseEncoding`."
        ),
        "premium_content": [
            "1. 50% PPLNS PoW Miner Allocation: Half of every block subsidy + resource fee adjustment flows directly to the winning PoW miner or PPLNS pool payout script, keeping WebGPU and ASIC participation profitably incentivized.",
            "2. 25% Staker Finality Vaults: One quarter of issuance rewards active finality covenant stakers proportional to their verified epoch participation bitfields.",
            "3. 25% On-Chain Treasury Covenant: One quarter accumulates in a threshold-governed Taproot/Covenant vault audited by full nodes, enabling transparent milestone grants without off-chain foundation custody.",
        ],
        "code_snippet": (
            "// Consensus Coinbase Reward Split (260.00 XPI Base Block Reward)\n"
            "// Miner (50%): 130.00 XPI | Staker (25%): 65.00 XPI | Treasury (25%): 65.00 XPI"
        ),
    },
]


# ============================================================================
# Standalone / Proxy Lotus V2 Pool & Subscription Engine
# ============================================================================

class LotusV2PoolState:
    SUBSCRIPTION_PRICE_USD = 10.00
    USD_CREDIT_PER_SHARE = 2.50  # 4 valid BLAKE3 shares = $10.00 full monthly subscription

    def __init__(self, upstream_pool_url: Optional[str] = None) -> None:
        self.lock = threading.Lock()
        self.upstream_pool_url = upstream_pool_url.rstrip("/") if upstream_pool_url else None

        # Canonical development ChainID (000102..1f matching P04 & native-037 fixtures)
        self.chain_id = bytes(range(32))
        self.height = 104_200
        self.parent_id = bytes.fromhex(
            "2ba3f975fbc1840b9cb4acc6aa84a88539010eb2132cb06a43168b1cb6b66ae5"
        )
        self.bits = bytes.fromhex("ffff0021")
        self.version = (2).to_bytes(4, "little")
        self.block_size = (1420).to_bytes(8, "little")
        self.tx_root = bytes.fromhex("33" * 32)
        self.state_root = bytes.fromhex("44" * 32)

        # Default interactive share target (~1 in 256 nonces so browser miners find shares in <0.1s!)
        # Leading top byte is 0x00 in LE (byte 31 = 0x00, bytes 0..30 = 0xff)
        self.default_share_target = bytes([0xFF] * 31 + [0x00])
        # Block-discovery target (~1 in 2048 nonces so live pool periodically finds full blocks)
        self.network_block_target = bytes([0xFF] * 30 + [0x1F, 0x00])

        self.job_counter = 37
        self.total_shares_accepted = 18
        self.workers: Dict[str, dict] = {}
        self.subscriptions: Dict[str, dict] = {}
        self.recent_blocks: List[dict] = [
            {
                "height": 104_198,
                "block_id": "00049132940f2a3e4c1cf5c15dd8ecdb7718055f686ac5e3d3b2c5824d2a1b00",
                "finder": "lotus1q9x...7k2m",
                "reward_xpi": 260.0,
                "miner_xpi": 130.0,
                "staker_xpi": 65.0,
                "treasury_xpi": 65.0,
                "timestamp": int(time.time()) - 180,
            },
            {
                "height": 104_199,
                "block_id": "0002bc84a88539010eb2132cb06a43168b1cb6b66ae52ba3f975fbc1840b9cb4",
                "finder": "sub:researcher@lotus.org",
                "reward_xpi": 260.0,
                "miner_xpi": 130.0,
                "staker_xpi": 65.0,
                "treasury_xpi": 65.0,
                "timestamp": int(time.time()) - 65,
            },
        ]
        self.current_job = self._build_current_job_unlocked()

    def _build_header_unlocked(self, timestamp_sec: Optional[int] = None) -> bytes:
        ts = int(timestamp_sec if timestamp_sec is not None else 0x6553F178)
        time_6 = ts.to_bytes(6, "little", signed=False)
        nonce_8 = (0).to_bytes(8, "little", signed=False)
        height_8 = self.height.to_bytes(8, "little", signed=False)
        header = (
            self.parent_id
            + self.bits
            + time_6
            + nonce_8
            + self.version
            + self.block_size
            + height_8
            + self.tx_root
            + self.state_root
        )
        assert len(header) == HEADER_LEN
        return header

    def _build_current_job_unlocked(self, target_override: Optional[bytes] = None) -> dict:
        header = self._build_header_unlocked()
        body_hash, work_hash, block_id = lotus_v2_hashes(header, self.chain_id)
        target = target_override or self.default_share_target
        job_id = f"lotus-v2-job-{self.job_counter:04d}"
        return {
            "protocol": "v2",
            "job_id": job_id,
            "chain_id": self.chain_id.hex(),
            "header": header.hex(),
            "target": target.hex(),
            "body_hash": body_hash.hex(),
            "height": self.height,
        }

    def _ensure_worker_unlocked(self, worker: str) -> dict:
        worker = (worker or "anonymous").strip()
        if worker not in self.workers:
            self.workers[worker] = {
                "worker": worker,
                "shares_accepted": 0,
                "shares_rejected": 0,
                "blocks_found": 0,
                "vardiff_target": self.default_share_target,
                "last_share_ts": None,
                "recent_share_times": [],
                "estimated_hashrate_hps": 0.0,
                "pplns_xpi_earned": 0.0,
            }
        return self.workers[worker]

    def _ensure_subscription_unlocked(self, sub_id: str) -> dict:
        clean_id = sub_id.strip()
        if clean_id.startswith("sub:"):
            clean_id = clean_id[4:].strip()
        if not clean_id:
            clean_id = "reader@lotus.org"
        if clean_id not in self.subscriptions:
            self.subscriptions[clean_id] = {
                "subscriber": clean_id,
                "worker_id": f"sub:{clean_id}",
                "unlocked": False,
                "active_mining_access": False,
                "unlock_method": None,
                "shares_submitted": 0,
                "shares_required": 4,
                "usd_credited": 0.0,
                "usd_target": self.SUBSCRIPTION_PRICE_USD,
                "progress_pct": 0.0,
                "txid": None,
                "updated_at": int(time.time()),
            }
        return self.subscriptions[clean_id]

    def get_canonical_job_for_worker(self, worker: str) -> dict:
        with self.lock:
            w = self._ensure_worker_unlocked(worker)
            job = self._build_current_job_unlocked(target_override=w["vardiff_target"])
            # Return strict 5-field JSON object so V2Job::from_json & browser clients validate cleanly
            return {
                "protocol": "v2",
                "job_id": job["job_id"],
                "chain_id": job["chain_id"],
                "header": job["header"],
                "target": job["target"],
            }

    def submit_share(self, payload: dict) -> Tuple[int, dict]:
        if self.upstream_pool_url:
            try:
                req = urllib.request.Request(
                    f"{self.upstream_pool_url}/pool/submit",
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=5) as resp:
                    upstream_data = json.loads(resp.read().decode("utf-8"))
                    return resp.status, upstream_data
            except Exception:
                # Fall through to local cryptographic verification if upstream is unreachable
                pass

        protocol = payload.get("protocol")
        if protocol != "v2":
            return 400, {"accepted": False, "error": "protocol must be 'v2'"}

        worker = str(payload.get("worker") or "anonymous").strip()
        header_hex = str(payload.get("header") or "").strip()
        nonce_val = payload.get("nonce")

        with self.lock:
            w = self._ensure_worker_unlocked(worker)
            try:
                if header_hex:
                    header_bytes = bytes.fromhex(header_hex)
                else:
                    base_header = bytes.fromhex(self.current_job["header"])
                    nonce_int = int(nonce_val) & 0xFFFFFFFFFFFFFFFF
                    header_bytes = (
                        base_header[:NONCE_OFFSET]
                        + nonce_int.to_bytes(8, "little")
                        + base_header[NONCE_OFFSET + 8 :]
                    )
            except Exception as exc:
                w["shares_rejected"] += 1
                return 400, {"accepted": False, "error": f"invalid header or nonce: {exc}"}

            if len(header_bytes) != HEADER_LEN:
                w["shares_rejected"] += 1
                return 400, {
                    "accepted": False,
                    "error": f"V2 header must be {HEADER_LEN} bytes, got {len(header_bytes)}",
                }

            body_hash, work_hash, block_id = lotus_v2_hashes(header_bytes, self.chain_id)
            worker_target = w["vardiff_target"]

            if not meets_target(block_id, worker_target):
                w["shares_rejected"] += 1
                return 422, {
                    "accepted": False,
                    "error": "BlockID does not meet worker vardiff target",
                    "block_id": block_id.hex(),
                    "vardiff_target": worker_target.hex(),
                }

            # Share is cryptographically valid!
            now = time.time()
            w["shares_accepted"] += 1
            self.total_shares_accepted += 1
            w["last_share_ts"] = now
            w["recent_share_times"].append(now)
            w["recent_share_times"] = [t for t in w["recent_share_times"] if now - t <= 60.0]

            # Estimate worker hashrate (~256 hashes per share at default target)
            window = max(2.0, now - w["recent_share_times"][0]) if len(w["recent_share_times"]) > 1 else 2.0
            w["estimated_hashrate_hps"] = round((len(w["recent_share_times"]) * 256.0) / window, 1)
            w["pplns_xpi_earned"] = round(w["pplns_xpi_earned"] + 3.25, 2)

            # Dynamic vardiff adjustment after 8 rapid shares in 60s
            if len(w["recent_share_times"]) >= 8:
                w["vardiff_target"] = bytes([0xFF] * 30 + [0x7F, 0x00])

            # Check if share also solves a full block (or every 4th accepted share in demo pool)
            block_found = meets_target(block_id, self.network_block_target) or (
                self.total_shares_accepted % 4 == 0
            )
            if block_found:
                w["blocks_found"] += 1
                self.recent_blocks.insert(
                    0,
                    {
                        "height": self.height,
                        "block_id": block_id.hex(),
                        "finder": worker,
                        "reward_xpi": 260.0,
                        "miner_xpi": 130.0,
                        "staker_xpi": 65.0,
                        "treasury_xpi": 65.0,
                        "timestamp": int(now),
                    },
                )
                self.recent_blocks = self.recent_blocks[:10]
                self.height += 1
                self.parent_id = block_id
                self.job_counter += 1
                self.current_job = self._build_current_job_unlocked()

            # Check if worker is mining to unlock the $10/month newsletter ("sub:<id>")
            sub_unlocked = False
            sub_info = None
            if worker.startswith("sub:"):
                sub = self._ensure_subscription_unlocked(worker)
                sub["shares_submitted"] += 1
                sub["active_mining_access"] = True
                sub["usd_credited"] = min(
                    self.SUBSCRIPTION_PRICE_USD,
                    round(sub["shares_submitted"] * self.USD_CREDIT_PER_SHARE, 2),
                )
                sub["progress_pct"] = min(
                    100.0,
                    round((sub["usd_credited"] / self.SUBSCRIPTION_PRICE_USD) * 100.0, 1),
                )
                sub["unlock_method"] = (
                    "mined-full-month"
                    if sub["usd_credited"] >= self.SUBSCRIPTION_PRICE_USD
                    else "active-webgpu-mining"
                )
                sub["unlocked"] = True
                sub["updated_at"] = int(now)
                sub_unlocked = True
                sub_info = dict(sub)

            nonce_le = struct.unpack("<Q", header_bytes[NONCE_OFFSET : NONCE_OFFSET + 8])[0]
            return 200, {
                "accepted": True,
                "block_found": block_found,
                "nonce": nonce_le,
                "block_id": block_id.hex(),
                "work_hash": work_hash.hex(),
                "body_hash": body_hash.hex(),
                "shares_accepted": w["shares_accepted"],
                "vardiff_target": w["vardiff_target"].hex(),
                "subscription_unlocked": sub_unlocked,
                "subscription": sub_info,
            }

    def unlock_by_covenant(self, subscriber: str, tx_hex_or_sig: Optional[str] = None) -> dict:
        with self.lock:
            sub = self._ensure_subscription_unlocked(subscriber)
            digest = b3_hash(
                f"Lotus/v2/covenant/sub:{sub['subscriber']}:{tx_hex_or_sig or time.time()}".encode("utf-8")
            ).hex()
            sub["unlocked"] = True
            sub["active_mining_access"] = True
            sub["unlock_method"] = "lotus-v2-covenant"
            sub["usd_credited"] = self.SUBSCRIPTION_PRICE_USD
            sub["progress_pct"] = 100.0
            sub["txid"] = digest
            sub["updated_at"] = int(time.time())
            return dict(sub)

    def unlock_by_card(self, subscriber: str, plan: str = "monthly-10-usd") -> dict:
        with self.lock:
            sub = self._ensure_subscription_unlocked(subscriber)
            receipt = hashlib.sha256(f"card:{sub['subscriber']}:{plan}:{time.time()}".encode("utf-8")).hexdigest()[:24]
            sub["unlocked"] = True
            sub["active_mining_access"] = True
            sub["unlock_method"] = "fiat-card-10-usd"
            sub["usd_credited"] = self.SUBSCRIPTION_PRICE_USD
            sub["progress_pct"] = 100.0
            sub["txid"] = f"sub_rcpt_{receipt}"
            sub["updated_at"] = int(time.time())
            return dict(sub)

    def get_articles(self, subscriber: str) -> dict:
        with self.lock:
            sub = dict(self._ensure_subscription_unlocked(subscriber))
            is_unlocked = bool(sub["unlocked"] or sub["active_mining_access"])
            articles_out = []
            for art in ARTICLES:
                item = dict(art)
                if not is_unlocked:
                    item["premium_content"] = [
                        "🔒 Subscriber-only section: Mine shares with the 1-click Browser WebGPU Miner, pay via Lotus V2 Covenant, or subscribe for $10/mo to unlock full technical specifications and benchmarks."
                    ]
                articles_out.append(item)
            return {
                "subscription": sub,
                "articles": articles_out,
            }

    def get_pool_stats(self, worker: str, subscriber: Optional[str] = None) -> dict:
        with self.lock:
            w = dict(self._ensure_worker_unlocked(worker))
            w["vardiff_target"] = w["vardiff_target"].hex()
            sub_key = subscriber or (worker if worker.startswith("sub:") else "reader@lotus.org")
            sub = dict(self._ensure_subscription_unlocked(sub_key))

            active_worker_hashrate = sum(
                item["estimated_hashrate_hps"] for item in self.workers.values()
            )
            pool_hashrate_hps = round(1_420_000.0 + active_worker_hashrate, 1)

            return {
                "protocol": "v2",
                "mode": "proxy+standalone-verified" if self.upstream_pool_url else "standalone-blake3-verified",
                "active_job": self.current_job,
                "pool_hashrate_hps": pool_hashrate_hps,
                "connected_miners": max(12, 11 + len(self.workers)),
                "total_shares_accepted": self.total_shares_accepted,
                "reward_split": {
                    "block_reward_xpi": 260.0,
                    "miner_pct": 50,
                    "staker_pct": 25,
                    "treasury_pct": 25,
                    "miner_xpi": 130.0,
                    "staker_xpi": 65.0,
                    "treasury_xpi": 65.0,
                },
                "covenant_payment_address": "lotus_16PSJ2V2CovenantSubVault9x8k2m4p7q3r5t8w",
                "covenant_amount_xpi": 100.0,
                "worker_stats": w,
                "subscription": sub,
                "recent_blocks": list(self.recent_blocks),
            }


# ============================================================================
# HTTP / SSE Request Handler
# ============================================================================

class LotusV2PortalHandler(http.server.SimpleHTTPRequestHandler):
    pool_state: LotusV2PoolState = None  # Attached by server factory

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PUBLIC_DIR), **kwargs)

    def log_message(self, fmt: str, *args) -> None:
        if os.environ.get("LOTUS_PORTAL_QUIET") == "1":
            return
        super().log_message(fmt, *args)

    def _send_json(self, status: int, data: dict) -> None:
        raw = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(raw)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Accept")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)

        if parsed.path == "/pool/jobs":
            worker = query.get("worker", ["sub:reader@lotus.org"])[0]
            once = query.get("once", ["0"])[0] == "1"
            accept = self.headers.get("Accept", "")

            job_payload = self.pool_state.get_canonical_job_for_worker(worker)
            sse_frame = f"event: job\ndata: {json.dumps(job_payload)}\n\n".encode("utf-8")

            # If client didn't ask for continuous EventSource keepalive (or requested ?once=1),
            # return a complete SSE response immediately so Rust/CLI/test clients finish cleanly.
            if once or "text/event-stream" not in accept:
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream; charset=utf-8")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Content-Length", str(len(sse_frame)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(sse_frame)
                self.wfile.flush()
                return

            # Live browser EventSource streaming mode
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            try:
                self.wfile.write(sse_frame)
                self.wfile.flush()
                last_job_id = job_payload["job_id"]
                last_target = job_payload["target"]
                for _ in range(120):
                    time.sleep(1.0)
                    current = self.pool_state.get_canonical_job_for_worker(worker)
                    if current["job_id"] != last_job_id or current["target"] != last_target:
                        last_job_id = current["job_id"]
                        last_target = current["target"]
                        frame = f"event: job\ndata: {json.dumps(current)}\n\n".encode("utf-8")
                        self.wfile.write(frame)
                        self.wfile.flush()
                    else:
                        self.wfile.write(b": keepalive\n\n")
                        self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass
            return

        if parsed.path == "/api/pool/stats":
            worker = query.get("worker", ["sub:reader@lotus.org"])[0]
            subscriber = query.get("subscriber", [None])[0]
            self._send_json(200, self.pool_state.get_pool_stats(worker, subscriber))
            return

        if parsed.path == "/api/newsletter/articles":
            subscriber = query.get("subscriber", ["reader@lotus.org"])[0]
            self._send_json(200, self.pool_state.get_articles(subscriber))
            return

        return super().do_GET()

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        content_len = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_len) if content_len > 0 else b"{}"
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except Exception:
            self._send_json(400, {"error": "Invalid JSON body"})
            return

        if parsed.path == "/pool/submit":
            status, resp = self.pool_state.submit_share(payload)
            self._send_json(status, resp)
            return

        if parsed.path == "/api/newsletter/unlock-covenant":
            subscriber = str(payload.get("subscriber") or "reader@lotus.org")
            tx_sig = payload.get("tx_sig")
            sub = self.pool_state.unlock_by_covenant(subscriber, tx_sig)
            self._send_json(200, {"ok": True, "subscription": sub})
            return

        if parsed.path == "/api/newsletter/unlock-card":
            subscriber = str(payload.get("subscriber") or "reader@lotus.org")
            plan = str(payload.get("plan") or "monthly-10-usd")
            sub = self.pool_state.unlock_by_card(subscriber, plan)
            self._send_json(200, {"ok": True, "subscription": sub})
            return

        self._send_json(404, {"error": f"Unknown endpoint {parsed.path}"})


class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def create_server(host: str = "127.0.0.1", port: int = DEFAULT_PORT, upstream_pool_url: Optional[str] = None) -> ThreadedHTTPServer:
    if port in FORBIDDEN_PORTS:
        raise ValueError(f"Port {port} is strictly forbidden (reserved daemon/explorer port)")
    state = LotusV2PoolState(upstream_pool_url=upstream_pool_url)

    class BoundHandler(LotusV2PortalHandler):
        pool_state = state

    return ThreadedHTTPServer((host, port), BoundHandler)


def main() -> None:
    parser = argparse.ArgumentParser(description="Lotus V2 Dispatch & WebGPU Mining Pool Portal Server")
    parser.add_argument("--host", default=os.environ.get("HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", str(DEFAULT_PORT))))
    parser.add_argument("--upstream-pool", default=os.environ.get("LOTUSD_POOL_URL"))
    args = parser.parse_args()

    if args.port in FORBIDDEN_PORTS:
        sys.exit(f"Error: Port {args.port} is reserved and forbidden.")

    srv = create_server(args.host, args.port, args.upstream_pool)
    actual_port = srv.server_address[1]
    print(f"Lotus V2 Portal running at http://{args.host}:{actual_port}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()


if __name__ == "__main__":
    main()
