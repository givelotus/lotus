# Patch metadata and reproducible replay

V1 patches are single-message `git format-patch` files. Setup imports them with
`git am`, retaining each subject, body, author and author date. Committer identity
is the builder, not an assertion that the original author performed the replay.
Reference series may still contain raw diffs; their synthetic commit messages are
explicitly labeled `Apply patch:` until historical metadata is recovered.

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
