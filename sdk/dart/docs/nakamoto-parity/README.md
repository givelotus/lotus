# Chain-explicit Dart API

`package:lotus_dart/nakamoto.dart` exposes addresses, keys, HD derivation,
transaction/header codecs and explicit signing for the same six chain families
as Frank's `@frank/nakamoto`. The reference is Frank commit
`8c9e38f46ee429826ff918df6eb79214a06af98c`. This is a Dart API with matching
byte behavior for the operations below, rather than a replacement for every
TypeScript export. `lotus.dart` and Vase's existing imports remain unchanged.

Network facts have one owner: the pinned Nakamoto descriptors and Frank's
canonical protocol registry. The Dart constants are generated from the recorded
reference fixture. No default network, fee rate, dust threshold or coin type is
silently selected. Descriptors retain the upstream provenance, capabilities,
identity probes, script-era metadata and explicitly unpinned facts. Declared
proxy capabilities do not mean a client has contacted or verified an endpoint.

## Public operations

| Nakamoto concept | Dart API |
|---|---|
| Explicit chain descriptors | `chains`, `getChain(protocolId)` |
| Address encoding/decoding and locking scripts | `Address.fromPublicKey`, `Address.fromScriptPubKey`, `Address.parse`, `encode`, `scriptPubKey` |
| Secret/public keys and chain-specific WIF | `ChainKey.fromBytes`, `fromWif`, `publicKey`, `toWif`, `address` |
| BIP32 and explicit BIP44 derivation | `ChainHDKey.fromSeed`, `parse`, `derive`, `derivePath`, `deriveBip44Account`, `neuter`, `serialize` |
| Raw transactions and chain-specific IDs | `ChainTransaction.parse`, `fromHex`, `serialize`, `txid`, `wtxid`, `blockMerkleLeaf`, `chainMerkleRoot` |
| Explicit signature digest and standard input signing | `transactionSignatureHash`, `signTransactionInput` |
| Base headers and block hashes | `ChainBlockHeader` |
| Low-S DER ECDSA | `signEcdsa`, `verifyEcdsa` |
| BIP340 Schnorr primitive | `signSchnorrBip340`, `verifySchnorrBip340` |
| ECDH and additive tweaks | `ecdh`, `tweakAddPrivateKey`, `tweakAddPublicKey` |

`signSchnorrBip340` requires explicit 32-byte auxiliary randomness. It is not
BCH Schnorr and does not implement transaction-level BIP341 signing. `ecdh`
returns the compressed shared point, without silently applying a hash/KDF.
As in Nakamoto, ECDH and ECDSA verification accept SEC1 or 32-byte x-only keys;
x-only keys are lifted with even Y. Address and HD-key parsing require SEC1.
The ECDSA facade accepts strict DER signatures; use the separate existing
`BCHSignature` API for compact/recoverable signature formats.
PointyCastle and Dart BigInt operations do not provide constant-time guarantees.

## Supported chains

| Family | Networks | Address formats | Standard input signing |
|---|---|---|---|
| BTC | mainnet, testnet, regtest | Base58Check; Bech32 v0; Bech32m v1 output keys | P2PKH legacy; native P2WPKH BIP143 |
| BCH | mainnet, testnet, regtest | Base58Check; CashAddr | P2PKH fork-id ECDSA |
| XEC | mainnet, testnet, regtest | Base58Check; CashAddr | P2PKH fork-id ECDSA |
| XPI | mainnet, testnet, regtest | XAddress P2PKH/P2SH | P2PKH fork-id ECDSA; explicit replay-protection option |
| DOGE | mainnet, testnet | Base58Check | P2PKH legacy ECDSA |
| LTC | mainnet, testnet | Base58Check; Bech32 v0; Bech32m v1 output keys | P2PKH legacy; native P2WPKH BIP143 |

Canonical IDs include `btc-mainnet`, `xpi-mainnet`, `doge-mainnet` and
`litecoin-mainnet` (not `ltc-mainnet`). `btc-testnet` means testnet3 in the pinned
reference. Other networks in Frank's broader protocol registry, such as Bitcoin
testnet4, are not implicitly accepted by this library.

All families have chain-specific compressed/uncompressed WIF and BIP32 version
bytes. BIP44 callers must name the coin type explicitly. Address recognition is
limited to the listed standard output templates: decoding an address does not
prove script spendability. Bech32m output-key addresses are supported without
claiming Taproot spending. Lotus Taproot/state scripts and arbitrary XAddress
scripts are not implemented in this entry point.

Transaction codecs preserve legacy and supported SegWit serialization. Values
are unsigned 64-bit `BigInt` base units; this wire range is not a consensus
maximum-money check. Lotus uses merkleized TxIds, raw-serialization TxHashes,
zero-padded odd Merkle layers and its combined block Merkle leaf. Other chains
use conventional transaction IDs. Header codecs read the 80-byte base header or
160-byte Lotus header. Dogecoin AuxPoW extensions and Litecoin MWEB framing/PoW
validation are outside this header-only API.

## Explicit signing

```dart
final chain = getChain('xec-mainnet');
final key = ChainKey.fromBytes(secretBytes);
final recipient = Address.parse(recipientText, chain: chain);
final tx = ChainTransaction(
  chain: chain,
  inputs: [ChainTxInput.fromDisplayTxId(txid: previousTxid, outputIndex: 0)],
  outputs: [ChainTxOutput(
    value: BigInt.parse('100000'),
    scriptPubKey: recipient.scriptPubKey,
  )],
);
final signed = signTransactionInput(
  tx, 0,
  key: key,
  spentOutput: ChainTxOutput(
    value: BigInt.parse('101000'),
    scriptPubKey: key.address(chain: chain).scriptPubKey,
  ),
  spendType: SimpleSpendType.p2pkh,
  algorithm: SighashAlgorithm.forkId,
  hashType: 0x41,
);
print(signed.toHex());
```

Callers provide and independently verify the spent output, chain, fee and
authorization. Signing checks that the supplied key matches that output and
returns a new transaction. It does not discover coins, reserve funds, broadcast
or retry. Every input requires an explicit signing call; this is not an atomic
`signAll` implementation. Use legacy algorithm/`0x01` for BTC/DOGE/LTC P2PKH,
BIP143/`0x01` for native BTC/LTC P2WPKH, and fork-id/`0x41` for current
BCH/XEC/XPI P2PKH. NONE, SINGLE and ANYONECANPAY digest behavior is also tested.

Unsupported algorithms/capabilities fail explicitly rather than falling back.
Remaining parity gaps include Script evaluation, general scriptCode /
OP_CODESEPARATOR handling, P2SH/multisig spending, BCH Schnorr, CashTokens and
SIGHASH_UTXOS, transaction-level Taproot/BIP341, SIGHASH_LOTUS, DLEQ, message
signing and partial-Merkle proofs. The legacy API's Script helpers do not
establish these capabilities for the new entry point. Chronik and Electrum
remain separate existing imports; Electrum requires `dart:io`.

## Reproducing reference evidence

Run from `sdk/dart`:

```sh
dart pub get
node tool/generate_nakamoto_fixtures.mjs /path/to/frank \
  --output test/fixtures/nakamoto-parity.json \
  --provenance test/fixtures/nakamoto-provenance.json
dart run tool/generate_nakamoto_chains.dart --check
dart test
dart analyze --no-fatal-warnings
dart compile js tool/check_nakamoto_web.dart -o /tmp/lotus-nakamoto-web.js
node /tmp/lotus-nakamoto-web.js
```

Fixture generation executes the actual pinned TypeScript exports with Frank's
installed esbuild/Noble dependencies. It records the exact Git revision,
source/dependency hashes and canonical registry, and refuses a different source
revision. The resulting reference is `test/fixtures/nakamoto-parity.json`;
`nakamoto-provenance.json` records hashes and tool versions. The generator does
not modify Frank. Re-run the chain generator without `--check` only when
deliberately updating the reference; review the resulting source diff.

Independent reference tests exercise all sixteen descriptors, addresses, WIF,
BIP32 and supported signature digests. Official BIP143 and BIP340 vectors add
separate standards evidence. The unchanged BIP340 CSV was downloaded from
`https://raw.githubusercontent.com/bitcoin/bips/master/bip-0340/test-vectors.csv`,
SHA256 `34c9d1d9c3a88d524bc80778540dc43f8306ec249a7485293063c376db851c2d`.
Existing Lotus fixtures retain their independently checked mainnet RPC/Chronik
provenance. These checks make no claim of live spending or six-chain node
consensus validation.

The API adapts Nakamoto concepts and protocol algorithms. Upstream MIT notices
are preserved in [NAKAMOTO-LICENSE](NAKAMOTO-LICENSE); the original SDK license
also remains intact.
