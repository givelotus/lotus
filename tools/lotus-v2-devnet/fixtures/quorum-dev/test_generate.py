"""Offline boundaries and reproducibility; no node subprocesses or sockets."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('quorum_generator', Path(__file__).with_name('generate.py'))
g=importlib.util.module_from_spec(spec); spec.loader.exec_module(g)

class CandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest, cls.report = g.construct()

    def test_independent_profile_and_initial_state(self):
        baseline=json.loads((g.HERE.parent/'local-test-manifest.json').read_text())
        m=self.manifest
        self.assertNotEqual(m['header']['chain_id'], baseline['header']['chain_id'])
        self.assertNotEqual(m['header']['genesis_id'], baseline['header']['genesis_id'])
        self.assertEqual(m['schema'],2)
        self.assertEqual(m['tail_formula_version'],1)
        self.assertEqual(m['monetary'][1:],baseline['monetary'][1:])
        state=bytes.fromhex(m['initial_monetary'])
        self.assertEqual(int.from_bytes(state[:8],'little'),1<<43)
        self.assertEqual(int.from_bytes(state[8:16],'little'),1_000_000)
        self.assertEqual(int.from_bytes(state[16:48],'little'),2)
        for bad_reserve in (-1,1<<64):
            with self.assertRaises(ValueError):
                g.initialize_genesis(g.Profile(*m['monetary'][:11],2),
                    bootstrap_reserve=bad_reserve,tail_subsidy=1_000_000,
                    genesis_work=2,ema_block_cost=65536)

    def test_actual_schedule_and_default_stake_bounds(self):
        r=self.report
        self.assertEqual(r['first_deduction'],242)
        self.assertGreaterEqual(min(r['first_nine_payouts']),g.STAKE_DUST)
        self.assertGreaterEqual(r['minimum_any_eight'],g.QUORUM)
        self.assertLess(2023-9,g.STAKE_CONFIRMATIONS-1)
        self.assertEqual(2024-9,g.STAKE_CONFIRMATIONS-1)
        self.assertEqual(r['schedule_seconds'],340)
        self.assertEqual(r['max_work'],5)
        self.assertEqual(r['reserve_at_maturity'],0)
        self.assertLess(sum(r['first_nine_payouts']),2_100_000_000_000_000)

    def test_generation_is_explicit_new_and_deterministic(self):
        with tempfile.TemporaryDirectory() as directory:
            a=Path(directory)/'a'; b=Path(directory)/'b'
            g.generate(a);g.generate(b)
            self.assertEqual((a/'manifest.json').read_bytes(),(b/'manifest.json').read_bytes())
            self.assertEqual((a/'report.json').read_bytes(),(b/'report.json').read_bytes())
            with self.assertRaises(FileExistsError):g.generate(a)
            self.assertEqual(set(p.name for p in a.iterdir()),{'manifest.json','report.json'})

if __name__=='__main__':unittest.main()
