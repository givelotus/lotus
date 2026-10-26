"""P01/C04 output wire grammar. No transaction or contextual validity claims."""

from dataclasses import dataclass
from typing import Callable, Sequence, TypeVar


class DecodeError(ValueError):
    """Malformed or profile-disallowed canonical wire value."""


@dataclass(frozen=True)
class Profile:
    """Explicit caller-selected bounds; no implied production parameter profile."""

    max_output_branches: int
    max_output_paths: int
    max_output_bytes: int
    max_bytes_field: int

    def __post_init__(self) -> None:
        if not 1 <= self.max_output_branches <= 16:
            raise ValueError("max_output_branches must be 1..16")
        if not 1 <= self.max_output_paths <= 16:
            raise ValueError("max_output_paths must be 1..16")
        if not 1 <= self.max_output_bytes <= 812:
            raise ValueError("max_output_bytes must be 1..812")
        if not 0 <= self.max_bytes_field <= 2**64 - 1:
            raise ValueError("max_bytes_field must fit u64")


@dataclass(frozen=True)
class Output:
    flags: int
    value: int
    token_id: bytes | None
    branches: tuple[bytes, ...]
    paths: tuple[tuple[int, ...], ...]


def encode_int(value: int, width: int, *, signed: bool = False) -> bytes:
    if width not in (1, 2, 4, 8, 16) or isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("invalid integer or width")
    low = -(1 << (width * 8 - 1)) if signed else 0
    high = (1 << (width * 8 - (1 if signed else 0))) - 1
    if not low <= value <= high:
        raise ValueError("integer out of range")
    return value.to_bytes(width, "little", signed=signed)


def encode_compact_size(value: int) -> bytes:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 2**64 - 1:
        raise ValueError("CompactSize out of range")
    if value < 253:
        return bytes([value])
    if value <= 0xffff:
        return b"\xfd" + encode_int(value, 2)
    if value <= 0xffffffff:
        return b"\xfe" + encode_int(value, 4)
    return b"\xff" + encode_int(value, 8)


def encode_bytes(value: bytes, *, max_length: int) -> bytes:
    if not isinstance(value, bytes) or len(value) > max_length:
        raise ValueError("Bytes field exceeds its explicit bound")
    return encode_compact_size(len(value)) + value


T = TypeVar("T")


def encode_vec(values: Sequence[T], encode_item: Callable[[T], bytes], *, max_count: int) -> bytes:
    if len(values) > max_count:
        raise ValueError("Vec count exceeds its explicit bound")
    return encode_compact_size(len(values)) + b"".join(encode_item(v) for v in values)


class Reader:
    def __init__(self, frame: bytes):
        if not isinstance(frame, bytes):
            raise TypeError("frame must be bytes")
        self.frame = frame
        self.offset = 0

    @property
    def remaining(self) -> int:
        return len(self.frame) - self.offset

    def take(self, count: int) -> bytes:
        if count < 0 or count > self.remaining:
            raise DecodeError("truncated frame")
        result = self.frame[self.offset:self.offset + count]
        self.offset += count
        return result

    def integer(self, width: int, *, signed: bool = False) -> int:
        if width not in (1, 2, 4, 8, 16):
            raise ValueError("unsupported integer width")
        return int.from_bytes(self.take(width), "little", signed=signed)

    def compact_size(self, *, max_value: int) -> int:
        lead = self.integer(1)
        if lead < 253:
            value = lead
        else:
            width = {253: 2, 254: 4, 255: 8}[lead]
            value = self.integer(width)
            if value < {2: 253, 4: 65536, 8: 2**32}[width]:
                raise DecodeError("nonminimal CompactSize")
        if value > max_value:
            raise DecodeError("declared length exceeds cap")
        return value

    def bytes_field(self, *, max_length: int) -> bytes:
        count = self.compact_size(max_value=max_length)
        return self.take(count)

    def vec(self, read_item: Callable[[], T], *, max_count: int, min_item_bytes: int) -> tuple[T, ...]:
        count = self.compact_size(max_value=max_count)
        if min_item_bytes < 1 or count > self.remaining // min_item_bytes:
            raise DecodeError("declared count exceeds remaining frame")
        return tuple(read_item() for _ in range(count))

    def finish(self) -> None:
        if self.remaining:
            raise DecodeError("trailing bytes")


def _validate_output(output: Output, profile: Profile) -> None:
    if not isinstance(output, Output):
        raise ValueError("expected Output")
    if output.flags not in (0, 1, 2, 3):
        raise ValueError("unknown output flags")
    encode_int(output.value, 8)
    if output.flags & 1:
        if not isinstance(output.token_id, bytes) or len(output.token_id) != 32 or output.token_id == bytes(32):
            raise ValueError("token ID must be nonzero h32")
    elif output.token_id is not None:
        raise ValueError("native output has token ID")
    if not 1 <= len(output.branches) <= profile.max_output_branches:
        raise ValueError("branch count out of bounds")
    if any(not isinstance(b, bytes) or len(b) != 32 for b in output.branches):
        raise ValueError("branch root must be h32")
    if len(set(output.branches)) != len(output.branches):
        raise ValueError("repeated branch root")
    if output.flags & 2:
        if output.paths:
            raise ValueError("burn output must have zero paths")
    elif not 1 <= len(output.paths) <= profile.max_output_paths:
        raise ValueError("spendable path count out of bounds")
    previous: tuple[int, ...] | None = None
    for path in output.paths:
        if not 1 <= len(path) <= len(output.branches):
            raise ValueError("path length out of bounds")
        if any(isinstance(i, bool) or not isinstance(i, int) or i < 0 or i >= len(output.branches) for i in path):
            raise ValueError("branch index out of bounds")
        if any(a >= b for a, b in zip(path, path[1:])):
            raise ValueError("path indices must increase")
        if previous is not None and previous >= path:
            raise ValueError("paths must increase lexicographically")
        previous = path


def encode_output(output: Output, profile: Profile) -> bytes:
    _validate_output(output, profile)
    result = bytes([output.flags]) + encode_int(output.value, 8)
    if output.token_id is not None:
        result += output.token_id
    result += encode_vec(output.branches, lambda branch: branch, max_count=profile.max_output_branches)
    result += encode_vec(
        output.paths,
        lambda path: encode_vec(path, encode_compact_size, max_count=profile.max_output_branches),
        max_count=profile.max_output_paths,
    )
    if len(result) > profile.max_output_bytes:
        raise ValueError("serialized output exceeds profile bound")
    return result


def decode_output(frame: bytes, profile: Profile) -> Output:
    if len(frame) > profile.max_output_bytes:
        raise DecodeError("output frame exceeds profile bound")
    reader = Reader(frame)
    flags = reader.integer(1)
    if flags not in (0, 1, 2, 3):
        raise DecodeError("unknown output flags")
    value = reader.integer(8)
    token_id = reader.take(32) if flags & 1 else None
    branches = reader.vec(lambda: reader.take(32), max_count=profile.max_output_branches, min_item_bytes=32)
    paths = reader.vec(
        lambda: reader.vec(
            lambda: reader.compact_size(max_value=profile.max_output_branches - 1),
            max_count=profile.max_output_branches,
            min_item_bytes=1,
        ),
        max_count=profile.max_output_paths,
        min_item_bytes=1,
    )
    reader.finish()
    result = Output(flags, value, token_id, branches, paths)
    try:
        _validate_output(result, profile)
    except ValueError as exc:
        raise DecodeError(str(exc)) from exc
    return result
