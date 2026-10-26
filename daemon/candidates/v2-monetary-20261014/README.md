# V2 monetary arithmetic review packet

**Status: REVIEW.** This one-commit mailbox applies to ABC/V2 source commit
`33563a7341b6393bf50246c25ab7acb18c31da5c` and produces tree
`88e74840201f34c0babe98d674d7adb8cd176d06`. The isolated implementation
is `/tmp/lotus-v2-monetary-review` at `98b4f17d202f3dd732fc18a26a437f34d4edbc25`.
No canonical series, source pin, workspace, node or release was changed.

The slice mirrors the parameterized P05/P06/C16 Python reference. It reuses the
existing `MonetaryState` wire layout and transaction/output models. It checks
genesis zero native issuance without stepping the recurrence; block 1 then uses
the genesis state. Subsequent steps compute the telescoping bootstrap draw,
exact integer work-ratio square root and tail clipping, checked u128 fees and
cost sums, parabolic costs, frozen-accounting EMA, enforcement burn floor,
token-output deduction once, odd-fee split, reward-funded coinbase byte floor,
underclaim and explicit burn. All constants are caller-supplied in an explicit
`MonetaryProfile`; only the specified 1000 atoms per decimal kB fee rate is
fixed. Wide work/tail arithmetic uses Boost.Multiprecision headers. The
standalone CMake harness locates Homebrew Boost or accepts
`-DLOTUS_BOOST_INCLUDE=<path>`; daemon integration must provision the same
header dependency or select an equivalent reviewed wide-integer backend.

The API expects independently checked per-transaction input/output records,
serialized bytes and static charges; `AccountValidatedOrdinary` derives
serialized length, output count and explicit burn from the native transaction
and the earlier ordinary validator's effects. It still relies on those effects
having come from successful ordinary validation. The block transition expects
an independently validated coinbase output sum, frame-prefix byte count,
accounting/enforcement cost totals and exact target-derived work. It does not
parse/connect a block, validate coinbase identity/context, calculate primitive
costs, enforce full P05 VM charges, select Avalanche payouts, check roots or
persist UTXO/monetary undo. Those remain block integration gates. No production
parameter manifest or economic simulation is provided by this packet.

Validation in the isolated source:

```sh
cmake -S src/lotus_v2/monetary_test -B /tmp/lotus-v2-monetary-build-debug \
  -DCMAKE_BUILD_TYPE=Debug \
  -DCMAKE_CXX_FLAGS='-O0 -g -fsanitize=undefined -fno-sanitize-recover=all'
cmake --build /tmp/lotus-v2-monetary-build-debug -j4
ctest --test-dir /tmp/lotus-v2-monetary-build-debug --output-on-failure
python3 src/lotus_v2/monetary_test/check_reference.py \
  /tmp/lotus-v2-monetary-build-debug/lotus_v2_monetary_test \
  /private/tmp/lotus-v2-repo/tools/lotus-v2-reference
```

Debug and Release CTest each passed 1/1. Each binary passed 300 independent
Python/native differential cases (26 accepted, 274 intentionally rejected),
plus hand-derived genesis, issuance, tail, cost, odd-fee, token-burn,
explicit-burn, overclaim and checked-width tests. A fresh `git am
--keep-non-patch` replay in `/tmp/lotus-v2-monetary-mailbox-replay` matched the
source tree exactly, and `git diff --check` passed. Exact source/spec digests
are in `manifest.json` because the draft may change.
