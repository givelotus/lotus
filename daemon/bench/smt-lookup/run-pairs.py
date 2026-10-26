#!/usr/bin/env python3
"""Run isolated alternating pairs; report only validated SMT lookups/second."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import statistics
import subprocess
import time


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--before", type=Path, required=True)
parser.add_argument("--after", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("--config", type=Path, default=Path(__file__).with_name("config.json"))
parser.add_argument("--approve-timing", action="store_true")
args = parser.parse_args()
if not args.approve_timing:
    parser.error("root must grant the isolated timing window first")
root = Path(__file__).resolve().parents[3]
config = json.loads(args.config.read_text())
assert config["seconds_per_variant"] >= 5 and config["alternating_pairs"] >= 3
output = args.output.resolve()
assert not output.exists(), "Keep prior attempts; choose a fresh output directory"
before, after = args.before.resolve(), args.after.resolve()
lock_path = Path.home() / "repos/archive/builds/lotus-bench/benchmark-host.lock"
lock_path.parent.mkdir(parents=True, exist_ok=True)
with lock_path.open("a") as lock:
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    # Root also coordinates other agents: this guard catches accidentally
    # overlapping compiler/build processes before each process invocation.
    def check_no_builds():
        processes = subprocess.check_output(["ps", "-axo", "pid=,comm="], text=True)
        for row in processes.splitlines():
            parts = row.strip().split(maxsplit=1)
            if len(parts) == 2 and Path(parts[1]).name in {"ninja", "make", "cmake", "clang", "clang++", "cc1", "cc1plus"}:
                raise RuntimeError("build process overlaps timing: " + row)
    check_no_builds()
    output.mkdir(parents=True)
    binaries = {"before": before, "after": after}
    builds = {label: json.loads(path.with_name("BUILD.json").read_text()) for label, path in binaries.items()}
    assert len({value["source_sha256"] for value in builds.values()}) == 1
    assert len({value["object_sha256"] for value in builds.values()}) == 1, "driver objects differ"
    hashes = {label: sha(path) for label, path in binaries.items()}
    for label, build in builds.items():
        assert build["binary_sha256"] == hashes[label]
    def check_libraries():
        for build in builds.values():
            frozen = Path(build["frozen"])
            receipt = json.loads((frozen / "PRESERVATION.json").read_text())
            for entry in receipt["external_libraries"]:
                assert sha(Path(entry["path"])) == entry["sha256"], entry["path"]
    check_libraries()
    rows = []
    complete = False
    try:
        for pair in range(config["alternating_pairs"]):
            cases = config["cases"][pair % len(config["cases"]):] + config["cases"][:pair % len(config["cases"])]
            for case in cases:
                labels = ["before", "after"] if pair % 2 == 0 else ["after", "before"]
                for label in labels:
                    check_no_builds()
                    check_libraries()
                    assert sha(binaries[label]) == hashes[label]
                    name = f"pair-{pair + 1}-{case['mode']}-t{case['threads']}-{label}"
                    command = [str(binaries[label]), str(config["coins"]), str(config["queries"]),
                               str(case["threads"]), str(config["seconds_per_variant"]), case["mode"]]
                    started = time.time()
                    with (output / (name + ".json")).open("w") as stdout, (output / (name + ".stderr")).open("w") as stderr:
                        subprocess.run(command, stdout=stdout, stderr=stderr, check=True, timeout=config["seconds_per_variant"] + 180)
                    result = json.loads((output / (name + ".json")).read_text())
                    assert result["errors"] == 0 and result["seconds"] >= 5
                    assert (result["coins"], result["queries"], result["threads"], result["mode"]) == (
                        config["coins"], config["queries"], case["threads"], case["mode"])
                    rows.append(dict(pair=pair + 1, variant=label, binary_sha256=hashes[label],
                                     started_unix=started, finished_unix=time.time(), load=os.getloadavg(), **result))
                    check_no_builds()
                    check_libraries()
                    (output / "STATE.json").write_text(json.dumps(dict(completed_processes=rows,
                        scope=config["scope"], binary_hashes=hashes, complete=False,
                        performance_publishable=False), indent=2) + "\n")
                    print(json.dumps(dict(status="partial trial; comparison incomplete",
                        pair=pair + 1, variant=label, mode=case["mode"], threads=case["threads"],
                        seconds=result["seconds"], lookups_per_second=result["lookups_per_second"])), flush=True)
        assert len({row["root"] for row in rows}) == 1, "variants built different trees"
        summary = []
        for case in config["cases"]:
            selected = [row for row in rows if row["mode"] == case["mode"] and row["threads"] == case["threads"]]
            values = {label: [row["lookups_per_second"] for row in selected if row["variant"] == label] for label in binaries}
            assert all(len(v) == config["alternating_pairs"] for v in values.values())
            ratio = statistics.median(values["after"]) / statistics.median(values["before"])
            paired_ratios = []
            for pair in range(1, config["alternating_pairs"] + 1):
                paired = {row["variant"]: row["lookups_per_second"] for row in selected if row["pair"] == pair}
                paired_ratios.append(paired["after"] / paired["before"])
            summary.append(dict(case, before_median=statistics.median(values["before"]),
                                after_median=statistics.median(values["after"]), after_before=ratio,
                                paired_ratios=paired_ratios, median_paired_ratio=statistics.median(paired_ratios)))
        (output / "SUMMARY.json").write_text(json.dumps(dict(status="PASS", scope=config["scope"],
            unit="validated SMT lookups/second", summary=summary, rows=rows,
            config=config, builds=builds, binary_hashes=hashes, config_sha256=sha(args.config)), indent=2) + "\n")
        complete = True
    finally:
        (output / "STATE.json").write_text(json.dumps(dict(completed_processes=rows,
            scope=config["scope"], binary_hashes=hashes, complete=complete,
            performance_publishable=complete), indent=2) + "\n")
