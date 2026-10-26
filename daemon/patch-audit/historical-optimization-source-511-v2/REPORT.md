# Historical optimization source audit

Source `6e5c518d4fa7eaede8ff8b20be32ec92577873fb`, tree `7e0440624555dbf1a0ef3df4598a2a80193b24db`.

264 patch entries; 264 unique payloads.

| Mechanical result | Unique payloads |
|---|---:|
| reverse_apply_check_pass | 26 |
| needs_review | 238 |

| Hunk result | Count |
|---|---:|
| exact_postimage_region | 3031 |
| changed_blocks_present_context_diverged | 874 |
| unresolved_review | 1554 |
| preimage_region_survives_review | 308 |
| path_missing_review | 36 |
| whitespace_insensitive_blocks_review | 33 |
| deleted_path_absent | 25 |

## Interpretation

Reverse-apply success means the original diff can be reversed against this committed source. It does not establish reachability, lock scope, configuration, correctness or speed.

Unmatched/preimage results need review: subsequent refactoring, fixes, native consensus adaptations, moves and superseding implementations can all change text. They are not automatic evidence of loss. Whitespace matches are review hints; their line numbers refer to the normalized nonempty-line stream.

Binary, mode-only and renamed files can require manual review. Owner candidates are file-overlap hints only. No builds, tests or benchmarks run. Historical patches are independent comparisons, not replayed in sequence.

See patches.csv, hunks.csv and audit.json for every patch, hunk, change block and diagnostic.
