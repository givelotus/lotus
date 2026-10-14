"""Offline release transactions use synthetic repositories, never live nodes."""
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("prepare_release", Path(__file__).with_name("prepare-release.py"))
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.upstream = self.root / "upstream"
        self.upstream.mkdir()
        subprocess.run(["git", "init", "-q", str(self.upstream)], check=True)
        files = {
            "contrib/aur/common/lotus.install": "post_remove() {\n  _rmuser\n  rm -rf /srv/lotus /run/lotus\n}\n",
            "contrib/aur/common/lotus.service": "ExecStop=/usr/bin/lotusd stop\n",
            "contrib/aur/common/lotus-reindex.service": "ExecStop=/usr/bin/lotusd stop\n",
            "CMakeLists.txt": "project(lotus\n\tVERSION 11.5.1\n)\n",
            "contrib/aur/lotus/PKGBUILD": "pkgver=1.0.0\npkgrel=3\nsource=(https://github.com/LogosFoundation/lotusd/archive/v$pkgver.tar.gz)\ncd ${pkgname}-$pkgver\n",
            "contrib/aur/lotus-qt/PKGBUILD": "pkgver=1.0.0\npkgrel=3\nsource=(https://github.com/logosfoundation/lotusd/archive/v$pkgver.tar.gz)\ncd lotus-$pkgver\n",
            "contrib/docker/lotus/Dockerfile": "FROM debian:bookworm-slim\n",
            "contrib/docker/lotus/README.md": "old example\n",
        }
        for name, data in files.items():
            path = self.upstream / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(data)
        self.git("add", ".")
        self.git("-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "Fixture")
        daemon = self.root / "daemon"
        (daemon / "patches/v1").mkdir(parents=True)
        (daemon / "bitcoin-abc-v1-version").write_text(self.git("rev-parse", "HEAD").decode().strip() + "\n")
        (daemon / "release-version").write_text("11.6.0\n")
        (daemon / "patches/v1/series").write_text("# Synthetic series\n")

    def tearDown(self):
        self.temporary.cleanup()

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.upstream), *args])

    def prepare(self, version="11.6.0", **kwargs):
        return release.prepare(self.root, self.upstream, version, **kwargs)

    def test_dry_run_is_read_only_then_write_and_check(self):
        before = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        result = self.prepare()
        self.assertTrue(result["changed"])
        self.assertEqual(before, {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()})
        self.prepare(write=True)
        self.assertEqual(self.prepare(check=True)["changed"], [])
        self.assertEqual(self.git("status", "--porcelain"), b"")

    def test_version_change_propagates_and_historical_patches_stay_fixed(self):
        self.prepare(write=True)
        self.prepare("12.0.1", write=True)
        data = (self.root / "daemon/patches/v1/999-release-metadata.patch").read_text()
        self.assertIn("+\tVERSION 12.0.1", data)
        self.assertIn("+pkgver=12.0.1", data)
        self.assertIn("lotus-v12.0.1-x86_64-linux-gnu.tar.gz", data)
        self.assertIn("/releases/download/v$pkgver/lotus-v$pkgver-source.tar.gz", data)
        self.assertEqual(self.prepare("12.0.1", check=True)["changed"], [])

    def test_bad_versions_do_not_write(self):
        for version in ("v12.0.0", "01.2.3", "1.2", "1.2.3;touch x", "1.2.3-rc1"):
            with self.assertRaises(ValueError):
                self.prepare(version, write=True)
        self.assertFalse((self.root / "daemon/release-manifest.json").exists())

    def test_drift_and_bad_patch_fail_without_writes(self):
        self.prepare(write=True)
        manifest = self.root / "daemon/release-manifest.json"
        manifest.write_text("{}\n")
        with self.assertRaisesRegex(ValueError, "drift"):
            self.prepare(check=True)
        series = self.root / "daemon/patches/v1/series"
        series.write_text("broken.patch\n" + release.PATCH + "\n")
        (series.parent / "broken.patch").write_text("not a patch")
        with self.assertRaises(subprocess.CalledProcessError):
            self.prepare(write=True)
        self.assertEqual(manifest.read_text(), "{}\n")

    def test_archive_matches_manifest_tree(self):
        import tarfile
        self.prepare(write=True)
        archive = self.root / "source.tar.gz"
        self.prepare(check=True, archive=archive)
        with tarfile.open(archive) as tar:
            cmake = tar.extractfile("lotus-v11.6.0/CMakeLists.txt").read()
            self.assertIn(b"VERSION 11.6.0", cmake)
        manifest = json.loads((self.root / "daemon/release-manifest.json").read_text())
        self.assertEqual(len(manifest["source_tree"]), 40)
        second = self.root / "source-again.tar.gz"
        self.prepare(check=True, archive=second)
        self.assertEqual(archive.read_bytes(), second.read_bytes())
        replay = self.root / "mail-replay"
        subprocess.run(["git", "clone", "-q", str(self.upstream), str(replay)], check=True)
        subprocess.run(["git", "-C", str(replay), "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "am", str(self.root / "daemon/patches/v1" / release.PATCH)], check=True, stdout=subprocess.PIPE)
        tree = subprocess.check_output(["git", "-C", str(replay), "rev-parse", "HEAD^{tree}"]).decode().strip()
        self.assertEqual(tree, manifest["source_tree"])

    def test_atomic_failure_restores_all_original_files(self):
        first, second = self.root / "first", self.root / "second"
        first.write_bytes(b"old")
        real_replace = release.os.replace
        def fail_second(source, destination):
            if destination == second:
                raise OSError("injected transaction failure")
            return real_replace(source, destination)
        with patch.object(release.os, "replace", side_effect=fail_second):
            with self.assertRaises(OSError):
                release.atomic_write({first: b"new", second: b"new"})
        self.assertEqual(first.read_bytes(), b"old")
        self.assertFalse(second.exists())
        self.assertEqual(list(self.root.glob(".release-*")), [])

    def test_candidate_promoted_once_and_failure_leaves_no_directory(self):
        subprocess.run(["git", "init", "-q", "-b", "main", str(self.root)], check=True)
        (self.root / ".git/info/exclude").write_text("upstream/\n")
        def git(*args):
            subprocess.run(["git", "-C", str(self.root), "-c", "user.name=Test", "-c", "user.email=test@example.invalid", *args], check=True, stdout=subprocess.PIPE)
        git("add", "daemon")
        git("commit", "-qm", "Candidate fixture")
        destination = self.root / "review"
        release.candidate(self.root, self.upstream, "12.0.0", destination)
        self.assertEqual((destination / "daemon/release-version").read_text(), "12.0.0\n")
        self.assertEqual((self.root / "daemon/release-version").read_text(), "11.6.0\n")
        self.assertEqual(release.prepare(destination, self.upstream, "12.0.0", check=True)["changed"], [])
        with self.assertRaisesRegex(ValueError, "already exists"):
            release.candidate(self.root, self.upstream, "12.0.0", destination)
        failed = self.root / "failed"
        with self.assertRaises(ValueError):
            release.candidate(self.root, self.upstream, "bad", failed)
        self.assertFalse(failed.exists())
        self.assertFalse(list(self.root.glob(".lotus-candidate-*")))

    def test_publish_exact_reviewed_commit_once_and_reject_dirty_checkout(self):
        self.prepare(write=True)
        remote = self.root / "remote.git"
        subprocess.run(["git", "init", "--bare", "-q", str(remote)], check=True)
        subprocess.run(["git", "init", "-q", "-b", "main", str(self.root)], check=True)
        def git(*args):
            return subprocess.check_output(["git", "-C", str(self.root), "-c", "user.name=Test", "-c", "user.email=test@example.invalid", *args], stderr=subprocess.PIPE).decode().strip()
        git("add", "daemon")
        # Keep the synthetic object source and remote outside the reviewed tree.
        (self.root / ".git/info/exclude").write_text("upstream/\nremote.git/\n")
        git("commit", "-qm", "Reviewed candidate")
        git("remote", "add", "origin", str(remote))
        git("push", "-q", "origin", "main")
        commit = git("rev-parse", "HEAD")
        git("config", "user.name", "Test")
        git("config", "user.email", "test@example.invalid")
        with self.assertRaisesRegex(ValueError, "HEAD differs"):
            release.publish(self.root, "11.6.0", "0" * 40)
        real_run = release.run
        def checked_run(args, **kwargs):
            if args[0] == "gh":
                return json.dumps({"headSha": commit, "conclusion": "success", "event": "workflow_dispatch", "workflowName": "Build & Release Lotus Daemon (with Chronik)"}).encode()
            return real_run(args, **kwargs)
        with patch.object(release, "run", side_effect=checked_run):
            self.assertEqual(release.publish(self.root, "11.6.0", commit, "123"), "v11.6.0")
        self.assertIn("refs/tags/v11.6.0", git("ls-remote", "origin", "refs/tags/v11.6.0"))
        with patch.object(release, "run", side_effect=checked_run):
            with self.assertRaisesRegex(ValueError, "already exists"):
                release.publish(self.root, "11.6.0", commit, "123")
        (self.root / "daemon/release-version").write_text("12.0.0\n")
        with self.assertRaisesRegex(ValueError, "clean"):
            release.publish(self.root, "12.0.0", commit)


if __name__ == "__main__":
    unittest.main()
