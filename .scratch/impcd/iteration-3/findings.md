# Snowstorm technical IMPCD — iteration 3

Operator: Shammah. Reviewer: Codex exercising the required eleven technical perspectives on the changed reply-vote/quorum rules. Correctness follows concrete scenarios, not votes; severity × confidence is the only weight. All applied choices were supplied by the operator, so no preference ballot is needed.

## Inputs

Previous committed review: `0c862e8801`. The original tracked bundle prefix remains unchanged; two operator messages were appended verbatim in order. Current bundle SHA256: `e6ab26b85fe03c3c0a327b21bb5d2da7fc9c38f9a2aee178a0d584f42b1abd1d` (48,180 bytes / 444 lines). `accepted-changes.md` records the intermediate digest and exact precedence. The final partial rule replaces the older guarded/inferred-sharing policy; the preceding explicit instruction excluding rescue-only discoveries remains applicable.

## Technical-perspective feedback

| Perspective | Fresh feedback | Severity | Confidence | Weight | Disposition |
|---|---|---|---|---|---|
| Coding theorist | Explicit decoded outcomes replace partial cell/schedule inference; keep the existing body/fingerprint limitations. | 6 | 10 | 60 | Final rule applied |
| IBLT researcher | Complete arrival, incomplete arrival and rescue have different observation rights; preserve dissemination and residual invariants. | 6 | 10 | 60 | Paths separated |
| Consensus researcher | The strict floor-plus-one threshold resolves simultaneous quorums, including zero adversary fraction. | 8 | 10 | 80 | Q13 closed |
| P2P developer | Votes describe preference rather than possession; exclusions override present-item assertions. | 7 | 10 | 70 | Exclusion priority explicit |
| Red-team attacker | Remove zero-cell inference entirely as instructed; rescue cannot create a new vote from later shared Ref. | 7 | 9 | 63 | No superseded mechanism retained |
| Formal-methods reviewer | For K>0, 2*alpha>K and yes+no<=K prove mutual exclusion of the two successes. | 8 | 10 | 80 | No unresolved branch |
| C++ implementer | Delete per-reply observation masks/bounds; use existing captured-lifetime round evidence without a new cell-index buffer. | 6 | 9 | 54 | Storage deletion explicit |
| Test engineer | Replace guard/mask/rescue-upgrade tests with explicit partial preference, complete-arrival and rescue-abstention cases. | 7 | 10 | 70 | Plan regenerated |
| Network engineer | Rescue still improves dissemination/body availability even when it supplies no new item votes that round. | 5 | 9 | 45 | Measurement scope retained |
| Minimalist | Delete the retired witness and its machinery rather than retain it as an alternative policy. | 5 | 10 | 50 | One active rule |
| Skeptical paper reviewer | Checked arithmetic/classification is distinct from compiled contract conformance or measured network agreement. | 6 | 9 | 54 | Evidence limits retained |

## Resolved findings, ordered by severity × confidence

### F3-01 — Q13's dual-success branch is removed

**Severity 8; confidence 10; weight 80; resolved.**

Current §8: “alpha=floor(((1+beta_adv)/2)*K)+1”.

**Prior concrete scenario:** D=5,K=2,beta_adv=0,yes=no=1 satisfied both old ceil-half predicates. The new alpha is 2, so neither succeeds. In general alpha>K/2 and one observation per peer gives yes+no<=K, excluding simultaneous success. The D=500,K=125 reference alpha changes from 75 to 76.

**Smallest authorized fix:** replace the threshold expression and table; no tie priority or Config restriction. Tests cover the five reference rows and strict uniqueness over D=1..1024 at zero, default and near-upper-bound adversary fractions.

### F3-02 — Possession is not the peer's item preference

**Severity 7; confidence 10; weight 70; resolved by final vote text.**

Operator text: “Votes are the peer’s preference; an item it holds but excludes is a no.”

**Scenario:** captured x is explicitly present in an incomplete arrival reply, but x is in peer exclusions. A presence-only test would record YES; the correct observation is NO. With a residual, a different unclaimed captured item must abstain rather than infer sharing from the reference or a cell.

**Smallest fix:** exclusion/absence priority, then explicit arrival presence, then complete-arrival shared inference or abstention as appropriate. Delete the superseded witness and metadata rather than add a new proof mechanism.

### F3-03 — Rescue success must not upgrade this round's arrival abstention

**Severity 6; confidence 10; weight 60; resolved.**

Operator text: “Decoded later in the round by rescue: abstain that round.”

**Scenario:** arrival leaves residual and captured x is neither explicitly decoded nor excluded, so x abstains. Another peer changes Ref; rescue later decodes x as present or completes the whole reply. The earlier policy upgraded x to YES. The current instruction keeps x abstaining that round, including same-call dirty cascades. A valid initial explicit observation for another item is not duplicated or upgraded.

**Smallest fix:** retain arrival observations under existing captured-lifetime filters, make rescue dissemination-only for new observations, and adjust independent audit/test expectations. No extra evidence peel or retained cell-index snapshot is needed.

## Integrity and verification

The reviewed source and test proposal were edited in their established paths. Historical input sections and earlier review records were not rewritten. Both latest messages are preserved verbatim in the maintained log. The final explicit partial rule and strict quorum are the sole active definitions; no obsolete guard/mask policy remains as an alternative.

PASS: 25 arithmetic/classification/document checks: reference alpha table, strict uniqueness including beta_adv=0, partial explicit yes/no/abstain, exclusion priority, complete-arrival shared items, MATCH preferences, rescue-abstention policy/text, preserved input prefix, matching draft input hashes and all 104 historical inventory rows. These checks do not execute the production node or new C++ acceptance tests. Final hash/patch/manifest checks are in the current conformance record.

## Termination

**Stop after iteration 3 of at most 4: no new blocker/major finding with a concrete failure scenario; all Q1–Q13 are closed.** The operator's technical stopping condition is met. Growth remains below 20%. This does not claim implementation validation, a network safety theorem, simulator success, final K calibration or a freeze. No fourth iteration is run on this unchanged version.
