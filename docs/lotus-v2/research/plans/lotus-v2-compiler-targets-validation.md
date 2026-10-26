# Initial compiler target implementation evidence

Development evidence, October 15, 2026. Implements the initial executable slice
of [the target architecture](lotus-v2-compiler-targets-review.md), not complete
cross-chain transaction construction.

## Implemented

- Immutable target descriptors distinguish supported compiler capabilities,
  execution semantics, entrypoint ABI, commitment model and resource limits.
- A validated, source-positioned IR describes exact bytes, Booleans, hashes,
  equality, requirements and conditional branches without chain opcodes.
- The eCash backend emits a separate `ecash/script-artifact/1` artifact with
  explicit revision/profile, source map and static resource accounting.
- `compileTargetContract` and the contract CLI honor explicit target selection.
  Existing Lotus-only APIs reject an eCash target instead of ignoring it.
  Default and explicit Lotus compilation preserve existing artifact bytes.
- The source adapter supports exact `Bytes32` and Boolean parameters and
  constructor bindings, SHA256/HASH256, equality, requirements and branches.
  A selected method produces one script, not a Lotus multi-method policy.

Source `Bytes(n)` is a maximum length, whereas the initial IR byte type is exact
length. Review found and corrected a translation that conflated these meanings:
the source adapter now rejects `Bytes(n)` explicitly. Direct IR exact-length
values remain supported. Helpers, package linking, assignments and optimization
for eCash are explicitly unsupported in this slice. Existing Lotus helper
inlining and package resolution are unchanged. Signatures, transaction reflection,
integer arithmetic, loops and token semantics require further target-specific
work; they do not silently acquire Lotus behavior. No DEFINE/INVOKE instruction
is emitted. Payload data bytes are distinct from decoded instructions.

## Validation

The actual Bitcoin ABC interpreter is pinned to
`1fb7db17c176cdea8a2c60d887891589382ee4e3`, source tree
`b2e4a0a9f57c593129028352d5dbb0c4ff294cdb`. Its research execution profile uses
that revision's standard script flags plus MINIMALIF; this does not claim those
flags are a network consensus profile. The harness builds its own exact-source
dependencies, with wallet and Chronik disabled.

The independent backend corpus performed 45 native executions: 24 accepted and
21 rejected as expected. Coverage includes SHA256/HASH256 preimages, both branch
outcomes, canonical Boolean arguments, exact byte widths, mixed argument order,
extra arguments, minimal push encodings and resource boundaries. Raw artifacts,
arguments and engine results remain in
`/private/tmp/lotus-v2-ecash-backend-native-final-evidence-20261015.jsonl`;
earlier evidence was preserved separately. The checked-in tests reproduce these
cases when `LOTUS_ECASH_NATIVE` identifies the built harness.

Root integration independently passed all 159 compiler tests, zero failures and
zero skips, including source-to-script native executions and the existing Python
reference tests. Command, from `tools/lotus-v2-compiler`:

```sh
LOTUS_V2_PYTHON=/private/tmp/lotus-v2-compiler-review-venv/bin/python \
LOTUS_ECASH_NATIVE=/private/tmp/lotus-v2-ecash-native-build-20261015/ecash-native \
npm test
```

Log: `/private/tmp/lotus-v2-targets-integrated-tests-20261015.log` (18.16 seconds).
An earlier invocation with system Python failed because `blake3` was absent;
the documented reference environment resolved that dependency. An unset native
harness variable skips its optional execution checks and is not equivalent to
the native evidence above. The Lotus native signing runner was not configured
for this compiler test invocation; prior signed Lotus evidence remains separate.

No complete eCash transaction, wallet signature, mempool acceptance or block
acceptance is established. Lotus consensus rules, daemon mailboxes and native
source are outside this compiler packet.
