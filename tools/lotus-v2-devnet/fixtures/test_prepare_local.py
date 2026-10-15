"""Offline setup regressions: python3 -m unittest discover -s this directory."""
import importlib.util
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

spec = importlib.util.spec_from_file_location('prepare_local', Path(__file__).resolve().parents[1] / 'prepare-local.py')
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)


class PrepareTests(unittest.TestCase):
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
