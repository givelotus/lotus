# Pinned eCash native script harness

`ecash-native SCRIPT_HEX ARG_HEX...` executes the actual unmodified Bitcoin ABC
script interpreter at commit `1fb7db17c176cdea8a2c60d887891589382ee4e3`, tree
`b2e4a0a9f57c593129028352d5dbb0c4ff294cdb`. Arguments enter the initial stack
bottom-to-top. An empty argument is the empty hex string, not `00`.

Acceptance comes exclusively from ABC `VerifyScript`. The adapter canonically
pushes the exact argument bytes into a scriptSig, including OP_0/OP_1–16 and
OP_1NEGATE where required. It replays the same native `EvalScript` calls to report
the final or partial stack. It does not implement script evaluation itself.
CLEANSTACK and final truth are therefore native verification results. The
scriptSig is a test adapter for supplied stack items, not a signed transaction.

The explicit compiler research profile is
`ecash-script-minimal-cleanstack-1fb7db17`: exact ABC
`STANDARD_SCRIPT_VERIFY_FLAGS | SCRIPT_VERIFY_MINIMALIF`, mask **15820783**
(`0x00f167ef`). MINIMALIF is an added research restriction, not a claim about
upstream network consensus/default policy. This requires canonical empty/01
values at IF/NOTIF; the compiler must enforce its Boolean ABI at other uses too.
The fixed flags are:

```text
SCRIPT_VERIFY_P2SH
SCRIPT_VERIFY_STRICTENC
SCRIPT_VERIFY_DERSIG
SCRIPT_VERIFY_LOW_S
SCRIPT_VERIFY_SIGPUSHONLY
SCRIPT_VERIFY_MINIMALDATA
SCRIPT_VERIFY_DISCOURAGE_UPGRADABLE_NOPS
SCRIPT_VERIFY_CLEANSTACK
SCRIPT_VERIFY_CHECKLOCKTIMEVERIFY
SCRIPT_VERIFY_CHECKSEQUENCEVERIFY
SCRIPT_VERIFY_MINIMALIF
SCRIPT_VERIFY_NULLFAIL
SCRIPT_ENABLE_SIGHASH_FORKID
SCRIPT_DISALLOW_SEGWIT_RECOVERY
SCRIPT_ENABLE_SCHNORR_MULTISIG
SCRIPT_VERIFY_INPUT_SIGCHECKS
SCRIPT_ENFORCE_SIGCHECKS
```

CLEANSTACK requires the P2SH flag, but this adapter supports direct locking
scripts only; a P2SH envelope returns typed `unsupported`. All signature checks,
CODESEPARATOR, CHECKLOCKTIMEVERIFY and CHECKSEQUENCEVERIFY are unsupported,
including in skipped branches. It has no transaction, amount or signature
context and never presents an empty checker's answer as signature validation.
Decoded 0x89/0x8a instructions are also unsupported; no V2 instruction semantics
are linked. Those byte values inside pushed constants or arguments are valid
data. Other malformed/disabled/unknown instructions and resource limits are
handled by the exact ABC interpreter, including opcode counts and disabled
instructions inside skipped branches.

## Build

Use a new **real `.git` clone**, rather than resetting an existing workspace.
The upstream full CMake configuration requires that layout. For example, using
an existing local ABC repository containing the exact revision:

```sh
git clone --shared /path/to/local/abc-repository /tmp/new-ecash-source
git -C /tmp/new-ecash-source checkout --detach 1fb7db17c176cdea8a2c60d887891589382ee4e3
cmake -S tools/lotus-v2-compiler/test/ecash-native -B /tmp/new-ecash-harness -GNinja \
  -DABC_SOURCE_DIR=/tmp/new-ecash-source
cmake --build /tmp/new-ecash-harness -j4
/tmp/new-ecash-harness/ecash-native --describe
/tmp/new-ecash-harness/ecash-native 6351675168 01
/tmp/new-ecash-harness/ecash-native 6351675168 ''
```

CMake verifies the exact revision/tree, rejects tracked differences and all
untracked/ignored files in the source clone, and repeats that check before each
build. It configures ABC's own complete CMake project in an isolated build
subdirectory with Chronik, wallet, GUI and ZMQ disabled, then builds only the
required static libraries. The harness links those freshly built ABC libraries;
external `ABC_BUILD_DIR`/`ABC_LIBRARIES` inputs are rejected. Thus interpreter
headers and archives come from the same checked source. No V2 library or daemon
patch is used. This is an interpreter build, not full node/test-suite validation.
The current recipe uses Ninja and Unix static archives; macOS arm64 was tested.

`--describe` emits exact revision, tree, `targetProfile`, verification profile,
flag names/mask, and SHA256 of interpreter.cpp, script_flags.h and policy.h. Normal
results include the same provenance plus:

- `status`: `accepted`, `rejected`, `unsupported`, or `malformed_input`.
- `accepted`: the native verification decision, false for unsupported inputs.
- `executed`: false when execution was unavailable or input parsing failed.
- `final_stack`: lowercase hex items from native evaluation, bottom-to-top.
- `error`/`error_code`: native VerifyScript diagnostic/code for executed scripts.
- `evaluation_error`: native replay diagnostic; it may be OK when final truth or
  CLEANSTACK makes VerifyScript reject.
- `script_sig`: the adapter's canonical unlocking bytes.

Execution outcomes return exit 0 so callers must inspect status, not merely the
process exit. Malformed CLI/hex/local capacity failures return exit 1.
Unsupported is distinct from a demonstrated native rejection. Local input caps
allow native script/element/opcount/stack limits to be exercised; they are not
new chain parameters.

## Observed validation

Build source: `/private/tmp/lotus-v2-ecash-interpreter-src-20261015`, exact pin above.
Binary: `/private/tmp/lotus-v2-ecash-native-build-20261015/ecash-native`.
ABC dependency CMake cache records Chronik OFF, wallet OFF and that exact source.

The compiler worker's command passed all five tests without skips:

```sh
LOTUS_ECASH_NATIVE=/private/tmp/lotus-v2-ecash-native-build-20261015/ecash-native \
  node --test test/ecash.test.mjs
```

An additional 37 native vectors passed: SHA256/HASH256 correct and wrong digest,
31/33-byte width failures, extra-argument CLEANSTACK, mixed Bytes/Bool ordering in
both directions and both IF arms, malformed Boolean 00, DUP/PICK, canonical and
nonminimal pushes, reserved byte values as data, 201/202 operation boundaries,
skipped-branch counts/disabled opcodes, oversized script, 1001 initial stack
items, 520/521-byte pushes, and typed unsupported capability cases. Evidence:
`/private/tmp/lotus-v2-ecash-native-corpus-20261015.json` and
`/private/tmp/lotus-v2-ecash-compiler-native-20261015.log`.

Configure rejection evidence is retained separately for a wrong source pin and
attempted prebuilt library injection. No node, sockets, mainnet data or existing
workspace were used or reset.
