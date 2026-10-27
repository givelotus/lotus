# Snowstorm proposal conformance — IMPCD iteration 5

The spec and test proposal remain at their existing `.scratch/oneshot/` paths. Operator amendments were committed separately as `355ea9be55`; this terminal review adds independent records and updates only review/status metadata. No normative protocol rule or test-requirement row changed during iteration5.

## Maintained input and author decisions

Both F5 and F1 messages were appended verbatim in arrival order. Current bundle SHA256 is **`fb84e15abe521460cd55f65f693835b8047be070075191729fe07df0128e9d96`**,49,197bytes/458lines, pinned in both proposals. Intermediate SHA256 after F5 is `9153f677b2680aaa309704b91828b53c3cbd0f1b20d8f0c2001b4e0b978df823`; the preceding48,180-byte prefix remains unchanged. Exact messages and sparse ledger changes are preserved in iteration-4/author-resolutions.json.

F1 CLOSED: gate_value=c only when the item's previous success side is IN, otherwise0, for both the single prechange W mean and outsider entry. The old capped-OUT-streak witness is blocked; twelve subsequent IN successes make it FINAL-in and eligible. An entrant into a still-nonempty frozen W must be FINAL-in. Empty-W mean0 and other selected rules remain unchanged.

F5 CLOSED: the >=99%-within25-rounds acceptance condition is withdrawn. Retain1000fixed seeds, run fixtures to a horizon long enough to finish, and report freeze-round distributions and nonfinishing trials. Zero false freezes and zero split freezes remain hard assertions. No replacement performance percentage, threshold or seed tuning was introduced.

## Independent IMPCD review

Installed IMPCD v3.0.0 with the operator's eleven technical perspectives and counterexample-first rules. Independent gpt-6-astra and gpt-6.1-sol contexts reviewed the same amended ledger/spec/tests; neither saw the other's revision before submission. Both submitted empty substantive operations and no new concrete finding or unresolved high-severity issue. Their reports include adversarial fixed-population withholding/delay, equivocation, fake Pending and valid-assertion analysis; Sybil resistance stays deferred.

Root reproduced the F1 trace and checked4,930 distinct item states through24updates with13,338 transitions. Both revisers independently checked the local gate implication; their additional bounded checks are documented in their reports. These are item-state checks, not network agreement proofs or SnowstormNode execution.

Substantive disagreement0, no disputes, no new locks. All document-review criteria are answered. **STOP: fixed point / no-new-major condition at iteration5.** The explicit continuation request superseded the earlier capped stop; the resumed5–8cap is not reached. Spec metadata growth0.242361% is below20%; no oscillation or cutback. Historical reports and initial/final ledgers remain preserved.

## Verification and limits

PASS:22 ledger/document/integrity checks, unchanged104historical inventory rows and all active test rows during the terminal step, verbatim ordered input appends/prefix, gate and F5 requirement checks, regenerated normative patch applicability and whitespace. Final renderings match ledger-final.json. Frozen acceptance-manifest SHA256 remains `4aa896175e94e472f645c2d7ca25552a3efb079a789dd8aaca203b0e318906db`; canonical parent and source files remain unchanged.

No implementation acceptance, sanitizer, simulator, sizing-table generation, frozen-artifact migration, human expert review, source freeze, production/node-data change, publication or deployment. Provisional K/f selection, executable header/harness/oracle correction, implementation conformance, empirical hard-safety outcomes and real-network validation remain future evidence obligations. Document-review convergence does not validate those outcomes.

SPEC SHA256 **`b22450e5b399510a203592c97d83a0e973e62658f8d2984b6d592900d32a1956`**,78,172bytes. TESTS SHA256 **`55e7000ee6b2ce0487fbf97329c9e6b9ce36900a4e9415d33e219f0f01440f18`**,54,221bytes. No unresolved contract finding remains from this review. See iteration-5/findings.md,minority-report.md,accepted-changes.md and both independent revisions.
