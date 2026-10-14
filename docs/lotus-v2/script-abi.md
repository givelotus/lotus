# Script and wallet ABI

Status: review draft, derived from [consensus C04–C25](consensus.md). P01 and P03 now specify candidate signing bytes and opcode semantics; their independent conformance evidence is still pending. This is not a compiler release or a promise of CashScript bytecode compatibility.

## Invocation boundary

| Item | Proposed contract |
| --- | --- |
| Script selection | Spending input selects one committed path; witnesses correspond exactly to its branch indices |
| Method selection | Revealed script plus unordered membership proof selects a leaf; no numeric method index in consensus |
| Arguments | Count followed by length-prefixed byte strings; wire order is bottom-to-top, last argument on top |
| Initial machine | Fresh main stack, empty alternate stack, no shared mutable branch state. In a mint, the node pushes the mint delta above the arguments |
| Numeric operand | Exactly 16 bytes, signed two's complement, little-endian; no implicit Bitcoin ScriptNum conversion |
| Boolean | Exactly int128 zero or one; Boolean consumers reject other values in this draft |
| Bytes | Remain bytes until an explicit opcode interprets them; hashes, keys and signatures are not int128 values |
| Success | Ordinary execution: exactly one Boolean true on main stack, empty alternate stack. An unassigned OP_SUCCESS_N instead succeeds for the whole invocation during P03's scan, after outer witness/proof checks |
| Failure | Invalid encoding/type/range/index, overflow, division by zero, unmatched structure, resource excess, or false result rejects under ordinary execution; P03 defines the success-scan exception |
| State | Not a separate output field. Data or Merkle roots are stored in `branches` in three ways (P02): (1) a data leaf inside the executing branch tree (`BranchNode(DataLeaf, M)`) enforced with `OUTPUTCONTINUESBRANCH` (`0xcf`) or `OUTPUTEXCLUSIVEBRANCH` (`0xcb`), (2) a dedicated unexecuted data branch on a spendable coin (`branches=[CodeRoot, StateMerkleRoot]`, `paths=[[0]]`) read with `UTXOBRANCH`/`OUTPUTBRANCH`, or (3) a pruneable `IS_BURN` (`0x02`/`0x03`) output with `paths=[]` and up to 16 32-byte commitment words/roots. Internal sets and maps use `MERKLEROOT_SORTED` (`0xee`) and `MERKLEROOT_INDEXED` (`0xef`) |

[P03](decisions/vm-semantics.md) owns exact opcode bytes, stack effects, integer/limb conversions, shifts, LOG/SQRT algorithms, structured control flow, Merkle-root opcodes and crypto profiles. CHECKSIG is BIP340 over P01's exact transaction message; CHECKDATASIG has only selectors 0..3; unknown selectors error. Every otherwise unassigned opcode byte is a generic OP_SUCCESS_N, not an algorithm-specific fallback. Do not infer 33-byte keys for BIP340 or silently substitute a library's Ed25519 acceptance rules. Opcode/cost conformance remains unproven until independent vectors pass.

## Introspection and context

P03 defines field and complete-output/path reads, active invocation kind, branch-continuation (`OUTPUTCONTINUESBRANCH` `0xcf`) and spend-only operations; a mint's delta arrives as a node-pushed stack item above the arguments, and its token ID is read with BRANCHROOT. Every coin a script reads is one the transaction spends (`C13`). Out-of-range or undefined-context reads reject. No operation reads block height, block time, block hashes, or the global UTXO root (`OP_BLOCKHEIGHT`, `OP_BLOCKTIME`, `OP_BLOCKHASH` and `OP_UTXOPROOFVERIFY` are rejected; see [rationale](rationale.md#rejected-opcodes-and-consensus-features-and-how-to-build-those-contracts-instead) for why they are excluded and how limit orders, Dutch auctions, linear vesting, expiring offers and in-contract Merkle collections are built instead), so a script's result does not change as blocks arrive (`C22a`). `SIGHASH` (`0xec`) takes a signing mode (`0`, `1` or `2`; mode `2` errors if `INPUTINDEX >= TXOUTPUTCOUNT`) and exposes that mode's invocation digest in $O(1)$ time for application signature policies. Other invocations' successful execution and `TxHash` remain unavailable; the proposed field accessors do not establish the old Master/Companion optimization.

## Signing and addresses

The signing API returns the exact digest and a decoded display of the committed intent: chain, inputs and resolved assets (`InputsRoot` and `CoinsRoot`), paths, outputs (`OutputsRoot`), native fee, positive mint deltas and invocation (`input_index`, `branch_index`, and `Leaf(script)` in a spend). In partial modes `01` and `02`, the preimage commits to the 32-byte per-input digest `OwnInputHash(i)` and either `OutputsRoot` or `OutputLeaf(i)` so every signature check hashes at most 3 BLAKE3 blocks in $O(1)$ time. Hardware wallets must refuse unsupported context, not silently sign a hash they display as an ordinary native payment. [P01](decisions/encoding-and-signatures.md) now defines the preimage bytes; signing fixtures become executable only when generated and independently checked against that proposal.

An address identifies a network and a construction template or a complete output policy. A branch root alone does not identify a multi-branch path policy. Address encoding/checksum, script template, parameter widths and policy reconstruction must be specified together. Roots change when policies change. The `xpi` prefix is a historical proposal, not a complete address standard. Direction from the maintainer (2026-10-09): a cashaddr-style encoding whose checksum covers the prefix, with no `:` separator because it breaks copy and paste; wallets accept an address with the prefix omitted and recover it by trying the known prefixes against the checksum. The payload must distinguish a single-branch, single-path policy (one 32-byte root) from a full serialized branch-and-path policy.

Native XPI uses a 6-decimal-place base unit (**`1 XPI = 10^6 atoms`**; [P06](decisions/issuance-and-time.md)). Standard wallet UIs and signing displays format native amounts to **2 decimal places (`1.00 XPI`, like dollars and cents)** and hide the lower 4 sub-cent decimal places (`0.00_0000`) by default (exposing full 6-decimal atom precision on hover/detail inspection or hardware-wallet exact-atom screens). Ordinary transaction fees ($\sim 200\text{--}2{,}000\text{ atoms} = 0.0002\text{--}0.0020\text{ XPI}$) therefore sit entirely inside the hidden sub-cent precision as invisible rounding dust to everyday users while preserving $10{,}000$ integer ticks per `0.01 XPI` for [P05](decisions/resources-and-parameters.md)'s parabolic fee-burn accounting and micro-stamps.

Application state is committed in a data leaf with a documented, versioned layout with explicit lengths and units. A covenant must verify successor asset identity, value constraints, state and authorization paths (`OUTPUTCONTINUESBRANCH` or `OUTPUTEXCLUSIVEBRANCH`). A balance equality check alone does not preserve a vault's restrictions.

## Language boundary

The small language in [examples](examples/README.md) is explanatory pseudocode with explicit transaction and invocation access. Its assembly uses symbolic opcode names. A subsequent reference assembler must emit exact bytes, source maps and a static-cost report, then execute those bytes in the scalar evaluator. Freeze consensus opcode semantics; permit compiler syntax and optimizations to evolve while preserving those semantics.

Each generated artifact records compiler/evaluator revisions, consensus/parameter digests, argument order, selected policy, leaf/proof bytes, core/complete transaction bytes, TxID/TxHash, signature digest, final stack, resulting state and static charges. A pretty source listing is not a conformance vector.
