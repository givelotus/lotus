"""Lotus V2 sighash preimages.

Field order and domain strings follow native PrepareSigningContext and
SigningMessage. This is a reference connector, not lotusd ConnectTip.
"""

from __future__ import annotations

from dataclasses import dataclass

import blake3

from .encoding import (
    DecodeError, Output, Profile, Reader, decode_output, encode_bytes,
    encode_compact_size, encode_output,
)

_OUTPUT_PROFILE = Profile(16, 16, 812, 8192)


class SigningError(ValueError):
    """The transaction cannot produce the native sighash preimage."""


@dataclass(frozen=True)
class TxProfile:
    max_inputs: int
    max_outputs: int
    max_mints: int
    max_script_bytes: int
    max_arguments: int
    max_argument_bytes: int
    max_branch_proof_depth: int


@dataclass(frozen=True)
class Witness:
    script: bytes
    siblings: tuple[bytes, ...] = ()
    arguments: tuple[bytes, ...] = ()


@dataclass(frozen=True)
class Input:
    prev_txid: bytes
    prev_index: int
    sequence: int
    flags: int
    path_index: int = 0
    witnesses: tuple[Witness, ...] = ()


@dataclass(frozen=True)
class Transaction:
    lock: int
    inputs: tuple[Input, ...]
    outputs: tuple[Output, ...]


@dataclass(frozen=True)
class IdentityDigests:
    txid: bytes
    txhash: bytes
    inputs_root: bytes
    full_inputs_root: bytes
    outputs_root: bytes
    output_leaves: tuple[bytes, ...]


def _tagged(tag: str, payload: bytes) -> bytes:
    hasher = blake3.blake3()
    hasher.update(tag.encode("ascii"))
    hasher.update(b"\x00")
    hasher.update(payload)
    return hasher.digest()


def _valid_profile(profile: TxProfile) -> None:
    if (not isinstance(profile, TxProfile) or profile.max_inputs == 0
            or profile.max_inputs > 65535 or profile.max_outputs > 65535
            or profile.max_mints > profile.max_inputs or profile.max_arguments > 65535
            or profile.max_argument_bytes > 8192 or profile.max_branch_proof_depth > 64):
        raise SigningError("profile")


def _u32(value: int, label: str) -> bytes:
    if type(value) is not int or not 0 <= value <= 0xFFFFFFFF:
        raise SigningError(label)
    return value.to_bytes(4, "little")


def _output_bytes(output: Output) -> bytes:
    try:
        return encode_output(output, _OUTPUT_PROFILE)
    except ValueError as exc:
        raise SigningError(str(exc)) from exc


def _witness_wire(witness: Witness, profile: TxProfile, core: bool) -> bytes:
    if (len(witness.script) > profile.max_script_bytes
            or len(witness.siblings) > profile.max_branch_proof_depth
            or len(witness.arguments) > profile.max_arguments):
        raise SigningError("witness cap")
    if any(not isinstance(sibling, bytes) or len(sibling) != 32 for sibling in witness.siblings):
        raise SigningError("siblings")
    encoded = encode_bytes(witness.script, max_length=profile.max_script_bytes)
    encoded += encode_compact_size(len(witness.siblings)) + b"".join(witness.siblings)
    if core:
        return encoded
    encoded += encode_compact_size(len(witness.arguments))
    for argument in witness.arguments:
        if not isinstance(argument, bytes) or len(argument) > profile.max_argument_bytes:
            raise SigningError("argument cap")
        encoded += encode_bytes(argument, max_length=profile.max_argument_bytes)
    return encoded


def _input_wire(inp: Input, profile: TxProfile, core: bool) -> bytes:
    if inp.flags not in (1, 3):
        raise SigningError("unsupported input kind for signing")
    if not isinstance(inp.prev_txid, bytes) or len(inp.prev_txid) != 32:
        raise SigningError("prev txid")
    encoded = inp.prev_txid + _u32(inp.prev_index, "prev index")
    encoded += _u32(inp.sequence, "sequence") + bytes([inp.flags])
    if inp.flags == 1:
        if (type(inp.path_index) is not int or inp.path_index >= 16 or not inp.witnesses
                or len(inp.witnesses) > 16
                or (inp.sequence != 0xFFFFFFFF and (inp.sequence & ~0x40FFFF))):
            raise SigningError("spend authorization")
        encoded += encode_compact_size(inp.path_index) + encode_compact_size(len(inp.witnesses))
        for witness in inp.witnesses:
            encoded += _witness_wire(witness, profile, core)
        return encoded
    if (inp.prev_txid == bytes(32) or inp.prev_index != 0 or inp.sequence != 0xFFFFFFFF
            or inp.path_index != 0 or len(inp.witnesses) != 1):
        raise SigningError("mint pseudo-outpoint")
    return encoded + _witness_wire(inp.witnesses[0], profile, core)


def _require_transaction(tx: Transaction, profile: TxProfile) -> None:
    _valid_profile(profile)
    if (not isinstance(tx, Transaction) or not tx.inputs or len(tx.inputs) > profile.max_inputs
            or len(tx.outputs) > profile.max_outputs or type(tx.lock) is not int
            or not 0 <= tx.lock <= 2**64 - 1 or (tx.lock & 255) > 2
            or ((tx.lock & 255) == 0 and tx.lock != 0)):
        raise SigningError("transaction header")
    seen: set[tuple[bytes, int]] = set()
    spends = 0
    mints = 0
    for inp in tx.inputs:
        spends += inp.flags == 1
        mints += inp.flags == 3
        key = (inp.prev_txid, inp.prev_index)
        if key in seen:
            raise SigningError("repeated outpoint")
        seen.add(key)
        _input_wire(inp, profile, False)
    if spends == 0 or mints > profile.max_mints:
        raise SigningError("ordinary input mix")
    for output in tx.outputs:
        _output_bytes(output)


def _header(tx: Transaction) -> bytes:
    return ((7).to_bytes(4, "little") + tx.lock.to_bytes(8, "little")
            + len(tx.inputs).to_bytes(2, "little") + len(tx.outputs).to_bytes(2, "little"))


def _indexed_root(leaves: tuple[bytes, ...] | list[bytes]) -> bytes:
    if not leaves:
        return _tagged("Lotus/v2/merkleidx", b"\x02")
    if len(leaves) == 1:
        return leaves[0]
    current = list(leaves)
    layer = 0
    while len(current) > 1:
        if len(current) % 2:
            current.append(bytes(32))
        nxt: list[bytes] = []
        for index in range(0, len(current), 2):
            payload = bytes([1]) + layer.to_bytes(2, "little") + current[index] + current[index + 1]
            nxt.append(_tagged("Lotus/v2/merkleidx", payload))
        current = nxt
        layer += 1
    return current[0]


def _leaf_bytes(domain: str, body: bytes) -> bytes:
    return _tagged(domain, encode_compact_size(len(body)) + body)


def _less_little_endian(left: bytes, right: bytes) -> bool:
    for index in range(31, -1, -1):
        if left[index] != right[index]:
            return left[index] < right[index]
    return False


def _branch_leaf(script: bytes) -> bytes:
    return _tagged("Lotus/v2/branch", bytes([0]) + encode_compact_size(len(script)) + script)


def _branch_node(left: bytes, right: bytes) -> bytes:
    low, high = (left, right) if _less_little_endian(left, right) else (right, left)
    return _tagged("Lotus/v2/branch", bytes([1]) + low + high)


def _branch_root(leaf: bytes, siblings: tuple[bytes, ...]) -> bytes:
    root = leaf
    for sibling in siblings:
        root = _branch_node(root, sibling)
    return root


def identity_digests(tx: Transaction, profile: TxProfile, chain_id: bytes) -> IdentityDigests:
    """Txid and txhash for one already framed transaction. Witness bytes stay in txhash only."""
    if not isinstance(chain_id, bytes) or len(chain_id) != 32:
        raise SigningError("chain id")
    _require_transaction(tx, profile)
    cores = tuple(_input_wire(inp, profile, True) for inp in tx.inputs)
    fulls = tuple(_input_wire(inp, profile, False) for inp in tx.inputs)
    output_wires = tuple(_output_bytes(output) for output in tx.outputs)
    output_leaves = tuple(_leaf_bytes("Lotus/v2/output", wire) for wire in output_wires)
    inputs_root = _indexed_root(tuple(_tagged("Lotus/v2/inputcore", core) for core in cores))
    full_root = _indexed_root(tuple(_tagged("Lotus/v2/inputfull", full) for full in fulls))
    outputs_root = _indexed_root(output_leaves)
    header = _header(tx)
    return IdentityDigests(
        _tagged("Lotus/v2/txid", chain_id + header + inputs_root + outputs_root),
        _tagged("Lotus/v2/txhash", chain_id + header + full_root + outputs_root),
        inputs_root, full_root, outputs_root, output_leaves,
    )


def coins_root(tx: Transaction, resolved: tuple[Output | None, ...]) -> bytes:
    _resolved_ok(tx, resolved)
    leaves = []
    for inp, coin in zip(tx.inputs, resolved):
        if inp.flags == 3:
            leaves.append(_leaf_bytes("Lotus/v2/coinentry", b""))
        else:
            if not isinstance(coin, Output):
                raise SigningError("spend resolved coin")
            leaves.append(_leaf_bytes("Lotus/v2/coinentry", _output_bytes(coin)))
    return _indexed_root(leaves)


def own_input_hash(tx: Transaction, profile: TxProfile, resolved: tuple[Output | None, ...],
                   input_index: int) -> bytes:
    _require_transaction(tx, profile)
    _resolved_ok(tx, resolved)
    if type(input_index) is not int or not 0 <= input_index < len(tx.inputs) or tx.inputs[input_index].flags != 1:
        raise SigningError("own input spend")
    coin = resolved[input_index]
    if not isinstance(coin, Output):
        raise SigningError("own input spend")
    core = _input_wire(tx.inputs[input_index], profile, True)
    wire = _output_bytes(coin)
    return _tagged("Lotus/v2/owninput", core + encode_compact_size(len(wire)) + wire)


def _resolved_ok(tx: Transaction, resolved: tuple[Output | None, ...]) -> None:
    if not isinstance(resolved, tuple) or len(resolved) != len(tx.inputs):
        raise SigningError("resolved count")
    for inp, coin in zip(tx.inputs, resolved):
        if inp.flags == 1 and (not isinstance(coin, Output) or coin.flags & 2):
            raise SigningError("spend resolved coin")
        if inp.flags == 3 and coin is not None:
            raise SigningError("mint resolved coin")


@dataclass(frozen=True)
class _Invocation:
    kind: int
    selector: bytes


@dataclass(frozen=True)
class _Prepared:
    chain_id: bytes
    lock: int
    txid: bytes
    coins_root: bytes
    outputs_root: bytes
    output_leaves: tuple[bytes, ...]
    own_input_hashes: tuple[bytes | None, ...]
    invocations: tuple[tuple[_Invocation, ...], ...]


def _prepare(tx: Transaction, profile: TxProfile, chain_id: bytes,
             resolved: tuple[Output | None, ...]) -> _Prepared:
    identities = identity_digests(tx, profile, chain_id)
    _resolved_ok(tx, resolved)
    own: list[bytes | None] = [None] * len(tx.inputs)
    invocations: list[tuple[_Invocation, ...]] = []
    for index, inp in enumerate(tx.inputs):
        if inp.flags == 1:
            coin = resolved[index]
            if not isinstance(coin, Output):
                raise SigningError("spend resolved coin")
            if inp.path_index >= len(coin.paths) or len(inp.witnesses) != len(coin.paths[inp.path_index]):
                raise SigningError("positional witness count/index")
            wire = _output_bytes(coin)
            core = _input_wire(inp, profile, True)
            own[index] = _tagged("Lotus/v2/owninput", core + encode_compact_size(len(wire)) + wire)
            built: list[_Invocation] = []
            for witness_index, branch_index in enumerate(coin.paths[inp.path_index]):
                witness = inp.witnesses[witness_index]
                leaf = _branch_leaf(witness.script)
                if (branch_index >= len(coin.branches)
                        or _branch_root(leaf, witness.siblings) != coin.branches[branch_index]):
                    raise SigningError("branch membership")
                selector = bytes([1]) + _u32(index, "input index") + _u32(branch_index, "branch index") + leaf
                built.append(_Invocation(1, selector))
            invocations.append(tuple(built))
        else:
            witness = inp.witnesses[0]
            leaf = _branch_leaf(witness.script)
            if _branch_root(leaf, witness.siblings) != inp.prev_txid:
                raise SigningError("mint root")
            selector = bytes([3]) + inp.prev_txid + bytes(16) + leaf
            invocations.append((_Invocation(3, selector),))
    return _Prepared(
        chain_id, tx.lock, identities.txid, coins_root(tx, resolved), identities.outputs_root,
        identities.output_leaves, tuple(own), tuple(invocations),
    )


def _nonzero(delta: bytes) -> bool:
    return any(delta)


def signing_message(tx: Transaction, profile: TxProfile, chain_id: bytes,
                    resolved: tuple[Output | None, ...], input_index: int, witness_index: int,
                    mode: int, positive_delta: bytes | None = None) -> bytes:
    """Hash one fixed-width sighash preimage. Widths are 138, 150, and 178."""
    prepared = _prepare(tx, profile, chain_id, resolved)
    if (type(mode) is not int or mode > 2 or type(input_index) is not int
            or type(witness_index) is not int or input_index < 0 or witness_index < 0
            or input_index >= len(prepared.invocations)
            or witness_index >= len(prepared.invocations[input_index])):
        raise SigningError("signing mode or invocation index")
    invocation = prepared.invocations[input_index][witness_index]
    if invocation.kind == 1 and positive_delta is not None:
        raise SigningError("spend delta")
    if invocation.kind == 3 and (
            mode != 0 or not isinstance(positive_delta, bytes) or len(positive_delta) != 16
            or not _nonzero(positive_delta)):
        raise SigningError("mint selector delta/mode")
    if positive_delta is not None and (not isinstance(positive_delta, bytes) or len(positive_delta) != 16):
        raise SigningError("mint selector delta/mode")
    if mode == 2 and input_index >= len(prepared.output_leaves):
        raise SigningError("partial mode unavailable")
    preimage = bytearray(prepared.chain_id)
    preimage.append(mode)
    if mode == 0:
        preimage += prepared.txid + prepared.coins_root
    else:
        own = prepared.own_input_hashes[input_index]
        if own is None:
            raise SigningError("partial mode unavailable")
        preimage += (7).to_bytes(4, "little") + prepared.lock.to_bytes(8, "little") + own
        commitment = prepared.outputs_root if mode == 1 else prepared.output_leaves[input_index]
        preimage += commitment
    if invocation.kind == 3:
        if not isinstance(positive_delta, bytes):
            raise SigningError("mint selector delta/mode")
        preimage += invocation.selector[:33] + positive_delta + invocation.selector[49:]
    else:
        preimage += invocation.selector
    expected = 178 if invocation.kind == 3 else (138 if mode == 0 else 150)
    if len(preimage) != expected:
        raise SigningError("sighash preimage width")
    return _tagged("Lotus/v2/sighash", bytes(preimage))


def _read_witness(reader: Reader, profile: TxProfile) -> Witness:
    script = reader.bytes_field(max_length=profile.max_script_bytes)
    count = reader.compact_size(max_value=profile.max_branch_proof_depth)
    if count > reader.remaining // 32:
        raise DecodeError("sibling count")
    siblings = tuple(reader.take(32) for _ in range(count))
    count = reader.compact_size(max_value=profile.max_arguments)
    if count > reader.remaining:
        raise DecodeError("argument count")
    arguments = tuple(
        reader.bytes_field(max_length=profile.max_argument_bytes) for _ in range(count))
    return Witness(script, siblings, arguments)


def _read_output(reader: Reader) -> Output:
    start = reader.offset
    flags = reader.integer(1)
    if flags > 3:
        raise DecodeError("output prefix")
    reader.take(8 + (32 if flags & 1 else 0))
    branches = reader.compact_size(max_value=16)
    if branches > reader.remaining // 32:
        raise DecodeError("output branches")
    reader.take(branches * 32)
    paths = reader.compact_size(max_value=16)
    if paths > reader.remaining:
        raise DecodeError("output paths")
    for _ in range(paths):
        length = reader.compact_size(max_value=16)
        if length > reader.remaining:
            raise DecodeError("output path length")
        for _ in range(length):
            reader.compact_size(max_value=15)
    if reader.offset - start > 812:
        raise DecodeError("output bytes")
    return decode_output(reader.frame[start:reader.offset], _OUTPUT_PROFILE)


def _read_input(reader: Reader, profile: TxProfile) -> Input:
    prev_txid = reader.take(32)
    prev_index = reader.integer(4)
    sequence = reader.integer(4)
    flags = reader.integer(1)
    if flags == 1:
        path_index = reader.compact_size(max_value=15)
        count = reader.compact_size(max_value=16)
        if count > reader.remaining // 3:
            raise DecodeError("witness count")
        witnesses = tuple(_read_witness(reader, profile) for _ in range(count))
        return Input(prev_txid, prev_index, sequence, flags, path_index, witnesses)
    if flags == 3:
        return Input(prev_txid, prev_index, sequence, flags, 0, (_read_witness(reader, profile),))
    raise DecodeError("input flags")


def decode_transaction(frame: bytes, profile: TxProfile) -> Transaction:
    """Decode one full transaction frame. Failure leaves no partial result."""
    _valid_profile(profile)
    if not isinstance(frame, bytes):
        raise SigningError("frame")
    reader = Reader(frame)
    try:
        if reader.integer(4) != 7:
            raise DecodeError("version/lock")
        lock = reader.integer(8)
        input_count = reader.integer(2)
        output_count = reader.integer(2)
        if input_count == 0 or input_count > profile.max_inputs or output_count > profile.max_outputs:
            raise DecodeError("transaction count")
        inputs = tuple(_read_input(reader, profile) for _ in range(input_count))
        outputs = tuple(_read_output(reader) for _ in range(output_count))
        reader.finish()
    except DecodeError as exc:
        raise SigningError(str(exc)) from exc
    transaction = Transaction(lock, inputs, outputs)
    _require_transaction(transaction, profile)
    return transaction
