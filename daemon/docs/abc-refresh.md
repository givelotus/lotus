# Coordinated Bitcoin ABC refresh

`daemon/bitcoin-abc-version` is the shared non-V1 ABC selector for the eCash
reference stack and maintained Dogecoin stack. `daemon/patches/doged/manifest.json`
stores the base and intermediate trees to verify Dogecoin patch replay; it is
provenance, not another active pin. `daemon/chronik/source.json` records the
exact ABC commit, Chronik tree, and exported source hashes for the provider.
Those provenance records must agree with the shared pin after a candidate is
promoted.

Lotus V1 is intentionally separate at `daemon/bitcoin-abc-v1-version`. It has
its own consensus patches, release history, and validation evidence. A
coordinated non-V1 update never moves the V1 selector.

## Prepare a candidate

```sh
make -C daemon refresh-abc REF=latest \
  CANDIDATE=/tmp/abc-refresh-2026-10-15
```

`REF=latest` resolves the canonical ABC remote's advertised default branch
once. An exact branch, tag, or commit can be supplied instead. The command
refuses an existing candidate directory and keeps every output under the new
candidate path. It does not modify tracked pins, active workspaces, or releases.

The candidate contains:

- `bitcoin-abc-version`: the proposed shared pin.
- `workspaces/ecash` and `workspaces/doged`: separate patch replays at that
  exact base. The empty eCash series is reported as a successful base-only
  replay; Dogecoin replays its complete 174-patch series.
- `doged-manifest.json`: proposed Dogecoin provenance with the candidate base,
  intermediate trees, and integration commit IDs. Original patch author, date,
  and message hashes must remain unchanged.
- `chronik-provider/`: a source-verified Chronik export and candidate provider
  pin from the same ABC commit, plus clean-application checks for the ABC,
  BCHN, and Bitcoin Core Chronik adapters.
- `refresh-report.json` and per-stack replay logs, distinguishing application
  and export from builds and behavioral validation.

Patch application and export do not prove builds, sync, consensus behavior,
indexing parity, or reorg handling. Run each target's documented build and
behavioral checks against the candidate before promotion. A failed target does
not stop the remaining checks and never changes the active pin.

The 2026-10-15 candidate at ABC `33ae885a` has since passed Doged patch
provenance, an arm64 macOS CMake build, all 757 `test_bitcoin` cases, all 144
Avalanche unit cases, PoW checks, and selected AuxPoW/activation/P2P/mining/
Chronik functional tests. Exact identities and limits are in
[Doged candidate validation](doged-abc-33ae-validation.md). This is not full
mainnet-tip sync or reproducible-binary evidence, and it does not promote the
active selector or historical Doged release manifest.

## Promote only after validation

After reviewing the candidate and passing the required target checks, promote
the shared base selector, Dogecoin provenance manifest, and Chronik provider
source pin/export metadata together in one commit. Keep their ABC commit values
consistent. Do not copy a partial candidate into the active tree. V1 release
assets and its pin are outside this process.
