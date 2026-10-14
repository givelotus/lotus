# Independent finalized-ancestor pruning verification fixture

This test-only mailbox patch exercises eCash candidate `04-prune-finalized-mempool-ancestors.patch` across a partially finalized diamond graph. It is not enabled in a daemon series, changes no production source, and does not make the unrelated mining candidates acceptable.

Apply candidate 04 first to clean ABC `8c67fe1e85a602204a2ce65aa3b643469c2c3a1d` or the independently checked current revision `1fb7db17c176cdea8a2c60d887891589382ee4e3`, then apply this mailbox patch:

```sh
git am --keep-non-patch /path/to/daemon/patches/ecash/04-prune-finalized-mempool-ancestors.patch
git am --keep-non-patch /path/to/000-pruned-diamond-boundary-test.patch
ninja -C build test_bitcoin
build/src/test/test_bitcoin \
  --run_test=mempool_tests/setAvalancheFinalized_pruned_diamond_boundary \
  --color_output=no --report_level=short
```

The fixture checks both ancestor lookup modes, pruning only the finalized side of shared ancestry, exact newly finalized IDs/counts, rejection of an unfinalized locked child, and clearing a previously populated result on repeated finalization. Like the upstream mempool unit fixtures, it directly inserts entries to exercise finalization internals; separate real transaction admission/finalization coverage comes from the upstream isolated regtest functional test.

See [the independent verification report](../../docs/ecash-independent-verification.md) for exact application, native build, unit, and functional results. The test asserts state/graph behavior; it is not a performance benchmark.
