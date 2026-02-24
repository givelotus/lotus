# patches/archive/ — Proto-v1 Era Patches

These are flat, unnumbered patches from the earliest Lotus development phase, predating the
numbered `patches/v1/` series. They represent the first attempt at Lotus mainnet changes
applied on top of Bitcoin ABC / eCash ancestry.

## Provenance

These patches were written before the formal numbered-series scheme was established. They
overlap significantly with the current `patches/v1/` series but are **not** applied by any
build target — they exist for historical reference and extraction of specific algorithms or
logic that may not yet have a clean home in the numbered series.

## Contents

| Patch | Topic |
|---|---|
| `activation.patch` | Consensus upgrade epoch activation logic |
| `addresses.patch` | Lotus address encoding (early XAddress draft) |
| `amount.patch` | XPI denomination and amount formatting |
| `block.patch` | Block structure modifications |
| `chainparams.patch` | Chain parameters (genesis block, ports, magic bytes) |
| `consensus.patch` | Core consensus rule changes |
| `currencyunit.patch` | Currency unit / denomination |
| `iguana.patch` | IGUANA interleaved Merkle tree |
| `interpreter.patch` | Script interpreter changes (opcodes, sighash) |
| `intmath.patch` | Integer math helpers |
| `merkle.patch` | Merkle tree changes |
| `minerfund.patch` | IFP / miner fund (removed in v2) |
| `nng-interface.patch` | NNG pub/sub interface (replaces ZeroMQ) |
| `script-opcodes.patch` | New Lotus script opcodes |
| `transaction.patch` | Dual txid system: `id` (Lotus txid) vs `hash` (legacy) |
| `util-intmath-log2.patch` | Log2 fixed-point math (Turner algorithm) |
| `xaddress.patch` | XAddress encoding implementation |

## Relationship to Numbered Series

The current maintained Lotus mainnet series lives in `patches/v1/` (48 numbered patches,
`01-lotus-mainnet.patch` through `42-version-10.4.10.patch`). That series applies cleanly
against LotusiaStewardship/lotusd.

Notable patches in this archive that are not yet isolated in the numbered series:

- **`transaction.patch`** — the dual txid system (`GetId()` / `ComputeId()` alongside
  `GetHash()` / `ComputeHash()`). This is part of `01-lotus-mainnet.patch` but not yet
  extracted as a standalone numbered patch. See v1 TODO: `44-txid.patch`.

- **`chainparams.patch`** — the proto-v1 genesis block definition, superseded by
  the genesis block embedded in `01-lotus-mainnet.patch`. See v1 TODO: `43-genesis.patch`.

## mainnet/ Subdirectory

`patches/archive/mainnet/` contains patches specific to the Lotus mainnet network
parameters (block hashes, checkpoint values) for a specific network snapshot.

## See Also

- `patches/v1/` — current Lotus mainnet-compatible numbered series
- `patches/v2/` — new-chain series (eCash base + Lotus redesign)
