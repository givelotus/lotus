# Integrated compiler and authenticated VM validation — 2026-10-15

Offline review at immutable monorepo commit `c19e134d70a99af115c57661e2543b8ffd858182` (tree `74379dd054c3621eb4e735c96d757ffdddfd01f1`) and native commit `d4119718505d0bfbd358c97ac9bfb81aeb48b2da` (tree `b49617e51ac6d1c1135ba7a1d555514989a2e7b6`). This validates compiler tooling and VM invocation behavior; it supplies no transaction or block acceptance claim.

The source checkouts were isolated worktrees at `/private/tmp/lotus-v2-compiler-integrated-validation-20261015` and `/private/tmp/lotus-v2-native-compiler-validation-20261015`. Native output is in `/private/tmp/lotus-v2-native-compiler-build-20261015`. Neither owner checkout, main, running nodes, chain data nor release assets were changed. No compiler or native implementation changes were necessary.

## Results

| Gate | Result |
| --- | --- |
| `npm ci`, TypeScript build, complete `npm test` | 187 tests: 185 passed, 2 skipped, 0 failed/cancelled/todo |
| Native standalone VM CTest | 1/1 passed |
| Native `context_runner_test.py` | Passed signing modes, context mutations, missing SINGLE output, authenticated success membership, derived mint delta and FULL-only mint framing |
| Generated differential seed 79225 | 61 cases compared; 0 discrepancies |
| Frozen `corpus-v1.json` | 17 cases compared; 0 discrepancies |
| Frozen `authenticated-corpus-v1.json` | 10 cases compared; 0 discrepancies |
| Explicit handbuilt versus compiler signed Payment | 4 cases compared; 0 discrepancies |

All four differential runs have zero unsupported outcomes, inconclusive comparisons, operational errors and tool errors. The generated run includes 48 compiler arithmetic cases, three handbuilt parsing/VM cases, two signed Payment cases and eight signed linked-library cases. Signed linked Escrow, Payer and Receiver fixtures execute the same complete transaction bytes and resolved coins in both engines; invalid signatures and the wrong linked root reject.

The two skips are the separate eCash tests `pinned ABC executes hashlocks, branches, exact byte widths and clean stacks` and `real source predicates execute in exact pinned ABC interpreter`. `LOTUS_ECASH_NATIVE` was unset: these results establish no execution evidence for eCash. Python-backed compiler, wrapper, optimizer, gallery, token and linked tests ran with the requested virtual environment. The full suite also retained the existing CABI06 optimizer boundary disagreements: its 24 observations matched the checked-in golden exactly. Existing corpus/golden files were not regenerated.

The explicit handbuilt comparison signs each program's own authenticated transaction. `PUSH_32 owner CHECKSIG` and compiler Payment both accept their valid signature and reject its mutation, in Python and native execution. Their scripts, roots and charges differ: native accounting is 180 for the handbuilt form and 182 for compiler output. These are equivalent tested signature outcomes, not interchangeable commitments or exact cost equivalence.

## Reproduction and evidence

Use Node `v26.10.0`, npm `11.19.1` and Python `3.13.16` from `/private/tmp/lotus-v2-compiler-review-venv/bin/python`. Native configuration was:

```sh
cmake -S src/lotus_v2/vm_test \
  -B /private/tmp/lotus-v2-native-compiler-build-20261015 \
  -DLOTUS_SECP_LIBRARY=/private/tmp/lotus-v2-daemon-runtime-staging-20261015/build/src/secp256k1/libsecp256k1.a \
  -DCMAKE_CXX_FLAGS=-I/opt/homebrew/opt/boost/include
cmake --build /private/tmp/lotus-v2-native-compiler-build-20261015 -j2
ctest --test-dir /private/tmp/lotus-v2-native-compiler-build-20261015 --output-on-failure
```

In `tools/lotus-v2-compiler`, set these variables before running `npm ci`, `npm test` and `node test/differential/run.mjs NEW_OUTPUT_DIRECTORY 79225 [CORPUS_JSON]`:

```sh
export LOTUS_V2_PYTHON=/private/tmp/lotus-v2-compiler-review-venv/bin/python
export LOTUS_V2_NATIVE_VM=/private/tmp/lotus-v2-native-compiler-build-20261015/lotus_v2_vm_runner
```

The current runner supports `--context` and links signing, transaction and output code. Historical documentation describing an unsigned runner does not apply to this binary. The standalone native context test is `src/lotus_v2/vm_test/context_runner_test.py RUNNER tools/lotus-v2-reference`, invoked with the Python environment above from the monorepo root.

Evidence is under [`tools/lotus-v2-compiler/test/evidence/integrated-20261015`](../../tools/lotus-v2-compiler/test/evidence/integrated-20261015). It retains full npm/native logs, generated and frozen differential reports, CABI04 frontend/gallery/stateful observations, and the explicit handbuilt comparison script and report. Large JSON reports use lossless deterministic gzip; inspect with `gzip -dc PATH.json.gz`. Report process diagnostics are those emitted by the existing harness, not performance measurements or speedup evidence. `manifest.json`, source tree listings and `SHA256SUMS` identify exact inputs and artifacts.

Native runner SHA-256: `cbbd10248177e8e6a1dfab8624ff41680080405b57329f73cee2e6e6e7f48039`.

Native runner source SHA-256: `12bda1db31078a1fc3060694b0e8b5fce74c4c99b62ff02b2430458f4eda5f07`.

No network node was started. VM invocation success does not establish outer coin/lock validity, transaction acceptance, fee-floor validity, block connection or consensus deployment readiness.
