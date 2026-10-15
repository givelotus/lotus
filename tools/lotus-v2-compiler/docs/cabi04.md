# CABI04 executable state, recovery and covenant packet

This packet executes compiled covenant scripts in the Python P03 reference VM.
It covers a committed counter, signed owner continuation and guardian recovery,
full-fill and partial-fill order settlement, two-input merge and input × output enumeration.
Existing mint/transfer fixtures remain the token coverage. This is invocation
coverage, not complete CABI04 acceptance, transaction accounting or block acceptance.

## Frontend primitives

| Source operation | P03 lowering / result |
| --- | --- |
| `num_bytes(n: Int)` | ADD zero validates canonical signed 16-byte N; returns `Bytes(16)` |
| `this.coin.branch(i)` / `.branch_count()` | INPUTINDEX then UTXOBRANCH / UTXOBRANCHCOUNT |
| `input.coin.branch(i)` / `.branch_count()` | Enumerated input's UTXOBRANCH / UTXOBRANCHCOUNT |
| `input.branch(i)` / `.branch_count()` | Same input reads |
| `output.branch(i)` / `.branch_count()` | OUTPUTBRANCH / OUTPUTBRANCHCOUNT |
| `output.exclusive_branch(root)` | OUTPUTEXCLUSIVEBRANCH, Boolean |
| `output.continues_branch(root)` | OUTPUTCONTINUESBRANCH, Boolean |
| `check_lock(kind, bound)` | CHECKLOCKTIMEVERIFY then true |
| `check_sequence(kind, bound)` | CHECKSEQUENCEVERIFY then true |

Indices and locks require Int operands; policy predicates require ContractRootHash.
Branch reads return Bytes32; counts return Int. Branch indices are checked by the
VM against actual branch counts, including negative and large indices. A failed
lock check errors even if its Boolean result is subsequently combined with other
expressions. There is no current-block height or clock read. These functions also
compile through the package frontend, with parity tests against standalone builds.
Existing golden artifact/script tests continue to pass unchanged.

## Counter representation and successor obligations

Counter stores `sha256(N(counter))` in branch 1 of a two-branch token coin.
Branch 0 is its code root. The data branch is unexecuted: the ordinary selected
path is `[[0]]`, not `[[0,1]]`. The method authenticates the supplied counter by
reading the old data branch, then requires exactly one successor with unchanged
asset/value/code branch and state commitment `sha256(N(counter + 1))`.
OUTPUTEXCLUSIVEBRANCH permits the code-only spend path and rejects a policy which
makes the unexecuted data branch mandatory. Exact branch count and index checks
prevent extra/reordered/substituted commitments. Nonnegative counters are required;
int128 overflow rejects. This is genuine authenticated branch state, with no
fictitious UTXO state field and no token amount consumed to represent a step.

Tests execute counter 0, 9 and maximum-minus-one transitions and reject stale or
skipped state, forged old state, negative counter, overflow, asset/value changes,
missing/duplicate successors, code substitution, branch reordering and policies
that add a hostage branch or bypass code. State hash encoding is independently
constructed with Node's SHA256 over exact little-endian 16-byte integers.

## Vault, order, merge and enumeration

Vault's owner method verifies its signature and preserves exact branches/paths,
amount and asset. A data branch remains unexecuted and unchanged. Recovery verifies
the guardian signature and requires absolute height lock kind 1 with bound 100.
Tests independently sign transactions with locks 99, 100 and 101; 99 rejects and
100/101 accept. Wrong kind, disabled lock, owner impersonating guardian and an
output mutation after signing reject. These are transaction lock-operand checks;
actual candidate height/MTP maturity is an outer node obligation, not executed here.
Relative check_sequence boundaries 4/5/6 with required delay 5 also execute.
All keys are deterministic public test fixtures, never wallet secrets.

LimitOrder constrains exactly one quote settlement output, its fixed amount, and
an exclusive seller policy so an extra mandatory branch cannot hold settlement hostage.
The original LimitOrder remains a small full-fill guard. PartialLimitOrder adds the
complete partial-fill obligations described below. Merge requires exactly
two spend inputs carrying the same asset and sole code branch, sums their values,
and requires one exclusive same-policy successor. Both invocations execute
independently. Wrong counterpart policy/asset and hostage successors reject.
Outpoint uniqueness and execution of every other required branch remain transaction
validator responsibilities. Cartesian preserves asset and mandatory code policy for
every input/output pair and rejects vacuous empty enumeration; it does not enforce
amount conservation or exclusive ownership.

Two diagnostic fixtures remain explicitly unsupported: fictitious `this.state`
access (use real branch commitments), and arbitrary `requires_path` syntax.
Unsupported VM execution fails the tests and never counts as a negative rejection.
Expected source behavior is a manually specified oracle, not an independent
source-language interpreter. No performance measurement or native execution claim
is made.

## Reproduction and retained evidence

From the compiler directory:

```sh
npm ci --ignore-scripts
npm run build
LOTUS_V2_PYTHON=/path/to/reference-venv/bin/python \
LOTUS_V2_VM_REFERENCE_PACKAGE=/path/to/expanded/lotus-v2-reference \
LOTUS_V2_CABI04_RESULTS=/tmp/cabi04-results \
node --test test/cabi04-*.test.mjs
```

The frontend tests depend on expanded reference commit `b37414dc` (or its
successor), specifically authenticated_context and branch/lock instructions.
Local runs used the root integration worktree's reference package and the provided
review Python environment. `cabi04-reference.py` derives signing messages and VM
context from exact transaction, resolved coin and branch proof. Its results retain
full transaction bytes, TxID, TxHash, digest, stack and abstract charge. Signature
attachment uses public fixture keys in Node and reference verification in Python.
Both use established secp256k1 implementations; this is not independent native
execution. No complete transaction accounting validation runs in this helper.

Optional result export writes source, compiler artifact/bytecode, source expectation,
exact invocation/transaction and reference result after each case, before an
assertion can fail. Failures are retained rather than regenerated into passing
expectations. Original first-packet amount-counter/vault behavior was deliberately
superseded by the branch-state counter and signed vault in a separate commit.
Local evidence is at `/private/tmp/cabi04-results`. The complete compiler suite
passed all 111 tests without skips; the final settlement-policy fixture refinement
then passed all 12 CABI04 tests. Existing golden files were unchanged.


## Partial-fill order

`PartialLimitOrder` uses the offered token amount as remaining inventory state.
A call chooses `sold` and the buyer policy. It requires `0 < sold < inventory`
and a positive fixed quote-per-unit price. Offered and quote assets must differ;
buyer/seller policy roots must differ from the order code root. Exactly three
output roles exist: unchanged-policy remainder with inventory minus sold, an
exclusive buyer output containing exactly sold units, and an exclusive seller
output containing exactly sold × price quote units. Additional outputs reject in
this narrow example; a more general wallet transaction needs explicit change roles.
A full fill is intentionally a separate termination method not implemented here.

Exactly one input may carry the offered asset, and exactly one occurrence of the
order root may appear anywhere among all input branches. The source scans all 16
P03-permitted branch positions behind branch-count guards. This presence check
includes roots on optional paths, rather than treating a mandatory-root predicate
as root-presence detection. It prevents a second selected order input from sharing
the same successor/delivery/payment claims, including another asset or a root at
branch index 15. Successor OUTPUTCONTINUESBRANCH preserves every existing policy
branch/path, including unexecuted data commitments. Separate role counters prevent
one output from satisfying multiple obligations or duplicate successor claims.

The exact-transaction harness now supports multiple independently resolved inputs
and independently selected witnesses. A two-branch order/rules path also executes
both obligations independently, and dropping or bypassing the required rules branch
in the remainder rejects. The fixture rules script is a deliberately minimal true
branch, not a production token-rules implementation.
The positive partial-fill transaction has offered-token, quote-token and native-fee
inputs. Its unsigned order invocation executes permissionlessly, then both funding
inputs receive deterministic FULL signatures and all three invocations execute.
The baseline carries 10 offered units into outputs of 6 remaining + 4 delivered,
12 quote units into a seller output of 12, and a native input of 100 with no native
output. This is a locally balanced example; native/token conservation, fee burn,
resource aggregation and block acceptance remain enclosing validator obligations.
A second partial transition (6 → 4 remaining + 2 delivered) executes independently.

Negative cases cover wrong/zero/negative/overfilled quantities, wrong output asset,
price and recipient policy, hostage branches, missing or duplicate role outputs,
extra order inputs including optional and late-position code roots, additional
outputs, state/policy replacement and post-signature output mutation. Exact source,
bytecode, full transaction, commitments, signatures, VM stack/charge and results are
retained in `/private/tmp/cabi04-results/partial-limit-order.json`. A package parity
test preserves the standalone script. `input.coin.requires_branch(root)` is also
available via assigned UTXOREQUIRESBRANCH (`dd`); its every-path semantics remain
distinct from the source's explicit branch-presence scan.

A stateful allowance/spending-cap example remains unimplemented. Counter demonstrates
authenticated numeric state, but it does not authorize a spender, bind a recipient,
or decrement a committed allowance while preserving asset inventory. Completing
that scenario requires its own source and signed transition/replay/substitution
fixtures; it is not implied by the counter or partial-order results.

Partial-fill validation: the compiler suite passed 115 tests without skips; the
subsequent multiple-required-witness preservation check and all CABI04 tests pass
with the expanded helper. No existing fixture bytes or expectations were changed.
