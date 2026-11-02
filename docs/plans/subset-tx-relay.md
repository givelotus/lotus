# Subset transaction relay

Status: planned (not started). Depends on: Snowstorm core landing; f set by the (f, K) grid experiment.

## Change
lotusd currently announces every newly admitted transaction (inv) to every peer,
after a per-peer Poisson delay. Replace that with:

- On admission, announce the transaction immediately to f peers chosen uniformly
  at random, freshly per transaction, from peers not already known to have it
  (keep the existing known-inventory filter).
- No Poisson delay on transaction announcements.
- Block announcements are unchanged.

## Why
Snowstorm polls (pull) fill in anything announcements (push) miss, so announcing to
every peer is redundant. Push to a random subset plus pull from a random subset is
push-pull gossip (Karp et al., FOCS 2000), which converges faster than either alone
at much lower cost. The delay existed to batch announcements and avoid announcing back to
peers that announced first; with subset push there is little redundancy left to save,
and sending immediately shrinks first-round reconciliation differences.

## Non-goals
Origin privacy. Reconciliation replies reveal where a transaction appeared first;
that is accepted.

## Value of f
Provisional f = ceil(D/4), D = connected compatible peers. Final value from the
(f, K) grid experiment on the Snowstorm reference simulator.

## Where in the code
net_processing: the transaction relay path (RelayTransaction or equivalent, which
queues the inv for every peer) and the per-peer inv trickle timer in SendMessages.
Confirm exact names in daemon/lotusd before implementing.