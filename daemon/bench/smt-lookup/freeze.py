#!/usr/bin/env python3
"""Freeze existing gated binaries, cache and production link inputs. No build."""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import shutil
import subprocess


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--build", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("--source-commit", required=True)
parser.add_argument("--source-tree", required=True)
parser.add_argument("--gate-receipt", type=Path, required=True)
args = parser.parse_args()
root = Path(__file__).resolve().parents[3]
build, output = args.build.resolve(), args.output.resolve()
assert not output.exists(), "Never overwrite a frozen variant"
gate = json.loads(args.gate_receipt.read_text())
expected = gate["binary"]
for rel, key in [("src/lotusd", "daemon_sha256"), ("src/lotus-cli", "cli_sha256"),
                 ("src/test/test_bitcoin", "test_sha256"), ("CMakeCache.txt", "cmake_cache_sha256")]:
    assert sha(build / rel) == expected[key], rel
paths = [build / name for name in ["src/lotusd", "src/lotus-cli", "src/test/test_bitcoin",
    "CMakeCache.txt", "build.ninja", "CMakeFiles/rules.ninja",
    "src/lotus_v2/CMakeFiles/lotus_v2_header.dir/mempool_overlay.cpp.o"]]
paths.extend((build / "src").rglob("*.a"))
paths.extend((build / "src").rglob("*.dylib"))
output.mkdir(parents=True)
files = []
for path in sorted(set(paths)):
    if not path.is_file():
        continue
    relative = path.relative_to(build)
    target = output / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, target)
    assert sha(path) == sha(target)
    files.append(dict(path=str(relative), sha256=sha(target), bytes=target.stat().st_size))
commands = {}
for label, target in [("smt_compile", "src/lotus_v2/CMakeFiles/lotus_v2_header.dir/mempool_overlay.cpp.o"),
                      ("unit_link", "src/test/test_bitcoin"), ("daemon_link", "src/lotusd")]:
    commands[label] = subprocess.check_output(["ninja", "-C", str(build), "-t", "commands", target], text=True).splitlines()[-1]
(output / "COMMANDS.json").write_text(json.dumps(commands, indent=2) + "\n")
external = {}
for value in shlex.split(commands["unit_link"]):
    path = Path(value)
    if path.is_absolute() and path.is_file() and path.suffix in {".a", ".dylib"}:
        external[str(path)] = dict(path=str(path), sha256=sha(path), bytes=path.stat().st_size)
receipt = dict(status="Frozen existing gated artifacts; no build/timing", source_commit=args.source_commit,
    source_tree=args.source_tree, gate_receipt=str(args.gate_receipt.resolve()),
    gate_receipt_sha256=sha(args.gate_receipt), original_build=str(build.relative_to(root)),
    frozen_build=str(output.relative_to(root)), files=files, external_libraries=list(external.values()),
    commands_sha256=sha(output / "COMMANDS.json"), retained_original=True,
    runtime_note="Copied original test binary retains old rpath; use frozen/src in DYLD_LIBRARY_PATH. Micro build rewrites its own rpath to this frozen variant.")
(output / "PRESERVATION.json").write_text(json.dumps(receipt, indent=2) + "\n")
