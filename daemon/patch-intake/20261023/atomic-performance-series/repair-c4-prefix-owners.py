#!/usr/bin/env python3
"""Relocate exact prerequisites to their causal native owners, tree-exact."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
SOURCE = ROOT / "daemon/worktrees/grok-progression-source"
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--plan", default="C4-PREFIX-REPAIR-PLAN.json")
parser.add_argument("--state", default="C4-PREFIX-REPAIR-STATE.json")
parser.add_argument("--branch", default="consolidation/native-c4-prefix-owners-20261023")
args = parser.parse_args()
assert Path(args.plan).name == args.plan
assert Path(args.state).name == args.state
STATE = OUT / args.state
ENV = dict(os.environ, GIT_SEQUENCE_EDITOR="true",
           GIT_COMMITTER_EMAIL="213740+schancel@users.noreply.github.com")


def git(*args):
    return subprocess.check_output(["git", "-C", str(SOURCE), *args], text=True).strip()


def run(*args):
    with (OUT / "C4-PREFIX-REPAIR-GIT.log").open("a") as log:
        return subprocess.run(["git", "-C", str(SOURCE), *args], env=ENV,
                              stdout=log, stderr=subprocess.STDOUT)


def original(commit):
    return subprocess.check_output(["git", "-C", str(SOURCE), "show",
                                   commit + ":" + source_file], text=True)


def projected(commit, position):
    text = original(commit)
    if plan.get("repair_profile") == "daemon-development-source":
        if 32 <= position <= 58:
            anchor = "add_executable(lotusd bitcoind.cpp)"
            assert text.count(anchor) == 1
            text = text.replace(anchor,
                "add_executable(lotusd bitcoind.cpp lotus_v2/development_command.cpp)", 1)
        return text
    if plan.get("repair_profile") == "api-followup":
        if 32 <= position <= 49:
            assert "#include <rpc/async_waiter.h>" not in text
            anchor = "#include <reverse_iterator.h>\n"
            assert text.count(anchor) == 1
            text = text.replace(anchor, anchor + "#include <rpc/async_waiter.h>\n", 1)
        if 32 <= position <= 43:
            anchor = "std::make_unique<StakingRewardsPolicy>(\n                            *avalanche, consensusParams, *pindexNew,\n                            blockConnecting))"
            assert text.count(anchor) == 1
            text = text.replace(anchor, anchor.replace("blockConnecting))", "blockConnecting, blockSubsidy))"), 1)
        if 32 <= position <= 45:
            anchor = "std::make_unique<PreConsensusPolicy>(\n                                *avalanche, *pindexNew, blockConnecting))"
            assert text.count(anchor) == 1
            text = text.replace(anchor, anchor.replace("blockConnecting))", "blockConnecting,\n                                m_mempool, &disconnectpool))"), 1)
        return text
    if 32 <= position <= 40:
        assert "#include <lotus_v2/fee_hysteresis.h>" not in text
        anchor = "#include <lotus_v2/fast_sync.h>\n"
        assert text.count(anchor) == 1
        text = text.replace(anchor, anchor + "#include <lotus_v2/fee_hysteresis.h>\n", 1)
    if 32 <= position <= 39:
        anchor = "    return m_cached_snapshot_base;\n\nvoid Chainstate::InitCoinsDB"
        assert text.count(anchor) == 1
        text = text.replace(anchor, "    return m_cached_snapshot_base;\n}\n\nvoid Chainstate::InitCoinsDB", 1)
    return text


with (SOURCE / ".git/progression.lock").open("a") as lock:
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    plan = json.loads((OUT / args.plan).read_text())
    source_file = plan.get("file", "src/validation.cpp")
    assert source_file in ("src/validation.cpp", "src/CMakeLists.txt")
    assert not git("status", "--porcelain", "--untracked-files=no")
    commits = git("rev-list", "--reverse", plan["shared"] + ".." + plan["input_native"]).splitlines()
    assert len(commits) == 154
    if STATE.exists():
        state = json.loads(STATE.read_text())
        assert state["status"] == "running"
        assert git("rev-parse", "HEAD") == state["head"]
    else:
        assert git("rev-parse", "HEAD") == plan["input_native"]
        assert run("switch", "-c", args.branch, plan["shared"]).returncode == 0
        state = dict(status="running", index=0, head=plan["shared"], mapping=[])
        STATE.write_text(json.dumps(state, indent=2) + "\n")
    for index in range(state["index"], len(commits)):
        old = commits[index]
        position = index + 1
        target = projected(old, position)
        result = run("cherry-pick", old)
        if result.returncode:
            conflicts = git("diff", "--name-only", "--diff-filter=U").splitlines()
            assert conflicts == [source_file], conflicts
            (SOURCE / source_file).write_text(target)
            assert run("add", source_file).returncode == 0
            assert run("cherry-pick", "--continue").returncode == 0
        if (SOURCE / source_file).read_text() != target:
            # Only the introducing owner needs an explicit prerequisite edit.
            assert position == 32
            (SOURCE / source_file).write_text(target)
            assert run("add", source_file).returncode == 0
            owner = git("rev-parse", "HEAD")
            assert run("-c", "user.email=213740+schancel@users.noreply.github.com",
                       "commit", "--fixup", owner).returncode == 0
            assert run("-c", "rebase.updateRefs=false", "rebase", "-i", "--autosquash",
                       "--no-update-refs", "HEAD~2").returncode == 0
        assert (SOURCE / source_file).read_text() == target
        new = git("rev-parse", "HEAD")
        changed = git("diff", "--name-only", old, new).splitlines()
        expected = [source_file] if target != original(old) else []
        assert changed == expected, (position, changed)
        assert git("show", "-s", "--format=%s", old) == git("show", "-s", "--format=%s", new)
        state["mapping"].append(dict(position=position, old=old, new=new,
                                     tree=git("rev-parse", "HEAD^{tree}"), differences=changed))
        state.update(index=position, head=new)
        STATE.write_text(json.dumps(state, indent=2) + "\n")
    assert git("rev-parse", "HEAD^{tree}") == plan["input_tree"]
    state["status"] = "Exact final tree and all154 per-owner projections PASS; compile/runtime gates pending"
    STATE.write_text(json.dumps(state, indent=2) + "\n")
    print(state["status"], state["head"], flush=True)
