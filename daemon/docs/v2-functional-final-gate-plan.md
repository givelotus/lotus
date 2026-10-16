# Exact 63c5149944 functional gate plan

This plan covers native source `63c51499441ded6d0fe34d87ff43d53a14b1398f`
and monorepo base `aa0dccd4`. All **292 scripts / 319 registered variants** are
scheduled exactly once in **52 sequential batches**, with one script job at a
time. No functional batch has run under this plan. Earlier-pin smoke results
are retained separately and confer no passes here.

The [batch manifest](evidence/v2-functional-final-gate-plan-63c5149944/plan.json)
contains every script SHA256, expected variant identity, exact command array,
feature profile, outer timeout and disk budget. Its coverage check found 319
unique identities with no omissions or duplicates. All 317 source paths in the
existing inventory, including setup paths, and the runner hash match this pin.
Inventory classifications remain provisional scheduling guidance; a fixture
mismatch must be investigated, with original failures retained.

| Lane | Scripts | Variants | Batches | Prerequisite |
| --- | ---: | ---: | ---: | --- |
| Primary retained regression | 155 | 176 | 23 | Current Debug/Chronik/wallet profile |
| Primary fixture-sensitive regression | 119 | 121 | 16 | Same profile; attribute failures |
| SQLite storage | 1 | 1 | 1 | Wallet ON |
| Long resource | 5 | 6 | 5 | Separate disk/time allocation |
| Chronik plugins | 4 | 4 | 1 | Same-source plugins-enabled build |
| ZeroMQ | 1 | 1 | 1 | Same-source ZMQ-enabled build + pyzmq |
| Linux network/binding | 4 | 7 | 4 | Isolated Linux network environment |
| Linux USDT | 3 | 3 | 1 | Tracing build, BCC and BPF permission |
| **Total** | **292** | **319** | **52** | **No exclusions or manufactured passes** |

Ordinary batches contain at most eight registered variants and eight scripts.
Explicit script selection plus `--extended` covers variants beyond the default
40-second cutoff. The runner expands `TEST_PARAMS`; the manifest names the exact
expected receipts. Commands use `--jobs=1 --failfast --timeout-factor=2
--nocleanup`, a fresh root/cache/JUnit per batch, ports based at 44000, and an
1800-second outer limit. Historical timing data only guides packing; it is not
current performance evidence or a completion guarantee.

## Approved prerequisite setup

After the nine-node run terminated and its children exited, the owner approved
only `lotus-cli`, `bitcoin-wallet` and `protobuf-chronik` in the existing shared
build, with two jobs. They built successfully at exact 63c; source/configuration
were unchanged and the build window was released. Older c0ddb tools were not
reused. Immutable copies accompany the supplied daemon, SHA256
`7d86468e24d457eaf2bbac541cc33ddd422e8a481fee96c8e5b6c07e70de7d0e`, under
`/private/tmp/lotus-v2-functional-full-63c5149944-20261015/primary/build-frozen/`.

The Python3.13 interpreter initially lacked protobuf and websocket-client, and
`chronik_pb2.py` was absent. Approved setup generated that module and created a
fresh isolated Python3.13.16 venv with **protobuf7.36.2** and
**websocket-client1.9.2**. Generated-module import passed with matching generator
and runtime versions. [Prerequisite evidence](evidence/v2-functional-final-gate-plan-63c5149944/prerequisites.json)
records exact hashes, build logs and `pip freeze`. This is dependency readiness,
with no functional test result.

The next executable action, after plan review, is to export source with
`git archive` at exact 63c into the gate root, then derive a frozen generated
config by rebinding only `SRCDIR`, `BUILDDIR` and `RPCAUTH`. Preserve truthful
feature flags and copy generated protobuf into the frozen build's `test/`.
No full clone or full rebuild is needed. Then launch **batch-001 only**:

```text
abc-cmdline.py abc-invalid-chains.py abc-invalid-message.py abc-sync-chain.py
abc_feature_parkedchain.py abc_feature_persist_headers_time.py
abc_mempool_chainedtx.py abc_p2p_compactblocks.py
```

The manifest supplies its complete command and expected eight identities. Stop
for review after its result; later batches require the owner's continuation.

## Resource and environment gates

Disk inspection found approximately **5.15GiB free** before prerequisite setup;
post-setup measurements are retained in the manifest. No existing build or home
was deleted. Primary batches propose a 2GiB scratch cap with a **2GiB free-disk
floor**, requiring at least 4GiB before launch. A supervisor must monitor disk
and the outer deadline, clean up only its recorded process group, and preserve
failure/timeout logs before any approved cleanup.

`feature_pruning.py` explicitly warns of 4GB and 30 minutes to two hours. Its
batch, and the proposed wallet-pruning lane, require **at least 8GiB free** and a
three-hour outer allowance. They are currently disk-blocked, still scheduled,
and never counted passed. `feature_dbcrash.py` intentionally crashes nodes with
480-second RPC timeouts; it has its own three-hour batch. AssumeUTXO batches have
two-hour allowances. These allocations are proposed budgets, not measured bounds.

Plugins and ZMQ require separately approved same-source feature builds with
honest generated configs, appropriate Python packages, and enough additional
build storage. USDT needs Linux, `ENABLE_TRACING=ON`, Python BCC and actual BPF
permission. No current macOS skip can satisfy it. Binding tests need an isolated
Linux environment with the intended interface addresses; two require fixture
flags `--ihave1111` / `--ihave1111and2222`. `rpc_bind.py` retains all four variants
and uses fixed32171/32172; discovery fixtures also use31001. Assign1.1.1.1 and
2.2.2.2 only inside the approved isolated environment, with no external routing.
The framework port base alone is insufficient isolation for these tests.

Twenty-one IPC setup entrypoints remain separate paired-client gates. The
manifest maps nineteen to matching Chronik-client TypeScript files and the
remaining two to ecash-lib/Agora integration consumers. Use exact lockfile/build
hashes, `BUILD_DIR` pointing to the same-profile frozen build and venv Python
first on `PATH`; require consumer assertions, IPC completion and both exits.
Three setup entrypoints require plugins. Four helper modules are inventory,
never standalone test passes.

Any substantive failure pauses progression without weakening assertions. Record
skip77, timeout, resource refusal and unrun remainder explicitly. Full inherited
functional acceptance needs all319 variant receipts; native V2 chain, VM,
quorum/finality and asset acceptance remain separate.

## First approved batch result

At exact native `63c51499441ded6d0fe34d87ff43d53a14b1398f`, batch001
exited1 after128.48seconds: **2passed,1failed,5notrun due failfast**.
The five runner skips are unexecuted variants, with no feature exclusions.
`abc_p2p_compactblocks.py` and `abc_feature_parkedchain.py` passed.
`abc-cmdline.py:100` expects the upstream Bitcoin ABC user-agent brand;
retained peer version logs show `/Lotus:0.34.1(EB32.0; testnode-0)/`.
Its2MB restart passed `getexcessiveblock` before the brand assertion failed.
The existing EB2.0 and comment assertions must survive the fixture correction.

[Batch receipt](evidence/v2-functional-final-gate-plan-63c5149944/batch-001/results.json)
records all eight identities, exact source/config/binary provenance, raw log
paths and hashes, JUnit, resource supervision and empty final process group.
There was no deadline/resource termination or cleanup signal. Minimum observed
free space was4,603,490,304bytes; peak measured scratch216,354,816bytes.
All raw homes/logs remain at the recorded paths. No later batch ran.
Across the319variant plan there are2passes,1failure and316notrun.
Continuation is paused for review; only the failing script may be rerun after
review of its scoped fixture correction. These inherited regtest results do
not establish native V2 quorum or consensus acceptance.

### Reviewed fixture rerun

The separately authorized `abc-cmdline.py` rerun **passed** in18.07seconds
using unchanged frozen63c daemon/CLI/wallet binaries, fresh data, and reviewed
test-only commit `2e66cae1b2b8fbcb1d02744f29deec627c345278`. The sole source
change expects literal `Lotus` branding while retaining EB2.0/comment assertions.
Fixture SHA256: `bf6264844d11ca9dfd7492d482e03b32a90493c4d5a5a59af890d4444c479010`.
[Separate rerun receipt](evidence/v2-functional-final-gate-plan-63c5149944/cmdline-reviewed-rerun/results.json)
retains the exact binary/config/fixture hashes, JUnit, raw-log locations and
resource evidence. The final process group was empty; no termination signals
were needed. Root approved a3GiB launch allowance for this single case after
observing3.953GiB free; the2GiB free floor/scratch cap and1800second deadline
remained enforced. No existing artifacts were deleted. This allowance does
not authorize another ordinary batch. The original exact63c batch failure and
its counts remain preserved; the rerun uses the explicitly identified fixture
candidate and does not establish complete functional-suite acceptance.

### Five previously unrun variants

The separately authorized remaining-five run **passed all5** using unchanged
exact63c scripts and frozen63c binaries. Runner elapsed8seconds; supervisor
elapsed10.04seconds. Neither the two original passes nor the corrected
command-line fixture was rerun.
[Remaining-five receipt](evidence/v2-functional-final-gate-plan-63c5149944/batch-001-remaining-five/results.json)
records every case/source hash, JUnit, raw log locations and resource evidence.
Root approved3GiB launch minimum only for this five-case set, retaining the
2GiB floor/scratch cap, jobs1/failfast and1800second deadline. No signals were
needed and the final process group was empty. No subsequent batch ran.

The first eight identities now have passes across the documented scoped runs:
7with unchanged63c fixtures and1with reviewed branding correction. The original
command-line fixture failure remains recorded. There are311variants still
notrun; this evidence does not claim complete-suite acceptance.
