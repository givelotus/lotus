# Lotus V2 VM context and Merkle proof review packet

Review only; outside every active daemon patch series.

- Upstream/native base: `33563a7341b6393bf50246c25ab7acb18c31da5c` (tree `f3fd01ed1d52e21a48dd746e4c1a5a3bb9d2fb5f`).
- Source commit: `5b36ef23af2ca0ba09f423025651aed5f6eedb34`.
- Expected and independently replayed final tree: `c71e4259117cc4481168e369fafeca8d925dfb5e`.
- P01 SHA-256: `ccadd12af570de5014ac05e8e5db2a6a42a69e09a90120e9b31431104482faa7`.
- P03 prose SHA-256: `326a84e29544f486d37007c88eeefe868ffb797484199509a895fb672b1f3af4`.
- P03 opcode JSON SHA-256: `fb790b230e76befc90a1f183ea727cb3232d1f03e9b5838b10d025d96b9832da`.
- P05 prose SHA-256: `90eb7379660f37737a3a6c98d5a1938e120eb6be04d9076dd01d4b4e93ded2fb`.
- Validation: standalone native VM Debug and Release builds/tests, 684 independent Python/native Merkle vectors, 900 byte vectors, 2,117 integer vectors, 363 Python/native core cases, 494 Python/native P05 cases, and machine coverage of all 215 assigned opcodes. Six assigned opcodes remain intentionally unsupported and reject when executed: `b0`–`b4`, `bd`.

Merkle cost charges derive per-step prices from the explicit caller-supplied BLAKE3/SHA256/HASH256 opcode coefficients and conservative fixed input sizes. Unknown selectors take the maximum of all four derived prices. This is a draft implementation choice pending the genesis coefficient freeze; no mainnet defaults are supplied. Caller-provided field-size hints must be derived from authenticated transaction/coin data or omitted to retain the safe maximum-size fallback. The packet does not claim full consensus activation or transaction-wide VM validation.
