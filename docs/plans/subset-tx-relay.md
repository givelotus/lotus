# Subset transaction relay

Status: the subset announcement itself shipped in `ecashd` and is inherited by
Lotus V2. One gap remained: peers with no way to recover a skipped announcement
were included in the subset. The fix is the draft pull request
https://github.com/givelotus/bitcoin-abc/pull/1. The final value of `f` is
undetermined.

Compared against the published tips `origin/ecashd` 578f015bdf (givelotus/bitcoin-abc)
and `origin/main` 666033be0e (givelotus/lotusd). `net_processing.cpp` differs between
them, but not in fan-out selection or the announcement timer.

## What is already done

An earlier version of this plan said the node announces every transaction to every
peer after a per-peer Poisson delay. That stopped being true with `50cc208ab5`
(`net: relay transactions to a fan-out of peers through one queue`).

| The plan asked for | What the code does |
|---|---|
| Announce to `f` peers picked uniformly, freshly per transaction | Done, in `DrainRelayQueue`, by partial Fisher-Yates per transaction |
| Skip peers known to have the transaction | Done. The known-inventory filter decides who is a candidate, and the send loop checks it again |
| No Poisson delay on transaction announcements | Done on every path (see below) |
| Block announcements unchanged | Done |
| Announce immediately on admission | Replaced by a fixed tick, deliberately (see below) |
| `f = ceil(D/4)` | Differs (see below) |

Three things exist that the plan did not describe:

- Transactions this node originated (wallet, RPC) go to every candidate.
- A child also follows its nearest recently relayed parent, through a 50,000-entry
  route memory. A transaction can therefore reach more than `f` peers.
- Reconciliation (`-txreconinterval`, default 250 ms, over `-txreconwindow`, default
  30 s) is the pull half: a round-robin Merklix summary to one negotiating peer per
  interval.

### Poisson delays

No transaction announcement path uses one. `SendMessages` sends transaction `inv` and
`invshort`, and answers BIP35 `mempool` requests, on `-txrelaytick`. Short-id body
pushes (`-txrelaypushhb`, off by default) use the same tick.

The exponential timers still in `net_processing.cpp` are for avalanche proof
announcements (`INBOUND_`/`OUTBOUND_INVENTORY_BROADCAST_INTERVAL`, which only proofs
use now), address relay and `feefilter`. Two other delays touch transactions but are
not Poisson announcement delays: the fixed 200 ms and 2 s request delays in
`TX_REQUEST_PARAMS`, on the receiving side, and the 10 to 15 minute retry of
unbroadcast transactions, which goes back through the same queue.

### Immediate send against the 10 ms tick

Announcements wait for the next `-txrelaytick` boundary, 10 ms by default and settable
down to 1 ms. Sending truly on admission is not worth doing:

- The plan's reason was to shrink first-round reconciliation differences. Summaries
  leave out the newest two reconciliation intervals (500 ms by default), so a wait of
  at most 10 ms cannot change what a first round sees.
- `contrib/bench/tx-relay/RESULTS.md` records the one-hop delay from accept to queued
  announcement as median 3.1 ms and p90 9.7 ms. It also records per-tick messages as
  the main reason bytes per transaction exceed the old relay's at low rates.
  Per-transaction sends can only make that worse.

### The `f` formula

Code: `clamp(max(min, ceil(pct x D)), min, max)` with defaults 8, 0.25 and 32. The
plan's formula has neither bound.

| Relay peers `D` | Plan `ceil(D/4)` | Code at defaults |
|---|---|---|
| 8 | 2 | 8 (every peer) |
| 16 | 4 | 8 |
| 32 | 8 | 8 |
| 33 | 9 | 9 |
| 128 | 32 | 32 |
| 256 | 64 | 32 |
| 1024 (default connection limit) | 256 | 32 |

The two agree only from 29 to 128 peers. No code is needed to run the plan's formula:
`-txrelayfanoutmin=1 -txrelayfanoutpct=0.25 -txrelayfanoutmax=100000` gives it. Changing
the defaults would be tuning without evidence, which is not a gap.

## The real gap

The plan's argument is that pull fills in what push misses, so pushing to everyone is
redundant. That only holds for a peer that has a pull path. The code applied fan-out
to every relay peer, including peers that never negotiated reconciliation:

- stock Bitcoin ABC nodes, which ignore `sendinvshort`;
- light clients using BIP37 filters;
- every peer of a node running with `-txreconinterval=0` or `-txrelayshortids=0`.

For those peers, an announcement is the only way to learn of an unconfirmed
transaction from this node, and a skipped one is never made up. `ecashd` is meant to
stay compatible with stock ABC, so this matters on the default configuration.

As arithmetic, not a measurement: a stock node with 8 neighbours, each picking 10 of
its 40 relay peers independently, is skipped by all 8 for about 10% of transactions
(0.75^8). `RESULTS.md` already records the failure mode with reconciliation off and 30%
of the nodes silent: one of three runs never delivered two node-transactions. No
recorded run used a mixed network of stock and reconciling peers.

**The fix.** Peers that negotiated reconciliation stay in the fan-out, and `D` counts
only them. All other relay peers get every announcement, as they would from a stock
node. This only ever adds announcements, and only to peers that have no fill-in, so it
is safe with stock ABC and on by default. Between nodes that all reconcile, nothing
changes. `-txrelayfloodnonrecon=0` restores the old selection; the silent-node
benchmark needs it to keep modelling silent peers that use up fan-out slots.

**Tier.** `ecashd`: it is about stock peers, and has no V2 or Snowstorm code. V2 inherits
it on the next restack. The patch applies cleanly to `origin/main`, but V2 has not been
built with it.

## The Snowstorm dependency

It is not real for anything above. Reconciliation already provides the pull half, and
the fix depends only on whether a peer negotiated it. The original wording, "Depends on:
Snowstorm core landing", no longer applies.

Snowstorm remains separate. `src/snowstorm/` on `origin/snowstorm/implementation` is
not called from `net_processing.cpp`, `net.cpp` or `init.cpp` on that branch, and neither
stack contains it. Those branches carry their own older copy of the fan-out code.

## Still open

- **Final `f`: undetermined.** The (f, K) grid experiment was never run. No results
  exist in this repository, on the `snowstorm/*` branches, or under `~/repos/archive`.
  The simulator in `~/repos/archive/snowstorm-research-sim` could not run it as it
  stands: it has no announcement fan-out parameter, and it is marked superseded. The
  in-tree `contrib/devtools/relay-sim` varies fan-out (which it calls `K`) against
  reconciliation, not Snowstorm polls, so it does not answer this either.
- **Whether Snowstorm polls justify a lower `f`.** Only a V2 or Snowstorm tier could
  use one. Anything reducing announcements below the current defaults has to be
  default-off in `ecashd`, because stock peers have no polling. This waits for Snowstorm
  to be wired in and for the experiment.
- **Slots spent on filtered peers.** A reconciling peer picked by fan-out whose
  `feefilter` rejects the transaction uses up a slot, and the send loop then drops the
  announcement. Effective fan-out can be lower than `f` when fee filters rise. There is
  no measurement showing this matters.
- **Reconciliation reach at high peer counts.** One peer per 250 ms means a node with
  more than 120 reconciling peers revisits each less often than the 30 s window. A peer
  still hears summaries from its other neighbours, so this should affect timing rather
  than reachability, but it has not been measured.
- **Mixed-network measurement.** Neither the simulator nor the cluster benchmark has
  modelled a network of stock and reconciling peers.

## Non-goals

Origin privacy. Reconciliation replies reveal where a transaction appeared first, and a
node's own transactions go to all of its peers at once. Both are accepted.

## Why subset push at all

Push to a random subset plus pull from a random subset is push-pull gossip (Karp et al.,
FOCS 2000), which converges faster than either alone at much lower cost.
