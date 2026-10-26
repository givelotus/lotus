# [specification] Close the v2 ordinary-payment reference slice

Status: unpublished proposal, CANDIDATE_SPECIFICATION_AVAILABLE; maintainer acceptance and independent evidence pending. Tier 3: durable consensus encodings. Decision owner: project maintainer; independent reviewer/evaluator implementer unassigned.

## Outcome

A reviewer can independently turn one signed payment into exact wire bytes, a block commitment and a reversible state transition. The [consensus draft](../../lotus-v2/consensus.md) and [ABI](../../lotus-v2/script-abi.md) now link six concrete decision packets covering opcode, signing and block/tree algorithms. Mainnet parameters and monetary/time-eligibility decisions remain open. [I02](../implementation-entry.md) scopes a parameterized reference tool that can start against those candidates without claiming production block validation.

## Bounded specification contract

Review D01–D04 and the payment subset of D07/D08/D12–D14. Fix each byte order, length/count, domain tag, script/key/signature encoding, sighash preimage, coinbase identity, block-context rule and required limit for the reference test chain. Label test-chain-only constants; they do not close mainnet genesis choices. No monetary or token-identity decision may be silently adopted to make the example compile.

Deliver a canonical parameter artifact, byte grammar, signature preimage walkthrough, complete opcode subset and vector schema with stable requirement IDs. The prepared I02 contract describes V2-01 as a separate implementation unit producing the scalar parser/evaluator and actual generated example. No optimization, network daemon or compiler framework is required for that first unit.

## Acceptance and proof

All ordinary-payment inputs/results are computable without unspecified code defaults. An independent reviewer checks the preimage and commitments. The evaluator later produces exact source/assembly/bytecode/arguments/transactions/state/undo and bounded cost. Documentation-only pseudocode remains marked incomplete until that evidence exists.

No legacy v1 validity changes, native-token implementation, Master/Companion shortcuts, faucet mechanism or full compiler in this slice. Any schema change before genesis regenerates dependent fixtures; keep rejected alternatives and artifact revisions in the decision record.
