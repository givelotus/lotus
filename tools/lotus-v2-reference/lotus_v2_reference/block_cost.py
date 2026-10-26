"""Explicit conservative development P05 schedule; no launch coefficients.

All inputs derive from decoded transactions and resolved coins. Reserve 64
bytes of domain prefix for each hash and 27 collapsed sparse-tree levels per key.
The quadratic asset comparison bound covers deterministic ordered lookups.
Genesis allocation shares accounting/enforcement; extensions need separate
validated engines before using this boundary. No caller supplied cost override.
This abstract schedule excludes oracle view copying/rebuilding and redundant
verification of authenticated ancestor headers. Their implementation overhead
is an uncalibrated measurement gap; no resource-safety/calibration claim.
"""
from dataclasses import dataclass
from .encoding import encode_compact_size, encode_output
from .signing import encode_transaction, _input_wire
from .monetary import U64, U128, uint
from .block import OUTPUT_PROFILE, Coin

@dataclass(frozen=True)
class BlockCostProfile:
    hash_base: int
    hash_byte: int
    resolve_byte: int
    asset_comparison: int

    def __post_init__(self):
        for value in vars(self).values():
            if not uint(value, U64, 'cost coefficient'):
                raise ValueError('nonpositive block cost schedule')

    def hash(self, size):
        return self.hash_base + (size + 64) * self.hash_byte

@dataclass(frozen=True)
class TransactionCosts:
    account_linear: int
    enforce_linear: int


def _width(n):
    return len(encode_compact_size(n))


def _state_key(coin, cost):
    size = len(coin.encode())
    return cost.hash(36) + cost.hash(33 + _width(size) + size) + 27*cost.hash(67)


def authenticated_transaction_costs(tx, profile, coins, height, parent_mtp, invocation_cost, cost):
    total = len(encode_transaction(tx, profile)) + uint(invocation_cost, U128, 'invocation cost')
    total += 2*cost.hash(112)
    spends = 0
    for inp in tx.inputs:
        core, full = _input_wire(inp, profile, True), _input_wire(inp, profile, False)
        total += cost.hash(len(core)) + cost.hash(len(full))
        for w in inp.witnesses:
            total += cost.hash(1 + _width(len(w.script)) + len(w.script))
            total += len(w.siblings)*cost.hash(65)
        if inp.flags == 1:
            spends += 1
            coin = coins.get((inp.prev_txid, inp.prev_index))
            if coin is None:
                raise ValueError('cost unresolved coin')
            output = encode_output(coin.output or _native_output(coin), OUTPUT_PROFILE)
            total += len(coin.encode())*cost.resolve_byte
            total += cost.hash(_width(len(output)) + len(output))
            total += cost.hash(len(core) + _width(len(output)) + len(output))
            total += 256*cost.asset_comparison + _state_key(coin, cost)
        elif inp.flags == 3:
            total += cost.hash(0)
    input_trees = 4 if tx.inputs[0].flags == 2 else 6
    total += (input_trees*max(len(tx.inputs), 1) + 2*max(len(tx.outputs), 1))*cost.hash(66)
    for j, output in enumerate(tx.outputs):
        raw = encode_output(output, OUTPUT_PROFILE)
        total += cost.hash(_width(len(raw)) + len(raw))
        if not output.flags & 2:
            coin = Coin(bytes(32), j, output.value, output.branches[0], height,
                        parent_mtp, tx.inputs[0].flags == 2, output)
            total += _state_key(coin, cost)
    records = len(tx.inputs) + len(tx.outputs)
    total += (records*records + records + spends)*cost.asset_comparison
    total = uint(total, U64, 'transaction linear cost')
    return TransactionCosts(total, total)


def _native_output(coin):
    from .encoding import Output
    return Output(0, coin.value, None, (coin.branch,), ((0,),))


def authenticated_envelope_cost(frames, count, cost):
    uint(frames, U64, 'frame prefixes')
    uint(count, 0xffffffff, 'transaction count')
    if not count:
        raise ValueError('empty block cost')
    total = 138 + frames + (count*count+count)*cost.asset_comparison
    total += (2*count-1)*cost.hash(65) + cost.hash(37)
    total += sum(cost.hash(n) for n in (130, 116, 50, 64))
    return uint(total, U128, 'envelope cost')
