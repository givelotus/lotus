"""P05 abstract size bounds and deterministic static VM cost algebra.

Only charges are selected here. Unknown syntax paths use the element maximum;
this pass never decides invocation validity.
"""

from dataclasses import dataclass
from typing import Mapping, Sequence

from .encoding import Output, encode_output
from .vm import (Conditional, Instruction, Loop, Node, UnsupportedFeature,
                 VMError, VMProfile, U128_MAX, _checked_cost)
from .vm_context import InvocationContext


@dataclass(frozen=True)
class SizeState:
    main: tuple[int, ...] | None
    alt: tuple[int, ...] | None


UNKNOWN = SizeState(None, None)


@dataclass(frozen=True)
class SizeCharge:
    cost: int
    state: SizeState | None
    exits: Mapping[int, SizeState]
    worst_cost: int


def _merge(a: SizeState | None, b: SizeState | None) -> SizeState | None:
    if a is None:
        return b
    if b is None:
        return a
    if a.main is None or b.main is None or len(a.main) != len(b.main) or len(a.alt) != len(b.alt):
        return UNKNOWN
    return SizeState(tuple(map(max, a.main, b.main)), tuple(map(max, a.alt, b.alt)))


def _same_height(a: SizeState, b: SizeState) -> bool:
    return (a.main is not None and b.main is not None and
            len(a.main) == len(b.main) and len(a.alt) == len(b.alt))


def _literal(ins: Instruction | None) -> int | None:
    if ins is None:
        return None
    if ins.data is not None:
        return int.from_bytes(ins.data, "little", signed=True) if len(ins.data) == 16 else None
    if ins.opcode == 0:
        return 0
    if ins.opcode == 0x4d:
        return -1
    if 0x4e <= ins.opcode <= 0x5d:
        return ins.opcode - 0x4d
    return None


# Result width classes for assigned operations whose execution is outside this
# interpreter slice. This still selects conservative costs for their syntax.
NUMERIC = frozenset((0x78, 0x8b, 0x8c, *range(0x98, 0xb5),
                     0xc8, 0xc9, 0xca, 0xcb, 0xcc, 0xcd,
                     0xd0, 0xd1, 0xd3, 0xd4, 0xd5, 0xd6, 0xd8, 0xda,
                     0xe0, 0xe1, 0xe3, 0xe5, 0xe8, 0xe9, 0xea, 0xf1))
HASHES = frozenset((*range(0xb8, 0xbb), 0xbe, 0xbf, 0xc0, 0xc1, 0xc2,
                    0xce, 0xcf, 0xd2, 0xd7, 0xd9, 0xe2, 0xe4, 0xf2))
FIELD_READS = frozenset((0xdb, 0xdc, 0xe6, 0xe7, 0xf0))


def _path_sizes(outputs: Sequence[Output]) -> tuple[int, ...]:
    widths: list[int] = []
    for output in outputs:
        for slot, path in enumerate(output.paths):
            encoded = 1 + len(path)
            if slot >= len(widths):
                widths.extend([0] * (slot + 1 - len(widths)))
            widths[slot] = max(widths[slot], encoded)
    return tuple(widths)


def _output_size(output: Output, context: InvocationContext) -> int:
    try:
        return len(encode_output(output, context.output_profile))
    except ValueError as exc:
        raise VMError("field-size output encoding") from exc


def derive_field_sizes(context: InvocationContext) -> dict[int, tuple[int, ...]]:
    """Serialized sizes for UTXOPATH, UTXOOUTPUT, OUTPUTPATH and OUTPUTRECORD.

    Path slots are ``1 + len(path)``, the bytes those opcodes push. An input
    with no resolved coin contributes 0. Empty path vectors mean no path exists.
    """
    if not isinstance(context, InvocationContext):
        raise TypeError("field sizes require an invocation context")
    coins = tuple(item.coin for item in context.inputs if item.coin is not None)
    coin_sizes = []
    for item in context.inputs:
        coin_sizes.append(0 if item.coin is None else _output_size(item.coin, context))
    return {
        0xdb: _path_sizes(coins),
        0xdc: tuple(coin_sizes),
        0xe6: _path_sizes(context.outputs),
        0xe7: tuple(_output_size(output, context) for output in context.outputs),
    }


def _paths_uncovered(hint: tuple[int, ...], outputs: Sequence[Output]) -> bool:
    if not hint:
        return False
    widest = max(hint)
    for output in outputs:
        for slot, path in enumerate(output.paths):
            encoded = 1 + len(path)
            if widest < encoded or (slot < len(hint) and hint[slot] < encoded):
                return True
    return False


def bind_authenticated_field_sizes(
    field_sizes: Mapping[int, tuple[int, ...]] | None,
    context: InvocationContext | None,
    *,
    max_element_bytes: int | None = None,
) -> dict[int, tuple[int, ...]]:
    """Fill absent hints from ``context``. A larger hint stays; a smaller one errors.

    With no context the caller hints are returned unchanged. An empty map means
    the size pass keeps MAX_ELEMENT_BYTES. A derived size above the element cap
    is capped, which matches the size pass and cannot under-charge a push.
    """
    merged = {op: tuple(sizes) for op, sizes in (field_sizes or {}).items()}
    if context is None:
        return merged
    derived = derive_field_sizes(context)
    coins = tuple(item.coin for item in context.inputs if item.coin is not None)
    for op, hint in merged.items():
        if not hint or op == 0xf0:
            continue
        if op in (0xe7, 0xdc):
            expected = derived[op]
            if len(hint) != len(expected):
                raise VMError("field-size hint count")
            if any(got < need for got, need in zip(hint, expected)):
                raise VMError("field-size hint below authenticated field")
        elif op in (0xdb, 0xe6):
            sources = coins if op == 0xdb else context.outputs
            if _paths_uncovered(hint, sources):
                raise VMError("field-size hint below authenticated field")
    for op, sizes in derived.items():
        if not sizes or merged.get(op):
            continue
        if max_element_bytes is not None:
            sizes = tuple(min(size, max_element_bytes) for size in sizes)
        if sizes:
            merged[op] = sizes
    return merged


def static_size_cost(ast: tuple[Node, ...], profile: VMProfile, *,
                     initial_sizes: tuple[int, ...], script_length: int,
                     input_count: int, output_count: int,
                     field_sizes: Mapping[int, tuple[int, ...]] | None = None) -> SizeCharge:
    """Return P05 static cost and abstract exit state for an ordinary script.

    Cost functions receive `(operand_size_bounds, result_size_bounds)` and
    must be positive, monotone conservative upper bounds over those sizes.
    Missing field-size vectors fall back to MAX_ELEMENT_BYTES. This function
    does not read a transaction; bind_authenticated_field_sizes first when an
    invocation context is present.
    """
    limit = profile.max_element_bytes
    fields = field_sizes or {}
    if any(type(size) is not int or not 0 <= size <= limit for size in initial_sizes):
        raise ValueError("invalid initial size bounds")
    for op, sizes in fields.items():
        if op not in FIELD_READS or any(type(size) is not int or not 0 <= size <= limit for size in sizes):
            raise ValueError("invalid field-size vector")

    def charge(op: int, operands: tuple[int, ...], results: tuple[int, ...], *,
               enforce: bool = True) -> int:
        try:
            formula = profile.opcode_costs[op]
        except KeyError as exc:
            raise UnsupportedFeature(f"missing static charge for assigned opcode {op:02x}") from exc
        amount = formula(operands, results) if callable(formula) else formula
        if type(amount) is not int or amount <= 0:
            raise ValueError(f"invalid cost formula for {op:02x}")
        return _checked_cost(amount, U128_MAX) if enforce else amount

    def merkle_step(selector: int | None) -> int:
        # resources-and-parameters.md charges max(C_blake3, C_hash256). That
        # sentence under-charges algorithm 0, whose tagged preimage is 96
        # bytes rather than a 64-byte pair, and it ignores a schedule where
        # SHA256 is the dearest of the four. Use the max of all four.
        tagged, pair, digest = (96,), (64,), (32,)
        options = (
            charge(0xba, tagged, digest),
            charge(0xba, pair, digest),
            charge(0xb8, pair, digest),
            charge(0xb9, pair, digest),
        )
        if selector is not None and 0 <= selector <= 3:
            return options[selector]
        return max(options)

    def merkle_steps(op: int, proof_bound: int | None) -> int:
        if op == 0xc0:
            return 64 if proof_bound is None else min(64, proof_bound // 32)
        if op == 0xc1:
            # Unknown proofs are bounded by the element-size limit. A known
            # proof uses its own bound, capped at 256 indexed steps.
            if proof_bound is None:
                return min(256, limit // 32)
            return min(256, proof_bound // 32)
        return 0

    def add_merkle(op: int, base: int, selector: int | None,
                   proof_bound: int | None, *, enforce: bool) -> int:
        steps = merkle_steps(op, proof_bound)
        if steps == 0:
            return base
        extra = merkle_step(selector) * steps
        if not enforce:
            return base + extra
        return _checked_cost(base + extra, U128_MAX)

    def worst_charge(op: int, *, enforce: bool) -> int:
        base = charge(op, (limit,) * 6, (limit,) * 4, enforce=enforce)
        return add_merkle(op, base, None, None, enforce=enforce)

    def transfer(ins: Instruction, state: SizeState, previous: Instruction | None) -> tuple[SizeState, int]:
        op = ins.opcode
        if state.main is None:
            return UNKNOWN, worst_charge(op, enforce=True)
        main, alt = list(state.main), list(state.alt)
        operands: list[int] = []
        result: list[int] = []
        merkle_op: tuple[int, int | None, int] | None = None

        def pop() -> int:
            if not main:
                raise IndexError
            size = main.pop()
            operands.append(size)
            return size

        def push(size: int) -> None:
            main.append(min(size, limit))
            result.append(min(size, limit))

        try:
            if ins.data is not None:
                push(len(ins.data))
            elif op == 0 or 0x4d <= op <= 0x5d:
                push(16)
            elif op == 0x60 or op == 0x66:
                pass
            elif op == 0x70:
                alt.append(pop())
            elif op == 0x71:
                if not alt: raise IndexError
                size = alt.pop()
                operands.append(size)
                push(size)
            elif op == 0x72:
                pop(); pop()
            elif op in (0x73, 0x74, 0x75):
                count, offset = {0x73: (2, 2), 0x74: (3, 3), 0x75: (2, 4)}[op]
                if len(main) < offset: raise IndexError
                for size in main[-offset:-offset+count or None].copy(): push(size)
            elif op in (0x76, 0x77):
                count = 6 if op == 0x76 else 4
                if len(main) < count: raise IndexError
                operands.extend(main[-count:])
                main[-count:] = main[-count+2:] + main[-count:-count+2]
            elif op == 0x78:
                push(16)
            elif op == 0x79:
                pop()
            elif op == 0x7a:
                if not main: raise IndexError
                operands.append(main[-1])
                push(main[-1])
            elif op == 0x7b:
                if len(main) < 2: raise IndexError
                operands.append(main.pop(-2))
            elif op == 0x7c:
                if len(main) < 2: raise IndexError
                operands.append(main[-2])
                push(main[-2])
            elif op in (0x7d, 0x7e):
                pop()
                index = _literal(previous)
                if index is not None and 0 <= index < len(main):
                    selected = main[-1-index]
                    operands.append(selected)
                    if op == 0x7d: push(selected)
                    else: push(main.pop(-1-index))
                else:
                    largest = max(main, default=limit)
                    operands.append(largest)
                    if op == 0x7d: push(largest)
                    else: main[:] = [largest] * len(main)
            elif op == 0x7f:
                if len(main) < 3: raise IndexError
                operands.extend(main[-3:])
                main[-3:] = main[-2:] + main[-3:-2]
            elif op == 0x80:
                if len(main) < 2: raise IndexError
                operands.extend(main[-2:])
                main[-2:] = main[-2:][::-1]
            elif op == 0x81:
                if len(main) < 2: raise IndexError
                a, b = main[-2:]
                operands.extend((a, b))
                main[-2:] = [b, a, b]
                result.append(b)
            elif op == 0x88:
                b, a = pop(), pop()
                push(a+b)
            elif op == 0x89:
                pop(); size = pop()
                push(size); push(size)
            elif op == 0x8a:
                pop(); pop()
                width = _literal(previous)
                push(width if width is not None and 0 <= width <= limit else limit)
            elif op == 0x8b:
                pop(); push(16)
            elif op == 0x8c:
                if not main: raise IndexError
                operands.append(main[-1]); push(16)
            elif op == 0x8d:
                push(pop())
            elif op in (0x8e, 0x8f, 0x90, 0x93):
                b, a = pop(), pop()
                push(max(a,b))
                if op == 0x93: push(max(a,b))
            elif op in (0x91, 0x92):
                pop(); pop()
                if op == 0x91: push(16)
            elif op == 0x94:
                pop(); push(pop())
            elif op in (*range(0x98, 0x9e), 0xb3, 0xb4):
                pop(); push(16)
            elif op in (0x9e, 0x9f, 0xa0, 0xa1, 0xa2, 0xa3, *range(0xa4, 0xaf)):
                pop(); pop()
                if op != 0xa7: push(16)
            elif op in (0xaf, 0xb0, 0xb1):
                pop(); pop(); pop()
                if op == 0xaf: push(16)
                else: push(16); push(16)
            elif op == 0xb2:
                pop(); pop(); push(16); push(16)
            elif op in HASHES:
                arity = {0xbf: 2, 0xc0: 3, 0xc1: 4, 0xc2: 1,
                         0xd9: 2, 0xe4: 2}.get(op, 0 if op in (0xce, 0xcf, 0xf2) else 1)
                proof_bound = 0
                for index in range(arity):
                    operand = pop()
                    # Top is the selector; the next pop is the proof.
                    if op in (0xc0, 0xc1) and index == 1:
                        proof_bound = operand
                push(32)
                if op in (0xc0, 0xc1):
                    merkle_op = (op, _literal(previous), proof_bound)
            elif op in (0xbb, 0xbc):
                pop(); pop()
                if op == 0xbb: push(16)
            elif op == 0xbd:
                pop(); pop(); pop(); pop(); push(16)
            elif op == 0xdd:
                pop(); pop(); push(16)
            elif op in NUMERIC:
                # A conservative shape for supported future context operations.
                if op in (0xd1, 0xd3, 0xd4, 0xd5, 0xd6, 0xd8, 0xda, 0xe0, 0xe1,
                          0xe3, 0xe5): pop()
                if op in (0xe8, 0xe9, 0xea): pop(); pop()
                push(16)
            elif op in FIELD_READS:
                # The literal is the top operand: input/output index for a
                # complete read, path slot for UTXOPATH/OUTPUTPATH. An in-range
                # constant uses that slot; anything else uses the widest hint.
                index = _literal(previous)
                for _ in range(2 if op in (0xdb, 0xe6) else 0 if op == 0xf0 else 1): pop()
                sizes = fields.get(op)
                if op == 0xf0:
                    size = script_length
                elif sizes and index is not None and 0 <= index < len(sizes):
                    size = sizes[index]
                else:
                    size = max(sizes) if sizes else limit
                push(size)
            else:
                return UNKNOWN, worst_charge(op, enforce=True)
        except IndexError:
            return UNKNOWN, worst_charge(op, enforce=True)
        base = charge(op, tuple(operands), tuple(result))
        if merkle_op is not None:
            base = add_merkle(merkle_op[0], base, merkle_op[1], merkle_op[2], enforce=True)
        return SizeState(tuple(main), tuple(alt)), base

    def sequence(nodes: tuple[Node, ...], state: SizeState, entries: tuple[SizeState, ...]) -> SizeCharge:
        current: SizeState | None = state
        exits: dict[int, SizeState] = {}
        total = 0
        worst_total = 0
        previous: Instruction | None = None
        for node in nodes:
            starting = current if current is not None else UNKNOWN
            if isinstance(node, Instruction):
                if node.opcode == 0x6b:
                    if starting.main is None or not starting.main:
                        after = UNKNOWN
                    else:
                        after = SizeState(starting.main[:-1], starting.alt)
                    literal = _literal(previous)
                    targets = (1,) if literal == 1 and entries else range(1, len(entries) + 1)
                    for depth in targets:
                        target = entries[-depth]
                        exit_state = after if _same_height(after, target) else UNKNOWN
                        exits[depth] = _merge(exits.get(depth), exit_state)
                    part = charge(node.opcode, (16 if starting.main is not None else limit,), ())
                    current = None
                elif node.opcode == 0x65:
                    next_state = (SizeState(starting.main[:-1], starting.alt)
                                  if starting.main is not None and starting.main else UNKNOWN)
                    part = charge(node.opcode, (starting.main[-1] if starting.main else limit,), ())
                    current = next_state if current is not None else None
                else:
                    next_state, part = transfer(node, starting, previous)
                    current = next_state if current is not None else None
                worst_part = worst_charge(node.opcode, enforce=False)
                previous = node
            elif isinstance(node, Conditional):
                condition_size = starting.main[-1] if starting.main else limit
                arm_start = (SizeState(starting.main[:-1], starting.alt)
                             if starting.main is not None and starting.main else UNKNOWN)
                left = sequence(node.then_arm, arm_start, entries)
                right = sequence(node.else_arm, arm_start, entries)
                part = charge(node.opcode, (condition_size,), ()) + charge(0x64, (), ())
                if node.has_else: part += charge(0x63, (), ())
                part += max(left.cost, right.cost)
                worst_part = (charge(node.opcode, (limit,) * 6, (limit,) * 4, enforce=False) +
                              charge(0x64, (), (), enforce=False) +
                              (charge(0x63, (), (), enforce=False) if node.has_else else 0) +
                              max(left.worst_cost, right.worst_cost))
                current = _merge(left.state, right.state) if current is not None else None
                for source in (left.exits, right.exits):
                    for depth, exit_state in source.items():
                        exits[depth] = _merge(exits.get(depth), exit_state)
                previous = None
            else:
                loop_entry = starting
                if node.opcode == 0x69:
                    loop_entry = (SizeState(starting.main[:-1], starting.alt)
                                  if starting.main is not None and starting.main else UNKNOWN)
                bound = {0x67: input_count, 0x68: output_count, 0x69: 256}[node.opcode]
                body_start = (SizeState(loop_entry.main + (16,), loop_entry.alt)
                              if loop_entry.main is not None else UNKNOWN)
                inner_entries = entries + (loop_entry,)
                body = sequence(node.body, body_start, inner_entries)
                local_break = body.exits.get(1)
                joined = _merge(body.state, local_break)
                if joined is not None and _same_height(joined, loop_entry):
                    widened = SizeState(tuple(limit if x > y else y for x, y in zip(joined.main, loop_entry.main)),
                                        tuple(limit if x > y else y for x, y in zip(joined.alt, loop_entry.alt)))
                    second_start = SizeState(widened.main + (16,), widened.alt)
                    second = sequence(node.body, second_start, inner_entries)
                    second_joined = _merge(second.state, second.exits.get(1))
                    if second_joined is not None and _same_height(second_joined, widened) and all(
                        x <= y for x, y in zip(second_joined.main + second_joined.alt,
                                                  widened.main + widened.alt)):
                        body = second
                        post = _merge(loop_entry, second_joined)
                    else:
                        body = SizeCharge(_checked_cost(second.worst_cost, U128_MAX), UNKNOWN,
                                          {depth: UNKNOWN for depth in second.exits}, second.worst_cost)
                        post = UNKNOWN
                elif joined is None:
                    post = _merge(loop_entry, local_break)
                else:
                    body = SizeCharge(_checked_cost(body.worst_cost, U128_MAX), UNKNOWN,
                                      {depth: UNKNOWN for depth in body.exits}, body.worst_cost)
                    post = UNKNOWN
                part = charge(node.opcode, (16,) if node.opcode == 0x69 else (), ())
                iteration = _checked_cost(charge(0x6a, (), ()) + body.cost, U128_MAX)
                part = _checked_cost(part + _checked_cost(bound * iteration, U128_MAX), U128_MAX)
                worst_part = (charge(node.opcode, (limit,) * 6, (limit,) * 4, enforce=False) +
                              bound * (charge(0x6a, (), (), enforce=False) + body.worst_cost))
                current = post if current is not None else None
                for depth, exit_state in body.exits.items():
                    if depth > 1:
                        exits[depth-1] = _merge(exits.get(depth-1), exit_state)
                previous = None
            total = _checked_cost(total + part, U128_MAX)
            worst_total += worst_part
        return SizeCharge(total, current, exits, worst_total)

    result = sequence(ast, SizeState(initial_sizes, ()), ())
    _checked_cost(result.cost, profile.max_invocation_cost)
    return result
