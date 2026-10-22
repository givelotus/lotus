# Admission-slice publication deferral: no safe drop-in change

Read-only source audit of tested `a429917c018437d38f684c2a6bb5b839a0437157` (base canonical `2cf83331`). No production edit, compiler, node, benchmark or new test was launched. The primary-CoW redesign remains deferred for user review.

## Proposed benefit and actual boundary

`RpcAdmissionDispatcher::Impl::Run` drains up to32 requests and holds one `cs_main` acquisition (`src/node/transaction.cpp:185–229`). Each ordinary commit still publishes its addition and, for relay requests, unbroadcast metadata. An outer `CTxMemPool::ScopedSnapshotDefer` could reduce publication tuples to one per nonempty slice; it would not combine transaction checks, primary-container writes or canonical path updates into a shared batch algorithm. Achieved batch size and throughput benefit would require measurement, not inference from the32 limit.

## Ordering that a defer changes

1. Ordinary admission adds the transaction, publishing its numeric view (`CTxMemPool::addUnchecked`), then `MemPoolAccept::Finalize` emits `TransactionAddedToMempool` with owned tx, spent coins and mempool sequence (`src/validation.cpp:1735–1760`).
2. `ValidationSignals` enqueues the event immediately; its scheduler may run before admission releases `cs_main` (`src/validationinterface.cpp:208–223`). There is no publication-defer dependency in that queued task.
3. Wallet notifications proxy the event to their dedicated worker; `CWallet::transactionAddedToMempool` calls `SyncTransaction`, which can notify UI listeners and launch `-walletnotify` (`src/node/interfaces.cpp:445–470`, `src/wallet/wallet.cpp:1094–1120,1400–1411`). Native Chronik proxies the owned tx/spent coins to its independent worker and calls `HandleTxAddedToMempool` (`chronik/native/hosts/abc/abc_subscriber.cpp:90–122`). These paths can process and expose the event while the writer is still handling later requests in the same slice.
4. A snapshot-backed concurrent RPC can read without `cs_main`; `getrawtransaction` uses the published read generation (`src/rpc/rawtransaction.cpp:176` onward). Under the proposed defer it can therefore lag an already delivered addition notification until the entire slice flushes. The current code publishes before enqueueing that addition. This is a changed ordering window, not a claim callbacks always observe an exact per-transaction snapshot: later commits/removals may already advance the current view normally.
5. The send RPC result future is fulfilled after the slice unlocks. Its caller subsequently waits for its independent notification barrier and `SyncSecondaryQueues` (`src/node/transaction.cpp:220–235,314–328`). That protects successful RPC completion but cannot retroactively protect listeners that already ran before the flush.

The audited wallet and native Chronik callback implementations do **not** directly require the global root/sequence tuple; they process owned event payloads. PeerManager's addition callback updates its separate relay index (`src/net_processing.cpp:873`), while reconciliation later joins that index to the published snapshot (`:3980` onward). No direct production callback dereference requiring exact numeric snapshot equality was found. The risk is the public event/read ordering and concurrent external consumers, not a fabricated internal root assertion.

The existing `validationinterface_tests/admission_notification_observes_per_transaction_publication` deterministically demonstrates the changed observable ordering with an ImmediateTaskRunner. It is supporting evidence, not proof that the current implementation choice is a permanent protocol requirement. Delaying or redesigning notification delivery could intentionally change that boundary, but would need explicit treatment of added/removed ordering, secondary queues, subscriber lifetimes, registration failures and notification barriers.

## Failure and locking considerations

Existing ScopedSnapshotDefer requires `pool.cs` at construction and destruction (`src/txmempool.h:710`, `src/txmempool.cpp:1271`). The dispatcher currently holds only `cs_main` around generic commit closures and has no bound pool reference. Adding the scope also broadens pool-lock hold time or needs a deliberate ownership API. Its destructor publishes dirty state, including allocating snapshot/template data; a slice-level failure path must complete every queued request and preserve pending deltas, not let a destructor exception terminate the worker. The current per-request exception containment cannot simply enclose an unrelated destructor outside the loop.

## Decision

Do not add a naive outer defer and do not rewrite callback queues solely to force this optimization. A correct batching design is possible in principle, but it is not the requested bounded drop-in candidate. Preserve the already passing generic arena gate, use the next profile to choose a measured narrow target, and discuss selective primary CoW separately with the user. No throughput benefit or regression result is claimed by this source-only audit.
