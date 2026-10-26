"""Deterministic header candidate; future clock eligibility is deliberately separate."""
from dataclasses import dataclass
from .asert import Parent, compact_decode, required_bits
from .block_seal import Header, MAX_TIME, serialize_header, block_id

@dataclass(frozen=True)
class HeaderChainProfile:
    chain_id: bytes
    version: int
    genesis_time: int
    genesis_bits: int
    pow_limit: int
    half_life_seconds: int
    spacing_seconds: int

    def __post_init__(self):
        if not isinstance(self.chain_id, bytes) or len(self.chain_id) != 32:
            raise ValueError("chain ID")
        for name in ("version", "genesis_time", "genesis_bits", "pow_limit", "half_life_seconds", "spacing_seconds"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError(f"{name} must be an integer")
        if not 0 <= self.version <= 0xffffffff or not 0 <= self.genesis_time <= MAX_TIME:
            raise ValueError("chain profile width")
        if self.half_life_seconds <= 0 or self.spacing_seconds <= 0:
            raise ValueError("positive schedule parameters required")
        compact_decode(self.genesis_bits, self.pow_limit)


def parent_median_time(profile: HeaderChainProfile, parent: Header, history: list[Header]) -> int:
    """Newest first, authenticated oldest entry; verify links in the window."""
    serialize_header(parent)
    if len(history) != min(parent.height + 1, 11) or history[0] != parent:
        raise ValueError("authenticated parent history")
    for i, header in enumerate(history):
        serialize_header(header)
        if header.height != parent.height-i or header.version != profile.version:
            raise ValueError("history height/version")
        if i+1 < len(history) and header.prev_id != block_id(profile.chain_id, history[i+1]):
            raise ValueError("history link")
        if header.height == 0 and (header.time != profile.genesis_time or header.bits != profile.genesis_bits or header.prev_id != bytes(32)):
            raise ValueError("history genesis")
    return sorted(h.time for h in history)[len(history)//2]


def validate_child_header(profile: HeaderChainProfile, parent: Header,
                          history: list[Header], child: Header, *,
                          expected_tx_root: bytes, expected_state_root: bytes,
                          expected_size: int) -> None:
    """Caller derives roots/size from full accepted body, authenticates history."""
    mtp = parent_median_time(profile, parent, history)
    serialize_header(child)
    if len(profile.chain_id) != 32 or not 0 <= profile.genesis_time <= MAX_TIME:
        raise ValueError("chain profile")
    genesis = compact_decode(profile.genesis_bits, profile.pow_limit)
    bits = required_bits(Parent(parent.time, parent.height), t0=profile.genesis_time,
                         genesis_target=genesis, spacing=profile.spacing_seconds,
                         half_life=profile.half_life_seconds, pow_limit=profile.pow_limit)
    if child.height != parent.height+1 or child.prev_id != block_id(profile.chain_id, parent):
        raise ValueError("child parent/height")
    if child.version != profile.version or child.time <= mtp:
        raise ValueError("child version/median time")
    if (child.tx_root, child.state_root, child.size) != (expected_tx_root, expected_state_root, expected_size):
        raise ValueError("child commitments")
    target = compact_decode(child.bits, profile.pow_limit)
    if child.bits != bits:
        raise ValueError("required target")
    if int.from_bytes(block_id(profile.chain_id, child), 'little') > target:
        raise ValueError("proof of work")
