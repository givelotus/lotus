"""Bounded P03 VM reference slice; assigned unsupported operations fail closed.

The opcode allocation is the SHA-256 fb790b230e76befc90a1f183ea727cb3232d1f03e9b5838b10d025d96b9832da
snapshot of docs/lotus-v2/tools/opcodes.json (2026-10-14). No production limits
or cost coefficients are selected here.
"""

from dataclasses import dataclass
from hashlib import sha256
from types import MappingProxyType
from typing import Callable, Mapping

from .encoding import DecodeError, Reader, encode_compact_size


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
                               signing: SigningContext | None = None) -> None:
    """Check bounded invocation inputs before the instruction-boundary scan."""
    if not isinstance(script, bytes) or len(script) > profile.max_script_bytes:
        raise VMError("script exceeds explicit bound")
    if type(input_count) is not int or type(output_count) is not int or not (0 <= input_count <= 65535 and 0 <= output_count <= 65535):
        raise VMError("invalid transaction counts")
    if not isinstance(args, tuple) or len(args) > profile.max_arguments or any(
        not isinstance(arg, bytes) or len(arg) > profile.max_element_bytes for arg in args
    ):
        raise VMError("argument framing exceeds bounds")
    if len(args) > profile.max_stack_items or sum(map(len, args)) > profile.max_vm_bytes:
        raise VMError("initial stack exceeds bounds")
    if signing is not None and (signing.output_count != output_count or
                                signing.input_index >= input_count):
        raise VMError("signing context indices disagree with invocation counts")
    if signing is not None and branch_leaf_hash(script) != signing.selected_leaf_hash:
        raise VMError("selected leaf does not match script")


def evaluate(script: bytes, args: tuple[bytes, ...], profile: VMProfile, *,
             input_count: int = 0, output_count: int = 0,
             field_sizes: Mapping[int, tuple[int, ...]] | None = None,
             signing: SigningContext | None = None) -> VMResult:
    """Evaluate one invocation; caller handles witness, membership and outer checks."""
    validate_invocation_inputs(script, args, profile, input_count=input_count,
                               output_count=output_count, signing=signing)
    if success_scan(script, profile):
        charge = _checked_cost(len(script) * profile.structural_byte_cost, profile.max_invocation_cost)
        return VMResult(True, True, charge, None)
    ast = decode(script, profile)
    charge = _checked_cost(len(script) * profile.structural_byte_cost + static_cost(
        ast, profile, input_count=input_count, output_count=output_count,
        initial_sizes=tuple(map(len, args)), script_length=len(script),
        field_sizes=field_sizes), profile.max_invocation_cost)
    stack = list(args)
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
            elif op in (0xb8, 0xb9):
                data = pop()
                digest = sha256(data).digest()
                push(digest if op == 0xb8 else sha256(digest).digest())
            elif op in (0xbb, 0xbc):
                public_key, signature = pop(), pop()
                verified = _verify_checksig(signature, public_key, signing)
                if op == 0xbc:
                    if not verified:
                        raise VMError("CHECKSIGVERIFY failed")
                else:
                    push(number(int(verified)))
            else:
                raise UnsupportedFeature(f"assigned opcode {op:02x} is outside this VM slice")
        return 0

    if execute(ast, 0):
        raise VMError("BREAK escaped top level")
    if stack != [number(1)] or alt:
        raise VMError("unclean final stacks")
    return VMResult(True, False, charge, tuple(stack))
