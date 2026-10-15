"""Dependent ordinary payments, block cost rollback, and undo."""

import unittest

from lotus_v2_reference.block import (
    OP_TRUE_COST, Coin, Parent, Payment, connect_ordinary_block, disconnect,
    encode_native_output, encode_spend_core, load_snapshot, state_root,
    transaction_id, utxo_root, write_snapshot, branch_leaf,
)
from lotus_v2_reference.monetary import MonetaryState, Profile

CHAIN = bytes(range(32))
BRANCH = branch_leaf(b"\x4e")
MONEY = MonetaryState(9, 200, 9, 4)
MONETARY = Profile(2, 3, 2, 4, 3, 5, 2, 2000, 3, 1000, 200, 9)


def _coin(tag: int, index: int, value: int) -> Coin:
    return Coin(bytes([tag]) + bytes(31), index, value, BRANCH, 90, 49000)


def _world():
    coins = {}
    for coin in (_coin(0x71, 3, 20000), _coin(0x72, 1, 8000)):
        coins[coin.key()] = coin
    root = utxo_root(coins)
    parent = Parent(CHAIN, 99, 50000, state_root(CHAIN, 99, root, MONEY), MONEY)
    return coins, parent, root


def _chain(parent: Parent):
    first = Payment(bytes([0x71]) + bytes(31), 3, 15000)
    core = encode_spend_core(first.spent_tx, first.spent_index)
    output = encode_native_output(first.value, BRANCH)
    txid1 = transaction_id(parent.chain_id, core, output)
    second = Payment(txid1, 0, 10000)
    txid2 = transaction_id(
        parent.chain_id, encode_spend_core(txid1, 0), encode_native_output(10000, BRANCH)
    )
    third = Payment(txid2, 0, 5000)
    return first, second, third, txid1, txid2, core, output


def reference_report() -> dict[str, str]:
    coins, parent, parent_root = _world()
    first, second, third, txid1, txid2, core, output = _chain(parent)
    cap = OP_TRUE_COST * 2
    connected = connect_ordinary_block(
        (first, second), parent, coins, MONEY, MONETARY,
        candidate_height=100, parent_mtp=50000, block_cap=cap,
    )
    image = write_snapshot(coins, connected.transition.state)
    restored = disconnect(connected.undo, coins)
    reloaded, reloaded_money = load_snapshot(image)
    over_coins, over_parent, over_root = _world()
    over_first, over_second, over_third, _, _, _, _ = _chain(over_parent)
    over_error = ""
    try:
        connect_ordinary_block(
            (over_first, over_second, over_third), over_parent, over_coins, MONEY,
            MONETARY, candidate_height=100, parent_mtp=50000, block_cap=cap,
        )
    except ValueError as exc:
        over_error = str(exc)
    coin_coins, coin_parent, _ = _world()
    try:
        connect_ordinary_block(
            (Payment(bytes(32), 0, 1, "coinbase"),), coin_parent, coin_coins, MONEY,
            MONETARY, candidate_height=100, parent_mtp=50000, block_cap=cap,
        )
        coinbase = ""
    except ValueError as exc:
        coinbase = str(exc)
    mint_coins, mint_parent, _ = _world()
    try:
        connect_ordinary_block(
            (Payment(bytes([0x71]) + bytes(31), 3, 15000, "mint"),), mint_parent,
            mint_coins, MONEY, MONETARY, candidate_height=100, parent_mtp=50000,
            block_cap=cap,
        )
        mint = ""
    except ValueError as exc:
        mint = str(exc)
    bad_coins, bad_parent, bad_root = _world()
    bad_first, _, _, _, _, _, _ = _chain(bad_parent)
    try:
        connect_ordinary_block(
            (bad_first, Payment(bytes([0x99]) + bytes(31), 9, 1000)), bad_parent,
            bad_coins, MONEY, MONETARY, candidate_height=100, parent_mtp=50000,
            block_cap=cap,
        )
        bad = ""
    except ValueError as exc:
        bad = str(exc)
    transition = connected.transition
    return {
        "invocation_cost": str(connected.invocation_cost),
        "total_fees": str(transition.total_fees),
        "token_burn": str(transition.token_burn),
        "burned_fees": str(transition.burned_fees),
        "required_underclaim": str(transition.required_underclaim),
        "actual_underclaim": str(transition.actual_underclaim),
        "spendable_supply_delta": str(transition.spendable_supply_delta),
        "subsidy": str(transition.subsidy),
        "bootstrap_issued": str(transition.bootstrap_issued),
        "reserve": str(transition.state.bootstrap_reserve),
        "tail": str(transition.state.tail_subsidy),
        "ema": str(transition.state.ema_block_cost),
        "work": str(transition.state.prev_work),
        "parent_utxo": parent_root.hex(),
        "parent_state": parent.state_root.hex(),
        "parent_monetary": MONEY.to_bytes().hex(),
        "connected_utxo": connected.utxo_root.hex(),
        "connected_state": connected.state_root.hex(),
        "connected_monetary": connected.monetary_bytes.hex(),
        "undo_utxo": utxo_root(coins).hex(),
        "undo_state": state_root(CHAIN, 99, utxo_root(coins), restored).hex(),
        "undo_monetary": restored.to_bytes().hex(),
        "snapshot_utxo": utxo_root(reloaded).hex(),
        "snapshot_state": state_root(CHAIN, 100, utxo_root(reloaded), reloaded_money).hex(),
        "over_cap": over_error,
        "over_cap_utxo": utxo_root(over_coins).hex(),
        "over_cap_monetary": MONEY.to_bytes().hex(),
        "coinbase": coinbase,
        "mint": mint,
        "bad_second": bad,
        "bad_second_utxo": utxo_root(bad_coins).hex(),
        "txid1": txid1.hex(),
        "txid2": txid2.hex(),
        "tx1_core": core.hex(),
        "tx1_output": output.hex(),
        "over_root_unchanged": str(utxo_root(over_coins) == over_root),
        "bad_root_unchanged": str(utxo_root(bad_coins) == bad_root),
    }


class OrdinaryBlockTests(unittest.TestCase):
    def test_two_payments_undo_snapshot_and_over_cap(self):
        report = reference_report()
        self.assertEqual(OP_TRUE_COST, 18)
        self.assertEqual(report["invocation_cost"], "36")
        self.assertEqual(report["total_fees"], "10000")
        self.assertEqual(report["token_burn"], "0")
        self.assertEqual(report["burned_fees"], "5000")
        self.assertEqual(report["required_underclaim"], "138")
        self.assertEqual(report["actual_underclaim"], "5202")
        self.assertEqual(report["spendable_supply_delta"], "-10000")
        self.assertEqual(report["subsidy"], "202")
        self.assertEqual(report["bootstrap_issued"], "2")
        self.assertEqual(report["reserve"], "7")
        self.assertEqual(report["tail"], "200")
        self.assertEqual(report["ema"], "12")
        self.assertEqual(report["work"], "9")
        self.assertEqual(report["undo_utxo"], report["parent_utxo"])
        self.assertEqual(report["undo_state"], report["parent_state"])
        self.assertEqual(report["undo_monetary"], report["parent_monetary"])
        self.assertEqual(report["snapshot_utxo"], report["connected_utxo"])
        self.assertEqual(report["snapshot_state"], report["connected_state"])
        self.assertNotEqual(report["connected_utxo"], report["parent_utxo"])
        self.assertEqual(report["over_cap"], "block invocation cost over cap")
        self.assertEqual(report["over_cap_utxo"], report["parent_utxo"])
        self.assertEqual(report["over_cap_monetary"], report["parent_monetary"])
        self.assertEqual(report["coinbase"], "coinbase is not an ordinary transaction")
        self.assertEqual(report["mint"], "mint without matching positive token delta")
        self.assertEqual(report["bad_second"], "unresolved spend")
        self.assertEqual(report["bad_second_utxo"], report["parent_utxo"])
        self.assertEqual(report["over_root_unchanged"], "True")
        self.assertEqual(report["bad_root_unchanged"], "True")
        self.assertEqual(len(report["txid1"]), 64)
        self.assertNotEqual(report["txid1"], report["txid2"])

    def test_second_payment_is_unspendable_before_the_first(self):
        coins, parent, root = _world()
        _, second, _, _, _, _, _ = _chain(parent)
        with self.assertRaises(ValueError) as caught:
            connect_ordinary_block(
                (second,), parent, coins, MONEY, MONETARY,
                candidate_height=100, parent_mtp=50000, block_cap=OP_TRUE_COST * 2,
            )
        self.assertEqual(str(caught.exception), "unresolved spend")
        self.assertEqual(utxo_root(coins), root)


if __name__ == "__main__":
    unittest.main()
