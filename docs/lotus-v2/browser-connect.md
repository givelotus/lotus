# Lotus V2 and multi-chain browser connect protocol (`lotus-connect/1`)

Status: candidate browser and multi-chain wallet connection specification,
provisional through pre-launch testnet. This is an application and
wallet-bridge protocol, not a consensus change. It defines how web applications
discover and communicate with a user's browser extension or companion wallet
over a dedicated W3C `MessageChannel` (`MessagePort`), how intent-first native
Lotus V2 transactions and contract calls integrate with
[`@lotus/v2-payment-compiler/transaction-runtime`](../../tools/lotus-v2-compiler/TRANSACTION-RUNTIME.md)
(`prepareTransactionCall` / `finalizeTransactionCall`, `lotus-v2/contract-artifact/2`,
`lotus-v2/policy-artifact/1`) and [Lotus V2 PSBT profile 1 (`0x4c560001`)](psbt.md),
how origin-bound personas and [application message signatures (`lotus-chain-bound-compact-ecdsa-v1`)](message-signing.md)
prevent cross-site tracking, and how the same envelope dispatches across
multi-chain CAIP-2 namespaces (`bip122:*`, `eip155:*`, `solana:*`).

## Why legacy Web3 attachment protocols fail

Existing browser wallet injection standards (`window.ethereum` / EIP-1193,
EIP-6963, Solana `@wallet-standard`, Bitcoin WBIP004 / `window.unisat`, and
eCash Cashtab `window.postMessage` broadcasts) share four structural flaws:

1. **Ambient authority and passive fingerprinting**:
   Injecting provider objects onto `window` at `document_start` or replying to
   unprompted `eip6963:requestProvider` / `wallet-standard:app-ready` broadcasts
   allows every visited webpage to enumerate the user's installed wallet
   extensions in under 1 ms without a user gesture. A static `info.uuid` or
   combination of `window.*` flags acts as a cross-origin browser fingerprint
   bitmask that persists across IP rotations.
2. **Cross-site address correlation ("identity-first" supercookies)**:
   Legacy dApps call `eth_requestAccounts`, `solana.connect()`, or
   `unisat.requestAccounts()` immediately on page load before any transaction
   intent exists. When a wallet returns one global primary address across
   origins, third-party analytics scripts correlate the user's identity, net
   worth, and transaction history across unrelated websites.
3. **UTXO inventory leakage and Common-Input-Ownership Heuristic (CIOH)**:
   On UTXO chains (Lotus, Bitcoin, Bitcoin Cash, eCash, Dogecoin, Litecoin),
   legacy dApps query the user's wallet UTXO set to build unsigned transactions
   in page JavaScript. Exposing the wallet's UTXO inventory reveals the user's
   total balance to the webpage, and co-spending multiple wallet UTXOs in an
   application-constructed transaction permanently links those addresses on
   chain under CIOH.
4. **Cross-world DOM event cloning hazards and shared-bus eavesdropping**:
   In WebKit/Safari Web Extensions, dispatching a `CustomEvent` whose `detail`
   contains functions (such as an EIP-1193 or Wallet Standard provider) from an
   `ISOLATED` content script to the `MAIN` page world causes structured cloning
   to strip `event.detail` to `null`. Conversely, broadcasting RPC payloads over
   `window.postMessage(..., '*')` exposes every request and response to any
   third-party script running in the same document and requires hex/Base64
   stringification of binary transaction templates, Merkle proofs, and
   signatures.

`lotus-connect/1` replaces ambient globals and shared-bus broadcasts with a
capability-scoped W3C `MessageChannel` (`MessagePort`), connectless transaction
intent fulfillment (`wallet_fulfillIntent`), and per-origin cryptographic
persona isolation (`account = 1'`).

## Transport layer: W3C `MessageChannel` (`MessagePort`) handshake

### Stealth discovery and explicit port transfer

A compliant wallet MUST NOT mutate `window` or emit unsolicited provider
announcements on arbitrary origins when configured in `stealth` or
`connected-only` mode. Instead, a dedicated point-to-point `MessagePort` is
established only when:

1. The user explicitly invokes a connection or payment gesture, or
2. The current `window.location.origin` already holds an active, non-expired
   session grant in the wallet enclave.

To initiate a channel, the page creates a standard W3C `MessageChannel` and
transfers `port2` to the extension's isolated content script via a one-time
handshake message:

```ts
const channel = new MessageChannel();
const clientPort: MessagePort = channel.port1;
clientPort.start();

window.postMessage(
  {
    protocol: "lotus-connect/1",
    type: "handshake-init",
    requestedChains: [
      "bip122:000000000abc0cde58ee7e919d3d4de1", // Lotus mainnet
      "eip155:143",                              // Monad mainnet
      "solana:5eykt4UsFv8P8NJdTREpY1vzqKqZKvdp", // Solana mainnet
    ],
  },
  window.location.origin,
  [channel.port2],
);
```

### Transport invariants

1. **Private point-to-point pipe**:
   Once `channel.port2` is transferred in the `MessageEvent.ports` array to the
   extension's `ISOLATED` content script, all subsequent requests, responses,
   and lifecycle events flow exclusively across `port1 <-> port2`. Third-party
   scripts injected into the page after the handshake cannot eavesdrop on or
   spoof messages on the port.
2. **Native W3C Structured Clone payloads**:
   Messages over `MessagePort` use the browser's native Structured Clone
   algorithm (`Uint8Array`, `bigint`, `Map`, `Set`, and nested typed records),
   eliminating hex/Base64 serialization overhead and `JSON.stringify` `BigInt`
   exceptions when transporting Lotus V2 transaction wire bytes, sparse-state
   `CoinProof`s, or `lotus-v2/contract-artifact/2` bundles.
3. **Unspoofable origin and frame binding**:
   The `ISOLATED` content script MUST ignore any origin claim inside the page's
   payload and attach the browser-verified `origin: window.location.origin`,
   `href: window.location.href`, and `isTopFrame: window.top === window` to
   every envelope forwarded to the wallet background enclave. Cross-origin
   `<iframe>` contexts without explicit user activation MUST be rejected before
   reaching the signing engine.
4. **Handshake response (`handshake-ack`)**:
   The wallet replies on `port2` with `handshake-ack` containing only non-identifying
   protocol support metadata (`protocol: "lotus-connect/1"`, supported CAIP-2
   chain IDs, and Lotus V2 compiler/ABI profile `'P01-P02-P03-candidate-2026-10-14'`).
   No account address, public key, UTXO, or persistent wallet UUID is returned
   during `handshake-init` / `handshake-ack`.

## CAIP-2 chain identification

Every `lotus-connect/1` request carries an explicit, non-null
[CAIP-2](https://chainagnostic.org/CAIPs/caip-2) chain identifier (`caip2`).
Wallets MUST validate both the CAIP-2 identifier and the underlying consensus
chain parameters (`ChainID[32]` on Lotus V2, `eth_chainId` + block checkpoint on
EVM, `genesisHash` on Solana, and fork/genesis block checkpoint on Bitcoin-family
chains).

| Chain family | Network | Canonical `caip2` identifier | Lotus V2 `ChainID[32]` / native binding |
| --- | --- | --- | --- |
| Lotus (`xpi`) | Mainnet | `bip122:000000000abc0cde58ee7e919d3d4de1` | `960da6d7e4c6f4fe0b639f08e7c344a2c654610aed4b3377149666406a0d1597` (`hrp = xpi`) |
| Lotus (`xpi`) | Testnet | `bip122:00000000080a6c9633aae9d24b9acda1` | `5f5e904cc5dfab62a8b62ee22551bca02e47a6d92d0de1f73c150e906bc3851b` (`hrp = txpi`) |
| Lotus (`xpi`) | Regtest | `bip122:xpi-regtest` | `0000000000000000000000000000000000000000000000000000000000000000` (`hrp = rxpi`) |
| EVM (`evm`) | Monad / ETH / L2s | `eip155:<decimal_chain_id>` (e.g. `eip155:143`, `eip155:1`, `eip155:8453`) | EIP-155 `chainId` uint256 |
| Solana (`solana`) | Mainnet / Devnet / Testnet | `solana:5eykt4UsFv8P8NJdTREpY1vzqKqZKvdp` / `solana:EtWTRABZaYq6iMfeYKouRu166VU2xqa1` | 32-byte genesis hash |
| Bitcoin (`btc`) | Mainnet / Testnet3 / Testnet4 / Regtest | `bip122:000000000019d6689c085ae165831e93` / `bip122:000000000933ea01ad0ee984209779ba` / `bip122:00000000da84f2bafbbc53dee25a72ae` / `bip122:btc-regtest` | Genesis hash prefix |
| Bitcoin Cash (`bch`) | Mainnet / Testnet / Regtest | `bip122:000000000000000000651ef99cb9fcbe` / `bip122:00000000000e38fef93ed9582a7df438` / `bip122:bch-regtest` | Post-fork checkpoint hash prefix |
| eCash (`xec`) | Mainnet / Testnet / Regtest | `bip122:000000000000000004284c9d8b2c8ff7` / `bip122:00000000062c7f32591d883c99fc89eb` / `bip122:xec-regtest` | Post-fork checkpoint hash prefix |
| Dogecoin (`doge`) | Mainnet / Testnet | `bip122:1a91e3dace36e2be3bf030a65679fe82` / `bip122:bb0a78264637406b6360aad926284d54` | Genesis hash prefix |
| Litecoin (`ltc`) | Mainnet / Testnet | `bip122:12a765e31ffd4059bada1e25190f6e98` / `bip122:4966625a4b2851d9fdee139e56211a0d` | Genesis hash prefix |

## Core primitive 1: `wallet_fulfillIntent` (connectless transaction and contract-call fulfillment)

The primary operation in `lotus-connect/1` is `wallet_fulfillIntent`. A web
application submits a declarative payment, token transfer, or covenant
interaction **without first calling `connect()` or learning the user's
persistent address or UTXO inventory**. The wallet enclave privately selects
funding inputs, derives fresh receive/change policies, verifies contract
artifacts and state proofs, presents the exact net balance deltas to the user,
signs, and broadcasts or returns the finalized transaction.

### Request envelope

```ts
export type WalletFulfillIntentRequest = {
  protocol: "lotus-connect/1";
  id: string;
  method: "wallet_fulfillIntent";
  caip2: string;
  broadcast?: boolean; // default true
  intent:
    | LotusV2TransactionIntentPayload
    | LotusV2PsbtIntentPayload
    | EvmCallBundleIntentPayload
    | SolanaInstructionIntentPayload
    | BitcoinUtxoIntentPayload;
};
```

### Lotus V2 native integration with `@lotus/v2-payment-compiler/transaction-runtime` and `psbt.md`

On Lotus V2 (`bip122:000000000abc0cde58ee7e919d3d4de1`,
`bip122:00000000080a6c9633aae9d24b9acda1`, `bip122:xpi-regtest`), a dApp
submits either a structured **Partial `TransactionIntent`** compatible with
`@lotus/v2-payment-compiler/transaction-runtime` (`prepareTransactionCall` /
`finalizeTransactionCall`) or a binary **[Lotus V2 PSBT Profile 1 (`0x4c560001`)](psbt.md)**
document (`Uint8Array`).

#### Mode A: Partial `TransactionIntent` with symbolic wallet slots

When interacting with compiled Lotus V2 contracts (`lotus-v2/contract-artifact/2`)
and policies (`lotus-v2/policy-artifact/1`), the dApp knows the protocol
outpoints (e.g., an AMM pool UTXO, vault singleton, or orderbook covenant) and
the required contract outputs, but does **not** know the user's funding UTXOs
or destination policy. The dApp supplies a `LotusV2TransactionIntentPayload`:

```ts
export type WalletPolicyPlaceholder =
  | "$WALLET_FRESH_RECEIVE_POLICY"
  | "$WALLET_PERSONA_POLICY";

export type IntentAssetOutput = {
  flags: 0 | 1 | 2 | 3; // 0=native spendable, 1=token spendable, 2=native burn, 3=token burn
  value: bigint;        // u64 atoms (1 XPI = 10^6 atoms) or token units
  tokenId?: string;     // 32-byte hex for flags 1 or 3
  branches: string[] | WalletPolicyPlaceholder;
  paths: number[][] | WalletPolicyPlaceholder;
  policyArtifact?: PolicyArtifactV1; // optional companion lotus-v2/policy-artifact/1
};

export type IntentSpendInput = {
  kind: "spend";
  prevTxid: string;
  prevIndex: number;
  sequence: number;
  coin: AssetOutput;          // resolved CoinOutput
  rawCoinBytes?: Uint8Array;  // full sparse_state EncodeCoin bytes (with 34-byte suffix)
  coinProof?: Uint8Array;     // sparse_state Present CoinProof against UTXO_ROOT
  pathIndex: number;
  witnesses: {
    artifact: ContractArtifact; // schema: 'lotus-v2/contract-artifact/2'
    methodName: string;
    args: Record<string, Uint8Array | bigint | boolean | null | "$WALLET_PUBKEY" | "$WALLET_SIG">;
  }[];
};

export type IntentMintInput = {
  kind: "mint";
  artifact: ContractArtifact; // schema: 'lotus-v2/contract-artifact/2', kind: 'token'
  methodName: string;
  args: Record<string, Uint8Array | bigint | boolean | null | "$WALLET_PUBKEY" | "$WALLET_SIG">;
};

export type WalletFundingRequirement = {
  kind: "$WALLET_FUNDING_INPUTS";
  nativeAtomsRequired?: bigint;         // optional hint; wallet recomputes exact deficit + fee
  tokenAmountsRequired?: Record<string, bigint>; // tokenId (32-byte hex) -> required u128 amount
};

export type LotusV2TransactionIntentPayload = {
  kind: "lotus-v2-transaction-intent";
  profile: "P01-P02-P03-candidate-2026-10-14";
  chainId: string;          // 32-byte raw digest order hex
  utxoRoot?: Uint8Array;    // 32-byte header state commitment for COIN_PROOF verification
  lock?: bigint;            // u64 P01 lock encoding
  dustLimitAtoms: bigint;
  inputs: (IntentSpendInput | IntentMintInput | WalletFundingRequirement)[];
  outputs: (IntentAssetOutput | { kind: "$WALLET_CHANGE_OUTPUT" })[];
};
```

#### Mode B: Binary Lotus V2 PSBT Profile 1 (`0x4c560001`)

For partially signed multiparty workflows or hardware-wallet interchange
defined in [`psbt.md`](psbt.md), the dApp supplies a binary PSBT container
directly as a `Uint8Array`:

```ts
export type LotusV2PsbtIntentPayload = {
  kind: "lotus-v2-psbt";
  psbtBytes: Uint8Array; // Magic 70736274ff, global VERSION 0100564c (0x4c560001), proprietary "lotus-v2"
  contractArtifacts?: ContractArtifact[]; // optional schema-2 artifacts for human-readable method/arg decoding
  policyArtifacts?: PolicyArtifactV1[];   // optional schema-1 policy artifacts for multi-branch verification
};
```

#### Wallet enclave verification and completion pipeline (7 steps)

When the wallet enclave receives a `LotusV2TransactionIntentPayload` or
`LotusV2PsbtIntentPayload`, it MUST execute the following deterministic pipeline
before rendering the user approval prompt:

1. **Chain identity verification**:
   Verify `caip2` and the 32-byte `chainId` (`CHAIN_ID` global proprietary key
   `01` in PSBT) against the wallet's active local chain configuration. Reject
   immediately on mismatch.
2. **Sparse-state coin authentication (`COIN` + `COIN_PROOF`)**:
   For every application-supplied `SpendInput` (or PSBT input record), verify
   the full canonical `Coin-v2` bytes (`prev_txid:32 || prev_index:u32 || Bytes(CoinOutput) || creation_height:u64 || creation_parent_mtp:u64 || coinbase:u8 || encoding_version:u8 (=2) || fee_per_output:u64 || expiration_height:u64`)
   and verify its `COIN_PROOF` (`bitmap:32 || CS(sibling_count) || sibling:32*`)
   against the wallet's independently obtained `UTXO_ROOT` / validated chain
   header commitment, as required by [`psbt.md`](psbt.md#coin-authentication-and-signing).
   Never trust an attacker-supplied `UTXO_ROOT` without header/chainstate
   validation.
3. **Contract and policy artifact verification (`lotus-v2/contract-artifact/2` & `lotus-v2/policy-artifact/1`)**:
   Run `assertContractArtifact(artifact)` from `@lotus/v2-payment-compiler/call-runtime`
   on every supplied contract artifact. Recompute `methodRoot(m.scriptHex, m.proof)`,
   verify `sorted-leaves-largest-power-split-v1` tree construction, verify that
   each witness method's root matches `coin.branches[coin.paths[pathIndex][w]]`,
   and verify any companion `lotus-v2/policy-artifact/1` branch-and-path lowering
   (`Vec(h32)||Vec(Vec(CS(index)))`). Unsupported bytecode without a verified
   policy or explicit user override MUST fail closed.
4. **Private wallet input selection and fresh policy substitution**:
   - Replace every `$WALLET_FRESH_RECEIVE_POLICY` placeholder with a freshly
     derived, unlinked single-key Type-1 policy (`DUP BLAKE3 PUSH32(keyhash) EQUALVERIFY CHECKSIG`,
     `flags = 0 | 1`, `branches = [BranchLeaf(program)]`, `paths = [[0]]`; see
     [`addresses.md`](addresses.md#type-1-x-only-keyhash-template-candidate)).
   - Replace `$WALLET_PERSONA_POLICY` (and any `$WALLET_PUBKEY` / `$WALLET_SIG`
     witness placeholders) with the x-only public key and policy bound to the
     origin's isolated `account = 1'` Persona (`Persona(origin, xpi)`).
   - Select uncorrelated wallet UTXOs (`planUtxoPersonaJitInputSelection`) to
     satisfy the transaction's native XPI deficit, token input deficits, the
     complete-wire byte fee floor (`BigInt(predicted.wire.length)`), the token
     output dust floor (`2n * dustLimitAtoms * BigInt(tokenOutputCount)`), and
     P05's parabolic fee-burn calculation (`simulateFeeAndAdjustChange`).
   - Append fresh change output(s) (`$WALLET_CHANGE_OUTPUT`) locked to newly
     derived wallet change policies.
5. **Transaction planning (`prepareTransactionCall`)**:
   Construct the complete `TransactionIntent` and execute
   `prepareTransactionCall(completeIntent)` from
   `@lotus/v2-payment-compiler/transaction-runtime` (or `PrepareSigningContextChecked`
   for PSBT Profile 1). This validates canonical framing, duplicate outpoints,
   checked `u128` per-asset sums, `int128` mint deltas, and produces the
   immutable `TransactionPlan` containing `txid`, `unsignedWire`,
   `projectedFullBytes`, `feeAtoms`, `minimumFeeAtoms`, `tokenDeltas`,
   `tokenBurns`, and `FullSignatureRequest[]`.
6. **Human-readable intent approval UI**:
   Present the verified `TransactionPlan` in the wallet's trusted UI (Chrome
   Side Panel, Firefox Sidebar, Safari extension sheet, or PWA modal):
   - **Native XPI formatting**: Display native XPI amounts and net balance
     changes formatted to **2 decimal places (`1.00 XPI`, like dollars and cents)**
     by default, hiding the lower 4 sub-cent decimal places (`0.00_0000`) while
     exposing exact 6-decimal atom counts (`1 XPI = 10^6 atoms`, e.g. `feeAtoms = 420 atoms = 0.000420 XPI`)
     in the expandable detail/hardware-wallet inspection view (per [`script-abi.md`](script-abi.md#signing-and-addresses)).
   - **Asset deltas, mints, and burns**: Display per-token net user debits/credits,
     positive `tokenDeltas` (minting), and `tokenBurns` (implicit input-minus-output
     burns plus explicit `flags = 2 | 3` burn outputs).
   - **Contract and method provenance**: Display the verified `artifact.contract`
     name, `methodName`, decoded typed arguments, and signing mode (`mode = 0`
     full transaction vs `mode = 1 | 2` partial sighash with explicit warning).
7. **BIP-340 Schnorr signing, finalization (`finalizeTransactionCall`), and branch verification**:
   Upon user approval, sign each `FullSignatureRequest.digest` belonging to the
   wallet's keys using native BIP-340 Schnorr (`scheme = 0`, 64 bytes for
   `mode = 0`, or 64 bytes + 1 mode byte for `mode = 1 | 2` in PSBT Profile 1).
   Execute `finalizeTransactionCall(plan, signatures)` to produce
   `{ wire, txid, txhash }`, run local VM branch verification over all spent
   inputs and mints, and either broadcast `wire` via the configured relay/node
   or return `{ txid, txhash, wire }` over the `MessagePort`.

### Multi-chain `wallet_fulfillIntent` dispatch across EVM, Solana, and Bitcoin-family chains

The same `wallet_fulfillIntent` method dispatches by `caip2` prefix across all
other supported chain families:

| `caip2` namespace | Intent payload kind | Enclave completion and anti-correlation mechanics |
| --- | --- | --- |
| `eip155:<chainId>` (EVM: Monad, Ethereum, Base, Arbitrum, Polygon, BNB, Hyperliquid, Tempo) | `evm-call-bundle`: `{ calls: { to, data, value }[], requiredTokens?: { token, amount }[] }` | Derives the origin's isolated `account = 1'` Persona EOA (`m/44'/60'/1'/0/k`). Computes $\Delta_{\text{shortfall}} = \max(0, V_{\text{tx}} + G_{\text{dapp}} \cdot F_{\max} - B_{\text{persona}})$. If $\Delta_{\text{shortfall}} > 0$, executes a Just-In-Time (JIT) Stamp Pool sweep (`executeDappJitSweepAndSignTx`) into the Persona EOA, prepends exact-amount ERC-20 `approve` calls (never unlimited `MAX_UINT256`), simulates net balance changes, signs EIP-1559 (Type 2), and broadcasts. |
| `solana:<genesisPrefix>` (Solana Mainnet, Devnet, Testnet) | `solana-instruction-intent`: `{ instructions: IntentInstruction[], lookupTables?: string[] }` with `$WALLET_FEE_PAYER` / `$WALLET_FRESH_RECEIVE` slots | Resolves the origin's `account = 1'` SLIP-0010 Ed25519 Persona (`m/44'/501'/1'/k'`) and Associated Token Accounts (ATAs). Fetches a fresh `recentBlockhash` and attaches `ComputeBudgetProgram` priority fees **at the moment of user approval** (eliminating Solana's 60-second pre-built transaction expiration bug), signs with Ed25519, and broadcasts. |
| `bip122:<genesisOrForkPrefix>` (Bitcoin, BCH, eCash, Dogecoin, Litecoin) | `bitcoin-utxo-intent`: declarative `{ outputs: { addressOrScript, valueSats }[] }` or BIP-174 PSBT (`0x70736274ff` with `PSBT_GLOBAL_UNSIGNED_TX`) | Verifies that a Bitcoin PSBT does not mix native Lotus V2 `0x4c560001` global version keys (`psbt.md`). Uses `planUtxoPersonaJitInputSelection` to fund from the origin's `account = 1'` Persona UTXOs or a 1-hop JIT funding output so the dApp never links the user's primary UTXO cluster, signs via `@frank/nakamoto` (secp256k1 ECDSA or BIP-340 Taproot Schnorr), finalizes, and returns `{ txid, psbtBytes, rawTxHex }`. |

## Core primitive 2: `wallet_requestSession` and `wallet_signMessage` (origin-bound personas and scoped session keys)

When a web application genuinely requires a persistent session identity,
off-chain authentication, or high-frequency micro-actions (such as social
stamps, games, or orderbook cancellations), it invokes `wallet_requestSession`
or `wallet_signMessage` over the `MessagePort`.

### Cryptographic per-origin persona isolation (`account = 1'`)

To prevent cross-site address correlation across all 7 chain families:

1. **Dedicated HD account branch (`account = 1'`)**:
   Primary holdings and privacy/stamp pools reside at `account = 0'` and are
   **never** exposed to any browser origin. All dApp personas are derived under
   `account = 1'` (`m/44'/899'/1'/0/k` or `m/44'/10605'/1'/0/k` for Lotus/eCash,
   `m/44'/60'/1'/0/k` for EVM, `m/44'/501'/1'/k'` for Solana, `m/84'/0'/1'/0/k`
   and `m/86'/0'/1'/0/k` for Bitcoin SegWit/Taproot, `m/44'/145'/1'/0/k` for
   BCH, `m/44'/3'/1'/0/k` for Dogecoin, and `m/84'/2'/1'/0/k` for Litecoin).
2. **Default `'per-origin-burner'` mode**:
   Each origin `https://app-a.example` vs `https://app-b.example` is assigned a
   cryptographically distinct Persona index $k \ge 1$:
   $$\text{Persona}(\text{origin}, \text{caip2}) \neq \text{Persona}(\text{origin}', \text{caip2}) \quad \text{for } \text{origin} \neq \text{origin}'$$
   Two websites cannot correlate a user by comparing returned `xpi1p...`,
   `0x...`, `bc1q...`, or Solana base58 addresses.

### Lotus V2 application message signing (`lotus-chain-bound-compact-ecdsa-v1`)

When a web application requests `wallet_signMessage` on a Lotus V2 chain (`xpi`,
`txpi`, `rxpi`), the wallet uses the exact scheme defined in
[`message-signing.md`](message-signing.md) and [`addresses.md`](addresses.md):

1. **Mandatory origin and nonce binding for web sessions**:
   To prevent a malicious website from tricking a user into signing an off-chain
   challenge belonging to another origin, the wallet enforces or prepends canonical
   origin framing in the UTF-8 `message` body unless the user explicitly unlocks
   raw-text signing in an advanced warning flow:
   ```text
   <domain> wants you to sign in with your Lotus account:
   <xpi1p...>

   Origin: <https://origin>
   Chain ID: <caip2>
   Nonce: <nonce>
   Issued At: <ISO-8601 timestamp>
   ```
   The wallet verifies that `Origin:` matches the browser-verified
   `window.location.origin` attached by the isolated content script.
2. **Exact chain-bound digest (`message-signing.md`)**:
   ```text
   preimage = CompactSize(22) || UTF8("Lotus Signed Message:\n")
              || 0x01 || ChainID[32]
              || CompactSize(len(message)) || message
   digest = SHA256(SHA256(preimage))
   ```
   where `ChainID[32]` is in raw digest byte order (`960da6d7...` on mainnet,
   `5f5e904c...` on testnet, `00..00` on regtest).
3. **65-byte recoverable compact ECDSA signature and Type-1 address check**:
   The wallet signs `digest` using deterministic RFC 6979 low-$S$ secp256k1
   recoverable ECDSA (`ECDSA+Recovery  ` 16-byte personalization) with native
   Type-1 header byte `header = 27 + recovery_id + 4` (`31..34`), returning
   both the 65-byte `Uint8Array` and canonical padded RFC 4648 Base64 string.
   Verifiers recover the secp256k1 public key, extract its 32-byte big-endian
   x-coordinate, and check `BLAKE3(xonly_public_key) == address.payload`
   against the origin's Type-1 `xpi1p...` persona address.

### Scoped session keys and bounded micro-budgets

To eliminate repetitive popup fatigue for high-frequency dApp actions (such as
1-cent `0.01 XPI` micro-stamps, forum upvotes, or game moves):

1. The web application generates a non-extractable WebCrypto or in-memory
   ephemeral secp256k1 x-only keypair (`sessionPublicKey: Uint8Array` of length
   32) inside the browser tab and passes it in `wallet_requestSession`:
   ```ts
   export type WalletRequestSessionParams = {
     caip2: string;
     personaMode?: "per-origin-burner" | "selected-persona";
     sessionKey?: {
       sessionPublicKey: Uint8Array; // 32-byte BIP-340 x-only pubkey (or Ed25519/secp256k1 per chain)
       maxSpendAtoms: bigint;        // e.g. 5_000_000n = 5.00 XPI
       expiresAtUnix: number;        // bounded session TTL
       allowedContractRoots?: string[]; // optional whitelist of 32-byte branch roots
     };
   };
   ```
2. Upon a **single user approval**, the wallet either:
   - Funds a dedicated session UTXO locked to a 2-path policy (`branches = [OwnerPersonaRoot, SessionKeyRoot]`, `paths = [[0], [1]]`) containing at most `maxSpendAtoms`, or
   - Enforces the `maxSpendAtoms` and `expiresAtUnix` allowance inside the background enclave for silent `wallet_fulfillIntent` calls authenticated by `sessionPublicKey`.
3. If the web page is compromised, the maximum value at risk is strictly bounded
   by the session UTXO's `maxSpendAtoms` (e.g., `5.00 XPI`), while the user's
   primary `account = 0'` vault and other origin personas remain unreachable.

## Legacy compatibility shims

While native Lotus V2 and privacy-first multi-chain applications communicate
directly over `lotus-connect/1` `MessagePort` channels, browser wallets MUST
remain compatible with existing EVM, Solana, Bitcoin, and eCash websites. A
compliant wallet architecture layers thin in-page compatibility shims on top of
the exact same internal router and per-origin persona engine:

| Legacy ecosystem surface | In-page shim behavior | Internal mapping to `lotus-connect/1` enclave |
| --- | --- | --- |
| **EVM (`EIP-6963` + `EIP-1193`)** | Announces `rdns: 'mx.signet.frank'` with a **per-page-load ephemeral `crypto.randomUUID()`** (never a static trackable UUID) when allowed by `DappTrackabilityPolicy`. | Maps `eth_requestAccounts` to `wallet_requestSession` (`account = 1'` per-origin burner EOA) and `eth_sendTransaction` to `wallet_fulfillIntent` with automatic JIT Stamp Pool sweeps (`executeDappJitSweepAndSignTx`). |
| **Solana (`@wallet-standard`)** | Registers `standard:connect`, `standard:disconnect`, `solana:signIn` (SIWS), `solana:signMessage`, `solana:signTransaction`, and `solana:signAndSendTransaction`. | Maps `solana:signIn` and `standard:connect` to `account = 1'` per-origin SLIP-0010 Ed25519 personas (`m/44'/501'/1'/k'`). |
| **Bitcoin (`WBIP004` / `sats-connect` + `window.unisat`)** | Exposes `BitcoinProvider` and `window.unisat` shims for `getAccounts`, `signMessage` (ECDSA & BIP-322), and `signPsbt` / `signPsbts`. | Maps each origin to isolated `m/84'/0'/1'/0/k` (`p2wpkh`) and `m/86'/0'/1'/0/k` (`p2tr`) personas, using `planUtxoPersonaJitInputSelection` and `@frank/nakamoto` BIP-174 PSBT signing. |
| **eCash (`Cashtab` `FROM_PAGE` / `FROM_CASHTAB`)** | Listens for `window.postMessage` `{ type: 'FROM_PAGE', text: 'Cashtab' }` requests. | Maps `addressRequest` and `txInfo` to `account = 1'` `ecash:q...` per-origin personas (`m/44'/899'/1'/0/k`) and uncorrelated UTXO selection. |
| **BCH / Doge / Litecoin (`bch_*`, `doge_*`, `ltc_*`)** | Exposes per-family RPC methods over the in-page bridge. | Maps to `m/44'/145'/1'/0/k`, `m/44'/3'/1'/0/k`, and `m/84'/2'/1'/0/k` per-origin personas with anti-cluster UTXO selection. |
