# Lotus vanity-prefix coinbase height commitment: review candidate

This is a Lotus consensus candidate, not an eCash/Bitcoin ABC defect. It is not
activated on any network and must not be deployed as an uncoordinated tightening
of existing mainnet validation.

## Reproduction and scope

Lotus v8.3.4 change 5843fea81acc269a5447c69499a82a4cfafb6ef7 (replayed as
a2de18f85314883bc2351eb4a43e0d0ba60c5c95) intended to allow an arbitrary
vanity prefix such as FRBTC in the existing first-output OP_RETURN, followed by
the block height. Instead, at heights >= 1,018,000 a prefix other than `logos`
returns true before parsing the height. `OP_RETURN <FRBTC>` and
`OP_RETURN <FRBTC> <wrong-height>` therefore pass ContextualCheckBlock.
The header's height remains checked; coinbase output amounts, total reward,
miner-fund rules and other ConnectBlock checks are not bypassed by this return.
The same Lotus-specific rule is absent from upstream Bitcoin ABC revisions
252182e957, 8c67fe1e85 and 1fb7db17.

## Proposed rule and activation

A new consensus parameter `coinbaseHeightValidationActivationHeight` defaults to
INT_MAX, explicitly a disabled sentinel. No chainparams or live network activation
is chosen in this patch. Maintainers must select a coordinated activation height
in a separate network upgrade change.

Before activation, the historical parser and acceptance behavior remain intact.
After activation, a vanity prefix no longer returns success early. Validation
continues through the existing height-length and height-value checks. A correctly
encoded FRBTC prefix and height remain accepted. Missing, wrong, truncated or
overlong height commitments are rejected as `bad-cb-height`.

The parser's existing serialization rules are unchanged: direct byte prefix and
height lengths, height at most three bytes, unsigned little-endian height value,
and trailing data permitted. This patch deliberately does not add PUSHDATA parsing,
small-integer opcodes, signed numeric interpretation or four-byte heights. Those
would broaden consensus acceptance and require separate review. The historical
logos requirement below height 1,018,000 and early-block exceptions are unchanged.
Only the historical vanity-prefix success return is gated. No coinbase payout,
reward or ordinary transaction rules change.

This is a candidate tightening of the existing accepted block set after the chosen
height. It does not restore a compulsory `logos` prefix or create a second OP_RETURN
output. Existing mainnet acceptance is unchanged while activation remains disabled.

## Applying

Exact Lotus base: 6590d92300ba588325628ab7c1a166e392947cff
(on Bitcoin ABC 8c67fe1e85a602204a2ce65aa3b643469c2c3a1d).

```
git am 0001-*.patch
```

This patch is a standalone candidate after the maintained 153-patch V1 chain;
it is not added to the default series or release candidate. Applying directly to
LotusiaStewardship's older source may require adapting surrounding APIs/includes.
No external report, issue, email, tag, release or node deployment was performed.

## Validation

Candidate source commit: cc2dc566b4472efaf762a93e0a8cb5222d122798.
Final/replayed tree: a14c5957e6f3a39bc6d24f56e29d853e3dfeb59d.
A fresh detached worktree applied the mailbox with git am and matched this tree.

On native macOS arm64, the identical final TestBlockValidity regression fails
eight assertions before the fix (four malformed vanity commitments accepted),
and passes afterward. All 13 cases across validation_block_tests, miner_tests,
txvalidation_tests and txvalidationcache_tests pass. Chronik was OFF for these
focused C++ checks; Rust and Chronik sources are unchanged. Logs are included as
before-tests.log, after-tests.log and related-suites.log. validation.json records
the exact patch SHA256, base and replay tree.

Suggested recipient note: “The FRBTC vanity exception currently returns before
checking the coinbase height. This candidate gates that early return so the existing
height checks still run, without changing script formats. Tests reproduce actual
block acceptance before the fix and rejection afterward. Activation is deliberately
disabled pending a coordinated upgrade height.”
