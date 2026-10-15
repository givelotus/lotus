import unittest
from dataclasses import replace
from lotus_v2_reference.block import (Parent, Coin, OP_TRUE, OUTPUT_PROFILE,
    connect_complete_block, encode_native_output, state_root, utxo_root, branch_leaf)
from lotus_v2_reference.block_cost import (BlockCostProfile, authenticated_transaction_costs,
    authenticated_envelope_cost)
from lotus_v2_reference.block_wire import (complete_transaction_root, encode_block_wire,
    decode_block_wire)
from lotus_v2_reference.block_seal import Header, block_id, serialize_header
from lotus_v2_reference.signing import Input, Witness, Transaction, encode_transaction
from lotus_v2_reference.encoding import Output, encode_compact_size
from lotus_v2_reference.block import PAYMENT_TX_PROFILE as TX
from lotus_v2_reference.dev_genesis import make_development_genesis, DEVELOPMENT_GENESIS
from lotus_v2_reference.header_context import HeaderChainProfile
from lotus_v2_reference.monetary import advance, block_cost

COST = BlockCostProfile(1, 1, 1, 1)  # explicit unit schedule, not launch values
CHAIN = bytes(32)

def cb(parent=bytes(32), height=1, *, burn=True, data=None):
    output = Output(2 if burn else 0, 0, None, (bytes(32),), () if burn else ((0,),))
    return Transaction(0, (Input(parent,height,0xffffffff,2,0,(),data),), (output,))

def ordinary(*, arguments=(), outputs=()):
    return Transaction(0, (Input(bytes([7])*32,0,0xffffffff,1,0,
                       (Witness(OP_TRUE,(),arguments),)),), outputs)

def framed(txs, **kwargs):
    size = 138 + sum(len(encode_transaction(tx, TX)) +
        len(encode_compact_size(len(encode_transaction(tx, TX)))) for tx in txs)
    root = complete_transaction_root(txs, TX, CHAIN)
    header = Header(bytes(32),0x1d00ffff,1,0,2,size,1,root,bytes(32))
    return encode_block_wire(replace(header, **kwargs), txs, TX)

class BlockWireTests(unittest.TestCase):
    def test_canonical_roundtrip_and_exact_charge(self):
        tx = cb()
        wire = framed((tx,))
        block = decode_block_wire(wire, TX, CHAIN)
        self.assertEqual(block.transactions, (tx,))
        self.assertEqual(block.frame_prefix_bytes, (1,))
        self.assertEqual(len(wire), 240)
        charges = authenticated_transaction_costs(tx, TX, {}, 1, 0, 0, COST)
        envelope = authenticated_envelope_cost(1, 1, COST)
        self.assertEqual(charges.account_linear, charges.enforce_linear)
        self.assertEqual(charges.account_linear, 1570)
        self.assertEqual(envelope, 993)
        self.assertEqual(block_cost(envelope, (1570,), DEVELOPMENT_GENESIS),310675)

    def test_empty_missing_misplaced_and_duplicate_ids(self):
        for txs in ((), (ordinary(),), (ordinary(), cb()), (cb(), cb())):
            with self.assertRaises(ValueError):
                complete_transaction_root(txs, TX, CHAIN)
        # Same TxID despite different arguments, no output insertion to catch it.
        a, b = ordinary(), ordinary(arguments=(b'x',))
        with self.assertRaisesRegex(ValueError, 'duplicate transaction id'):
            complete_transaction_root((cb(), a, b), TX, CHAIN)
        burned = Output(2, 0, None, (bytes(32),), ())
        with self.assertRaisesRegex(ValueError, 'duplicate transaction id'):
            complete_transaction_root((cb(), ordinary(outputs=(burned,)),
                ordinary(arguments=(b'x',), outputs=(burned,))), TX, CHAIN)

    def test_frame_mutations(self):
        wire = framed((cb(),))
        block = decode_block_wire(wire, TX, CHAIN)
        candidates = [wire[:-1], wire+b'x']
        # Keep supplied size consistent to exercise exact consumption separately.
        candidates.append(serialize_header(replace(block.header,size=len(wire)+1))+wire[134:]+b'x')
        candidates.append(serialize_header(replace(block.header,size=len(wire)+2))+wire[134:138]+b'\xfd\x65\x00'+wire[139:])
        for count in (0, 2, 0xffffffff):
            candidates.append(wire[:134]+count.to_bytes(4,'little')+wire[138:])
        candidates.append(wire[:139]+b'\x08'+wire[140:])  # tx version
        candidates.append(framed((cb(),), tx_root=bytes(32)))
        for bad in candidates:
            with self.assertRaises(ValueError):
                decode_block_wire(bad, TX, CHAIN)
        for cut in range(len(wire)):
            with self.assertRaises(ValueError):
                decode_block_wire(wire[:cut], TX, CHAIN)

    def test_cost_includes_coinbase_data_state_and_proof(self):
        bare, data, created = cb(), cb(data=b'x'*253), cb(burn=False)
        charge = lambda tx: authenticated_transaction_costs(tx, TX, {}, 1, 0, 0, COST).account_linear
        self.assertGreater(charge(data), charge(bare)+253)
        self.assertGreater(charge(created), charge(bare)+256)
        huge = BlockCostProfile((1<<64)-1, 1, 1, 1)
        with self.assertRaisesRegex(ValueError, 'linear cost'):
            authenticated_transaction_costs(bare, TX, {}, 1, 0, 0, huge)

    def test_existing_genesis_cannot_fund_first_complete_block(self):
        # Minimum burn coinbase is 101 bytes; K = 101+134+4+1 =240 >202.
        from lotus_v2_reference.dev_genesis import initial_test_state, HEADER_BITS
        state = initial_test_state()
        tx = cb()
        self.assertEqual(len(encode_transaction(tx,TX)),101)
        self.assertEqual((state.bootstrap_reserve>>DEVELOPMENT_GENESIS.boot_shift)+state.tail_subsidy,202)
        with self.assertRaisesRegex(ValueError, 'insufficient .*entitlement'):
            advance(DEVELOPMENT_GENESIS,state,work=state.prev_work,transactions=(),
                coinbase_native_outputs=0,coinbase_native_burn=0,coinbase_bytes=101,
                tx_frame_prefix_bytes=1,account_block_cost=0,enforce_block_cost=0)
        # Existing genesis also uses toy prev_work9, not target-derived work.
        from lotus_v2_reference.asert import compact_decode
        self.assertEqual((1<<256)//(compact_decode(HEADER_BITS,(1<<256)-1)+1),4295032833)
        self.assertEqual(state.prev_work,9)

    def test_synthetic_funded_parent_complete_acceptance_and_atomic_mutations(self):
        # Module fixture only: this funding is not attributed to genesis issuance.
        from lotus_v2_reference.block import _complete_ordinary, PAYMENT_VM
        from lotus_v2_reference.monetary import MonetaryState
        from lotus_v2_reference.signing import identity_digests
        money = MonetaryState(9, 200, 2, 4)
        funding = Coin(bytes([7])+bytes(31),0,10**18,branch_leaf(OP_TRUE),0,1000)
        coins = {funding.key():funding}
        genesis = Header(bytes(32),0x207fffff,1000,0,2,134,0,bytes(32),bytes(32))
        parent_header = replace(genesis, height=1,time=1120,prev_id=block_id(CHAIN,genesis),
            state_root=state_root(CHAIN,1,utxo_root(coins),money))
        parent = Parent(CHAIN,1,1120,parent_header.state_root,money,parent_header)
        hp = HeaderChainProfile(CHAIN,2,1000,0x207fffff,(1<<256)-1,172800,120)
        coinbase = cb(block_id(CHAIN,parent_header),2)
        output = Output(0,1000,None,(funding.branch,),((0,),))
        spend = Transaction(0,(Input(funding.tx_id,0,0xffffffff,1,0,(Witness(OP_TRUE,(),()),)),),(output,))
        record, vm, spent = _complete_ordinary(spend,parent,coins,DEVELOPMENT_GENESIS,
            height=2,mtp=1120,maturity=2,vm_profile=PAYMENT_VM,tx_profile=TX,block_cap=1000000)
        self.assertEqual(vm,18)
        c = authenticated_transaction_costs(coinbase,TX,coins,2,1120,0,COST)
        s = authenticated_transaction_costs(spend,TX,coins,2,1120,vm,COST)
        self.assertEqual((c.account_linear,s.account_linear),(1570,70742))
        cost = block_cost(authenticated_envelope_cost(2,2,COST),(1570,70742),DEVELOPMENT_GENESIS)
        self.assertEqual(cost,625935502)
        trans = advance(DEVELOPMENT_GENESIS,money,work=2,transactions=(record,),
            coinbase_native_outputs=0,coinbase_native_burn=0,coinbase_bytes=101,
            tx_frame_prefix_bytes=2,account_block_cost=cost,enforce_block_cost=cost)
        txid = identity_digests(spend,TX,CHAIN).txid
        created = Coin(txid,0,1000,funding.branch,2,1120,False,output)
        root = utxo_root({created.key():created})
        header = Header(block_id(CHAIN,parent_header),0x207fffff,1121,0,2,0,2,
            complete_transaction_root((coinbase,spend),TX,CHAIN),state_root(CHAIN,2,root,trans.state))
        size = 138 + sum(len(encode_transaction(t,TX))+1 for t in (coinbase,spend))
        header = replace(header,size=size)
        while int.from_bytes(block_id(CHAIN,header),'little') > 0x7fffff << (8*29):
            header = replace(header,nonce=header.nonce+1)
        wire = encode_block_wire(header,(coinbase,spend),TX)
        before = dict(coins)
        bad_pow = header
        while int.from_bytes(block_id(CHAIN,bad_pow),'little') <= 0x7fffff << (8*29):
            bad_pow=replace(bad_pow,nonce=bad_pow.nonce+1)
        bad_wire=bytearray(encode_block_wire(bad_pow,(coinbase,spend),TX))
        bad_wire[139]=8
        with self.assertRaisesRegex(ValueError,'proof of work'):
            connect_complete_block(bytes(bad_wire),parent,[parent_header,genesis],hp,
                coins,money,DEVELOPMENT_GENESIS,COST,block_cap=1000000)
        self.assertEqual(coins,before)
        def reject(h,txs=(coinbase,spend)):
            h = replace(h,tx_root=complete_transaction_root(txs,TX,CHAIN))
            while int.from_bytes(block_id(CHAIN,h),'little') > (h.bits & 0x7fffff) << (8*((h.bits>>24)-3)):
                h=replace(h,nonce=h.nonce+1)
            mutated = encode_block_wire(h,txs,TX)
            with self.assertRaises(ValueError):
                connect_complete_block(mutated,parent,[parent_header,genesis],hp,
                    coins,money,DEVELOPMENT_GENESIS,COST,block_cap=1000000)
            self.assertEqual(coins,before)
        reject(replace(header,state_root=bytes(32)))
        reject(replace(header,prev_id=bytes(32)))
        reject(replace(header,bits=0x207ffffe))
        reject(replace(header,version=3))
        bad_cb=replace(coinbase,inputs=(replace(coinbase.inputs[0],prev_index=3),))
        reject(header,(bad_cb,spend))
        result = connect_complete_block(wire,parent,[parent_header,genesis],hp,
            coins,money,DEVELOPMENT_GENESIS,COST,block_cap=1000000)
        self.assertEqual(result.state_root,header.state_root)
        self.assertEqual(result.monetary_bytes,trans.state.to_bytes())
        from lotus_v2_reference.block import disconnect
        self.assertEqual(disconnect(result.undo,coins),money)
        self.assertEqual(coins,before)
