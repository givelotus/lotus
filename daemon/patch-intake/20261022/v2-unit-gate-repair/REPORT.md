# Point 527 V2 unit-gate repair

Status: repaired correctness gate; point 527 remains **UNMEASURED**. No progression runner, benchmarks, production data, consensus change, or interpreter suppression was used.

| Causal global ID | Owning mailbox | Failure and repair | Validation |
|---|---|---|---|
| 375 | v2/001 | Production gates high-bandwidth body pushes on negotiated SENDINVSHORT features. Two fixed-tick test fixtures still set only the handler's legacy flag. Negotiate the actual capability in both fixtures; retain 16 body pushes, known-inventory exclusion and original assertions. | v2_protocol_handler_tests passes |
| 377 | v2/003 | The XPI currency change requires five amount-bearing script JSON vectors to express the same atoms in six-decimal XPI. Replace 123450000000.00 XEC with 12345000.000000 XPI; signatures, scripts, flags, expected errors and cases are identical. | script_tests passes |

The reported interpreter exception was a misleading first-throw diagnosis. A debugger trace continued 2,500 caught script-number exceptions. The next escaping exception came from `AmountFromValue` while parsing the stale amount vector; Boost then reported unknown type. Existing production interpreter error conversion works. No production interpreter edit is necessary or made. `throws.log.gz` records the complete trace; `throw_trace.py` and `throws.lldb` reproduce the diagnosis against the before binary. No UPDATE_JSON_TESTS generation was enabled.

Clean sequential temporary-index replay from ABC `1fb7db17c176cdea8a2c60d887891589382ee4e3` checks and applies **all 527** mailboxes, arriving at tree `1a554ffc949842a1243fb9f54ad2d16514f2fa24`. Both causal mailboxes also pass `git apply --cached --check` against their own original parents. Later mailboxes were not edited. Prior repairs in 040, 041, 062, 063, 075 and 096 remain intact.

The existing replay checkout is clean at `385b64d7e7e0666e2bfff9865ee831a3186795fd`, tree `1a554ffc949842a1243fb9f54ad2d16514f2fa24`. Old tip `73b7dbc180e532d13a1ecd5594cfcc5570311df6` is preserved at `refs/backup/grok-v2-unit-gate-before-20261022`; repaired tip is preserved at `refs/backup/grok-v2-unit-gate-repair-20261022`. `replay.bundle` is an incremental recovery bundle requiring the old source history, verified in the existing checkout. It is a local backup, not a pushed branch. `replay-commits.json` maps every V2 original/replayed commit and tree.

Validation:

- Existing native Release `test_bitcoin` rebuild: PASS (pre-existing documentation warnings and duplicate static-library linker warning remain).
- Direct `--run_test=script_tests,v2_protocol_handler_tests --report_level=detailed`: PASS, 41 cases, 248,698 assertions.
- Exact previous gate argv, read from the original unit.log, executed directly with no runner edits: PASS, 951 cases, 4,898,431 assertions; 235 cases remain excluded by that unchanged gate configuration.
- Full 527-mailbox clean application/check: PASS, same final source tree.

`gate-result.json` records exact binary/config hashes and argv. `artifact-hashes.json` records evidence hashes. Compressed logs are standalone gzip artifacts. `amount-vector-proof.json` proves the five unchanged atom commitments. The source delta from the preserved old endpoint is exactly the two test fixture files; there is no production behavior change in this repair.
