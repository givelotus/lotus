#!/usr/bin/env python3
"""Apply reviewed offline host overlays to a private verified export copy."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(root, name):
    path = Path(name)
    if path.is_absolute() or ".." in path.parts or ".git" in path.parts:
        raise ValueError(f"Unsafe profile path: {name}")
    result = root / path
    if not result.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"Profile path escapes root: {name}")
    return result


def files(root):
    return {
        str(p.relative_to(root)): digest(p)
        for p in root.rglob("*")
        if p.is_file() and ".git" not in p.relative_to(root).parts
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True, type=Path)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--host-source", required=True, type=Path)
    parser.add_argument("--host-profile", required=True)
    parser.add_argument("--host-upstream-commit", required=True)
    parser.add_argument("--provider-upstream-commit", required=True)
    args = parser.parse_args()
    profile = json.loads(args.profile.read_text())
    if profile["format"] != 1 or profile["host_profile"] != args.host_profile:
        raise ValueError("Unsupported or mismatched host profile")
    if profile["host_upstream_commit"] != args.host_upstream_commit:
        raise ValueError("Host upstream pin differs from reviewed profile")
    if profile["provider_upstream_commit"] != args.provider_upstream_commit:
        raise ValueError("Chronik provider pin differs from reviewed profile")
    for name, expected in profile["host_files_sha256"].items():
        if digest(relative(args.host_source, name)) != expected:
            raise ValueError(f"Host adapter source differs: {name}")
    native = profile["native_overlay"]
    if digest(relative(args.profile.parent, native["path"])) != native["sha256"]:
        raise ValueError("Native host mailbox differs from reviewed profile")
    before = files(args.source)
    # Own repository prevents git apply discovering a parent host repository.
    subprocess.run(["git", "init", "--quiet", str(args.source)], check=True)
    for overlay in profile["overlays"]:
        patch = relative(args.profile.parent, overlay["path"]).resolve()
        if digest(patch) != overlay["sha256"]:
            raise ValueError(f"Host overlay differs: {patch.name}")
        command = ["git", "-C", str(args.source), "apply", "--whitespace=error-all"]
        subprocess.run(command + ["--check", str(patch)], check=True)
        subprocess.run(command + [str(patch)], check=True)
    after = files(args.source)
    changed = {
        name: value for name, value in after.items() if before.get(name) != value
    }
    deleted = set(before) - set(after)
    if deleted or changed != profile["result_files_sha256"]:
        raise ValueError("Host overlay result differs from reviewed file set/hashes")
    print(
        json.dumps(
            {
                "host_profile": profile["host_profile"],
                "host_upstream_commit": profile["host_upstream_commit"],
                "changed_files": len(changed),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
