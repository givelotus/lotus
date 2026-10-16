# Native default-policy quorum acceptance

`daemon/tests/check-v2-native-quorum.py` runs real isolated node processes with
caller-pinned daemon source and binary SHA256. It accepts an existing bootstrap
corpus only when its native evidence records all 2024 blocks accepted and hashes
each submitted block against the accepted ledger. It imports those blocks into
a fresh **Avalanche-enabled observer** home, comparing tip, height, UTXO root,
state root and monetary bytes after every connection. The earlier disabled
bootstrap home is never reopened or copied.

The seed phase stops cleanly before any copies. Its namespace marker binds the
chain, genesis and validation profile, without binding the filesystem location.
The quorum phase can reuse only a cleanly stopped seed with matching manifest
and binary evidence. Nine fresh homes receive individual proofs created by the
native existing-only `-lotusv2provision` command from authoritative native coins.
The fixtures use the publicly known scalars 1 through 9, including their master
and session credentials. Private request and credential files remain mode 0600
outside the repository; the harness never records their contents.

Each later node connects to every earlier node, forming one connection for each
pair. All nodes therefore have exactly eight neighbors, without duplicate
connections. Proof dust (10,000,000,000), stake maturity (2016 confirmations),
quorum (1,000,000,000,000), confidence (128), cooldowns and poll rules retain the
native defaults. The configured minimum download height is 2024; proof/quorum
rules are never replaced by test values.

The staged gates are actual authenticated peer counts and established quorum,
actual tip finality from polling, a newly mined and propagated finalized block,
a separately mined two-block competing fork, rejection of a higher-work switch,
retained proof stores, clean shutdown of all nine owned processes, restart with
those same credentials and homes, renewed authentication/quorum, retained fork
headers and actual finality. Failures retain the last real statuses, raw JSONL,
body hashes, launched commands and owned child exit codes. The global deadline
bounds every phase; cleanup is limited to children launched by the harness.

The immutable initial daemon is source
`d4119718505d0bfbd358c97ac9bfb81aeb48b2da`, SHA256
`97190feb57f60b4c567a9248c1e0bb4018d8d62dfbfadd41ffd5a9d20b4184e8`.
Its `blockstatus` API exposes retained headers and active-tip exclusion, but
cannot expose the requested block's parked/finalized observation. Thus that pin
cannot establish the internal parked reason from public API evidence. A new
observational node API is being prepared separately; its source and binary must
be pinned before making that stronger claim.

This document describes the harness and its gates. Recorded execution evidence
is required before claiming any gate passed. Seed preparation alone is never a
quorum, polling, fork or recovery acceptance result.

## Actual bounded import and recovery blocker

The first enabled observer run hit its 1800-second deadline with stable height
1737 and a pending journal for the next submitted block. The observer still had
zero proofs, zero authenticated peers, no quorum and no finalized tip. Its
requested graceful stop exited **1**, reporting `Avalanche peer save:
runtime-not-authoritative`. This is a failed import run, rather than a clean
completed seed.

A fresh copy of that stopped enabled home was opened with source
`09e36f683003db0cc487fd59ed54622bb1f02195`, binary SHA256
`07a295e559de393f304ce1ed311ba2fdc415908b5a88f4eb27ce95f568b55600`.
That process also exited **1**, before readiness, reporting `Avalanche startup:
runtime-not-authoritative`. The native runtime had not drained the pending
journal before the driver required an authoritative snapshot. Both owned
processes are stopped; the original stopped home and all JSONL traces remain
preserved. The queued quorum launcher was stopped before any quorum home or
proof credentials were created.

[Failure evidence](evidence/v2-native-quorum-recovery-blocker-20261015.json)
records both exact binaries, commands, exit statuses, the last pending snapshot
and hashes/paths for the retained raw traces. Quorum, polling, parking and fork
restart gates have **not run** at this point.

The harness distinguishes `--resume-seed` after a clean bounded timeout from
`--recover-seed --resume-seed` for this exact failed shutdown. Explicit recovery
keeps the old failure evidence, copies only the stopped enabled home, requires
the known shutdown error and exit code, and checks the recovered authoritative
native state against the accepted ledger before importing the remaining suffix.
A native lifecycle correction must be independently reviewed and pinned before
using the latter path. It never clears or edits the journal itself.
