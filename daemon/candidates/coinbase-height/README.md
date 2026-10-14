# Coinbase height validation review patches

Apply these standalone Lotus patches in the order recorded in `series`:

1. `0001-enforce-vanity-coinbase-height.patch` fixes the early success return for non-logos vanity prefixes, so the existing height checks run after activation.
2. `0002-parse-coinbase-height-with-script-helpers.patch` replaces handwritten byte parsing with GetOp and CScriptNum after its independent activation. It reads variable-length prefix pushes and validates the actual Script number representing the height.

Both activation parameters default to INT_MAX, explicitly disabled. These files are review candidates outside the maintained V1 series. Adding them here does not activate or deploy either change. Maintainers must coordinate network activation separately; the parser changes accepted encodings in both directions and requires consensus compatibility review.

Exact source base: `6590d92300ba588325628ab7c1a166e392947cff` (Lotus on ABC `8c67fe1e85`). Apply in an isolated daemon source checkout, not the monorepo:

```sh
git am /absolute/path/0001-enforce-vanity-coinbase-height.patch \
       /absolute/path/0002-parse-coinbase-height-with-script-helpers.patch
```

The first patch's identical native full-block regression fails eight assertions before and passes afterward; 13 related native cases pass. The second patch's full-block parser regression fails nine assertions before and passes afterward; 14 related native cases pass. Checks use actual TestBlockValidity, with Chronik OFF; Rust/Chronik sources are unchanged. Each mailbox records its rationale and validation. See height-check-notes.md for the first patch's detailed scope.

These patches target the recorded modern Lotus source. Other forks may require context/API adaptation. Published releases, running nodes and the default patch series are unchanged.
