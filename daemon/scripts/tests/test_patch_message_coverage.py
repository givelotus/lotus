"""Patch message coverage must survive subsequent imports and refreshes."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location('patch_message_audit', ROOT / 'daemon/scripts/check-patch-metadata.py')
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


class MessageCoverage(unittest.TestCase):
    def test_all_tracked_patches_have_rationale_or_explicit_placeholder(self):
        counts = AUDIT.audit(ROOT)
        self.assertGreaterEqual(counts['mail'], 183)
        self.assertEqual(counts['placeholder'], 6)

    def test_missing_rationale_rejected(self):
        data = (ROOT / 'daemon/patches/ecash/01-nlogn-block-construction.patch').read_bytes()
        headers = data.split(b'\n\n', 1)[0]
        diff = data[data.index(b'diff --git '):]
        with self.assertRaisesRegex(ValueError, 'rationale'):
            AUDIT.inspect_patch(headers + b'\n\n' + diff)

    def test_raw_source_diff_rejected(self):
        with self.assertRaisesRegex(ValueError, 'metadata'):
            AUDIT.inspect_patch(b'diff --git a/file b/file\n')

    def test_invalid_author_date_rejected(self):
        data = (ROOT / 'daemon/patches/ecash/01-nlogn-block-construction.patch').read_bytes()
        import re
        data = re.sub(br'(?m)^Date:.*$', b'Date: unavailable', data)
        with self.assertRaisesRegex(ValueError, 'Date|date'):
            AUDIT.inspect_patch(data)
