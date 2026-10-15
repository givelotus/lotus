"""Seal one child header from an ordinary connect result.

This mirrors the native sealer. It does not search a nonce, call a miner, or
claim that lotusd accepted the header.

``header.state_root`` is the connect result's ``state_root``. That value is
``state_root()`` in ``block.py`` (the ``StateRoot`` commitment: chain id, child
height, UTXO root, and the 56-byte monetary record). The UTXO root is not the
header state commitment. The connect result has no transaction root; the caller
passes that commitment and it is copied unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass

from .block import state_root, tagged
from .monetary import MonetaryState

HEADER_SIZE = 134
MAX_TIME = (1 << 48) - 1
HEADER_BODY = "Lotus/v2/header/body"
HEADER_WORK = "Lotus/v2/header/work"
BLOCK_ID = "Lotus/v2/blockid"


@dataclass(frozen=True)
class Header:
    prev_id: bytes
    bits: int
    time: int
    nonce: int
    version: int
    size: int
    height: int
    tx_root: bytes
    state_root: bytes


def _u32(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 0xFFFFFFFF:
        raise ValueError(f"{name} out of range")
    return value


def _u64(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 0xFFFFFFFFFFFFFFFF:
        raise ValueError(f"{name} out of range")
    return value


def _hash(value: bytes, name: str) -> bytes:
    if not isinstance(value, bytes) or len(value) != 32:
        raise ValueError(f"{name} must be 32 bytes")
    return value


def serialize_header(header: Header) -> bytes:
    time = _u64(header.time, "time")
    if time > MAX_TIME:
        raise ValueError("timestamp above MAX_TIME")
    raw = bytearray()
    raw += _hash(header.prev_id, "prev_id")
    raw += _u32(header.bits, "bits").to_bytes(4, "little")
    raw += time.to_bytes(6, "little")
    raw += _u64(header.nonce, "nonce").to_bytes(8, "little")
    raw += _u32(header.version, "version").to_bytes(4, "little")
    raw += _u64(header.size, "size").to_bytes(8, "little")
    raw += _u64(header.height, "height").to_bytes(8, "little")
    raw += _hash(header.tx_root, "tx_root")
    raw += _hash(header.state_root, "state_root")
    if len(raw) != HEADER_SIZE:
        raise ValueError("header round trip")
    return bytes(raw)


def parse_header(data: bytes) -> Header:
    if not isinstance(data, bytes) or len(data) != HEADER_SIZE:
        raise ValueError("header round trip")
    return Header(
        data[0:32],
        int.from_bytes(data[32:36], "little"),
        int.from_bytes(data[36:42], "little"),
        int.from_bytes(data[42:50], "little"),
        int.from_bytes(data[50:54], "little"),
        int.from_bytes(data[54:62], "little"),
        int.from_bytes(data[62:70], "little"),
        data[70:102],
        data[102:134],
    )


def _body_hash(chain_id: bytes, header: Header) -> bytes:
    body = bytearray(chain_id)
    body += _u32(header.version, "version").to_bytes(4, "little")
    body += _u64(header.size, "size").to_bytes(8, "little")
    body += _u64(header.height, "height").to_bytes(8, "little")
    body += _hash(header.tx_root, "tx_root")
    body += _hash(header.state_root, "state_root")
    if len(body) != 116:
        raise ValueError("header body width")
    return tagged(HEADER_BODY, bytes(body))


def block_id(chain_id: bytes, header: Header) -> bytes:
    _hash(chain_id, "chain_id")
    if _u64(header.time, "time") > MAX_TIME:
        raise ValueError("parent block id")
    work = bytearray()
    work += _u32(header.bits, "bits").to_bytes(4, "little")
    work += header.time.to_bytes(6, "little")
    work += _u64(header.nonce, "nonce").to_bytes(8, "little")
    work += _body_hash(chain_id, header)
    if len(work) != 50:
        raise ValueError("header work width")
    digest = tagged(BLOCK_ID, _hash(header.prev_id, "prev_id") + tagged(HEADER_WORK, bytes(work)))
    return digest


def meets_target(block: bytes, target: bytes) -> bool:
    block = _hash(block, "block id")
    target = _hash(target, "target")
    for index in range(31, -1, -1):
        if block[index] < target[index]:
            return True
        if block[index] > target[index]:
            return False
    return True


def _encode_target(target: bytes) -> int:
    top = 31
    while top >= 0 and target[top] == 0:
        top -= 1
    if top < 0:
        return 0
    exponent = top + 1
    if exponent <= 3:
        mantissa = 0
        for index in range(top, -1, -1):
            mantissa = (mantissa << 8) | target[index]
        mantissa <<= 8 * (3 - exponent)
    else:
        mantissa = (target[top] << 16) | (target[top - 1] << 8) | target[top - 2]
    if mantissa & 0x00800000:
        mantissa >>= 8
        exponent += 1
    return (exponent << 24) | mantissa


def decode_target(bits: int, pow_limit: bytes) -> bytes | None:
    bits = _u32(bits, "bits")
    limit = _hash(pow_limit, "pow_limit")
    exponent = bits >> 24
    mantissa = bits & 0x007FFFFF
    if (bits & 0x00800000) or mantissa == 0:
        return None
    decoded = bytearray(32)
    for index in range(3):
        position = exponent - 3 + index
        byte = (mantissa >> (8 * index)) & 0xFF
        if position >= 32 and byte != 0:
            return None
        if 0 <= position < 32:
            decoded[position] = byte
    raw = bytes(decoded)
    if raw == bytes(32):
        return None
    if _encode_target(raw) != bits or not meets_target(raw, limit):
        return None
    return raw


def _monetary_state(connected) -> MonetaryState:
    monetary = connected.monetary.state if hasattr(connected, "monetary") else connected.transition.state
    if not isinstance(monetary, MonetaryState):
        raise ValueError("connect result monetary bytes")
    return monetary


def seal_child_header(parent, connected, tx_root: bytes, version: int, time: int,
                      size: int, bits: int, pow_limit: bytes) -> Header:
    """Return the child header. Raises ValueError and does not search a nonce."""
    version = _u32(version, "version")
    time = _u64(time, "time")
    size = _u64(size, "size")
    tx_root = _hash(tx_root, "tx_root")
    if time > MAX_TIME:
        raise ValueError("timestamp above MAX_TIME")
    if decode_target(bits, pow_limit) is None:
        raise ValueError("compact target rejected")
    header = parent.header
    if not isinstance(header, Header):
        raise ValueError("parent header")
    if header.height == 0xFFFFFFFFFFFFFFFF:
        raise ValueError("parent header height")
    try:
        parent_id = block_id(parent.chain_id, header)
    except ValueError as exc:
        raise ValueError("parent block id") from exc
    height = header.height + 1
    monetary = _monetary_state(connected)
    monetary_bytes = monetary.to_bytes()
    supplied = connected.monetary_bytes
    if not isinstance(supplied, bytes) or supplied != monetary_bytes:
        raise ValueError("connect result monetary bytes")
    committed = state_root(parent.chain_id, height, _hash(connected.utxo_root, "utxo_root"), monetary)
    if _hash(connected.state_root, "state_root") != committed:
        raise ValueError("connect result height")
    sealed = Header(
        parent_id, bits, time, 0, version, size, height, tx_root, committed,
    )
    raw = serialize_header(sealed)
    parsed = parse_header(raw)
    if parsed != sealed or serialize_header(parsed) != raw or len(raw) != HEADER_SIZE:
        raise ValueError("header round trip")
    return sealed
