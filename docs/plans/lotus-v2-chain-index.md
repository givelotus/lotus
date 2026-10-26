# Development chain index implementation review

Status: design review after native `7432a0aa1`, monorepo `5abf0198`.
This is a storage/runtime design, not a consensus change or network-profile
adoption. Exact APIs and migration behavior must be reviewed before integration.

## Existing boundary

`DiskStateTransaction::Commit` atomically writes live coins/nodes, current head
`S`, schema/profile `V`, and immutable undo `U || BlockID`. Disconnect restores
coins/nodes and `S` in one batch, retaining undo records. Retained-body reads
authenticate bytes but do not establish active-chain membership. There is no
persistent height index or accumulated-work fork selector. A caller cannot use
monetary `prev_work` as accumulated chainwork: it represents one block's work.

## Required next storage packet

Keep the chain index in the same LevelDB database and synchronous batch as `S`.
A second database or a write after chainstate publication would create a crash
window where the active index and spendable state disagree.

Proposed record families:

| Key | Value and purpose |
| --- | --- |
| `H || BlockID` | Canonical 134-byte header, accumulated work, explicit validation stage, and eligibility summary |
| `A || height_u64be` | Active BlockID at an exact height |
| `I` | Index schema/readiness and active tip/height/work, checked against `S` |

Header validity, body availability and successful complete-block connection must
remain distinct states. A valid header does not validate its state root. A body
present on disk is not necessarily validated. Retain disconnected header/body
records without asserting that they are active. Invalidity propagation and
best-candidate filtering need explicit rules; storage/resource errors never mark
a header consensus-invalid.

Compute work mathematically from canonical positive target. Check accumulation
before encoding; do not wrap at 256 bits. A 40-byte unsigned representation can
hold cumulative work over the u64 height domain: positive target bounds each
block's work by 2^255, with at most 2^64 blocks. Equal accumulated work retains
the current valid tip. Clock eligibility remains external and reversible; an
ancestor-time summary, if retained, must not become consensus state.

## Bounded query and transition requirements

- Build locators from direct `A` lookups at exponentially spaced heights.
- Match received locators using indexed header height and exact active-ID lookup,
  then return only a caller-bounded number of active headers. No linear walk from
  genesis or full UTXO scan per request.
- Plan forks using parent records with explicit disconnect/connect/read budgets.
  Exceeding a local budget returns capacity refusal, not invalidity.
- Connect/disconnect must update `H/A/I` with `S` atomically. Keep disconnected
  historical records; remove the old active-height mapping on undo.
- A multi-block reorg is not made atomic by per-block batches. Define a durable
  resumable plan or equivalent recovery procedure before claiming crash-safe
  fork switching. Missing bodies, invalid replacement blocks and storage errors
  must have separately tested recovery outcomes.
- No network service bit may be inferred solely from index presence. Serving
  promises also require verified, retained complete body availability.

## Compatibility and tests

Do not reset existing native/reference/replay/compiler worktrees or data. Prefer
an explicit development index schema with new isolated homes and fail-closed
old-store detection until a bounded, resumable migration is designed. Generic
raw-store fixtures may keep the existing non-indexed mode; the development
initializer must explicitly select the mode it requires.

Required tests include exact height/locator results across forks and reopen,
work overflow and equal-work behavior, malformed header/index records,
profile/genesis mismatch, index/head divergence, bounded fork-planning refusal,
and injected failures before/after each atomic write. Separate header-only
admission from full signed-body validation. The existing signed compiler pilot
must still accept/reject at its intended checks after integration.

This document records requirements and source inspection only. Persistent index,
fork selection, reorg recovery and peer synchronization are not yet implemented.
