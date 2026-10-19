#!/usr/bin/env python3
"""Unit tests for daemon/scripts/lotus-git.py two-tier branch & patch-sync machinery."""

from __future__ import annotations

import argparse
import importlib.util
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parent.parent / "lotus-git.py"
SPEC = importlib.util.spec_from_file_location("lotus_git", SCRIPT_PATH)
assert SPEC and SPEC.loader
lotus_git = importlib.util.module_from_spec(SPEC)
sys.modules["lotus_git"] = lotus_git
SPEC.loader.exec_module(lotus_git)


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args]).decode().strip()


class TestLotusGitMachinery(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="test-lotus-git-"))
        self.orig_daemon_dir = lotus_git.DAEMON_DIR
        self.orig_monorepo_root = lotus_git.MONOREPO_ROOT

        self.monorepo = self.tmp / "monorepo"
        self.daemon_dir = self.monorepo / "daemon"
        (self.daemon_dir / "patches/ecash").mkdir(parents=True)
        (self.daemon_dir / "patches/v2").mkdir(parents=True)

        lotus_git.MONOREPO_ROOT = self.monorepo
        lotus_git.DAEMON_DIR = self.daemon_dir

        # Create a mock workspace-v2 git repository with base -> 2 ecash commits -> 2 v2 commits
        self.ws = self.daemon_dir / "workspace-v2"
        self.ws.mkdir(parents=True)
        git(self.ws, "init", "-b", "lotus-v2-work")
        git(self.ws, "config", "user.name", "Test Bot")
        git(self.ws, "config", "user.email", "test@lotus.org")

        (self.ws / "base.txt").write_text("base v1\n")
        git(self.ws, "add", "base.txt")
        git(self.ws, "commit", "-m", "upstream: initial base commit")
        self.base_sha = git(self.ws, "rev-parse", "HEAD")
        (self.daemon_dir / "bitcoin-abc-version").write_text(self.base_sha + "\n")

        # 2 Tier-1 (ecash) commits
        (self.ws / "ecash1.txt").write_text("ecash 1\n")
        git(self.ws, "add", "ecash1.txt")
        git(self.ws, "commit", "-m", "mempool: add chunked slab allocator")

        (self.ws / "ecash2.txt").write_text("ecash 2\n")
        git(self.ws, "add", "ecash2.txt")
        git(self.ws, "commit", "-m", "chronik: offload validation callbacks to worker")
        self.ecash_tip = git(self.ws, "rev-parse", "HEAD")
        git(self.ws, "branch", "daemon/ecash", self.ecash_tip)

        # 2 Tier-2 (v2) commits
        (self.ws / "v2_1.txt").write_text("v2 1\n")
        git(self.ws, "add", "v2_1.txt")
        git(self.ws, "commit", "-m", "v2: add 134-byte header and BLAKE3 PoW")

        (self.ws / "v2_2.txt").write_text("v2 2\n")
        git(self.ws, "add", "v2_2.txt")
        git(self.ws, "commit", "-m", "v2: add v7 transaction schema")
        self.v2_tip = git(self.ws, "rev-parse", "HEAD")

    def tearDown(self) -> None:
        lotus_git.DAEMON_DIR = self.orig_daemon_dir
        lotus_git.MONOREPO_ROOT = self.orig_monorepo_root
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_init_and_sync_two_tier_stack(self) -> None:
        # 1. Run init v2
        rc = lotus_git.cmd_init(argparse.Namespace(series="v2", ecash_tip=None))
        self.assertEqual(rc, 0)
        self.assertEqual(git(self.ws, "config", "--get", "rebase.updateRefs"), "true")
        self.assertEqual(git(self.ws, "config", "--get", "rebase.autoSquash"), "true")
        self.assertEqual(git(self.ws, "rev-parse", "refs/heads/daemon/ecash"), self.ecash_tip)
        self.assertEqual(git(self.ws, "rev-parse", "refs/heads/daemon/v2"), self.v2_tip)

        # 2. Run sync v2 (default: updates SHA pin files without writing .patch files)
        rc = lotus_git.cmd_sync(argparse.Namespace(series="v2", export_patches=False, verify_replay=False, push=False))
        self.assertEqual(rc, 0)
        self.assertEqual(lotus_git.read_head_pin_sha(lotus_git.SERIES_SPECS["ecash"]), self.ecash_tip)
        self.assertEqual(lotus_git.read_head_pin_sha(lotus_git.SERIES_SPECS["v2"]), self.v2_tip)

        # 3. Verify optional --export-patches still works when requested
        rc = lotus_git.cmd_sync(argparse.Namespace(series="v2", export_patches=True, verify_replay=False, push=False))
        self.assertEqual(rc, 0)
        ecash_series = (self.daemon_dir / "patches/ecash/series").read_text().splitlines()
        v2_series = (self.daemon_dir / "patches/v2/series").read_text().splitlines()
        self.assertEqual(len(ecash_series), 2)
        self.assertEqual(v2_series[0], "@include ../ecash/series")
        self.assertEqual(len(v2_series), 3)

    def test_sink_to_ecash_and_extract_pr(self) -> None:
        lotus_git.cmd_init(argparse.Namespace(series="v2", ecash_tip=None))

        # Add a chain-agnostic wallet commit at the top of daemon/v2
        (self.ws / "wallet_async.txt").write_text("async notifications proxy\n")
        git(self.ws, "add", "wallet_async.txt")
        git(self.ws, "commit", "-m", "wallet: offload NotificationsProxy to worker queue")

        # Sink HEAD down to daemon/ecash
        rc = lotus_git.cmd_sink_to_ecash(argparse.Namespace(commit="HEAD", export_patches=False, no_sync=False))
        self.assertEqual(rc, 0)

        # Verify daemon/ecash now has 3 commits and daemon/v2 still has 2 commits on top of it
        new_ecash_tip = git(self.ws, "rev-parse", "refs/heads/daemon/ecash")
        self.assertEqual(int(git(self.ws, "rev-list", "--count", f"{self.base_sha}..{new_ecash_tip}")), 3)
        self.assertEqual(int(git(self.ws, "rev-list", "--count", f"{new_ecash_tip}..HEAD")), 2)
        self.assertEqual(lotus_git.read_head_pin_sha(lotus_git.SERIES_SPECS["ecash"]), new_ecash_tip)

        # Extract that sunk commit onto a clean upstream PR branch directly on base/abc
        rc = lotus_git.cmd_extract_pr(
            argparse.Namespace(series="ecash", branch="pr/wallet-async", commits=[new_ecash_tip])
        )
        self.assertEqual(rc, 0)
        self.assertEqual(int(git(self.ws, "rev-list", "--count", f"{self.base_sha}..refs/heads/pr/wallet-async")), 1)
        self.assertEqual(
            git(self.ws, "log", "-1", "--format=%s", "refs/heads/pr/wallet-async"),
            "wallet: offload NotificationsProxy to worker queue",
        )

    def test_rebase_upstream_and_fixup_guard(self) -> None:
        lotus_git.cmd_init(argparse.Namespace(series="v2", ecash_tip=None))

        # Create a new upstream commit on top of self.base_sha
        git(self.ws, "checkout", "-b", "upstream-next", self.base_sha)
        (self.ws / "upstream_new.txt").write_text("new upstream feature\n")
        git(self.ws, "add", "upstream_new.txt")
        git(self.ws, "commit", "-m", "upstream: add new ABC commit")
        new_base_sha = git(self.ws, "rev-parse", "HEAD")

        # Switch back to lotus-v2-work and rebase onto new_base_sha
        git(self.ws, "checkout", "lotus-v2-work")
        rc = lotus_git.cmd_rebase_upstream(
            argparse.Namespace(series="v2", onto=new_base_sha, export_patches=False, no_sync=False)
        )
        self.assertEqual(rc, 0)

        # Verify pin file updated and both tiers rebased cleanly
        self.assertEqual((self.daemon_dir / "bitcoin-abc-version").read_text().strip(), new_base_sha)
        rebased_ecash = git(self.ws, "rev-parse", "refs/heads/daemon/ecash")
        self.assertEqual(int(git(self.ws, "rev-list", "--count", f"{new_base_sha}..{rebased_ecash}")), 2)
        self.assertEqual(int(git(self.ws, "rev-list", "--count", f"{rebased_ecash}..HEAD")), 2)

        # Verify unsquashed fixup! commits are caught by sync
        (self.ws / "ecash_1.txt").write_text("ecash 1 fixed via fixup\n")
        git(self.ws, "add", "ecash_1.txt")
        git(self.ws, "commit", "--fixup", ":/slab allocator")
        git(self.ws, "branch", "-f", "daemon/v2", "HEAD")
        with self.assertRaises(RuntimeError):
            lotus_git.cmd_sync(argparse.Namespace(series="v2", export_patches=False, verify_replay=False, push=False))

        # Verify cmd_autosquash non-interactively folds the fixup into daemon/ecash and updates both tiers
        rc = lotus_git.cmd_autosquash(
            argparse.Namespace(series="v2", export_patches=False, no_sync=False)
        )
        self.assertEqual(rc, 0)
        squashed_ecash = git(self.ws, "rev-parse", "refs/heads/daemon/ecash")
        squashed_v2 = git(self.ws, "rev-parse", "refs/heads/daemon/v2")
        self.assertEqual(int(git(self.ws, "rev-list", "--count", f"{new_base_sha}..{squashed_ecash}")), 2)
        self.assertEqual(int(git(self.ws, "rev-list", "--count", f"{squashed_ecash}..{squashed_v2}")), 2)
        self.assertEqual(lotus_git.read_head_pin_sha(lotus_git.SERIES_SPECS["ecash"]), squashed_ecash)
        self.assertEqual(lotus_git.read_head_pin_sha(lotus_git.SERIES_SPECS["v2"]), squashed_v2)


if __name__ == "__main__":
    unittest.main()
