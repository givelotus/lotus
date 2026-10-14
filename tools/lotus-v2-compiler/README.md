# Lotus V2 TypeScript Payment compiler candidate

This package compiles only the example `Payment<owner: PublicKey>` contract with one `spend(signature: Signature)` method and `require(checksig(signature, owner));`. Identifiers, whitespace and comments may vary. Other statements, methods, types, opcodes and `OP_SUCCESS_N` are rejected. `owner` is a supplied 32-byte x-only public key, so compilation is deterministic and has no wallet, network, signing or RPC side effect.

The CLI emits a versioned JSON artifact with the P03 `PUSH_32 owner CHECKSIG` script, P02 one-leaf branch root and path, source byte spans, static stack report, and thin TypeScript and Python binding sources. The generated Python binding declares the runtime protocol; a production Python runtime is not yet implemented. Both bindings keep signing separate from call preparation. The maintained TypeScript runtime in this package implements only one native spending input, FULL-mode BIP340 signatures, one branch/path with zero siblings, and native spendable outputs. It requires explicit `chainId`, outpoint, sequence, resolved coin, outputs and profile. Amounts are `bigint`; bytes are `Uint8Array` internally. The fixture-only profile name prevents treating this as production network validation.

```sh
cd tools/lotus-v2-compiler
npm ci
npm test
node dist/cli.js examples/payment.lotus f9308a019258c31049344f85f89d5229b531c845836f99b08601f113bce036f9 /tmp/lotus-payment-abi
node examples/run-payment.mjs
```

`run-payment.mjs` signs with the public BIP340 test key 3 and zero auxiliary randomness. It prints actual transaction bytes and machine-readable stage results. Its signed wire, TxID, TxHash and signing digest match the independent Python reference candidate at `c0126889`; the same values appear in native C++ candidate `40a5479a` tests. These candidates are pending integration review. No VM invocation, contextual coin/lock check, block fee-floor check, connect or disconnect is claimed. The `stages` fields report these as `unavailable`.

The artifact schema is `lotus-v2/payment-artifact/1`; its target is `P01-P02-P03-candidate-2026-10-14`. JSON hashes and bytecode are lowercase hex; user-facing native amounts must be decimal atom strings and parsed to checked `bigint`. The runtime accepts no implicit network and rejects an artifact whose policy root does not match its script. Generated clients must pin this schema and supply a separately reviewed signer; they must not assume that a valid signature alone makes a transaction valid.

Current source mapping records UTF-16 offsets (JavaScript string offsets) and byte intervals in the emitted script. A future compiler profile should define UTF-8 source byte offsets for cross-language editor interoperability. This is a schema issue before broader language support.
