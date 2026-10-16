# Argon audit intake and current-tree triage

Audit supplied by the user covers patches000–300. Triage baseline is native
`63c51499441ded6d0fe34d87ff43d53a14b1398f`, maintained series000–307.
Reported severity and proposed fixes are hypotheses until checked against this
source, specification and actual behavior. Existing passing component tests do
not dispose of new findings. No audit finding is closed by this intake alone.

Source reports are preserved at
`/Users/shammah/.gemini/antigravity/brain/636d0566-bb91-4e80-b1e5-2611e231d925/scratch/`:
`review-000-086.md`, `review-087-172.md`, `review-173-260.md`.
The user also supplied the extended000–300 consolidation blueprint in chat.

| ID | Reported issue | Owner / current investigation |
|---|---|---|
| 1 | 256-level state-key charge | Astra: compare actual BlockCostProfile, P02/P05 and reference; no consensus change yet |
| 2 | Quadratic inner costs yield quartic effective scaling | Astra: terms present; specification intent/calibration and replacement require review |
| 3 | Lexicographic relay known-set eviction | Network owner: present, reproduce adversarial eviction and bound FIFO replacement |
| 4 | Dispatcher drops applications on tip changes | Network owner: ordinary-tip premise appears stale; actual authority/invalid-epoch invalidation still needs safe preservation review |
| 5 | macOS-only temporary paths | Safety owner: development-chain/recovery/runtime fixtures; network owner: dispatcher test |
| 6 | Mixed transaction/proof inventory demux | Network owner: current Node already partitions; verify end-to-end before closing, no redundant demux added |
| 7 | Branch-root width inconsistency | Astra: compare opcode contract/reference before changing VM consensus |
| 8 | Prepared VM copy/move identity hazard | Safety owner: reported shared-Impl description stale; investigate actual pointer lifetimes and callers |
| 9 | Admission work before exhausted budget check | Safety owner: late guard present; callback-count regression before repair |
| 10 | Repeated full block authentication for chunks | Root: pending measurement and cursor/authority design review; existing storage experiment is not an adopted fix |
| 11 | Wallet FD nonblocking flags not restored | Safety owner: actual binary/shared-description regression and RAII restoration |
| 12 | Repeated transaction encoding/identities | Root: pending call-path verification; no speculative optimization |
| 13 | Inventory traversal reset / mandatory relay bit | Root: pending current policy/fairness verification |
| 14 | Invalid monetary fixture aggregate | Safety owner: current field layout verified; named fields and invariant checks proposed |

## Consolidation boundary

Astra owns the consensus/consolidation review document. The proposed58-commit
map is not executable as supplied: some patch numbers are assigned to multiple
unrelated components, and301–307 are absent. Verify the exact hunk dependencies
and every retained caller/test before dropping prototypes or moving code.

Correctness fixes require independent review and regression evidence first.
Consolidation is a separate isolated candidate, preserving the existing series
and source history. Separate tree-preserving reordering/squashing from explicit
source deletion/behavior changes. Preserve patch033 binary literal. Every
candidate intermediate commit must build and pass its registered tests before
promotion; matching only the final tree is insufficient. No fixed58-commit
count overrides dependency correctness or reviewability. Existing mailbox and
series-parent/replay requirements remain in force until a reviewed replacement
is ready.

The independently discovered expired-poll response mismatch is being repaired
in disjoint Avalanche peer/poll/driver files. It is not evidence that Argon's
other findings are resolved, or that the nine-node finality failure is fixed.
