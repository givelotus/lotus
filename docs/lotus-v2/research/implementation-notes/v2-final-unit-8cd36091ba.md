# Pinned native unit acceptance — 8cd36091ba

On 2026-10-15, all three registered native C++ aggregates passed at exact source
`8cd36091ba9da0665ceab621ce42306963fcbfd9`:

| Aggregate | Registered runners | Result |
| --- | ---: | --- |
| `check-bitcoin` | 147 | 147 passed |
| `check-bitcoin-upgrade-activated` | 147 | 147 passed |
| `check-avalanche` | 11 | 11 passed |

The aggregate invocation exited **0**. These are 305 runner invocations, not 305
individual test cases. `check-bitcoin-util` is a separate Python utility target
and is excluded. The default aggregate also contains V2 wallet fixtures.

The upgrade-named runners change logging and the test-suite name; their CMake
commands supply no activation override. Their success does not establish a
separate activated consensus scenario.

## Build and provenance

The native clone at
`/private/tmp/lotus-v2-final-unit-native-8cd36091ba-20261015` has a real `.git`
directory and is pinned to the exact source above. Documentation was prepared in
a separate monorepo worktree based on `a3a821dc0ddf54aa5962468622dceb88b8cf41d0`.

Only approximately 10GiB was free at setup. The coordinator therefore authorized
an exclusive build window using the already configured, exact-revision
`/private/tmp/lotus-v2-daemon-runtime-staging-20261015/build-chronik-v2` rather than
duplicating its 10GiB Debug build. Source and configuration remained unchanged;
no reset, top-level reconfiguration or version mutation occurred. The shared
window was released immediately after evidence capture.

Configuration was Debug, Chronik ON, wallet ON, Qt/seeder/ZeroMQ OFF, Rust 1.93.0,
Python 3.13.16 and AppleClang 21, with two Ninja jobs. Actual native validation
and Chronik bridge compile commands both retain `DEBUG`, `DEBUG_LOCKORDER` and
`ABORT_ON_FAILED_ASSUME`, with no `NDEBUG`. No runtime switch disabled source logging or assertions. Source HEAD and tracked cleanliness were checked before
and after execution.

| Executable | SHA256 |
| --- | --- |
| `test_bitcoin` | `9cedc1f5d1d3f4d52050f89abd89ad3e91b556452788cba893c1505ac67e4d25` |
| `test-avalanche` | `4a6d33aff2fe90e3fd20d560c79f771243686aa55ff236ddd1a0fbfe7206464f` |

Immutable binary copies and all 305 raw runner logs were retained under the new
clone's `build-final-unit-evidence/`. Binary hashes matched before and after the
aggregate run. [Results and per-log hashes](../../../../daemon/docs/evidence/v2-final-unit-8cd36091ba/results.json)
and the [complete aggregate command log](../../../../daemon/docs/evidence/v2-final-unit-8cd36091ba/aggregates.log)
record the source, tool versions, compile flags and every runner verdict.

## Reproduction and scope

Using the matching configured Debug/Chronik build:

```sh
PYO3_PYTHON=/opt/homebrew/bin/python3.13 cmake --build build-chronik-v2 --target test_bitcoin test-avalanche -j2
PYO3_PYTHON=/opt/homebrew/bin/python3.13 cmake --build build-chronik-v2 --target check-bitcoin check-bitcoin-upgrade-activated check-avalanche -j2 -- -k0
```

This is shared native unit regression evidence. The full standalone V2 component
suite, funded network quorum/finality and later startup/shutdown recovery source
changes are separate gates. No production nodes, chain data or published assets
were changed.

Linking retained the known warning about dependency objects built for macOS26.5
against a26.0 deployment target. Tests ran on macOS26.6 arm64; this result makes
no earlier-macOS or other-platform portability claim.
