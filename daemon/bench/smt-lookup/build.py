#!/usr/bin/env python3
"""Compile one driver and link a variant's frozen production archive closure.

No source checkout mutations. Requires an explicit compilation authorization.
Use the recorded Ninja commands, not a rewritten model of the SMT algorithm.
"""
import argparse
import fcntl
import hashlib
import json
from pathlib import Path
import shlex
import subprocess


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def compiler_args(command):
    args = shlex.split(command)
    if "&&" in args:
        args = args[args.index("&&") + 1:]
    if "&&" in args:
        args = args[:args.index("&&")]
    return args


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--frozen", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("--approve-compilation", action="store_true")
parser.add_argument("--plan-only", action="store_true")
args = parser.parse_args()
if not args.approve_compilation and not args.plan_only:
    parser.error("root must grant the isolated compilation slot first")
frozen = args.frozen.resolve()
output = args.output.resolve()
assert not output.exists(), "Preserve prior artifacts; select a new output directory"
output.mkdir(parents=True)
commands = json.loads((frozen / "COMMANDS.json").read_text())
receipt = json.loads((frozen / "PRESERVATION.json").read_text())
for entry in receipt["files"]:
    assert sha(frozen / entry["path"]) == entry["sha256"], entry["path"]
for entry in receipt["external_libraries"]:
    assert sha(Path(entry["path"])) == entry["sha256"], entry["path"]
driver = Path(__file__).with_name("lookup.cpp").resolve()
compile_args = compiler_args(commands["smt_compile"])
filtered = []
i = 0
while i < len(compile_args):
    if compile_args[i] in {"-MT", "-MF", "-o", "-c"}:
        i += 2
    elif compile_args[i] == "-MD":
        i += 1
    else:
        filtered.append(compile_args[i])
        i += 1
compile_cmd = [*filtered, "-o", str(output / "lookup.o"), "-c", str(driver)]
link_args = compiler_args(commands["unit_link"])
link_cmd = []
inserted_driver = False
i = 0
original_build = Path(receipt["original_build"])
root = Path(__file__).resolve().parents[3]
original_build = root / original_build
while i < len(link_args):
    value = link_args[i]
    if value.endswith(".o"):
        if not inserted_driver:
            link_cmd.append(str(output / "lookup.o"))
            inserted_driver = True
    elif value == "-o":
        link_cmd.extend([value, str(output / "lookup")])
        i += 1
    elif value.endswith((".a", ".dylib")) and not Path(value).is_absolute():
        path = frozen / value
        assert path.is_file(), path
        link_cmd.append(str(path))
    else:
        link_cmd.append(value.replace(str(original_build / "src"), str(frozen / "src")))
    i += 1
assert inserted_driver
(output / "COMMANDS.json").write_text(json.dumps(dict(compile=compile_cmd, link=link_cmd), indent=2) + "\n")
if args.plan_only:
    (output / "PLAN.json").write_text(json.dumps(dict(status="Prepared only; no compilation or timing",
        frozen=str(frozen), driver_sha256=sha(driver),
        preservation_sha256=sha(frozen / "PRESERVATION.json")), indent=2) + "\n")
    raise SystemExit(0)
lock_path = Path.home() / "repos/archive/builds/lotus-bench/benchmark-host.lock"
lock_path.parent.mkdir(parents=True, exist_ok=True)
with lock_path.open("a") as lock:
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    for name, command in [("compile", compile_cmd), ("link", link_cmd)]:
        with (output / (name + ".log")).open("w") as stream:
            subprocess.run(command, cwd=original_build, stdout=stream, stderr=subprocess.STDOUT, check=True)
(output / "BUILD.json").write_text(json.dumps(dict(
    status="Compiled; not timed", frozen=str(frozen), source_sha256=sha(driver),
    object_sha256=sha(output / "lookup.o"), binary_sha256=sha(output / "lookup"),
    preservation_sha256=sha(frozen / "PRESERVATION.json"),
    smt_library_sha256=sha(frozen / "src/lotus_v2/liblotus_v2_header.a"),
    source_commit=receipt["source_commit"], source_tree=receipt["source_tree"]), indent=2) + "\n")
