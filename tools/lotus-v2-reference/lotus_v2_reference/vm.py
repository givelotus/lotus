"""Bounded P03 VM reference slice; assigned unsupported operations fail closed.

The opcode allocation is the SHA-256 fb790b230e76befc90a1f183ea727cb3232d1f03e9b5838b10d025d96b9832da
snapshot of docs/lotus-v2/tools/opcodes.json (2026-10-14). No production limits
or cost coefficients are selected here.
"""

import math
from dataclasses import dataclass
from hashlib import sha256, sha512
from types import MappingProxyType
from typing import Callable, Mapping

from .encoding import DecodeError, Reader, encode_compact_size, encode_output
from .vm_context import InvocationContext, requires_branch


class VMError(ValueError):
    """This invocation fails under the implemented P03 subset."""


class UnsupportedFeature(VMError):
    """An assigned opcode needs implementation; never interpret as success."""


INT_MIN = -(1 << 127)
INT_MAX = (1 << 127) - 1
U128_MAX = (1 << 128) - 1
ASSIGNED = frozenset().union(*(range(a, b + 1) for a, b in (
    (0x00, 0x5d), (0x60, 0x6b), (0x70, 0x81), (0x88, 0x94),
    (0x98, 0xb4), (0xb8, 0xc2), (0xc8, 0xdd), (0xe0, 0xea), (0xf0, 0xf4))))


@dataclass(frozen=True)
class VMProfile:
    max_script_bytes: int
    max_arguments: int
    max_element_bytes: int
    max_stack_items: int
    max_altstack_items: int
    max_vm_bytes: int
    max_ast_depth: int
    max_invocation_cost: int
    structural_byte_cost: int
    opcode_costs: Mapping[int, int | Callable[[tuple[int, ...], tuple[int, ...]], int]]

    def __post_init__(self) -> None:
        for name in ("max_script_bytes", "max_arguments", "max_element_bytes",
                     "max_stack_items", "max_altstack_items", "max_vm_bytes",
                     "max_ast_depth", "max_invocation_cost", "structural_byte_cost"):
            value = getattr(self, name)
            if type(value) is not int or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
        if self.max_invocation_cost > U128_MAX:
            raise ValueError("cost cap exceeds u128")
        if any(type(k) is not int or k not in ASSIGNED or not (
            (type(v) is int and v > 0) or callable(v))
               for k, v in self.opcode_costs.items()):
            raise ValueError("opcode costs must be positive integers or cost functions for assigned bytes")
        object.__setattr__(self, "opcode_costs", MappingProxyType(dict(self.opcode_costs)))


@dataclass(frozen=True)
class Instruction:
    opcode: int
    data: bytes | None = None


@dataclass(frozen=True)
class Conditional:
    opcode: int
    then_arm: tuple["Node", ...]
    else_arm: tuple["Node", ...]
    has_else: bool


@dataclass(frozen=True)
class Loop:
    opcode: int
    body: tuple["Node", ...]


Node = Instruction | Conditional | Loop


@dataclass(frozen=True)
class VMResult:
    success: bool
    automatic: bool
    charged_cost: int
    stack: tuple[bytes, ...] | None


def branch_leaf_hash(script: bytes) -> bytes:
    """P02 Leaf(script), for explicit invocation-selector cross-checks."""
    if not isinstance(script, bytes):
        raise TypeError("script must be bytes")
    try:
        from blake3 import blake3
    except ImportError as exc:
        raise UnsupportedFeature("blake3 dependency is required for branch leaves") from exc
    preimage = b"Lotus/v2/branch\x00\x00" + encode_compact_size(len(script)) + script
    return blake3(preimage).digest()


@dataclass(frozen=True)
class SigningContext:
    """Externally prepared P01 messages for one selected script invocation.

    A transaction validator must independently construct and authenticate
    these messages and the branch membership proof. This object only checks
    that the claimed selected leaf matches the script passed to the VM.
    """

    selected_leaf_hash: bytes
    messages: Mapping[int, bytes]
    invocation_kind: str
    input_index: int
    output_count: int

    def __post_init__(self) -> None:
        if not isinstance(self.selected_leaf_hash, bytes) or len(self.selected_leaf_hash) != 32:
            raise ValueError("selected leaf hash must be h32")
        if self.invocation_kind not in ("spend", "mint"):
            raise ValueError("invocation kind must be spend or mint")
        if type(self.input_index) is not int or not 0 <= self.input_index <= 65535:
            raise ValueError("input index out of range")
        if type(self.output_count) is not int or not 0 <= self.output_count <= 65535:
            raise ValueError("output count out of range")
        if any(type(mode) is not int or mode not in (0, 1, 2) or
               not isinstance(message, bytes) or len(message) != 32
               for mode, message in self.messages.items()):
            raise ValueError("messages must map defined modes to 32-byte digests")
        object.__setattr__(self, "messages", MappingProxyType(dict(self.messages)))


def _verify_checksig(signature: bytes, public_key: bytes,
                     context: SigningContext | None) -> bool:
    if len(signature) == 64:
        mode = 0
    elif len(signature) == 65 and signature[-1] in (1, 2):
        mode = signature[-1]
    else:
        raise VMError("invalid CHECKSIG signature length or mode encoding")
    if len(public_key) != 32:
        raise VMError("CHECKSIG key must be 32-byte x-only encoding")
    if context is None:
        raise UnsupportedFeature("CHECKSIG requires an authenticated signing context")
    if mode and context.invocation_kind != "spend":
        raise VMError("partial CHECKSIG mode is spend-only")
    if mode == 2 and context.input_index >= context.output_count:
        raise VMError("mode 02 has no paired output")
    try:
        message = context.messages[mode]
    except KeyError as exc:
        raise UnsupportedFeature(f"signing message for mode {mode:02x} is unavailable") from exc
    try:
        from coincurve import PublicKeyXOnly
    except ImportError as exc:
        raise UnsupportedFeature("coincurve 21 dependency is required for CHECKSIG") from exc
    try:
        key = PublicKeyXOnly(public_key)
    except ValueError as exc:
        raise VMError("malformed CHECKSIG x-only key") from exc
    try:
        return key.verify(signature[:64], message)
    except ValueError:
        # Once framing and key parsing have succeeded, BIP340 scalar/point
        # noncanonicality belongs to the false-signature result.
        return False


def number(value: int) -> bytes:
    if type(value) is not int or not INT_MIN <= value <= INT_MAX:
        raise VMError("int128 overflow")
    return value.to_bytes(16, "little", signed=True)


def _numeric(data: bytes) -> int:
    if len(data) != 16:
        raise VMError("numeric operand is not N")
    return int.from_bytes(data, "little", signed=True)


def _boolean(data: bytes) -> bool:
    value = _numeric(data)
    if value not in (0, 1):
        raise VMError("noncanonical Boolean")
    return bool(value)


_U128_MASK = (1 << 128) - 1


def _unsigned(data: bytes) -> int:
    if len(data) != 16:
        raise VMError("operand is not U")
    return int.from_bytes(data, "little", signed=False)


def _unsigned_bytes(value: int) -> bytes:
    if type(value) is not int or not 0 <= value <= _U128_MASK:
        raise VMError("unsigned width")
    return value.to_bytes(16, "little")


def _log2_q64(x: int) -> int:
    """P03 LOG2_Q64. Not a claim of exact real-logarithm rounding."""
    if x <= 0:
        raise VMError("LOG requires x>0")
    e = x.bit_length() - 1
    z = x << (127 - e)
    fraction = 0
    for _ in range(64):
        t = (z * z) >> 127
        bit = 1 if t >= (1 << 128) else 0
        z = (t >> 1) if bit else t
        fraction = (fraction << 1) | bit
    return (e << 64) | fraction


# CHECKDATASIG profiles. Algorithm 2 is the strict prime-subgroup Ed25519
# equation, not a library's default cofactored verifier.
_ED_P = 2**255 - 19
_ED_L = 2**252 + 27742317777372353535851937790883648493
_ED_D = (-121665 * pow(121666, -1, _ED_P)) % _ED_P
_ED_I = pow(2, (_ED_P - 1) // 4, _ED_P)


def _ed_sqrt_ratio(u: int, v: int) -> int | None:
    root = pow((u * pow(v, _ED_P - 2, _ED_P)) % _ED_P, (_ED_P + 3) // 8, _ED_P)
    squared = (v * root * root) % _ED_P
    if squared == u % _ED_P:
        return root
    if squared == (-u) % _ED_P:
        return (root * _ED_I) % _ED_P
    return None


def _ed_decode(encoded: bytes) -> tuple[int, int] | None:
    if len(encoded) != 32:
        return None
    raw = int.from_bytes(encoded, "little")
    sign = raw >> 255
    y = raw & ((1 << 255) - 1)
    if y >= _ED_P:
        return None
    x = _ed_sqrt_ratio((y * y - 1) % _ED_P, (_ED_D * y * y + 1) % _ED_P)
    if x is None or (x == 0 and sign == 1):
        return None
    if (x & 1) != sign:
        x = _ED_P - x
    return (x, y)


def _ed_add(p1: tuple[int, int], p2: tuple[int, int]) -> tuple[int, int]:
    x1, y1 = p1
    x2, y2 = p2
    product = (_ED_D * x1 * x2 * y1 * y2) % _ED_P
    return (
        ((x1 * y2 + y1 * x2) * pow(1 + product, -1, _ED_P)) % _ED_P,
        ((y1 * y2 + x1 * x2) * pow(1 - product, -1, _ED_P)) % _ED_P,
    )


def _ed_mul(scalar: int, point: tuple[int, int]) -> tuple[int, int]:
    result = (0, 1)
    acc = point
    while scalar:
        if scalar & 1:
            result = _ed_add(result, acc)
        acc = _ed_add(acc, acc)
        scalar >>= 1
    return result


_ED_B = _ed_decode(bytes.fromhex(
    "5866666666666666666666666666666666666666666666666666666666666666"))
assert _ED_B is not None


def _ed_prime_nonidentity(point: tuple[int, int]) -> bool:
    return point != (0, 1) and _ed_mul(_ED_L, point) == (0, 1)


def _verify_ed25519(signature: bytes, public_key: bytes, message: bytes) -> bool:
    if len(public_key) != 32:
        raise VMError("CHECKDATASIG Ed25519 key encoding")
    if len(signature) != 64:
        raise VMError("CHECKDATASIG signature width")
    decoded_key = _ed_decode(public_key)
    if decoded_key is None:
        raise VMError("CHECKDATASIG Ed25519 key encoding")
    commitment = _ed_decode(signature[:32])
    scalar = int.from_bytes(signature[32:], "little")
    if (commitment is None or scalar >= _ED_L or
            not _ed_prime_nonidentity(decoded_key) or
            not _ed_prime_nonidentity(commitment)):
        return False
    challenge = int.from_bytes(
        sha512(signature[:32] + public_key + message).digest(), "little") % _ED_L
    return _ed_mul(scalar, _ED_B) == _ed_add(
        commitment, _ed_mul(challenge, decoded_key))


class _Curve:
    def __init__(self, p: int, a: int, b: int, gx: int, gy: int, order: int):
        self.p, self.a, self.b, self.n = p, a, b, order
        self.g = (gx, gy)

    def _lift(self, x: int) -> int | None:
        rhs = (x * x * x + self.a * x + self.b) % self.p
        y = pow(rhs, (self.p + 1) // 4, self.p)
        return y if y * y % self.p == rhs else None

    def _add(self, p1, p2):
        if p1 is None:
            return p2
        if p2 is None:
            return p1
        (x1, y1), (x2, y2) = p1, p2
        if x1 == x2 and (y1 + y2) % self.p == 0:
            return None
        if p1 == p2:
            slope = (3 * x1 * x1 + self.a) * pow(2 * y1, -1, self.p)
        else:
            slope = (y2 - y1) * pow(x2 - x1, -1, self.p)
        x3 = (slope * slope - x1 - x2) % self.p
        return (x3, (slope * (x1 - x3) - y1) % self.p)

    def _mul(self, k: int, point):
        result = None
        while k:
            if k & 1:
                result = self._add(result, point)
            point = self._add(point, point)
            k >>= 1
        return result

    def verify_digest(self, key: bytes, signature: bytes, message: bytes) -> bool:
        """SEC1 compressed key, low-S r||s, message is the raw digest."""
        if len(key) != 33 or key[0] not in (2, 3):
            raise VMError("CHECKDATASIG key encoding")
        if len(signature) != 64:
            raise VMError("CHECKDATASIG signature width")
        x = int.from_bytes(key[1:], "big")
        if x >= self.p:
            raise VMError("CHECKDATASIG key encoding")
        y = self._lift(x)
        if y is None:
            raise VMError("CHECKDATASIG key encoding")
        if (y & 1) != (key[0] & 1):
            y = self.p - y
        r = int.from_bytes(signature[:32], "big")
        s = int.from_bytes(signature[32:], "big")
        if not (1 <= r < self.n and 1 <= s <= self.n // 2):
            return False
        e = int.from_bytes(message, "big")
        w = pow(s, -1, self.n)
        point = self._add(self._mul(e * w % self.n, self.g),
                          self._mul(r * w % self.n, (x, y)))
        return point is not None and point[0] % self.n == r


_P256 = _Curve(
    2**256 - 2**224 + 2**192 + 2**96 - 1,
    2**256 - 2**224 + 2**192 + 2**96 - 1 - 3,
    0x5AC635D8AA3A93E7B3EBBD55769886BC651D06B0CC53B0F63BCE3C3E27D2604B,
    0x6B17D1F2E12C4247F8BCE6E563A440F277037D812DEB33A0F4A13945D898C296,
    0x4FE342E2FE1A7F9B8EE7EB4A7C0F9E162BCE33576B315ECECBB6406837BF51F5,
    0xFFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551)
_SECP256K1 = _Curve(
    2**256 - 2**32 - 977, 0, 7,
    0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798,
    0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8,
    0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141)


def _verify_bip340_message(signature: bytes, public_key: bytes, message: bytes) -> bool:
    if len(public_key) != 32:
        raise VMError("CHECKDATASIG x-only key encoding")
    if len(signature) != 64:
        raise VMError("CHECKDATASIG signature width")
    try:
        from coincurve import PublicKeyXOnly
    except ImportError as exc:
        raise UnsupportedFeature("coincurve 21 dependency is required for CHECKDATASIG") from exc
    try:
        key = PublicKeyXOnly(public_key)
    except ValueError as exc:
        raise VMError("CHECKDATASIG x-only key encoding") from exc
    try:
        return bool(key.verify(signature, message))
    except ValueError:
        return False


def _verify_datasig(signature: bytes, message: bytes, public_key: bytes,
                    algorithm: int) -> bool:
    if algorithm not in (0, 1, 2, 3):
        raise VMError("CHECKDATASIG algorithm")
    if len(message) != 32:
        raise VMError("CHECKDATASIG message width")
    if algorithm == 0:
        return _verify_bip340_message(signature, public_key, message)
    if algorithm == 1:
        return _P256.verify_digest(public_key, signature, message)
    if algorithm == 2:
        return _verify_ed25519(signature, public_key, message)
    return _SECP256K1.verify_digest(public_key, signature, message)


def _instruction(script: bytes, pos: int, profile: VMProfile) -> tuple[Instruction, int]:
    opcode = script[pos]
    pos += 1
    if 1 <= opcode <= 75:
        end = pos + opcode
        if end > len(script) or opcode > profile.max_element_bytes:
            raise VMError("truncated or oversized fixed push")
        return Instruction(opcode, script[pos:end]), end
    if opcode == 0x4c:
        reader = Reader(script[pos:])
        try:
            length = reader.compact_size(max_value=profile.max_element_bytes)
        except DecodeError as exc:
            raise VMError(str(exc)) from exc
        if 1 <= length <= 75:
            raise VMError("noncanonical PUSHDATA length")
        pos += reader.offset
        end = pos + length
        if end > len(script):
            raise VMError("truncated PUSHDATA")
        return Instruction(opcode, script[pos:end]), end
    return Instruction(opcode), pos


def success_scan(script: bytes, profile: VMProfile) -> bool:
    """Scan instruction boundaries only; ignore suffix immediately after success."""
    if not isinstance(script, bytes) or len(script) > profile.max_script_bytes:
        raise VMError("script exceeds explicit bound")
    pos = 0
    while pos < len(script):
        if script[pos] not in ASSIGNED:
            return True
        _, pos = _instruction(script, pos, profile)
    return False


def decode(script: bytes, profile: VMProfile) -> tuple[Node, ...]:
    """Decode the complete success-free script, including unreachable arms."""
    if success_scan(script, profile):
        raise VMError("automatic-success script has no ordinary AST")
    instructions = []
    pos = 0
    while pos < len(script):
        ins, pos = _instruction(script, pos, profile)
        instructions.append(ins)
    cursor = 0

    def sequence(depth: int, loop_depth: int, terminators: frozenset[int]) -> tuple[tuple[Node, ...], int | None]:
        nonlocal cursor
        if depth > profile.max_ast_depth:
            raise VMError("AST depth exceeded")
        nodes: list[Node] = []
        while cursor < len(instructions):
            ins = instructions[cursor]
            cursor += 1
            op = ins.opcode
            if op in (0x63, 0x64, 0x6a):
                if op not in terminators:
                    raise VMError("unmatched or crossing structure delimiter")
                return tuple(nodes), op
            if op in (0x61, 0x62):
                then_arm, end = sequence(depth + 1, loop_depth, frozenset((0x63, 0x64)))
                else_arm: tuple[Node, ...] = ()
                has_else = end == 0x63
                if end == 0x63:
                    else_arm, end = sequence(depth + 1, loop_depth, frozenset((0x64,)))
                if end != 0x64:
                    raise VMError("unclosed IF")
                nodes.append(Conditional(op, then_arm, else_arm, has_else))
            elif op in (0x67, 0x68, 0x69):
                if loop_depth >= 2:
                    raise VMError("loop nesting exceeds two")
                body, end = sequence(depth + 1, loop_depth + 1, frozenset((0x6a,)))
                if end != 0x6a:
                    raise VMError("unclosed ENUMERATE")
                nodes.append(Loop(op, body))
            else:
                nodes.append(ins)
        return tuple(nodes), None

    ast, end = sequence(0, 0, frozenset())
    assert end is None
    return ast


def _checked_cost(value: int, cap: int) -> int:
    if value > U128_MAX or value > cap:
        raise VMError("static cost exceeds bound")
    return value


def static_cost(ast: tuple[Node, ...], profile: VMProfile, *, input_count: int,
                output_count: int, initial_sizes: tuple[int, ...] = (),
                script_length: int = 0,
                field_sizes: Mapping[int, tuple[int, ...]] | None = None) -> int:
    """P05 size-aware structural charge; see ``vm_cost.static_size_cost``."""
    from .vm_cost import static_size_cost

    return static_size_cost(ast, profile, initial_sizes=initial_sizes,
                            script_length=script_length, input_count=input_count,
                            output_count=output_count, field_sizes=field_sizes).cost


def validate_invocation_inputs(script: bytes, args: tuple[bytes, ...],
                               profile: VMProfile, *, input_count: int,
                               output_count: int,
                               signing: SigningContext | None = None,
                               invocation: InvocationContext | None = None) -> tuple[bytes, ...]:
    """Check bounded invocation inputs before the instruction-boundary scan."""
    if not isinstance(script, bytes) or len(script) > profile.max_script_bytes:
        raise VMError("script exceeds explicit bound")
    if invocation is not None and not isinstance(invocation, InvocationContext):
        raise TypeError("invocation must be InvocationContext")
    if signing is not None and not isinstance(signing, SigningContext):
        raise TypeError("signing must be SigningContext")
    if type(input_count) is not int or type(output_count) is not int or not (0 <= input_count <= 65535 and 0 <= output_count <= 65535):
        raise VMError("invalid transaction counts")
    if not isinstance(args, tuple) or len(args) > profile.max_arguments or any(
        not isinstance(arg, bytes) or len(arg) > profile.max_element_bytes for arg in args
    ):
        raise VMError("argument framing exceeds bounds")
    if invocation is not None and (invocation.input_count != input_count or
                                   invocation.output_count != output_count):
        raise VMError("invocation context disagrees with transaction counts")
    if signing is not None and invocation is not None and (
        signing.invocation_kind != invocation.invocation_kind or
        signing.input_index != invocation.input_index or
        signing.output_count != invocation.output_count
    ):
        raise VMError("signing and invocation identities disagree")
    initial = args + ((number(invocation.mint_delta),) if invocation is not None and
                      invocation.invocation_kind == "mint" else ())
    if any(len(item) > profile.max_element_bytes for item in initial):
        raise VMError("initial element exceeds bound")
    if len(initial) > profile.max_stack_items or sum(map(len, initial)) > profile.max_vm_bytes:
        raise VMError("initial stack exceeds bounds")
    if signing is not None and (signing.output_count != output_count or
                                signing.input_index >= input_count):
        raise VMError("signing context indices disagree with invocation counts")
    if signing is not None and branch_leaf_hash(script) != signing.selected_leaf_hash:
        raise VMError("selected leaf does not match script")
    return initial


def evaluate(script: bytes, args: tuple[bytes, ...], profile: VMProfile, *,
             input_count: int | None = None, output_count: int | None = None,
             field_sizes: Mapping[int, tuple[int, ...]] | None = None,
             signing: SigningContext | None = None,
             invocation: InvocationContext | None = None) -> VMResult:
    """Evaluate one invocation; caller handles witness, membership and outer checks."""
    if invocation is not None:
        if input_count is not None and input_count != invocation.input_count:
            raise VMError("input count disagrees with invocation context")
        if output_count is not None and output_count != invocation.output_count:
            raise VMError("output count disagrees with invocation context")
        input_count, output_count = invocation.input_count, invocation.output_count
    else:
        input_count = 0 if input_count is None else input_count
        output_count = 0 if output_count is None else output_count
    initial = validate_invocation_inputs(script, args, profile, input_count=input_count,
                                         output_count=output_count, signing=signing,
                                         invocation=invocation)
    if success_scan(script, profile):
        charge = _checked_cost(len(script) * profile.structural_byte_cost, profile.max_invocation_cost)
        return VMResult(True, True, charge, None)
    ast = decode(script, profile)
    if invocation is not None:
        from .vm_cost import bind_authenticated_field_sizes
        field_sizes = bind_authenticated_field_sizes(
            field_sizes, invocation, max_element_bytes=profile.max_element_bytes)
    charge = _checked_cost(len(script) * profile.structural_byte_cost + static_cost(
        ast, profile, input_count=input_count, output_count=output_count,
        initial_sizes=tuple(map(len, initial)), script_length=len(script),
        field_sizes=field_sizes), profile.max_invocation_cost)
    stack = list(initial)
    alt: list[bytes] = []

    def pop() -> bytes:
        if not stack:
            raise VMError("stack underflow")
        return stack.pop()

    def push(value: bytes, *, alternate: bool = False) -> None:
        target = alt if alternate else stack
        cap = profile.max_altstack_items if alternate else profile.max_stack_items
        if len(value) > profile.max_element_bytes or len(target) >= cap or sum(map(len, stack)) + sum(map(len, alt)) + len(value) > profile.max_vm_bytes:
            raise VMError("VM stack bound exceeded")
        target.append(value)

    def require(n: int) -> None:
        if len(stack) < n:
            raise VMError("stack underflow")

    def context() -> InvocationContext:
        if invocation is None:
            raise UnsupportedFeature("introspection requires resolved invocation context")
        return invocation

    def input_view(index: int):
        try:
            return context().input(index)
        except IndexError as exc:
            raise VMError(str(exc)) from exc

    def coin_view(index: int):
        try:
            return context().coin(index)
        except IndexError as exc:
            raise VMError(str(exc)) from exc

    def output_view(index: int):
        try:
            return context().output(index)
        except IndexError as exc:
            raise VMError(str(exc)) from exc

    def execute(nodes: tuple[Node, ...], active_loops: int) -> int:
        for node in nodes:
            if isinstance(node, Conditional):
                condition = _boolean(pop())
                if node.opcode == 0x62:
                    condition = not condition
                signal = execute(node.then_arm if condition else node.else_arm, active_loops)
                if signal:
                    return signal
                continue
            if isinstance(node, Loop):
                if node.opcode == 0x67:
                    bound = input_count
                elif node.opcode == 0x68:
                    bound = output_count
                else:
                    bound = _numeric(pop())
                    if not 0 <= bound <= 256:
                        raise VMError("generic loop bound outside 0..256")
                for index in range(bound):
                    push(number(index))
                    signal = execute(node.body, active_loops + 1)
                    if signal:
                        if signal > 1:
                            return signal - 1
                        break
                continue
            op = node.opcode
            if node.data is not None:
                push(node.data)
            elif op == 0x00:
                push(number(0))
            elif 0x4d <= op <= 0x5d:
                push(number(-1 if op == 0x4d else op - 0x4d))
            elif op == 0x60:
                pass
            elif op == 0x65:
                if not _boolean(pop()):
                    raise VMError("VERIFY failed")
            elif op == 0x66:
                raise VMError("RETURN executed")
            elif op == 0x6b:
                depth = _numeric(pop())
                if not 1 <= depth <= active_loops:
                    raise VMError("BREAK depth outside active loops")
                return depth
            elif op == 0x70:
                value = pop()
                push(value, alternate=True)
            elif op == 0x71:
                if not alt:
                    raise VMError("alternate stack underflow")
                push(alt.pop())
            elif op in (0x72, 0x73, 0x74, 0x75, 0x76, 0x77):
                needed = {0x72: 2, 0x73: 2, 0x74: 3, 0x75: 4, 0x76: 6, 0x77: 4}[op]
                require(needed)
                if op == 0x72:
                    del stack[-2:]
                elif op == 0x73:
                    for value in stack[-2:].copy(): push(value)
                elif op == 0x74:
                    for value in stack[-3:].copy(): push(value)
                elif op == 0x75:
                    for value in stack[-4:-2].copy(): push(value)
                elif op == 0x76:
                    stack[-6:] = stack[-4:] + stack[-6:-4]
                else:
                    stack[-4:] = stack[-2:] + stack[-4:-2]
            elif op == 0x78:
                push(number(len(stack)))
            elif op == 0x79:
                pop()
            elif op == 0x7a:
                require(1)
                push(stack[-1])
            elif op == 0x7b:
                require(2)
                del stack[-2]
            elif op == 0x7c:
                require(2)
                push(stack[-2])
            elif op in (0x7d, 0x7e):
                index = _numeric(pop())
                if not 0 <= index < len(stack):
                    raise VMError("PICK/ROLL index out of range")
                if op == 0x7d:
                    push(stack[-1-index])
                else:
                    push(stack.pop(-1-index))
            elif op == 0x7f:
                require(3)
                stack[-3:] = stack[-2:] + stack[-3:-2]
            elif op == 0x80:
                require(2)
                stack[-2:] = stack[-2:][::-1]
            elif op == 0x81:
                require(2)
                value = stack[-1]
                push(value)
                stack[-3:] = [value, stack[-3], value]
            elif op == 0x88:
                b, a = pop(), pop()
                push(a + b)
            elif op == 0x89:
                index = _numeric(pop())
                data = pop()
                if not 0 <= index <= len(data):
                    raise VMError("SPLIT index out of range")
                push(data[:index])
                push(data[index:])
            elif op == 0x8c:
                require(1)
                push(number(len(stack[-1])))
            elif op == 0x91 or op == 0x92:
                b, a = pop(), pop()
                equal = a == b
                if op == 0x92:
                    if not equal:
                        raise VMError("EQUALVERIFY failed")
                else:
                    push(number(int(equal)))
            elif op in (0x98, 0x99, 0x9a, 0x9b, 0x9c, 0x9d):
                a = _numeric(pop())
                if op == 0x98: result = a + 1
                elif op == 0x99: result = a - 1
                elif op == 0x9a: result = -a
                elif op == 0x9b: result = abs(a)
                elif op == 0x9c:
                    if a not in (0, 1): raise VMError("noncanonical Boolean")
                    result = 1 - a
                else: result = int(a != 0)
                push(number(result))
            elif op == 0xa3:
                k, a = _numeric(pop()), _numeric(pop())
                if k >= 128:
                    if a: raise VMError("MULPOW2 overflow")
                    result = 0
                elif k >= 0:
                    result = a << k
                elif k <= -128:
                    result = 0
                else:
                    result = abs(a) >> -k
                    if a < 0: result = -result
                push(number(result))
            elif op in (0x9e, 0x9f, 0xa0, 0xa1, 0xa2, 0xa4, 0xa5, 0xa6, 0xa7,
                        0xa8, 0xa9, 0xaa, 0xab, 0xac, 0xad, 0xae):
                b, a = _numeric(pop()), _numeric(pop())
                if op in (0xa4, 0xa5) and (a not in (0, 1) or b not in (0, 1)):
                    raise VMError("noncanonical Boolean")
                if op in (0xa1, 0xa2):
                    if b == 0 or (a == INT_MIN and b == -1): raise VMError("invalid division")
                    q = (abs(a) // abs(b)) * (-1 if (a < 0) != (b < 0) else 1)
                    result = q if op == 0xa1 else a - q * b
                else:
                    result = {
                        0x9e: lambda: a+b, 0x9f: lambda: a-b, 0xa0: lambda: a*b,
                        0xa4: lambda: int(bool(a) and bool(b)), 0xa5: lambda: int(bool(a) or bool(b)),
                        0xa6: lambda: int(a == b), 0xa7: lambda: int(a == b),
                        0xa8: lambda: int(a != b), 0xa9: lambda: int(a < b),
                        0xaa: lambda: int(a > b), 0xab: lambda: int(a <= b),
                        0xac: lambda: int(a >= b), 0xad: lambda: min(a, b),
                        0xae: lambda: max(a, b),
                    }[op]()
                if op == 0xa7:
                    if not result: raise VMError("NUMEQUALVERIFY failed")
                else:
                    push(number(result))
            elif op == 0xaf:
                hi, lo, x = _numeric(pop()), _numeric(pop()), _numeric(pop())
                push(number(int(lo <= x < hi)))
            elif op in (0xb0, 0xb1):
                carry = _numeric(pop())
                b, a = _unsigned(pop()), _unsigned(pop())
                if carry not in (0, 1):
                    raise VMError("carry is not N(0)/N(1)")
                if op == 0xb0:
                    total = a + b + carry
                    push(_unsigned_bytes(total & _U128_MASK))
                    push(number(total >> 128))
                else:
                    push(_unsigned_bytes((a - b - carry) % (1 << 128)))
                    push(number(int(a < b + carry)))
            elif op == 0xb2:
                b, a = _unsigned(pop()), _unsigned(pop())
                product = a * b
                push(_unsigned_bytes(product >> 128))
                push(_unsigned_bytes(product & _U128_MASK))
            elif op == 0xb3:
                push(number(_log2_q64(_numeric(pop()))))
            elif op == 0xb4:
                value = _numeric(pop())
                if value < 0:
                    raise VMError("SQRT requires x>=0")
                push(number(math.isqrt(value)))
            elif op == 0xbd:
                algorithm = _numeric(pop())
                public_key, message, signature = pop(), pop(), pop()
                push(number(int(_verify_datasig(signature, message, public_key, algorithm))))
            elif op in (0xb8, 0xb9):
                data = pop()
                digest = sha256(data).digest()
                push(digest if op == 0xb8 else sha256(digest).digest())
            elif op == 0xba:
                data = pop()
                try:
                    from blake3 import blake3
                except ImportError as exc:
                    raise UnsupportedFeature("blake3 dependency is required for BLAKE3") from exc
                push(blake3(data).digest())
            elif op in (0xbb, 0xbc):
                public_key, signature = pop(), pop()
                verified = _verify_checksig(signature, public_key, signing)
                if op == 0xbc:
                    if not verified:
                        raise VMError("CHECKSIGVERIFY failed")
                else:
                    push(number(int(verified)))
            elif op == 0xbe:
                push(branch_leaf_hash(pop()))
            elif op == 0xbf:
                right, left = pop(), pop()
                if len(left) != 32 or len(right) != 32:
                    raise VMError("node children must be h32")
                from .signing import _branch_node
                push(_branch_node(left, right))
            elif op in (0xc0, 0xc1):
                algorithm = _numeric(pop())
                proof = pop()
                key = pop() if op == 0xc1 else None
                accumulator = pop()
                if algorithm not in range(4) or len(accumulator) != 32 or len(proof) % 32:
                    raise VMError("invalid Merkle operands")
                steps = len(proof) // 32
                if (op == 0xc0 and steps > 64) or (op == 0xc1 and
                    (not 1 <= len(key) <= 32 or steps > 8 * len(key))):
                    raise VMError("Merkle depth/key bound")
                from .signing import _tagged
                from blake3 import blake3
                for step in range(steps):
                    sibling = proof[32 * step:32 * (step + 1)]
                    if op == 0xc0:
                        left, right = sorted((accumulator, sibling), key=lambda b: int.from_bytes(b, "little"))
                    else:
                        left, right = ((sibling, accumulator) if (key[step // 8] >> (step % 8)) & 1
                                       else (accumulator, sibling))
                    pair = left + right
                    if algorithm == 0:
                        accumulator = _tagged("Lotus/v2/branch" if op == 0xc0 else "Lotus/v2/merkleidx",
                            b"\x01" + (b"" if op == 0xc0 else step.to_bytes(2, "little")) + pair)
                    elif algorithm == 1:
                        accumulator = blake3(pair).digest()
                    else:
                        accumulator = sha256(pair).digest()
                        if algorithm == 3:
                            accumulator = sha256(accumulator).digest()
                push(accumulator)
            elif op == 0xc2:
                mode = _numeric(pop())
                if signing is None:
                    raise UnsupportedFeature("SIGHASH requires authenticated context")
                if mode not in (0, 1, 2) or (mode and signing.invocation_kind != "spend") or (mode == 2 and signing.input_index >= signing.output_count):
                    raise VMError("invalid signing mode")
                if mode not in signing.messages:
                    raise UnsupportedFeature("signing mode message unavailable")
                push(signing.messages[mode])
            elif op == 0xc8:
                context()
                push(number(7))
            elif op in (0xcc, 0xcd, 0xce, 0xcf):
                ctx = context()
                if ctx.transaction is None:
                    raise UnsupportedFeature("exact transaction context required")
                if op == 0xcc:
                    push(number(ctx.transaction.lock >> 8))
                elif op == 0xcd:
                    push(number(ctx.transaction.lock & 255))
                else:
                    push(ctx.txid if op == 0xce else ctx.chain_id)
            elif op == 0xc9:
                push(number(context().input_count))
            elif op == 0xca:
                push(number(context().output_count))
            elif op == 0xcb:
                push(number(context().mint_count))
            elif op == 0xd0:
                push(number(context().input_index))
            elif op == 0xd1:
                push(number(input_view(_numeric(pop())).flags))
            elif op in (0xd2, 0xd3, 0xd4, 0xd5):
                index = _numeric(pop())
                input_view(index)
                ctx = context()
                if ctx.transaction is None:
                    raise UnsupportedFeature("exact input context required")
                item = ctx.transaction.inputs[index]
                if op == 0xd5 and item.flags != 1:
                    raise VMError("path index at nonspend input")
                push(item.prev_txid if op == 0xd2 else number(
                    {0xd3: item.prev_index, 0xd4: item.sequence, 0xd5: item.path_index}[op]))
            elif op in (0xd8, 0xda, 0xe3, 0xe5):
                item = coin_view(_numeric(pop())) if op < 0xe0 else output_view(_numeric(pop()))
                push(number(len(item.branches if op in (0xd8, 0xe3) else item.paths)))
            elif op in (0xd9, 0xdb, 0xe4, 0xe6):
                subindex, index = _numeric(pop()), _numeric(pop())
                item = coin_view(index) if op < 0xe0 else output_view(index)
                collection = item.branches if op in (0xd9, 0xe4) else item.paths
                if not 0 <= subindex < len(collection):
                    raise VMError("field index out of range")
                value = collection[subindex]
                push(value if op in (0xd9, 0xe4) else encode_compact_size(len(value)) +
                     b"".join(encode_compact_size(i) for i in value))
            elif op in (0xdc, 0xe7):
                item = coin_view(_numeric(pop())) if op == 0xdc else output_view(_numeric(pop()))
                push(encode_output(item, context().output_profile))
            elif op == 0xd6:
                push(number(coin_view(_numeric(pop())).value))
            elif op == 0xd7:
                coin = coin_view(_numeric(pop()))
                push(coin.token_id if coin.token_id is not None else bytes(32))
            elif op == 0xdd:
                root = pop()
                coin = coin_view(_numeric(pop()))
                push(number(int(requires_branch(coin, root))))
            elif op == 0xe0:
                push(number(output_view(_numeric(pop())).flags))
            elif op == 0xe1:
                push(number(output_view(_numeric(pop())).value))
            elif op == 0xe2:
                output = output_view(_numeric(pop()))
                push(output.token_id if output.token_id is not None else bytes(32))
            elif op == 0xe8:
                root = pop()
                output = output_view(_numeric(pop()))
                push(number(int(requires_branch(output, root))))
            elif op == 0xe9:
                root, index = pop(), _numeric(pop())
                if len(root) != 32:
                    raise VMError("exclusive root width")
                item = output_view(index)
                push(number(int(requires_branch(item, root) and any(
                    len(path) == 1 and item.branches[path[0]] == root for path in item.paths))))
            elif op == 0xea:
                root, index = pop(), _numeric(pop())
                if len(root) != 32 or context().invocation_kind != "spend":
                    raise VMError("continuation requires spend and h32")
                coin = context().coin(context().input_index)
                item = output_view(index)
                branches = list(coin.branches)
                branches[context().selected_branch_index] = root
                push(number(int(not item.flags & 2 and len(set(branches)) == len(branches)
                    and item.paths == coin.paths and item.branches == tuple(branches))))
            elif op == 0xf0:
                context()
                push(script)
            elif op in (0xf3, 0xf4):
                bound, kind = _numeric(pop()), _numeric(pop())
                ctx = context()
                if ctx.transaction is None:
                    raise UnsupportedFeature("exact transaction context required")
                if op == 0xf3:
                    lock = ctx.transaction.lock
                    if kind not in (1, 2) or not 0 <= bound < 1 << 56 or lock & 255 != kind or lock >> 8 < bound:
                        raise VMError("absolute lock unsatisfied")
                else:
                    item = ctx.transaction.inputs[ctx.input_index]
                    if item.flags != 1 or kind not in (1, 2) or not 0 <= bound <= 65535 or item.sequence == 0xffffffff or bool(item.sequence & (1 << 22)) != (kind == 2) or item.sequence & 65535 < bound:
                        raise VMError("relative lock unsatisfied")
            elif op == 0xf1:
                push(number(1 if context().invocation_kind == "spend" else 3))
            elif op == 0xf2:
                push(context().branch_root)
            else:
                raise UnsupportedFeature(f"assigned opcode {op:02x} is outside this VM slice")
        return 0

    if execute(ast, 0):
        raise VMError("BREAK escaped top level")
    if stack != [number(1)] or alt:
        raise VMError("unclean final stacks")
    return VMResult(True, False, charge, tuple(stack))
