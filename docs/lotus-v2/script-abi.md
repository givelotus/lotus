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
| Success | Exactly one Boolean true on main stack, empty alternate stack |
| Failure | Invalid encoding/type/range/index, overflow, division by zero, unmatched structure, resource excess, or false result rejects |
| State | Optional application-owned bytes; a program validates schema/version before interpreting them |

[P03](decisions/vm-semantics.md) owns exact opcode bytes, stack effects, integer/limb conversions, shifts, LOG/SQRT algorithms, structured control flow and crypto profiles. CHECKSIG is BIP340 over P01's exact transaction message; CHECKDATASIG has explicit candidate algorithm selectors. Do not infer 33-byte keys for BIP340 or silently substitute a library's Ed25519 acceptance rules. Opcode/cost conformance remains unproven until independent vectors pass.

## Introspection and context

P03 defines field and complete-output/path reads, active invocation kind and spend-only operations; a mint's delta arrives as a node-pushed stack item above the arguments, and its token ID is read with BRANCHROOT. References expose recorded coin fields while accounting excludes their values. Out-of-range or undefined-context reads reject. Candidate height and parent median time support expiration checks; context changes require mempool/cache revalidation. SIGHASH takes a signing mode and exposes that mode's invocation digest for application signature policies. Other invocations' successful execution and TxHash remain unavailable; the proposed field accessors do not establish the old Master/Companion optimization.

## Signing and addresses

The signing API returns the exact digest and a decoded display of the committed intent: chain, inputs and resolved assets, paths, outputs, native fee, positive mint deltas and invocation. Hardware wallets must refuse unsupported context, not silently sign a hash they display as an ordinary native payment. [P01](decisions/encoding-and-signatures.md) now defines the preimage bytes; signing fixtures become executable only when generated and independently checked against that proposal.

An address identifies a network and a construction template or a complete output policy. A branch root alone does not identify a multi-branch path policy. Address encoding/checksum, script template, parameter widths and policy reconstruction must be specified together. Roots change when policies change. The `xpi` prefix is a historical proposal, not a complete address standard. Direction from the maintainer (2026-10-09): a cashaddr-style encoding whose checksum covers the prefix, with no `:` separator because it breaks copy and paste; wallets accept an address with the prefix omitted and recover it by trying the known prefixes against the checksum. The payload must distinguish a single-branch, single-path policy (one 32-byte root) from a full serialized branch-and-path policy.

Application state uses a documented versioned schema with explicit lengths and units. A covenant must verify successor asset identity, value constraints, state and authorization paths. A balance equality check alone does not preserve a vault's restrictions.

## Language boundary

The small language in [examples](examples/README.md) is explanatory pseudocode with explicit transaction and invocation access. Its assembly uses symbolic opcode names. A subsequent reference assembler must emit exact bytes, source maps and a static-cost report, then execute those bytes in the scalar evaluator. Freeze consensus opcode semantics; permit compiler syntax and optimizations to evolve while preserving those semantics.

Each generated artifact records compiler/evaluator revisions, consensus/parameter digests, argument order, selected policy, leaf/proof bytes, core/complete transaction bytes, TxID/TxHash, signature digest, final stack, resulting state and static charges. A pretty source listing is not a conformance vector.
