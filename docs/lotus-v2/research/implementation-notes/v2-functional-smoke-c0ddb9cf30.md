# Pinned inherited functional smoke — c0ddb9cf30

The bounded smoke completed on 2026-10-15 at exact native source
`c0ddb9cf307a97a43309b72cffef383c29e559e8`: **8 scripts / 10 registered
invocations passed**, with zero failures, skips or timeouts. Runner exit was 0;
wall time was 32.49 seconds. Eleven framework self-tests also passed and are
counted separately.

| Script / registered variant | Result |
| --- | --- |
| `p2p_compactblocks_blocksonly.py` | Passed |
| `abc_p2p_version_timestamp.py` | Passed |
| `mempool_accept.py` | Passed |
| `mempool_reorg.py` | Passed |
| `feature_blocksdir.py` | Passed |
| `feature_reindex.py` | Passed |
| `wallet_createwallet.py` | Passed |
| `wallet_createwallet.py --usecli` | Passed |
| `wallet_createwallet.py --descriptors` | Passed |
| `wallet_sqlite_v2.py` | Passed |

This is **7 inherited scripts / 9 invocations**, plus one bespoke SQLite storage
script. The exact-source inventory remains 292 scripts / 319 invocations;
284 scripts / 309 invocations were not run by this gate. These checks exercise
inherited regtest subsystems and wallet storage. Native V2 chain, VM, assets,
quorum and finality acceptance remain separate gates.

## Frozen inputs and isolation

The supplied daemon SHA256 is
`5c05a1acf36a91c690505ca08bd291d9fd2e985fd483f9db08386c712c1f8bfa`.
The previously absent `lotus-cli` and `bitcoin-wallet` targets were built at the
same source, with two jobs, during an authorized exclusive build window. Their
immutable copies and hashes are recorded in the [manifest](../../../../daemon/docs/evidence/v2-functional-smoke-c0ddb9cf30/results.json).
The offline tool was available; the selected tests use wallet RPCs and the
registered CLI variant.

Unchanged scripts were frozen in a new native clone at
`/private/tmp/lotus-v2-functional-smoke-native-c0ddb9cf30-20261015`.
The existing generated config was copied into a new frozen build layout with
only `SRCDIR`, `BUILDDIR` and `RPCAUTH` paths rebound. All component flags remained
identical: wallet, CLI, wallet tool and Chronik ON; plugins and ZeroMQ OFF.
A generated-style runner link reads that config. Explicit `BITCOIND` and
`BITCOINCLI` overrides select the immutable copies. Source and binary hashes
were rechecked after execution; no test or source was edited.

The explicit eight-script selection bypassed the runtime cutoff and expanded to
all ten expected variants. Options were `--jobs=1 --failfast --timeout-factor=2
--nocleanup`, with a 1800-second outer limit. Explorer processes had stopped;
the quorum owner approved coexistence with its isolated single-node seed.

Fresh test homes/cache used
`/private/tmp/lotus-v2-functional-smoke-c0ddb9cf30-20261015/` and
`TEST_RUNNER_PORT_MIN=44000`. Runner seeds were 0–9. Generated P2P ports were
44000–44576, RPC 47000–47576 and configured Chronik 50000–50576; actual loopback
binding log entries are retained in the manifest. Ports 10604, 10605, 8331 and
the separate seed's 55550 were unused. Discovery, DNS/fixed seeds, NAT-PMP and
automatic external connections were disabled by framework configuration.

All test nodes shut down normally; the final process scan found no remaining
smoke child daemons. Passing homes/cache and raw node logs remain at the isolated
artifact path for review. The manifest records their paths and SHA256 hashes;
large node logs and databases are not tracked. Production data and published
assets were untouched.

[Runner log](../../../../daemon/docs/evidence/v2-functional-smoke-c0ddb9cf30/runner.log),
[JUnit results](../../../../daemon/docs/evidence/v2-functional-smoke-c0ddb9cf30/smoke.xml) and the
[exact command, provenance, ports and log manifest](../../../../daemon/docs/evidence/v2-functional-smoke-c0ddb9cf30/results.json)
preserve this run. Earlier failures remain in the
[historical functional audit](v2-abc-functional-audit.md).
