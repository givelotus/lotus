# IMPCPD — Iterative Multi-Perspective Code Plan Debugging
## Applied to Lotus Daemon Patches

Adapted from `~/repos/finch/src/planning/impcpd_methodology.md`.

---

## Purpose

A patch touching consensus code can silently corrupt a live network, cause
irreversible forks, or open an exploit that drains funds. Standard "does it
compile and pass tests" review is not enough.

IMPCPD runs multiple independent specialist perspectives over a patch or plan.
Each persona only cares about their domain. Together they catch what any single
reviewer would miss.

This document describes how to apply IMPCPD to Lotus daemon patches specifically.
For general software plans, see the original in `~/repos/finch/`.

---

## Personas

### Regression (always active)

- Does this patch touch code paths used by existing consensus or mempool behavior?
- Could the change break currently passing functional tests or unit tests?
- Are shared types, structs, or function signatures modified without updating all call sites?
- Does it change the serialization of blocks, transactions, or network messages in a
  way that would reject valid data from existing peers?

### Consensus Correctness (always active for patches touching validation, mining, mempool)

- Does the change preserve the invariant that a valid PoW block is always accepted?
- Is every branch of the state machine (IBD, normal operation, reorg, park) handled?
- If the patch changes activation logic: is the activation time/height applied
  consistently across mainnet, testnet, and regtest?
- If the patch changes coinbase validation: are all code paths (initial block download,
  reorg, accept-from-peer) updated, not just the happy path?
- Does the patch introduce any non-determinism? (Different nodes must reach the
  same conclusion from the same block data.)

### Security (activates when patch touches: script evaluation, signature checking,
  key derivation, address encoding, RPC auth, P2P message handling)

- Can a malformed or malicious peer message trigger the changed code path?
- Does the patch add any new way for an external input to influence consensus?
- Are new RPC methods properly access-controlled?
- Does the patch log or transmit anything that should be private (private keys,
  seeds, internal state)?

### Edge Cases (always active)

- What happens at block height 0 (genesis)?
- What happens when the mempool is empty?
- What happens during a reorg that goes back more than one block?
- What happens when the Avalanche quorum is not established (or disabled)?
- What if a relevant config argument is not provided (defaults must be safe)?
- Integer overflow: are block heights, timestamps, amounts, and sigop counts
  checked for overflow where relevant?

### Completeness (always active)

- Are all three network types (mainnet, testnet, regtest) updated if the patch
  changes consensus parameters?
- If a new activation function is added, is it called in every relevant place
  (validation.cpp, minerfund.cpp, activation.cpp, init.cpp)?
- Are functional tests updated to cover the new behavior?
- Does the series file reference this patch? Is it in the right position?
- Does the patch have correct context lines for the target base commit?
  (`git apply --check` must pass cleanly.)
- If the patch was originally written for a different base (eCash, BCHN, etc.),
  has the Portability persona been run? A patch that applies but silently uses a
  stale API is worse than one that fails to apply — it compiles and ships wrong.

### Tests & Docs (always active)

Every patch that changes consensus behavior MUST include:
- At minimum one functional test or unit test that would fail before the patch
  and pass after.
- If the patch adds a new activation time: a functional test that mines through
  the activation boundary and verifies pre/post behavior.
- If the patch changes coinbase outputs: the minerfund functional test must be updated.

Every patch that changes the public API (RPC, CLI args, network messages) MUST:
- Update the relevant help text and documentation strings.
- Update `daemon/docs/patch-strategy.md` if it changes patch status.

### Portability (activates when the patch has been ported from one base to another,
  e.g., eCash v0.24.11 → bitcoin-abc 252182e9, or ecash series → bchn series)

- Are the diff headers updated to the correct file paths in the target base?
  (e.g., did `src/miner.cpp` move to `src/node/miner.cpp`?)
- Are the git blob hashes in the diff header set to the target-base blobs,
  not the source-base blobs? (Wrong hashes cause silent `git apply --check` failures.)
- Are the context lines verbatim from the target base at the pinned commit?
  Even a single preceding reformatting commit can shift context lines by one line
  and cause the patch to fail.
- Have functions or types that the patch calls been renamed or refactored in the
  target base? (Patch may apply but be semantically wrong.)
- If an init.cpp hunk removes `-limitXxx` args: do those args still exist in the
  target base, or were they already removed upstream? (No-op patches should be
  documented as DEFERRED rather than silently dropped.)
- After porting, run `git apply --whitespace=nowarn --check` in a clean workspace
  at the exact pinned commit. A clean check is required before the patch is DONE.

### Minimality (always active)

- Does the patch do exactly one thing?
- Are there whitespace changes, reformats, or unrelated fixes bundled in?
- Could it be split into a smaller patch that is independently reviewable?
- Are there any commented-out code blocks, debug prints, or temporary stubs
  that should be removed before this patch lands?

---

## Scoring

For each issue found, assign:

- **severity** (1–10): Impact if not addressed.
  - 1–3 = minor (style, optional improvement)
  - 4–6 = moderate (likely bug, unclear behavior)
  - 7–9 = high (consensus regression, security gap)
  - 10 = critical (causes fork, crashes, or fund loss on mainnet)

- **confidence** (1–10): Certainty that the issue exists.
  - 1–3 = speculative
  - 4–6 = likely
  - 7–9 = near certain
  - 10 = definite

- **signal** = severity × confidence

- **is_must_address**: severity ≥ 8 AND confidence ≥ 7
- **is_minority_risk**: severity ≥ 7 AND confidence ≤ 4

---

## Applying to a Patch

Run each persona over the diff. For each issue, produce a structured finding:

```
Persona:     <name>
Concern:     <specific description — name the file and line if possible>
Severity:    <1-10>
Confidence:  <1-10>
Signal:      <severity × confidence>
Must-fix:    <yes/no>
```

A patch is ready to mark `DONE` when:
1. No `must-fix` issues remain.
2. `git apply --check` passes against the target base commit.
3. Relevant tests pass.

---

## Convergence

After each review pass:
- If no `must-fix` items remain → patch is ready.
- If `must-fix` items remain after two passes with no progress → escalate to
  design discussion; the patch may need to be reconceived.
