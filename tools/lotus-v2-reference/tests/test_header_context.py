import unittest
from dataclasses import replace
from lotus_v2_reference.header_context import HeaderChainProfile, parent_median_time, validate_child_header
from lotus_v2_reference.block_seal import Header, block_id
from lotus_v2_reference.asert import Parent, required_bits, compact_decode

class HeaderContextTest(unittest.TestCase):
    def setUp(self):
        self.p = HeaderChainProfile(bytes(32), 2, 1000, 0x207fffff, (1<<256)-1, 172800, 120)
        self.history = []
        for height in range(12):
            # Deliberate nonmonotone final timestamp, while retaining MTP eligibility.
            h = Header(block_id(self.p.chain_id, self.history[0]) if self.history else bytes(32),
                       self.p.genesis_bits, 1000+height*120 if height<11 else 5000,
                       0, 2, 200, height, bytes(32), bytes(32))
            history_target=compact_decode(h.bits,self.p.pow_limit)
            while int.from_bytes(block_id(self.p.chain_id,h),'little')>history_target:
                h=replace(h,nonce=h.nonce+1)
            self.history.insert(0,h)
        self.history = self.history[:11]
        parent=self.history[0]
        bits=required_bits(Parent(parent.time,parent.height),t0=1000,genesis_target=0x7fffff << 232,spacing=120,half_life=172800,pow_limit=self.p.pow_limit)
        self.child=Header(block_id(self.p.chain_id,parent),bits,2400,0,2,200,12,bytes(32),bytes(32))
        target = compact_decode(bits,self.p.pow_limit)
        while int.from_bytes(block_id(self.p.chain_id,self.child),'little')>target:
            self.child=replace(self.child,nonce=self.child.nonce+1)
    def validate(self, child=None, history=None):
        validate_child_header(self.p,self.history[0],self.history if history is None else history,self.child if child is None else child,expected_tx_root=bytes(32),expected_state_root=bytes(32),expected_size=200)
    def test_decreasing_time(self):
        self.assertLess(self.child.time,self.history[0].time)
        self.assertEqual(parent_median_time(self.p,self.history[0],self.history),1720)
        self.validate()
    def test_mutations(self):
        for mutation in [dict(time=1720),dict(height=13),dict(version=3),dict(bits=0x207fffff),dict(size=201),dict(tx_root=b'x'*32),dict(state_root=b'x'*32),dict(prev_id=bytes(32))]:
            with self.subTest(mutation=mutation), self.assertRaises(ValueError): self.validate(replace(self.child,**mutation))
        for history in [self.history[:10],self.history+[self.history[-1]],self.history[:1]+list(reversed(self.history[1:]))]:
            with self.assertRaises(ValueError): self.validate(history=history)
    def test_genesis_window(self):
        genesis=Header(bytes(32),self.p.genesis_bits,1000,0,2,200,0,bytes(32),bytes(32))
        self.assertEqual(parent_median_time(self.p,genesis,[genesis]),1000)
        with self.assertRaises(ValueError): parent_median_time(self.p,genesis,[])
