# Next inherited functional batch: final cd8d5140ec

Prepared from monorepo `e5bb81c0` for native
`cd8d5140ec7fce7da9a4e2a5a8b5d803ed4dc3f5`. **Batch002 executed; continuation paused after failure.**
Quorum currently owns the heavy window; execution requires its release and
root authorization. No build or functional node was launched during preparation.

## Frozen inputs

[Preparation receipt](evidence/v2-functional-final-cd8d5140ec/preparation.json)
contains exact archive/config/script/binary hashes and full command/environment.
A new source archive and immutable binary copies reside under
`/private/tmp/lotus-v2-functional-final-cd8d5140ec-20261015`.
The daemon, CLI and wallet tool match supplied final-pin `provenance.json`;
no older binary is reused. Debug, Chronik and wallet features remain truthful.
The validated Python3.13 venv is reused with protobuf7.36.2 and
websocket-client1.9.2; its freeze is retained. The generated Chronik module
is reused because the protobuf source is unchanged between pins.

The source contains295top-level Python files:292registered functional scripts
and3non-test helpers (`combine_logs.py`, `create_cache.py`, `test_runner.py`).
[Registered-script comparison](evidence/v2-functional-final-cd8d5140ec/registered-script-comparison.json)
records both pin hashes for each of the292registered identities. The only
changed script is `abc-cmdline.py`, the reviewed literal Lotus branding fix;
its EB2.0/comment assertions remain intact. Runner and protobuf sources are
unchanged. All eight selected scripts retain their original inventory hashes.
Original first-batch failure, reviewed fixture rerun and remaining-five receipts
remain preserved in the63c evidence directory. Their passes are not transferred
to this final binary pin.

## Next bounded action

Select existing manifest batch002: eight previously unrun primary variants,
including its existing extended selection. No first-batch identity is repeated.

```sh
/private/tmp/lotus-v2-functional-full-63c5149944-20261015/primary/venv/bin/python3 /private/tmp/lotus-v2-functional-final-cd8d5140ec-20261015/build-frozen/test/functional/test_runner.py --jobs=1 --failfast --extended --timeout-factor=2 --nocleanup --tmpdirprefix=/private/tmp/lotus-v2-functional-final-cd8d5140ec-20261015/batch-002/runs --cachedir=/private/tmp/lotus-v2-functional-final-cd8d5140ec-20261015/batch-002/cache --junitoutput=/private/tmp/lotus-v2-functional-final-cd8d5140ec-20261015/batch-002/results.xml abc_p2p_version_timestamp.py abc_rpc_excessiveblock.py abc_rpc_mocktime.py abc_wallet_dumpcoins.py abc_wallet_standardness.py example_test.py feature_abortnode.py feature_addrman.py
```

Set `TEST_RUNNER_PORT_MIN=44000`, `BITCOIND` and `BITCOINCLI` to the new
frozen binaries and `PYTHONPATH` to its `build-frozen/test` directory as
recorded in the receipt. Use fresh batch002 run/cache/JUnit paths, jobs1,
failfast,1800second outer deadline,2GiB scratch cap and2GiB free-disk floor.
Require4GiB free at launch; the earlier3GiB exceptions applied only to their
explicitly approved cases. Latest preparation measured5,259,216KiB
(approximately5.02GiB) free. Recheck at launch; no existing homes/builds
were removed. Historical timing sum22seconds is only a scheduling hint.

A supervisor must record and clean up only its owned process group on deadline
or resource refusal, retaining failure logs. Require JUnit to contain exactly
the eight registered identities and distinguish failfast-notrun from feature
exclusions. Stop on substantive failure; no following batch is authorized.
Inherited regtest results do not establish native V2 consensus/quorum acceptance.

## Batch002 result

Exact final-cd8 batch002 exited1 after12.02seconds: **2passed,1failed,
5notrun due failfast**, with no feature exclusions.
`abc_wallet_standardness.py` and `feature_addrman.py` passed.
`abc_rpc_excessiveblock.py:61` retains an upstream literal Bitcoin ABC brand
assertion with EB2.0/comment structure; it failed after the RPC update.
The five unexecuted variants are explicitly named in the
[batch receipt](evidence/v2-functional-final-cd8d5140ec/batch-002/results.json).
Original source assertions are preserved; no correction or rerun followed.

The supervisor enforced its4GiB launch check,2GiB floor/scratch cap and
1800second budget. No signals or resource/deadline refusal occurred; final
process group27241 was empty. Raw homes/logs remain at receipted paths.
A broad port probe encountered unrelated existing50415, but the shell
continued and launched the supervisor despite that probe failure. This
preflight enforcement mistake is recorded explicitly; selected tests reported
no bind error and their actual configured ports are retained in the receipt.
No unrelated process or existing home was modified. No later batch ran.

At this final binary pin there are2variant passes,1failure and316notrun.
Historical63c passes remain separate. Substantive failure pauses progression
until root review; complete-suite acceptance has not been established.

### Reviewed RPC fixture rerun

The separately reviewed `abc_rpc_excessiveblock.py` candidate
`dcb64ada9315ab2e4f17bf2c28140e52b3b8c548` **passed** using the same frozen
cd8d binaries and fresh data. Its three literal brand prefixes now expect
Lotus, preserving EB2.0/13.0/13.1 precision, comment and RPC value assertions.
Fixture SHA256: `a0d58cc800af977e1654a275f2f3e06f47e9132051fce4392438ccce662ea035`.
[Separate rerun receipt](evidence/v2-functional-final-cd8d5140ec/rpc-eb-reviewed-rerun/results.json)
retains exact hashes/JUnit/logs and actual port mapping. The supervisor took
4.02seconds and exited0 with an empty process group and no signals/refusal.
Disk and seed0 port checks now fail closed within the supervisor before
launch. The original batch failure remains preserved. Remaining five
failfast-unrun identities were not launched; no further batch is authorized.

### Remaining five result

All five previously unrun batch002 variants **passed** on unchanged frozen
cd8 scripts/binaries, in10.03seconds supervisor elapsed.
[Remaining-five receipt](evidence/v2-functional-final-cd8d5140ec/batch-002-remaining-five/results.json)
records exact identities, script/binary/config hashes, JUnit, retained raw logs
and actual ports. Its same-process supervisor failed closed on4GiB launch
disk and framework seed0..4/node0..7 port checks, with2GiB floor/scratch cap
and1800second deadline. No signals/refusal occurred; process group29075
was empty. Prior two passes and reviewed fixture were not rerun.

The final-cd8 batch002 identities now pass across scoped receipts:7with
unchanged fixtures and1with the reviewed fixture candidate. The original
branding failure is preserved;311of319variants remain notrun at this pin.
Historical63c passes remain separate. No broader batch has been launched
or authorized; complete functional acceptance remains outstanding.

## Prepared continuation automation (not executed)

[Continuation manifest](evidence/v2-functional-final-cd8d5140ec/primary-continuation.json)
and [supervisor](evidence/v2-functional-final-cd8d5140ec/run-primary-batches.py)
prepare ordinary primary batches003–040:38batches/282unique variants.
No first- or second-batch identity is selected; older63c passes are not final-pin
passes. The supervisor defaults to dry-run and requires an explicit inclusive
`--through` endpoint plus `--execute` after owner authorization. It refuses
existing batch output directories, preserving prior receipts without deletion.

Next proposed command, from this document worktree:

```sh
/private/tmp/lotus-v2-functional-full-63c5149944-20261015/primary/venv/bin/python3 daemon/docs/evidence/v2-functional-final-cd8d5140ec/run-primary-batches.py --start batch-003 --through batch-003 --execute
```

Remove `--execute` to inspect commands without launching nodes. Batch003 has
`feature_anchors.py`, `feature_asmap.py`, `feature_blocksdir.py`,
`feature_config_args.py`, `feature_dirsymlinks.py`, `feature_fastprune.py`,
`feature_filelock.py`, `feature_help.py`. Exact runner invocation/environment
is in the manifest; it retains jobs1/failfast/extended, fresh cache/JUnit/run
paths and timeout-factor2. Its scripts require the existing wallet/CLI-enabled
Debug profile and ordinary filesystem locking/symlink support, with no
plugin/ZMQ/USDT dependency. Source inspection finds maximum2nodes per script.
`feature_asmap.py`'s8333value is address-manager test data, not a listener.
`feature_config_args.py` uses127.1.1.1 for RPC argument-log coverage;
macOS fixture behavior remains an actual test result, never presumed passed.

Before each authorized batch, the same supervisor verifies binary/config/runner
and selected source hashes,4GiB launch disk, and initial framework port slots
for every possible timing-sorted script/seed pairing. Port mapping is
classbase44000/47000/50000/53000/56000 plus64*seed+node. It uses the maximum
constant `self.num_nodes` found in that batch and fails closed if this count
cannot be resolved. Batch019's `wallet_import_rescan.py` is explicitly
unresolved and will stop for port review, remaining pending. These checks
cover framework initial allocation; scripts' unusual endpoint overrides need
source review before their batch is authorized. They never alter existing
listeners or reserve ports against unrelated later processes.

Per batch:<=8variants,1800second outer budget,2GiB scratch cap/free-disk
floor and bounded50000file resource scan. The supervisor requires exact JUnit
identities and stops on any failure, skip, resource/preflight refusal, missing
JUnit or owned process requiring cleanup. It cleans only its recorded process
group with bounded INT/TERM/KILL escalation, retains logs and supervisor
receipts, and never automatically bypasses a stopped batch. Skip reasons
require review; failfast-notrun cannot become a feature exclusion. Disk is
rechecked after terminal cleanup as well as before each next launch.

Long resource batches041–045 remain separate pending gates: pruning needs
at least8GiB free and its proposed three-hour allowance; dbcrash/assumeutxo
retain their separate budgets. Plugin046 needs an honest plugin build and
dependencies; ZMQ047 needs an honest ZMQ build/Python package. Linux
network048–051 needs isolated interfaces and its explicit fixture flags,
USDT052 needs Linux tracing/BCC/BPF permissions. All12nonordinary batches
and their exact variants remain pending in the manifest, not excluded or
passed. SQLite batch040 remains a primary pending gate.

Preparation verification compiled the supervisor and dry-ran batch003 without
nodes, and checked282unique ordinary variants plus12pending nonordinary
batches. Cache owner currently holds the build/test window. No continuation
execution has been authorized or launched.

The JUnit parser treats both `<failure>` and `<error>` as failed cases, retaining
the original element kind. Skips stay distinct and require review. Six focused
synthetic-XML checks passed: pass/failure/error/skip, nonzero runner exit despite
all-pass cases, and identity mismatch.
[Parser check receipt](evidence/v2-functional-final-cd8d5140ec/supervisor-parser-check.json)
records the exact supervisor/test hashes. No child process or node was launched;
explicit range authorization and owner resource release are still required.
