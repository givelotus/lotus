# BCHN review features

Acceptance base: current BCHN master `abd433abe04f74780744b9eac06731f3690ce68a`
(29.2.1), resolved 2026-10-14. Default setup applies no optional patches.
See [the current audit](../../docs/bchn-current-audit.md).

| File | Purpose | Status |
|---|---|---|
| `01-prioritize-ready-transactions.patch` | Highest modified-feerate newly ready sibling first, preserving existing direct-parent scheduler | Applies at the exact pin; native miner tests pass, including two failed assertions before the fix. Full checks/functional evidence recorded in the audit. |
| `01-nlogn-block-construction.patch` | Historical experimental transitive-package replacement | Broken, retained for provenance; no longer selected. Current BCHN already avoids quadratic dependency traversal. |
| `02-remove-chaintx-limit.patch` | Historical unchecked-container-only test | Not an admission-policy change. BCHN already removed chain limits in 2021. |
| `03-mempool-cleanup.patch` | Historical comment-only no-op | Never apply. |
| `10-nng-interface.patch` | Optional default-OFF NNG raw-payload publisher | Exact-pin independent NNG ON/OFF and ZeroMQ coexistence builds and real subscriber regtests pass; new framing is not Lotus wire compatibility. Select with explicit experimental opt-in. |
| `11-remove-zeromq.patch` | Historical source-removal placeholder | Unimplemented; existing `BUILD_BITCOIN_ZMQ=OFF` independently disables ZeroMQ. |

Chronik would require a substantial independent port; this series does not
provide one. Avalanche-finalization pruning does not fit BCHN's consensus model.
