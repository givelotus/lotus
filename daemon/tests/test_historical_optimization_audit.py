"""Mechanical audit must distinguish source evidence from proof of loss."""
import importlib.util
import csv
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


spec = importlib.util.spec_from_file_location(
    'historical_audit', Path(__file__).parents[1] / 'scripts/audit-historical-optimizations.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)

PATCH = '''From: Example <example@example.com>
diff --git a/src/example.cpp b/src/example.cpp
--- a/src/example.cpp
+++ b/src/example.cpp
@@ -1,3 +1,3 @@ function
 context
-old_function();
+new_function();
 end
-- 
2.50.0
'''


class HistoricalAuditTests(unittest.TestCase):
    def result(self, source):
        file = audit.parse_patch(PATCH)[0]
        return audit.audit_hunk(file, file['hunks'][0], source)

    def test_mail_trailer_is_not_a_deleted_line(self):
        file = audit.parse_patch(PATCH)[0]
        self.assertEqual(len(file['hunks'][0]['lines']), 4)
        self.assertEqual(len(file['hunks']), 1)

    def test_postimage_and_surviving_old_text_are_distinct(self):
        new = self.result('context\nnew_function();\nend\n')
        old = self.result('context\nold_function();\nend\n')
        self.assertEqual(new['status'], 'exact_postimage_region')
        self.assertEqual(old['status'], 'preimage_region_survives_review')

    def test_refactored_context_is_not_declared_lost(self):
        result = self.result('different context\nnew_function();\nother end\n')
        self.assertEqual(result['status'], 'changed_blocks_present_context_diverged')

    def test_changed_implementation_requires_review(self):
        self.assertEqual(self.result('equivalent_but_renamed();\n')['status'], 'unresolved_review')
        self.assertEqual(self.result(None)['status'], 'path_missing_review')

    def test_whitespace_is_only_a_hint(self):
        self.assertEqual(self.result('new_function ( );\n')['status'],
                         'whitespace_insensitive_blocks_review')

    def test_deletion_not_vacuously_an_added_match(self):
        text = '''diff --git a/a.cpp b/a.cpp
deleted file mode 100644
--- a/a.cpp
+++ /dev/null
@@ -1 +0,0 @@
-old_function();
'''
        file = audit.parse_patch(text)[0]
        result = audit.audit_hunk(file, file['hunks'][0], None)
        self.assertEqual(result['status'], 'deleted_path_absent')

    def test_hunk_counts_fail_closed(self):
        with self.assertRaises(ValueError):
            audit.parse_patch(PATCH.replace('@@ -1,3 +1,3', '@@ -1,8 +1,8'))

    def test_end_to_end_pins_commit_and_preserves_dirty_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / 'source'
            repo.mkdir()
            def git(*args):
                return subprocess.check_output(['git', '-C', str(repo), *args], stderr=subprocess.DEVNULL)
            git('init')
            file = repo / 'src/example.cpp'
            file.parent.mkdir()
            file.write_text('context\nnew_function();\nend\n')
            git('add', '.')
            git('-c', 'user.name=Audit Test', '-c', 'user.email=audit@example.com', 'commit', '-m', 'fixture')
            file.write_text('uncommitted replacement\n')
            before = git('status', '--porcelain')
            index = git('write-tree')
            patch = root / 'example.patch'
            patch.write_text(PATCH)
            inventory = root / 'inventory.csv'
            with inventory.open('w') as stream:
                writer = csv.DictWriter(stream, fieldnames=['set', 'layer', 'patch', 'path', 'sha256'])
                writer.writeheader()
                writer.writerow(dict(set='fixture', layer='v2', patch=patch.name,
                                     path=str(patch), sha256=audit.sha(patch.read_bytes())))
            output = root / 'output'
            subprocess.run([sys.executable, str(Path(audit.__file__)), '--source', str(repo),
                            '--inventory', str(inventory), '--output', str(output)],
                           check=True, stdout=subprocess.DEVNULL)
            with (output / 'patches.csv').open() as stream:
                row = next(csv.DictReader(stream))
            self.assertEqual(row['classification'], 'reverse_apply_check_pass')
            self.assertEqual(file.read_text(), 'uncommitted replacement\n')
            self.assertEqual(before, git('status', '--porcelain'))
            self.assertEqual(index, git('write-tree'))


if __name__ == '__main__':
    unittest.main()
