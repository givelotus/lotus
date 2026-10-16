# Next inherited functional batch: final cd8d5140ec

Prepared from monorepo `e5bb81c0` for native
`cd8d5140ec7fce7da9a4e2a5a8b5d803ed4dc3f5`. **Not run.**
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

All292functional script identities were compared with frozen63c. The only
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
