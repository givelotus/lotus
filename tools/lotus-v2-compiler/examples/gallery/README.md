# Offline contract gallery

This gallery turns small source programs into compiler artifacts with exact
script bytes, method leaves, membership proofs, policy roots, ABI arguments,
source maps and static resource reports. The programs use the typed compiler
grammar in this package. All template values are deterministic public examples.

```sh
cd tools/lotus-v2-compiler
npm ci
npm run build
python3.13 -m venv /tmp/lotus-v2-gallery-venv
/tmp/lotus-v2-gallery-venv/bin/python -m pip install -r ../lotus-v2-reference/requirements-vm.txt -r test/requirements-vm.txt
LOTUS_V2_PYTHON=/tmp/lotus-v2-gallery-venv/bin/python \
  node examples/gallery/run-gallery.mjs /tmp/lotus-v2-gallery
LOTUS_V2_PYTHON=/tmp/lotus-v2-gallery-venv/bin/python npm test
```

When the reference VM package is present at `tools/lotus-v2-reference`, the
same command also executes the signed Payment, hashlock and inlined helper with
positive and negative witnesses, plus the linked commitment method. For an isolated VM
checkout, pass its package directory as a second argument:

```sh
node examples/gallery/run-gallery.mjs /tmp/lotus-v2-gallery \
  "$VM_REFERENCE_PACKAGE"
```

Set `LOTUS_V2_SKIP_VM=1` to generate artifacts without Python dependencies.
The VM run supplies an illustrative explicit opcode cost schedule; those
charges are not selected P05 consensus values.

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
| `linked.lotus` | A fully bound contract root and method leaf copied as compile-time constants into a second contract. This shows byte commitments; it does not enforce execution of the referenced contract. |
| `fungible-token.lotus` | Separate wallet, mandatory transfer-rules and issuer-mint trees for a fungible token. |
| `token-upgrade.lotus` | Burn old tokens to mint a replacement asset; the compiler-to-VM test checks sufficient and insufficient burns, including guarded reads past a mint input. |

The fungible token gallery can also be generated on its own:

```sh
cd tools/lotus-v2-compiler
npm ci
npm run build
python3.13 -m venv .venv
.venv/bin/python -m pip install -r ../lotus-v2-reference/requirements-vm.txt -r test/requirements-vm.txt
node test/generate-fungible-token-fixture.mjs
LOTUS_V2_PYTHON=.venv/bin/python \
  node examples/gallery/run-fungible-token.mjs /tmp/lotus-v2-token-gallery
LOTUS_V2_PYTHON=.venv/bin/python npm test
```

The public-only fixture uses BIP340's published test scalar 3 in the local
generator. It contains three chained transactions: a two-input mint, a
two-input transfer, and a three-input merge that spends both transfer token
outputs (700 + 250 units) plus the native change output into one 950-unit token
output with no token burn. The runner rebuilds all three transactions, checks
wire bytes, TxID, TxHash, method proofs, Schnorr signatures and
candidate-profile fee/token arithmetic, then executes every method invocation
in the repo-local reference VM: five for mint/transfer and five for the merge
(wallet and rules on each token input, wallet on the native input). It also
checks rejection of an unauthorized issuer signature, a bypass path, a token
output missing the wallet path, and an explicit burn output; for the merge it
checks that dropping either the wallet or the rules path from the merged output
is rejected. The machine-readable result is
`/tmp/lotus-v2-token-gallery/fungible-token-summary.json`. No node, wallet or
network is used. Native framing/signature checks and charged execution of all
mint, transfer and merge invocations can additionally be run with the
separately built V2 native checker ([build instructions](../../README.md)):

```sh
node test/run-native-token-fixtures.mjs /path/to/compiler_token_native_check
```

The native runner applies the same proof, selector and re-signed
missing-rules / missing-wallet path rejections to both transfer and merge.

For an artifact-only run without Python, use:

```sh
LOTUS_V2_SKIP_VM=1 \
node examples/gallery/run-fungible-token.mjs /tmp/lotus-v2-token-gallery
```

`FungibleToken` is a mint-only tree. Its root is the token ID. `FungibleRules`
is a separate spend tree that checks every output carrying that token ID.
Both the `FungibleRules` root and the `TokenWallet` root must appear on
**every path** of those outputs; the issuer's mint method enforces the same
two requirements on freshly minted outputs. A holder output has
`branches=[TokenWallet,FungibleRules]` and `paths=[[0,1]]`, so spending it
requires both the wallet and rules witnesses. `paths=[[0],[0,1]]` is a valid
policy shape but violates the token rule, because the first path bypasses the
rules branch; `branches=[FungibleRules]`, `paths=[[0]]` violates it because no
wallet signature would be required to spend.

The example mints 1,000 units, transfers 700 and 250 while implicitly burning
50, then merges the 700- and 250-unit outputs back into one 950-unit output.
A token `IS_BURN` output has no paths, so the rules script rejects it; the burn
is the difference between consumed and created token amounts (zero for the
merge). The issuer can mint again under the same token ID. There is no supply
cap or allowance state in this example.

V2 daemon patch 032 pins this fixture (SHA-256 `5e9151b9…fc716`) in the
standalone native ordinary validator, which applies the signed mint, transfer
and merge against a development UTXO view and rejects an inflated merge, a
dropped token input and a missing rules witness. Regenerate that header only
through a new daemon patch, using `node test/emit-ordinary-fixture-header.mjs`.
This is still transaction-level validation; no block containing these
transactions has been connected.

`summary.json` reports compile, proof, transaction framing, signature, VM,
accounting and block stages separately. The generic Payment method has its own
public signed fixture. The runner reconstructs its transaction wire, TxID,
TxHash and signing message, checks its Schnorr signature, and asks the VM to
execute correct and altered signatures. The other examples are compiler
artifacts, with VM checks only for hashlock, helper and linked in the base
runner. The separate fungible-token runner reports its own stages. Its VM
results are invocation-level checks with caller-supplied digests and
illustrative opcode costs; no block has been connected. The current
compiler/runtime does not implement a stateful counter, allowance state or
relative recovery delay. Those examples remain in the
semantic specification at `docs/lotus-v2/examples/README.md`. No node,
network, wallet or private key is needed to run this gallery.

The source syntax and artifact are candidate tooling, not a deployed contract
language or mainnet consensus result. The checked-in tests also reject missing
template bindings and cyclic `contract_root` dependencies.
