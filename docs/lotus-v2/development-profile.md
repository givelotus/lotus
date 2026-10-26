# Separate Lotus V2 development profile proposal

Status: **exact proposed test profile; not selected for deployment**. This document proposes a separate development-only profile and supplies its values, canonical parameter bytes, complete genesis and a funded first-block example. It does not change the existing zero-ChainID fixtures or adopt mainnet parameters. The candidate name is `lotus-v2-devnet-20261015-absolute1`; balances are disposable test coins. Implementation and launch follow the review gates in [peering milestones](research/plans/lotus-v2-peering-milestones.md).

“Separate” means a distinct ChainID, genesis, profile digest, network magic and datadir namespace. Nodes using this profile can agree on exactly which development chain to validate. Existing fixture values remain available for their original tests. After review and implementation, changing any consensus parameter requires a new development network name/ChainID and reset; it is not an in-place monetary upgrade. Mainnet D10–D14 stay open. The selected development P2P/RPC defaults are **10605/10604**.

## 1. Exact identity, time and target

| Parameter | Proposed value and reason |
| --- | --- |
| Name | `lotus-v2-devnet-20261015-absolute1`, a versioned disposable network |
| ChainID | `BLAKE3(ASCII("Lotus/v2/development-chain") \|\| 00 \|\| ASCII(name))`; chosen from the name alone, before genesis or profile hashing |
| Header / transaction version | 2 / 7, exact P04/P01 layouts |
| Genesis time | **1792022400**, `2026-10-15T00:00:00Z`, an ordinary UTC timestamp |
| Genesis bits / maximum target | `0x207fffff`; `pow_limit = 0x7fffff << 232`, exactly the decoded canonical target |
| Genesis work / initial previous work | `floor(2^256/(pow_limit+1)) = 2`; the target and monetary record agree |
| ASERT anchor | Genesis target/time/height 0; existing genesis-anchored P04 algorithm |
| Target spacing / half-life | **120 / 172800 seconds**, passed explicitly to the header API, with no new implicit library defaults |
| Median-time rule | Child time strictly greater than the sorted median of up to 11 authenticated ancestor times; initial even sample uses index `floor(n/2)` |
| Future eligibility | Child time must be at most injected current UTC seconds + **7200** for activation/relay; too-future blocks are deferred and reconsidered as time advances, never permanently invalidated on that basis |
| Coinbase maturity | **2** blocks; a coin created at height 1 can first be spent at height 3 |
| Avalanche | Disabled in this development profile; no payout split, staking reward or polling-dependent validity is added |

The easy target has about a one-half success probability per nonce. This tests the real header hash/PoW path without needing a mining farm; it provides no production attack resistance. ASERT still runs normally. Reproducible fixture children use `genesis_time + 120*height`; a running development node uses actual time and the same target algorithm. It may mine faster only while its timestamp remains eligible. Fast long tests should inject a shared test clock, not weaken consensus or silently turn off ASERT.

The future window is a proposed development eligibility policy with a named clock dependency, not a pure function of chain history. Use local UTC or an explicit test clock, not a peer-adjusted time source; a backward clock jump defers eligibility and never rewrites committed state. Keep future headers/bodies in bounded retry queues. The existing contextual-header module deliberately does not enforce this external-clock rule: networking integration must add and test it. Genesis itself is the manifest-pinned initialization block, not subject to post-genesis recurrence or a rolling clock test.

## 2. Monetary parameters and actual affordability

All values below are atoms unless specified; `1 XPI = 1,000,000 atoms`. These are proposed development constants, not economic recommendations. P06 uses absolute formula version 1: derive the paid tail from authenticated parent work with immutable anchors 1000000/2, and the next cache from current work. Cached tail/work must match this derivation.

| Parameter | Exact proposed value |
| --- | --- |
| Bootstrap shift | `k_boot = 20` |
| Initial reserve | `R0 = 1,048,576,000,000 = 2^20 * 1,000,000` atoms, or 1,048,576 test XPI |
| Initial tail / minimum tail | `T0 = Tmin = 1,000,000` atoms, or 1 test XPI |
| Maximum tail | `Tmax = 1,000,000,000` atoms, or 1000 test XPI |
| Initial previous work | `W_-1 = 2`, derived from genesis target |
| Initial / minimum EMA | `E0 = Emin = 65,536 cu` |
| Transaction knee / EMA shift | `S_tx_knee = 17`, `w = 10` |
| Block burn shifts | `S_linear = 64`, `S_quad = 32` |
| Minimum byte fee | `1000 atoms / 1000 bytes` |
| Token dust parameter | `DUST_LIMIT = 546`, hence mandatory burn minimum `1092 atoms` per token-bearing output |
| Genesis native issuance | Exactly zero; recurrence and recurring fee/EMA deductions do not run at genesis |
| Amount / aggregate widths | Individual values u64; checked asset/fee sums u128; tail numerator checked u384, as in the existing models |

No additional native-output dust threshold is proposed. C14a token burn and the ordinary byte-fee floor apply independently to the same fee; they are not added as two minimum fees. Existing 50% remaining-fee burn, underclaim, explicit-burn accounting and token conservation remain in force.

The bootstrap and tail each contribute 1,000,000 atoms to height 1, so its gross entitlement is **2,000,000 atoms**. This is computed from the selected state, never supplied as a caller override. The initial reserve is fully telescoping under the existing recurrence. With target work 2 at both genesis and the first block, the next tail stays 1,000,000.

The burn shifts are deliberately gentle test values. For the exact 103-byte spendable coinbase example below, the conservative outer schedule gives `L=5,437`, envelope cost `993`, and `C_block=6,655`. At initial EMA 65,536:

```text
R = ((6,655 * 65,536) >> 64) + ((6,655^2) >> 32) = 0
K = 103 + 134 + 4 + 1 = 242 atoms
U_required = max(K, R) = 242 atoms
payout = 2,000,000 - 242 = 1,999,758 atoms
```

All transaction, state and envelope costs are computed; a zero rounded parabolic floor does not waive the real byte charge. The resulting state is `(reserve=1,048,575,000,000, tail=1,000,000, work=2, EMA=65,478)`.

The choice of linear shift 64 also gives a useful liveness bound. For this fixed minimal spendable coinbase template and **every representable u64 EMA**, `R <= 6,654`; the quadratic term is zero. Even after the bootstrap reserve is exhausted, `Tmin=1,000,000` covers `max(K,R)` and leaves a positive payout. At maximum EMA, the next EMA for this small block decreases and fits u64. This proves affordability for that template and this schedule, not for every larger coinbase, arbitrary workload or future extension. Shift 20 would not give this all-EMA bound; we do not copy that choice without its liveness analysis.

## 3. Structural bounds and complete cost schedule

These are exact development profile bounds. They are enforced before allocation or mutation where applicable. P01–P06 define the underlying grammar/semantics; their document digests and the opcode-registry digest are included in the canonical parameter artifact to identify the reviewed proposal precisely.

| Boundary | Value |
| --- | --- |
| Inputs / outputs / mint inputs per transaction | 256 / 256 / 256; ordinary transactions still need a consuming input, so a transaction cannot contain 256 mints and another input |
| Output branches / paths | 16 / 16, with all existing distinct/sorted/nonempty rules |
| Encoded output / coin | 812 / 868 bytes |
| Script / element / argument bytes | 8192 / 8192 / 8192 |
| Arguments per witness | 64 |
| Branch membership siblings | 64 |
| Main / alternate stack entries | 256 / 256 |
| Combined runtime stack bytes | 1,048,576 |
| Syntax depth / loop depth | 64 / 2; generic enumeration charges bound 256 |
| Per-invocation static charge | 100,000,000 cu, with checked u128 intermediate algebra |
| Block transaction count | u32 maximum, 4,294,967,295; transport/remaining-byte checks prevent count-driven allocations |
| Total invocation charge | Checked u128 sum; no additional development block-invocation ceiling |
| Complete transaction / block bytes | No new consensus MAX_TX_BYTES/MAX_BLOCK_BYTES; P05 effective costs and exact framing apply |

Unimplemented assigned instructions are unsupported implementation errors, never accepted as success. Note: the `2026-10-15` snapshot below pins the historical `215 assigned / 41 success` registry (`fb790b230e76befc90a1f183ea727cb3232d1f03e9b5838b10d025d96b9832da`) and pre-pipelined reference package `6ed3c828`; the current specification ([`P03`](decisions/vm-semantics.md), [`tools/opcodes.json`](tools/opcodes.json), [`consensus.md` C03/C17](consensus.md)) updates the opcode allocation to **225 assigned / 31 success** (adding `EMITLOG`, `ENFORCEOUTPUT`, `STATEVERIFY`, `STATEHASH`, `ENUMERATE`, conditional `BREAK`, and `EXT2`), appends the 32-byte `history_root` to post-genesis `MonetaryState` (`88B` at $h \ge 1$), and pipelines post-genesis coinbase UTXO insertion by one block (`h -> h+1`, whereas line 257 of the historical `2026-10-15` script below inserted Block 1's coinbase directly at height 1). Success-scan consensus behavior and relay refusal follow P03. There are no activated opcode extensions in this profile. Monetary accounting and enforcement use the same genesis schedule. A native host `max_steps` guard is operational: reaching it must return an implementation/resource failure, not a new consensus-invalid result. Set it high enough for tested permitted invocations and retain the static-cost gate.

For each assigned opcode, charge `base + sum(operand_size_bounds) + sum(result_size_bounds)`, with P05's size analysis, control/loop algebra and separate structural charge **1 cu per script byte**. The complete base table is specified by these disjoint overrides; every other assigned byte has base 1:

| Opcodes | Base cu |
| --- | --- |
| `98..b4`, except `b3` | 1000 |
| `b3` LOG | 10000 |
| `b9` HASH256, `be` LEAFHASH, `bf` NODEHASH | 64 |
| `bb` CHECKSIG, `bc` CHECKSIGVERIFY, `bd` CHECKDATASIG | 50000 |
| `c2` SIGHASH | 256 |

The signature base includes the bounded signing-message hashing; the same CHECKDATASIG base covers all four defined algorithms. SHA256/BLAKE3 bases plus byte terms, explicit double-hash/domain allowances and fixed signing-preimage allowance make all charges reproducible. They are **uncalibrated test weights**, not benchmarked worst-case CPU guarantees. Merkle opcodes add per-step charges: selector 0 uses BLAKE3 with a 96-byte conservative tagged input bound; selector 1 uses BLAKE3 over 64 bytes; selectors 2/3 use SHA256/HASH256 over 64 bytes; each result bound is 32 bytes. A nonconstant selector uses the maximum of all four. Under this table those charges are 129/97/97/160, so the maximum is 160 and also agrees with P05's maximum-of-hash-families wording for this particular schedule. Use the full P05 bound on steps, not runtime early exit.

Outer transaction/block accounting uses the **explicit proposed conservative model** `conservative-block-cost-1`, implemented by the separately reviewed `block_cost.py` snapshot with SHA256 `b2e782254ab04844c9a0487cb8bbbc5e106d2549e631809c97e5a3104ea6f876`. The generator verifies that source digest. This digest identifies the proposed charge algorithm; it is not a requirement to execute Python or build the same binary. An equivalent native implementation must reproduce its integers. `BlockCostProfile(hash_base,hash_byte,resolve_byte,asset_comparison)=(1,1,1,1)`.

For clarity, the model's complete accounting recipe is:

- Write `h(n)=1+(n+64)`, `c(n)=len(CS(n))`, I=input count, O=output count and S=spend count. All hash charges reserve 64 domain-prefix bytes, even where the actual tag is shorter.
- Start L with exact full transaction bytes + summed charged invocations + `2*h(112)` for TxID/TxHash. For each input add `h(len(InputCore))+h(len(InputFull))`; for each revealed witness add `h(1+c(script_len)+script_len)+siblings*h(65)`.
- For each spending input, add encoded coin bytes for resolution, `h(c(output_len)+output_len)`, `h(core_len+c(output_len)+output_len)`, 256 comparison units, and one state-key charge. Each mint adds `h(0)` for its empty coin entry. Coinbase adds no coin-resolution/signing-coin charge.
- Add indexed-tree allowance `(A*max(I,1)+2*max(O,1))*h(66)`, with A=4 for coinbase and 6 otherwise. For every output add `h(c(output_len)+output_len)` and, for a spendable output, one state-key charge. Burn outputs create no state key.
- A state-key charge for a coin of serialized length n is `h(36)+h(33+c(n)+n)+27*h(67)`. It reserves 27 collapsed sparse levels rather than charging a cache-dependent or typical path. The value of the outpoint hash does not change the charge.
- Add `(r*r+r+S)` comparison units with r=I+O, covering conservative deterministic asset accumulation. Require final L to fit u64, then apply the existing knee formula with checked u128 square.
- For N block transactions and total frame-prefix bytes F, `C_envelope=138+F+(N*N+N)+(2*N-1)*h(65)+h(37)+h(130)+h(116)+h(50)+h(64)`. This includes bounded duplicate-ID comparison work, transaction-root hashing, state envelope and recursive header hashing. Accumulate block costs in checked u128.

This model intentionally overcounts some tree work and reserves quadratic comparisons. The model does not price reference-oracle view copying/rebuilding or redundant authenticated-history verification; those implementation bookkeeping costs still need measurement and bounded integration. It is a concrete candidate for development conformance, not a declaration that the open mainnet P05 cost schedule is calibrated or frozen. A revised model requires a revised parameter/profile artifact. All semantic cost inputs are derived from parsed transactions and authenticated coins; callers cannot supply free-form per-block charges to authorize acceptance.

## 4. Genesis and first-block construction

Genesis is a complete **240-byte block**: 134-byte header, u32 transaction count 1, one-byte frame length 101 and the 101-byte P01 coinbase. Coinbase version is 7, lock zero, one flags-02 input naming zero parent/height 0, sequence `ffffffff`, absent CoinbaseData, and one native `IS_BURN` output of value zero. Its one branch word is `H("Lotus/v2/development-genesis-note", ASCII(name))`, with no paths. This opaque commitment is legal C05 burn data; no new VM hash domain or instruction is added. It creates no UTXO and no genesis endowment. The committed initial MonetaryState is unchanged by genesis.

Compute both coinbase identities, the P02 ordered count-bound transaction root and the state root of the empty UTXO map plus initial monetary record. Set height/previous ID to zero and size to 240. Search nonce from zero upward at the exact easy target. The nonce is the first valid value found by the documented deterministic search. No genesis field depends on the profile digest or on a signature committing back to genesis. The separately published profile digest binds the selected parameter bytes; the outer manifest then binds that digest to exact genesis bytes and BlockID.

The first-block example uses time genesis+120, the genesis BlockID as parent and target work 2. Its coinbase has one ordinary spendable native output to the single-leaf script `PUSH32(79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798) CHECKSIG`, with one path `[0]`, and value 1,999,758. This is the public secp256k1 fixture key for scalar 1, deliberately usable by anyone running these tests. It is not a treasury or a required ongoing payout destination. Later miners choose their own legal output policies within the same total entitlement. No spend signature executes in this coinbase-only example.

## 5. Canonical parameter artifact and transport settings

The executable construction below is also the exact canonical parameter-file recipe. Its dictionary contains only ASCII keys and string/unsigned-decimal values (opcode rows use `base,operand_coefficient,result_coefficient`). Serialize the exact ASCII prefix `Lotus/v2/development-profile/1` followed by LF, then every key in increasing ASCII order as `key=value` followed by LF, with no spaces, CR, BOM or extra final newline. Keys/values may not contain newline or `=`. Decimal integers have no sign or leading zeros except zero itself. Expand all 215 assigned opcode rows. The values in that dictionary and tables above must agree.

The ChainID is computed from the independent name before creating this stream. `profile_digest=BLAKE3(ASCII("Lotus/v2/p2p/profile") || 00 || parameter_bytes)`. Neither digest nor genesis hash occurs inside parameter bytes. Outer manifest JSON is human/machine reporting only: its JSON formatting is not a hashed consensus preimage.

Proposed TCP magic is `d7 6c 32 a9`, matching the [peering proposal](peering.md); TCP 10605 and authenticated loopback RPC 10604 use the selected development defaults. Proposed future QUIC uses UDP 10605. Transport revision 1 and features `0x07` follow N02. Initially receive cap is 2 MiB, negotiable within 1..16 MiB as specified there. Transport values are outside the consensus parameter stream. No seeds, checkpoints, assumevalid, assumeutxo, production addresses or wallet prefix are selected. Use explicit loopback peers, separate namespace `lotus-v2-devnet-20261015-absolute1`, and automatically allocated test ports rather than occupied defaults.

The receive cap is local transport capacity, not a new consensus byte ceiling. Valid larger blocks can exceed the initial peering implementation; N05's availability follow-up remains required before general-network claims. Proposed operational defaults are a 10-second handshake timeout, 16 in-flight blocks per peer, 64 globally, 256 MiB mempool, 1 GiB received-body staging quota and disabled automatic public discovery. These limits are cancel/retry/refusal policy, never permanent-invalid cache keys. Peer scheduling/resource measurements and separate disk-magic/schema allocation remain implementation gates.

## 6. Verification evidence and remaining gates

The scratch construction was run with the isolated Python environment against reference packet `6ed3c828` (including its contextual-header and VM prerequisites) and the monetary review candidate's `block_wire`, `block_cost` and `connect_complete_block` modules. It checked exact full framing and identity roots, genesis PoW and initial state, target/work equality, the actual first-block resource deduction, one-atom overclaim rejection without state mutation, contextual child ASERT/PoW/state validation, and connect/disconnect back to the empty genesis UTXO state and identical 56-byte monetary record. It also checked the all-u64-EMA affordability bound algebraically. The future-time check used an explicit injected clock. This is **reference in-memory evidence**, not daemon networking, native whole-chain parity, a persistent-database test or production capacity validation.

Before selecting this profile for a runnable devnet, review its monetary/cost choices, finish native/reference agreement for these exact artifacts and signed mature spends, add the external-clock eligibility gate, validate persistent initialization/undo/reorg, and integrate the reviewed TCP protocol. Tests must include maturity rejection at height 2 and a signed spend at height 3, signatures/arguments with identical TxID but different TxHash, resource/coinbase overclaims and corrupted roots. Missing implementations fail closed as unsupported; they do not silently tighten the profile. D10–D14 production constants, public network identity/seeds, calibrated performance costs, address format and public QUIC identity remain open.

The source-digest assertion in the script intentionally rejects a changed cost model. Re-review and regenerate the candidate after a semantic change; do not update only the expected output to make it pass. The existing fixture functions and their constants must remain unchanged.

## 7. Reproduction code and expected artifacts

Run this Python in an empty temporary directory with `PYTHONPATH` pointing to the reviewed reference package (the baseline before the monetary packet does not contain these APIs). It writes parameter/report files only; it opens no sockets or node/datadir. The reference package must include the pinned outer cost model and the contextual-header/complete-block candidate. Save the code as `make_dev_profile.py`, then use the isolated Python environment. The code is a proposal/verifier embedded in documentation, not an installed node configuration.

```python
from dataclasses import replace
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from blake3 import blake3
from lotus_v2_reference.block import (Coin, Parent, branch_leaf, empty_utxo_root,
    state_root, utxo_root, connect_complete_block, disconnect)
from lotus_v2_reference.block_cost import (BlockCostProfile,
    authenticated_transaction_costs, authenticated_envelope_cost)
from lotus_v2_reference.block_wire import (complete_transaction_root,
    encode_block_wire, decode_block_wire)
from lotus_v2_reference.block_seal import Header, block_id
from lotus_v2_reference.header_context import HeaderChainProfile
from lotus_v2_reference.asert import compact_decode
from lotus_v2_reference.encoding import Output
from lotus_v2_reference.signing import TxProfile, Input, Transaction, encode_transaction, identity_digests
from lotus_v2_reference.monetary import Profile, initialize_genesis, block_cost, required_block_burn, advance
from lotus_v2_reference.vm import ASSIGNED, VMProfile

def H(tag, payload):
    return blake3(tag.encode('ascii') + b'\0' + payload).digest()
name = 'lotus-v2-devnet-20261015-absolute1'
chain = H('Lotus/v2/development-chain', name.encode('ascii'))
t0 = int(datetime(2026, 10, 15, tzinfo=timezone.utc).timestamp())
limit = 0x7fffff << 232
p = dict(name=name, chain_id=chain.hex(), header_version=2, transaction_version=7,
    genesis_time=t0, genesis_bits=0x207fffff, pow_limit=limit,
    spacing_seconds=120, half_life_seconds=172800, mtp_window=11,
    coinbase_maturity=2, boot_shift=20, bootstrap_reserve=1048576000000,
    tail_formula_version=1, genesis_tail=1000000, genesis_work=2,
    initial_tail=1000000, tail_min=1000000, tail_max=1000000000,
    initial_work=2, initial_ema=65536, ema_min=65536, ema_shift=10,
    tx_knee_shift=17, linear_shift=64, quad_shift=32,
    dust_limit=546, min_fee_per_kb=1000,
    max_inputs=256, max_outputs=256, max_mints=256,
    max_output_branches=16, max_output_paths=16, max_output_bytes=812,
    max_coin_bytes=868, max_script_bytes=8192, max_arguments=64,
    max_element_bytes=8192, max_branch_proof_depth=64,
    max_stack_items=256, max_altstack_items=256, max_vm_bytes=1048576,
    max_ast_depth=64, max_loop_depth=2, max_generic_iterations=256,
    max_invocation_cost=100000000, structural_byte_cost=1,
    max_block_transactions=4294967295, max_block_invocation_sum=(1<<128)-1,
    outer_schedule='conservative-block-cost-1',
    outer_model_sha256='b2e782254ab04844c9a0487cb8bbbc5e106d2549e631809c97e5a3104ea6f876',
    future_rule='local-utc-plus-window-retry', future_window_seconds=7200,
    hash_base=1, hash_byte=1,
    resolve_byte=1, asset_comparison=1,
    opcode_registry_sha256='fb790b230e76befc90a1f183ea727cb3232d1f03e9b5838b10d025d96b9832da',
    accounting_extensions='none', avalanche_payout_policy='disabled',
    max_amount=(1<<64)-1, max_aggregate=(1<<128)-1,
    max_tail_numerator=(1<<384)-1,
    p01_sha256='ccadd12af570de5014ac05e8e5db2a6a42a69e09a90120e9b31431104482faa7',
    p02_sha256='b63f7c39a1c68b63379fd51ec959f34061b7b1c4dc76622aafb096c6bcc5a780',
    p03_sha256='326a84e29544f486d37007c88eeefe868ffb797484199509a895fb672b1f3af4',
    p04_sha256='2651bfe7b9b516129133327da30116ceb6cf448cab15aef7111906327a367e4c',
    p05_sha256='90eb7379660f37737a3a6c98d5a1938e120eb6be04d9076dd01d4b4e93ded2fb',
    p06_sha256='8032d2088a3eeb5fecab11a7288aa9b0fa06efdef5712585bb51fdcac01857da')
import lotus_v2_reference.block_cost as cost_model
assert sha256(Path(cost_model.__file__).read_bytes()).hexdigest()==p['outer_model_sha256']
base = {op:1 for op in ASSIGNED}
for op in range(0x98, 0xb5): base[op] = 1000
base[0xb3] = 10000  # LOG: fixed 64-round path
base[0xb9] = 64     # HASH256: double-hash schedule
base[0xbe] = base[0xbf] = 64  # application hash prefix allowance
base[0xc2] = 256    # fixed-size signing preimage allowance
for op in (0xbb, 0xbc, 0xbd): base[op] = 50000
for op in sorted(ASSIGNED):
    p[f'opcode_{op:02x}'] = f'{base[op]},1,1'
params = ('Lotus/v2/development-profile/1\n' + ''.join(
    f'{key}={p[key]}\n' for key in sorted(p))).encode('ascii')
profile_digest = H('Lotus/v2/p2p/profile', params)
TX = TxProfile(256,256,256,8192,64,8192,64)
M = Profile(20,17,10,65536,64,32,1000000,1000000000,546,1000,1000000,2)
COST = BlockCostProfile(1,1,1,1)
VM = VMProfile(8192,64,8192,256,256,1048576,64,100000000,1,
    {op:(lambda operands, results, b=b: b+sum(operands)+sum(results)) for op,b in base.items()})
initial = initialize_genesis(M, bootstrap_reserve=1048576000000,
    tail_subsidy=1000000, genesis_work=2, ema_block_cost=65536)
assert compact_decode(0x207fffff,limit)==limit
assert (1<<256)//(limit+1)==initial.prev_work
note = H('Lotus/v2/development-genesis-note', name.encode('ascii'))
gtx = Transaction(0,(Input(bytes(32),0,0xffffffff,2),),
    (Output(2,0,None,(note,),()),))
assert len(encode_transaction(gtx,TX))==101

def mine(header):
    for nonce in range(1<<64):
        h=replace(header,nonce=nonce)
        if int.from_bytes(block_id(chain,h),'little')<=limit:return h
    raise RuntimeError('nonce exhaustion')
genesis = mine(Header(bytes(32),0x207fffff,t0,0,2,240,0,
    complete_transaction_root((gtx,),TX,chain), state_root(chain,0,empty_utxo_root(),initial)))
gwire = encode_block_wire(genesis,(gtx,),TX)
assert decode_block_wire(gwire,TX,chain).transactions==(gtx,)
# All genesis native outputs total zero; its sole IS_BURN output is pruned.
assert sum(o.value for o in gtx.outputs)==0 and gtx.outputs[0].flags==2
pubkey=bytes.fromhex('79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798')
script=b'\x20'+pubkey+b'\xbb'
policy=branch_leaf(script)
cb=Transaction(0,(Input(block_id(chain,genesis),1,0xffffffff,2),),
    (Output(0,0,None,(policy,),((0,),)),))
linear=authenticated_transaction_costs(cb,TX,{},1,t0,0,COST).account_linear
envelope=authenticated_envelope_cost(1,1,COST)
cost=block_cost(envelope,(linear,),M)
floor=required_block_burn(cost,initial.ema_block_cost,M)
assert required_block_burn(cost,(1<<64)-1,M)<M.tail_min
payout=2000000-max(242,floor)
cb=replace(cb,outputs=(replace(cb.outputs[0],value=payout),))
tr=advance(M,initial,work=2,transactions=(),coinbase_native_outputs=payout,
    coinbase_native_burn=0,coinbase_bytes=103,tx_frame_prefix_bytes=1,
    account_block_cost=cost,enforce_block_cost=cost)
id1=identity_digests(cb,TX,chain)
coin=Coin(id1.txid,0,payout,policy,1,t0,True,cb.outputs[0])
root=utxo_root({coin.key():coin})
first=mine(Header(block_id(chain,genesis),0x207fffff,t0+120,0,2,242,1,
    complete_transaction_root((cb,),TX,chain),state_root(chain,1,root,tr.state)))
fwire=encode_block_wire(first,(cb,),TX)
parent=Parent(chain,0,t0,genesis.state_root,initial,genesis)
hp=HeaderChainProfile(chain,2,t0,0x207fffff,limit,172800,120)
coins={}
bad_cb=replace(cb,outputs=(replace(cb.outputs[0],value=payout+1),))
bad_header=mine(replace(first,tx_root=complete_transaction_root((bad_cb,),TX,chain)))
bad_wire=encode_block_wire(bad_header,(bad_cb,),TX)
try:
    connect_complete_block(bad_wire,parent,[genesis],hp,coins,initial,M,COST,
        tx_profile=TX,vm_profile=VM,block_cap=(1<<128)-1,coinbase_maturity=2)
    raise AssertionError('overclaim accepted')
except ValueError as error:
    assert 'coinbase overclaims' in str(error) and coins=={}
accepted=connect_complete_block(fwire,parent,[genesis],hp,coins,initial,M,COST,
    tx_profile=TX,vm_profile=VM,block_cap=(1<<128)-1,coinbase_maturity=2)
assert accepted.state_root==first.state_root and accepted.monetary_bytes==tr.state.to_bytes()
assert disconnect(accepted.undo,coins)==initial and coins=={}
# External future eligibility rule, with explicitly injected test UTC time.
assert first.time <= (t0+120)+7200
manifest=dict(name=name,chain_id=chain.hex(),profile_digest=profile_digest.hex(),
    genesis_id=block_id(chain,genesis).hex(),genesis_hex=gwire.hex(),
    first_id=block_id(chain,first).hex(),first_hex=fwire.hex(),genesis_nonce=genesis.nonce,
    first_nonce=first.nonce,genesis_time=t0,pow_limit_le=limit.to_bytes(32,'little').hex(),
    initial_state=initial.to_bytes().hex(),first_state=tr.state.to_bytes().hex(),
    linear_cost=linear,envelope_cost=envelope,block_cost=cost,burn_floor=floor,payout=payout,
    genesis_txid=identity_digests(gtx,TX,chain).txid.hex(),
    genesis_txhash=identity_digests(gtx,TX,chain).txhash.hex(),first_txid=id1.txid.hex(),
    genesis_txroot=genesis.tx_root.hex(),genesis_stateroot=genesis.state_root.hex(),
    first_txroot=first.tx_root.hex(),first_stateroot=first.state_root.hex(),
    parameter_bytes=len(params),parameter_sha256=sha256(params).hexdigest(),
    netmagic='d76c32a9',tcp_port=10605,rpc_port=10604,
    future_eligibility_seconds=7200, receive_limit=2097152)
print(json.dumps(manifest,sort_keys=True,indent=2))
Path('lotus-v2-devnet-20261015-absolute1.parameters').write_bytes(params)
Path('lotus-v2-devnet-20261015-absolute1.manifest.json').write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n')
```

Expected artifact identifiers and measurements from that run:

- `chain_id`: `00fee6074719a08dda1bfca8e1d3c9831338af36f493626348ff935551466b80`
- `profile_digest`: `d846ed873bf36a1c2c414221c326f31898c863880de229c1223923128473b177`
- `parameter_bytes`: `5817`
- `parameter_sha256`: `ee122b5068a36925715cf9b4140ce152cc334bdcea0700fb16deca52cd6e6496`
- `genesis_id`: `7b76718e1f49d8bbad83cc6db172d99c7ea1a377802b646975b2a7865eaaed4a`
- `genesis_nonce`: `0`
- `first_id`: `87a602074908bb91959fb5e14216b37f2f2e3f8a0f82b7e6f1aca29ccee1c128`
- `first_nonce`: `0`
- `linear_cost`: `5437`
- `envelope_cost`: `993`
- `block_cost`: `6655`
- `burn_floor`: `0`
- `payout`: `1999758`
- `initial_state`: `00000024f400000040420f000000000002000000000000000000000000000000000000000000000000000000000000000000010000000000`
- `first_state`: `c0bdf023f400000040420f00000000000200000000000000000000000000000000000000000000000000000000000000c6ff000000000000`

Exact genesis block bytes (240 bytes, hexadecimal, digest order):

```text
0000000000000000000000000000000000000000000000000000000000000000ffff7f208017d06a0000000000000000000002000000f0000000000000000000000000000000a07e5c4611c38eba225ab1b32225f094fae68388900b5ffe8d6e853fe50734e9372714a12df138b80f0d36967eb25e8649a9c5f9741fc28bdeea08ab13faf39a010000006507000000000000000000000001000100000000000000000000000000000000000000000000000000000000000000000000000000ffffffff020002000000000000000001882401d84d04d8d4bd2c90b32a5924cdc5d643c0cf7827f923cfac1506858d3400
```

Exact first block bytes (242 bytes; this is an illustrative mined child, not a checkpoint):

```text
7b76718e1f49d8bbad83cc6db172d99c7ea1a377802b646975b2a7865eaaed4affff7f20f817d06a0000000000000000000002000000f2000000000000000100000000000000fc65566329c5f2498b97ddedfdf06969a159c3543e606aca5b7b8c166c1629fc7285b111fc96547a46d0b41170692ba2fb375fe6ae737a0398bc21f46f751daf0100000067070000000000000000000000010001007b76718e1f49d8bbad83cc6db172d99c7ea1a377802b646975b2a7865eaaed4a01000000ffffffff0200008e831e00000000000159128a347a29ca0178ac8ab3dd868a6a30ab185e9f51dad77c5737e4cbad0526010100
```

Absolute-tail migration: this renamed proposal replaces prior `lotus-v2-devnet-20261015-a`. Historical ChainID `63b5ddca6f75cbc64df5ff128cadd35e8658905595afc290b7698b2419b9745c`, profile digest `384bb3c6cd4f47eb84860ebb56f4ceafebaa6414ebf7f230e85682a2afe8fdd1` and genesis `9dc4d2fa9803bad48ae38ec24027bf55abff952f7e549a738986112848fab629` describe that earlier recurrence proposal. The actual tested controller fixture has separate migration evidence.

---

## References

1. **[Nakamoto 2008]** Satoshi Nakamoto, *"Bitcoin: A Peer-to-Peer Electronic Cash System"*, October 2008 (`https://bitcoin.org/bitcoin.pdf`).
2. **[Chancellor 2026]** Shammah Chancellor, *"Adaptive PoW Monetary Policy Without Oracles: A Constructive Mechanism for Pseudo-Stability via Work-Coupled Tail Emission and Burn"*, Lotus Network Technical Paper, 2026.
3. **[O'Connor, Aumasson, Neves, & Wilcox-O'Hearn 2020]** Jack O'Connor, Jean-Philippe Aumasson, Samuel Neves, and Zooko Wilcox-O'Hearn, *"BLAKE3: One Function, Fast Everywhere"*, January 2020 (`https://github.com/BLAKE3-team/BLAKE3-specs`).
4. **[Lundeberg 2020]** Mark B. Lundeberg, *"ASERT (`aserti3-2d`): Absolutely Scheduled Exponentially Rising Targets"*, Bitcoin Cash Specification, July 2020.
