# Temporary chain-domain correctness audit

Exact original base `23ff06e9fa8bd43ab77efc8a039d19c0a25142d2`, candidate `306f4dfe2b9e25890bd361fc337f8f8344f43d55` / tree `3a9227011fce3a8e853ab9f8e7e7cb30108c9425`. Source inspection and prepared tests only; no compiler/runtime or performance claim. This is separate from native warmup optimization.

## Writers and factory call graph

The process value is a plain `lotus::v2::ChainId` array in `primitives/block.cpp:33`; `GetActiveV2ChainId` returns its reference and SetActive assigns it without synchronization. Production selected-domain installation is `common/init.cpp:50` / command-line startup tools → SelectParams → CreateChainParams → factory construction → final SetActiveV2ChainId (`chainparams.cpp:50–53`). This must finish before worker readers; changing a live node's selected network remains unsupported.

The bug is the separate **runtime** factory side effect: `kernel/chainparams.cpp` constructors Main/TestNet/RegTest each create local ScopedV2ChainId. Its ctor reads the previous global and calls SetActive; its dtor restores that global. These are the only additional production setter calls; tests/bench/fuzz startup helpers are listed separately in setter-calls.txt.

Runtime factory entry paths include:

- Snapshot metadata network mismatch decode (`node/utxo_snapshot.h:86,90`) → GetNetworkForMagic → all three CChainParams factories. This is reachable while reading a supplied snapshot, not only startup selection.
- Lazy miner-fund destination (`minerfund.cpp:29` BuildDestination/GetMinerFundDestination) → CreateChainParams(MAIN). The function-static guard serializes its own initialization, not concurrent transaction decoding elsewhere.
- Treasury address fallback (`avalanche/treasury.cpp:65` onward) → each network factory with both address-prefix modes.
- Other direct CChainParams/CreateChainParams consumers retain the same behavior: they can safely construct another network's settings only if temporary construction context is confined to their calling thread.

Within a factory, scope → CreateGenesisBlock → V2 coinbase construction/MakeTransactionRef → cached transaction identities; BlockMerkleRoot uses those identities; ComputeV2BlockStateRoot/RecordV2BlockState and genesis.GetHash consume the same temporary domain. All implicit GetActive calls on this path execute on the construction thread. TransactionSubtreeA async children receive already computed identity pairs and do not call GetActive, so no scoped-domain inheritance to spawned workers is needed here.

## Concurrent identity and validation readers

The complete direct production read inventory is production-global-read-inventory.csv (source grep at the exact original base, with tests/bench/API declaration/definition excluded). It includes the temporary selector's own save read as well as the consumer sites; no consumer was removed from the inventory merely because it holds cs_main.

The decisive RPC path is `rpc/mempool.cpp:88–93` (and analogous batch entries): DecodeHexTx → CMutableTransaction bytes → MakeTransactionRef → OwnedLayout/Place → CTransaction(Layout) → InitHashes. Native fast hashing (`primitives/transaction.cpp:446`) and general ComputeTxIdentities (`:317`) both read the implicit active domain. `CMutableTransaction::GetId/GetHash` also use that general helper. Deserializing directly into an immutable CTransaction follows the same InitHashes path. These calls occur before admission's cs_main scope and cache TxId/TxHash permanently; restoring the global later does not repair the object.

Other production consumers in the inventory are ordinary native signature fast paths and CScriptCheck preparation, block/state-root and fast/reverse-sync verification, network root/shard verification, pool jobs/metadata, native PSBT/signing VM helpers and mining RPC metadata. References are consumed synchronously or copied into owned preparation/cache/draft state; no production persistent pointer/reference escape to a temporary factory-local domain was found.

Two independent hazards exist. Unsynchronized array writes/readers constitute a C++ data race and can select a wrong or torn domain. Even replacing the array with atomic storage would not fix semantic cross-thread leakage: overlapping scopes can restore out of order (Reg→Main, Main→Test, restoreReg, restoreMain), permanently changing the selected global. Snapshot/chain locks do not serialize all factory writers or lock-free RPC readers.

## Narrow repair and regression contract

The candidate keeps the startup-selected process value and setter, but gives temporary ScopedV2ChainId an **owned thread-local override**. GetActive uses that scope only in the calling thread, otherwise the selected process fallback. Scope copies its input, cannot copy/move, nests with previous-pointer restoration and asserts LIFO teardown. Returned references are valid only while their owning scope remains alive; retaining callers must copy the domain. No chain IDs, genesis constants, serialization, identity formulas, monetary rules or caller-validation policy change.

The deterministic regression holds an explicitly different network scope while an unscoped async RPC-like reader finishes; no further domain write occurs until the reader joins. The old process-global semantics therefore choose the wrong domain even without invoking a data race. The test checks both fast one-output and fallback seventeen-output V2 identity paths, mutable decoding, immutable cached IDs/hashes, and wire roundtrip against explicit-domain ComputeTransactionIdentities. Nested scopes restore through exceptions and own their input after the caller changes its source array.

A second bounded test constructs all three actual networks concurrently, verifies known stored genesis IDs and cached V2 coinbase identities against each network's explicit domain, recalculates block IDs under a local scope, and concurrently decodes transactions under the unchanged process-selected domain. Workers return owned verdicts; all futures drain before borrowed fixtures leave scope. Existing mainnet/testnet known genesis/PoW/serialization checks remain and now use the production scope rather than a test-global override.

Causal owner is `bf728caced8` (historical363922665a4), which introduced temporary global selection for cross-network genesis construction. The new warmup checker already captures configured chain parameters explicitly, but does not fix ordinary callers; this patch must not be represented as a performance-patch repair. Native test execution and independent source review are pending.
