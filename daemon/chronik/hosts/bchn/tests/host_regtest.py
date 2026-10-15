#!/usr/bin/env python3
"""Real in-process BCHN Chronik parity/lifecycle test with the upstream HTTP client."""
import hashlib
import importlib.util
from io import BytesIO
from pathlib import Path
import sys
import socket
import time

from test_framework.address import byte_to_base58
from test_framework.blocktools import create_block, create_coinbase
from test_framework.messages import CTransaction, CTxIn, CTxOut, COutPoint, TokenOutputData, deser_string
from test_framework.script import CScript, OP_TRUE, OP_DROP, OP_RETURN, hash160
from test_framework.test_framework import BitcoinTestFramework
from test_framework.test_node import ErrorMatch
from test_framework.util import assert_equal, assert_raises_rpc_error, p2p_port, wait_until


def txid_bytes(txid):
    return bytes.fromhex(txid)[::-1]


def wrapped(output):
    return deser_string(BytesIO(output.serialize()[8:]))


class BchnChronikTest(BitcoinTestFramework):
    def set_test_params(self):
        self.num_nodes = 1
        self.setup_clean_chain = True

    def add_options(self, parser):
        parser.add_argument("--chronik-export", type=Path, required=True,
                            help="Unmodified pinned Chronik source export containing the public client")
        parser.add_argument("--chronik-protobuf-dir", type=Path, required=True,
                            help="Directory containing chronik_pb2.py generated from the pinned schema")

    def setup_network(self):
        global ChronikClient
        sys.dont_write_bytecode = True
        sys.path.insert(0, str(self.options.chronik_protobuf_dir))
        client_path = self.options.chronik_export / "test/functional/test_framework/chronik/client.py"
        assert hashlib.sha256(client_path.read_bytes()).hexdigest() == "951340e2654af0c77e3eb90c028c77c46a27862c3fcc6d12113cc5f05b5dc63b"
        spec = importlib.util.spec_from_file_location("public_chronik_client", client_path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        ChronikClient = module.ChronikClient
        self.port = p2p_port(1)
        self.args = ['-chronik=1', '-chronikbind=127.0.0.1:' + str(self.port), '-chronikscripthashindex=1']
        self.add_nodes(1, [[]])
        self.start_nodes()
        self.nodes[0].generatetoaddress(101, byte_to_base58(hash160(CScript([OP_TRUE])), 196))
        self.restart_node(0, self.args)
        self.client = ChronikClient('127.0.0.1', self.port)

    def synced(self):
        wait_until(lambda: self.client.blockchain_info().ok().tip_height == self.nodes[0].getblockcount())
        assert_equal(self.client.blockchain_info().ok().tip_hash, txid_bytes(self.nodes[0].getbestblockhash()))

    def raw_parity(self, txid, raw):
        assert_equal(self.client.raw_tx(txid).ok().raw_tx, bytes.fromhex(raw))
        assert_equal(self.client.tx(txid).ok().txid, txid_bytes(txid))

    def run_test(self):
        node, client = self.nodes[0], self.client
        self.synced()
        genesis = node.getblockhash(0)
        assert_equal(client.block_header(0).ok().raw_header, bytes.fromhex(node.getblockheader(genesis, False)))
        redeem = CScript([OP_TRUE])
        destination = byte_to_base58(hash160(redeem), 196)
        hashes = [node.getblockhash(h) for h in range(1, 102)]
        self.synced()
        for height in [0, 1, 50, 101]:
            assert_equal(client.block_header(height).ok().raw_header, bytes.fromhex(
                node.getblockheader(node.getblockhash(height), False)))
        cb = node.getblock(hashes[0], 2)['tx'][0]
        amount = int(cb['vout'][0]['value'] * 100000000)
        parent = CTransaction()
        parent.vin = [CTxIn(COutPoint(int(cb['txid'], 16), 0), CScript([redeem]))]
        parent.vout = [CTxOut(amount - 2000, CScript([OP_TRUE]), TokenOutputData(id=int(cb['txid'],
                              16), amount=1)), CTxOut(1000, CScript([OP_TRUE, OP_DROP, OP_TRUE]))]
        parent_raw = parent.serialize().hex()
        ws = client.ws(timeout=10)
        ws.sub_to_txs()
        time.sleep(0.1)
        parent_id = node.sendrawtransaction(parent_raw)
        added = ws.recv().tx
        assert_equal(added.msg_type, 0)
        assert_equal(added.txid, txid_bytes(parent_id))
        wait_until(lambda: len(client.unconfirmed_txs().ok().txs) == 1)
        self.raw_parity(parent_id, parent_raw)
        indexed_parent = client.tx(parent_id).ok()
        assert_equal(indexed_parent.outputs[0].output_script, wrapped(parent.vout[0]))
        assert_equal(indexed_parent.inputs[0].sats, amount)
        assert_equal(indexed_parent.inputs[0].output_script, bytes.fromhex(cb["vout"][0]["scriptPubKey"]["hex"]))
        token_script = wrapped(parent.vout[0])
        token_script_client = client.script('scripthash', hashlib.sha256(token_script).digest()[::-1].hex())
        assert_equal([tx.txid for tx in token_script_client.history().ok().txs], [txid_bytes(parent_id)])
        # This is indexing of the complete wrapped script, not CashTokens semantics.
        full_script = bytes(parent.vout[1].scriptPubKey)
        script_client = client.script("scripthash", hashlib.sha256(full_script).digest()[::-1].hex())
        unspent = script_client.utxos().ok()
        assert_equal(unspent.script, full_script)
        assert_equal([utxo.sats for utxo in unspent.utxos], [1000])
        history = client.script('scripthash', hashlib.sha256(full_script).digest()[::-1].hex()).history().ok()
        assert_equal([tx.txid for tx in history.txs], [txid_bytes(parent_id)])
        child = CTransaction()
        child.vin = [CTxIn(COutPoint(int(parent_id, 16), 0), CScript())]
        child.vout = [CTxOut(amount - 3000, CScript([OP_TRUE]), TokenOutputData(id=int(cb['txid'],
                             16), amount=1)), CTxOut(0, CScript([OP_RETURN, bytes(60)]))]
        child_raw = child.serialize().hex()
        child_id = node.sendrawtransaction(child_raw)
        added = ws.recv().tx
        assert_equal(added.msg_type, 0)
        assert_equal(added.txid, txid_bytes(child_id))
        wait_until(lambda: len(client.unconfirmed_txs().ok().txs) == 2)
        self.raw_parity(child_id, child_raw)
        indexed_child = client.tx(child_id).ok()
        assert_equal(indexed_child.inputs[0].sats, parent.vout[0].nValue)
        assert_equal(indexed_child.inputs[0].output_script, wrapped(parent.vout[0]))
        assert_equal(client.tx(parent_id).ok().outputs[0].spent_by.txid, txid_bytes(child_id))
        assert_equal({tx.txid for tx in token_script_client.history().ok().txs},
                     {txid_bytes(parent_id), txid_bytes(child_id)})
        assert_equal([utxo.sats for utxo in token_script_client.utxos().ok().utxos], [child.vout[0].nValue])
        ws.sub_to_txs(is_unsub=True)
        ws.sub_txid(parent_id)
        ws.sub_txid(child_id)
        time.sleep(0.1)
        blockhash = node.generatetoaddress(1, destination)[0]
        self.synced()
        confirmed = [ws.recv().tx, ws.recv().tx]
        assert_equal({msg.txid for msg in confirmed}, {txid_bytes(parent_id), txid_bytes(child_id)})
        assert all(msg.msg_type == 2 for msg in confirmed)
        assert_equal(client.unconfirmed_txs().ok().txs, [])
        for txid, raw in [(parent_id, parent_raw), (child_id, child_raw)]:
            self.raw_parity(txid, raw)
            assert_equal(client.tx(txid).ok().block.height, 102)
        node.invalidateblock(blockhash)
        self.synced()
        wait_until(lambda: len(client.unconfirmed_txs().ok().txs) == 2)
        assert_equal([ws.recv().tx.msg_type, ws.recv().tx.msg_type], [0, 0])
        # A single global stream preserves removal order; separate txid streams
        # are multiplexed by the unchanged server without a cross-stream order.
        ws.sub_txid(parent_id, is_unsub=True)
        ws.sub_txid(child_id, is_unsub=True)
        ws.sub_to_txs()
        time.sleep(0.1)
        conflict = CTransaction()
        conflict.vin = parent.vin
        conflict.vout = [CTxOut(amount - 1000, CScript([OP_TRUE])), CTxOut(0, CScript([OP_RETURN, bytes(60)]))]
        conflict.rehash()
        coinbase = create_coinbase(102)
        coinbase.vout[0].nValue += 1000
        coinbase.rehash()
        block = create_block(int(node.getbestblockhash(), 16), coinbase,
                             node.getblockheader(node.getbestblockhash())["time"] + 1)
        block.vtx.append(conflict)
        block.hashMerkleRoot = block.calc_merkle_root()
        block.solve()
        assert_equal(node.submitblock(block.serialize().hex()), None)
        self.synced()
        assert_equal(client.unconfirmed_txs().ok().txs, [])
        client.tx(parent_id).err(404)
        client.tx(child_id).err(404)
        self.raw_parity(conflict.hash, conflict.serialize().hex())
        removals = [ws.recv().tx, ws.recv().tx]
        assert_equal([msg.msg_type for msg in removals], [1, 1])
        assert_equal([msg.txid for msg in removals], [txid_bytes(child_id), txid_bytes(parent_id)])
        ws.close()
        node.invalidateblock(block.hash)
        node.reconsiderblock(blockhash)
        self.synced()
        self.raw_parity(parent_id, parent_raw)
        self.raw_parity(child_id, child_raw)
        grandchild = CTransaction()
        grandchild.vin = [CTxIn(COutPoint(int(child_id, 16), 0), CScript())]
        grandchild.vout = [CTxOut(amount - 4000, CScript([OP_TRUE]), TokenOutputData(id=int(cb['txid'],
                                  16), amount=1)), CTxOut(0, CScript([OP_RETURN, bytes(60)]))]
        grandchild_raw = grandchild.serialize().hex()
        broadcast = client.broadcast_tx(bytes.fromhex(grandchild_raw), skip_token_checks=True).ok()
        grandchild_id = broadcast.txid[::-1].hex()
        assert grandchild_id in node.getrawmempool()
        missing = CTransaction(grandchild)
        missing.vin[0].prevout = COutPoint(12345, 0)
        assert "Missing inputs" in client.broadcast_tx(missing.serialize(), skip_token_checks=True).err(400).msg
        wait_until(lambda: len(client.unconfirmed_txs().ok().txs) == 1)
        self.restart_node(0, self.args)
        self.synced()
        self.raw_parity(parent_id, parent_raw)
        self.raw_parity(child_id, child_raw)
        assert_equal(client.tx(child_id).ok().inputs[0].output_script, wrapped(parent.vout[0]))
        assert_equal(node.getrawtransaction(child_id, False, blockhash), child_raw)
        wait_until(lambda: len(client.unconfirmed_txs().ok().txs) == 1)
        self.raw_parity(grandchild_id, grandchild_raw)
        assert_equal(client.tx(grandchild_id).ok().inputs[0].output_script, wrapped(child.vout[0]))
        node.invalidateblock(blockhash)
        self.synced()
        wait_until(lambda: len(client.unconfirmed_txs().ok().txs) == 3)
        self.raw_parity(grandchild_id, grandchild_raw)
        node.reconsiderblock(blockhash)
        self.synced()
        wait_until(lambda: len(client.unconfirmed_txs().ok().txs) == 1)
        self.stop_node(0)
        node.assert_start_raises_init_error(
            self.args + ['-chroniktokenindex=1'], 'Error: CashTokens-aware Chronik indexing is not implemented; raw token bytes are preserved')
        node.assert_start_raises_init_error(self.args + ['-chronikbind=invalid'],
                                            'Invalid Chronik host address', match=ErrorMatch.PARTIAL_REGEX)
        with socket.socket() as occupied:
            occupied.bind(('127.0.0.1', p2p_port(2)))
            occupied.listen()
            node.assert_start_raises_init_error(self.args + ['-chronikbind=127.0.0.1:' + str(p2p_port(2))],
                                                'Chronik failed binding', match=ErrorMatch.PARTIAL_REGEX)
        self.start_node(0, self.args)
        self.synced()
        self.raw_parity(grandchild_id, grandchild_raw)
        # Exercise a real non-block batch removal with a dependent three-tx chain.
        node.invalidateblock(blockhash)
        self.synced()
        wait_until(lambda: len(client.unconfirmed_txs().ok().txs) == 3)
        cb2 = node.getblock(node.getblockhash(2), 2)['tx'][0]
        expiry_trigger = CTransaction()
        expiry_trigger.vin = [CTxIn(COutPoint(int(cb2['txid'], 16), 0), CScript([redeem]))]
        expiry_trigger.vout = [CTxOut(int(cb2['vout'][0]['value'] * 100000000) - 1000,
                                      CScript([OP_TRUE])), CTxOut(0, CScript([OP_RETURN, bytes(60)]))]
        node.setmocktime(node.getblockheader(node.getbestblockhash())['time'] + 3600 * 337)
        rejected = CTransaction()
        rejected.vin = [CTxIn(COutPoint(int(grandchild_id, 16), 0), CScript())]
        rejected.vout = [CTxOut(amount - 5000, CScript([OP_TRUE]), grandchild.vout[0].tokenData),
                         CTxOut(0, CScript([OP_RETURN, bytes(60)]))]
        rejected.rehash()
        # Native expiry removes this tentative child with its old ancestors,
        # before native admission succeeds; the indexer never observed it.
        assert_raises_rpc_error(-26, "mempool full", node.sendrawtransaction, rejected.serialize().hex())
        wait_until(lambda: len(client.unconfirmed_txs().ok().txs) == 0)
        client.tx(rejected.hash).err(404)
        trigger_raw = expiry_trigger.serialize().hex()
        trigger_id = node.sendrawtransaction(trigger_raw)
        wait_until(lambda: len(client.unconfirmed_txs().ok().txs) == 1)
        self.raw_parity(trigger_id, trigger_raw)
        for txid in (parent_id, child_id, grandchild_id):
            client.tx(txid).err(404)
        node.setmocktime(0)
        assert_equal(node.verifychain(4, 0), True)
        self.log.info('PASS bootstrap/headers/raw/CashTokens opaque scripts/full-script history/spent coins/mempool/conflicts/reorg/expiry/WS/restart; token-aware mode rejected')


if __name__ == '__main__':
    BchnChronikTest().main()
