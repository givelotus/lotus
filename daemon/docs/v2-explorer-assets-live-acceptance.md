# Native explorer asset acceptance

The dedicated gate is `daemon/tests/check-v2-explorer-assets-live.py`. It uses
native development-node JSONL controls and actual explorer HTTP. It creates fresh
homes, binds ephemeral loopback ports, refuses ports 10604/10605/8331, stops its
own child processes, and never opens an existing production index.

The authorization fixture is explicitly the public native TRUE script `4e` and
MINT script `794e` used by native `test_ordinary_validation.cpp`. This is native
token acceptance, not compiler contract or wallet token acceptance. The Python
reference encodes bytes and checks native-reported transaction/block identities;
the native node decides ordinary transaction and complete block acceptance.
Transactions enter `submittransaction` and blocks are selected through
`minepool`. No caller supplies a block's transaction array or inserts DB records.

The complete gate checks:

- Real coinbase funding and maturity, followed by a 1,000-unit mint, including
  a zero-valued token burn output.
- A transfer spending 1,000 token units into 600 live units and 250 explicit
  burn units; the event must report another 150 units burned implicitly.
- A transaction consuming the remaining 600 live units without any token
  outputs; its input-only token event must report 600 implicit burn units.
- Exact native TxID, TxHash, block, height, transaction index and output ordinal
  joins, all asset event sums, occurrence counters, zero/burn history, spend
  references and native coin presence. Names, decimals, issuer and supply stay
  explicitly unknown. Asset lists exclude native currency.
- One-item pagination at one snapshot, followed by a longer actual native fork
  from a saved common ancestor. Asset registry/events/output membership must
  disappear, the original native funding coin must return, and exact original
  transaction bytes must re-confirm from the native pool at new locations.

The harness records exact binary/profile/harness/reference hashes, process
commands, accepted full block bytes, submitted transaction bytes, native JSONL
responses, and timestamped HTTP requests. A final `passed:true` requires every
stage. There is a separate HTTP-only idle publication probe; it must not hide
sustained generation churn behind unbounded snapshot retries.

Example (requires Python with `blake3`, and a freshly named output directory):

```sh
python3 daemon/tests/check-v2-explorer-assets-live.py \
  --daemon /absolute/path/to/lotusd \
  --daemon-source FULL_NATIVE_COMMIT \
  --expected-daemon-sha256 EXACT_BINARY_SHA256 \
  --manifest tools/lotus-v2-devnet/fixtures/local-test-manifest.json \
  --output /tmp/new-explorer-assets-acceptance
```

## Initial live finding

Binary source `86201398e3df61605c2eb2d09c201ce774013e7f`, SHA256
`8c6c2d0ed9fc490b8cdb8900f01564ca6902c5d7dbe269eae8d0becefe27ae32`,
accepted the real testscript mint into its pool and then a connected block. Its
asset summary and mint event were correct. The pinned output pagination then
returned 503 followed by 409 `stale_snapshot` at the same canonical block.

The independent HTTP-only idle probe used ten requests spaced 25 ms apart. At
unchanged genesis and service epoch, all ready observations advanced generation:
`16, 26, 36, 48, 60, 72, 80, 92, 100, 112`. No native control command occurred
inside the probe. Source inspection found unconditional authority invalidation
and publication in the native event loop. These original traces are retained at
`/private/tmp/lotus-v2-explorer-assets-native-live-20261015-c/` and
`/private/tmp/lotus-v2-explorer-assets-native-live-20261015-d/`.

This initial binary does not pass the complete gate. Mint acceptance and the
failed pinned read do not establish transfer, burn, rollback or complete explorer
acceptance. A repaired exact binary must pass the entire same gate before those
claims are made.
