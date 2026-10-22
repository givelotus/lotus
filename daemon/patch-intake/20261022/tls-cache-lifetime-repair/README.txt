Matched527/528 repair and release, 2026-10-22

Final527 source0f42fcfde6d36fd4326b8de18df17ce740b22446
Treea2c855dc0f6d16fa260549c40958ba37aecb03b9
Final528 source922eb4a7f9d8ec8af7a5e64d521454c572ece937
Tree1c267e0b5b115f216d5d88731074f4ac794f7a4f
Current endpoint source/binary/cache/config paths and SHA256: ENDPOINTS.json.
Matched Release, walletOFF, ChronikOFF, USE_JEMALLOC=OFF.
527 full unfiltered1,187 cases PASS;528 full unfiltered1,200 cases PASS.
Both source checkouts clean; allowned compiler/test runtimes drained before release.
Original385/c4 sources and immutable endpoint binaries remain preserved separately.

Cause1, global26/ecash025 (first signature-cache TLS owner):
TLS slots identified their cache only by its address. Test setup resets the RNG
per fixture, so salts and signature keys can repeat; allocation-address reuse
then revived a TLS hit from a destroyed cache. A deterministic placement-new
regression using an opaque fixed entry key proved two stale hits (main thread
and persistent worker), independent of nonce randomness. Production fix assigns
a nonwrapping process-unique lifetime ID once per cache constructor; TLS slots
compare the lifetime ID. Signature hashing and existing erase semantics remain.
The original warmup cold-cache assertion is unchanged. Before: two regression
failures. After: complete full gates pass, including that assertion and regression.

Cause2, global349/ecash348 (first admission fixture owner):
The test said it compared an identical transaction but signed two different
funding outpoints. Valid ECDSA DER lengths can differ, so their sizes need not
match. The fixture now removes the first admission through ordinary recursive
mempool removal, asserts its absence, then admits the identical signed bytes via
the ordinary path. Result, reject reason, debug message, size and fee equality
assertions remain; no production admission behavior changed. Additional failure
messages retain actual size diagnostics. No check was deleted, weakened or skipped.

Both repairs are fixups folded into their earliest owners. The snapshot tree
remains the sole new global528/V2patch154. Only ecash025 and ecash348 mailbox
bytes changed during this repair; patch154 and other mailbox payloads are intact.
All528 canonical mailboxes and every intermediate tree replay to exact source.
Changing the shared owners invalidates runtime evidence from global26 onward;
old385/c4 evidence is historical and is not relabelled as these repaired sources.

Logs and SHA256 inventory are committed in logs/ and log-inventory.json. The
intermediate cache-only full528 run's separate fixture failure is preserved.
The source recovery bundle includes final review, daemon/ecash and daemon/v2 refs
and verifies against its recorded historical prerequisite. No push/deployment.

Rebase optimization restored timestamps only for6,480 files whose complete
SHA256 remained identical, preserving correct Ninja dependencies; changed files
and generated Git build identities were built normally. Final exact binary
versions/identities and full gates were verified after the last source rewrite.

Heavy host is released directly to canonical_records_sync for matched500k
endpoint benchmark execution. No generic/cooperative worker pool was integrated.
