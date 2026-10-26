# Historical daemon development-command link prerequisite

Read-only source/history review. No checkout switches, source edits, bundles/replays, builds/tests or new worktrees. The earlier executor lane is now assigned elsewhere and was not accessed for edits. All gitshow/log/grep reads used the existing grok-progression-source object store; active HEAD was not changed.

Frozen reviewed refs:

- Shared `fec2cab9ce9d8f2ba2bb451ce2bdcdc3a7897830`.
- Current native `cd8eef5cc3989486ac5511562036871790a36aba`.
- Failed native position32 `cdc93b4e4c02560ac75eb1a8688ed37cf608a6cc`.
- Failure evidence: benchmark-results/20261023/atomic-c4-native-prefix-gates-repaired2/32/build.log, lines1337–1344. The daemon link reports only `lotus::v2::RunDevelopmentCommand(int,char**)` undefined from `_main`; subsequent test_bitcoin link succeeds. This review adds no runtime/build claim.

## Causal chain, exact owners

Positions below are1-based `git rev-list --reverse fec2cab9..cd8eef5c`.

| Position / owner | Exact source effect |
| --- | --- |
| 23 / `e5181e6bee224a9c82f030488b5cd013bd056833` — development genesis/chain/runtime/command interfaces | First introduces src/lotus_v2/development_command.cpp and .h, plus development_chain/runtime sources. Header declares RunDevelopmentCommand; cpp defines it atline179. No production CMake source assignment in this commit. |
| 24 / `68a0fee15171739c1ffc668d20adec5e0243002a` — standalone storage/runtime libraries | Registers the native foundation CMake targets. lotus_v2_validation includes development_chain.cpp, disk_state.cpp, monetary.cpp, header_context.cpp and related implementation; development runtime has its separate target. development_command.cpp is absent from daemon and all foundation libraries. |
| 32 / `cdc93b4e4c02560ac75eb1a8688ed37cf608a6cc` — native consensus integration | First includes development_command.h in bitcoind.cpp and calls RunDevelopmentCommand for explicit -lotusv2development. Same owner links server to lotus_v2_validation, but leaves `add_executable(lotusd bitcoind.cpp)` unchanged. This introduces the actual undefined reference. |
| 33 / `1c3aff310f026bd48aecab7b76c59d4c38aa6d38` — SQLite/native wallet providers | Adds development_command.cpp to lotus-v2-wallet-pilot and POSIX lotus-v2-wallet-client executable sources, and standalone wallet review targets. These executable-local objects do not provide a symbol to lotusd. Their src/wallet subtree is entered only under BUILD_WALLET. They are not a daemon repair, with wallet ON or OFF. |
| 59 / `156574f06e940d9982f9c50d35bff9fa31ac4f2a` — decentralized share-pool coordinator | First assigns development_command.cpp to the daemon: `add_executable(lotusd bitcoind.cpp lotus_v2/development_command.cpp)`. Also changes daemon direct linkage from server to server+lotus_v2_validation. This is the first later historical source change that closes the missing-object cause. It is unrelated to the share-pool feature's new mining_pool.cpp behavior. |

`git log -G 'RunDevelopmentCommand|development_command.cpp'` and the narrower daemon CMake history identify these owners. `git log -G 'development_chain.cpp|add_library\(lotus_v2_validation'` identifies position24. No earlier production CMake assignment of development_command.cpp was removed: this is a caller introduced before target-source registration, not accidental dropping of an already-wired source.

## Immutable definition/header evidence

The following exact blobs are identical at position23, failed position32 and current native tip. `git log` restricted to development_command.{cpp,h} reports only their introducing position23 owner in the native range.

| File | Git blob | SHA256 |
| --- | --- | --- |
| src/lotus_v2/development_command.cpp | `a54816e352450cca332a0dc69037c909b4b12438` | `6c5baba91dcacb24e9d80ef78b7317920c06158791076e41ca10932030a48eea` |
| src/lotus_v2/development_command.h | `15874d6e0de7db2032399af95b24080a13da2e46` | `d04c7cb0537fdce552d3760e4269ffea60faa2b3bfd5e0aa88074cf483ecf57e` |

Definition and declaration signatures already match: `int RunDevelopmentCommand(int argc,char *argv[])`. No implementation body, header fix, wrapper or stub is missing. The cpp includes development_chain.h and univalue; it has no wallet include or wallet preprocessor condition. Its manifest/home parser helpers are in the same cpp. Calls to OpenDevelopmentChain, ConnectEligibleDiskBlock and DisconnectDevelopmentTip use the existing position23 development_chain.cpp; monetary/header/disk dependencies are already in the validation/library closure registered by24.

## Smallest bounded exact-source relocation

At position32, add only the preexisting cpp filename to the daemon executable declaration:

```diff
 # lotusd
-add_executable(lotusd bitcoind.cpp)
+add_executable(lotusd bitcoind.cpp lotus_v2/development_command.cpp)
 target_link_libraries(lotusd server)
```

At position59, remove only the now-redundant executable-source hunk from that owner's diff. Retain its existing purposeful direct-link addition and all pool/coordinator source:

```diff
 # lotusd
 add_executable(lotusd bitcoind.cpp lotus_v2/development_command.cpp)
-target_link_libraries(lotusd server)
+target_link_libraries(lotusd server lotus_v2_validation)
```

This moves one literal target-source assignment to the first caller without moving any cpp contents or enabling another feature early. It retains the explicit -lotusv2development mode, strict manifest/data-home checks and every implementation byte. It requires no BUILD_WALLET guard or new native library. The endpoint source/CMake tracked tree can remain exactly equal to the frozen input because position59 already has the same final executable declaration.

Why the later direct-link addition need not move: position32 already links server to lotus_v2_validation with the existing non-PRIVATE target_link_libraries form. The actual failed link command proves src/lotus_v2/liblotus_v2_validation.a, its dependency libraries and src/univalue/libunivalue.a are already on the daemon link line. The undefined item is the executable-local RunDevelopmentCommand definition, not an omitted validation archive. Retain the later direct link in its original owner for minimum historical movement. Root must still compile/link position32 after the source assignment; static source reasoning is not a passing gate.

Safe editing bounds: require exactly one daemon declaration `add_executable(lotusd bitcoind.cpp)` at frozen32 and exactly one final declaration containing development_command.cpp at frozen59. Modify only src/CMakeLists.txt at the two mapped owners. Do not copy the entire current wallet/pool CMake or current development runtime target into32; no necessary prerequisite is absent from the frozen command source/header history.

## Required root proof and gates

Root owns recovery bundles, old-to-new ledger, rewritten refs and replay. Before rewriting preserve exact refs and dirty state. Ledger one row: position59 daemon development-command source assignment moved to position32 first caller; all implementation/header bytes retained at23; later direct validation link and pool source stay59. Preserve earlier five exact-owner repairs and this review's frozen ref identities.

Require the final tracked Git tree after replay to equal current frozen cd8eef5c tree exactly for this pure placement change. Verify all intermediate trees/commit mappings; source-code identity alone does not prove build order. Build/link lotusd, lotus-cli and test_bitcoin at repaired32 with the same Release/Chronik-OFF flags, then rerun intended prefix suites. Later prefix50/94 and complete endpoint need their scheduled gates; do not infer them from this32 diagnosis.

A bounded CLI smoke gate can exercise `lotusd -lotusv2development` argument validation, expecting the existing usage error/exit1 from the real command implementation. Full command validation should use its retained development_command_test documentation/fixtures and must preserve isolated manifest/datadir behavior; no generated stub or feature bypass. If adding the real cpp exposes another genuine prerequisite, trace its exact first owner separately rather than guessing compatibility implementations or removing the call.
