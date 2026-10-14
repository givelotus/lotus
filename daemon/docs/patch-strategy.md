# Lotus Mainnet Patch Strategy

The executable manifest in `daemon/patches/v1/series` and the base pin in `daemon/bitcoin-abc-v1-version` define the Lotus mainnet source that setup applies. See the [build guide](../README.md) and [validation report](v1-8c67fe1e85-validation.md).

## Patch Quality Standard

**These patches run a live network. Bugs mean lost funds, forks, or downtime.**

Every patch — whether written from scratch or rebased from history — must be
reviewed before it goes into a series. Sloppy context lines, half-applied hunks,
or logic errors that happen to compile are the failure mode. The goal is not "it
applies cleanly"; the goal is "it is correct."

### IMPCPD review

Every patch must pass IMPCPD review before being marked `DONE`.
See **`daemon/docs/impcpd-methodology.md`** for the full checklist and scoring guide.

Summary of the personas applied to every patch:
- **Regression** — does it break existing behavior?
- **Consensus Correctness** — is every branch of the state machine handled?
- **Security** — does it add a new attack surface?
- **Edge Cases** — genesis, empty mempool, reorg, disabled Avalanche?
- **Completeness** — all three networks updated? series file correct? `git apply --check` passes?
- **Tests & Docs** — test that fails before and passes after?
- **Minimality** — does it do exactly one thing?

A patch that fails Minimality (does more than it claims) must be split before
the other personas are even applied.

---

**Status legend:**
- `DONE` — applies cleanly, correct, no further work needed
- `NEEDS-REBASE` — logically correct but context lines outdated; re-express against current base
- `NEEDS-WRITE` — patch does not yet exist; write from scratch
- `NEEDS-FIX` — patch exists but has known placeholders or errors
- `NEEDS-EXTRACT` — change exists in a larger patch; pull out into its own named patch
- `SKELETON` — stub exists; implementation not started
- `NO-OP` — trivially empty against current base (upstream already applied it)
- `DEFERRED` — intentionally not yet done; blocked on a decision or another patch

---

## V1 — Lotus Mainnet

**Base:** bitcoin-abc `8c67fe1e85a602204a2ce65aa3b643469c2c3a1d` (`daemon/bitcoin-abc-v1-version`)
**Release:** `v11.6.0`
**Validation (2026-10-14):** All 153 patches replay onto the pinned base. Daemon/CLI, C++ tests, and Rust crate checks pass. Isolated mainnet replay reached height 1,400,898, `verifychain 4 1000` passed, and sampled Chronik headers and transactions matched RPC. This covers the V1 daemon; it does not establish validation of every monorepo component. The earlier `252182e9` rebase is historical.

### V1 Patch Manifest Summary (`daemon/patches/v1/series`)

| Range | Source / Purpose | Status | Notes |
|-------|------------------|--------|-------|
| `000` | `000-decouple-avalanche.patch` | `DONE` | Decouples Avalanche finalization & `MinerFundPolicy` / `StakingRewardsPolicy` from `ConnectTip` while preserving `src/avalanche/` and `ParkingPolicy` for optional coordination |
| `001–002` | Historical mining candidates | `AUDITED` | 001 experimental selection is reverted by 246 after native regression failures; 002 tests unchecked container insertion, not admission-policy changes. No speedup or O(1) admission claim. |
| `004–199` | `givelotus/lotusd` | `DONE` | Core Lotus protocol, 2-min blocks, ASERT, $\log_2$ issuance, 50% fee burn, Merkleized txid, 160-byte header + `vMetadata`, XAddress, NNG interface, epochs through Judges |
| `203–245` | `LotusiaStewardship/lotusd` | `DONE` | Ruth, 1st/2nd Samuel, 1st/2nd Kings epochs, Taproot (`P2TR`), `SIGHASH_LOTUS` |
| `246` | `246-port-chronik-and-rtt-for-lotus.patch` | `DONE` | Ports in-process Rust/C++ Chronik (`-DBUILD_CHRONIK=ON`: 160B headers, `vMetadata` disk offset, Merkleized `TxId::from_tx`, `P2TR` script indexing) and 120s `RTTPolicy` target spacing; restores upstream mining selection with boundary regressions |
| `247` | `247-bump-version-to-11.6.0.patch` | `DONE` | Bumps client version to `v11.6.0` and updates repository URLs to `givelotus/lotus` |

---

## Export and replay

Keep the 153-entry manifest aligned with 153 ordered commits on the pinned Bitcoin ABC base. Export each patch from its corresponding parent-to-commit diff. Apply the exported patches to a temporary Git index initialized from that base and compare the final tree with the implementation HEAD.

Patch 246 includes upstream API and build compatibility repairs alongside the Chronik/RTT adaptation. Historical Lotus activation rules and the replay-protection timestamp must remain unchanged during an upstream compatibility rebase.

Build and test in an isolated workspace. Mainnet replay and Chronik checks use a separate datadir and ports; preserve the running node and its chain data until a replacement has been validated. Changes to release source require the release build and protocol checks described in the validation report.

The V1 `refresh` helper rebases the patch series onto the requested Bitcoin ABC commit and updates `bitcoin-abc-v1-version`. Use it in an isolated workspace and resolve any conflicts before validation.
