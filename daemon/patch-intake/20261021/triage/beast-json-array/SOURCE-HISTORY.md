# Historical regression and current boundaries

The original report concerned **single-client latency**, not a collapse in concurrent array throughput. Recovered original observations in `historical/http_ab.pass{1,2,3}.json` show:

| 50 sequential getblockhash calls in one HTTP request | ABC/libevent | Beast |
|---|---:|---:|
| Client concurrency 1, p50 HTTP latency | 111 / 116 / 111 us | 146 / 150 / 151 us |
| Concurrency 16, HTTP requests/second | 15,506 / 15,566 / 15,164 | 15,079 / 15,580 / 15,440 |
| Concurrency 64, HTTP requests/second | 15,029 / 15,184 / 15,578 | 16,345 / 15,946 / 15,823 |

Each HTTP array request performs 50 commands **sequentially**, as intended. Do not multiply per-request latency into a per-command claim or describe these old finite request counts as sustained five-second measurements. Original host load was uncontrolled and binary/source provenance is weaker than current frozen receipts.

The original I/O optimization commit (now owner 155, current source `8b82a04bbbc114ded769a0ae332e12ec6e306f6f`) explicitly records per-stage timing: roughly 13 us in the small-response write and per-operation timer rearming. It introduced a nonblocking immediate write fast path and one idle timer per connection. Its commit message reports remaining c=1 batch latency of 130 us versus libevent 113–119 us, attributing the remaining gap to two cross-thread handoffs. This is historical author evidence, not a fresh stage-timing measurement.

Current source retains that fast path:

- `DispatchRequest` constructs an HTTP request on the connection's I/O strand and enqueues one work item onto a per-connection strand backed by the RPC worker pool.
- `JSONRPCExecBatchAsync` iterates and awaits each command in sequence. Generic synchronous actors call through directly; asynchronous long-poll actors may suspend safely. There is no intentional per-element executor post.
- `HTTPRequest::WriteReply` posts the response back to the connection's I/O executor, fills the response slot and cancels its waiter timer.
- `WriteResponse` attempts nonblocking `http::write_some` immediately; only would-block falls back to `async_write`. Idle expiry is maintained once per connection rather than rearmed around each individual operation.

These connection→RPC-worker→connection boundaries permit blocking handlers to coexist with nonblocking socket I/O and long polls. They have fixed latency costs but are not evidence of an extra thread hop for every command in a JSON-RPC array. Moving arbitrary RPC actors onto the I/O executor would risk stalling unrelated network I/O.

The exact introducing boundary in the current 521 lineage is:

- before: `e6f5b77e75a3e4003a286e411f7c38ca56ad6478` (libevent HTTP, coroutine RPC already present);
- after: `8796bdb44618cd0e15125aa1534e9b3aba066a4e` (Beast HTTP, same coroutine command dispatcher).

A build of those two sources would isolate the initial HTTP replacement more directly than ABC versus current. It would not represent the later write/timer repairs or today's full native endpoint. Fresh before/after source builds have **not** been performed in this investigation.

`size_probe.py` prepares the next control: 207- and 414-byte deterministic binary values encoded as 414- and 828-character hexadecimal JSON arguments; each echoed response is validated. Cases use singles and arrays of 50, client concurrency 1 and 8, five seconds each, full per-request p50/p95/p99 and exact request/response byte counts. Echo deliberately includes an equally large response, so it bounds combined parse/serialize cost rather than exactly reproducing sendrawtransaction's short TxId response. No arrays are parallelized and no daemon asyncio path is introduced.

Do not start that control until the independently owned network benchmark drains and the coordinator transfers the runtime boundary. No new production fix is justified by the existing control.
