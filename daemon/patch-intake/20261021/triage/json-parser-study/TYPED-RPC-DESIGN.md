# Typed request and result boundary (proposal, no wire change)

Current JSON-RPC is dynamic at both ends: `JSONRPCRequest` owns UniValue `id` and `params`; handlers manually assemble UniValue results. `RPCArg`/`RPCResult` describe help and runtime checks, not C++ request/result types. Switching parsers alone does not remove those tree allocations or handler-level copies.

## A small bidirectional pilot

Start with `sendrawtransaction` and `submitrawtxbatch`, reusing their authoritative admission routines. Give each method a typed request and typed result, with one field-description tuple defining names, member pointers, argument order, required/default/null behavior, encoding and help. C++20 member-pointer templates and tuples suffice; no language-standard upgrade or C++23 reflection is required.

Conceptual types:

- `SendRawRequest`: owned hex string; max-feerate input with explicit absent/null/value distinction and exact decimal lexeme.
- `SendRawResult`: transaction identity encoded as the existing scalar hex result, not a new object.
- `SubmitBatchRequest`: owned vector of hex strings and the same max-feerate policy.
- `SubmitBatchResult`: `accepted`, optional `package-error`, ordered `txids`, ordered per-transaction results.
- Per-transaction results can use a tagged C++ variant for accepted/rejected/prevalidation states, but the serializer emits the existing heterogeneous JSON objects, optional fields and names, without adding a wire tag.

The same field definition should feed the named/positional decoder, generated `RPCArg`/`RPCResult` documentation where expressible, legacy-UniValue adapter, and central JSON serializer. Do not replace each handwritten handler with a different handwritten JSON writer or repeat the field names in three places. Existing runtime metadata cannot itself magically generate C++ struct types; migrated methods need a compile-time descriptor source, with legacy metadata derived from it.

## Envelope and compatibility

Keep the generic envelope separate: method string, dynamic `id`, positional/named params, and existing JSON-RPC errors. Preserve the current method/parameter lookup and error order. Current parsing extracts `id` first; absent and explicit-null `params` both become an empty positional array. Other scalar params reject. String/number/null identifiers, exact number lexemes and existing error encoding remain intact; do not introduce JSON-RPC 2.0 notification rules as a side effect.

Named arguments must retain aliases, unknown-name errors, order/default behavior and duplicate-field resolution. The current UniValue lookup resolves the first duplicate key; this must be checked at both envelope and method boundaries. An optional C++ member cannot by itself distinguish an omitted field from explicit JSON null. Use a presence-aware input type (absent, explicit null, value) until method policy resolves it. For these two methods explicit-null maxfeerate currently selects the same default as omission.

Arrays of independent JSON-RPC calls remain sequential and keep their per-call error behavior. The dedicated batch method retains its separate all-or-nothing admission semantics. A parser must validate the **entire JSON document**, including unneeded fields and later array members, before executing any method; a malformed trailing member must not allow an earlier `stop`/submission to execute.

## Exact amounts and result serialization

`AmountFromValue` currently accepts JSON numbers and strings, then uses `ParseFixedPoint` with active Currency decimals and range checks. Preserve that exact path first. A typed input can own the original decimal lexeme and number/string kind and delegate to the existing conversion; never parse through `double`.

For typed result Amount fields, use the existing integer-atom representation and Currency formatting policy. The custom serializer must emit exactly the existing JSON token kind and decimal formatting for each chain configuration; do not infer token kind from the documentation's STR_AMOUNT label. Negative values, range boundaries, exponent input, trailing zeros and current default behavior need parity fixtures. Integer identifiers and 64-bit counts must never round-trip through binary floating point.

The outer response adapter should preserve dynamic id/error values while centrally serializing a typed success result. Unchanged methods continue returning UniValue through the existing registration adapter. Incremental migration is possible without changing the wire protocol or rewriting the entire RPC table.

## Ownership and coroutine suspension

Direct parser-to-owned-request extraction is the useful optimization boundary. A faster parser followed by a full UniValue tree, followed by copying into typed fields may improve syntax scanning but adds another materialization. Report that cost explicitly.

For simdjson On-Demand, all input/padding, parser state and unescaped string storage must remain alive during traversal. Do not retain its views across `co_await` or reuse a thread-local parser after suspension. Finish full validation and copy only the typed request fields into request-owned storage before dispatch can suspend. Dynamic id/error/unknown legacy params still require owned representations. yyjson document strings similarly belong to the document unless copied or a document owner is retained. No borrowed string should escape an arena that is reset on another request.

Typed results should own their data until the central serializer finishes, then move the generated response bytes into the existing HTTP reply ownership chain. Long-poll results must not borrow mutable chain/mempool state across suspension.

## Gates

1. Differential request/result fixtures against unchanged handlers: named/positional params, null/omission/defaults, aliases, duplicate order, exact ids/amounts, errors and batch ordering.
2. Full-document malformed-input rejection before dispatch, strict UTF-8/escape validation and depth bounds.
3. Parse → owned-request → suspension/parser reuse lifetime test; result serialization lifetime test.
4. Isolated parse/materialization/serialization benchmark including ownership costs, followed by actual HTTP submission workload only if the boundary has measurable benefit.
5. Keep consensus/admission semantics and dynamic legacy handlers unchanged. No whole-codebase migration or production parser dependency until this pilot is reviewed and measured.
