# EVM behavior translated into Lotus V2 transactions

Status: **architecture candidate, not EVM compatibility or a contract release**. Source/compiler baseline is `9939ab0d881ce9f1791546a0dc57b1e9580cf835`. The executable files use today's compiler. LC-1 listings use the proposed [language and policy ABI](../../script-abi.md#composition-proposal-lc-1-not-implemented); they deliberately have no generated artifacts until implemented. Economic parameters, genesis values, and D10–D14 remain outside this work.

| Conversion | Working evidence here | Proposed or different behavior |
| --- | --- | --- |
| [ERC20, cap, burn, allowance, permit](erc20.md) | Issuer signature and per-mint limit; repeated mint demonstrates why it is not a cap | Authenticated controller, allowance state and nonce permits; expiry and Ethereum signatures differ |
| [ERC721](erc721.md) | Reuses tested holder signature primitive only | Singleton issuance, collection identity, approvals, receiver acceptance; no callback |
| [Safe threshold, timelock, vesting](controls.md) | All three pairs of a 2-of-3 policy; bad signature rejection | Generic threshold helper, stateful key changes, operation tickets, linear vesting |
| [Escrow, 0x-style orders, Uniswap V2](markets.md) | Hash escrow claim/refund and lock operand checks; bounded swap arithmetic | Partial-fill roles, authenticated pool/reserve transitions, LP accounting; expiry/TWAP/callback differences |
| [Proxy upgrade and calls](upgrade-and-calls.md) | Existing CABI-08 linked-library test gate | Explicit authorized state migration; no delegatecall or synchronous reentrancy |

These are behavioral decompositions. A passing authorization slice does not prove its surrounding protocol. Every proposed conversion states which coins carry authority, which transitions must execute, and which original behavior is unavailable. Primary EIPs and exact upstream source revisions are linked beside the relevant claims; [sources.json](sources.json) records immutable commits and source SHA-256 values. Local designs and recommendations are our inference, not claims made by those projects. No upstream contract code is copied into the Lotus sources.

## Run the executable slices

From the repository root, use an isolated Python 3.13 environment with the two checked-in requirements files and build the unchanged compiler:

```sh
npm --prefix tools/lotus-v2-compiler ci --ignore-scripts
npm --prefix tools/lotus-v2-compiler run build
python3.13 -m venv /tmp/lotus-language-examples
/tmp/lotus-language-examples/bin/python -m pip install \
  -r tools/lotus-v2-reference/requirements-vm.txt \
  -r tools/lotus-v2-compiler/test/requirements-vm.txt
LOTUS_V2_PYTHON=/tmp/lotus-language-examples/bin/python \
  node docs/lotus-v2/examples/evm-porting/run.mjs /tmp/lotus-language-evidence
```

The checked-in [summary](evidence/summary.json) records 5 artifacts, 16 VM invocations (9 accepted, 7 rejected), and 5 frontend rejections. [cases.json](evidence/cases.json) retains script bytes, arguments, complete transaction bytes/resolved output bytes when applicable, explicit cost schedule, final stacks and exact engine outcomes. Individual artifact files retain source digest, script/proof/root, ABI, source maps and static resource counts. The runner independently hashes scripts and folds every method's membership proof. Public test scalars 3, 4 and 5 sign only the local examples. It requires a new output directory and refuses to overwrite evidence. Future compiler support is recorded as a successful capability probe alongside the preserved baseline failure; it is not a reason to replace that historical record.

Threshold, escrow and mint cases derive signing/invocation contexts from complete transaction bytes through the Python reference runner. Their input coins are supplied fixtures: outpoint existence, maturity, block lock eligibility and complete block connection are **not** checked. In particular, the successful refund case proves `tx.lock >= bound` with the right lock kind, not that chain height reached that lock. The AMM cases check only arithmetic over supplied witnesses. Costs use an illustrative schedule; these are not selected production CU prices.

The [frontend failure record](evidence/frontend-gaps.json) preserves original sources and diagnostics. `entry`, `policy`, state syntax, division and a data-signature binding are unavailable. A genuine emitter defect is recorded separately: `Amount <= Amount` parses/types but fails emission (`E0403`). The working mint slice uses the equivalent `limit >= delta`; [less-equal.lotus](proposed/less-equal.lotus) preserves the failing input. Rejected frontend cases have `bytecode: null` and were not sent to a VM. Expected VM rejections retain their bytecode and engine output; no consensus or golden fixture was changed to make them pass.

Python 3.14 setup failed while building coincurve 21.0.0 because its cffi distribution license metadata was not found. Python 3.13's pinned wheel succeeded. This is environment evidence, not a contract failure. Existing CABI-08/transaction-runtime checks and exact command outcomes are recorded in the [work plan](../../../plans/lotus-v2-language-composition.md).
