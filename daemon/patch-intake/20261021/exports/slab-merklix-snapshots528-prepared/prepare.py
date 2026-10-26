#!/usr/bin/env python3
"""Export only the reviewed feature on corrected527; never promote main patches.

The original halted script reused a proof for a different527 source tree. This
version checks the corrected immutable parent and actually replays the generated
feature mailbox with a private Git index. Prefix validation remains root-owned.
"""
import argparse
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path

D = Path(__file__).resolve().parent
PARENT = "385b64d7e7e0666e2bfff9865ee831a3186795fd"
BASE = "1fb7db17c176cdea8a2c60d887891589382ee4e3"
BRANCH = "review/merklix-slab-snapshot-20261022"
NAME = "154-lotus_v2-slab-backed-persistent-merklix-snapshots-with-lazy-hashing-and-minhash.patch"
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--source", type=Path, required=True)
args = parser.parse_args()
source = args.source.resolve()

def git(*arguments, env=None):
    return subprocess.check_output(["git", "-C", str(source), *arguments], env=env).decode().strip()

head = git("rev-parse", "refs/heads/" + BRANCH)
tree = git("rev-parse", head + "^{tree}")
assert git("rev-parse", head + "^") == PARENT
assert git("rev-list", "--count", BASE + ".." + head) == "528"
assert not git("status", "--porcelain", "--untracked-files=no")
raw = subprocess.check_output(["git", "-C", str(source), "format-patch", "-1",
                               "--stdout", "--full-index", "--binary", head])
out = D / "final-export" / "v2"
out.mkdir(parents=True, exist_ok=True)
mailbox = out / NAME
mailbox.write_bytes(raw)
fd, index = tempfile.mkstemp(prefix="feature-replay-", dir=D)
os.close(fd)
os.unlink(index)
env = dict(os.environ, GIT_INDEX_FILE=index)
try:
    git("read-tree", PARENT, env=env)
    subprocess.run(["git", "-C", str(source), "apply", "--cached", "--binary",
                    "--whitespace=error", "-"], input=raw, env=env, check=True)
    replayed = git("write-tree", env=env)
finally:
    if os.path.exists(index):
        os.unlink(index)
assert replayed == tree
record = {
    "schema": 1, "status": "PASS_FEATURE_MAILBOX_REPLAY_ON_CORRECTED527",
    "source_repo": str(source), "source_branch": BRANCH,
    "head": head, "tree": tree, "parent": PARENT,
    "parent_tree": git("rev-parse", PARENT + "^{tree}"),
    "source_history_count": 528, "feature_count": 1,
    "global_number": 528, "layer_number": 154,
    "stable_contract_id": "slab-merklix-snapshots-20261022",
    "mailbox": str(mailbox.relative_to(D)),
    "mailbox_sha256": hashlib.sha256(raw).hexdigest(),
    "files_changed": git("diff", "--name-only", PARENT, head).splitlines(),
    "replay_tree": replayed,
    "prefix_validation": "Corrected527 parent is root-owned; no original527 proof reused",
    "adoption": "prepared only; active main manifests and patches untouched",
}
(D / "manifest.json").write_text(json.dumps(record, indent=2) + "\n")
(D / "direct-replay-result.json").write_text(json.dumps(record, indent=2) + "\n")
print(json.dumps(record, indent=2))
