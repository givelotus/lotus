# Separate development candidate for default Avalanche bootstrap

Status: proposed disposable development fixture, 2026-10-15. The user authorized a separate development profile. This candidate changes neither the existing local-test fixture nor production constants. Root integration, native validation and explicit adoption remain required. No nodes were launched for this packet.

The current easy-work fixture pays a tail of 1,000,000 base units and bootstrap `max(1, reserve >> 20)`, initially about 1,000,000 more. Its initial reserve is 1,048,576,000,000. At constant work 2, integer gross issuance first reaches 1,000,000,000,000 at height 563,863; remaining reserve is 612,437,423,083. This excludes burns and consolidation fees. Those coinbases all reach 2,016 confirmations by tip 565,878, approximately 785.94 days at 120-second spacing. Gross issuance after 2,016 blocks is only 4,030,063,206. This calculation describes work 2; harder targets can increase the anchored tail, so it is not a universal lower bound.

## Exact candidate

Name: `lotus-v2-quorum-development-20261015-v1`. Start from the schema-2 local-test manifest whose SHA256 is `0ccb2872198a354e9cdc5e9c91d1816cf65bf8109efc200d86537d65dc660d05`. Change only the network identity/genesis and these monetary inputs:

| Input | Candidate |
| --- | --- |
| Initial bootstrap reserve | `2^43 = 8,796,093,022,208` base units |
| Bootstrap shift | `3` |
| Absolute tail anchors | unchanged: `1,000,000 / work 2` |
| Tail bounds | unchanged: `1,000,000` through `1,000,000,000` |
| Initial EMA | unchanged: `65,536` |
| PoW limit / genesis work | unchanged easy target `0x207fffff` / `2` |
| ASERT half life / spacing | unchanged `172,800 / 120` seconds |
| Coinbase spend maturity | unchanged `2`; distinct from proof maturity |

All values pass the existing reference profile/state width checks. Bootstrap remains the existing reserve schedule, and tail remains the existing absolute genesis-anchored formula. Genesis contains only its zero-valued burn coinbase and issues nothing. No genesis funding exemption or consensus rule is added.

Retain actual upstream proof defaults: stake dust `10,000,000,000`, quorum stake `1,000,000,000,000`, 2,016 stake confirmations, eight connected neighbors and eight proof-inventory neighbors. The adapter maps one V2 base unit to one ABC satoshi. Inherited amount/score limits still apply; this proposal's funded stake is far below the inherited per-proof `MAX_MONEY = 2,100,000,000,000,000`. Preserve the connected-stake ratio and other proof defaults too. Public proof payout metadata does not choose a V2 coinbase destination.

## Reproducible participant sequence

Use fresh node homes and participant-generated keys. Fully connect nine nodes, possibly distributed among a few operators. Mine blocks 1–9 with one coinbase assigned to each node's registered single-key Payment output (`PUSH32 x-only-key; 0xbc; 0x4e`). Do not use the scalar-1 public test key employed internally by the generator's first-child validation.

For the candidate's normal 242-byte one-output coinbase, reference accounting computes block cost 46,362 and required deduction 242. The nine resulting funding amounts are:

```
1099512627534 962073674062 841814589774
736587891022 644514529614 563950338382
493456671054 431774712142 377802998094
```

Every funding output exceeds stake dust. Any eight total at least 5,051,975,404,144, exceeding quorum. Keep these outputs unspent. Mine to tip 2,024, at which point the ninth output has `2024 - 9 + 1 = 2016` confirmations. It remains immature at tip 2,023. Each operator builds and signs proofs using its own keys, and peers individually revalidate proofs against current coins. Start Avalanche polling only after funding maturity and the required connections/inventory exchange. Nine nodes controlled by a few people demonstrate behavior; they do not demonstrate independent economic control or attack resistance.

A larger/slower reserve is unnecessary: with shift 3 this reserve is depleted by the maturation tip, while the normal positive tail continues. No participant should infer a production issuance recommendation from these disposable values.

## Fast timestamps and actual ASERT checks

A deterministic offline schedule selects each child time as authenticated parent MTP plus one second, derives required compact bits from the actual parent using the reference ASERT implementation, and mines/checks every header's PoW through height 2,024. It reaches genesis plus 340 seconds, with maximum per-block work 5. Thus the inherited difficulty rule does not require a 2.8-day wall-clock wait for this maturity exercise. This uses consensus's MTP rule; it does not substitute a 1-second target spacing or disable ASERT.

The external clock gate remains intact: start at or after the fixed genesis UTC time `1792022400` (2026-10-15T00:00:00Z), and keep proposed times within real UTC plus the manifest's 7,200-second future window. The entire minimal schedule fits that window even if started exactly at genesis. Later sessions may use `max(real UTC, MTP+1)` and must derive ASERT from the actual accepted parent; they cannot reuse the offline schedule's bits blindly. Host runtime throughput, current native target agreement and a complete 2,024-block run are separate validation gates.

## Offline generation and evidence

The generator validates complete genesis framing, roots, zero issuance, PoW and initial anchor/work equality using reference modules. It connects and disconnects a full first spendable child, then checks 2,024 actual ASERT/PoW/MTP headers and independent monetary transitions. Later headers are a schedule feasibility exercise with synthetic roots, **not complete accepted blocks**. The script opens no sockets, runs no node processes and persists no private keys. It produces a manifest/report only upon an explicit invocation into a new directory:

```sh
/private/tmp/lotus-v2-compiler-review-venv/bin/python \
  tools/lotus-v2-devnet/fixtures/quorum-dev/generate.py \
  --output /private/tmp/lotus-v2-quorum-development-candidate
/private/tmp/lotus-v2-compiler-review-venv/bin/python -m unittest discover \
  -s tools/lotus-v2-devnet/fixtures/quorum-dev -p 'test_*.py'
```

Use any Python environment containing the reference package's dependencies (`blake3`). The generator imports the existing reviewed native profile-digest encoder and preserves manifest schema 2/formula version 1. Expected deterministic identities:

| Artifact | Identifier |
| --- | --- |
| ChainID | `8d868cc48a44d3886937d399bb6c14c8e3e6b201b4c58e8902c0f3b3207dac32` |
| Genesis BlockID | `02ae823d09a4aad1b385625f4d26fc557c4219e2b65216f9154859c83dae9f53` |
| Native validation profile digest | `40bfdb2b538035f66d0d5ed552dfc831b2b25e0eac3e0db38dd2e357c5d9173a` |
| Manifest SHA256 | `ff076ce72db2055f2d115082c29039ae89a6214f79215b18aa0e9bc58a3a171d` |

Changing the proposed parameters requires a new versioned name, regenerated ChainID/genesis/state/profile digest and fresh datadirs. Do not transplant this manifest into an existing home or change `prepare-local.py`'s current fixture selection. Native loader/digest parity, nine participant funding, proof maturity rejection/acceptance, default quorum establishment and persistence/restart remain root verification gates before adoption.
