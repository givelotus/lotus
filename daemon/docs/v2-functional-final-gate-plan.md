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
