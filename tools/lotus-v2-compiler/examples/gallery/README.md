# Offline contract gallery

This gallery turns seven small source programs into compiler artifacts with exact
script bytes, method leaves, membership proofs, policy roots, ABI arguments,
source maps and static resource reports. The programs use the typed compiler
grammar in this package. All template values are deterministic public examples.

```sh
cd tools/lotus-v2-compiler
npm ci
npm run build
node examples/gallery/run-gallery.mjs /tmp/lotus-v2-gallery
npm test
```

If the separate reference VM candidate is available, pass its package
directory as a second argument to execute the hashlock and inlined helper with
correct and incorrect preimages, plus the linked commitment method:

```sh
node examples/gallery/run-gallery.mjs /tmp/lotus-v2-gallery \
  /tmp/lotus-v2-vm-reference/tools/lotus-v2-reference
```

Install that VM package's `requirements-vm.txt` first and set
`LOTUS_V2_PYTHON` to its Python interpreter if needed. The run supplies an
illustrative explicit opcode cost schedule; those charges are not selected P05
consensus values.

The command writes one artifact per example and a machine-readable
`summary.json`. It independently hashes each emitted script and folds each
method proof to the advertised root. A changed template public key changes the
Payment root; changing the referenced `LinkedTarget` changes the
`LinkedVerifier` root. The helper example must emit the same bytes as the
direct Hashlock example, showing that the helper is copied into its caller.

| Source | What it demonstrates |
| --- | --- |
| `payment.lotus` | One owner signature and the compiler's generic argument handling. |
| `two-key.lotus` | Two required signatures in one method. |
| `hashlock.lotus` | A 32-byte preimage compared with a bound SHA256 digest. |
| `signed-hashlock.lotus` | Signature and preimage requirements together. |
| `recovery.lotus` | Two independently committed owner and guardian methods, each with its own leaf and proof. The guardian method has no delay. |
| `helper.lotus` | A typed free helper whose operations are inlined into a method. |
| `linked.lotus` | A fully bound contract root and method leaf copied as compile-time constants into a second contract. |

`summary.json` reports compile, proof, transaction framing, signature, VM,
accounting and block stages separately. The generic Payment method has different
script bytes from the package's earlier signed schema-1 fixture. These compiler
artifacts are not signed transactions. The current compiler/runtime does not
implement a stateful counter, mint policy, relative recovery delay, full coin
context, fee accounting or block connection. Those examples remain in the
semantic specification at `docs/lotus-v2/examples/README.md`. No node,
network, wallet or private key is needed to run this gallery.

The source syntax and artifact are candidate tooling, not a deployed contract
language or mainnet consensus result. The checked-in tests also reject missing
template bindings and cyclic `contract_root` dependencies.
