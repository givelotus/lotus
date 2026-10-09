# Upstream contribution plan

Status: local candidates only. No external submission or message is authorized by this plan.

Keep upstream patches independent of Lotus chain identity, issuance, unfinished v2 formats and historical v1 compatibility. Pin each upstream base at execution time; the recorded ABC commit is a candidate, not a claim about current upstream HEAD. Upstream acceptance is not required to maintain a tested Lotus-local improvement.

| Candidate | Local evidence | Conditions before submission |
| --- | --- | --- |
| Block-template construction | `patches/ecash/01-nlogn-block-construction.patch`, BCHN equivalent | Correct dependency ordering; complexity stated in vertices and edges; fee/package-quality comparison; reproducible benchmark against exact base |
| Mempool bookkeeping/chain limits | 02/03 candidates | Treat removal of a field already absent as no-op; prove memory/edge/admission bounds before removing limits; independent review from miner selection algorithm |
| NNG notifications | Historical Lotus NNG patches and candidate slots | Concrete upstream consumer, API/thread/backpressure/reconnect tests, dependency/packaging cost |
| ZeroMQ changes | Separate candidate slot | Compatibility/migration case accepted upstream; adding NNG alone does not justify deleting existing notification APIs |
| Shared correctness/tooling fixes | Future evidence during v1 port | Minimal chain-agnostic regression and independently applicable patch |

Each packet contains problem, old/new behavior, immutable base/candidate, provenance, narrowly scoped diff, correctness argument, tests, measured limits and remaining risks. Avoid absolute throughput claims and purely promotional rationale. Do not combine an algorithm improvement with a consensus rule change or transport replacement.

When accepted upstream, record the commit and verify equivalence before retiring the local patch. Maintain independent upstream checkout/build/data directories; current eCash/v2 workspace sharing must be removed under V1-01.
