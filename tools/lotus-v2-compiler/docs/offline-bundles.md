# Offline invocation bundles v1

`fixtures/offline/{payment,fungible-token,linked}.json` retain public deterministic development fixtures without private keys. The versioned schema is `bundle-v1.schema.json`. Bundles contain exact UTF8 original fixture/package source bytes, canonical artifact bytes, roots and method proofs, full public transaction/coin/signing context, caller VM cost profiles, and exact supported invocation results, traces and charges.

Generation is explicit and requires the built compiler:

```sh
npm ci --ignore-scripts
npm run build
LOTUS_V2_PYTHON=/path/to/python node test/generate-offline-bundles.mjs
```

Review changed bytes and results before accepting generation. Verification never generates fixtures:

```sh
LOTUS_V2_PYTHON=/path/to/python node --test test/offline-bundles.test.mjs
```

The consumer requires the sibling Python reference package and dependencies in `test/requirements-vm.txt`. It imports no compiler, generated binding or TypeScript runtime and works without `dist` or `node_modules`. Missing dependencies fail rather than skip. Verification checks the schema, bundle/file/artifact digests, method membership proofs, selected script bytes and exact Python VM results. SHA256 provides integrity checking, not authenticated provenance; an adversary who rewrites an entire internally consistent fixture can choose another valid fixture.

Canonical JSON recursively sorts object keys lexicographically, uses UTF8 without whitespace, and permits integer JSON numbers only within the exact JavaScript integer range. Monetary quantities and mint deltas use unsigned decimal strings without leading zeroes. SHA256 covers the canonical payload. Files separately hash exact UTF8 bytes; artifacts hash canonical bytes. Token amounts remain strings until the Python invocation adapter validates and converts them.

Executed programs are generic `Payment.spend`; `TokenWallet.spend`, `FungibleToken.issue`, and `FungibleRules.transfer` for existing mint, transfer and merge transactions; and linked `Escrow.spend`, `Payer.spend`, `Receiver.spend`. Signed invocations also retain zero-signature rejections. All embedded method proofs are checked, but methods without invocation cases are not claimed as executed.

Results certify individual Python VM invocations with caller supplied signing messages and field inputs. Embedded wire, TxID, TxHash, fee/accounting and coin data preserve original transaction context; this consumer does not independently derive signing messages or validate full transaction framing/accounting. Linked constant checks commit to library bytes without executing the referenced contract. Block validation and daemon acceptance are unsupported. This packet freezes no network parameter or open consensus decision.
