# BCHN MR 2174 performance measurements

The ready-child priority change has a measurable cost when many skipped children
become eligible together. It improves which transactions fit into a constrained
block; it does not speed up BCHN's dependency traversal. Independent and long-chain
controls show no convincing change on this shared host. A large ready queue costs
more CPU work and wall time, as expected from replacing FIFO with a fee heap.

## Exact comparison and method

- Upstream: `abd433abe04f74780744b9eac06731f3690ce68a`.
- Standalone submitted MR: `640b8bd1c8e88107421a201828eaaf2b46802b28`.
- Apple M5 Max, 18 logical CPUs, 48 GiB RAM, macOS 26.6 (25G72).
- Apple clang 21.0.0 (clang-2100.1.1.101), native arm64 Release builds (`-O3`),
  identical options/dependencies. No diagnostic-mempool/NNG/ZeroMQ-removal patch.
- Three rounds, three evaluations per round, ten measured templates per synthetic
  evaluation, after three warm-ups. Baseline/patched process order reverses each
  round. That is 90 raw samples per workload per revision.
- Setup, mining/funding, mempool insertion, warm-up and result output are outside
  timing. Selection-only timings cover complete `CreateNewBlock` including CTOR,
  coinbase and destruction, with template validation disabled only inside timing.
- All fixtures pass the native mining-template validity check before timing,
  including script checks; explicit accounting/parent/size checks also pass.
  Funds originate in mined, matured regtest coinbases. Fixture insertion bypasses
  relay policy via `addUnchecked`, as upstream benchmarks do. Mining minimum
  fee remains BCHN's default 1,000 satoshi/kB; all parents meet that minimum.

The machine was concurrently running unrelated builds/tests and Guix. Timing
spreads include scheduling/allocator/cache effects and are not confidence
intervals. These samples are repeated measurements of fixed synthetic fixtures,
not independent real-world traffic samples. Small changes and apparent speedups
must not be interpreted as algorithmic improvements.

## Wall-clock results

Synthetic values are median milliseconds, with p10–p90 in parentheses. Full
uncapped runs select all entries. `Validated` includes the warmed normal template
validity check in the timed region; other rows validate beforehand only. Scripts
are simple P2SH OP_DROP/OP_TRUE, with zero signature checks, so the validated rows
do not estimate expensive signature workloads.

| Workload | Upstream ms (p10–p90) | MR 2174 ms (p10–p90) | Median change |
| --- | ---: | ---: | ---: |
| Chains100000 | 62.328 (54.785–73.994) | 57.619 (52.409–71.220) | -7.6% |
| Chains2000 | 0.433 (0.409–0.597) | 0.455 (0.412–0.688) | +5.2% |
| Chains20000 | 7.410 (6.994–8.608) | 7.403 (6.918–10.537) | -0.1% |
| Diamonds2000 | 0.385 (0.372–0.572) | 0.392 (0.374–0.444) | +1.8% |
| Diamonds20000 | 6.221 (5.855–7.337) | 5.862 (5.653–7.505) | -5.8% |
| Fanout100000 | 68.869 (61.111–81.040) | 79.469 (73.157–89.337) | +15.4% |
| Fanout2000 | 0.419 (0.408–0.485) | 0.603 (0.560–0.863) | +43.8% |
| Fanout20000 | 7.588 (6.880–10.340) | 9.391 (8.640–11.288) | +23.8% |
| Fanout20000Cap | 3.512 (3.117–4.075) | 4.284 (3.673–5.715) | +22.0% |
| Fanout20000CapValidated | 22.519 (19.845–30.436) | 22.962 (20.782–29.808) | +2.0% |
| Fanout20000Validated | 97.822 (88.720–128.203) | 95.252 (87.919–128.849) | -2.6% |
| Independent2000 | 0.184 (0.172–0.311) | 0.194 (0.183–0.249) | +5.3% |
| Independent20000 | 6.508 (5.424–8.904) | 6.474 (5.504–8.529) | -0.5% |
| Wide2000 | 0.445 (0.418–0.706) | 0.845 (0.784–1.013) | +89.9% |
| Wide20000 | 8.117 (7.110–10.203) | 17.594 (16.102–21.111) | +116.8% |
| Wide20000Cap | 5.554 (4.977–6.775) | 7.193 (6.566–8.888) | +29.5% |

Grouped fanout has up to 64 children per parent; wide fanout has one parent
with 1,999 or 19,999 children. The latter is a deliberate consensus-valid stress
case whose large parent is nonstandard for relay; it is not presented as a
representative mainnet mempool. Chains have length 100. `Cap` limits generated
blocks to 1,000,000 bytes; other cases allow 32,000,000 bytes. Full details and
reproduction commands are in [the harness guide](../bench/bchn-miner/README.md).

The unchanged upstream benchmarks use three evaluations in each of three rounds
at `-scaling=.1`; below is the median of their per-round median timings. Raw
min/max/evaluation statistics remain in the logs. Their small differences are
consistent with shared-host noise.

| Existing upstream benchmark | Upstream ms | MR 2174 ms |
| --- | ---: | ---: |
| AssembleBlock | 0.114 | 0.113 |
| GenerateBlock50ChainedTxs | 0.174 | 0.178 |
| GenerateBlock500ChainedTxs | 1.771 | 1.713 |

## Selection result and interpretation

The 20,000-entry wide-fanout fixture with a 1 MB block cap selects 1,909
transactions and produces the same 998,999-byte block size on both revisions.
Selection-only time increases from 5.554 to 7.193 ms (+1.639 ms, +29.5%).

| Fees in that constrained template | Upstream satoshis | MR 2174 satoshis | Change |
| --- | ---: | ---: | ---: |
| Actual fees paid | 10,352,318 | 14,769,516 | +42.7% |
| Modified fees used by selection | 12,896,318 | 22,401,516 | +73.7% |

Every third child has a +4,000-satoshi prioritization delta. Actual fees and
modified fees are deliberately reported separately; deltas do not increase the
coinbase. This fixture demonstrates the selection behavior, not a projected
mainnet revenue increase. The 64-child grouped fixture has a smaller constrained
selection difference: 4,555 transactions/999,005 bytes on both, actual fees
21,209,030 → 21,242,027 and modified fees 27,373,030 → 27,446,027 satoshis.

Both versions already traverse direct dependencies with parent counts. The new
queue contributes O(b log w) work for b backlog entries and ready width w, versus
O(b) FIFO work. Chain width one shows essentially unchanged 20,000-entry timing;
large widths expose the added comparisons. No CPFP behavior or new global
fee-index policy was introduced. Dedicated-host/Linux measurements and signed
real-mempool replays would be useful independent follow-ups; this measurement
adds no mainnet performance, synchronization or reproducible-binary claim.

## Evidence and proposed maintainer response

[Structured results with all raw samples](evidence/bchn-mining-performance-20261014/results.json),
[environment, exact flags and binary/source hashes](evidence/bchn-mining-performance-20261014/environment.json),
and twelve `run-*.log` files in the same directory preserve the measurement.
The code and raw data are a local review artifact; no response has been posted.

> I measured the exact upstream and MR commits using identical clang 21 Release
> builds on an M5 Max, with repeated warmed block construction. The change costs
> work when the ready backlog gets wide: for 20k transactions, independent txs
> and chains were essentially unchanged (~6.5 and ~7.4 ms), while groups of up to
> 64 ready children increased from 7.59 to 9.39 ms. An intentionally extreme
> 19,999-child fanout increased from 8.12 to 17.59 ms.
>
> With a 1 MB cap, that wide-fanout case increased from 5.55 to 7.19 ms while
> selecting the same 1,909 transactions; actual fees increased from 10.35M to
> 14.77M satoshis, and modified fees from 12.90M to 22.40M. This demonstrates
> the intended selection tradeoff, not an expected mainnet revenue percentage.
> The extra heap work is O(b log w), replacing FIFO's O(b), where w is the ready
> backlog width. Upstream's small assembly/chain benchmarks were within a few
> percent. These are synthetic consensus-valid fixtures on a shared host, so I
> would not claim a speedup or attach significance to small timing differences.
