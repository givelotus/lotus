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
| `04-topological-mempool-check.patch` | Use existing topological index for optional diagnostic checking | Independent exact-tip replay/build/C++ checks pass. Native 512-chain ancestor visits fall from 130,816 to zero; admission policy is unchanged. Select `mempool-check` with experimental opt-in. |
| `10-nng-interface.patch` | Optional default-OFF NNG raw-payload publisher | Exact-pin independent NNG ON/OFF and ZeroMQ coexistence builds and real subscriber regtests pass; new framing is not Lotus wire compatibility. Select with explicit experimental opt-in. |
| `11-disable-zeromq.patch` | Default ZeroMQ OFF; source and explicit ON preserved | Independent one-line CMake default change; fresh default-OFF native daemon/CLI build and mining regtest pass. |
| `12-remove-zeromq.patch` | Delete implementation, dependencies, CLI/RPC/logging/docs/tests | Requires 11 first; no NNG/mining/mempool dependency. Exact application and native validation are documented in [the removal audit](../../docs/bchn-zeromq-removal.md). |

Chronik would require a substantial independent port; this series does not
provide one. Avalanche-finalization pruning does not fit BCHN's consensus model.

`zeromq-off` remains the existing build flag, without applying a patch.
`zeromq-default-off` selects 11; `zeromq-remove` selects ordered 11 then 12.
Source changes require `--allow-experimental`; default setup stays base-only.
Removal deliberately drops the public ZeroMQ interface, and is not an NNG
requirement or a claimed performance optimization.
