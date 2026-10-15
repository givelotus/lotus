# Doged on Bitcoin ABC `33ae885a`

Checked 2026-10-15. This is isolated candidate evidence; the shared ABC pin,
Doged release manifest, production nodes, and published assets remain unchanged.

The complete maintained 174-patch Dogecoin series replays on
`33ae885a5ba7c3f71a7b6a6d0e709d5ec6eee503` with provenance verification:

| Result | Identity |
|---|---|
| Candidate source HEAD | `7fa197c11b8f0a0cbca51ad68cc654105143e3c7` |
| Candidate source tree | `8e9d6eaa7a67c0753641dcebfee182e8c010efe5` |
| Exact ABC base | `33ae885a5ba7c3f71a7b6a6d0e709d5ec6eee503` |
| Chronik provider tree | `84b19eab61f15c7887f12d1139026f3323d57de6` |

On arm64 macOS, a standalone ordinary clone configured with CMake/Ninja and
compiled `doged`, `doge-cli`, `test_bitcoin`, `test-avalanche`, and `check-pow`
with in-process Chronik enabled. The configure selected Qt and ZeroMQ off,
Chronik on, wallet on, Rust 1.93.0, and Python 3.13. All 543 build steps passed.
The linked-worktree configure failure was upstream CMake's `.git`-directory
assumption; the successful build used a regular clone and made no source fix.

Native test results:

- `test_bitcoin`: 757/757 cases, 32,918,581 assertions passed.
- `test-avalanche`: 144/144 cases, 17,717,531 assertions passed.
- Dogecoin proof-of-work checks passed.
- Functional checks passed for AuxPoW, activation boundaries, P2P inventory
  download, raw mining, transaction ordering, and Chronik block/header/reorg
  behavior. The Chronik Python requirements and generated protobuf bindings
  were installed/generated under temporary directories only.

This does not establish full Dogecoin mainnet-tip synchronization, a complete
reindex, live Avalanche quorum behavior, or bit-for-bit reproducible binaries.
The checked-in release workflow and component manifest still select the
historical Doged source; do not publish this candidate as `doged-v0.4.1` until
the source selector/manifest is deliberately prepared and reviewed. ABC's
inherited Guix machinery has not yet been adapted and run for this Doged
candidate. Current reproducible-binary evidence applies to the Lotus Guix
workflow only.

The source replay and export candidate are retained under
`/tmp/lotus-abc-refresh-final-20261015`; the native build and test trees are
under `/tmp/lotus-abc-33ae-doged-*`. Recreate them with the commands and
manifests in [coordinated ABC refresh](abc-refresh.md) and the maintained
[Dogecoin patch series](../patches/doged/README.md).
