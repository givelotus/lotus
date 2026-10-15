#!/usr/bin/env python3
"""Prepare an isolated shared-Chronik provider refresh candidate.

The active source pin, adapter profiles, releases and workspaces are read-only.
The candidate contains a new source pin, verified deterministic export, adapter
patch applicability results, and a report suitable for an LLM/human rebase.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[2]
PROVIDER = ROOT / "daemon/chronik"
EXPORTER = ROOT / "daemon/scripts/export-chronik.py"
PROFILES = ("abc", "bchn", "bitcoin-core")


def run(*args: str, cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=check)


def git_bytes(repo: Path, *args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(repo), *args], stderr=subprocess.PIPE)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_exporter():
    spec = importlib.util.spec_from_file_location("export_chronik", EXPORTER)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def resolve_source(upstream: Path | None, requested: str, temp: Path, canonical_url: str) -> tuple[Path, str, str]:
    """Fetch only the requested ABC commit/tree, avoiding a full working checkout."""
    if requested == "latest":
        remote = canonical_url
    elif upstream is None:
        raise ValueError("An ABC clone is required for explicit refs; omit --ref or use --ref latest")
    else:
        remote = run("git", "-C", str(upstream), "remote", "get-url", "origin").stdout.strip()
    clone = temp / "abc"
    clone.mkdir()
    run("git", "-C", str(clone), "init", "--quiet")
    run("git", "-C", str(clone), "remote", "add", "origin", remote)
    if requested == "latest":
        advertised = run("git", "ls-remote", "--symref", remote, "HEAD")
        branch_line = next((line for line in advertised.stdout.splitlines() if line.startswith("ref:") and line.endswith("\tHEAD")), None)
        if not branch_line:
            raise ValueError("Origin did not advertise a default branch; pass --ref with a branch or commit")
        branch = branch_line.split()[1]
        run("git", "-C", str(clone), "fetch", "--quiet", "--filter=blob:none", "--depth=1", "origin", branch)
        ref = "FETCH_HEAD"
    else:
        fetched = run("git", "-C", str(clone), "fetch", "--quiet", "--filter=blob:none", "--depth=1", "origin", requested, check=False)
        if fetched.returncode:
            raise ValueError(f"Cannot fetch upstream ref {requested!r}: {fetched.stderr.strip()}")
        ref = "FETCH_HEAD"
    commit = run("git", "-C", str(clone), "rev-parse", f"{ref}^{{commit}}", check=False)
    if commit.returncode:
        raise ValueError(f"Fetched ref does not resolve to a commit: {requested}")
    revision = commit.stdout.strip()
    return clone, remote, revision


def adapter_result(candidate_export: Path, profile_dir: Path, output: Path) -> dict:
    """Apply a host's Chronik-source overlays to a private copy, recording conflicts."""
    profile = json.loads((profile_dir / "profile.json").read_text())
    dest = output / profile["host_profile"]
    shutil.copytree(candidate_export, dest)
    try:
        run("git", "init", "--quiet", str(dest))
        overlays = []
        for row in profile["overlays"]:
            patch = profile_dir / row["path"]
            actual = sha256(patch)
            if actual != row["sha256"]:
                return {"status": "invalid-profile-hash", "patch": row["path"], "expected": row["sha256"], "actual": actual}
            check = run("git", "-C", str(dest), "apply", "--check", "--whitespace=error-all", str(patch), check=False)
            if check.returncode:
                return {"status": "conflict", "patch": row["path"], "detail": (check.stderr or check.stdout).strip()}
            run("git", "-C", str(dest), "apply", "--whitespace=error-all", str(patch))
            overlays.append(row["path"])
        return {"status": "clean-apply", "overlays": overlays,
                "note": "Patch application only; profile result hashes, host build, and runtime behavior are not validated."}
    finally:
        shutil.rmtree(dest)


def abc_adapter_result(abc_source: Path, revision: str, output: Path) -> dict:
    patch = PROVIDER / "hosts/abc/0001-build-chronik-from-pinned-external-source.patch"
    target_files = re.findall(r"(?m)^diff --git a/(.*?) b/", patch.read_text())
    dest = output / "abc-host"
    dest.mkdir()
    try:
        archive = git_bytes(abc_source, "archive", "--format=tar", revision, "--", *target_files)
        with tarfile.open(fileobj=io.BytesIO(archive)) as stream:
            stream.extractall(dest, filter="data")
        run("git", "init", "--quiet", str(dest))
        check = run("git", "-C", str(dest), "apply", "--check", "--whitespace=error-all", str(patch), check=False)
        if check.returncode:
            return {"status": "conflict", "patch": str(patch.relative_to(ROOT)),
                    "detail": (check.stderr or check.stdout).strip()}
        return {"status": "clean-apply", "patch": str(patch.relative_to(ROOT)),
                "note": "Patch application only; ABC build, profile output hashes, and runtime behavior are not validated."}
    finally:
        shutil.rmtree(dest)


def prepare(upstream: Path | None, requested: str, candidate: Path) -> dict:
    candidate = candidate.absolute()
    if candidate.exists() or candidate.is_symlink():
        raise ValueError("Candidate destination already exists; choose a new directory")
    if upstream is not None and not upstream.is_dir():
        raise ValueError(f"Upstream clone does not exist: {upstream}")
    candidate.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".chronik-refresh-", dir=candidate.parent))
    try:
        pin = json.loads((PROVIDER / "source.json").read_text())
        clone, remote, revision = resolve_source(upstream, requested, stage, pin["upstream_url"])
        pin["upstream_commit"] = revision
        pin["chronik_tree"] = run("git", "-C", str(clone), "rev-parse", f"{revision}:chronik").stdout.strip()
        pin["upstream_files"] = {
            name: hashlib.sha256(git_bytes(clone, "show", f"{revision}:{name}")).hexdigest()
            for name in pin["upstream_files"]
        }
        pin["support_trees"] = {
            name: run("git", "-C", str(clone), "rev-parse", f"{revision}:{name}").stdout.strip()
            for name in pin.get("support_trees", {})
        }
        # Copy the reviewed dependency lock unchanged. The exporter rejects new
        # packages/edges or dependency drift instead of silently upgrading crates.
        staged_provider = stage / "provider"
        (staged_provider / "locks").mkdir(parents=True)
        lock_name = f"{revision[:12]}-Cargo.lock"
        shutil.copyfile(PROVIDER / pin["derived_lockfile"], staged_provider / "locks" / lock_name)
        pin["derived_lockfile"] = f"locks/{lock_name}"
        pin["derived_lockfile_sha256"] = sha256(staged_provider / "locks" / lock_name)
        pin.pop("export_manifest_sha256", None)
        pin_path = staged_provider / "source.json"
        pin_path.write_text(json.dumps(pin, indent=2, sort_keys=True) + "\n")
        export_path = stage / "export"
        exporter = load_exporter()
        manifest = exporter.export(clone, export_path, pin_path)
        pin["export_manifest_sha256"] = sha256(export_path / "chronik-source.json")
        pin_path.write_text(json.dumps(pin, indent=2, sort_keys=True) + "\n")
        adapters = {}
        adapter_root = stage / "adapter-checks"
        adapter_root.mkdir()
        adapters["abc"] = abc_adapter_result(clone, revision, adapter_root)
        for name in ("bchn", "bitcoin-core"):
            profile_dir = PROVIDER / "hosts" / name
            adapters[name] = adapter_result(export_path, profile_dir, adapter_root)
        report = {
            "schema": 1,
            "candidate_only": True,
            "requested_ref": requested,
            "resolved_from": remote,
            "upstream_commit": revision,
            "chronik_tree": manifest["chronik_tree"],
            "export_manifest_sha256": pin["export_manifest_sha256"],
            "source_pin": "provider/source.json",
            "export_directory": "export",
            "adapter_checks": adapters,
            "limitations": [
                "Clean adapter patch application does not verify profile output hashes, compile a host, or establish behavior.",
                "The reviewed dependency lockfile is retained; dependency drift or new crates cause export to fail for explicit review.",
                "No active pin, host profile, daemon workspace, release manifest, or published artifact was changed.",
            ],
            "next_steps": [
                "Review Chronik source and upstream dependency changes.",
                "Rebase each host overlay and native lifecycle patch, update profile hashes, and validate build/regtest per host.",
                "Only after host evidence passes, copy the reviewed provider pin/lock/export metadata into the active tree.",
            ],
        }
        (stage / "refresh-report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        # Drop the temporary full ABC clone; retain only portable review outputs.
        shutil.rmtree(clone)
        if candidate.exists() or candidate.is_symlink():
            raise ValueError("Candidate destination appeared while preparing; refusing replacement")
        os.rename(stage, candidate)
        return report
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream", type=Path, help="Optional ABC clone; explicit refs use its origin. latest uses the canonical URL in source.json")
    parser.add_argument("--ref", default="latest", help="Origin default branch ('latest'), branch, tag, or exact commit")
    parser.add_argument("--candidate", type=Path, required=True, help="New output directory; never overwritten")
    args = parser.parse_args()
    try:
        result = prepare(args.upstream, args.ref, args.candidate)
    except subprocess.CalledProcessError as error:
        detail = error.stderr.decode(errors="replace") if isinstance(error.stderr, bytes) else (error.stderr or "")
        parser.exit(1, f"Chronik refresh candidate failed: command exited {error.returncode}: {' '.join(error.cmd)}\n{detail}")
    except (ValueError, OSError, KeyError) as error:
        parser.exit(1, f"Chronik refresh candidate failed: {error}\n")
    print(json.dumps({"candidate": str(args.candidate.absolute()), "upstream_commit": result["upstream_commit"],
                      "adapter_checks": result["adapter_checks"]}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
