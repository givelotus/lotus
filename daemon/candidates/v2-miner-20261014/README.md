# V2 miner integration review packet

Prepared October 14, 2026. These six ordered mailbox patches are an isolated
review candidate for the `lotus-v2` monorepo branch. They change `miner/` only.
They are **not** in the selectable daemon V2 patch series and do not enable V2
network mining. Existing V1 remains the default; CLI `--protocol=v2` exits
before RPC or GPU setup, while the GUI shows an error panel without starting
mining. A V2 daemon job API and scheduler remain to be integrated.

## Exact source and prerequisites

| Item | Revision or tree |
| --- | --- |
| Exact V2 monorepo base | `beebcbde834fc23a1c4dd67209efd61d7c81fcf9` |
| V2 base miner tree | `5ee01fd06ae96ec5401cd85a2c5bd7af98018a65` |
| Maintained main miner source | `173182e4231657ea0acdf63c1f46ca8f31bf798d:miner` |
| Maintained main miner tree | `5c5e186a3d561357b03ea06c67311a1aa4646b49` |
| Integration commits | `147e610ca5652f97d819b3f35cb7669793ebb33e`, `4ffb631c92e63f2cf3825c26244d4508cdf53232`, `e66b11fccb01978fe4b431981aa0dfc8b4e3cd94`, `94e176f431270d076784ea489da2d3803eddd388`, `a3ea57d2fab17f24b3116fd9ecf91ddb3e6566ed`, `be149500cee5ee4c5c04d344137152ac1f0fa4a9` |
| Final miner tree | `ade6e7c5c3a3d6cf13d8d44eeec570d37729bf8d` |
| Final full source tree | `d4a2a9fabb3e75a6da73fbaaaf1eb34bee489114` |

Patch 0001 imports the exact maintained main miner subtree. Its 33 changed
paths are listed in [prerequisite-paths.tsv](prerequisite-paths.tsv). The source
work was originally carried by main commits `0c432838` (Rust 1.99 toolchain,
dependency and GUI compatibility, embedded V1 kernel, tests and native
packaging) and `caff29c9` (Linux CC0 license notices). The V2 branch's older
miner lacked those changes, so applying only the two V2 commits would omit their
tested source and packaging base. Patch 0001's resulting miner tree matches
`173182e4:miner` byte for byte. Current main at review (`1c2e3b4f`) has the
same miner tree.

Patch 0002 adds explicit V1/V2 selection and P04 CPU hashing. Patch 0003 adds
the bounded OpenCL work/BlockID kernel and CPU recheck of reported target hits.
Together their miner tree matches the original current-main miner review commit
`e75fa5e8a62b3545cdbcea8c809dbfa2c8a4023d:miner` exactly. Patch 0004
adds only deterministic GPU tests and documentation for the V2 branch. Patch
0005 defers GUI server/device setup until after persisted settings are read,
shows unsupported V2 and malformed-config errors in the GUI, and updates the
CLI message to reflect that the OpenCL kernel exists but the job API and GPU
scheduler are pending. It adds startup/protocol boundary tests.
Patch 0006 validates numeric settings before any CLI/GUI/server conversion or
OpenCL setup. Negative poll intervals or device indices and out-of-range kernel
sizes return errors; malformed CLI numeric text no longer panics. A malformed
GUI config or persisted interval shows the error panel without starting mining.

## Patch integrity and replay

| Ordered file | SHA-256 |
| --- | --- |
| `0001-Import-maintained-miner-subtree-for-V2-integration-r.patch` | `52db54a7c93834602a5d1ea9164453e5ecd5f0384484bfbb08c427d8d3f10bf8` |
| `0002-Prepare-explicit-V2-miner-protocol-selection-and-hea.patch` | `15e3b61c8eaeeec24ee997380572d6c525456718b25adcf83f6ae1683a9fdeed` |
| `0003-Add-bounded-V2-OpenCL-hash-batches-and-GPU-parity-ch.patch` | `3c82c6deff673b686a26bdac4a9d3327cc047d373298a4cb045f1e605c7ad3cf` |
| `0004-Expand-V2-GPU-parity-across-header-fields-and-nonce-.patch` | `260bd4803dd170f570a7e835679ae7a09efa113e98f7daf5157242996103e000` |
| `0005-Show-unsupported-V2-GUI-mode-without-initializing-mi.patch` | `9e482ebb6ce9034a5978ce9014cf535bfe15b503e68bfbffd8c76b15abfffe83` |
| `0006-Reject-malformed-miner-settings-before-startup.patch` | `69a18fa2f13232ccc5323a010f632470e5ce9c8f8dfe8f7477e120343cbf8bc9` |

In a fresh checkout of the exact base, apply these files in numeric order with
`git am`. A clean replay in `/private/tmp/lotus-v2-miner-patch-replay` matched
the final full source tree `d4a2a9fabb3e75a6da73fbaaaf1eb34bee489114`.
The isolated integration worktree is `/private/tmp/lotus-v2-miner-integration`,
branch `codex/v2-miner-integration`. Root integrated the six source commits into canonical `lotus-v2`, ending at
`41456528`; its miner subtree exactly matches the recorded candidate
`ade6e7c5c3a3d6cf13d8d44eeec570d37729bf8d`. The daemon series is separate.

## Validation on the exact integration tree

From `miner/`, Rust and Cargo 1.99.0 on macOS arm64 (Apple M5 Max):

| Command | Result |
| --- | --- |
| `cargo test --locked --workspace` | Passed: 17 unit tests, 3 device tests ignored by default; CLI and GUI compiled. |
| `cargo clippy --locked --workspace --all-targets -- -D warnings` | Passed. |
| `cargo fmt --all -- --check` and `git diff --check` | Passed. |
| `cargo test --locked -p lotus-miner-lib -- --ignored --nocapture` | All 3 executed and passed on Apple M5 Max: existing V1 kernel compilation, V2 independent-vector/nonce/target parity, and expanded V2 header/batch corpus. |
| `cargo run --locked -q -p lotus-miner-cli -- --protocol v2 --config /private/tmp/lotus-v2-miner-no-config` | Exited 1 with the intended V2 job/scheduler integration error before RPC or GPU setup. |
| `cargo run --locked -q -p lotus-miner-cli -- --config /private/tmp/lotus-v2-miner-no-config --mine-to-address dummy --kernel-size=bad` | Exited 1 with a numeric parse error, without a panic. |
| Same command with `--kernel-size=-1` | Exited 1 with a range error, without GPU setup. |

The new boundary tests check the V1 configuration default, invalid protocol
deserialization, CLI V2 refusal, and GUI V2 refusal before server/device setup
even when the value comes from persisted GUI settings. An invalid GUI config
also remains an error state instead of silently starting V1 mining.
Patch 0006 tests negative/out-of-range numeric configuration, malformed CLI
numeric input, and malformed GUI configuration and persisted numeric state. The
server checks the same bounds before building a miner.

The expanded corpus independently varies ChainID, parent ID, bits, timestamp,
version, size, height, transaction root and state root. It compares every GPU
digest with CPU tagged BLAKE3 across batches of 1, 2, 7 and 16 nonces, including
u32 carry and the u64 end. It checks inclusive exact targets and the immediately
lower little-endian target. The separate P04 vector test includes its base
nonce, nonce + 1 and `UINT64_MAX`. GPU test success establishes actual
kernel execution on this device, not a measured hash rate or block acceptance.

## Remaining integration gates

Use a versioned, explicit P04 candidate profile and development ChainID for
development tests; final production values are a launch gate. Define and test
the V2 daemon job/template schema, chain identity, stale-job handling, permitted
time and coinbase mutations, complete transaction/state/size commitments, and
submission validation. Wire a scheduler to the existing bounded GPU hash API
without reusing V1 job parsing. Test cross-device GPU/CPU parity, V1 regression
behavior, pool/template mutation, and a GPU-mined disposable development block
accepted by an independent CPU validator and daemon. No V2 daemon job API,
accepted block, live mining or production network parameters are claimed here.

## Root integration review

Root reran the final 17 workspace tests, strict Clippy and formatting checks.
The three device tests also passed during root review of the kernel tree;
the subsequent startup correction changes no kernel bytes. Root identified
the malformed-numeric-config panic and reviewed its patch 0006 correction
before integration. The original main checkout and running miners were untouched.
