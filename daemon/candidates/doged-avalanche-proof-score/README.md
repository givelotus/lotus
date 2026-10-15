# Optional Dogecoin Avalanche proof-score repair

This independent candidate targets `doged-io/doged` commit `9690833b8b6709b7a7837bc397f0d04bf3b885d1`. It is deliberately outside both the maintained current-ABC Dogecoin series and the historical reference series: Chronik and ordinary Dogecoin synchronization do not require enabling or changing Avalanche. It is not a port onto current Bitcoin ABC.

The original score calculation multiplies satoshis by 100 before dividing by satoshis per coin. Above approximately 1.84 billion DOGE, the uint64 intermediate wraps, violating intended stake-score scaling. A 2-billion-DOGE amount produces `15532559262` instead of `200000000000`; MAX_MONEY produces `77662796314` instead of `1000000000000`. The original maximum-money test also evaluates an overflowing expression and misses this error.

The patch divides directly by the exact satoshis per one hundredth of a coin, keeping existing nonnegative clamping and integer rounding. Regression checks use independent constants, sum scaling and values immediately around rounding boundaries. All five assertions fail before the repair and pass afterward. All 139 separate Avalanche unit cases pass after repair (17,717,287 assertions), including the nine proof-suite cases. The patch applies independently to the exact unmodified Doged pin. This establishes arithmetic behavior only, not network proof validity, quorum security or finalization.

Apply only in a disposable Doged candidate checkout:

```sh
git am --keep-non-patch --keep-cr --committer-date-is-author-date \
  /path/to/daemon/candidates/doged-avalanche-proof-score/000-fix-proof-score-overflow.patch
ninja -C build -j8 test-avalanche
build/src/avalanche/test/test-avalanche --run_test=proof_tests --report_level=detailed
```

On Apple arm64, the existing default Doged test-literal repair is needed for `test_bitcoin`; it is unrelated to this proof-score test binary. The optional score patch is validated in an isolated checkout containing the two default Doged compatibility/regression patches. No production node, chain data or release is modified.
