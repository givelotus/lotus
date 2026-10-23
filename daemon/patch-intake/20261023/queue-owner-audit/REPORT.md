# Mixed owner377: RPC queue and peer-capability reversals

Status: source finding verified; queue-only control preserved, unintegrated, build and timing gates pending. No claim that a measured regression is fixed.

The original377 commit (`77bc9fb0c949479471c27079c0a911a9fc58b4b2`) does more than its RPC commit-owner subject describes. Relative to parent376 (`e48c87338c5282d368858ccfeb1561fbf92d9335`) it also:

- Removes `TXRELAY_HIGH_BANDWIDTH` from the private capability flags and their protocol documentation.
- Stops deriving high-bandwidth eligibility from the remote peer's advertised capability.
- Sets the private handler's high-bandwidth state from local `-highbandwidthtx` at initialization/VERACK.
- Uses ordinary BIP152 high-bandwidth state or NoBan permission as alternatives to explicit private-wire capability in the push path.
- Removes/changes associated peer-capability tests.

The capability originates in shared owner267 (`b1531b4038`, short-id announcement work). These are factual source differences, not yet a finding about which change causes the observed throughput or synchronization symptoms. A 376→377 timing difference cannot be attributed solely to the queue.

The isolated control `55756f6e98ae8ba43f1b4494f3714db7779a7440` keeps all nine queue/documentation/lifetime/callback files byte-identical to377, but restores the four peer-capability production files and two related test files byte-identically to376. [Exact file ledger and input preservation](CONTROL.json), [queue-only delta from376](QUEUE-ONLY.diff), [restoration relative to377](CONTROL-RESTORATION.diff), [complete control commit export](CONTROL.patch).

The original377 input ref, full reviewed input history and all original hunks remain preserved. The control does not replace the reviewed shared/V2 branches or any submodule pin. Both the control and original377 must pass their relevant queue/callback/peer tests before the paired controls run. Compare376→control to measure the queue with peer behavior held equal, then control→original377 to measure the peer changes with the queue held equal. Do not silently exclude these hunks from a final repair: record any eventual ownership relocation or production correction explicitly.

The broader matched ABC progression is [here](../../../../benchmark-results/20261023/commit-regressions/shared-range-progression/TABLE.md). It records76 successful samples and5 failed setup samples; failed cells are not credited a rate.

## Correct the stale fixture, not the peer rule

Adding the existing peer/callback suites to the next build gate exposed two failures at375: `single_tx_relays_wait_for_the_relay_tick` expects16 pushed transactions but sets only local handler state, without advertising the required private capability. Another case in the same file already uses the correct wire negotiation. The first continuation stopped at this gate; it launched no further timing stages.

The fixture now sends SENDINVSHORT with the advertised capability, following that existing case. The16-push expectation, zero-push negative scenarios,16 total announcements and known-inventory exclusion all remain intact. The expanded127-case gate passes. [Exact test change](FIXTURE-REPAIR.diff), [unit evidence](FIXTURE-UNITS.log), [test-only companion identities/preservation](FIXTURE-CONTROLS.json).

These companions change only `src/test/v2_protocol_handler_tests.cpp`:375=`fb1e79a93ec68564b8952a1fb562bf1f3559e101`,376=`21e068ea3a98685899a0ffef3ab3708c55a03b5f`, queue-only=`94453bdd7d8a681d6a872df85366f370bfa78089`. They are explicit unmerged fixups targeting capability owner267, not a change to the active review stack. Their production source equals the corresponding numbered prefix/control exactly. The successor continuation records actual companion SHAs in every affected sample and stops on any build/unit gate failure. Its state is `benchmark-results/20261023/commit-regressions/CONTINUATION-FIXTURE.json`.
