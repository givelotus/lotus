# Snowstorm proposal conformance — author resolutions after iteration 4

Updated the existing spec and tests in place from the accepted ledger plus the exact operations in `.scratch/impcd/iteration-4/author-resolutions.json`. Historical iteration4 review records are preserved; current F1/F5 author decisions supersede their open dispositions.

## Maintained input

Appended the complete F5 and F1 messages verbatim, in order, as final sections. Prior48,180-byte prefix unchanged. SHA256 after F5: `9153f677b2680aaa309704b91828b53c3cbd0f1b20d8f0c2001b4e0b978df823`. Current whole-bundle SHA256: **`fb84e15abe521460cd55f65f693835b8047be070075191729fe07df0128e9d96`**, pinned in both proposals.

## Applied decisions

F5 CLOSED: remove the obsolete >=99%-within25-rounds performance acceptance condition. Preserve1000fixed seeds and workload counts. Run fixtures to a horizon long enough to finish and report freeze-round distributions and nonfinishing trials. Hard assertions remain zero false freezes and zero split freezes.

F1 CLOSED: gate_value equals c only for previous success IN, otherwise zero. Use that value for both the single prechange W mean and simultaneous entries. The previous nonpreferred-capped-streak witness is blocked from frozen W; a later entrant into a nonempty frozen W must be FINAL-in. Whole-state Pending transfer, immutable FINAL, strict full-K quorum, arrival votes and rescue abstention remain unchanged.

No unresolved author decision remains from iteration4. Provisional K, simulator measurements, implementation conformance, table generation, freeze migration and network validation remain future evidence obligations. The latest instruction explicitly resumes independent IMPCD review beyond the prior cap; no convergence claim is made by this amendment application.

## Verification and boundaries

Checked verbatim append/prefix preservation, ledger-operation rendering, the revised gate witness, all104 historical inventory rows and the retained1000seed fixture. Regenerated the review-only normative patch and checked applicability and Markdown whitespace. No production/header/harness/oracle/manifest/canonical-parent change, simulator run, source freeze or deployment.

SPEC SHA256 `b39bf5d2e0e9403492d3d4388ccd1044e05bc9b4ee65b4b96f68d6ab7d07612e`; TESTS SHA256 `fd1afa77a7403fade0ddf56d5fa00100c93b43bb4c56f1bccc57fbbdc5ebb1c7`. Source acceptance-manifest SHA256 remains `4aa896175e94e472f645c2d7ca25552a3efb079a789dd8aaca203b0e318906db`.
