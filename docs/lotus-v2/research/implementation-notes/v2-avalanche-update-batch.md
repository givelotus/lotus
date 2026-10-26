# Avalanche update batch read-budget repair

At native source `7808120ec6`, 1,024 overlapping Accepted updates on 2,024 mechanically checked indexed headers exceeded the unchanged default 100,000-read budget. The ordinary regression failed; a separate historical-mode check verified atomic refusal with unchanged root, tip, revision and context generation. These indexed headers do not establish contextually executed block validity.

Reviewed repair `82f9dc2b59`, integrated as `09e36f683003db0cc487fd59ed54622bb1f02195`, caches successful checked headers within one serialized update batch. Ordered ancestor walks remain intact. Cache misses retain database read charges and failure behavior. Combined header/staged logical payload is bounded by the existing pending-byte limit; allocator overhead is not included in that logical bound. Defaults and consensus rules are unchanged.

The repaired focused regression and existing Avalanche runtime suite pass 2/2. Independent review reran the focused executable and checked original failure evidence. Tests cover ordering on real connected fixtures, memory/read-capacity refusal, missing headers and corruption-induced authority revocation. They do not establish network quorum/finality.

The integrated Chronik-enabled daemon built successfully; binary SHA256 `07a295e559de393f304ce1ed311ba2fdc415908b5a88f4eb27ce95f568b55600`. [Retained evidence](../../../../daemon/docs/evidence/v2-avalanche-update-batch-20261015) includes failure/pass logs and binary provenance. Full build log is `/private/tmp/lotus-v2-avalanche-batch-integrated-build-20261015.log`. macOS dependency deployment-target warnings remain.

Repeated CPU ancestor walks, deep unique ancestry and the separate bounded disk candidate-policy scan remain limitations. Actual funded quorum and restart recovery require the separate live acceptance gate. This repair follows maintained patch 300 and requires full mailbox replay before series append.
