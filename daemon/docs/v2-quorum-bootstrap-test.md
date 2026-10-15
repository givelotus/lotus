# Native development stake preparation

`daemon/tests/check-v2-quorum-bootstrap.py` prepares a real accepted 2024-block
native development chain. It establishes funding and maturity inputs for a later
peer-proof/quorum driver. Successful preparation makes no claim about proof
registration, connected stake, quorum readiness, polling, finality or mainnet.

First run the reviewed candidate generator into a new directory:

```sh
python3 tools/lotus-v2-devnet/fixtures/quorum-dev/generate.py \
  --output /tmp/new-quorum-profile
```

Then use a reviewed native build and built Payment compiler, with exact full
source commits and another new output directory:

```sh
python3 daemon/tests/check-v2-quorum-bootstrap.py \
  --daemon /absolute/path/to/lotusd \
  --compiler /absolute/path/to/built/compiler \
  --manifest /tmp/new-quorum-profile/manifest.json \
  --daemon-source FULL_COMMIT \
  --compiler-source FULL_COMMIT \
  --generator-source FULL_COMMIT \
  --output /tmp/new-native-quorum-bootstrap
```

The candidate report must match the manifest digest and chain identity. The
harness requires its nine funding blocks and 2016-confirmation threshold. It
compiles nine Payment roots from x-only public keys of deterministic scalars
1–9. **These are public test fixtures, including their known signing scalars;
never send real funds to these policies.** These outputs belong to no production
wallet. Later proof builders can reproduce their fixture signatures.

Blocks 1–9 use an explicit uint64 maximum claim bound. The actual native block
assembler quotes permitted entitlement and cost/burn deductions, then selects
the full available net claim. Subsequent blocks cap the claim at 100000. Every
block uses `minepool` with an empty actual native pool. Neither payment bytes nor
synthetic state roots enter mining. Nonce batches retain the same parent and
continue from the native next nonce, within explicit per-block and overall
bounds. The default overall deadline is 1800 seconds.

Timestamps use the authenticated eleven-header median plus one. They retain the
candidate's actual 120-second ASERT spacing and target calculation. The harness
reads every produced body, independently verifies its actual ASERT target,
PoW, parent links, MTP, complete transaction root and coinbase identity/value,
and waits for authoritative native acceptance before advancing. The offline
generator's header schedule is not substituted for native accepted blocks.

At heights 2023 and 2024, native coin/proof lookups must contain exact funding
coin bytes, creation heights and parent MTPs from the produced blocks. The
harness reconstructs the UTXO root from all actual produced coinbase outputs and
checks the state commitment against the native monetary bytes. The youngest
funding output crosses 2015 to 2016 confirmations at these two milestones.
This arithmetic boundary is preparation evidence; native Avalanche proof
acceptance remains a separate gate. Actual funding must exceed stake dust, and
any eight of the nine actual payouts must total at least the candidate quorum.

The output retains the copied manifest/report, compiler artifacts, all produced
block bodies, ordered `accepted-blocks.jsonl`, native requests/stdout/stderr,
and `evidence.json`. Funding records include outpoints, values, creation
metadata, public keys, Payment scripts/roots and exact native coin bytes. Source
pins and executable/artifact hashes identify the run. Homes and output paths
must be fresh; no reset/resume path exists. The exact child is stopped on success
or failure. Only ephemeral loopback ports are used, excluding 10604, 10605 and
8331. Preserve failed outputs and select another fresh directory for retries.
