# BCHN disconnected-mining RPC test race

This standalone test-only review mailbox applies directly to BCHN
`abd433abe04f74780744b9eac06731f3690ce68a`. It is outside selectable daemon
features and maintained manifests. It has no dependency on mining, mempool,
NNG or ZeroMQ patches, and does not change daemon behavior.

The existing helper waits for the first endpoint only. The test immediately
expects both endpoints to report RPC error -9, although the second socket
handler can still retain its connection. Wait for that endpoint with the same
helper before checking the unchanged errors. No timeout or assertion is relaxed.

Source commit: `029370ebe42a07ee9cc19aff55a1bb963c2c1504`. Expected tree:
`997734ce27472b34c55be37628c82961e6a88bc7`.

## Reproduce with actual nodes

`delayed_close_repro.py SOURCE` runs the actual functional test from the chosen
source directory. It uses transparent TCP proxies between real regtest nodes:
message payloads flow immediately, while close propagation is delayed three
seconds. The original test deterministically fails at its second-node assertion;
the fixed test passes under the identical schedule. All original assertions,
helper timeouts and RPC/node implementations remain intact.

Use a wallet-enabled BCHN build and a fresh isolated temporary directory:

```sh
python3 daemon/candidates/bchn-gbt-disconnect/delayed_close_repro.py \
  /path/to/original-bchn-source \
  --configfile=/path/to/build/test/config.ini \
  --tmpdir=/tmp/bchn-gbt-original-fresh
# Expected: exit 1, second-node "No exception raised".

python3 daemon/candidates/bchn-gbt-disconnect/delayed_close_repro.py \
  /path/to/fixed-bchn-source \
  --configfile=/path/to/the-same-build/test/config.ini \
  --tmpdir=/tmp/bchn-gbt-fixed-fresh
# Expected: exit 0, Tests successful.
```

For an instrumented build, also set
`UBSAN_OPTIONS=print_stacktrace=1:halt_on_error=1:log_path=stdout`.
Before/after results were demonstrated with native upstream C++ binaries
(only their CMake ZeroMQ default differs) and with the native Debug UBSan
MR 2174 binary, whose networking/RPC code is upstream. Ten ordinary fixed-test
UBSan repetitions pass. These are focused checks of the Python synchronization
fix; full Linux CI of this separate patch remains pending.

## Evidence and review

MR 2174's retried complete UBSan job succeeds. MR 2175 passes all 708 C++
cases and 190 functional cases, but fails this one test: its node1 GBT request
starts at `23:47:03.932715`, before the final peer's close at `.933306` and
disconnection at `.934139`.

See [full job and reproduction evidence](../../docs/evidence/bchn-ubsan-followthrough-final-20261014.json)
and [proposed upstream description](upstream-description.md). MR 2175's source
is unchanged; this independent test-fix source and submission await root review.
No external MR/comment/push was performed for this candidate.
