#!/usr/bin/env python3
"""Retire only unchanged, clean, inactive worktrees with verified HEAD backups.

Ignored data is retained by same-filesystem rename, never deleted. Dirty source,
untracked source, open-file references, and changed HEADs cause a refusal.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time


def git(path, *args):
    return subprocess.check_output(["git", "-C", str(path), *args])


def save(path, value):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(value, indent=2) + "\n")
    tmp.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--retain-ignored", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    records = root / "daemon/patch-audit/consolidation/20261022"
    out = records / "worktree-retirement"
    audit = json.loads((records / "worktree-cleanup-audit.json").read_text())["entries"]
    preservation = json.loads((out / "HEAD-PRESERVATION.json").read_text())
    backed = {r["path"]: r for r in preservation["entries"]}
    bundle = json.loads((out / "BUNDLE.json").read_text())
    with Path(bundle["path"]).open("rb") as stream:
        assert hashlib.file_digest(stream, "sha256").hexdigest() == bundle["sha256"]
    subprocess.run(["git", "--git-dir=" + preservation["archive_git_dir"],
                    "bundle", "verify", bundle["path"]], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    open_names = [s[1:] for s in (root / "daemon/.local-artifact-archive/cleanup-open-files.txt")
                  .read_text(errors="replace").splitlines() if s.startswith("n/")]
    processes = subprocess.check_output(["ps", "-axo", "pid=,command="], text=True)
    retained = root / "daemon/.local-artifact-archive/retired-worktree-data"
    retained.mkdir(mode=0o700, exist_ok=True)
    os.chmod(retained, 0o700)
    result = {"started_unix": time.time(), "execute": args.execute, "entries": []}
    receipt = out / ("retirement-ignored.json" if args.retain_ignored else "retirement-clean.json")
    for old in audit:
        if not old.get("retire_candidate"):
            continue
        item = {"path": old["path"], "family": old["family"]}
        result["entries"].append(item)
        path = Path(old["path"])
        moved = []
        try:
            if not path.exists():
                item["status"] = "already-absent"
                continue
            assert path.parent == Path("/Users/shammah/repos"), "Outside audited scope"
            assert (path / ".git").is_file(), "Not a linked worktree"
            assert not any(n == str(path) or n.startswith(str(path) + "/")
                           for n in open_names), "Open files or working directory"
            assert not any(str(path) in line for line in processes.splitlines()), "Referenced by process"
            expected = backed[str(path)]
            assert git(path, "rev-parse", "HEAD").decode().strip() == expected["head"], "HEAD changed"
            archived = subprocess.check_output(["git", "--git-dir=" + preservation["archive_git_dir"],
                                                "rev-parse", expected["archive_ref"]], text=True).strip()
            assert archived == expected["head"], "Backup ref mismatch"
            status = git(path, "status", "--porcelain=v1", "-z", "--ignored=matching",
                         "--untracked-files=normal")
            assert hashlib.sha256(status).hexdigest() == old["status_sha256"], "Working state changed"
            entries = [x for x in status.decode(errors="surrogateescape").split("\0") if x]
            assert all(x.startswith("!! ") for x in entries), "Dirty or untracked source"
            ignored = [x[3:].rstrip("/") for x in entries]
            if ignored and not args.retain_ignored:
                item["status"] = "ignored-data-held"
                continue
            item["head"] = expected["head"]
            item["archive_ref"] = expected["archive_ref"]
            item["retained_data"] = []
            if not args.execute:
                item["status"] = "eligible"
                continue
            for relative in sorted(ignored, key=lambda s: (s.count("/"), s)):
                rel = Path(relative)
                assert not rel.is_absolute() and ".." not in rel.parts
                if any(rel.is_relative_to(Path(m[0])) for m in moved):
                    continue
                source = path / rel
                target = retained / old["family"] / path.name / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                assert not target.exists() and not target.is_symlink(), "Retention destination exists"
                before = source.lstat()
                assert before.st_dev == target.parent.stat().st_dev, "Cross-filesystem move refused"
                info = {"original": str(source), "retained": str(target),
                        "device": before.st_dev, "inode": before.st_ino,
                        "symlink": source.is_symlink()}
                if source.is_symlink():
                    info["link_target"] = os.readlink(source)
                os.rename(source, target)
                after = target.lstat()
                assert (after.st_dev, after.st_ino) == (before.st_dev, before.st_ino)
                moved.append((relative, target))
                item["retained_data"].append(info)
                save(receipt, result)
            assert not git(path, "status", "--porcelain=v1", "-z", "--ignored=matching",
                           "--untracked-files=normal"), "Data remains; removal refused"
            command = ["git", "--git-dir=" + old["git_common_dir"], "worktree", "remove", str(path)]
            subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            assert not path.exists()
            item["status"] = "removed"
            print("REMOVED", path, flush=True)
        except Exception as error:
            item["status"] = "held"
            item["reason"] = str(error)
            if path.exists():
                for relative, target in reversed(moved):
                    original = path / relative
                    if target.exists() or target.is_symlink():
                        if not original.exists() and not original.is_symlink():
                            original.parent.mkdir(parents=True, exist_ok=True)
                            os.rename(target, original)
                if moved:
                    item["retention_rolled_back"] = True
        finally:
            save(receipt, result)
    result["finished_unix"] = time.time()
    save(receipt, result)
    from collections import Counter
    print(dict(Counter(r["status"] for r in result["entries"])), flush=True)


if __name__ == "__main__":
    main()
