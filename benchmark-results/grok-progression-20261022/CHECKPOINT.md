# Grok progression checkpoint

Append-only. Times are UTC.

## 2026-10-22T15:45:00Z

- Candidate `c7cf36456179e9a7ccdae3be03a749d3f07c8bda` on `lotus-v2-optimizations` (ahead of origin by 109). Canonical manifest `acc5bc80bde249d4f624da7ea9deb54a332e53507eb2b7e6539fb492b8de537d`. Contracts `50bce6c5004e9076b279b1a79bb73d3e45f03820c46f233df684ee16a01d5b6f`.
- Ordered stack: 527 mailboxes. eCash is global 1–374. V2 starts at global 375 and ends at 527. Endpoint points are 0, 374, and 527.
- Build profile from the runner: Release, wallet off, Qt off, ZMQ off, CLI on, bitcoin-tx off, Chronik off, seeder off, UPnP off, NAT-PMP off. Allocator is the process default. Three repetitions, 10 build jobs.
- Host: Apple M5 Max, 18 CPUs, 48 GiB, macOS 26.6. At freeze, memory free indicator 38%, vm pressure level 2, swap about 19.5/20 GiB used. `explore` pid 82695 is an unrelated one-core loop and was left running. Production and testnet `lotusd` processes were left running.
- No daemon benchmark or compile was already running. `benchmark-results/20261022/native527-dedicated-network500k-v1` is prepared and held; it is not started.
- Dirty tracked notes in `.gitignore`, `AGENTS.md`, and `daemon/patch-audit/progression/RECOVERY-APPEND.md` are saved at `preserved-dirty-candidate.diff` (`8be727f721cd8c52fa4adcd4e2c8f0a392cb44a596f4ee599bc4dadd0c3153dc`) and restored after the runner's clean-tree check. They are not part of this measurement.
- Next: point 0, then 374, then 527. Sustained 500k work is a separate fingerprint at those boundaries. Nothing is measured yet.

## 2026-10-22T15:45:30Z

- Point 0 passed the clean-tree check. Replay source is `1fb7db17c176cdea8a2c60d887891589382ee4e3`, tree `b2e4a0a9f57c`. Local clone ignored `--filter` (740 KiB git dir, 500 MiB worktree). Disk free stayed 111 GiB.
- Preserved dirty notes were restored. Stamp: `dirty-tree-restored.txt`.
- Configure passed. Ninja is building `bitcoind`, `test_bitcoin`, `test-avalanche`, `bitcoin-bench`, and `bitcoin-cli` with `-j 10`. Runner pid 17239. No timing result yet.

## 2026-10-22T15:48:00Z — point 0 complete

- Status ok. Source `1fb7db17c176cdea8a2c60d887891589382ee4e3`, tree `b2e4a0a9f57c593129028352d5dbb0c4ff294cdb`. Binary sha256 `788ca330b50ef094762b59d5c5be406b6f0958514287cac0ae0a777dcf84b074`, copied to `daemon/.local-artifact-archive/grok-progression-binaries/point-000-bitcoind`.
- Build 87.8s. Correctness passed: `mempool_tests`, `rpc_tests`, `miner_tests`, `proof_tests`, `delegation_tests`. Kernel benchmark absent. `gbt_compact` unavailable (`Invalid mode`), not zero.
- Workload is the runner's historical short burst: 500 or 801 transactions, three repetitions. These are not 500k sustained results. `json_rpc_batch50` puts 50 `sendrawtransaction` calls in one HTTP request. `single_tx` is one call per HTTP request. `relay500` waits until all three peers report mempool size 500.

| point | metric | median | min | max | n |
| --- | --- | --- | --- | --- | --- |
| 0 | single_tx tx/s | 12970.3 | 10623.1 | 13025.1 | 3 |
| 0 | json_rpc_batch50 tx/s | 21393.8 | 20442.6 | 22122.1 | 3 |
| 0 | relay500 tx/s, admission through 3-peer size 500 | 4093.1 | 4022.7 | 4125.7 | 3 |
| 0 | read_unloaded RPC method calls/s | 17179.4 | 17075.6 | 17197.8 | 3 |
| 0 | read_loaded RPC method calls/s | 9211.8 | 8905.1 | 9254.3 | 3 |
| 0 | block500 three-node ms | 5.533 | 5.455 | 10.464 | 3 |

- Next command: `--point 374`. Every patch 1–374 has a canonical source tree. Sustained 500k remains a separate run against the preserved point-0 binary.

## 2026-10-22T15:59:00Z — point 374 replay matched, measurement running

- Two immediate preflight refusals (`Commit candidate changes`) are not correctness failures. The runner requires a clean tracked tree. Tracked notes were stashed only across that check and restored. No failure packet was written.
- Replay of patches 1–374 matched canonical tree `11d13069e44bbe765b2e58413a90756f72988bb1` at `0252fc77a278aebbdbb399c2988ce4fed346faf6`. Configure passed. Ninja and the correctness gates are in progress. Runner pid 49444.
- Candidate commit recorded by the runner is `d1e1d785e04655dddfb525b911a92dff334c5a82`, which adds an unmeasured Merklix A/B harness and does not change the patch bytes.
- Sustained 500k is still unmeasured. The prepared native527 network run remains unlaunched.

| point | boundary | status | median | range | n | evidence |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | ABC `1fb7db17` | ok, short burst | see table above | n=3 | 3 | benchmark-results/grok-progression-20261022/patch_000.json |
| 374 | final eCash | build failed, then test assertion corrected; not remeasured | | | 3 | failure-point-374-build.json |
| 527 | final V2 | replay applies; not measured | | | 3 | |

## 2026-10-22T16:10:00Z — point 374 build failed; global 267 assertion corrected

- Runner pid 49444 is dead. Ninja `-j 10` returned 1 after 82.4s. The only compile error is `src/test/txrelay_tests.cpp:973` and `:974`: `no member named 'mining_template' in 'node::ChainAndMempoolSnapshot'`. Packet: `failure-point-374-build.json`. Attempt log: `attempts/patch_374/20261022T155947521732Z/build.log`. That packet is the pre-correction build. It is kept.
- The failed composed tree was `11d13069e44bbe765b2e58413a90756f72988bb1` at `0252fc77a278aebbdbb399c2988ce4fed346faf6`. Configure had passed. No timing ran.
- Owner is global 267, contract `recovered-relay-20261020-0004`, file `266-net-announce-transactions-by-8-byte-short-ids-to-peers-that-support-it.patch`. Patch 081 already publishes template ids through const `GetMiningTemplate()`. The assertion now calls that accessor and still requires the template id to increase by one. The check is not removed or weakened.
- Mailbox sha256 `ecc153bc653e2807eca3a041a9214b77fac87b2856683aacaf053e0ed345a3f3` became `7d013dc689b55e58418040890bea39d62838df555bf68d6177ca83ff474148ba`. No other mailbox bytes changed. `git am` of global 267–527 onto parent `6fb15ce153720a6d542089d95e5c1f3ca298a783` (tree `f0e76a205d629b487349f80d21ec4842e3b6ee4c`, same as stored global 266) produced 261 commits. Tip `cd3ee0cf18d633e5619a602470b89c5abda5ea65`, tree `ae49789b3d5571669121dbd596567fe74c0fcadb`.
- Refreshed canonical identities, historical `sha`/`tree`/`parent` unchanged. Prefixes before 267 unchanged, so the point 0 record stays current. Manifest sha256 `7fedd075eabc3612cbec86e4f30e815fa65c8565bdd614eaab108766fc44111c`.

| global | commit | tree |
| --- | --- | --- |
| 267 | `f59e780787e2d055ace43ec5ad05e848366c5891` | `5c51be8ee3e9f6843fe1afd90eb2612585940117` |
| 374 | `642e8c944f5bf41d6aee594f78e11c52a387c783` | `3ec37f7ca55f9383ef155d8ab81873e5905d984a` |
| 527 | `cd3ee0cf18d633e5619a602470b89c5abda5ea65` | `ae49789b3d5571669121dbd596567fe74c0fcadb` |

- Global 266's stored canonical commit remains `8894dcfabf4c1a3178bc468c2fd568785758c1d3`. This checkout's equivalent commit is `6fb15ce1` with the same tree. Prior composed-tree native/500k claims do not apply from global 267 onward.
- V2 patch 041 still names `mining_template` as a member. It applied with whitespace warnings only. It was not edited. Compile at point 527 is unknown.
- Repair ledger entry appended. Committed on `benchmark/grok-progression-20261022` as `1b3078c32f1b354041b154c0ebbc909d5ee34158`. Not pushed. Backup of this commit is the local branch only.
- Point 374 rerun started at pid 65859 after the clean-tree check. Notes were stashed only across that check and restored. The corrected replay tip remains on source branch `grok-corrected-replay-20261022`. Point 527 and the sustained 500k workload stay unstarted. The held native527 network run stays unlaunched.

## 2026-10-22T16:19:00Z — point 374 build failed on a missing txrelay include

- Pid 65859 exited. Ninja returned 1 after 79.1s. The only failed target was `v2_protocol_handler_tests.cpp.o`. `txrelay::` was undeclared because global 374 deleted `#include <net/txrelay_index.h>` while tests from global 267 and 268 still call `MakeEpochKey`, `ComputeShortId`, and `EpochKey`. Packet: `failure-point-374-missing-txrelay-include.json`. The earlier `mining_template` error did not return. Tree check had passed at `642e8c944f5bf41d6aee594f78e11c52a387c783` / `3ec37f7ca55f9383ef155d8ab81873e5905d984a`.
- The include is restored in global 374. `TXRELAY_HIGH_BANDWIDTH` and the `#include <common/args.h>` removal stay. The corrected object compiled with existing warnings and no errors.
- V2 patch 001 had added that include back. Its hunk now adds only `common/args.h` and keeps the existing txrelay header as context. All 153 V2 mailboxes then applied. Tip `e6e0fe3557503fe8d5df0a0425d2f9bcaaa8a5f6`. Its tree `ae49789b3d5571669121dbd596567fe74c0fcadb` matches the previous corrected V2 tip tree. Point 374's new tree is `0400e2c12189c9f38a450adf9ad0cbc97c1e310a`. Prefixes before 374 are unchanged. Manifest sha256 `a3bdec4dbc1a2994ca14e839af238d9958300486647506ebe93ee73f354c0a91`.
- Committed as `1032d92c08411754513f6ec22af85fef64c53b39` on `benchmark/grok-progression-20261022`. Not pushed.
- Point 374 rerun started at pid 77899. Notes were restored after the clean-tree check. Point 527 and sustained 500k stay unstarted.

## 2026-10-22T16:40:00Z — point 374 compiled, then suite selection failed

- Pid 77899 is dead. Ninja `-j 10` exited 0 in 91.2s. No unit binary was launched. `record.error` is `"'mempool_overlay_tests'"`, which is `KeyError` from `native_suite_selection`. `failure_details` is empty because no command failed. Packet: `failure-point-374-suite-schema.json`. Attempt: `attempts/patch_374/20261022T162005170525Z`. Source `62a0d4e3ee4b2ef4b0d9f6b6feea38eb9c85f122`, tree `0400e2c12189c9f38a450adf9ad0cbc97c1e310a`.
- Six contracts used Boost suite names as `required_native_suites` keys. The runner only accepts `bitcoin` and `avalanche`, and each value is a whole suite. Those suites are now under the matching binary. The named cases remain on `required_native_case_names`. No mailbox or source tree changed.
- `test_lotus_v2_commitment` is a separate executable from v2/024 (global 398), not a Boost suite. The runner builds and runs `required_standalone_binaries` when the ninja target exists. At global 374 that target is absent, so the result is unavailable, not zero. `tx_overlay_arena_matches_block_merkle_root` is added inside `mempool_overlay_tests` by v2/038; the whole suite is required from global 11.
- `rpc_independent_admission.py` and `wallet_v2_native_receive.py` are created by global 517. They moved from the global 374 contract to `native-wallet-receiving-20261020`. The wallet receive test skips when the wallet is off. This profile keeps the wallet off.
- Chronik, HTTP/2, and WebTransport are off in this build. Their translation units are not linked, so those file-scan suites are recorded as build exclusions. A compiled suite, or a suite a contract requires, still fails closed if it is unregistered. The point-374 binaries contain `mempool_overlay_tests`, `validationinterface_tests`, and `preconsensus_batch_tests`, and the simulated selection has no missing suite.
- Prefixes from global 11 through 527 were recomputed. Global 0–10, including the point 0 prefix, are unchanged. Manifest sha256 `6e0add0d0da2c10a6aa7ec33e31d56d7ca0cd25658b6fd6a3f79463d7f4b0be6`. Contracts sha256 `239f1426bec0af0d428abaa9bae54b709fb7677c3f1e71d7c04e00ac2d4a9890`.
- The runner file is part of the harness fingerprint. The previous point 0 record is preserved as `point0-ok-before-schema-harness.json`. Point 0 will be remeasured on this harness before point 374, then point 374. Point 527 and the sustained 500k workload stay unstarted. The held native527 network run stays unlaunched. Not pushed. Backup is the local branch after this commit.
- Schema repair committed as `31b635c10a0f1601f3b88a332f09d30d7621af0c`. Point 0 remeasure started as pid 94898 after the clean-tree check. Notes were restored. This is not a completed measurement yet.

## 2026-10-22T16:37:37Z — point 0 remeasured on the new harness

- Pid 94898 exited 0. Status ok. Source `1fb7db17c176cdea8a2c60d887891589382ee4e3`, tree `b2e4a0a9f57c593129028352d5dbb0c4ff294cdb`. Prefix `d31812321128763d3b6c9414b600f3dae02218575fd805b06391bb056ce3fe36`, same as the previous point 0 record. Harness `ef608f917cd0d321b5c4f4989b6b77ceb157554560d4c28ce2926cd5b898c7f3`.
- `bitcoind` sha256 `788ca330b50ef094762b59d5c5be406b6f0958514287cac0ae0a777dcf84b074`, byte-identical to the preserved copy. Configure 1.9s, ninja 67.2s. Units 0.4s, avalanche 0.5s, three legacy repetitions 11.1/10.8/10.7s. Correctness passed. No Chronik/HTTP2/WebTransport suites were linked. `gbt_compact` remains unavailable (`Invalid mode`). Kernel benchmark still absent.
- Same historical short burst: 500 or 801 transactions, n=3. Not a 500k result.

| metric | median | min | max |
| --- | --- | --- | --- |
| single_tx tx/s | 13446.2 | 12530.4 | 13649.8 |
| json_rpc_batch50 tx/s | 21176.6 | 13232.2 | 21195.0 |
| relay_ingest tx/s | 14740.5 | 13700.6 | 14760.7 |
| relay500 tx/s | 3986.4 | 3890.6 | 4242.7 |
| read_unloaded RPC method calls/s | 19025.2 | 19012.0 | 19032.3 |
| read_loaded RPC method calls/s | 9785.7 | 9116.2 | 10101.2 |
| block500 three-node ms | 5.554 | 5.379 | 8.042 |
| block801 three-node ms | 17.225 | 8.357 | 20.788 |

- `block801` three-node median is higher than the previous harness median of 8.995ms because one of three sub-25ms samples was 20.8ms. The daemon binary is unchanged. This is sample spread, not a source change.
- Next: `--point 374` on this harness. Point 527 and sustained 500k stay unstarted. Not pushed.
- Point 0 result committed as `ef2e1e01`. Point 374 runner pid 99681 started after the clean-tree check. Notes were restored. Not a completed measurement.

## 2026-10-22T16:41:00Z — point 374 unit gate failed two assertions

- Pid 99681 is dead. Replay, configure (1.5s), and ninja `-j 10` (84.1s) exited 0. `test_bitcoin` returned 201 after 21.9s. Source `62a0d4e3ee4b2ef4b0d9f6b6feea38eb9c85f122`, tree `0400e2c12189c9f38a450adf9ad0cbc97c1e310a`. Packet: `failure-point-374-unit.json`. Record copy: `patch-374-unit-failed.json`. Attempt: `attempts/patch_374/20261022T163943713948Z`.
- `metrics_tests/misbehavior_reasons`: `Transports().size() == 3U` failed `[4 != 3]`. The labels are `tcp`, `ws`, `wss`, `webtransport`. Global 363 added the fourth label and left the global 218 inventory check at 3. The test now requires that exact sequence. WebTransport stays off. The label is source inventory, not a compiled feature.
- `txrelay_tests/shorttx_fetch_publishes_unbroadcast_batch`: `after->GetMiningTemplate().template_id == before->GetMiningTemplate().template_id + 1` failed `[8615 != 8616]`. Both snapshots reported id 8615. `InitMiningTemplate` shares the previous cache when tip, nBits, `transactions_updated`, and mempool size are unchanged. Clearing unbroadcast publishes a new snapshot and does not change those inputs. The +1 check was the earlier compile repair and is the wrong observation. The test now requires one new snapshot, `PublicationCount` increased by one, a shared mining cache, and equal template ids. The second fetch must not publish again. Unbroadcast clearing and entry flags stay.
- Clean `git am` from global 266 parent `6fb15ce15372` applied 261 mailboxes. Only mailbox hashes for globals 267 and 363 changed. Point 374 is now `6dab13b0dd5a195e575ebb1f6d39117d02ed66b6`, tree `f460f6f809ac742a2c55bf83e4602a177edfd4ca`. V2 tip `b1e8d7bd4ee95a6d85ed9b3fb0b4d2cbc3cd8526`, tree `c0da886b2a452f28127038ccabcbc04727f451fd`. Prefixes 0–266 are unchanged, including point 0. Manifest sha256 `424b4aca9e4653285578adca421042e2389b5a15fcf6a9fa87697b13666ce473`.
- These gates have not passed on the repaired trees. Point 527 and the sustained 500k workload stay unstarted. The held native527 network run stays unlaunched. Not pushed.
- Repair committed as `4b63296f`. Point 374 runner pid 17829 started after the clean-tree check. Notes were restored. Not a completed measurement.

## 2026-10-22T16:58:13Z — point 374 stopped on a Chronik-off skip

- Pid 17829 is dead. Replay matched `6dab13b0dd5a195e575ebb1f6d39117d02ed66b6`, tree `f460f6f809ac742a2c55bf83e4602a177edfd4ca`. Prefix `d38949120a0f7493dde4cf48d5db017cb8a166d06de5a9947a9df068819db067`. Configure 1.8s, ninja `-j 10` 87.1s, `test_bitcoin` 23.6s, and `test-avalanche` 5.2s all returned 0. The repaired template and transport assertions held. No timing samples ran.
- `chronik_rpc_port_proxy.py` returned 77 in 0.131s. The log says `Test Skipped: Chronik indexer has not been compiled.` That test is required from global 84. It is the only Chronik functional in the 374 prefix. The measurement profile keeps `BUILD_CHRONIK=OFF`. Enabling Chronik would be a different benchmark.
- Packet: `failure-point-374-chronik-skip.json` (`84bf3bb2f3cd766242920c75aca67c1a474bb084788ee8a04136534b098b5386`). Record copy: `patch-374-chronik-skip.json` (`df43ceee0b5114c0fa58347bf82d4cb6c434f0984d243233f92265291120b68b`). Attempt: `attempts/patch_374/20261022T165509062173Z`.
- The runner now records exit 77 only for the closed set of feature-off framework reasons (Chronik, Chronik plugins, Chronik Electrum, wallet, bitcoin-wallet, ZMQ, HTTP/2) as `functional_skipped` with result `N/A` and `coverage` false. Any other non-zero status still fails. `wallet_v2_native_receive.py` at global 517 is the later wallet case. This edits `daemon/scripts/patch-progression.py`, so the harness changes. The previous point 0 record is `point0-ok-before-feature-skip-harness.json`. Point 0 must be remeasured on harness `10bb374b410b4e684b465fab223ffe3a48f1bf3d8c8f285f04e23d0f960bc8c3` before point 374 can be compared. Prefixes are unchanged.
- `websocket-client` 1.9.2 and `zstandard` 0.25.0 are installed for `/usr/local/bin/python3`, which is the interpreter that runs functional tests. `p2p_websocket_inbound.py` skips the whole test when those modules are missing. That skip is not in the feature-off set, so the modules were installed and the test must actually run. OpenSSL 4.0.3 is on `PATH`.
- Point 374 is not measured. Point 527 and the sustained 500k workload stay unstarted. The held native527 network run stays unlaunched. Not pushed.

## 2026-10-22T17:10:48Z — point 0 remeasured on the feature-skip harness

- Pid 53019 exited 0. Status ok. Source `1fb7db17c176cdea8a2c60d887891589382ee4e3`, tree `b2e4a0a9f57c593129028352d5dbb0c4ff294cdb`. Prefix `d31812321128763d3b6c9414b600f3dae02218575fd805b06391bb056ce3fe36`, unchanged. Harness `10bb374b410b4e684b465fab223ffe3a48f1bf3d8c8f285f04e23d0f960bc8c3`. Candidate `e2b648177b80890babfeae3a7c195bdc9105556d`.
- `bitcoind` sha256 `788ca330b50ef094762b59d5c5be406b6f0958514287cac0ae0a777dcf84b074`, byte-identical to `daemon/.local-artifact-archive/grok-progression-binaries/point-000-bitcoind` and to the previous harness. Configure 1.7s, ninja 60.7s, units 0.4s, avalanche 0.5s, three legacy repetitions 11.3/10.7/10.8s. No functional tests are required at point 0, so `functional_skipped` is empty. `gbt_compact` remains unavailable (`Invalid mode`). Kernel benchmark still absent.
- Same historical short burst: 500 or 801 transactions, n=3. Not a 500k result. This record replaces `patch_000.json` as the comparison baseline. The previous harness record remains `point0-ok-before-feature-skip-harness.json`.

| metric | median | min | max |
| --- | --- | --- | --- |
| single_tx tx/s | 14324.0 | 14132.5 | 14396.0 |
| json_rpc_batch50 tx/s | 21724.9 | 21609.6 | 21949.4 |
| relay_ingest tx/s | 14668.8 | 13511.4 | 14780.6 |
| relay500 tx/s | 4099.5 | 3867.3 | 4105.1 |
| read_unloaded RPC method calls/s | 19009.4 | 18699.9 | 19111.4 |
| read_loaded RPC method calls/s | 10084.7 | 9628.3 | 10318.8 |
| gbt_standard p50 ms | 1.549 | 1.548 | 1.561 |
| block500 three-node ms | 5.275 | 5.164 | 5.470 |
| block801 three-node ms | 19.275 | 17.840 | 24.604 |

- `block801` still includes one sample above 20ms on the unchanged binary. That is sample spread. Next: `--point 374` on this harness. Point 527 and sustained 500k stay unstarted.

## 2026-10-22T17:15:57Z — point 374 functional gate failed in prefetch metrics

- Pid 57307 is dead. Units and avalanche passed. `chronik_rpc_port_proxy.py` was recorded N/A (`Chronik indexer has not been compiled.`, coverage false). Ten functional tests passed. `interface_http_metrics.py` returned 1 after 5.1s. Source was still `6dab13b0dd5a195e575ebb1f6d39117d02ed66b6`, tree `f460f6f809ac742a2c55bf83e4602a177edfd4ca`. No timing samples.
- The log is `TypeError: 'Scrape' object is not subscriptable` at `samples[("fullnode_block_prefetch_started_total", ())]`. Global 277 added those empty-label subscripts after `scrape()` already returned `Scrape`. The rest of the test uses `value(m(name))`, which ignores the constant client and network labels. The expected counts are unchanged. The empty tuple was not a series key.
- Packet: `failure-point-374-http-metrics.json` (`b922f1ff88dc162fa2e7384e0f7eb60043fd9108b4fa31a9c44605263ef95262`). Record copy: `patch-374-http-metrics-failed.json` (`01d8fb4324120cef1dffc1997e651db43fd5a70b20964d6925506bac7f7560c8`).
- Clean `git am` from global 276 parent `96998e2e9065` applied 251 mailboxes. Only global 277's mailbox hash changed, to `075ecb5b6d60d81da83562f48399654f948fa5a2c6da82ded57b956378eb80dc`. Prefixes 0–276 are unchanged, including point 0. Point 374 is now `f14e7838966a651ee808e619e0c628fb5d9c90dd`, tree `6f3d52f6198117d0dfba12ae2e0bb2d10b519f2d`. V2 tip `ec6f79f7b6c497e70c57a3442bd7d714d7602ef3`, tree `41e7c702526a0687cdbc3148286b72fea8c7605a`. Manifest sha256 `d2ff0bf40293b1d2bd36268d3669b34a42675ddbef9700083620a985ea632e02`. Historical `sha`/`tree`/`parent` fields were left as provenance.
- These gates have not passed on the repaired tree. Point 527 and the sustained 500k workload stay unstarted. The held native527 network run stays unlaunched. Not pushed.

## 2026-10-22T17:29:00Z — repaired point 374 measurement started

- Merklix ninja 9690 and shell 9687 finished. No other ninja or cmake was running. Notes stash `9cd0588c` was popped after the dataset manifest rewrite and the stash list is empty.
- Runner pid 14080. Candidate `c4938895e56304abc177764542fc57c0252cd4f1`. Harness `10bb374b410b4e684b465fab223ffe3a48f1bf3d8c8f285f04e23d0f960bc8c3`, unchanged by the unmeasured Merklix dispatch commit. Repetitions 3, jobs 10. Expected point 374 source `f14e7838966a651ee808e619e0c628fb5d9c90dd`, tree `6f3d52f6198117d0dfba12ae2e0bb2d10b519f2d`.
- Host memory pressure level 2. Swap about 34.5/35.8 GiB used. Unrelated `explore` pid 82695 remains. Replay had reached global 276 parent `96998e2e90` while this note was written. No timing yet.

## 2026-10-22T17:37:22Z — point 374 passed

- Pid 14080 exited 0. Status ok. Source `f14e7838966a651ee808e619e0c628fb5d9c90dd`, tree `6f3d52f6198117d0dfba12ae2e0bb2d10b519f2d`. Prefix `3b214d5fdd071e4eb02784754d344263e97a1fd19938b5cb0bbc80374764e767`. Harness `10bb374b410b4e684b465fab223ffe3a48f1bf3d8c8f285f04e23d0f960bc8c3`. Candidate at start `c4938895e56304abc177764542fc57c0252cd4f1`.
- Configure 2.0s, ninja 96.1s, units 25.5s, avalanche 6.0s. Correctness passed. 35 functional tests passed. `chronik_rpc_port_proxy.py` is N/A (`Chronik indexer has not been compiled.`, coverage false). `test_lotus_v2_commitment` is unavailable at this boundary. Chronik, HTTP/2, and QUIC suites are unlinked and are not coverage.
- `bitcoind` sha256 `7946be7840ec3a70f6294599ee517b91a9b4708cda3c67f99609abd909461c75`, copied to `daemon/.local-artifact-archive/grok-progression-binaries/point-374-bitcoind`. The point 0 archive `788ca330` was left in place.
- Comparable workload is `legacy-v2-p2pkh-schnorr64`, 500 or 801 transactions, n=3. This is a short burst. The change from point 0 to point 374 spans patches 1–374 and is not isolated to one patch.

| metric | point 0 median (min–max) | point 374 median (min–max) |
| --- | --- | --- |
| single_tx tx/s | 14324 (14133–14396) | 9277 (7528–9477) |
| json_rpc_batch50 tx/s | 21725 (21610–21949) | 20910 (19030–22780) |
| relay_ingest tx/s | 14669 (13511–14781) | 9637 (7543–9839) |
| relay500 tx/s, admission through 3-peer size 500 | 4100 (3867–4105) | 8538 (6863–8718) |
| read_unloaded RPC method calls/s | 19009 (18700–19111) | 12230 (9230–12240) |
| read_loaded RPC method calls/s | 10085 (9628–10319) | 7003 (5348–7055) |
| gbt_standard p50 ms | 1.549 (1.548–1.561) | 1.762 (1.732–1.805) |
| block500 three-node ms | 5.275 (5.164–5.470) | 9.439 (7.287–9.633) |
| block801 three-node ms | 19.275 (17.840–24.604) | 14.66 (14.53–14.84) |

- Legacy `gbt_compact` is unavailable at point 374 (`standard template returned`). At point 0 it was unavailable (`Invalid mode`). Neither value is zero.
- `historical-l1` ran only at point 374, because batch RPC is registered there. Point 0 has no matching samples. Its largest admission is 6000 transactions in about 0.04–0.54s, so its tx/s figures are short bursts. One-call batches: 6000 requests, median 11170 tx/s. Batches of 200: 30 HTTP requests, median 136300 tx/s. A 4000-transaction batch of 1000 lasted median 0.027s (145800 tx/s). Three-node relay of a 6001-transaction block took median 68.4 ms. These are not a 500k sustained result and are not a comparison with point 0.
- Point 527 and the sustained 500k workload stay unstarted. Not pushed.

## 2026-10-22T17:44:30Z — point 527 measurement started

- Merklix ninja 61030 finished. No other ninja or clang had a Merklix build directory as its working directory. Notes stash `bf1c8fa8` was popped after the dataset manifest rewrite. The stash list is empty.
- Runner pid 64312. Candidate `e3c62b33`. Harness `10bb374b410b4e684b465fab223ffe3a48f1bf3d8c8f285f04e23d0f960bc8c3`. Repetitions 3, jobs 10. Expected tip `ec6f79f7b6c497e70c57a3442bd7d714d7602ef3`, tree `41e7c702526a0687cdbc3148286b72fea8c7605a`.
- Host memory pressure level 2. Swap about 30.6/31.7 GiB used. Replay was in progress at `ced306c14c` when this note was written. No timing yet. V2 patch 041 still names `mining_template`; its compile has not been tested.

## 2026-10-22T17:48:00Z — point 527 build failed in the txrelay template test

- Pid 64312 exited 1 after 167s. Replay reached the V2 tip and ninja failed while compiling `src/test/txrelay_tests.cpp`. No timing samples.
- The test still called `PublicationCount`, `mining`, and `GetMiningTemplate`. V2 patch 041 removes those and stores `mining_template` by value. Packet `failure-point-527-txrelay-template-api.json` (`9c7331e9dbd436034ab225fdba991816628ed9570257e905fc96241cb7abe5ff`).
- The test in that mailbox now calls `EnsureMiningTemplate()` and requires the new template id to be the previous id plus one. Snapshot identity, `transactions_updated`, mempool size, and the unbroadcast flags stay checked. Prefixes 0–414 are unchanged, so the point 0 and point 374 records stay valid.
- Replayed tip `aa4f90e58240072c0f2cb7bf54fa502d36ca05b6`, tree `4bff83f7c062f483ec7958db7695b674b75b7404`. Global 415 commit `901e2815b831d144f77e2774966883f9a3aeff99`, tree `b5c554fa52ca19f0eb89b5ed76756dc0826b465b`. These gates have not passed. The sustained 500k workload stays unstarted.

## 2026-10-22T17:56:05Z — point 527 compiled, then the state-sync suite was not registered

- The template-id rebuild, pid 77942, compiled and linked. The gate then stopped: `ecash_state_sync_tests` is required by split-20 and the source file still defines that suite, but v2/040 had removed it from `test_bitcoin`. Packet `failure-point-527-unlinked-state-sync-suite.json` (`fa274d86f98461f8505b5f1d4d866ec78b2f67f536cf7d947979e7e9e066f95f`). No timing samples.
- v2/040 now links `ecash_state_sync_tests.cpp` beside `native_state_sync_tests.cpp`. The SnapSync comment text stays, so v2/122 through v2/124 still apply. The program-binding case corrupts the stored legacy script on this regtest fixture, and the coinbase-context case selects a version-7 coinbase. A direct run passed 8 cases and 6447 assertions. That is not the canonical gate.
- Replayed tip `775040d51b9b483181a3f4f6300d85ca495fda08`, tree `b98c3ebc4a108a21daf41f48ec9922619f4b497d`. Global 414 commit `a62bb760c85de1640b97c4157e9caeeb20fbd2c9`, tree `020fca4a3ebe840b05edb9c4bd2dd958c5763c52`. Prefixes 1–413 are unchanged. Point 0 and point 374 stay comparable. The canonical remeasure has not finished.
