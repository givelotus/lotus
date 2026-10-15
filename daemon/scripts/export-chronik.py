#!/usr/bin/env python3
"""Export pinned ABC Chronik into a self-contained, source-verified workspace.

Only committed Git objects are read. Existing output directories are refused.
The exported Rust/C++/schema files remain byte-identical to their upstream tree;
only the root Cargo workspace/lock are derived. No host port is implied.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import tempfile
import tomllib

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PIN = ROOT / "daemon/chronik/source.json"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git(repo: Path, *args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(repo), *args], stderr=subprocess.PIPE)


def derive_workspace(original: bytes, members: list[str]) -> bytes:
    parsed = tomllib.loads(original.decode())
    upstream_members = parsed["workspace"]["members"]
    if set(members) != {m for m in upstream_members if m.startswith("chronik/")}:
        raise ValueError("Chronik Cargo members differ from upstream workspace")
    replacement = "members = [\n" + "".join(f'    "{member}",\n' for member in members) + "]"
    rewritten, count = re.subn(r"(?ms)^members = \[.*?^\]", replacement, original.decode(), count=1)
    if count != 1:
        raise ValueError("Unsupported upstream Cargo workspace layout")
    # Keep upstream's implicit resolver choice explicit; do not change resolution.
    if "resolver" not in parsed["workspace"]:
        rewritten = rewritten.replace("[workspace]\n", '[workspace]\nresolver = "1"\n', 1)
    return rewritten.encode()


def verify_lock(original: bytes, derived: bytes, member_names: set[str]) -> dict:
    old = tomllib.loads(original.decode())
    new = tomllib.loads(derived.decode())
    def identity(package):
        return tuple(package.get(key) for key in ("name", "version", "source", "checksum"))
    old_packages = {identity(p): p for p in old["package"]}
    def edges(package, packages):
        result = set()
        for edge in package.get("dependencies", []):
            parts = edge.split(" ", 2)
            choices = [p for p in packages if p["name"] == parts[0]]
            if len(parts) > 1:
                choices = [p for p in choices if p["version"] == parts[1]]
            if len(parts) > 2:
                choices = [p for p in choices if p.get("source") == parts[2].strip("()")]
            if len(choices) != 1:
                raise ValueError("Ambiguous or missing lockfile dependency edge")
            result.add(identity(choices[0]))
        return result
    for package in new["package"]:
        previous = old_packages.get(identity(package))
        if previous is None:
            raise ValueError("Derived lockfile changes a dependency version/source/checksum")
        if not edges(package, new["package"]) <= edges(previous, old["package"]):
            raise ValueError("Derived lockfile introduces dependency edges")
    local = {p["name"] for p in new["package"] if "source" not in p}
    if local != member_names:
        raise ValueError("Derived lockfile local packages do not match Chronik members")
    return {"upstream_packages": len(old["package"]), "export_packages": len(new["package"])}


def export(repo: Path, output: Path, pin_path: Path = DEFAULT_PIN) -> dict:
    output = output.absolute()
    if output.exists() or output.is_symlink():
        raise ValueError("Output already exists; choose a new candidate directory")
    pin = json.loads(pin_path.read_text())
    revision = pin["upstream_commit"]
    if pin.get("format") != 1 or re.fullmatch(r"[0-9a-f]{40}", revision) is None:
        raise ValueError("Source pin requires format 1 and an exact Git commit")
    actual = git(repo, "rev-parse", f"{revision}^{{commit}}").decode().strip()
    if actual != revision:
        raise ValueError("Upstream commit differs from pin")
    tree = git(repo, "rev-parse", f"{revision}:chronik").decode().strip()
    if tree != pin["chronik_tree"]:
        raise ValueError("Chronik source tree differs from pin")
    roots = pin["upstream_files"]
    required = {"Cargo.toml", "Cargo.lock", "COPYING", "cmake/modules/RustHelper.cmake"}
    if set(roots) != required:
        raise ValueError("Unsupported export root-file set")
    original = {name: git(repo, "show", f"{revision}:{name}") for name in roots}
    for name, data in original.items():
        if digest(data) != roots[name]:
            raise ValueError(f"Pinned upstream file differs: {name}")
    lock_path = (pin_path.parent / pin["derived_lockfile"]).resolve()
    if not lock_path.is_relative_to(pin_path.parent.resolve()):
        raise ValueError("Lockfile path escapes provider directory")
    lock = lock_path.read_bytes()
    if digest(lock) != pin["derived_lockfile_sha256"]:
        raise ValueError("Derived lockfile checksum differs from pin")
    support_trees = pin.get("support_trees", {})
    allowed_support = {"test/functional/test_framework"}
    if not set(support_trees) <= allowed_support:
        raise ValueError("Unsupported source support tree")
    for name, expected in support_trees.items():
        if git(repo, "rev-parse", f"{revision}:{name}").decode().strip() != expected:
            raise ValueError(f"Support source tree differs from pin: {name}")
    archive = git(repo, "archive", "--format=tar", revision, "chronik", *sorted(roots), *sorted(support_trees))
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".chronik-export-", dir=output.parent))
    try:
        with tarfile.open(fileobj=io.BytesIO(archive)) as stream:
            entries = stream.getmembers()
            if any(not (m.isfile() or m.isdir()) for m in entries):
                raise ValueError("Export contains unsupported links or special files")
            stream.extractall(stage, filter="data")
        source_hashes = {
            str(path.relative_to(stage)): digest(path.read_bytes())
            for prefix in ["chronik", *sorted(support_trees)]
            for path in sorted((stage / prefix).rglob("*")) if path.is_file()
        }
        # git archive may honor export attributes; verify every actual blob,
        # not merely the archive's claimed source-tree identity.
        tree_entries = git(repo, "ls-tree", "-r", "-z", revision, "chronik", *sorted(support_trees)).split(b"\0")
        expected_paths = set()
        for record in filter(None, tree_entries):
            metadata, name = record.split(b"\t", 1)
            mode, kind, object_id = metadata.split(b" ")
            path = name.decode()
            if kind != b"blob" or mode not in (b"100644", b"100755"):
                raise ValueError("Chronik tree contains unsupported object modes")
            data = (stage / path).read_bytes()
            blob = b"blob " + str(len(data)).encode() + b"\0" + data
            if hashlib.sha1(blob).hexdigest().encode() != object_id:
                raise ValueError(f"Export changes upstream blob: {path}")
            expected_paths.add(path)
        if expected_paths != set(source_hashes):
            raise ValueError("Export file set differs from upstream Chronik tree")
        members = sorted(str(path.parent.relative_to(stage)) for path in (stage / "chronik").glob("*/Cargo.toml"))
        member_names = {tomllib.loads((stage / member / "Cargo.toml").read_text())["package"]["name"] for member in members}
        lock_info = verify_lock(original["Cargo.lock"], lock, member_names)
        workspace = derive_workspace(original["Cargo.toml"], members)
        # Keep the original root inputs next to the explicit derived workspace.
        (stage / "upstream-workspace").mkdir()
        for name in ("Cargo.toml", "Cargo.lock"):
            (stage / "upstream-workspace" / name).write_bytes(original[name])
        (stage / "Cargo.toml").write_bytes(workspace)
        (stage / "Cargo.lock").write_bytes(lock)
        for member in members:
            data = tomllib.loads((stage / member / "Cargo.toml").read_text())
            def validate_paths(value):
                if isinstance(value, dict):
                    if "path" in value:
                        dependency = (stage / member / value["path"]).resolve()
                        if not dependency.is_relative_to((stage / "chronik").resolve()) or not (dependency / "Cargo.toml").is_file():
                            raise ValueError(f"Path dependency escapes the Chronik workspace: {member}")
                    for child in value.values():
                        validate_paths(child)
                elif isinstance(value, list):
                    for child in value:
                        validate_paths(child)
            # Only dependency sections; package/lib/build-script paths aren't crates.
            for key, value in data.items():
                if key.endswith("dependencies") or key == "target":
                    validate_paths(value)
        manifest = {
            "format": 1,
            "upstream_url": pin["upstream_url"],
            "upstream_commit": revision,
            "chronik_tree": tree,
            "support_trees": support_trees,
            "rust_toolchain": pin["rust_toolchain"],
            "upstream_root_hashes": roots,
            "workspace_members": members,
            "workspace_sha256": digest(workspace),
            "lockfile_sha256": digest(lock),
            "lockfile": lock_info,
            "source_files_sha256": source_hashes,
            "host_profiles": pin["host_profiles"],
        }
        manifest_bytes = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
        if "export_manifest_sha256" in pin and digest(manifest_bytes) != pin["export_manifest_sha256"]:
            raise ValueError("Generated export manifest differs from reviewed pin")
        (stage / "chronik-source.json").write_bytes(manifest_bytes)
        if output.exists() or output.is_symlink():
            raise ValueError("Output appeared during export; refusing replacement")
        os.rename(stage, output)
        return manifest
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream", type=Path, required=True, help="Read-only Git object source containing the exact pinned ABC revision")
    parser.add_argument("--output", type=Path, required=True, help="New output directory; never overwrite an existing export")
    parser.add_argument("--pin", type=Path, default=DEFAULT_PIN)
    args = parser.parse_args()
    try:
        result = export(args.upstream, args.output, args.pin)
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Chronik export failed: {error}\n")
    print(json.dumps({"upstream_commit": result["upstream_commit"], "chronik_tree": result["chronik_tree"], "members": len(result["workspace_members"]), "output": str(args.output)}))


if __name__ == "__main__":
    main()
