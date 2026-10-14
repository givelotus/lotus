# BCHN ready-backlog measurement

This compares immutable upstream `abd433abe04f74780744b9eac06731f3690ce68a`
with the standalone MR 2174 commit
`640b8bd1c8e88107421a201828eaaf2b46802b28`. Neither candidate 04 nor NNG nor
ZeroMQ removal is included. The only overlay adds the same benchmark translation
unit to each source tree; production source is unchanged.

The change prioritizes newly ready children by modified fee rate. It adds heap
work; it is not an optimization of BCHN's already bounded dependency traversal.
For b backlog entries and maximum simultaneously ready backlog width w, the new
queue work is O(b log w), versus O(b) FIFO work. Existing parent-count/map lookup,
transaction processing and CTOR sorting costs remain. Long chains have w = 1;
wide fanout deliberately stresses the added queue cost.

## Reproduce

A local BCHN repository must contain both exact commits. The script creates its
own clones/builds and never resets an existing workspace or starts a node.
A fresh output path is required. Install normal BCHN CMake/Ninja dependencies.

```sh
python3 daemon/bench/bchn-miner/run.py \
  --source /path/to/bitcoin-cash-node \
  --output /tmp/bchn-ready-performance --jobs 6 --rounds 3 --evals 3
```

Both builds use `CMAKE_BUILD_TYPE=Release`, the same compiler/default target
architecture and identical flags. The script records compiler, hardware/OS,
complete CMake caches, exact revisions, binary/overlay hashes and raw logs.
The baseline/patched execution order reverses every round. Do not run the two
binaries concurrently. Each synthetic evaluation builds its fixture, validates
it, warms three templates, then collects ten individual elapsed-time samples.
Three rounds with three evaluations yield 90 samples per synthetic workload per
revision. Setup and output are outside the timed region. Timings include fresh
`BlockAssembler`/template construction, CTOR ordering, coinbase construction and
template destruction, not just the queue method.

Existing `AssembleBlock`, `GenerateBlock50ChainedTxs` and
`GenerateBlock500ChainedTxs` run unmodified with `-scaling=.1`, three evaluations
per round. Their upstream min/max/median statistics are recorded separately;
the report must not call these individual raw iteration timings.

## Fixtures and checks

All synthetic fixtures start with actual mined/matured regtest coinbase funds.
A funding transaction is mined, then dependent transactions are inserted in a
local mempool in topological order, using upstream `TestMemPoolEntryHelper` and
`addUnchecked`. This deliberately isolates assembly, not relay/admission policy;
some funding/fanout transactions exceed the standard relay size. No fabricated
coins or unrelated chain data is loaded.

Scripts match upstream's simple P2SH OP_DROP/OP_TRUE benchmark scripts. These
contain no signature operations; fixtures therefore record zero sigchecks.
They do not characterize expensive ECDSA/script validation. Full
`CreateNewBlock(..., checkValidity=true)` succeeds before every timed evaluation
(using the normal mining-template validity check without PoW/merkle checks),
including for the selection-only runs. Additional checks verify each selected
transaction appears once, all selected children have all their parents, actual
fees match template entries, the coinbase pays exactly subsidy plus actual fees,
full-capacity runs include all entries, and serialized blocks remain under their
configured capacity. Mining the funding block also validates its scripts and
accounting through the real node code.

Workloads:

- Independent: no backlog; deterministic mixed fees, 2,000/20,000 transactions.
- Chains: disjoint chains of length 100, increasing fees toward the tip,
  2,000/20,000/100,000 transactions. A newly ready backlog normally has width one.
- Diamonds: repeated split/two-child/join graphs, 2,000/20,000 transactions.
- Fanout: groups of one parent with up to 64 children,
  2,000/20,000/100,000 transactions.
- Wide: one parent with 1,999/19,999 children, a deliberate large-ready-queue
  stress case, not a claim about typical mainnet traffic.
- Constrained: 20,000-entry grouped/wide fanout with a 1,000,000-byte generated
  block limit; uncapped runs allow 32,000,000 bytes. The native assembler's
  coinbase reservation/termination heuristics still apply.
- Validated: grouped fanout, capped and uncapped, also times full validation
  after cache warming. Other synthetic cases skip full validation only inside
  the timed region.

Fanout children have deterministic actual fees and every third child has an
explicit +4,000-satoshi prioritization delta. Results report actual and modified
fees separately. Modified fees guide policy; they are not extra coinbase income.
The mining minimum is BCHN's default 1,000 satoshi/kB. Fanout parent fees
scale with output count so every parent meets this minimum while remaining
below its children in feerate. There is no free-parent/minimum-fee override and
no new CPFP policy. No artificial assembly time limit is imposed.

`results.json` contains every synthetic sample and fixture, percentile summaries
and paired median changes; raw console logs preserve upstream statistics.
Differences in selected fees describe these synthetic fixtures, not a projected
mainnet revenue increase. Shared-host load, allocator/cache effects and CPU
scheduling affect results; report spreads and avoid declaring tiny differences
significant. Larger dedicated-host/Linux runs and signed real-world mempool
replays remain useful independent follow-ups.
