"""Offline overlays must match native/source identities before compilation."""

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[2] / "chronik/cmake/apply-host-profile.py"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class HostProfileTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / "source"
        self.source.mkdir()
        (self.source / "wire").write_text("old\n")
        self.host = self.root / "host"
        self.host.mkdir()
        (self.host / "native").write_text("adapter\n")
        patch = self.root / "host.patch"
        patch.write_text(
            "diff --git a/wire b/wire\n--- a/wire\n+++ b/wire\n@@ -1 +1 @@\n-old\n+new\n"
        )
        self.profile = {
            "format": 1,
            "host_profile": "bitcoin-core",
            "host_upstream_commit": "a" * 40,
            "provider_upstream_commit": "b" * 40,
            "host_files_sha256": {"native": sha(self.host / "native")},
            "overlays": [{"path": patch.name, "sha256": sha(patch)}],
            "native_overlay": {"path": patch.name, "sha256": sha(patch)},
            "result_files_sha256": {"wire": hashlib.sha256(b"new\n").hexdigest()},
        }

    def run_profile(self, profile="bitcoin-core", host_pin="a" * 40):
        manifest = self.root / "profile.json"
        manifest.write_text(json.dumps(self.profile))
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--profile",
                str(manifest),
                "--source",
                str(self.source),
                "--host-source",
                str(self.host),
                "--host-profile",
                profile,
                "--host-upstream-commit",
                host_pin,
                "--provider-upstream-commit",
                "b" * 40,
            ],
            capture_output=True,
            text=True,
        )

    def test_real_offline_patch(self):
        result = self.run_profile()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.source / "wire").read_text(), "new\n")

    def test_wrong_component(self):
        self.assertNotEqual(self.run_profile(profile="bchn").returncode, 0)

    def test_wrong_upstream_pin(self):
        self.assertNotEqual(self.run_profile(host_pin="c" * 40).returncode, 0)

    def test_native_source_drift(self):
        (self.host / "native").write_text("different\n")
        self.assertNotEqual(self.run_profile().returncode, 0)
        self.assertEqual((self.source / "wire").read_text(), "old\n")

    def test_mailbox_drift(self):
        (self.root / "host.patch").write_text("changed")
        self.assertNotEqual(self.run_profile().returncode, 0)

    def test_result_drift(self):
        self.profile["result_files_sha256"]["wire"] = "0" * 64
        self.assertNotEqual(self.run_profile().returncode, 0)

    def test_path_escape(self):
        self.profile["overlays"][0]["path"] = "../host.patch"
        self.assertNotEqual(self.run_profile().returncode, 0)


if __name__ == "__main__":
    unittest.main()
