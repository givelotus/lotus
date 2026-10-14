#!/usr/bin/env python3
"""Export doged's unmatched commits and optionally try them on an exact ABC base.

This diagnostic deliberately stops at conflicts. Exported commits include
unmerged upstream work as well as Dogecoin adaptations and require review.
Only the newly created output directory is modified; no node is started.
"""
import argparse
import json
from pathlib import Path
import subprocess


def git(repo, *args, **kwargs):
    return subprocess.check_output(["git", "-C", str(repo), *args], **kwargs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path,
                        help="isolated Git clone containing both pinned revisions")
    parser.add_argument("--output", required=True, type=Path,
                        help="new directory; existing paths are refused")
    parser.add_argument("--doged", default="9690833b8b6709b7a7837bc397f0d04bf3b885d1")
    parser.add_argument("--abc", default="8c67fe1e85a602204a2ce65aa3b643469c2c3a1d")
    parser.add_argument("--apply", action="store_true", help="try git am --3way in a new clone")
    args = parser.parse_args()
    if args.output.exists():
        parser.error(f"Output already exists: {args.output}")
    source = args.source.resolve()
    doged = git(source, "rev-parse", f"{args.doged}^{{commit}}", text=True).strip()
    abc = git(source, "rev-parse", f"{args.abc}^{{commit}}", text=True).strip()
    ancestor = git(source, "merge-base", doged, abc, text=True).strip()
    cherry = git(source, "cherry", abc, doged, text=True).splitlines()
    unmatched = {line.split()[1] for line in cherry if line.startswith("+ ")}
    ordered = git(source, "rev-list", "--reverse", "--topo-order",
                  f"{abc}..{doged}", text=True).splitlines()
    commits = [commit for commit in ordered if commit in unmatched]
    args.output.mkdir(parents=True, exist_ok=False)
    patches = args.output / "patches"
    patches.mkdir()
    entries = []
    for index, commit in enumerate(commits):
        name = f"{index:04d}-{commit}.patch"
        (patches / name).write_bytes(git(source, "format-patch", "--stdout",
                                       "--no-signature", "--full-index", "-1", commit))
        entries.append({"commit": commit, "patch": name,
                        "subject": git(source, "show", "-s", "--format=%s", commit,
                                       text=True).strip()})
    report = {"doged": doged, "abc": abc, "common_ancestor": ancestor,
              "equivalent_commits_excluded": len(cherry) - len(commits),
              "unmatched_commits": entries, "application": "not attempted",
              "build": "not attempted", "behavior": "not attempted",
              "caution": "Unmatched commits are not necessarily Dogecoin-specific."}
    if args.apply:
        candidate = args.output / "candidate"
        subprocess.run(["git", "clone", "--no-hardlinks", "--no-checkout",
                        str(source), str(candidate)], check=True)
        subprocess.run(["git", "-C", str(candidate), "checkout", "--detach", abc], check=True)
        paths = [str((patches / item["patch"]).resolve()) for item in entries]
        with (args.output / "git-am.log").open("wb") as log:
            result = subprocess.run(["git", "-C", str(candidate), "am", "--3way", "--keep-non-patch", "--keep-cr",
                                     "--committer-date-is-author-date", *paths],
                                    stdout=log, stderr=subprocess.STDOUT)
        report["application"] = "passed" if result.returncode == 0 else "failed; see git-am.log"
        report["applied_commits"] = int(git(candidate, "rev-list", "--count",
                                            f"{abc}..HEAD", text=True))
        report["conflicted_paths"] = git(candidate, "diff", "--name-only",
                                          "--diff-filter=U", text=True).splitlines()
        report["candidate_head"] = git(candidate, "rev-parse", "HEAD", text=True).strip()
    (args.output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(args.output / "report.json")
    return 1 if report["application"].startswith("failed") else 0


if __name__ == "__main__":
    raise SystemExit(main())
