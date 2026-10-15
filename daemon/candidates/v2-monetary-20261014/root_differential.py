#!/usr/bin/env python3
"""Root-review differential: bias toward accepted transitions and wide values.

Usage: monetary_diff_root.py NATIVE_EXE REFERENCE_DIR [COUNT]
"""
import random, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.argv[2]).resolve()))
from lotus_v2_reference.monetary import MonetaryState, OrdinaryTx, Profile, advance

P = Profile(2, 3, 2, 4, 3, 5, 2, 2000, 3, 1000)  # must match test_monetary.cpp
count = int(sys.argv[3]) if len(sys.argv) > 3 else 20000
rng = random.Random(0x5EED2026)
rows, expected = [], []
U64 = (1 << 64) - 1
for i in range(count):
    wide = i % 5 == 0
    reserve = rng.randrange(0, U64 if wide else 100000)
    tail = rng.randrange(2, 2001)
    prev_work = rng.randrange(1, U64 if wide else 1 << 20)
    work = rng.randrange(1, U64 if wide else 1 << 20)
    ema = rng.randrange(0, 64)
    size = rng.randrange(1, 400)
    tokens = rng.randrange(0, 4)
    fee = max(size, 6 * tokens) + rng.randrange(0, 2000)  # usually above floors
    explicit_burn = rng.randrange(0, 101)
    cb_bytes = rng.randrange(1, 300)
    prefix = rng.randrange(1, 4)
    account = rng.randrange(0, 40)
    enforce = account + rng.randrange(0, 40)
    # Pick payout under the entitlement most of the time.
    payout = rng.randrange(0, 4000)
    cb_burn = rng.randrange(0, min(payout, 50) + 1)
    row = (reserve, tail, prev_work, ema, work, fee, size, tokens,
           explicit_burn, payout, cb_burn, cb_bytes, prefix, account, enforce)
    rows.append(row)
    try:
        tx = OrdinaryTx(fee + 100, 100, size, tokens, explicit_burn)
        r = advance(P, MonetaryState(reserve, tail, prev_work, ema), work=work,
                    transactions=(tx,), coinbase_native_outputs=payout,
                    coinbase_native_burn=cb_burn, coinbase_bytes=cb_bytes,
                    tx_frame_prefix_bytes=prefix, account_block_cost=account,
                    enforce_block_cost=enforce)
        # Native prints only the low byte of prev_work.
        expected.append(" ".join(map(str, (
            r.state.bootstrap_reserve, r.state.tail_subsidy, r.state.prev_work & 255,
            r.state.ema_block_cost, r.bootstrap_issued, r.subsidy, r.total_fees,
            r.token_burn, r.burned_fees, r.required_underclaim, r.actual_underclaim,
            r.spendable_supply_delta))))
    except ValueError:
        expected.append("ERR")
inp = "".join(" ".join(map(str, row)) + "\n" for row in rows)
out = subprocess.run([sys.argv[1], "--vectors"], input=inp, text=True,
                     capture_output=True, check=True).stdout.splitlines()
assert len(out) == len(expected), (len(out), len(expected))
bad = [(i, g, w) for i, (g, w) in enumerate(zip(out, expected)) if g != w]
acc = sum(e != "ERR" for e in expected)
for i, g, w in bad[:5]:
    print("MISMATCH", i, rows[i], "native=", g, "python=", w)
print(f"{count} vectors, {acc} accepted, {count-acc} rejected, {len(bad)} mismatches")
sys.exit(1 if bad else 0)
