# Doged on current Bitcoin ABC

This review candidate contains **174 maintained mailbox patches** on immutable Bitcoin ABC **`1fb7db17c176cdea8a2c60d887891589382ee4e3`**, resolved from the primary upstream remote on 2026-10-14. It ports Tobias's Dogecoin implementation and retains current ABC/Chronik APIs. It is a working build candidate; **full Dogecoin mainnet synchronization remains incomplete**. Production nodes, data, original workspaces and published releases were not modified.

The old [23-patch candidate](../doged-on-current-abc-initial/README.md) remains unchanged on `8c67fe1e85a602204a2ce65aa3b643469c2c3a1d`. The validated reference `SERIES=doged` still selects original Doged `9690833b8b6709b7a7837bc397f0d04bf3b885d1`; it does not silently select this new source.

| Identity | Exact value |
| --- | --- |
| Upstream base | `1fb7db17c176cdea8a2c60d887891589382ee4e3` |
| Tested integration commit | `3047eec50b23b9ad0ceba53e507c034b73ec4efa` |
| Metadata-maintained export commit | `59b343a4dcce4259fa8eec8562ec5f0cb2cb3da2` |
| Final source tree | `2b378152efca0ea2c578433f348e71db367202b0` |
| Doged lineage reference | `9690833b8b6709b7a7837bc397f0d04bf3b885d1` |
| Official Dogecoin Core comparison | `47a303a449999314abcf83bd1fc7e77dd4540fcd` |

## Replay and build

From the monorepo root, use a **new** directory. The existing patch-series tool verifies every intermediate tree and mailbox author/date/message before promoting the complete result. Do not run setup/reset against an original or production workspace.

```sh
git clone https://github.com/Bitcoin-ABC/bitcoin-abc.git /tmp/doged-current-review
git -C /tmp/doged-current-review checkout --detach \
  1fb7db17c176cdea8a2c60d887891589382ee4e3
python3 daemon/scripts/patch-series.py /tmp/doged-current-review \
  daemon/candidates/doged-on-current-abc/series \
  --base 1fb7db17c176cdea8a2c60d887891589382ee4e3 \
  --provenance daemon/candidates/doged-on-current-abc/manifest.json \
  --expect-tree 2b378152efca0ea2c578433f348e71db367202b0

cmake -S /tmp/doged-current-review -B /tmp/doged-current-build -GNinja \
  -DBUILD_CHRONIK=ON -DBUILD_QT=OFF -DBUILD_ZMQ=OFF \
  -DENABLE_UPNP=OFF -DENABLE_NATPMP=OFF -DENABLE_MAN=OFF \
  -DRust_TOOLCHAIN=1.93.0 \
  -DPython_EXECUTABLE=/opt/homebrew/bin/python3.13
ninja -C /tmp/doged-current-build doged doge-cli test_bitcoin
ninja -C /tmp/doged-current-build check-bitcoin check-pow
```

The Python path above is the tested macOS host path; select an installed Python 3.13 on another host. Build prerequisites remain the upstream documentation's responsibility. Add `--check` to the replay command for isolated verification without changing the supplied workspace. A direct `git am --keep-non-patch` over `series` is equivalent, but the shared verifier additionally checks provenance trees and metadata. Use `export-patch-series.py` into a new directory for future maintained exports.

## Consensus and compatibility

The series preserves historical difficulty algorithms and transitions, subsidy, height-dependent maturity, legacy Script/signature behavior, Scrypt, AuxPoW commitments and variable serialization, chain IDs, activation rules and Dogecoin network parameters. It adapts the old global PoW queue to modern node-owned initialization/shutdown. The complete current mining fixture scenarios execute with real easy Scrypt headers; the historical reference skip is not retained.

Review identified additional defects in the inherited/adapted code and repaired them explicitly:

- Disabled BCH/eCash activation fields must not narrow into immediate activation. Foreign mainnet/testnet assumeutxo snapshots are removed; deterministic Dogecoin regtest snapshot coverage is retained.
- AuxPoW activates at mainnet 371337, testnet 158100 and regtest 20; early proofs and post-activation legacy headers are rejected. Modern ordinary Scrypt blocks remain valid.
- Legacy numeric Script operands use four bytes, with five-byte CLTV/CSV exceptions; legacy DER handling and signature-cache modes stay separate from Schnorr. The eCash P2SH recovery shortcut cannot bypass Dogecoin redeem-script evaluation.
- Dogecoin's fixed 1 MB consensus limit applies even if local excessive-block policy is raised. Mining also respects that cap.
- Without CTOR, transaction inputs become available in block order, preserving dependency validation and UTXO undo. A hidden regtest-only activation override exercises these rules without changing inherited regtest fixture defaults; mainnet/testnet are unaffected.
- Optional finalized mining preserves its selected transaction set but orders parents before children when CTOR is disabled; radix/transaction-ID ordering alone would produce invalid Dogecoin templates. Regression explicitly forces a child ID lower than its parent and checks selection, dependency order and determinism.
- Restarted mainnet header presync reconstructs only the stored 80-byte base fields from an AuxPoW header index when its full block is not on disk. It retains the actual AuxPoW proof requirement for validation, wire serialization, and full-header RPC.
- Header presync checks the same candidate-height DigiShield rule as full validation, including the first mainnet transition at 145000.
- Aggregate block fees may exceed the per-transaction 10-billion-DOGE limit. Accumulation/reward comparison uses saturation beyond signed int64; because a valid coinbase itself is bounded far below int64 maximum, this preserves the mathematical reward comparison. Optional fee-accounting output saturates beyond about 92.23 billion DOGE. Official Core uses unchecked signed addition at that edge, so equivalence to its undefined overflow behavior is **not claimed**.

Chronik retains HTTP/WebSocket/Electrum and modern upstream lifecycle behavior. Its bridge exports actual AuxPoW-bearing headers and calculates transaction disk offsets from their serialized lengths. Signed transaction versions, historical database migrations, native explorer addresses, decimal amounts and existing protobuf meanings are preserved. Synthetic migration regression covers the repaired v10-to-current transition; migration of every real legacy database has not been demonstrated.

## Features and mining

| Capability | Selection / boundary |
| --- | --- |
| Chronik | Independent `BUILD_CHRONIK=ON/OFF`, runtime `-chronik=1`. |
| Avalanche | Retained, default disabled; runtime `-avalanche=0` does not block PoW or Chronik. No compile-time removal switch is claimed. Score overflow repair stays distinct from PoW consensus. |
| RTT / optional coordination | Retained and default off. Inherited RTT uses block-ID/600-second-derived behavior; no operational Dogecoin policy or live quorum claim. |
| ZeroMQ | Retained; independently selectable with upstream `BUILD_ZMQ`. |
| NNG | Absent in the original Doged and this candidate. No substitute wire protocol was introduced. This requested optional capability remains unimplemented. |
| Mining RPC | Existing `getblocktemplate`, `submitblock`, `submitheader` and generation APIs retained; new `getrawunsolvedblock(address)` returns `{blockhex,target}`. |
| Merged-mining work RPC | Original and current Doged lack `getauxblock`, `createauxblock`, `submitauxblock`. Valid externally constructed AuxPoW blocks can be submitted; that does not provide a merged-mining coordinator. |

Use an isolated datadir and explicit ports for review. Mainnet defaults are RPC 22555, P2P 22556 and Chronik 22554. Wallet/config branding uses `dogecoin.conf` and the inherited `.doge` datadir. The miner's [Dogecoin instructions](../../../miner/README.md#dogecoin-direct-scrypt-mining) describe explicit chain selection, RPC URL and credentials. The new OpenCL Scrypt backend preserves Lotus behavior and CPU-verifies GPU candidates. It mined an accepted regtest block on Apple M5 Max, including post-AuxPoW-activation direct mining. No Stratum pool client, parent-chain merged-mining work construction, live financial mining or profitability claim is included.

## Evidence and remaining validation

Exact build, native/functional test and mainnet evidence is recorded separately in [validation evidence](../../docs/evidence/doged-current-abc-validation-20261014.json), [replay/build/Rust evidence](../../docs/evidence/doged-current-abc-maintenance-20261014.json), and the [validation report](../../docs/doged-current-abc-validation.md) and [restart follow-up](../../docs/doged-current-abc-fullsync-followup.md). Successful replay alone establishes no runtime property.

The real network tests use fresh isolated data. At 2026-10-15 03:05 UTC, the default-minimum-work run had accepted **37,993 blocks** while presyncing headers; it remains in IBD. A separate, explicitly test-only `-minimumchainwork=0 -assumevalid=0` run reached its planned stop at block **371,340**, accepting real blocks through DigiShield activation at 145,000 and AuxPoW activation at 371,337–371,339. Offline `verifychain 4 1000` passes across the AuxPoW boundary. At heights 371,336–371,340, Chronik raw headers match RPC byte-for-byte (80-byte direct headers beside 535/535/495-byte AuxPoW headers), and Chronik raw coinbase bytes match RPC/disk bytes. A whole-datadir `verifychain 4 0` is still running with 16 GiB database cache; the earlier 1 GiB attempt skipped level 3–4 checks. These historical blocks demonstrate real activation-boundary acceptance; neither run is a full-tip sync. Exact snapshots and limitations are in the [sync follow-up](../../docs/doged-current-abc-fullsync-followup.md) and [AuxPoW evidence](../../docs/evidence/doged-current-abc-auxpow-boundary-20261015.json).

Not all inherited extended functional, GUI, SDK or deployed explorer integration suites have been executed. Inherited Electrum `blockchain.address.*` aliases still parse CashAddress; native Dogecoin consumers should use the standard `blockchain.scripthash.*` methods. Full-header RPC for headers-only AuxPoW entries still needs a full proof source and returns an error before the block body arrives; active indexed blocks retain full-header RPC. GUI/platform packaging and deployment, every existing database migration, live Avalanche operation, full-tip synchronization, NNG and merged-mining work service remain explicit gaps. Historical logos, landing-page styles and documentation cleanup are not all reapplied; exact dispositions are retained in the inventory.

## Provenance

[manifest.json](manifest.json) records patch hashes, all intermediate trees, author/date/message digests, original metadata, source integration commits and export identities. [metadata-map.json](metadata-map.json) records tree-identical maintenance of line endings and added rationale. Original meaningful messages, authors and author dates are retained; added explanations are clearly labelled, and CRLF/terminal blank lines are normalized for stable mailbox replay.

[lineage-review.json](lineage-review.json) retains all **414 unmatched original commits**, including 273 same-subject upstream counterparts requiring delta review. It records complete original messages/authorship/dates and explicit dispositions; 107 original commits have corroborated mappings to 103 exported patches. Remaining patches are current-API integration, independent repairs and regressions. This is not a claim that all 414 should be replayed wholesale. The inventory's integration snapshot predates the final independent repair tail; the manifest and metadata map identify the exact final chain.
