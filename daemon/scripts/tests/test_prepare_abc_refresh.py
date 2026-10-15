"""Tests for the candidate-only shared ABC refresh workflow."""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "prepare-abc-refresh.py"
SPEC = importlib.util.spec_from_file_location("prepare_abc_refresh", SCRIPT)
ABC_REFRESH = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(ABC_REFRESH)


class PrepareAbcRefresh(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def git(self, repo, *args):
        return subprocess.check_output(["git", "-C", str(repo), *args], stderr=subprocess.PIPE)

    def test_pin_drift_refuses_before_candidate_creation(self):
        daemon = self.root / "daemon"
        (daemon / "patches/doged").mkdir(parents=True)
        (daemon / "chronik").mkdir()
        pin = daemon / "bitcoin-abc-version"
        pin.write_text("a" * 40 + "\n")
        doged = daemon / "patches/doged/manifest.json"
        doged.write_text(json.dumps({"base": "b" * 40}))
        chronik = daemon / "chronik/source.json"
        chronik.write_text(json.dumps({"upstream_commit": "a" * 40}))
        candidate = self.root / "candidate"
        with patch.object(ABC_REFRESH, "PIN", pin), \
             patch.object(ABC_REFRESH, "DOGED_MANIFEST", doged), \
             patch.object(ABC_REFRESH, "CHRONIK_PIN", chronik):
            with self.assertRaisesRegex(ValueError, "pins have drifted"):
                ABC_REFRESH.prepare("latest", candidate)
        self.assertFalse(candidate.exists())

    def test_doged_candidate_manifest_updates_trees_but_preserves_metadata(self):
        daemon = self.root / "daemon"
        patch_dir = daemon / "patches/doged"
        patch_dir.mkdir(parents=True)
        (patch_dir / "series").write_text("0001-change.patch\n")
        repo = self.root / "repo"
        repo.mkdir()
        self.git(repo, "init", "-q")
        self.git(repo, "config", "user.name", "Base")
        self.git(repo, "config", "user.email", "base@example.invalid")
        (repo / "file").write_text("base\n")
        self.git(repo, "add", "file")
        self.git(repo, "commit", "-qm", "Base")
        base = self.git(repo, "rev-parse", "HEAD").decode().strip()
        (repo / "file").write_text("candidate\n")
        self.git(repo, "add", "file")
        self.git(repo, "-c", "user.name=Patch Author", "-c", "user.email=author@example.invalid",
                 "-c", "user.date=2026-10-15T12:00:00Z", "commit", "-qm", "Preserve patch metadata")
        commit = self.git(repo, "rev-parse", "HEAD").decode().strip()
        row = {"patch": "0001-change.patch", "metadata_sha256": ABC_REFRESH.metadata_hash(repo, commit),
               "integration_commit": "old", "tree": "old"}
        source_manifest = {"base": "old", "final_tree": "old", "validation": "previous validation",
                           "patches": [row]}
        manifest_path = patch_dir / "manifest.json"
        manifest_path.write_text(json.dumps(source_manifest))
        output = self.root / "candidate-manifest.json"
        with patch.object(ABC_REFRESH, "DAEMON", daemon), patch.object(ABC_REFRESH, "DOGED_MANIFEST", manifest_path):
            result = ABC_REFRESH.refresh_doged_manifest(repo, base, output)
        updated = json.loads(output.read_text())
        self.assertEqual(updated["base"], base)
        self.assertEqual(updated["final_tree"], self.git(repo, "rev-parse", "HEAD^{tree}").decode().strip())
        self.assertEqual(updated["patches"][0]["integration_commit"], commit)
        self.assertNotEqual(updated["patches"][0]["tree"], "old")
        self.assertEqual(updated["patches"][0]["metadata_sha256"], row["metadata_sha256"])
        self.assertIn("validation pending", result["validation"])

    def test_candidate_build_clone_survives_moving_candidate_directory(self):
        source = self.root / "source"
        source.mkdir()
        self.git(source, "init", "-q")
        self.git(source, "config", "user.name", "Fixture")
        self.git(source, "config", "user.email", "fixture@example.invalid")
        (source / "file").write_text("fixture\n")
        self.git(source, "add", "file")
        self.git(source, "commit", "-qm", "Fixture")
        candidate = self.root / "candidate"
        candidate.mkdir()
        upstream = candidate / "abc-upstream.git"
        subprocess.run(["git", "clone", "--quiet", "--bare", str(source), str(upstream)], check=True)
        workspace = candidate / "workspaces/ecash"
        ABC_REFRESH.materialize_source(upstream, workspace,
                                       self.git(source, "rev-parse", "HEAD").decode().strip(),
                                       str(upstream))
        moved = self.root / "renamed-candidate"
        shutil.move(candidate, moved)
        self.assertTrue((moved / "workspaces/ecash/.git").is_dir())
        self.assertEqual(self.git(moved / "workspaces/ecash", "remote", "get-url", "origin").decode().strip(),
                         str(upstream))
        self.assertEqual(self.git(moved / "workspaces/ecash", "rev-parse", "HEAD").decode().strip(),
                         self.git(moved / "abc-upstream.git", "rev-parse", "HEAD").decode().strip())


if __name__ == "__main__":
    unittest.main()
