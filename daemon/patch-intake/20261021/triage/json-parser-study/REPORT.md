# Faster parsing is feasible; production compatibility remains held

Both candidates reduced the cost of parsing into the **same owned UniValue representation**. Including conversion, destruction and the existing UniValue serializer, the six fixture observations improved by roughly **1.6–1.8×**. These are isolated JSON costs, not daemon TPS gains or evidence that JSON explains the remaining submission bottleneck.

| Fixture | Bytes | UniValue parse + owned tree | simdjson → owned tree | yyjson → owned tree |
|---|---:|---:|---:|---:|
| Single 207-byte transaction-sized hex envelope | 482 | 1.50 µs | 0.34 µs | 0.27 µs |
| Single 414-byte transaction-sized hex envelope | 896 | 2.50 µs | 0.41 µs | 0.36 µs |
| Array of 50, 207-byte hex arguments | 24,191 | 75.22 µs | 15.65 µs | 12.40 µs |
| Array of 50, 414-byte hex arguments | 44,891 | 128.43 µs | 19.81 µs | 17.16 µs |
| Dedicated 200-transaction envelope | 83,465 | 230.56 µs | 21.16 µs | 22.65 µs |
| Synthetic block-like result, 1,000 transactions | 1,302,147 | 4.66 ms | 1.38 ms | 0.95 ms |

| Same fixtures, including existing serialization | UniValue | simdjson adapter | yyjson adapter |
|---|---:|---:|---:|
| Single207 | 2.89 µs | 1.79 µs | 1.75 µs |
| Single414 | 5.43 µs | 3.19 µs | 3.16 µs |
| Array50/207 | 153.95 µs | 87.93 µs | 89.92 µs |
| Array50/414 | 275.21 µs | 167.39 µs | 164.20 µs |
| Batch200 | 514.24 µs | 299.38 µs | 297.15 µs |
| Block1000 | 8.38 ms | 5.23 ms | 4.60 ms |

Each parser/mode/fixture executes at least 0.5 seconds in a tight repeated microbenchmark; large documents finish their eight-iteration chunk before checking the timer. All six converted fixture serializations match current UniValue byte-for-byte before timing. Sources use Clang O3, C++20 and assertions retained; there is no jemalloc-specific linkage. The simdjson parser is reused, but each request's padding/copy and every owned-tree conversion/destruction are timed. yyjson's DOM allocation/conversion/free are also timed. The same existing writer is used for all candidates. No parser is allowed to keep borrowed data in the resulting tree.

These are one set of observations under recorded, uncontrolled host load. The large-block input is synthetic, not a captured daemon result; parsing that output is relevant to clients/readback but a server already constructing a result does not reparse its JSON before sending it. Likewise, serializing an echoed request document is not the exact cost of sendrawtransaction's short TxId response. The tables isolate building-block costs rather than predicting endpoint speedup.

## Correctness findings

The 48-case differential corpus preserves huge integer/exponent number lexemes, exact decimal text, duplicate-key order, embedded NULs, escaped keys, Unicode, depth boundaries and malformed later batch elements/trailing input. Retained UniValue results remain unchanged after repeated reuse of each parser.

**47/48 cases match at both adapters. One existing-acceptance difference blocks a drop-in production claim:** current UniValue accepts the overlong UTF-8 encoding C0 AF inside a string, while strict simdjson and yyjson reject it. This is one differential case counted as two adapter mismatches; it is not two independent bugs. The study does not weaken either parser to accept invalid UTF-8 or silently change existing RPC behavior. Correctness output is `correctness.tsv`; its mismatch exit is preserved. The valid benchmark fixtures all pass exact-output validation separately.

A replacement would need a deliberate decision/test around that invalid-input tightening. This study is not a complete compatibility proof or fuzz campaign. No production parser dependency, wire behavior or handler was changed.

## Integration options and effort

**yyjson compatibility adapter:** comparatively small C API surface. NUMBER_AS_RAW preserves every numeric lexeme without a binary-floating-point round trip. Its strict complete DOM parse finishes before conversion; object iteration preserves duplicate order. The prototype is roughly 30 lines for conversion plus the read/ownership wrapper. Integration still needs build/depends/Guix/ABI coverage, current error/depth policy, allocation failure handling and sustained endpoint measurements. This line count is not a calendar estimate.

**simdjson compatibility adapter:** similarly feasible and portable across supported SIMD targets, but On-Demand lifetime and full-validation rules need more care. The prototype copies into an owned padded wrapper, traverses every value and validates number grammar explicitly so valid huge exponents/integers survive unchanged. That wrapper/padding/copy is included in costs. It deliberately avoids DOM numeric conversion, which would lose exact token spelling or reject valid out-of-range numbers. A request must finish materialization before coroutine suspension or parser reuse.

**Typed request and typed result boundary:** the larger architectural benefit is direct parser → owned request and typed result → central serializer, bypassing the full generic tree for migrated methods. One C++20 field descriptor tuple can feed codec, schema/help and compatibility adapter; `RPCArg`/`RPCResult` are currently runtime descriptions, not actual C++ types. The pilot should cover sendrawtransaction and submitrawtxbatch, preserve dynamic id/errors and unchanged handlers, and keep arrays sequential. Exact amounts must reuse fixed-point/integer-atom policy, with absent/null/default distinctions preserved. See `TYPED-RPC-DESIGN.md`.

Typed result serialization has **not** been implemented or measured here. The study uses the current writer because that is the current handler contract. Direct yyjson/simdjson output or schema-driven writers are separate candidates; these tables must not be presented as their measurements.

Latest Glaze requires C++23, so it is not an automatic drop-in for the node's C++20 build. No standard upgrade or wholesale RPC migration is proposed as part of this measurement.

## Recommendation

The compatibility adapters are promising enough for an isolated, reviewed prototype, with yyjson offering the simpler complete-DOM/raw-number route. Neither is approved as a production drop-in yet. Preserve the existing invalid-input policy deliberately, prove ownership across coroutine suspension, and measure a real RPC endpoint before attributing daemon performance gains. A limited typed request/result pilot is a distinct next step rather than an assumption that the faster parser eliminates handler copies.

The original Beast investigation remains separate: cheap and transaction-sized echo arrays did not show a consistent generic array-throughput regression. This JSON study neither identifies Beast as the cause nor repairs the observed P2P convergence problem.

Official pinned sources: [simdjson On-Demand value API](https://github.com/simdjson/simdjson/blob/a7228cb376bf54d475cd86e451bb7cac92adf7c1/include/simdjson/generic/ondemand/value.h), [simdjson parser ownership/padding API](https://github.com/simdjson/simdjson/blob/a7228cb376bf54d475cd86e451bb7cac92adf7c1/include/simdjson/generic/ondemand/parser.h), [yyjson API and read flags](https://github.com/ibireme/yyjson/blob/556bf1c12b99608957271d319a546010e301da63/doc/API.md), [Glaze requirements](https://github.com/stephenberry/glaze#readme). Exact source file digests, compiler command/version, fixture/binary hashes, raw CSV and observed load are preserved beside this report.
