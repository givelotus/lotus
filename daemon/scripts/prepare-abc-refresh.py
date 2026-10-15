#!/usr/bin/env python3
"""Prepare coordinated, isolated candidates for non-V1 ABC patch stacks.

One exact ABC revision is selected once. eCash and Dogecoin patch stacks are
replayed into separate candidate worktrees, and the Chronik provider is
exported from the same revision. No active pin, workspace, or release changes.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
DAEMON = ROOT / "daemon"
PIN = DAEMON / "bitcoin-abc-version"
DOGED_MANIFEST = DAEMON / "patches/doged/manifest.json"
CHRONIK_PIN = DAEMON / "chronik/source.json"
CHRONIK_REFRESH = DAEMON / "scripts/prepare-chronik-refresh.py"
PATCH_SERIES = DAEMON / "scripts/patch-series.py"


def run(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=check)


def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return run(["git", "-C", str(repo), *args], check=check)


def read_pin(path: Path) -> str:
    for line in path.read_text().splitlines():
        value = line.strip()
        if value and not value.startswith("#"):
            return value
    raise ValueError(f"No commit pin found in {path}")


def resolve_base(repo: Path, requested: str, remote: str) -> tuple[str, str]:
    repo.mkdir()
    git(repo, "init", "--bare", "--quiet")
    git(repo, "remote", "add", "origin", remote)
    if requested == "latest":
        advertised = run(["git", "ls-remote", "--symref", remote, "HEAD"])
        branch_line = next((line for line in advertised.stdout.splitlines()
                            if line.startswith("ref:") and line.endswith("\tHEAD")), None)
        if not branch_line:
            raise ValueError("ABC remote did not advertise its default branch")
        ref = branch_line.split()[1]
        branch = ref.removeprefix("refs/heads/")
    else:
        ref = requested
        branch = ""
    fetched = git(repo, "fetch", "--quiet", "--filter=blob:none", "--depth=1", "origin", ref, check=False)
    if fetched.returncode:
        raise ValueError(f"Could not fetch ABC ref {requested}: {fetched.stdout.strip()}")
    commit = git(repo, "rev-parse", "FETCH_HEAD^{commit}").stdout.strip()
    git(repo, "update-ref", f"refs/lotus/candidate/{commit}", commit)
    return commit, branch


def worktree(repo: Path, path: Path, commit: str, remote: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    git(repo, "worktree", "add", "--quiet", "--detach", str(path), commit)
    git(path, "remote", "set-url", "origin", remote)
    make_worktree_portable(path)


def make_worktree_portable(path: Path) -> None:
    admin = Path(git(path, "rev-parse", "--path-format=absolute", "--git-dir").stdout.strip())
    admin_link = os.path.relpath(admin.resolve(), path.resolve())
    reverse_link = os.path.relpath((path / ".git").resolve(), admin.resolve())
    (path / ".git").write_text(f"gitdir: {admin_link}\n")
    (admin / "gitdir").write_text(f"{reverse_link}\n")
    # Verify the relative gitdir/commondir links before making candidate edits.
    if git(path, "rev-parse", "--show-toplevel").stdout.strip() != str(path.resolve()):
        raise ValueError(f"Could not make candidate worktree portable: {path}")


def patch_names(series_path: Path) -> list[str]:
    return [line.strip() for line in series_path.read_text().splitlines()
            if line.strip() and not line.lstrip().startswith("#")]


def metadata_hash(repo: Path, commit: str) -> str:
    metadata = git(repo, "show", "-s", "--format=%an%x00%ae%x00%aI%x00%B", commit).stdout.encode()
    return hashlib.sha256(metadata).hexdigest()


def refresh_doged_manifest(workspace: Path, base: str, destination: Path) -> dict:
    original = json.loads(DOGED_MANIFEST.read_text())
    names = patch_names(DAEMON / "patches/doged/series")
    commits = git(workspace, "rev-list", "--reverse", "--first-parent", f"{base}..HEAD").stdout.splitlines()
    if len(commits) != len(names) or len(original["patches"]) != len(names):
        raise ValueError("Dogecoin candidate commit count does not match its patch series")
    for index, (name, commit) in enumerate(zip(names, commits, strict=True)):
        row = original["patches"][index]
        if row["patch"] != name:
            raise ValueError(f"Dogecoin provenance order differs at {name}")
        if metadata_hash(workspace, commit) != row["metadata_sha256"]:
            raise ValueError(f"Dogecoin patch metadata changed during replay: {name}")
        row["integration_commit"] = commit
        row["tree"] = git(workspace, "rev-parse", f"{commit}^{{tree}}").stdout.strip()
    original["base"] = base
    original["final_tree"] = git(workspace, "rev-parse", "HEAD^{tree}").stdout.strip()
    if "tested_integration_head" in original:
        original["previous_tested_integration_head"] = original.pop("tested_integration_head")
    original["validation"] = (
        f"Patch replay only on candidate ABC {base}; build and behavioral validation pending."
    )
    destination.write_text(json.dumps(original, indent=2) + "\n")
    return original


def chronik_module():
    spec = importlib.util.spec_from_file_location("prepare_chronik_refresh", CHRONIK_REFRESH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load Chronik candidate exporter")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def report_write(path: Path, report: dict) -> None:
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")


def prepare(requested: str, candidate: Path) -> dict:
    candidate = candidate.absolute()
    if candidate.exists() or candidate.is_symlink():
        raise ValueError("Candidate destination already exists; choose a new directory")
    shared_pin = read_pin(PIN)
    doged_pin = json.loads(DOGED_MANIFEST.read_text())["base"]
    chronik_pin = json.loads(CHRONIK_PIN.read_text())
    if not (shared_pin == doged_pin == chronik_pin["upstream_commit"]):
        raise ValueError("Shared ABC, Dogecoin provenance, and Chronik source pins have drifted; reconcile them first")
    remote = chronik_pin["upstream_url"]
    candidate.parent.mkdir(parents=True, exist_ok=True)
    candidate.mkdir()
    report_path = candidate / "refresh-report.json"
    report = {
        "schema": 1,
        "candidate_only": True,
        "requested_ref": requested,
        "upstream_url": remote,
        "source_pin": str(PIN.relative_to(ROOT)),
        "previous_commit": shared_pin,
        "resolved_commit": None,
        "default_branch": None,
        "targets": {
            "ecash": {"application": "not attempted", "build": "not attempted", "behavior": "not attempted"},
            "doged": {"application": "not attempted", "provenance": "not attempted",
                      "build": "not attempted", "behavior": "not attempted"},
            "chronik-provider": {"export": "not attempted", "host_patch_application": "not attempted", "host_builds": "not attempted", "behavior": "not attempted"},
        },
        "limitations": [
            "Patch replay and export do not establish a successful build or protocol behavior.",
            "Lotus V1 pin and release artifacts are intentionally excluded.",
            "No active pin, workspace, patch manifest, or published release is modified.",
        ],
    }
    report_write(report_path, report)
    try:
        base_repo = candidate / "abc-upstream.git"
        commit, branch = resolve_base(base_repo, requested, remote)
        report["resolved_commit"] = commit
        report["default_branch"] = branch or None
        report_write(report_path, report)

        pin_copy = candidate / "bitcoin-abc-version"
        pin_lines = PIN.read_text().splitlines()
        pin_copy.write_text("\n".join([commit, *pin_lines[1:]]) + "\n")

        for name, series, allow_empty in (("ecash", "ecash", True), ("doged", "doged", False)):
            workspace = candidate / "workspaces" / name
            result = report["targets"][name]
            try:
                worktree(base_repo, workspace, commit, remote)
                command = [sys.executable, str(PATCH_SERIES), str(workspace),
                           str(DAEMON / "patches" / series / "series"), "--base", commit]
                if allow_empty:
                    command.append("--allow-empty")
                replay = run(command, check=False)
                (candidate / f"{name}-replay.log").write_text(replay.stdout)
                result["application"] = "passed" if replay.returncode == 0 else "failed"
                result["exit_code"] = replay.returncode
                if replay.returncode == 0:
                    result["head"] = git(workspace, "rev-parse", "HEAD").stdout.strip()
                    result["tree"] = git(workspace, "rev-parse", "HEAD^{tree}").stdout.strip()
                    if name == "doged":
                        try:
                            manifest = refresh_doged_manifest(workspace, commit, candidate / "doged-manifest.json")
                            result["provenance"] = "passed"
                            result["candidate_manifest"] = "doged-manifest.json"
                            result["patches"] = len(manifest["patches"])
                        except (OSError, ValueError, subprocess.CalledProcessError) as error:
                            result["provenance"] = "failed"
                            result["provenance_detail"] = str(error)
            except (OSError, ValueError, subprocess.CalledProcessError) as error:
                result["application"] = "failed"
                result["detail"] = str(error)
            report_write(report_path, report)

        try:
            chronik_module().prepare(base_repo, commit, candidate / "chronik-provider")
            chronik_report = json.loads((candidate / "chronik-provider/refresh-report.json").read_text())
            report["targets"]["chronik-provider"]["export"] = "passed"
            report["targets"]["chronik-provider"]["provider_commit"] = chronik_report["upstream_commit"]
            report["targets"]["chronik-provider"]["host_patch_application"] = {
                name: row["status"] for name, row in chronik_report["adapter_checks"].items()
            }
        except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
            report["targets"]["chronik-provider"]["export"] = "failed"
            report["targets"]["chronik-provider"]["detail"] = str(error)
        report_write(report_path, report)
        return report
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        report["fatal_error"] = str(error)
        report_write(report_path, report)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ref", default="latest", help="Canonical ABC default branch, tag, or commit")
    parser.add_argument("--candidate", type=Path, required=True, help="New isolated output directory; never overwritten")
    args = parser.parse_args()
    try:
        report = prepare(args.ref, args.candidate)
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"ABC refresh candidate failed: {error}\n")
    print(json.dumps({"candidate": str(args.candidate.absolute()), "resolved_commit": report["resolved_commit"],
                      "targets": report["targets"]}, indent=2, sort_keys=True))
    failed = any(target.get("application") == "failed" or target.get("export") == "failed"
                 for target in report["targets"].values())
    failed = failed or report["targets"]["doged"].get("provenance") == "failed"
    failed = failed or any(status != "clean-apply" for status in
                           report["targets"]["chronik-provider"].get("host_patch_application", {}).values())
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
