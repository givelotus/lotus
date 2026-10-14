# Packaging license supplements

`MIT.txt` is the standard MIT license template from the SPDX license list:
https://github.com/spdx/license-list-data/blob/main/text/MIT.txt
Its placeholder copyright line is a template, not a claim about dependency
ownership. `DEPENDENCIES.json` supplies original authors and license declarations;
the package retains complete published crate sources for fallback cases to
preserve actual copyright notices.

`Apache-2.0.txt` is the unmodified Apache License 2.0 text also distributed in
`ocl-core-vector-0.1.1/LICENSE-APACHE`. See that directory's `SOURCE.txt` for its
immutable upstream source. Other subdirectories contain unmodified upstream
license supplements with their own `SOURCE.txt` provenance.

The packaging script first preserves distributed license/notice files and
supplements. Where upstream did not distribute license text, it includes the
standard declared MIT or Apache-2.0 license plus the published crate source.
Do not silently fall back for unknown license expressions.
