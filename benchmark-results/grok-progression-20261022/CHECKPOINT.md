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
- Repair ledger entry appended. Next: commit this identity on `benchmark/grok-progression-20261022`, then rerun `--point 374` with 3 repetitions and 10 jobs. Point 527 and the sustained 500k workload stay unstarted. The held native527 network run stays unlaunched.
