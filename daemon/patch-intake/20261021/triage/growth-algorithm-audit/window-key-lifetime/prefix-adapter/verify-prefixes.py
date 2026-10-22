#!/usr/bin/env python3
"""Verify every transformed tree and normal downstream diff replay in private indices."""
import argparse
import csv
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument("--repo", required=True)
parser.add_argument("--owner", default="c1828a84aa3fcb18ff37f489bd5d90e2665ca6d7")
parser.add_argument("--tip", default="2cf83331db74d3d13c6945fcce9fb99f12027339")
parser.add_argument("--endpoint", default="2995b4b215")
args = parser.parse_args()
here = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("adapter", here / "transform.py")
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)

def git(*argv, data=None, env=None):
    return subprocess.check_output(["git", "-C", args.repo, *argv], input=data, env=env)

def rev(ref):
    return git("rev-parse", ref).decode().strip()

commits = git("rev-list", "--first-parent", "--reverse", args.owner + "^.." + args.tip).decode().splitlines()
assert commits and commits[0] == rev(args.owner)
previous_old = rev(args.owner + "^")
previous_new_tree = rev(previous_old + "^{tree}")
rows = []
with tempfile.TemporaryDirectory(prefix="lotus-window-lifetime-indices-") as tmp:
    direct_env = dict(os.environ, GIT_INDEX_FILE=str(Path(tmp) / "direct.index"))
    replay_env = dict(os.environ, GIT_INDEX_FILE=str(Path(tmp) / "replay.index"))
    for commit in commits:
        parents = git("show", "-s", "--format=%P", commit).decode().strip().split()
        assert parents == [previous_old], (commit, parents, previous_old)
        old_tree = rev(commit + "^{tree}")
        old = git("show", commit + ":" + adapter.PATH)
        changed = adapter.transform({adapter.PATH: old})[adapter.PATH]
        assert changed != old
        assert adapter.transform({adapter.PATH: changed})[adapter.PATH] == changed
        blob = git("hash-object", "-w", "--stdin", data=changed).decode().strip()
        git("read-tree", old_tree, env=direct_env)
        git("update-index", "--cacheinfo", "100644," + blob + "," + adapter.PATH, env=direct_env)
        mapped_tree = git("write-tree", env=direct_env).decode().strip()
        # Apply the original whole-purpose diff to the preceding repaired tree.
        # The owner enters unmodified, then its local transform is applied once;
        # later diffs must preserve it without ad-hoc downstream adaptations.
        git("read-tree", previous_new_tree, env=replay_env)
        diff = git("diff", "--binary", "--no-ext-diff", previous_old, commit)
        git("apply", "--cached", "--check", "--whitespace=nowarn", "-", data=diff, env=replay_env)
        git("apply", "--cached", "--whitespace=nowarn", "-", data=diff, env=replay_env)
        staged = git("show", ":" + adapter.PATH, env=replay_env)
        staged = adapter.transform({adapter.PATH: staged})[adapter.PATH]
        staged_blob = git("hash-object", "-w", "--stdin", data=staged).decode().strip()
        git("update-index", "--cacheinfo", "100644," + staged_blob + "," + adapter.PATH, env=replay_env)
        replay_tree = git("write-tree", env=replay_env).decode().strip()
        assert replay_tree == mapped_tree, (commit, replay_tree, mapped_tree)
        ordinal = int(git("rev-list", "--count", "base/abc.." + commit))
        rows.append(dict(ordinal=ordinal, commit=commit, old_tree=old_tree,
                         repaired_tree=mapped_tree, header_blob=blob,
                         idempotent=True, downstream_diff_replay_equal=True))
        previous_old, previous_new_tree = commit, mapped_tree
endpoint = rev(args.endpoint + "^{tree}")
assert previous_new_tree == endpoint, (previous_new_tree, endpoint)
(here / "prefix-ledger.json").write_text(json.dumps(rows, indent=2) + "\n")
with (here / "prefix-map.csv").open("w") as file:
    writer = csv.DictWriter(file, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)
summary = dict(status="PASS_SOURCE_TRANSFORM_AND_EVERY_INTERMEDIATE_TREE", prefixes=len(rows),
               first_ordinal=rows[0]["ordinal"], last_ordinal=rows[-1]["ordinal"],
               owner=rev(args.owner), tip=rev(args.tip), endpoint_commit=rev(args.endpoint),
               endpoint_tree=endpoint, source_only=True, builds_or_runtimes=False,
               method="Pure idempotent one-header transform; independent full-tree mapping equals original downstream diff replay in private indices at every prefix")
(here / "RESULT.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary))
