# Doged current-ABC validation

The maintained [174-patch series](../patches/doged/README.md) builds and runs on immutable Bitcoin ABC `1fb7db17c176cdea8a2c60d887891589382ee4e3`, rechecked against the primary remote at the end of this work. It preserves Tobias's lineage while adapting modern ABC and Chronik APIs. **Full Dogecoin mainnet synchronization is not complete.** No production workspace, node, chain data, release, tag or upstream PR was changed.

Final integration source is `2ddac16d140df1b9637ec489bffeba287669434e`, tree `b019768499700c6cca14007f211358bd2b0aed82`. Metadata-maintained export is `29472b1ee39663516050d5e2064cf7fee95245a5`, with the identical source tree. Work is committed on monorepo branch `doged-current-abc-complete` in `/tmp/lotus-wt-doged-complete`; the standalone integration source is `/tmp/lotus-doged-complete-source`. The older partial-port base and original Doged reference remain distinct and unchanged.

## Separate acceptance evidence

| Check | Result / scope |
| --- | --- |
| Clean application | All 173 mailbox patches replay with shared `patch-series.py`; every intermediate tree and author/date/message digest matches. |
| Chronik ON build | Native macOS arm64 `doged`, `doge-cli`, native/PoW/Avalanche test binaries build on exact final source. |
| Chronik OFF build | Separate build succeeds; isolated node mines through regtest 22, `verifychain 4 0` passes, raw-work fields match, and `-chronik=1` is rejected as unsupported. |
| Main native suite | **756/756 cases, 32,817,013 assertions pass** on final source. Both full mining validity scenarios execute. |
| PoW suite | **14 cases pass**, including historical Dogecoin difficulty and transition coverage. |
| Optional coordination units | Avalanche **144 cases / 17,717,486 assertions**; RTT **3 cases / 19,093 assertions** pass on final source. No live-quorum claim. |
| Functional suite | **17/17 pass** on final source; cases listed below. |
| Rust / consumer code | Final integrated source: core 49 unit + 58 doc tests; Chronik DB 38; indexer 14; explorer 3 unit + 1 doc test pass. |
| Mainnet parity | Final binary: 5 sampled blocks / 103 transactions, exact headers, TxIds and raw transaction disk bytes match Chronik and RPC; `verifychain 4 1000` passes at accepted height 14,942 with zero peers. |
| GPU mining | M5 Max OpenCL Scrypt produced an accepted regtest block at height 22 through `getrawunsolvedblock`/`submitblock` on an earlier integration binary; independent RPC/Chronik/disk parity and `verifychain 4 0` passed. Miner subtree unchanged; final native/functional tests separately validate the final node. |

Commands, binary hashes, source identities, test counts, local log hashes and detailed distinctions are retained in [node validation evidence](evidence/doged-current-abc-validation-20261014.json) and [replay/OFF/Rust/miner evidence](evidence/doged-current-abc-maintenance-20261014.json). The maintained series README supplies replay/build commands. `SERIES=doged` selects the current-ABC Dogecoin implementation; `SERIES=doged-reference` selects the historical Doged source.

The final functional batch runs `dogecoin_auxpow.py`, `chronik_dogecoin_reorg.py`, `dogecoin_activation.py`, `dogecoin_transaction_order.py`, `dogecoin_raw_mining.py`, `feature_legacy_script_flags.py`, `feature_legacy_script_rules.py`, `feature_legacy_signrawtransaction.py`, `chronik_block.py`, `chronik_block_header.py`, `rpc_signmessage.py`, `dogecoin_rpc_psbt_versions.py`, `feature_deterministic_chain_setup.py`, `rpc_dumptxoutset.py`, `feature_assumeutxo.py`, `dogecoin_default_fees.py`, and `dogecoin_p2p_inv_download.py`.

These cover ordinary and AuxPoW mining/activation, competing branches and reconnect/restart, dependency-order UTXO undo, signed transaction versions, wallet signing, fees, generated snapshots and Chronik header/transaction/disk indexing. They are a selected integration suite, not a claim that every inherited upstream functional test has been ported or executed.

## Real mainnet observation

Both online tests used fresh isolated data, disabled Avalanche, enabled Chronik and `assumevalid=0`. They did not borrow a production datadir.

- **Default minimum chain work:** 1,033.1 seconds of observation; accepted **0 blocks**, maximum logged header presync **808,000**. Header presync is not accepted blocks or full synchronization.
- **Explicit test-only `-minimumchainwork=0`:** 540.7 seconds of observation; accepted **14,942 blocks**, header index **918,000**, IBD still true. Last accepted hash: `f04f18b14bec6bf450ae09f64fed9ce8b8014df8d6424973775c65d246690420`.
- All downloaded blocks were replayed offline with `-reindex-chainstate -chronikreindex` at source `cb3a8cfc15a683972a057ff6bd2d8a6fee555b8f`, with full verification and no peers. That run reached 14,942 again, rebuilt Chronik and passed `verifychain 4 1000`.
- The three subsequent commits change only optional finalized mining order and its native tests. The **final binary** separately passes offline parity and `verifychain 4 1000` over that data. The earlier whole-chain replay is retained with its actual source identity rather than relabelled as a final-source run.

This sample does not cross real DigiShield height 145000 or AuxPoW height 371337. Historical/native/generated boundary tests passed, but sustained default-work synchronization to the network tip and full historical chain validation remain outstanding. Earlier reference download through height 100 remains separate historical evidence.

## Repairs exposed by validation

The independent audit compared actual historical consensus behavior against immutable official Dogecoin Core `47a303a449999314abcf83bd1fc7e77dd4540fcd`. It found and repaired canonical AuxPoW activation, legacy numeric/DER/P2SH behavior, fixed block-size enforcement, sequential non-CTOR UTXO availability, the initial DigiShield header-presync target, and aggregate fees beyond the per-transaction money bound. Each correction has dedicated rationale and regression coverage; this is not a formal equivalence proof.

Final combined validation exposed a genuine optional mining bug after sequential UTXO validation was corrected: the upstream finalized radix tree produced TxId order even when Dogecoin CTOR was disabled. An intermediate native run passed 755/756 cases and failed the preconsensus mining case. The repair preserves finalized membership/accounting and emits deterministic dependency order. The final regression guarantees a child ID below its parent's, checks the independent expected order and repeats template construction. All 756 cases now pass; no assertion was skipped to conceal the failure.

Aggregate fees above signed int64 saturate for reward comparison and optional accounting. Valid coinbases are individually bounded below that maximum, so the mathematical reward comparison remains valid. Official Core's corresponding signed-overflow behavior is undefined; equivalence at that extreme is not claimed. This caveat and historical presentation omissions are recorded in the candidate's provenance rather than silently discarded.

## Preserved interfaces and explicit gaps

Chronik and ordinary PoW do not require Avalanche. Chronik ON/OFF and ZeroMQ remain independent build choices; Avalanche/RTT are retained and default off at runtime. No compile-time Avalanche removal switch or operational network quorum is claimed. Separate optional native evidence is recorded in the node evidence JSON.

NNG was absent from original Doged and remains unimplemented; no substitute protocol was introduced. Original mining RPCs remain, with new direct-work `getrawunsolvedblock`. `getauxblock`, `createauxblock` and `submitauxblock` work-construction services are still absent: accepting an externally constructed AuxPoW block does not provide merged-mining coordination. The miner has no Stratum client or live mainnet mining validation. See the [interface audit](doged-interface-compatibility.md) and [miner instructions](../../miner/README.md#dogecoin-direct-scrypt-mining).

Inherited Electrum address aliases remain CashAddress-only; standard scripthash queries are retained for native Dogecoin consumers. Synthetic legacy Chronik migrations pass, but arbitrary existing databases, GUI/browser deployment, SDK service integrations, other GPU/platform packaging and every inherited extended functional suite remain unvalidated. Historical logos/styles/documentation are explicitly classified in the 414-entry inventory. No claim of complete compatibility extends beyond the recorded checks.
