# First reviewed consolidation: HTTP response ownership

Candidate only; active source pins, main/master and tags are unchanged.

| Item | Before | After | Validation |
|---|---|---|---|
| Shared commits | 378 | 377 | All original owners mapped in COHORT-A-STATE.json |
| Native commits above shared | 153 | 153 | No source changes |
| Shared endpoint tree | 2c6b9bc763382dd3236952d5c8c66efe77f10241 | identical | PASS |
| Full native endpoint tree | a576cd04fc505e68069809d0bc00ec8ed96b4955 | identical | PASS |
| Corrected introducing Beast owner | original86 | df81e5f557bf3201e9773ad6495b9f6f76559b62 | Release build, 88 unit cases, interface_http and four large-body HTTP combinations PASS |

Original98 (`221e9074648e7237d0836e334e4aead9edd744cb`) is folded into Beast owner86. All four source files survive. The original repair uses a compression helper introduced later: the earlier owner retains inline compression, and owner95 retains its helper extraction while carrying response ownership forward. COHORT-A-ADAPTERS.json records these context adaptations. The new tree at original98 is exactly `277e54c91ddc3009b42aec5247aa791002c08552`; all subsequent checkpoint trees match their original owners. This is a history-only reduction; it claims no new speedup.

Shared candidate: `8267586b0d74d4bc4a32a5f0282f299ecbeaef5e`, pushed to `givelotus/bitcoin-abc`, branch `consolidation/ecash-http-body-repair-20261023`.
Native candidate: `4c2007d09211113f9d2ce459e1787aa5b582b4bb`, pushed to `givelotus/lotusd`, branch `consolidation/http-body-repair-20261023`.

Full original reachable histories remain in the verified input recovery bundle. The verified incremental candidate bundle and remote backups are recorded in COHORT-A-PRESERVATION.json. No intentional exclusions. The rest of the ownership audit remains open; the initial19 candidates are not19 approved whole-commit deletions.

Build evidence: `benchmark-results/20261023/repair-cohort-a-owner86/`; exact receipt in `daemon/.local-artifact-archive/commit-regressions/repair-cohort-a-owner86/point-086/BUILD.json`. Release flags disable wallet, Chronik, H2, WebTransport and jemalloc. Functional evidence: COHORT-A-HTTP-0.log and COHORT-A-HTTP-ROUNDTRIP/RESULTS.json. These checks do not establish optional-feature or cross-platform coverage. Existing native endpoint evidence applies only through its exact unchanged tree, rather than a newly rebuilt endpoint in this cohort.
