#!/usr/bin/env python3
"""Compile and exercise each native owner requiring a C4 executor adapter.

Run only when root grants the isolated host slot. Never modifies source or refs;
temporary detached checkouts are restored even after a failed gate.
"""
import argparse
import fcntl
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
SOURCE = ROOT / "daemon/worktrees/grok-progression-source"
BUILD = ROOT / "daemon/.local-artifact-archive/grok-progression-build"
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--plan", default="COMMIT4-PREFIX-GATE-PLAN.json")
parser.add_argument("--output-name", default="atomic-c4-native-prefix-gates")
parser.add_argument("--compiler-launcher", type=Path)
args = parser.parse_args()
assert Path(args.plan).name == args.plan
assert Path(args.output_name).name == args.output_name
DATA = ROOT / "benchmark-results/20261023" / args.output_name
configure_extra = []
if args.compiler_launcher:
    args.compiler_launcher = args.compiler_launcher.resolve(strict=True)
    assert args.compiler_launcher.is_file()
    configure_extra = ["-DCMAKE_C_COMPILER_LAUNCHER=" + str(args.compiler_launcher),
                       "-DCMAKE_CXX_COMPILER_LAUNCHER=" + str(args.compiler_launcher)]
spec = importlib.util.spec_from_file_location("audit", ROOT / "daemon/bench/commit-regressions/run.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def git(*args):
    return subprocess.check_output(["git", "-C", str(SOURCE), *args], text=True).strip()


def run(args, log, cwd=None):
    with log.open("w") as stream:
        subprocess.run(list(map(str, args)), stdout=stream, stderr=subprocess.STDOUT,
                       cwd=cwd, check=True)


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


with (SOURCE / ".git/progression.lock").open("a") as source_lock, \
        (ROOT / "daemon/.local-artifact-archive/benchmark-host.lock").open("a") as host_lock:
    for lock in (source_lock, host_lock):
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    plan = json.loads((OUT / args.plan).read_text())
    assert not DATA.exists(), "Retain prior attempt; select a new evidence directory before retry"
    assert not git("status", "--porcelain", "--untracked-files=no")
    assert git("rev-parse", "HEAD") == plan["endpoint"]
    assert git("rev-parse", "HEAD^{tree}") == plan["endpoint_tree"]
    branch = git("symbolic-ref", "--short", "HEAD")
    DATA.mkdir(parents=True)
    results = []
    try:
        for prefix in plan["prefixes"]:
            point = DATA / str(prefix["native_position"])
            point.mkdir()
            print("PREFIX", prefix["native_position"], prefix["commit"], flush=True)
            subprocess.run(["git", "-C", str(SOURCE), "switch", "--detach", prefix["commit"]], check=True)
            assert git("rev-parse", "HEAD^{tree}") == prefix["tree"]
            run(["cmake", "-GNinja", "-S", SOURCE, "-B", BUILD, *audit.FLAGS,
                 *configure_extra], point / "configure.log")
            run(["ninja", "-C", BUILD, "-j10", "-k0", "lotusd", "lotus-cli", "test_bitcoin"], point / "build.log")
            runtime = point / "unit-runtime"
            runtime.mkdir()
            binary = BUILD / "src/test/test_bitcoin"
            run([binary, "--run_test=util_tests,validation_tests,mempool_admission_tests,txvalidationcache_tests,txrelay_tests",
                 "--log_level=test_suite", "--report_level=short"], point / "targeted-units.log", runtime)
            assert not git("status", "--porcelain", "--untracked-files=no")
            result = dict(prefix, status="PASS", binary_sha256=sha(binary),
                          daemon_sha256=sha(BUILD / "src/lotusd"), flags=audit.FLAGS)
            result["configure_extra"] = configure_extra
            if args.compiler_launcher:
                result["compiler_launcher_sha256"] = sha(args.compiler_launcher)
            (point / "PASS.json").write_text(json.dumps(result, indent=2) + "\n")
            results.append(result)
    finally:
        # Refuse to overwrite unexpected source changes while restoring.
        assert not git("status", "--porcelain", "--untracked-files=no")
        subprocess.run(["git", "-C", str(SOURCE), "switch", branch], check=True)
        assert git("rev-parse", "HEAD") == plan["endpoint"]
        (DATA / "STATE.json").write_text(json.dumps(dict(passed=results,
            endpoint_restored=plan["endpoint"], complete=len(results) == len(plan["prefixes"])), indent=2) + "\n")
    print("ALL PREFIXES PASS; ENDPOINT SOURCE RESTORED; build binary remains last prefix", flush=True)
