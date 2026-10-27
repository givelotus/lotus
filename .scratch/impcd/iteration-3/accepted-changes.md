# Iteration 3 — final reply votes and strict sample quorum

Applied the operator's two new messages to the existing proposal and test plan in place. Appended each complete message verbatim, in arrival order, under the final titled sections `PER-ITEM REPLY VOTES — ARRIVAL EVIDENCE` and `FINAL PARTIAL-PEEL RULE AND STRICT SAMPLE QUORUM` in the maintained input bundle.

Intermediate input SHA256 after the reply-vote message: `8cd0115c5f23fc06ef2ca101bdf74cce2f09cfe34f0d746e71db6c5806fd4e52`.

Final input SHA256: **`e6ab26b85fe03c3c0a327b21bb5d2da7fc9c38f9a2aee178a0d584f42b1abd1d`**; 48,180 bytes, 444 lines. The preceding 46,566-byte tracked input is unchanged. Future spec-changing instructions continue to be appended verbatim before application.

## Applied rules

- A vote describes the peer's preference: held but excluded is NO.
- MATCH: YES in captured W; NO for other captured items.
- Arrival decode: present and nonexcluded is YES; absent or excluded is NO. If residual remains, all other captured items abstain. With no residual, remaining eligible captured reference items are shared and YES unless excluded.
- DIFF is complete at arrival: classify present/absent from its full raw-set reconstruction, then apply exclusions. A captured Pending item absent from that complete raw assertion is NO, not an inferred shared item.
- Items first decoded later by rescue abstain that round, as the preceding reply-vote message requires. Same-call cascade attempts are rescue too. A complete rescue does not upgrade arrival abstentions. Existing valid arrival observations remain subject to captured-lifetime and validity filters.
- The final partial rule contributes only explicit arrival-decoded-present, decoded-absent and exclusion observations. Removed the zero-cell witness, current-Pending guard, “proven shared” definition, per-reply observation masks and their resource bound. Existing bounded round-evidence records remain; no replacement cell-index buffer is added.
- alpha=floor(((1+beta_adv)/2)*K)+1. The reference table is now (D,K,alpha,beta_c): (16,4,3,12), (32,8,5,12), (64,16,10,12), (128,32,20,12), (500,125,76,12).

Q13 is closed: 2*alpha>K for K>0, so disjoint yes/no observations cannot both meet quorum. All Q1–Q13 are now closed. No new contract question was identified; provisional K and the existing implementation/simulation evidence obligations remain explicitly pending work rather than undefined rules.

## Regeneration and checks

Updated §§6.2,6.5,8,10 and the current test table, including rescue audit expectations and mutation requirements. Added requirements for complete-arrival shared items, preference/exclusion priority, explicit partial observations, rescue-only abstention, and the corrected zero-adversary boundary. Preserved all 104 historical acceptance inventory rows and existing workloads.

PASS: 25 independent classification/quorum/document checks. The source freeze manifest and production files are unchanged; no compiled node acceptance, simulator, sizing-table generation or freeze was performed. Regenerated the review-only normative patch and current conformance hashes.

Stop after this third review round. There is no new blocker/major counterexample from this pass and the previously open Q13 is resolved. This is completion of the technical review's no-new-major stopping condition, not implementation or network-safety validation.
