# RPC parser feasibility study

Isolated compile and valid-fixture timings are complete; see REPORT.md. No production dependency or RPC code changed. Production compatibility remains held by one invalid-UTF8 acceptance difference.

The study compares current UniValue with benchmark-only adapters using official exact-revision simdjson and yyjson sources. Both adapters fully materialize the same owned UniValue tree before returning. The existing writer is used for every round trip, so parse+conversion cost and parse+conversion+serialization cost include the representation actually required by unchanged RPC handlers. There is no binary-floating-point conversion of numbers.

Pinned source URLs, commits and hashes are in `sources.json`; existing UniValue sources are frozen by Git commit and hash in `univalue-source.json`. Third-party caches and benchmark binaries are ignored, not vendored into daemon dependencies. `fetch_sources.py` downloads exact official source files over verified HTTPS. `make_fixtures.py` deterministically generates the benchmark and 48-case differential corpus.

Correctness covers raw numeric lexemes (including values outside double/u64), duplicate key order, strings and embedded NULs, UTF-8/escape validity, malformed later batch elements, trailing content and depth bounds. Retained owned values are checked after parser reuse. No method can execute until full input parsing/materialization succeeds. The benchmark does not run any method.

The simdjson adapter uses an owned padded wrapper array so arbitrary scalar roots and exact out-of-range number lexemes can be handled uniformly; copy, padding, wrapper traversal and strict number-grammar validation are included in timing. All keys and strings are copied into owned storage. yyjson uses NUMBER_AS_RAW with otherwise strict read defaults, then copies its DOM into owned UniValue. These are conservative compatibility adapters, not claims about the fastest possible typed parser route.

Inputs include 207/414-byte raw transaction-sized hex strings, arrays of 50 individual envelopes, a 200-transaction dedicated-batch envelope, and a 1.30 MB synthetic 1,000-transaction block-like result. The latter is explicitly synthetic and has string-valued example amounts; separate exact numeric fixtures cover real number tokens. No daemon TPS or real block-output gain is inferred from this microbenchmark.

`TYPED-RPC-DESIGN.md` describes the distinct useful next boundary: directly parsing owned typed requests and centrally serializing typed results, with one shared field descriptor for schema/help/codecs and unchanged UniValue fallback. Latest Glaze requires C++23, while this node uses C++20; this study does not upgrade the standard.

Build and timing ran in an empty compiler/runtime window with no daemon benchmark overlap. Commands, compiler version, input/source/binary hashes, host load and results are recorded. The initial compile error and corrected compile log are retained; the 48-case differential mismatch is not relabeled as a full compatibility pass.
