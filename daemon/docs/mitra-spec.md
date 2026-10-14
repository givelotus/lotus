# Mitra Transaction Format Specification

**Source:** givelotus/givelotus.github.io, branch `mitra-specification`
**Reference implementation:** https://github.com/LogosFoundation/lotusd/tree/mitra

---

## Overview

Mitra is a new transaction format designed to solve four problems with current Bitcoin-family
transactions:

1. Verifying transactions requires fetching UTXOs from database first (bottleneck)
2. Transactions are malleable
3. SLP tokens have limited use for smart contracts
4. SLP tokens are not scalable

The solution introduces:
- **Preambles** — scripts expressing additional constraints on the entire transaction
- **Outputs in inputs** — each input carries the complete output it is spending, enabling
  isolated signature validation without database lookup
- **Carryover field** — arbitrary data attached to each output, must be specified identically
  when the output is spent (simplifies inductive proofs)
- **Loop opcodes** — `OP_LOOP` / `OP_ENDLOOP` for do-while loops with pre-computed counts
- **Introspection opcodes** — 13 new opcodes for accessing transaction data from scripts
- **New txid** — prevents external malleation
- **New sighash** — updated format including the new fields

---

## Transaction Format

### CTransaction

| Field | Type | Description |
|---|---|---|
| `nVersion` | `int32_t` | Transaction version |
| `preambles` | `CTxPreamble[]` | Preamble scripts for inductive proofs |
| `vin` | `CTxIn[]` | Inputs spent |
| `vout` | `CTxOut[]` | Outputs created |
| `nLockTime` | `uint32_t` | Lock time threshold |

### CTxPreamble

| Field | Type | Description |
|---|---|---|
| `predicateScript` | `uint8_t[]` | Script with additional transaction predicates |
| `witnesses` | `uint8_t[][]` | Script inputs to the preamble |
| `loopCounts` | `uint8_t[]` | Pre-computed loop iteration counts |

### CTxIn

| Field | Type | Description |
|---|---|---|
| `prevout` | `COutPoint` | Txid and output index being spent |
| `nSequence` | `uint32_t` | Sequence number for relative time locks |
| `output` | `CTxOut` | Complete output being spent (enables isolated validation) |
| `hasPreambleMerkleRoot` | `uint8_t` | Flag (1 or 0) |
| `preambleMerkleRoot` | `uint256?` | Optional merkle root of preamble scripts from spending tx |
| `witnesses` | `uint8_t[][]` | Unlocking witnesses for scriptPubKey |
| `loopCounts` | `uint8_t[]` | Pre-computed loop counters |

### CTxOut

| Field | Type | Description |
|---|---|---|
| `value` | `uint64_t` | Output value in satoshis |
| `scriptPubKey` | `uint8_t[]` | Locking script |
| `carryover` | `uint8_t[]` | Data carried to the spending input verbatim |

---

## Loop Opcodes

`OP_LOOP` and `OP_ENDLOOP` implement do-while loops using a separate loop stack:

- **`OP_LOOP`**: Pushes the current program counter onto the loop stack.
- **`OP_ENDLOOP`**: Pops the top of the loop stack. If the main stack top is `1`, jumps back
  to the saved program counter (loop continues). If `0`, falls through (loop exits).

Loop counts must be pre-computed by the transaction creator and stored in `loopCounts`.
This allows fee metering without executing the script.

---

## Introspection Opcodes (13 total)

| Opcode | Code | Stack effect |
|---|---|---|
| `OP_THISINDEX` | `0xbf` | Push index of current input or preamble |
| `OP_NUMPREAMBLES` | `0xc0` | Push number of preambles |
| `OP_NUMINPUTS` | `0xc1` | Push number of inputs |
| `OP_NUMOUTPUTS` | `0xc2` | Push number of outputs |
| `OP_PICKPREAMBLEHASH` | `0xc3` | Push hash of preamble script at given index |
| `OP_PICKINPUTOUTPOINT` | `0xc4` | Push input outpoint (txid+vout) at given index |
| `OP_PICKINPUTVALUE` | `0xc5` | Push input value at given index |
| `OP_PICKINPUTSCRIPTPUBKEY` | `0xc6` | Push input scriptPubKey at given index |
| `OP_PICKINPUTCARRYOVER` | `0xc7` | Push input carryover at given index |
| `OP_PICKINPUTPREAMBLEMERKLEROOT` | `0xc8` | Push input preamble merkle root at given index |
| `OP_PICKOUTPUTVALUE` | `0xc9` | Push output value at given index |
| `OP_PICKOUTPUTSCRIPTPUBKEY` | `0xca` | Push output scriptPubKey at given index |
| `OP_PICKOUTPUTCARRYOVER` | `0xcb` | Push output carryover at given index |

Note: opcode codes `0xbf–0xcb` — verify no collision with existing Lotus opcodes (v2 series
currently uses `0xbd` = OP_LOG, `0xbe` = OP_SQRT, `0xbf–0xc4` = BIGINT ops). These ranges
**conflict** and must be resolved before implementation. See `patches/v2/25-26-op-log-op-sqrt.patch`
and `patches/v2/28-bigint-ops.patch`.

---

## Native Tokens (Inductive Token Example)

Mitra enables native tokens via inductive preamble proofs:

1. **Genesis UTXO**: Hard-code the genesis outpoint in the preamble script.
2. **Token amount in carryover**: Each output's `carryover` field stores the token amount.
3. **Transfer validation**: A preamble script uses `OP_LOOP` + `OP_PICKINPUTCARRYOVER` /
   `OP_PICKINPUTPREAMBLEMERKLEROOT` + `OP_PICKOUTPUTCARRYOVER` to sum token amounts across
   inputs (those with matching preamble merkle roots) and verify sum(inputs) >= sum(outputs).
4. **Burn allowed**: Input sum can exceed output sum (tokens are burned).

This enables tokens that are:
- Validated entirely in-script (no external indexer needed for consensus)
- Scalable (O(n) validation per transaction, not O(n²))
- Interoperable with smart contracts via the same introspection opcodes

---

## Opcode Conflict Resolution (TODO)

Before implementing Mitra introspection opcodes, resolve conflicts with existing v2 opcodes:

| Range | Current Use (v2) | Mitra Use |
|---|---|---|
| `0xbd` | OP_LOG | — |
| `0xbe` | OP_SQRT | — |
| `0xbf` | BIGADD | OP_THISINDEX |
| `0xc0` | BIGSUB | OP_NUMPREAMBLES |
| `0xc1` | BIGMUL | OP_NUMINPUTS |
| `0xc2` | BIGMOD | OP_NUMOUTPUTS |
| `0xc3` | BIGDIVMOD | OP_PICKPREAMBLEHASH |
| `0xc4` | BIGMULMOD | OP_PICKINPUTOUTPOINT |
| `0xc5–0xcb` | (free) | OP_PICKINPUT* / OP_PICKOUTPUT* |

Resolution options:
- Renumber BIGINT ops to higher range (e.g., `0xd0–0xd5`)
- Renumber Mitra introspection ops
- Retire BIGINT ops if Mitra's carryover field makes them redundant

---

## Implementation Plan (v2 series)

Target patch: `patches/v2/32-mitra-tx.patch`

Files to modify:
- `src/primitives/transaction.h` — add `preambles`, `CTxPreamble`, `carryover` to `CTxOut`,
  `output` + `hasPreambleMerkleRoot` + `preambleMerkleRoot` + `loopCounts` to `CTxIn`
- `src/primitives/transaction.cpp` — serialization/deserialization
- `src/script/interpreter.h/.cpp` — OP_LOOP, OP_ENDLOOP, 13 introspection opcodes
- `src/script/script.h` — opcode enum additions
- `src/consensus/tx_verify.cpp` — preamble validation
- Tests: `src/test/script_tests.cpp`, `src/test/transaction_tests.cpp`

---

## See Also

- `patches/v2/32-mitra-tx.patch` — implementation skeleton (not yet implemented)
- `patches/v2/28-bigint-ops.patch` — BIGINT opcodes (opcode conflict to resolve)
- `patches/v2/25-26-op-log-op-sqrt.patch` — OP_LOG/OP_SQRT (opcode conflict to resolve)
