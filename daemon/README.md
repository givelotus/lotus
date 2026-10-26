# Daemon source submodules

All daemon source checkouts live under `daemon/`; exact commits and trees are
locked in [sources.json](sources.json). Setup uses Git submodules and never
replays an archived patch series.

| Series | Path | Repository |
|---|---|---|
| `v2` | `lotusd` | `givelotus/lotusd` |
| `v1` (default) | `lotusv1` | `givelotus/lotusd` |
| `ecash` | `ecashd` | `givelotus/bitcoin-abc` |
| `doged` | `doged` | `givelotus/doged` |
| `bitcoin` | `bitcoind` | `givelotus/bitcoind` |
| `bchn` | `bitcoincashd` | `givelotus/bitcoincashd` |

```sh
make -C daemon setup SERIES=all
make -C daemon source-verify
make -C daemon build SERIES=v1
```

Private repositories require authenticated Git access. Select Python 3.13 for
Chronik builds, for example with `PYO3_PYTHON` and `-DPython_EXECUTABLE=...`.
Builds write to `daemon/.build/<series>`, leaving source submodules clean.
`make -C daemon help` lists source maintenance commands.

The selected Doged source is the original implementation, not the unfinished
current-ABC replay candidate. Source selection and inherited validation evidence
are recorded in [stack-review.json](stack-review.json). Historical consolidation
evidence is preserved outside the repository in `~/repos/archive/`.
Retained experiments are not release or production approvals.

Historical `workspace-*` directories and patch mailboxes remain preservation
material. The running mainnet node's workspace and chain data are untouched.
See [source maintenance](docs/adding-patches.md) for the current workflow.
