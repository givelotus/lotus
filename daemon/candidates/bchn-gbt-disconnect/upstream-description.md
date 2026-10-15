`disconnect_nodes(A, B)` waits only for A to remove its peers. B can still retain a connection until its socket handler processes the close. `mining_getblocktemplate_errors.py` immediately asserted a disconnected-node error on both endpoints, so its second assertion could race with that remote close and receive a valid template.

Wait at the second endpoint with the existing helper before checking both unchanged `RPC_CLIENT_NOT_CONNECTED` errors. This is a test-only synchronization fix; it changes no RPC behavior, timeout or mempool policy and is independent of the mempool diagnostic MR.

The failing Linux UBSan job's node logs place B's `getblocktemplate` request at `23:47:03.932715`, before its final peer's close at `.933306` and disconnection at `.934139`.

Test Plan:

- Run the actual before/after functional test through real TCP proxies forwarding payloads immediately and delaying only FIN propagation by three seconds. Before fails at the same second-node assertion; after passes. This holds with upstream C++ binaries and a native Debug UBSan build.
- Ten ordinary fixed-test native UBSan repetitions pass.
- Python compilation and `git diff --check` pass. Full Linux CI of this separate fix is pending.
