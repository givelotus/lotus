# Optional network release inputs

`daemon/scripts/prepare-network-release.py` supplies `prepare_network(replay,
config, allow_rpc=False)` to the release orchestrator. It returns file replacements
and normalized configuration/evidence. It never writes source, starts a daemon,
changes node settings or datadir, commits, or publishes. The caller combines these
replacements with version metadata into one candidate patch and manifest.

No network inputs means no seed/checkpoint changes. Inputs must select exactly
`main` or `test` and supply `expected_genesis` matching that network's assertion in
the replayed `src/kernel/chainparams.cpp`. No trusted network values are invented.

For seeds, supply `seeds`, an explicit nonempty array of numeric, globally routable
IP endpoints with ports (`IP:port` or `[IPv6]:port`). This is an operator-reviewed
bootstrap list, not evidence that peers are online or on the right chain. The
replayed `contrib/seeds/generate-seeds.py` generates the selected fixed-seed array
without contacting peers. The other network's array remains unchanged. DNS seed
configuration, consensus activation times, and other chain parameters are untouched.

For a checkpoint, supply `checkpoint` with:

- `height`, `hash`: an explicitly chosen positive block height and lowercase hash.
- `confirmation_depth`: an explicit positive number of blocks required above it.
- `cli`, `cli_sha256`, `datadir`: an existing trusted Lotus CLI binary, its reviewed
  SHA256 checksum, and an existing datadir for the running node.

Online verification requires the orchestrator's explicit RPC opt-in. Only
`getblockchaininfo`, `getblockhash`, and `getblockheader` are allowed, using the
selected chain. The node must have finished initial block download. Both genesis
and checkpoint raw headers must be exactly 160 bytes; their Lotus three-layer
SHA256 hashes and encoded heights are independently checked. The checkpoint must
extend the existing checkpoint list. Genesis identity, checkpoint identity and
confirmation depth are rechecked before candidate changes are returned. No eCash
crawler or Electrum checkpoint scripts are invoked.

Normalized configuration replaces private CLI/datadir details with `verification`
evidence containing `first` and `rechecked` observations, including raw headers,
network, heights and hashes. Persist it as `daemon/release-network.json` alongside
the candidate. Subsequent offline checks validate this evidence and reproduce the
same patch without contacting a node. Evidence records the preparation-time
observations: it does not claim present freshness, independently validate proof of
work or the entire ancestry, or replace operator trust in the selected node.
Refresh from explicit CLI inputs when a fresh observation is required.

Run synthetic validation with:

```sh
python3 -m unittest discover -s daemon/tests -p test_prepare_network_release.py -v
```

The tests cover hash/height validation, offline reproducibility, network scoping,
reorg/identity/depth failure, RPC opt-in, and seed input validation. No live node was
contacted to validate these tools and no new checkpoint or seeds have been selected.
