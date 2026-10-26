#!/usr/bin/env python3
"""Focused JUnit classification checks; never launch child processes or nodes."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('primary_supervisor', Path(__file__).with_name('run-primary-batches.py'))
supervisor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(supervisor)


class ResultsTest(unittest.TestCase):
    def parse(self, child='', expected=None, code=0):
        with tempfile.TemporaryDirectory(prefix='v2-supervisor-junit-') as directory:
            path = Path(directory) / 'results.xml'
            path.write_text('<testsuite><testcase name="case.py" time="1.25">' + child + '</testcase></testsuite>')
            return supervisor.read_results(path, ['case.py'] if expected is None else expected, code)

    def test_pass(self):
        cases, reason = self.parse()
        self.assertIsNone(reason)
        self.assertEqual(cases, [{'id': 'case.py', 'seconds': 1.25, 'junit_kind': 'passed', 'status': 'passed'}])

    def test_failure(self):
        cases, reason = self.parse('<failure message="assertion"/>')
        self.assertEqual(cases[0]['status'], 'failed')
        self.assertEqual(cases[0]['junit_kind'], 'failure')
        self.assertEqual(reason, 'substantive_failure_or_skip')

    def test_error_even_with_zero_exit(self):
        cases, reason = self.parse('<error message="exception"/>')
        self.assertEqual(cases[0]['status'], 'failed')
        self.assertEqual(cases[0]['junit_kind'], 'error')
        self.assertEqual(reason, 'substantive_failure_or_skip')

    def test_skip_remains_distinct(self):
        cases, reason = self.parse('<skipped/>')
        self.assertEqual(cases[0]['status'], 'not_run_or_skip_requires_review')
        self.assertEqual(cases[0]['junit_kind'], 'skipped')
        self.assertEqual(reason, 'substantive_failure_or_skip')

    def test_nonzero_exit_rejects_all_pass(self):
        cases, reason = self.parse(code=1)
        self.assertEqual(cases[0]['status'], 'passed')
        self.assertEqual(reason, 'runner_nonzero_exit')

    def test_identity_mismatch(self):
        with self.assertRaisesRegex(RuntimeError, 'junit_identity_mismatch'):
            self.parse(expected=['other.py'])


if __name__ == '__main__':
    unittest.main()
