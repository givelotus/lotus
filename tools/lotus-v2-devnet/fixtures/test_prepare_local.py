"""Offline setup regressions: python3 -m unittest discover -s this directory."""
import hashlib
import json
import importlib.util
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

spec = importlib.util.spec_from_file_location('prepare_local', Path(__file__).resolve().parents[1] / 'prepare-local.py')
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)


class PrepareTests(unittest.TestCase):
    def test_versioned_fixture_and_preserved_legacy(self):
        fixtures = Path(__file__).resolve().parent
        raw = (fixtures / 'local-test-manifest.json').read_bytes()
        current = json.loads(raw)
        old_raw = (fixtures / 'legacy-schema1-local-test-manifest.json').read_bytes()
        old = json.loads(old_raw)
        provenance = json.loads((fixtures / 'provenance.json').read_text())
        self.assertEqual(hashlib.sha256(raw).hexdigest(), setup.MANIFEST_SHA256)
        self.assertEqual(hashlib.sha256(old_raw).hexdigest(), provenance['legacy_manifest_sha256'])
        self.assertEqual(current['schema'], 2)
        self.assertEqual(current['tail_formula_version'], 1)
        self.assertEqual(current['monetary'][:10], old['monetary'])
        self.assertEqual(current['monetary'][10:], [1000000, '02' + '00' * 31])
        self.assertEqual(current['header']['chain_id'], provenance['chain_id'])
        self.assertEqual(current['header']['genesis_id'], provenance['genesis_id'])
        for key in old:
            if key not in ('schema', 'header', 'monetary', 'genesis'):
                self.assertEqual(current[key], old[key], key)
        for key in old['header']:
            if key not in ('chain_id', 'genesis_id'):
                self.assertEqual(current['header'][key], old['header'][key], key)
        self.assertNotEqual(current['header']['chain_id'], old['header']['chain_id'])
        self.assertNotEqual(current['header']['genesis_id'], old['header']['genesis_id'])
        state = bytes.fromhex(current['initial_monetary'])
        self.assertEqual(int.from_bytes(state[8:16], 'little'), current['monetary'][10])
        self.assertEqual(state[16:48].hex(), current['monetary'][11])

    def test_fresh_and_alias_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            executable = base / 'tool'
            executable.write_text('#!/bin/sh\nexit 99\n')
            executable.chmod(0o700)
            compiler = base / 'compiler'
            for name in ('dist/generic.js', 'examples/gallery/payment.lotus'):
                path = compiler / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('fixture')
            args = dict(daemon=str(executable), wallet_client=str(executable),
                        node=str(executable), compiler=str(compiler))
            (base / 'a').mkdir()
            (base / 'alias').symlink_to(base / 'a', target_is_directory=True)
            # Equal paths and ancestors through both '..' and symlink parents.
            for output, session in (
                ('a/../fresh', 'fresh'), ('alias/../fresh', 'fresh'),
                ('alias/fresh', 'a/fresh'), ('a/../fresh', 'fresh/session'),
                ('fresh/session', 'a/../fresh'),
            ):
                with self.subTest(output=output, session=session):
                    with self.assertRaises(ValueError):
                        setup.prepare(SimpleNamespace(**args, output=str(base / output), session=str(base / session)))
                    self.assertFalse((base / 'fresh').exists())
                    self.assertFalse((base / 'a/fresh').exists())
            (base / 'leaf').symlink_to(base / 'absent')
            with self.assertRaises(ValueError):
                setup.prepare(SimpleNamespace(**args, output=str(base / 'leaf'), session=str(base / 'session')))
            result = setup.prepare(SimpleNamespace(**args, output=str(base / 'inputs'), session=str(base / 'session')))
            self.assertFalse(result['session_created'])
            self.assertFalse((base / 'session').exists())
            self.assertTrue((base / 'inputs/config.json').is_file())
            with self.assertRaises(ValueError):
                setup.prepare(SimpleNamespace(**args, output=str(base / 'inputs'), session=str(base / 'session')))


if __name__ == '__main__':
    unittest.main()
