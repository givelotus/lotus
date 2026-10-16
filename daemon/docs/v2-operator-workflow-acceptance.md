# Private V2 operator workflow acceptance — 2026-10-15

The reviewed controller at `f5a72c4cef12f0f1ec599e40b683f656c2b644d8`
passed the native operator gate in 9.512 seconds. It launched two independent
foreground controller sessions with separate node/wallet homes, explicit nonzero
loopback P2P endpoints and separate Chronik listeners. All functional operations
used the unchanged public `Controller.execute` commands; the gate also recorded
bounded, read-only native transaction-status observations to fence asynchronous
P2P relay. It used no controller adapters or mocked native behavior.

This is a same-host private acceptance result with Avalanche **off**. It does not
establish separate-machine operation, quorum/finality, production synchronization,
release readiness or publication. Avalanche configuration validation is covered by
controller tests; this native gate does not demonstrate credential provisioning.

## Observed workflow

- Receiver created and registered `bob`, exported its public recipient descriptor,
  and shared that file. Sender imported it as `bob-remote`; matching descriptor
  SHA256 was `c718a9f914d63ae39e5c8482bbc027b31ffa177453d04a613c9c5262eb29c77e`.
  Import and export recompiled the public key using the pinned Payment compiler.
- `wallet pay alice --to-recipient bob-remote --amount 10000 --fee 1000` submitted
  the payment without changing the sender tip or creating a sender-side recipient
  wallet. Receiver independently mined the relayed transaction and discovered a
  present receipt with value `10000` through its explicit Chronik binding.
- Both sessions stopped cleanly and resumed their original homes/configuration at
  generation 2. Sender mined a longer branch while receiver was offline. On
  reconnection, receiver discovery cleared the detached receipt and sender wallet
  history reported `pending` on the competing branch. Sender was offline during
  the original confirmation, so this trace does not claim an observed sender
  `confirmed → pending` transition.
- Sender explicitly rebroadcast the original persisted transaction; native
  submission returned duplicate acceptance. Receiver independently mined it again
  and rediscovered the receipt. No second signing operation occurred.

| Observation | Native identifier |
| --- | --- |
| Payment TxId | `d108c9dc15e5078fd30c0f75ff0596b561cb1898d3d469bd7e74f3e97b0ac5bc` |
| Payment TxHash | `1751f8bd4d4eda23c24c600900a8824ec0b79161263a32cc4d98db9dcc3764d1` |
| Original confirmation | `c1521a034ea5c95ab1f0094f3d65bece90e2e824b2edd8336a865b0d8b306b56` |
| Competing tip | `c55ce0b101265e0b4c323c82e80b1fd9b0ab49df101792cd051ab41c2b65d407` |
| Reconfirmation | `31593343b54fef8e9f439f6a3677b65b3fa74ce2f64d3c681cb627ba2e7ca45a` |

The finalizer attempted cleanup for every controller, checked each owned child had
exited and been reaped, and recorded `cleanup_errors: []`. Both metadata files
ended in `stopped`, generation 2, with sender binding `alice → sender` and receiver
bindings `bob → receiver`, `miner → receiver`. Independent review audited the raw
trace, hashes, receipt transitions, original-wire rebroadcast, metadata and absence
of processes using the gate homes. No native gate run failed or was discarded.
Production homes, production ports 10604/10605/8331 and published assets were
untouched. The original isolated homes and full evidence remain at
`/private/tmp/lotus-v2-operator-native-gate-20261015`.

## Exact inputs and evidence

| Component | Source or SHA256 |
| --- | --- |
| Controller source | `f5a72c4cef12f0f1ec599e40b683f656c2b644d8` (initial implementation `19d33feb`) |
| Controller file | `e43c8017d9761bcf558479a1dce7bdd18682e64660396c9ffee29e0ba2efc825` |
| Native gate file | `9037195a5dcb13edf46824774d603e458076e61faf25ac9cc4707a399e2be29a` |
| Daemon source | `e775de1363c8ef9411f4c38b6c7504dacf4402be` |
| Daemon binary | `5d2ba8f0a2b5bb84de31a2e76860f8b6ef947ddf611b72bb9f03fb10635c59b0` |
| Wallet source | `1ab203f0c53ea4e620fac80ac6781e6176fa3fac` |
| Wallet binary | `080c39f2b71e0180933d216e7ef2b06dd32eccc9d83720cae34b2e61e4df50ff` |
| Manifest | `0ccb2872198a354e9cdc5e9c91d1816cf65bf8109efc200d86537d65dc660d05` |
| Compiler source | `2c61dd61d3b1939393634b06c90724fd9584f191` |
| Compiler `dist/generic.js` | `80c96c0f5ce93a5eedc7edfc81dd89bc5d9b8f3759f1447cb02b77b6c1130317` |
| Payment source | `6a2e30a64dbbab678e446a3d3d67241dc9320084eaeef8103abd61ef235911bd` |
| Node executable | `4ca2a42d6d55a834b04d0892c5bc646a6869fcebec57f91c849dac0aa1031610` |

Wallet source attribution was cross-checked against both
[the previous reviewed summary](discovery-live-wallet-acceptance.json) and its
underlying preserved native evidence. These daemon/wallet artifacts retain their
separate source pins; this gate did not build them at the controller revision.
Compiler hashes cover the explicit entry, Payment source and Node executable,
with no claim of a complete dependency-tree commitment.

The [archived raw evidence](evidence/v2-operator-workflow-acceptance-20261015/evidence.json)
contains all 58 public command/responses, three native relay observations, exact
identity, normalized configurations, final session metadata and native outputs.
Its SHA256 is `ff87e8ff46d13a318d4129f0ea9fbc818739b6a404a90a19cd275ce8f9748da0`.
[Per-command/response hashes](evidence/v2-operator-workflow-acceptance-20261015/command-hashes.json)
define their encoding and reference the raw trace by zero-based index.
[Provenance](evidence/v2-operator-workflow-acceptance-20261015/provenance.json)
records exact executable/source inputs, test results and historical wallet evidence
hash. [Checksums](evidence/v2-operator-workflow-acceptance-20261015/checksums.json)
cover the archived public evidence and configuration files. No encrypted wallet,
node database, passphrase, private key or credential file was copied into this
archive.

## Checks and replay

The combined Python suite ran 65 cases successfully: 63 passed and two explicit
native gates were skipped. The separate approved native operator gate passed 1/1. Independent
review ran the 13 operator cases and the additional runtime compiler-drift case in
an isolated checkout. The original local wallet-flow assertions remain enabled;
the transport fixtures now represent native home reopening, explicit bindings,
canonical temporary paths and metadata flush before fixture deletion.

```sh
python3 -m unittest discover -s tools/lotus-v2-devnet/tests -q
LOTUS_V2_APPROVED_OPERATOR=/absolute/approved-pinned-spec.json \
  python3 -m unittest discover -s tools/lotus-v2-devnet/tests \
  -p test_operator_native.py -v
```

The native specification supplies pinned daemon/wallet/manifest paths, compiler
and Node paths, expected chain/genesis/profile identity, and a **new** absolute
output directory. Use the recorded provenance inputs with locally verified
artifacts and a fresh directory; the gate refuses existing output. It allocates
four nonproduction loopback ports once, pins them in separate network inputs,
and preserves those exact ports through clean resume. Execute the runbook on
separate hosts and record actual Avalanche observations separately before making
those deployment or finality claims.
