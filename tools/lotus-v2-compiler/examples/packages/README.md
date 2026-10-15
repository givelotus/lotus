# Local package fixture (CABI-07)

`diamond/` is a root contract package with a local diamond dependency graph:

```text
app@0.1.0 (src/main.lotus, src/policy.lotus)
├── lib_a@1.0.0 (limits)      -- import core::amounts::{checkedAdd, atLeast}
├── lib_b@1.0.0 (digests)     -- import amounts_pkg::amounts as amounts
└── both depend on core@1.0.0 (amounts -> internal)
```

`src/main.lotus` shows a renamed selective import (`withinBudget as budgetOk`), a
whole-module alias (`lib_b::digests as digests` with `digests::opens(...)`) and a
package-local import (`package::policy::{authorized}` of a `package function`).
`core@1.0.0/amounts` is parsed and linked once even though both libraries import it.

```sh
npm run build
node dist/package-lock-cli.js examples/packages/diamond --check
node dist/generic-cli.js --package examples/packages/diamond examples/packages/diamond/options.json /tmp/diamond --trace
diff /tmp/diamond/artifact.json examples/packages/diamond/expected-artifact.json
```

`expected-artifact.json` is the golden package artifact (schema 2 plus the optional
`build` graph). `options.json` and `expected-artifact.json` sit outside the root source
root, so they are not modules and are not hashed. Negative cases (duplicate and
builtin-shadowing names, private/package-scoped access, missing module/symbol,
unknown alias, cycles, lock digest mismatch, `..`/absolute/symlink escapes, case and
Unicode collisions, undeclared files, limits) are generated from copies of this
fixture in temporary directories by `test/packages.test.mjs`.
