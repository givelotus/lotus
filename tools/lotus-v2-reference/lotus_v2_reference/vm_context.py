"""Immutable, externally resolved input/output view for one P03 invocation.

These records are supplied by a transaction validator. They enforce local
shape and selected-branch consistency, not outpoint resolution, membership,
asset conservation or contextual block validity.
"""

from dataclasses import dataclass

from .encoding import Output, Profile as OutputProfile, encode_output


def _h32(value: bytes, name: str) -> None:
    if not isinstance(value, bytes) or len(value) != 32:
        raise ValueError(f"{name} must be h32")


def _freeze_output(value: Output, profile: OutputProfile) -> Output:
    if not isinstance(value, Output):
        raise ValueError("coin/output must be Output")
    if type(value.flags) is not int or type(value.value) is not int:
        raise ValueError("output flags and value must be integers")
    result = Output(value.flags, value.value, value.token_id,
                    tuple(value.branches), tuple(tuple(path) for path in value.paths))
    encode_output(result, profile)
    return result


@dataclass(frozen=True)
class InputView:
    flags: int
    coin: Output | None = None
    mint_token_id: bytes | None = None


@dataclass(frozen=True)
class InvocationContext:
    inputs: tuple[InputView, ...]
    outputs: tuple[Output, ...]
    invocation_kind: str
    input_index: int
    branch_root: bytes
    output_profile: OutputProfile
    selected_path_index: int | None = None
    selected_branch_index: int | None = None
    mint_delta: int | None = None
    transaction: object | None = None
    chain_id: bytes | None = None
    txid: bytes | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.output_profile, OutputProfile):
            raise ValueError("explicit output profile required")
        if not isinstance(self.inputs, tuple) or not isinstance(self.outputs, tuple):
            raise ValueError("inputs and outputs must be tuples")
        if len(self.inputs) > 65535 or len(self.outputs) > 65535:
            raise ValueError("transaction count exceeds u16")
        _h32(self.branch_root, "branch root")
        frozen_inputs = []
        for item in self.inputs:
            if not isinstance(item, InputView) or type(item.flags) is not int or item.flags not in (1, 2, 3):
                raise ValueError("invalid input view flags")
            if item.flags == 1:
                if item.coin is None or item.mint_token_id is not None:
                    raise ValueError("spend requires one coin and no mint token ID")
                coin = _freeze_output(item.coin, self.output_profile)
                if coin.flags & 2:
                    raise ValueError("burn output cannot be a spend input")
                frozen_inputs.append(InputView(1, coin))
            elif item.flags == 3:
                if item.coin is not None:
                    raise ValueError("mint has no resolved coin")
                _h32(item.mint_token_id, "mint token ID")
                if item.mint_token_id == bytes(32):
                    raise ValueError("mint token ID must be nonzero")
                frozen_inputs.append(InputView(3, None, item.mint_token_id))
            else:
                if item.coin is not None or item.mint_token_id is not None:
                    raise ValueError("coinbase has no resolved coin or mint token ID")
                frozen_inputs.append(InputView(2))
        frozen_outputs = tuple(_freeze_output(item, self.output_profile) for item in self.outputs)
        if any(item.flags == 2 for item in frozen_inputs):
            raise ValueError("coinbase input cannot be part of spend/mint invocation")
        object.__setattr__(self, "inputs", tuple(frozen_inputs))
        object.__setattr__(self, "outputs", frozen_outputs)
        if type(self.input_index) is not int or not 0 <= self.input_index < len(self.inputs):
            raise ValueError("invocation input index out of range")
        active = self.inputs[self.input_index]
        if self.invocation_kind == "spend":
            if active.flags != 1 or active.coin is None:
                raise ValueError("spend invocation requires spend input")
            if type(self.selected_path_index) is not int or not 0 <= self.selected_path_index < len(active.coin.paths):
                raise ValueError("selected path index out of range")
            if type(self.selected_branch_index) is not int or not 0 <= self.selected_branch_index < len(active.coin.branches):
                raise ValueError("selected branch index out of range")
            if self.selected_branch_index not in active.coin.paths[self.selected_path_index]:
                raise ValueError("selected branch is absent from selected path")
            if active.coin.branches[self.selected_branch_index] != self.branch_root:
                raise ValueError("selected branch root mismatch")
            if self.mint_delta is not None:
                raise ValueError("spend invocation has no minted delta")
        elif self.invocation_kind == "mint":
            if active.flags != 3 or active.mint_token_id != self.branch_root:
                raise ValueError("mint root must equal input token ID")
            if self.selected_path_index is not None or self.selected_branch_index is not None:
                raise ValueError("mint has no spend path selection")
            if type(self.mint_delta) is not int or not 0 < self.mint_delta <= (1 << 127) - 1:
                raise ValueError("mint delta must be positive N")
        else:
            raise ValueError("invocation kind must be spend or mint")

    @property
    def input_count(self) -> int:
        return len(self.inputs)

    @property
    def output_count(self) -> int:
        return len(self.outputs)

    @property
    def mint_count(self) -> int:
        return sum(item.flags == 3 for item in self.inputs)

    def input(self, index: int) -> InputView:
        if type(index) is not int or not 0 <= index < len(self.inputs):
            raise IndexError("input index out of range")
        return self.inputs[index]

    def coin(self, index: int) -> Output:
        item = self.input(index)
        if item.flags != 1 or item.coin is None:
            raise IndexError("UTXO read at mint or coinbase input")
        return item.coin

    def output(self, index: int) -> Output:
        if type(index) is not int or not 0 <= index < len(self.outputs):
            raise IndexError("output index out of range")
        return self.outputs[index]


def requires_branch(output: Output, root: bytes) -> bool:
    """P03 every-path predicate; malformed-length root is simply false."""
    if not isinstance(root, bytes) or len(root) != 32 or output.flags & 2 or not output.paths:
        return False
    try:
        branch_index = output.branches.index(root)
    except ValueError:
        return False
    return all(branch_index in path for path in output.paths)


def authenticated_context(tx, profile, chain_id: bytes, resolved: tuple,
                          input_index: int, witness_index: int):
    """Derive both VM views from exact transaction/coins, checking all proofs.

    The caller resolves coins against its authenticated state. This function
    authenticates branch membership, and derives messages without trusted
    digest inputs; contextual height/MTP locks remain an outer obligation.
    """
    from .signing import _prepare, identity_digests, signing_message, _branch_leaf
    from .vm import SigningContext
    _prepare(tx, profile, chain_id, resolved)
    active = tx.inputs[input_index]
    witness = active.witnesses[witness_index]
    mint = active.flags == 3
    delta = None
    if mint:
        token = active.prev_txid
        incoming = sum(c.value for c in resolved if c is not None and c.token_id == token)
        outgoing = sum(c.value for c in tx.outputs if c.token_id == token)
        delta = outgoing - incoming
        if not 0 < delta <= (1 << 127) - 1:
            raise ValueError("mint delta must be positive N")
    coin = resolved[input_index]
    branch = None if mint else coin.paths[active.path_index][witness_index]
    root = active.prev_txid if mint else coin.branches[branch]
    inputs = tuple(InputView(i.flags, c, i.prev_txid if i.flags == 3 else None)
                   for i, c in zip(tx.inputs, resolved))
    invocation = InvocationContext(inputs, tx.outputs, "mint" if mint else "spend",
        input_index, root, OutputProfile(16, 16, 812, 8192),
        None if mint else active.path_index, branch, delta, tx, chain_id,
        identity_digests(tx, profile, chain_id).txid)
    modes = (0,) if mint else ((0, 1, 2) if input_index < len(tx.outputs) else (0, 1))
    messages = {mode: signing_message(tx, profile, chain_id, resolved,
        input_index, witness_index, mode, None if delta is None else delta.to_bytes(16, "little"))
        for mode in modes}
    signing = SigningContext(_branch_leaf(witness.script), messages,
        invocation.invocation_kind, input_index, len(tx.outputs))
    return invocation, signing
