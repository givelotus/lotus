"""Ordinary-block connect and disconnect for the Python reference.

This mirrors the standalone C++ model: ordered ordinary transactions, one
invocation-cost sum, rollback when that sum exceeds the block cap, and an undo
object that restores the UTXO root and 56-byte monetary record. It does not
parse a block wire, mine, run ASERT, or claim that lotusd accepted a block.

A first payment with kind ``coinbase`` is a development-profile coinbase when
the parent carries a header. Its wire is the flags-2 transaction codec, and
``advance`` receives that output value and encoded length. Ordinary blocks
still pass a zero coinbase payout. The parent work integer is not a new work
rule.

A CHECKSIG witness is retried with the mode-0 sighash from
``lotus_v2_reference.signing``. This is the reference connector, not lotusd
ConnectTip.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import blake3

from .encoding import Output, Profile, decode_output, encode_compact_size, encode_output
from .monetary import MonetaryState, OrdinaryTx, Profile as MonetaryProfile, advance
from .signing import (
    Input, Transaction, TxProfile, Witness, encode_transaction, identity_digests,
    signing_message,
)
from .vm import (
    ASSIGNED, SigningContext, UnsupportedFeature, VMError, VMProfile,
    branch_leaf_hash, evaluate,
)

OUTPUT_PROFILE = Profile(16, 16, 812, 8192)
OP_TRUE = b"\x4e"
# OP_1 pushes a numeric result bounded at 16 bytes. With base = per-result = 1
# and one structural unit per script byte, one empty-argument witness costs 18.
OP_TRUE_COST = 1 + 16 + 1


def _unit_witness_price(operands: tuple[int, ...], results: tuple[int, ...]) -> int:
    return 1 + sum(operands) + sum(results)


# Native ordinary schedule: base 1, per operand byte 1, per result byte 1.
PAYMENT_VM = VMProfile(
    max_script_bytes=512,
    max_arguments=8,
    max_element_bytes=8192,
    max_stack_items=32,
    max_altstack_items=32,
    max_vm_bytes=65536,
    max_ast_depth=16,
    max_invocation_cost=1_000_000,
    structural_byte_cost=1,
    opcode_costs={op: _unit_witness_price for op in ASSIGNED},
)


def tagged(tag: str, payload: bytes) -> bytes:
    hasher = blake3.blake3()
    hasher.update(tag.encode("ascii"))
    hasher.update(b"\x00")
    hasher.update(payload)
    return hasher.digest()


def branch_leaf(script: bytes) -> bytes:
    return tagged("Lotus/v2/branch", bytes([0]) + encode_compact_size(len(script)) + script)


def outpoint_key(tx_id: bytes, index: int) -> bytes:
    return tagged("Lotus/v2/outpointkey", tx_id + index.to_bytes(4, "little"))


def encode_spend_core(tx_id: bytes, index: int, script: bytes = OP_TRUE) -> bytes:
    return (
        tx_id
        + index.to_bytes(4, "little")
        + b"\xff\xff\xff\xff"
        + b"\x01\x00\x01"
        + encode_compact_size(len(script))
        + script
        + b"\x00"
    )


def encode_native_output(value: int, branch: bytes) -> bytes:
    return encode_output(Output(0, value, None, (branch,), ((0,),)), OUTPUT_PROFILE)


def transaction_id(chain_id: bytes, spend_core: bytes, output: bytes) -> bytes:
    header = (7).to_bytes(4, "little") + (0).to_bytes(8, "little")
    header += (1).to_bytes(2, "little") + (1).to_bytes(2, "little")
    inputs_root = tagged("Lotus/v2/inputcore", spend_core)
    outputs_root = tagged("Lotus/v2/output", encode_compact_size(len(output)) + output)
    payload = chain_id + header + inputs_root + outputs_root
    if len(payload) != 112:
        raise ValueError("txid preimage width")
    return tagged("Lotus/v2/txid", payload)


def encode_witness_arguments(arguments: tuple[bytes, ...]) -> bytes:
    encoded = encode_compact_size(len(arguments))
    for argument in arguments:
        encoded += encode_compact_size(len(argument)) + argument
    return encoded


def full_payment_bytes(core: bytes, output: bytes, arguments: tuple[bytes, ...] = ()) -> bytes:
    # Core omits the argument vector. Empty arguments are one zero byte.
    header = (7).to_bytes(4, "little") + (0).to_bytes(8, "little")
    header += (1).to_bytes(2, "little") + (1).to_bytes(2, "little")
    return header + core + encode_witness_arguments(arguments) + output


@dataclass(frozen=True)
class Coin:
    tx_id: bytes
    index: int
    value: int
    branch: bytes
    creation_height: int
    creation_parent_mtp: int
    coinbase: bool = False
    output: Output | None = None

    def key(self) -> tuple[bytes, int]:
        return (self.tx_id, self.index)

    def encode(self) -> bytes:
        output = (encode_output(self.output, OUTPUT_PROFILE) if self.output is not None
                  else encode_native_output(self.value, self.branch))
        body = (
            self.tx_id
            + self.index.to_bytes(4, "little")
            + encode_compact_size(len(output))
            + output
            + self.creation_height.to_bytes(8, "little")
            + self.creation_parent_mtp.to_bytes(8, "little")
            + bytes([1 if self.coinbase else 0])
        )
        if len(body) > 868:
            raise ValueError("coin encoding exceeds MAX_COIN_BYTES")
        return body


def empty_utxo_root() -> bytes:
    return tagged("Lotus/v2/utxo", bytes([2]))


def _bit(key: bytes, depth: int) -> int:
    return (key[depth // 8] >> (depth % 8)) & 1


def utxo_root(coins: dict[tuple[bytes, int], Coin]) -> bytes:
    entries = [(outpoint_key(coin.tx_id, coin.index), coin) for coin in coins.values()]

    def fold(rows: list[tuple[bytes, Coin]], depth: int) -> bytes:
        if not rows:
            return empty_utxo_root()
        if len(rows) == 1:
            raw = rows[0][1].encode()
            payload = bytes([0]) + rows[0][0] + encode_compact_size(len(raw)) + raw
            return tagged("Lotus/v2/utxo", payload)
        left: list[tuple[bytes, Coin]] = []
        right: list[tuple[bytes, Coin]] = []
        for row in rows:
            (right if _bit(row[0], depth) else left).append(row)
        payload = bytes([1, depth & 0xFF, (depth >> 8) & 0xFF])
        payload += fold(left, depth + 1) + fold(right, depth + 1)
        return tagged("Lotus/v2/utxo", payload)

    return fold(entries, 0)


def state_root(chain_id: bytes, height: int, root: bytes, monetary: MonetaryState) -> bytes:
    record = monetary.to_bytes()
    payload = bytes([0]) + chain_id + height.to_bytes(8, "little") + root
    payload += bytes([len(record)]) + record
    if len(payload) != 130:
        raise ValueError("state root preimage width")
    return tagged("Lotus/v2/state", payload)


def _transaction_subtree(identities: tuple[tuple[bytes, bytes], ...]) -> bytes:
    count = len(identities)
    if count == 0:
        return tagged("Lotus/v2/txroot", bytes([2]))
    if count == 1:
        tx_hash, tx_id = identities[0]
        return tagged("Lotus/v2/txroot", bytes([0]) + tx_hash + tx_id)
    # Greatest power of two strictly less than count. Children stay ordered.
    split = 1
    while split < count - split:
        split <<= 1
    left = _transaction_subtree(identities[:split])
    right = _transaction_subtree(identities[split:])
    return tagged("Lotus/v2/txroot", bytes([1]) + left + right)


def transaction_root(identities: tuple[tuple[bytes, bytes], ...]) -> bytes:
    """Count-wrapped ordered root of ``(tx_hash, tx_id)`` pairs.

    Empty is defined for tools. This does not require a coinbase or accept a block.
    """
    if isinstance(identities, (bytes, bytearray)) or not isinstance(identities, (list, tuple)):
        raise ValueError("transaction identities")
    count = len(identities)
    if count > 0xFFFFFFFF:
        raise ValueError("transaction count")
    leaves: list[tuple[bytes, bytes]] = []
    for item in identities:
        if (isinstance(item, (bytes, bytearray)) or not isinstance(item, (list, tuple))
                or len(item) != 2):
            raise ValueError("transaction identity")
        tx_hash, tx_id = item
        if (not isinstance(tx_hash, bytes) or len(tx_hash) != 32
                or not isinstance(tx_id, bytes) or len(tx_id) != 32):
            raise ValueError("transaction identity")
        leaves.append((tx_hash, tx_id))
    payload = bytes([3]) + count.to_bytes(4, "little") + _transaction_subtree(tuple(leaves))
    if len(payload) != 37:
        raise ValueError("transaction root preimage width")
    return tagged("Lotus/v2/txroot", payload)


@dataclass(frozen=True)
class Parent:
    chain_id: bytes
    height: int
    time: int
    state_root: bytes
    monetary: MonetaryState
    # Sealer header. Required only for a development coinbase block id.
    header: object | None = None


@dataclass(frozen=True)
class UndoStep:
    created: bool
    coin: Coin


@dataclass
class Undo:
    steps: list[UndoStep] = field(default_factory=list)
    prior_monetary: MonetaryState | None = None
    prior_utxo_root: bytes = b""
    prior_monetary_bytes: bytes = b""


@dataclass
class Connected:
    utxo_root: bytes
    state_root: bytes
    monetary_bytes: bytes
    transition: object
    undo: Undo
    invocation_cost: int


# Ordinary payment bounds. The sighash profile does not select a fee or locktime rule.
PAYMENT_TX_PROFILE = TxProfile(32, 32, 8, 512, 8, 8192, 64)
_CHECKSIG_CONTEXT = "CHECKSIG requires an authenticated signing context"


@dataclass(frozen=True)
class Payment:
    spent_tx: bytes
    spent_index: int
    value: int
    kind: str = "spend"  # spend, coinbase, or mint
    script: bytes = OP_TRUE
    arguments: tuple[bytes, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.arguments, tuple) or any(
            not isinstance(item, bytes) for item in self.arguments
        ):
            raise ValueError("witness arguments")


def disconnect(undo: Undo, coins: dict[tuple[bytes, int], Coin]) -> MonetaryState:
    """Reverse ``undo.steps`` and return the prior monetary record."""
    for step in reversed(undo.steps):
        key = step.coin.key()
        if step.created:
            if coins.pop(key, None) is None:
                raise ValueError("undo missing created coin")
        elif key in coins:
            raise ValueError("undo cannot restore spent coin")
        else:
            coins[key] = step.coin
    if undo.prior_monetary is None:
        raise ValueError("undo monetary missing")
    if utxo_root(coins) != undo.prior_utxo_root:
        raise ValueError("undo did not restore utxo root")
    if undo.prior_monetary.to_bytes() != undo.prior_monetary_bytes:
        raise ValueError("undo did not restore monetary root")
    return undo.prior_monetary


def _payment_output(value: int, branch: bytes) -> Output:
    return Output(0, value, None, (branch,), ((0,),))


def _mode0_context(tx: Payment, parent: Parent, spent: Coin) -> SigningContext:
    transaction = Transaction(
        0,
        (Input(
            spent.tx_id, spent.index, 0xFFFFFFFF, 1, 0,
            (Witness(tx.script, (), tx.arguments),),
        ),),
        (_payment_output(tx.value, spent.branch),),
    )
    message = signing_message(
        transaction, PAYMENT_TX_PROFILE, parent.chain_id,
        (_payment_output(spent.value, spent.branch),), 0, 0, 0,
    )
    return SigningContext(branch_leaf_hash(tx.script), {0: message}, "spend", 0, 1)


def _witness_charge(tx: Payment, parent: Parent, spent: Coin) -> int:
    # One spend input and one output, matching this payment model.
    # Scripts that do not execute CHECKSIG keep the no-context evaluation.
    try:
        result = evaluate(tx.script, tx.arguments, PAYMENT_VM, input_count=1, output_count=1)
    except UnsupportedFeature as exc:
        if str(exc) != _CHECKSIG_CONTEXT:
            raise ValueError(str(exc)) from exc
        try:
            result = evaluate(
                tx.script, tx.arguments, PAYMENT_VM, input_count=1, output_count=1,
                signing=_mode0_context(tx, parent, spent),
            )
        except VMError as inner:
            raise ValueError(str(inner)) from inner
    except VMError as exc:
        raise ValueError(str(exc)) from exc
    if not result.success:
        raise ValueError("witness VM invalid/unsupported")
    return result.charged_cost


def _apply_one(
    tx: Payment,
    parent: Parent,
    coins: dict[tuple[bytes, int], Coin],
    undo: Undo,
    accounted: list[OrdinaryTx],
    *,
    candidate_height: int,
    parent_mtp: int,
    coinbase_maturity: int,
) -> int:
    if tx.kind == "coinbase":
        raise ValueError("coinbase is not an ordinary transaction")
    spent = coins.get((tx.spent_tx, tx.spent_index))
    if spent is None:
        raise ValueError("unresolved spend")
    delay = coinbase_maturity if spent.coinbase else 0
    if spent.creation_height > candidate_height or candidate_height < spent.creation_height + delay:
        raise ValueError("coinbase maturity or future coin")
    # Fee, locktime, and field-size checks are still the existing block.py rules.
    witness_cost = _witness_charge(tx, parent, spent)
    output = encode_native_output(tx.value, spent.branch)
    core = encode_spend_core(tx.spent_tx, tx.spent_index, tx.script)
    wire = full_payment_bytes(core, output, tx.arguments)
    if tx.value > spent.value or spent.value - tx.value < len(wire):
        raise ValueError("native fee below byte or token-output floor" if tx.value <= spent.value
                         else "native inflation")
    if tx.kind == "mint":
        raise ValueError("mint without matching positive token delta")
    if tx.kind != "spend":
        raise ValueError("unsupported ordinary transaction")
    txid = transaction_id(parent.chain_id, core, output)
    if (txid, 0) in coins:
        raise ValueError("created outpoint already occupied")
    created = Coin(txid, 0, tx.value, spent.branch, candidate_height, parent_mtp, False)
    del coins[spent.key()]
    coins[created.key()] = created
    undo.steps.append(UndoStep(False, spent))
    undo.steps.append(UndoStep(True, created))
    accounted.append(OrdinaryTx(spent.value, tx.value, len(wire), 0, 0))
    return witness_cost


def _apply_coinbase(
    tx: Payment,
    parent: Parent,
    coins: dict[tuple[bytes, int], Coin],
    undo: Undo,
    *,
    candidate_height: int,
    parent_mtp: int,
) -> int:
    """Create one coinbase coin. Returns the encoded transaction length.

    No witness VM and no spent coin. Callers without a parent header keep the
    ordinary-transaction rejection; the block id is not invented.
    """
    if parent.header is None:
        raise ValueError("coinbase is not an ordinary transaction")
    from .block_seal import Header, block_id
    if type(candidate_height) is not int or not 0 <= candidate_height <= 0xFFFFFFFF:
        raise ValueError("coinbase parent/height")
    raw = parent.header
    seal_header = raw if isinstance(raw, Header) else Header(
        getattr(raw, "prev_id"), getattr(raw, "bits"), getattr(raw, "time"),
        getattr(raw, "nonce"), getattr(raw, "version"), getattr(raw, "size"),
        getattr(raw, "height"), getattr(raw, "tx_root"), getattr(raw, "state_root"),
    )
    prev_txid = block_id(parent.chain_id, seal_header)
    transaction = Transaction(
        0,
        (Input(prev_txid, candidate_height, 0xFFFFFFFF, 2, 0, (), None),),
        (_payment_output(tx.value, tx.script),),
    )
    wire = encode_transaction(transaction, PAYMENT_TX_PROFILE)
    txid = identity_digests(transaction, PAYMENT_TX_PROFILE, parent.chain_id).txid
    if (txid, 0) in coins:
        raise ValueError("created outpoint already occupied")
    created = Coin(txid, 0, tx.value, tx.script, candidate_height, parent_mtp, True)
    coins[created.key()] = created
    undo.steps.append(UndoStep(True, created))
    return len(wire)


def connect_ordinary_block(
    transactions: tuple[Payment, ...],
    parent: Parent,
    coins: dict[tuple[bytes, int], Coin],
    monetary: MonetaryState,
    monetary_profile: MonetaryProfile,
    *,
    candidate_height: int,
    parent_mtp: int,
    block_cap: int,
    coinbase_maturity: int = 2,
) -> Connected:
    """Apply ``transactions`` or leave ``coins`` unchanged.

    The returned undo restores both roots. A cost-cap failure is raised only
    after the ordered payments have been validated, then the undo is applied.
    """
    if (parent.height == 2**64 - 1 or candidate_height != parent.height + 1
            or parent_mtp != parent.time or parent.time > (1 << 48) - 1):
        raise ValueError("parent header context")
    if monetary != parent.monetary:
        raise ValueError("parent monetary context")
    root = utxo_root(coins)
    if state_root(parent.chain_id, parent.height, root, monetary) != parent.state_root:
        raise ValueError("parent state root")
    undo = Undo(prior_monetary=monetary, prior_utxo_root=root,
                prior_monetary_bytes=monetary.to_bytes())
    accounted: list[OrdinaryTx] = []
    total_cost = 0
    coinbase_outputs = 0
    coinbase_bytes = 0
    try:
        for index, tx in enumerate(transactions):
            if tx.kind == "coinbase":
                if index != 0:
                    raise ValueError("coinbase is not an ordinary transaction")
                coinbase_bytes = _apply_coinbase(
                    tx, parent, coins, undo,
                    candidate_height=candidate_height, parent_mtp=parent_mtp,
                )
                coinbase_outputs = tx.value
                cost = 0
            else:
                cost = _apply_one(
                    tx, parent, coins, undo, accounted,
                    candidate_height=candidate_height, parent_mtp=parent_mtp,
                    coinbase_maturity=coinbase_maturity,
                )
            if total_cost > (1 << 128) - 1 - cost:
                raise ValueError("block invocation cost overflow")
            total_cost += cost
            if total_cost > block_cap:
                raise ValueError("block invocation cost over cap")
        transition = advance(
            monetary_profile, monetary, work=monetary.prev_work,
            transactions=tuple(accounted),
            coinbase_native_outputs=coinbase_outputs,
            coinbase_native_burn=0, coinbase_bytes=coinbase_bytes,
            tx_frame_prefix_bytes=0,
            account_block_cost=total_cost, enforce_block_cost=total_cost,
        )
    except ValueError:
        disconnect(undo, coins)
        raise
    new_root = utxo_root(coins)
    return Connected(
        new_root,
        state_root(parent.chain_id, candidate_height, new_root, transition.state),
        transition.state.to_bytes(), transition, undo, total_cost,
    )


def write_snapshot(coins: dict[tuple[bytes, int], Coin], monetary: MonetaryState) -> bytes:
    ordered = [coins[key] for key in sorted(coins)]
    if len(ordered) > 65535:
        raise ValueError("snapshot coin cap")
    body = bytearray(b"LV2S")
    body += len(ordered).to_bytes(4, "little")
    for coin in ordered:
        raw = coin.encode()
        body += len(raw).to_bytes(4, "little")
        body += raw
    body += monetary.to_bytes()
    return bytes(body)


def _decode_coin(raw: bytes) -> Coin:
    if len(raw) < 36 + 17:
        raise ValueError("snapshot coin rejected")
    tx_id = raw[:32]
    index = int.from_bytes(raw[32:36], "little")
    output_len = raw[36]
    if output_len >= 253 or 37 + output_len + 17 != len(raw):
        raise ValueError("snapshot coin rejected")
    decoded = decode_output(raw[37:37 + output_len], OUTPUT_PROFILE)
    tail = raw[37 + output_len:]
    if decoded.flags != 0 or decoded.token_id is not None or len(decoded.branches) != 1:
        raise ValueError("snapshot coin rejected")
    if tail[16] > 1:
        raise ValueError("snapshot coin rejected")
    return Coin(
        tx_id, index, decoded.value, decoded.branches[0],
        int.from_bytes(tail[:8], "little"), int.from_bytes(tail[8:16], "little"),
        tail[16] == 1,
    )


def load_snapshot(blob: bytes) -> tuple[dict[tuple[bytes, int], Coin], MonetaryState]:
    if len(blob) < 8 + 56 or blob[:4] != b"LV2S":
        raise ValueError("snapshot header")
    count = int.from_bytes(blob[4:8], "little")
    if count > 65535:
        raise ValueError("snapshot coin count")
    offset = 8
    coins: dict[tuple[bytes, int], Coin] = {}
    for _ in range(count):
        if offset + 4 > len(blob):
            raise ValueError("snapshot coin frame")
        length = int.from_bytes(blob[offset:offset + 4], "little")
        offset += 4
        raw = blob[offset:offset + length]
        offset += length
        if len(raw) != length or not raw:
            raise ValueError("snapshot coin frame")
        coin = _decode_coin(raw)
        if coin.key() in coins:
            raise ValueError("snapshot coin rejected")
        coins[coin.key()] = coin
    record = blob[offset:]
    if len(record) != 56:
        raise ValueError("snapshot monetary frame")
    return coins, MonetaryState.from_bytes(record)


def _coin_output(coin: Coin) -> Output:
    return coin.output or _payment_output(coin.value, coin.branch)


def _complete_ordinary(tx, parent, coins, profile, *, height, mtp,
                       maturity, vm_profile, tx_profile, block_cap):
    """Authenticate full transaction effects; return monetary record and VM sum."""
    from .vm_context import authenticated_context
    from .signing import _prepare
    from .monetary import U128, uint
    raw = encode_transaction(tx, tx_profile)
    spent, resolved = [], []
    native_inputs, native_outputs = 0, 0
    inputs, outputs = {}, {}
    for inp in tx.inputs:
        if inp.flags == 1:
            coin = coins.get((inp.prev_txid, inp.prev_index))
            if coin is None:
                raise ValueError('unresolved spend')
            coin.encode()
            if height < coin.creation_height + (maturity if coin.coinbase else 0):
                raise ValueError('coinbase maturity or future coin')
            if inp.sequence != 0xffffffff:
                delay = inp.sequence & 65535
                if inp.sequence & 0x400000:
                    if mtp < coin.creation_parent_mtp + delay*512:
                        raise ValueError('relative time lock')
                elif height < coin.creation_height + delay:
                    raise ValueError('relative height lock')
            output = _coin_output(coin)
            spent.append(coin)
            resolved.append(output)
            if output.flags & 1:
                inputs[output.token_id] = uint(inputs.get(output.token_id, 0)+output.value, U128, 'token inputs')
            else:
                native_inputs = uint(native_inputs+output.value, U128, 'native inputs')
        else:
            resolved.append(None)
    kind, value = tx.lock & 255, tx.lock >> 8
    if (kind == 1 and height < value) or (kind == 2 and mtp < value):
        raise ValueError('absolute lock')
    explicit_burn = token_count = 0
    for output in tx.outputs:
        if output.flags & 1:
            token_count += 1
            outputs[output.token_id] = uint(outputs.get(output.token_id, 0)+output.value, U128, 'token outputs')
        else:
            native_outputs = uint(native_outputs+output.value, U128, 'native outputs')
            if output.flags & 2:
                explicit_burn += output.value
    if native_inputs < native_outputs:
        raise ValueError('native inflation')
    fee = native_inputs-native_outputs
    if fee < len(raw) or fee < 2*profile.dust_limit*token_count:
        raise ValueError('native fee below byte or token-output floor')
    deltas = {key: amount-inputs.get(key, 0) for key, amount in outputs.items()
              if amount > inputs.get(key, 0)}
    mints = {inp.prev_txid for inp in tx.inputs if inp.flags == 3}
    if mints != set(deltas):
        raise ValueError('positive token delta/mint mismatch')
    # Always authenticate every selected membership, including success-scan
    # invocations. No digest supplied by a caller is used as authorization.
    _prepare(tx, tx_profile, parent.chain_id, tuple(resolved))
    cost = 0
    for i, inp in enumerate(tx.inputs):
        for j, witness in enumerate(inp.witnesses):
            context, signing = authenticated_context(tx, tx_profile,
                parent.chain_id, tuple(resolved), i, j)
            result = evaluate(witness.script, witness.arguments, vm_profile,
                              invocation=context, signing=signing)
            if not result.success:
                raise ValueError('witness VM invalid/unsupported')
            cost = uint(cost+result.charged_cost, U128, 'invocation cost')
            if cost > block_cap:
                raise ValueError('block invocation cost over cap')
    return OrdinaryTx(native_inputs, native_outputs, len(raw), token_count, explicit_burn), cost, spent


def connect_complete_block(wire: bytes, parent: Parent, history, header_profile,
                           coins: dict, monetary: MonetaryState,
                           monetary_profile: MonetaryProfile, cost_profile, *,
                           tx_profile=PAYMENT_TX_PROFILE, vm_profile=PAYMENT_VM,
                           block_cap: int, coinbase_maturity: int = 2) -> Connected:
    """Atomic full framed-block candidate validation, genesis opcode allocation.

    Authenticated oldest history is the caller's responsibility. Development
    copying is an oracle implementation, not a storage-I/O resource proof.
    No persistent state is touched and this is not lotusd acceptance.
    """
    from .block_wire import decode_block_wire
    from .block_cost import authenticated_transaction_costs, authenticated_envelope_cost
    from .header_context import parent_median_time, validate_child_header
    from .asert import compact_decode
    from .monetary import U128, block_cost, uint
    from .block_seal import block_id
    if parent.header is None:
        raise ValueError('parent header required')
    from .block_seal import parse_header
    claimed = parse_header(wire[:134])
    header = parent.header
    if (header_profile.chain_id != parent.chain_id or header.height != parent.height
            or parent.state_root != header.state_root or monetary != parent.monetary):
        raise ValueError('complete parent context')
    mtp = parent_median_time(header_profile, header, history)
    # Claimed roots pass the cheap header gate; their correctness follows from
    # full frame decoding and the final state transition before committing.
    validate_child_header(header_profile, header, history, claimed,
        expected_tx_root=claimed.tx_root, expected_state_root=claimed.state_root,
        expected_size=len(wire))
    block = decode_block_wire(wire, tx_profile, parent.chain_id)
    parent_work = (1 << 256)//(compact_decode(header.bits, header_profile.pow_limit)+1)
    if monetary.prev_work != parent_work:
        raise ValueError('parent monetary work does not match target')
    height = header.height+1
    if height > 0xffffffff:
        raise ValueError('coinbase parent/height')
    child_work = (1 << 256)//(compact_decode(block.header.bits, header_profile.pow_limit)+1)
    before = utxo_root(coins)
    if state_root(parent.chain_id, parent.height, before, monetary) != parent.state_root:
        raise ValueError('parent state root')
    undo = Undo(prior_monetary=monetary, prior_utxo_root=before,
                prior_monetary_bytes=monetary.to_bytes())
    staged = dict(coins)
    accounted, account_linear, enforce_linear = [], [], []
    total_vm = coinbase_outputs = coinbase_burn = coinbase_bytes = 0
    for n, tx in enumerate(block.transactions):
        spent, invocation = [], 0
        if n == 0:
            inp = tx.inputs[0]
            if inp.prev_txid != block_id(parent.chain_id, header) or inp.prev_index != height:
                raise ValueError('coinbase parent/height')
            coinbase_bytes = len(encode_transaction(tx, tx_profile))
            coinbase_outputs = sum(out.value for out in tx.outputs)
            coinbase_burn = sum(out.value for out in tx.outputs if out.flags & 2)
        else:
            record, invocation, spent = _complete_ordinary(tx, parent, staged,
                monetary_profile, height=height, mtp=mtp, maturity=coinbase_maturity,
                vm_profile=vm_profile, tx_profile=tx_profile, block_cap=block_cap)
            accounted.append(record)
        charges = authenticated_transaction_costs(tx, tx_profile, staged, height,
                                                  mtp, invocation, cost_profile)
        account_linear.append(charges.account_linear)
        enforce_linear.append(charges.enforce_linear)
        total_vm = uint(total_vm+invocation, U128, 'invocation cost')
        if total_vm > block_cap:
            raise ValueError('block invocation cost over cap')
        identity = identity_digests(tx, tx_profile, parent.chain_id)
        created = []
        for j, output in enumerate(tx.outputs):
            if output.flags & 2:
                continue
            coin = Coin(identity.txid, j, output.value, output.branches[0], height,
                        mtp, n == 0, output)
            if coin.key() in staged:
                raise ValueError('created outpoint already occupied')
            created.append(coin)
        for coin in spent:
            del staged[coin.key()]
            undo.steps.append(UndoStep(False, coin))
        for coin in created:
            staged[coin.key()] = coin
            undo.steps.append(UndoStep(True, coin))
    frames = sum(block.frame_prefix_bytes)
    envelope = authenticated_envelope_cost(frames, len(block.transactions), cost_profile)
    transition = advance(monetary_profile, monetary, work=child_work,
        transactions=tuple(accounted), coinbase_native_outputs=coinbase_outputs,
        coinbase_native_burn=coinbase_burn, coinbase_bytes=coinbase_bytes,
        tx_frame_prefix_bytes=frames,
        account_block_cost=block_cost(envelope, tuple(account_linear), monetary_profile),
        enforce_block_cost=block_cost(envelope, tuple(enforce_linear), monetary_profile))
    root = utxo_root(staged)
    state = state_root(parent.chain_id, height, root, transition.state)
    validate_child_header(header_profile, header, history, block.header,
        expected_tx_root=block.header.tx_root, expected_state_root=state,
        expected_size=len(wire))
    coins.clear()
    coins.update(staged)
    return Connected(root, state, transition.state.to_bytes(), transition, undo, total_vm)
