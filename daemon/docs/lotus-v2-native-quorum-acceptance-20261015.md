# Native default-policy quorum acceptance

Current result: diagnostic source `bf4ddad652` passed the actual nine-node
authenticated quorum gate, and four of nine nodes (nodes 6, 7, 8 and 9) finalized
the seed tip, while the unchanged 300-second all-nine finality gate failed with
remaining tip confidences 105–127 against the 128 threshold. Fork/parking and
nine-node restart gates remain unexecuted. All twelve owned processes exited
cleanly and their PIDs are absent. The heavy execution window was released; no
retry followed. See the
[latest evidence](evidence/v2-native-quorum-bf4d-finality-deadline-20261015.json).

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

## Repaired recovery and actual nine-node readiness failure

With reviewed lifecycle source `c0ddb9cf307a97a43309b72cffef383c29e559e8`
(binary SHA256 `5c05a1acf36a91c690505ca08bd291d9fd2e985fd483f9db08386c712c1f8bfa`),
a new copy recovered the interrupted journal to height 1738 and matched the
accepted ledger's complete native state. Its remaining suffix reached 2024 and
stopped with exit 0. All nine existing-only native proof provisions passed with
mode 0600 credentials.

The funded pending-stop check passed separately: an actual admitted proof was
present during a pending journal, graceful stop exited 0, and its 487-byte public
cache was retained. Reopening the same home **as an observer without local proof
credentials** recovered the mined block at 2025 and loaded one proof with zero
authenticated peers and no quorum. That observer also stopped with exit 0.

The nine-node mesh then reached eight authenticated and eligible peers and nine
proofs per node. The readiness gate nevertheless failed at its unchanged
180-second deadline. During unchanged height-2024 snapshots with no download
jobs or pending recovery, each node repeatedly reentered initial download mode:
14–36 transitions occurred per node. Only one node reported an established
quorum in the retained samples. All twelve owned native processes exited 0.

[Ordered readiness evidence](evidence/v2-native-quorum-ibd-oscillation-20261015.json)
retains each native response and raw-trace hashes. It has no invented timestamps.
The source mechanism is `Node::Headers`, which starts header refreshes every
1000 ms and adds `pending_headers`, combined with `Node::InitialDownload`, which
rechecks that set every time. `Quorum::SentProofInventory` ignores inventories
sent while that initial-download flag is true. The pinned ABC implementation
uses a one-way catch-up latch. Its reviewed restoration is a separate source
change; no proof, voting, confidence, neighbor or cooldown default is weakened.

This run did not reach finality or fork checks. Future fork acceptance requires
requested-block observations before **each** rival submission and after it, with
the selected block still active and unfinalized. All nine nodes must then report
the known, valid, data-bearing rival parked while `conflicting_finalized=false`
and selected finality remains false. Any crossed finality boundary fails with
its original snapshots. The production park-write path is exclusively signed
poll response handling through `PollEngine::Receive`, `AvalancheDriver::Apply`
and `DevelopmentRuntime::ApplyAvalancheUpdates`.

## Latch-fixed peer-capacity failure

Source `e775de1363c8ef9411f4c38b6c7504dacf4402be`, binary SHA256
`5d2ba8f0a2b5bb84de31a2e76860f8b6ef947ddf611b72bb9f03fb10635c59b0`,
reused a new copy of the clean 2024 seed without reimport. All nine native proof
provisions and the funded pending-stop/observer-cache recovery check passed.
Initial download mode remained false, and each node reported an established
quorum in the retained snapshots. The simultaneous readiness gate did not pass.

Node seven then exited 1 with `Avalanche application:
avalanche-negotiated-capacity`. All twelve children are stopped: eleven exited 0
and node seven exited 1. Finality and fork gates did not run.

[Compact failure evidence](evidence/v2-native-quorum-peer-capacity-failure-20261015.json)
retains exact pins, cleanup, last states and raw-trace paths/hashes. The last two
node-seven states show authentication recovering from seven to eight peers and
nine total activations. Every configured receive limit was 2 MiB.

`AvalanchePeer::Queue` first bounds a payload to 256000 bytes, then emits the
negotiated-capacity error if `ActiveLimit` is absent or the payload exceeds that
limit. The dispatcher can return an absent limit for a removed peer or zero for
a non-active transport. The observed bounds therefore implicate a stale or dead
peer; the actual incoming application command, payload size and missing-versus-
zero limit were not logged and remain unknown. This peer-local condition must
not be presented as successful quorum acceptance. The failed homes remain
preserved; no retry is authorized until a reviewed immutable repair is supplied.

## Peer-fixed actual quorum and bounded finality failure

Source `63c51499441ded6d0fe34d87ff43d53a14b1398f`, binary SHA256
`7d86468e24d457eaf2bbac541cc33ddd422e8a481fee96c8e5b6c07e70de7d0e`,
ran the same reviewed harness in fresh copies with unchanged thresholds, budgets
and deadlines. Nine native proof provisions and funded pending-stop/observer
readmission passed. **The authenticated default quorum gate passed on all nine
nodes**, with eight authenticated and eligible peers each.

The unchanged 300-second all-nine seed finality gate then failed. At its last
snapshot, all nine nodes again had eight active/authenticated/eligible peers and
reported established, ready quorums. Only node six reported the tip finalized;
the other eight did not. Activation counts ranged from 13 to 23, establishing
reconnect activity without identifying its cause. No driver error was reported
in that last snapshot. All twelve owned native processes stopped with exit 0.

[Compact finality evidence](evidence/v2-native-quorum-finality-deadline-20261015.json)
retains the passed quorum checkpoint, exact final states, cleanup and raw-trace
hashes/paths. No raw incoming application trace or confidence counter was added.
This demonstrates actual authentication and quorum formation; it does not pass
the all-nine finality requirement or establish that finalization is universally
impossible. Fork, parking and nine-node restart gates were not reached. The
failure remains preserved, with no longer deadline or blind retry.


## Late-response policy repair: bounded actual run

The fresh run used native source `cd8d5140ec7fce7da9a4e2a5a8b5d803ed4dc3f5`,
immutable binary SHA256
`5767c34242f939f5d6fb0fa7f740f87b0c829d179717a58eb4df5cb84c88f7d9`,
and the unchanged reviewed harness. It copied the clean enabled 2024-block seed
into a new artifact directory; all previous homes and failures remain preserved.
Actual native provisioning, funded pending-stop recovery and all-nine authenticated
default quorum passed. The unchanged 300-second seed-finality deadline expired,
with only node eight finalized in the last gate snapshot. No fork, parking or
nine-node restart gate was reached.

The [recorded failure](evidence/v2-native-quorum-cd8d-finality-deadline-20261015.json)
contains the exact last gate statuses, the passed authenticated-quorum checkpoint,
each node's complete observed activation trajectory with stdout line and response
ID, final stdout statuses, input and raw-trace hashes, and all twelve clean exit
codes. The trajectories record reconnect activity; they do not identify its cause
or distinguish response handling from slow policy reads. All owned PIDs were
confirmed absent after terminal session exit 1, and the heavy execution window
was released. Further diagnosis and a reviewed repair pin are required before
another run; defaults and deadlines were not changed.

## Passive-diagnostic source `bf4ddad652`: bounded actual run

The diagnostic run in `/private/tmp/lotus-v2-native-quorum-diagnostics-20261015-a`
used native source `bf4ddad652ac50396b164e6ae018a51da31ac890`, immutable binary
SHA256 `82a591431485309f893814b522e61a46668c6876b147ccd1602891fb5485edbc`, and
the unchanged reviewed harness (`0ae10ff124b4238910686799c3000e2c99f60894d69bc3f79bac2edc0ff1562d`).
It copied the clean enabled 2024-block seed into a fresh directory while
preserving all prior runs. Actual native provisioning, funded pending-stop
recovery, observer readmission and all-nine authenticated default quorum passed
at stdout line 46 across all nine nodes.

The unchanged 300-second seed-finality deadline then expired. Four of the nine
nodes (nodes 6, 7, 8 and 9) finalized the seed tip (`tip_finalized=true`,
`tip_confidence` 132–134), while nodes 1 through 5 reached `tip_confidence` 110,
105, 127, 121 and 123 (below the 128 finalization threshold). Every observed
application rejection across all nine nodes fell into `application_rejections.other`
(final counts 4, 1, 9, 3, 8, 7, 12, 5, 6), paired 1:1 with
`peer_disconnect_causes.application_rejected`, occurring on the 60-second
`getavaproofs` discovery cycle and interrupting peer eligibility and confidence
accumulation. Zero cooldown rejections, zero response rejections, zero invalid
headers/bodies, and zero transport read/write errors occurred. All twelve owned
child processes exited 0 and their PIDs were confirmed absent.

The [diagnostic failure evidence](evidence/v2-native-quorum-bf4d-finality-deadline-20261015.json)
retains the passed quorum checkpoint, final gate and stdout statuses, per-line
confidence/rejection/activation trajectories, cleanup records and raw-trace
SHA256 digests. Fork, parking and nine-node restart gates were not reached. A
reviewed repair to proof-discovery shortid matching, already-known proof
registration and per-connection outbound queue draining is required before the
next acceptance run.

