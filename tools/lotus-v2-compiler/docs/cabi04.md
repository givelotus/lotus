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
| `this.coin.path_count()` / `input.coin.path_count()` / `output.path_count()` | UTXOPATHCOUNT / OUTPUTPATHCOUNT, Int |
| `this.coin.path(i)` / `input.coin.path(i)` / `output.path(i)` | UTXOPATH / OUTPUTPATH, canonical path bytes bounded by 8192 |
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

Stateful allowance coverage is added in the separate packet below; no periodic
reset, expiry or shared global budget semantics are implied.

Partial-fill validation: the compiler suite passed 115 tests without skips; the
subsequent multiple-required-witness preservation check and all CABI04 tests pass
with the expanded helper. No existing fixture bytes or expectations were changed.


## Stateful allowance application policy

The compiler plan names stateful allowances as an open example without defining
recipient selection, cap reset or expiry. StatefulAllowance makes explicit
application choices: one delegated signing key, one fixed recipient policy, a
positive per-call cap and a nonnegative total remaining budget. These constructor
choices are committed in the code policy. They are not consensus parameters or a
proposed general allowance standard. There is no automatic reset, expiry, clock,
issuance or global balance query.

The state coin stores code in branch 0 and `sha256(N(budget))` in unexecuted branch
1. A positive signed spend cannot exceed the cap or remaining budget, and must
leave positive inventory. Exactly two outputs exist: a successor carrying the
same asset with inventory minus amount and state commitment for budget minus
amount, and an exclusive fixed-recipient output carrying exactly amount units.
Budget can reach zero; its successor remains present and rejects further positive
spends. The spent inventory and committed budget are independent: exhausted budget
need not imply exhausted inventory. Withdrawal/reset/termination methods require
a separate policy design and are not implemented in this example.

All input branches are scanned within the P03 cap of 16. Exactly one state-code
root may occur, including optional and late-position roots. The code must be
mandatory on its input; successor code must remain available without executing the
data branch. Path count is exactly one, and canonical path bytes must equal the
constructor-bound `expected_path = 0100` (Vec with one branch index 0), on both
input and successor. This preserves exact `[[0]]` policy while updating only the
separate state commitment; extra redundant paths also reject. Duplicate state
inputs or output roles, missing successor/payment,
recipient changes, asset substitutions and bypass/hostage paths reject.

The fixture uses a native state coin of 100, budget 50 and cap 20. A spend pays
20 to the recipient and leaves inventory 80 / budget 30. A later spend of 10
references the prior transaction's actual TxID/output 0, resolves that exact
successor, and leaves inventory 70 / budget 20. The second fee input uses a distinct
fixture outpoint; no spend-outpoint or chain-state validation is implied. A separate
native input of 10 funds fees; both actual consuming invocations receive FULL
signatures and execute independently. A token-inventory variant also executes,
as does one-unit spending and exact budget exhaustion. Token rules beyond this
example's code/state branches need their own policy layout and independent
invocation fixtures; this is not an arbitrary token-policy migration tool.

Tests reject unsigned/wrong-signer calls, stale budget replay against a successor,
argument and output mutation, cap/budget violations, incorrect decrement, negative
state, wrong amount/asset/recipient, duplicate and extra state inputs/outputs,
branch substitutions and bypass paths. Negative covenant cases are signed again
after mutation so their rejection is not merely a stale signature. Signing/VM
checks do not enforce spent-outpoint replay protection; that remains the enclosing
UTXO validator's responsibility. Exact source, artifacts, resolved coins,
transactions, signatures, results, stacks and charges are exported to
`/private/tmp/cabi04-results/stateful-allowance.json`.

Path introspection is a frontend extension over existing assigned da/db/e5/e6
instructions; no opcode or consensus definition changes. Path reads use the same
receiver checks as branch reads, accept Int indices checked against actual path
counts by the VM, and return bounded canonical byte strings. Dedicated negative
tests cover bad argument types/arity, non-record receivers, negative/large/out-of-range
indices, changed path arrays and redundant paths. Package and standalone allowance
scripts match byte for byte. The test's expected path is explicit application schema
binding, not a new policy encoding or network parameter.

Allowance validation: the complete compiler suite passed 121 tests without skips.
The allowance tests use the integrated expanded Python reference package, preserve
existing golden fixtures unchanged, and introduce no reference or consensus source
changes. Enclosing fee/resource floors, token/native accounting and block acceptance
remain separate from these per-invocation results.
