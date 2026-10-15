"""Complete P04 framing. Structural decoding is separate from state acceptance."""
from dataclasses import dataclass
from .encoding import Reader, encode_compact_size
from .block_seal import Header, HEADER_SIZE, parse_header, serialize_header
from .signing import Transaction, TxProfile, decode_transaction, encode_transaction, identity_digests
from .block import transaction_root

@dataclass(frozen=True)
class FramedBlock:
    header: Header
    transactions: tuple[Transaction, ...]
    frame_prefix_bytes: tuple[int, ...]
    wire_bytes: int


def complete_transaction_root(txs, profile, chain_id):
    if not txs or len(txs) > 0xffffffff:
        raise ValueError("missing coinbase or count")
    ids, pairs = set(), []
    for i, tx in enumerate(txs):
        if any(inp.flags == 2 for inp in tx.inputs) != (i == 0):
            raise ValueError("first-and-only coinbase")
        d = identity_digests(tx, profile, chain_id)
        if d.txid in ids:
            raise ValueError("duplicate transaction id")
        ids.add(d.txid)
        pairs.append((d.txhash, d.txid))
    return transaction_root(tuple(pairs))


def decode_block_wire(wire: bytes, profile: TxProfile, chain_id: bytes) -> FramedBlock:
    reader = Reader(wire)
    header = parse_header(reader.take(HEADER_SIZE))
    if header.size != len(wire):
        raise ValueError("block size")
    count = reader.integer(4)
    if count == 0 or count > reader.remaining // 17:
        raise ValueError("block transaction count")
    txs, prefixes = [], []
    for _ in range(count):
        start = reader.offset
        length = reader.compact_size(max_value=reader.remaining)
        prefixes.append(reader.offset - start)
        if length < 16:
            raise ValueError("transaction frame")
        txs.append(decode_transaction(reader.take(length), profile))
    reader.finish()
    if complete_transaction_root(txs, profile, chain_id) != header.tx_root:
        raise ValueError("block transaction root")
    return FramedBlock(header, tuple(txs), tuple(prefixes), len(wire))


def encode_block_wire(header: Header, txs, profile: TxProfile) -> bytes:
    if len(txs) > 0xffffffff:
        raise ValueError("block transaction count")
    wire = serialize_header(header) + len(txs).to_bytes(4, 'little')
    for tx in txs:
        raw = encode_transaction(tx, profile)
        wire += encode_compact_size(len(raw)) + raw
    if header.size != len(wire):
        raise ValueError("block size")
    return wire
