#!/usr/bin/env python3
"""Isolated normal Chronik-ON build/unit gate; run only with the serial compiler lease."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

here = Path(__file__).resolve().parent
plan = json.loads((here / "PLAN.json").read_text())
source = Path(plan["source"])
build = Path(plan["build"])
results = dict(plan, status="RUNNING", stages=[])

def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def save():
    (here / "RESULT.json").write_text(json.dumps(results, indent=2) + "\n")

def run(name, command):
    actual = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip()
    if actual != plan["source_sha"]:
        raise RuntimeError("source changed before " + name + ": " + actual)
    stage = dict(name=name, command=command, started=now(), log=name + ".log")
    results["stages"].append(stage)
    save()
    print("START", name, flush=True)
    with (here / stage["log"]).open("w") as log:
        done = subprocess.run(command, cwd=source, stdout=log, stderr=subprocess.STDOUT)
    stage.update(finished=now(), exit=done.returncode)
    save()
    print("END", name, done.returncode, flush=True)
    if done.returncode:
        results["status"] = "FAILED_" + name
        save()
        sys.exit(done.returncode)

results.update(started=now(), pid=os.getpid(), compiler_lease="N1 direct drain explicitly granted")
save()
run("configure", ["cmake", "-S", str(source), "-B", str(build), "-G", "Ninja",
    "-DCMAKE_BUILD_TYPE=Release", "-DCMAKE_CXX_FLAGS_RELEASE=-O3", "-DCMAKE_C_FLAGS_RELEASE=-O3",
    "-DBUILD_CHRONIK=ON", "-DCHRONIK_IMPLEMENTATION=native", "-DBUILD_CHRONIK_PLUGINS=OFF",
    "-DCHRONIK_NATIVE_MDBX=ON", "-DCHRONIK_NATIVE_LEVELDB=OFF", "-DBUILD_WALLET=ON",
    "-DUSE_JEMALLOC=ON", "-DPython_EXECUTABLE=/opt/homebrew/bin/python3.13"])
cache = build / "CMakeCache.txt"
text = cache.read_text()
for expected in ("BUILD_CHRONIK:BOOL=ON", "CHRONIK_IMPLEMENTATION:STRING=native",
                 "BUILD_CHRONIK_PLUGINS:BOOL=OFF", "USE_JEMALLOC:BOOL=ON"):
    if expected not in text:
        raise RuntimeError("configuration did not retain required profile: " + expected)
results["cmake_cache_sha256"] = hashlib.sha256(cache.read_bytes()).hexdigest()
save()
run("normal-build", ["cmake", "--build", str(build), "--target", *plan["normal_targets"], "-j10"])
run("version", [str(build / "src/lotusd"), "--version"])
for suite in ("mempool_overlay_tests", "rpc_snapshot_read_tests", "lotus_v2_tests"):
    run(suite, [str(build / "src/test/test_bitcoin"), "--run_test=" + suite, "--report_level=detailed"])
run("block-assembler", [str(build / "src/lotus_v2/test_lotus_v2_block_assembler")])
run("preconsensus_batch_tests", [str(build / "src/avalanche/test/test-avalanche"),
    "--run_test=preconsensus_batch_tests", "--report_level=detailed"])
results.update(status="PASS_NORMAL_CHRONIK_ON_BUILD_AND_FOCUSED_TESTS", finished=now())
save()
print(results["status"], flush=True)
