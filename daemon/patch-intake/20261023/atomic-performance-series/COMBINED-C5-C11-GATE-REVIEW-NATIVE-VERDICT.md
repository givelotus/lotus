# Combined C5/C11 correctness gate review

Read-only review before root launch; reviewer owns native item11 and borrowed-SMT candidate lanes, not the primary combined source checkout. Root launches and coordinates the exclusive host slot. No source changes or gate processes were started by this review.

Reviewed `gate-combined-c5-c11.py`, expected combined commit `26bed6b96ba73a7a4a0f681edb19a885da491c80`, tree `a9c69e9083325bea48d911dd0b579ee494a1bf7e`, `COMBINED-C5-C11-RESULT.json` and `C11-PAIRED-AFTER-BUILD.json`.

Verdict: **no correctness launch blocker**. The script acquires source and host locks without waiting on an unverified old process, requires exact head/tree and clean tracked source, refuses an existing output attempt, preserves the prior diagnostic daemon/CLI/unit binary and cache before the rebuild, and uses native Release/Chronik-OFF flags with the intended source/config paths. Full native units and native MiniWallet, staged P2P and atomic RPC functionals use the built native binaries and matching SRCDIR/PYTHONPATH. The fixture scripts match the separately reviewed prerequisite; no assertion is weakened. End-of-gate clean/head checks preserve tracked-tree identity. Warning comparison and performance adoption are explicitly separate from the build/unit/functional PASS claim.

Confirmed prerequisites: archive parent exists; sccache path is present; the old diagnostic binary is identified as a failing prefix artifact, not mislabeled as a passing baseline. Cache-stop status records the actual subprocess return code rather than an assumed boolean.

Preservation finding sent to root before launch: the copied unit binary retains a BUILD/src rpath. Preserve/hash `libbitcoinconsensus*.dylib` alongside it and record a DYLD_LIBRARY_PATH replay hint, otherwise a later build can replace its runtime dependency. **Root added this before launch**, and the revised preservation loop was inspected. This is evidence preservation, not a new source or validity change.

An optional direct source-file SHA comparison against the expected map would supplement existing exact-head/tree/clean checks; its absence is not a launch blocker for the exclusively owned checkout. No build result, warning result or throughput improvement is claimed by this review. Root subsequently reported the combined gate running in session23277; this review does not independently mark it passed.
