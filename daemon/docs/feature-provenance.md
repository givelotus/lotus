# Feature and patch provenance

Status: source inventory, October 9, 2026. Repository base observed: `671cbd11e6871b03519bb1c3fe0b0cf18f70044a` plus local documentation/import changes. Source existence is not proof of clean application or active-network behavior.

## Machine-readable inventory

[Patch inventory CSV](../patches/inventory.csv) is a snapshot of v1, v2, eCash, BCHN and doged series and `*.patch` files. Fields record series, path, active/commented/unlisted status, series line, existence, byte size, SHA256, original `From` commit where present, presence of a diff header and verification status. `NOT_RUN` means application/build/test evidence has not been collected. A source commit header is provenance, not verification that its object is locally available.

| Series | Files or referenced filenames | Active entries | Active entries without a diff header |
| --- | ---: | ---: | ---: |
| v1 | 247 | 243 | 0 |
| v2 | 42 | 27 | 1 |
| ecash | 5 | 3 | 1 |
| bchn | 5 | 3 | 1 |
| doged | 0 | 0 | 0 |

The active no-diff entries are `03-mempool-cleanup.patch` in v2/eCash/BCHN. Determine whether to retire them as documented no-ops; do not treat successful file discovery as an applicable patch. Six commented v2 filenames are absent: 09b header, 09c outputs, 31 int128, 33 introspection/loops, 34 state/storage and 35 proof RPCs. Other placeholder files may contain prose or partial changes; `contains_diff=True` does not imply completeness.

## Capability ledger

| Capability | Existing local evidence | V1 requirement | V2 disposition / next evidence |
| --- | --- | --- | --- |
| Two-minute timing and ASERT | v1 patches 004, 044 and later chainparams history | Preserve observed activated behavior | Reuse arithmetic only after exact target/time rules selected |
| Extended headers/transaction identities | v1 094 (`fb997e62174368720901d4af7a8b312f5970f68f`): 48-bit time, 64-bit nonce, height/size and recursive SHA256 groups; v2 09/23 | Match live-network bytes/hashes, including existing >32-bit timestamp cases | P04 proposes revised recursive groups and a state commitment; widths/hash/ASERT still need acceptance |
| Issuance and minerfund | v1 087/095, epoch series, 206; v2 11/12/26/27/28 (`28-ifp-removal.patch`) | Preserve historical rewards and activation behavior | Reconcile paper and D10 (D11 protocol faucet/IFP rejected); legacy and proposed schedules cannot both be active |
| Script/signature changes | v1 053, 060–079, 185, 230/232/240/242; v2 14/15 | Preserve historical enable/disable transitions | Inventory each opcode/flag; do not assume old Taproot fits new branch MAST ABI |
| XAddress and denomination | v1 address history; v2 06/07 | Existing addresses/RPC units compatible | New-chain address/signing policy and asset-aware amounts |
| NNG and indexer integration | v1 155/158/175; v2 10 | Verify current consumers and reconnect/replay | Port where useful; compare direct Chronik integration and IPC requirements |
| Mining/block assembly | 01/02/03 across candidate series | Optional after compatibility evidence; policy impacts separate | Measure V/E/bytes, fee quality and resource bounds before chain-limit removal |
| Native single-asset outputs and variadic paths | Former combined draft; v2 commented 09c | Not a v1 consensus feature to introduce | New design; D01/D03/D05 and vectors required |
| int128/introspection/enumeration | Historical opcode work, Mitra reference; missing v2 31/33 | Preserve v1 semantics only | Partial conceptual reuse; full opcode/ABI/cost implementation unproven |
| Authenticated state and new storage | Missing v2 34/35; old design prose | No retroactive v1 header commitment | State algorithm new consensus; storage/RPC separate daemon work |
| Genesis/network identity | Historical v1 pins and v2 16–19 | Exact intended running chain | Replace all v1 launch state with independently verified v2 identity |

## Promotion to verified status

For each port record original source(s), target base, semantic delta, affected components, original/regression tests, disposition and replacement commit. Append exact result records rather than replacing `NOT_RUN` with a historical “DONE.” Preserve superseded patches as provenance outside the active application sequence. Update the inventory whenever series/files change and regenerate its hashes from local bytes.

Current setup facts: `scripts/setup.sh` actually reads `bitcoin-abc-version` for v1; Makefile/header comments disagree. eCash and v2 share `workspace-v2` in current routing. Setup can reset a workspace or force a branch checkout, and patch application suppresses commit failures. V1-01 must resolve these before publication of safe execution commands. No setup/reset command was run for this planning pass.
