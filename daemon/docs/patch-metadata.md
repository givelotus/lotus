# Patch metadata and reproducible replay

V1 patches are single-message `git format-patch` files. Setup imports them with
`git am`, retaining each subject, body, author and author date. Committer identity
is the builder, not an assertion that the original author performed the replay.
All tracked source patches now carry mail metadata and a nonempty explanation.
Comment-only no-op and placeholder files remain explicit non-patches; they must
not be imported with `git am`. The audit rejects new raw diffs or synthetic
`Apply patch:` subjects.

The metadata migration preserves the original 153 filenames and every diff byte.
`patches/v1/metadata-provenance.json` records each pre-migration commit and tree,
and a SHA256 digest of the recovered author, author date and complete message,
and the original Lotus history commit where recoverable. Metadata for 147 patches
was recovered from `givelotus/lotusd` history through `92a39c097559dcd73c510fc3a89405d28cfc9951`,
using unique normalized subject matches, preferring exact matches and first-parent
history. Adapted source comes from the recorded rebased commit, not the old tree.
Historical CRLF message lines are normalized to LF. Patch 191 embeds a literal
diff in its original explanation: its complete historical body is indented (with trailing whitespace removed) as a
quotation so `git am` cannot mistake it for the source patch. Non-PATCH bracketed
subject prefixes are retained with `git am --keep-non-patch`.
Six envelopes retain the recorded replay author/date and explicitly identify their
newly written explanations. Patch 245 has ambiguous historical version-bump
subjects; its existing payload actually sets the intermediate version to 11.5.1.
Patch 002 adds a long-chain regression test on the modern base; its historical
filename does not prove that it changes current chain-limit policy.

Verify every intermediate source tree without modifying the workspace:

```sh
python3 daemon/scripts/patch-series.py /path/to/isolated/abc \
  daemon/patches/v1/series --base 8c67fe1e85a602204a2ce65aa3b643469c2c3a1d \
  --check --provenance daemon/patches/v1/metadata-provenance.json \
  --expect-tree e0d4f9c0219739b6774864858c582a8144a443d9
```

Provenance permits appended release patches while checking all 153 recorded
prefix trees; omit the old final-tree expectation when the candidate intentionally
changes release metadata. A new upstream base needs newly reviewed tree evidence,
not an assertion that the old trees remain valid. Clean application alone does
not establish compilation, consensus correctness, indexing or synchronization.

For one new patch, commit its changes and rationale in an isolated workspace,
then run `make -C daemon mkpatch SERIES=v1 NAME=<number-description>`. The helper
refuses dirty workspaces and existing output files. Add the filename to `series`
after review. To refresh all patches after an interactive rebase or message edit:

```sh
python3 daemon/scripts/export-patch-series.py /path/to/isolated/abc \
  daemon/patches/v1/series --base <exact-base-sha> --output-dir /tmp/lotus-patch-candidate
python3 daemon/scripts/patch-series.py /path/to/isolated/abc \
  /tmp/lotus-patch-candidate/series --base <exact-base-sha> --check \
  --expect-tree <reviewed-source-tree-sha>
```

The exporter requires one linear commit per manifest entry, preserves binary
changes and complete commit messages, and writes a new directory only. Review
and install that candidate together with any intentionally updated provenance.
The former destructive `setup RESET=1` operation is refused; preserve or move
an existing workspace when a separate clone is needed. Replay validates all inputs first, applies them in a temporary clone, and promotes
the complete result only after success. A failed patch cannot leave the target
workspace on a partial series or in an `am` conflict state. Setup and refresh still
change their selected workspace on success: use a separate checkout, never a
running daemon's source workspace. Neither command stops or deploys a daemon.

Run isolated tooling checks with:

```sh
python3 -m unittest discover -s daemon/scripts/tests -v
```

## Subsequent block-assembly source repair

The initial metadata migration left source tree
`a8d838de8fb5887170d6f32e86fed19f8e82c124` unchanged. A later behavioral review
found that the experimental block scheduler could include free descendants and
mishandle strict block-size and fee-delta accounting. The separately committed
repair `e21d07c27a2235667d1450a003e883b246ed5aa3` restores the retained upstream
assembler and adds a boundary regression. It is deliberately folded into patch
246, preserving the 153-entry mapping. Its existing author, date and subject stay
intact; the body identifies the later source change and validation limits.

Only the final two source trees change: patch 246 to
`efc38f2ae92be9835f149bdc55ff1041ac53cc98`, and patch 247 to
`e0d4f9c0219739b6774864858c582a8144a443d9`. Patch 247 remains a version-only change.
The provenance file retains both prior trees and the repair commit. Replay checks
all 153 trees and metadata digests against this new candidate, whose final tree
exactly equals the independently tested repair commit.

The repair built `lotusd`, `lotus-cli` and `test_lotus` with Chronik disabled;
`miner_tests` and all 151 `check-bitcoin` targets passed. The same final tests
before repair failed five assertions, including the strict-size case expecting
three selected transactions but receiving two. These results validate the C++
repair, not a new Chronik build, live synchronization, or released binary. Those
checks remain separate requirements before publication or deployment.

Follow-up integration also passes the normal Chronik-enabled build, Rust checks,
all 156 C++ check targets, and isolated mainnet Chronik parity. See
[v1 validation](v1-8c67fe1e85-validation.md) for the exact source and evidence.

## Reference patch message backfill

The remaining four raw diffs, eCash/BCHN 01 and 02, now have newly authored
maintenance envelopes and explanations. Their original per-patch author dates
and messages could not be recovered. These are explicitly new metadata, not
claims of original authorship. The monorepo port/import is recorded as
`578bbcddd210de1601b280967700e07420f23782`. Its earlier mining import
`9686d09aac0ebe58d4ad173b2fb12360776869de` points to
[schancel's simple-mining branch](https://github.com/schancel/bitcoin-abc/tree/simple-mining),
whose recorded tip `c1bdbe00d29042af81e1846728088f32867c3498` has the original
subject “WIP: Stupidly simple mining.” That 2019 source is historical lineage,
not the adapted modern diff.

At the metadata-only backfill revision, the new messages explain actual behavior: 01 was a broken experimental static
ancestor-package assembler; 02 inserts transactions with `addUnchecked` and
does not establish admission-policy changes. Neither becomes supported through
this metadata update. Both remain outside default executable manifests.
`patches/reference-metadata-provenance.json` records original file hashes, exact
unchanged payload hashes, metadata hashes, exact pinned bases and resulting trees.
Each raw-diff tree was independently compared with its new `git am` replay:

| Reference | Exact base | Unchanged source tree |
| --- | --- | --- |
| eCash 01 | `252182e957120652960c1f88ec96515c448b1204` | `1bffd0dba02e9440857f7abaa9fbeae7743dd2d9` |
| eCash 02 | same | `0bed473a0ecb97967f131f26b6d0fcdcf09d92a0` |
| BCHN 01 | `0bc23ac4c1365f34ed824e2b07e554ec06a5f5cd` | `23f266df5b173e3840516b14bf7d17832812ccfb` |
| BCHN 02 | same | `f3d90d3c262eba8b0b1956af98e6e31bda5f060c` |

These four comparisons apply each candidate independently to its exact base.
They prove metadata conversion preserves source, not that the candidates work.

Thirteen subject-only commits in the incomplete current-ABC Dogecoin candidate
now append a labelled maintenance explanation. Original subjects, authors and
author dates remain intact; the new prose is explicitly not original author text.
Its manifest retains the old metadata hashes and original/adapted commit IDs
alongside new metadata digests. Replay checks all 23 intermediate trees and
retains final tree `bf971ab0f83cf34656bb6671e8078463099d9ee0`. The source segment
remains incomplete, unbuilt and outside selectable series.

V1's 153 already-recovered envelopes, Doged's maintained compatibility patches,
the optional proof-score candidate and eCash's finalized-pruning patch retain
their existing messages. No patch payload changes in this backfill. Run the
repository-wide coverage and payload audit with:

```sh
python3 daemon/scripts/check-patch-metadata.py
python3 -m unittest discover -s daemon/scripts/tests -v
```

The coverage check includes component patches if subsequently tracked, requires
a meaningful subject and explanation for every source patch, validates envelope
author/date fields, and recognizes only explicitly labelled non-patch placeholders.
The reference payload hash guard intentionally fails after a source correction;
update its evidence only alongside an independently reviewed source change.

### Later intentional eCash 01 source correction

The four raw-to-mail tree comparisons above are historical evidence for the metadata-only conversion. The later eCash 01 correction changes source deliberately: it retains the custom snapshot assembler, fixes dependency/fee/resource scheduling with a ready heap, and adds native regressions in one mailbox diff. It is not an upstream restoration. `reference-metadata-provenance.json` retains 01's prior payload/tree/metadata under `history` and records the replacement independently; the other three reference payloads remain unchanged. See [the corrected assembler evidence](ecash01-corrected-snapshot-assembler.md).
