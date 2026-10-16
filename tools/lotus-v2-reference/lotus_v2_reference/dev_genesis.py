"""Development-chain regtest genesis fixture. Not mainnet and not frozen consensus.

Height 0 and a zero previous id only. A nonzero previous id or height is
rejected and leaves the output unchanged. This records the existing monetary
test state with no issuance. It does not connect a block, and lotusd did not
accept one.
"""

from __future__ import annotations

from dataclasses import dataclass

from .block import empty_utxo_root, state_root, tagged
from .monetary import MonetaryState, Profile, initialize_genesis

HEADER_SIZE = 134
MAX_TIME = (1 << 48) - 1
# Version, compact target, and timestamp already accepted by the header tests.
HEADER_VERSION = 2
HEADER_BITS = 0x1D00FFFF
HEADER_TIME = 0x010203040506
if HEADER_TIME > MAX_TIME:
    raise ValueError("development header time exceeds MAX_TIME")

# Existing monetary test profile. Not a mainnet genesis.
DEVELOPMENT_GENESIS = Profile(2, 3, 2, 4, 3, 5, 2, 2000, 3, 1000, 200, 9)
# All-zero id for this development candidate. Not a mainnet chain id.
DEVELOPMENT_CHAIN_ID = bytes(32)


def empty_transaction_root() -> bytes:
    """TransactionRoot of no transactions (EmptyTxRoot = H_txroot(0x02))."""
    return tagged("Lotus/v2/txroot", bytes([2]))


def initial_test_state() -> MonetaryState:
    """Monetary test state: reserve 9, tail 200, work 9, EMA 4. No issuance."""
    return initialize_genesis(
        DEVELOPMENT_GENESIS,
        bootstrap_reserve=9,
        tail_subsidy=200,
        genesis_work=9,
        ema_block_cost=4,
        coinbase_native_value=0,
    )


@dataclass(frozen=True)
class Header:
    prev_id: bytes = b""
    bits: int = 0
    time: int = 0
    nonce: int = 0
    version: int = 0
    size: int = 0
    height: int = 0
    tx_root: bytes = b""
    state_root: bytes = b""


@dataclass
class DevelopmentGenesisFixture:
    chain_id: bytes = b""
    state: MonetaryState | None = None
    header: Header | None = None


def _le(value: int, width: int) -> bytes | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    if value < 0 or value >= 1 << (8 * width):
        return None
    return value.to_bytes(width, "little")


def _hash32(value: bytes) -> bytes | None:
    if not isinstance(value, (bytes, bytearray)) or len(value) != 32:
        return None
    return bytes(value)


def serialize_header(header: Header) -> bytes | None:
    """134-byte header. Failure returns None and writes nothing."""
    if not isinstance(header, Header) or header.time > MAX_TIME:
        return None
    prev_id = _hash32(header.prev_id)
    tx_root = _hash32(header.tx_root)
    state = _hash32(header.state_root)
    bits = _le(header.bits, 4)
    time = _le(header.time, 6)
    nonce = _le(header.nonce, 8)
    version = _le(header.version, 4)
    size = _le(header.size, 8)
    height = _le(header.height, 8)
    if (prev_id is None or bits is None or time is None or nonce is None
            or version is None or size is None or height is None
            or tx_root is None or state is None):
        return None
    encoded = prev_id + bits + time + nonce + version + size + height + tx_root + state
    if len(encoded) != HEADER_SIZE:
        return None
    return encoded


def parse_header(data: bytes) -> Header | None:
    """Structural parse. A wrong length returns None."""
    if not isinstance(data, (bytes, bytearray)) or len(data) != HEADER_SIZE:
        return None
    raw = bytes(data)
    return Header(
        prev_id=raw[:32],
        bits=int.from_bytes(raw[32:36], "little"),
        time=int.from_bytes(raw[36:42], "little"),
        nonce=int.from_bytes(raw[42:50], "little"),
        version=int.from_bytes(raw[50:54], "little"),
        size=int.from_bytes(raw[54:62], "little"),
        height=int.from_bytes(raw[62:70], "little"),
        tx_root=raw[70:102],
        state_root=raw[102:],
    )


def _rejected(prev_id: bytes, height: int) -> bool:
    if not isinstance(prev_id, (bytes, bytearray)):
        return True
    if len(prev_id) != 32 or any(prev_id):
        return True
    if isinstance(height, bool) or not isinstance(height, int) or height != 0:
        return True
    return False


def make_development_genesis(prev_id: bytes, height: int,
                             out: DevelopmentGenesisFixture) -> bool:
    """Fill ``out`` only for a zero previous id at height 0."""
    if not isinstance(out, DevelopmentGenesisFixture) or _rejected(prev_id, height):
        return False
    state = initial_test_state()
    tx_root = empty_transaction_root()
    utxo = empty_utxo_root()
    root = state_root(DEVELOPMENT_CHAIN_ID, 0, utxo, state)
    header = Header(
        prev_id=bytes(32),
        bits=HEADER_BITS,
        time=HEADER_TIME,
        nonce=0,
        version=HEADER_VERSION,
        size=HEADER_SIZE,  # Header encoding length, not a block-size rule.
        height=0,
        tx_root=tx_root,
        state_root=root,
    )
    out.chain_id = DEVELOPMENT_CHAIN_ID
    out.state = state
    out.header = header
    return True
