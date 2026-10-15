"""Ordinary-block connect and disconnect for the Python reference.

This mirrors the standalone C++ model: ordered ordinary transactions, one
invocation-cost sum, rollback when that sum exceeds the block cap, and an undo
object that restores the UTXO root and 56-byte monetary record. It does not
parse a block wire, mine, run ASERT, construct a coinbase, or claim that
lotusd accepted a block.

The monetary delta is ``advance`` with a zero coinbase payout and the parent
work integer. Those arguments let the existing arithmetic return its delta;
they are not a coinbase or work rule implemented here.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import blake3

from .encoding import Output, Profile, decode_output, encode_compact_size, encode_output
from .monetary import MonetaryState, OrdinaryTx, Profile as MonetaryProfile, advance
from .vm import ASSIGNED, VMError, VMProfile, evaluate

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


def full_payment_bytes(core: bytes, output: bytes) -> bytes:
    # Core omits the argument vector. This witness has an empty one.
    header = (7).to_bytes(4, "little") + (0).to_bytes(8, "little")
    header += (1).to_bytes(2, "little") + (1).to_bytes(2, "little")
    return header + core + b"\x00" + output


@dataclass(frozen=True)
class Coin:
    tx_id: bytes
    index: int
    value: int
    branch: bytes
    creation_height: int
    creation_parent_mtp: int
    coinbase: bool = False

    def key(self) -> tuple[bytes, int]:
        return (self.tx_id, self.index)

    def encode(self) -> bytes:
        output = encode_native_output(self.value, self.branch)
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


@dataclass(frozen=True)
class Payment:
    spent_tx: bytes
    spent_index: int
    value: int
    kind: str = "spend"  # spend, coinbase, or mint
    script: bytes = OP_TRUE


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


def _witness_charge(script: bytes) -> int:
    # One spend input and one output, matching this payment model.
    try:
        result = evaluate(script, (), PAYMENT_VM, input_count=1, output_count=1)
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
    witness_cost = _witness_charge(tx.script)
    output = encode_native_output(tx.value, spent.branch)
    core = encode_spend_core(tx.spent_tx, tx.spent_index, tx.script)
    wire = full_payment_bytes(core, output)
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
    try:
        for tx in transactions:
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
            transactions=tuple(accounted), coinbase_native_outputs=0,
            coinbase_native_burn=0, coinbase_bytes=0, tx_frame_prefix_bytes=0,
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
