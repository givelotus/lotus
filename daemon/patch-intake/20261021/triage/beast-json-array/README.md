# JSON-RPC array regression investigation

Status: source audit and bounded transport probe complete. See REPORT.md and comparison.json. Both owned daemons exited cleanly; all client processes joined. No production edit justified by this control.

Question: is the remaining array-of-individual-calls slowdown caused by HTTP transport/JSON dispatch, transaction admission, or both?

Pinned current source: `a60bba6facc924cdf43c34dc881805bb114fe373`, tree `caf6bd4ce012b2383e733b45df46753b49b2a894` (521 owners). ABC baseline: `1fb7db17c176cdea8a2c60d887891589382ee4e3`. Original finalized fast V2: `09f95c297a67de61836c495904ce9f20551bf415`, available in `daemon/workspace-v2`'s object store.

Source findings:

- Original fast V2 used libevent HTTP plus the Asio coroutine RPC dispatcher. Current V2 uses Beast HTTP plus coroutine RPC dispatch. ABC uses libevent and synchronous RPC dispatch. ABC/current comparisons therefore do not isolate Beast alone.
- Both original fast V2 and current V2 execute JSON-RPC arrays sequentially through `JSONRPCExecBatchAsync`. Generic synchronous handlers execute directly through coroutine wrappers; no per-element `post` or thread handoff was found in that path. Real asynchronous handlers retain their suspension behavior.
- Current HTTP work is scheduled once per HTTP request onto a per-connection strand in the coroutine pool. Separate connections can run concurrently. HTTP/2 and WebTransport are disabled in the preserved engine binaries being compared.
- Existing fixed-work profiling already showed submission-array latency growing with mempool depth (e.g. current shared 32k work: 6.609 seconds from an empty pool vs 25.338 seconds from 6k initial pool, while ABC stayed near 2.84 seconds). That cannot be explained entirely by fixed HTTP framing overhead. Later reconciliation/snapshot fixes address measured non-transport costs.
- Current RPC metrics add a timer and histogram record per executed call, absent from the original finalized source. This is a candidate overhead to measure, not an established cause.

Prepared `transport_probe.py` uses identical `echo` payloads on eight independent Python processes, persistent HTTP/1.1 connections, TCP_NODELAY and complete per-result validation. It tests ordinary individual requests and arrays of 50 calls for at least five seconds each, records client CPU, binary hashes, exact startup command and host load, and shuts down only its owned node. No UTXOs, signatures, fees, mempool publications or P2P relay are involved. A one-second optional sample is diagnostic and must be disclosed in timing comparisons. This whole-application probe can reveal a transport/dispatch gap but cannot attribute it to Beast alone.

No production edit is justified until the control isolates a remaining cost. Dedicated `submitrawtxbatch` and the three-node network ceiling are a separate coordinated benchmark lane.
