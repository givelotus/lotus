# Native explorer asset acceptance

The complete gate passes on native source
`8cd36091ba9da0665ceab621ce42306963fcbfd9`, binary SHA256
`635d7c5a6512b686e7af5add1daa29c8252eb5f77db5dcae4fd49f0dd84b2d0d`.
The recorded result is [the acceptance evidence](../../../../daemon/docs/evidence/v2-explorer-assets-live-acceptance.json).

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
stage. There is a separate HTTP-only idle publication probe. Each sample waits for
a ready status within a bounded deadline, retaining transient unavailable
observations. Ten ready samples must share the exact epoch, generation and tip;
there is no retry on a generation mismatch. Attempt counts and elapsed probe
time are recorded, with a 300-second overall run deadline.

Example (requires Python with `blake3`, and a freshly named output directory):

```sh
python3 daemon/tests/check-v2-explorer-assets-live.py \
  --daemon /absolute/path/to/lotusd \
  --daemon-source FULL_NATIVE_COMMIT \
  --expected-daemon-sha256 EXACT_BINARY_SHA256 \
  --manifest tools/lotus-v2-devnet/fixtures/local-test-manifest.json \
  --output /tmp/new-explorer-assets-acceptance
```

## Passing native lifecycle

The final run at
`/private/tmp/lotus-v2-explorer-assets-native-live-20261015-h/evidence.json`
passes all five complete asset observations. At height 3 the summary has one
event/two token outputs; height 4 has two events/four outputs; height 5 has
three events/four outputs and no live token UTXO. The mint's zero burn remains
in history. The transfer reports 250 explicit plus 150 implicit burned units;
the final input-only event reports another 600 implicit burned units.

A competing native chain forks from height 2 and becomes canonical at height 6.
The original asset and its transactions return fenced 404, the registry is empty,
and the original mined funding coin is restored. Each of the four former token
outpoints independently returns fenced `/outputs` 404 and has no native coin
before any re-mining occurs. The same three transaction
frames re-enter the real pool and are selected by `minepool`, then confirm in
height 7 at transaction indexes 1/2/3. The asset's first occurrence and every
creation/spend/event location move to this new block. Counters return to three
events/four outputs; both burn modes and an empty token UTXO set still match.
A same-home restart then repeats the complete asset audit: the new height-7
creation, spend, event and first-occurrence locations persist, while the service
epoch renews.

The idle HTTP-only probe keeps generation `3` at unchanged genesis for all ten
ready samples. The final evidence includes every native and HTTP request,
accepted body hashes and all process exit codes; every owned child exits cleanly.
The earlier passing runs `f` and `g` remain available independently. The recorded
interpreter was `/private/tmp/lotus-v2-review-venv/bin/python`, with `blake3`
installed for the checked reference encoding and identity calculations. Native consensus,
wallet token support and compiler contracts were not changed by this test.

## Initial live finding (preserved failure)

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
acceptance. The repaired exact binary listed above subsequently passes the complete gate;
the original failure traces remain unchanged.
