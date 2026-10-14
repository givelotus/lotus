#!/usr/bin/env python3
"""Compile actual corrected addTxs with adapters and count graph/heap work.

This checks algorithmic operations, not daemon consensus or wall-clock speed.
"""
import argparse
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile


def method(text):
    start = text.index("void BlockAssembler::addTxs(")
    depth = 0
    for position in range(text.index("{", start), len(text)):
        if text[position] == "{":
            depth += 1
        elif text[position] == "}":
            depth -= 1
            if depth == 0:
                return text[start:position + 1]
    raise ValueError("Unterminated addTxs")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-tree", type=Path, required=True)
    parser.add_argument("--cxx", default=shutil.which("c++") or "c++")
    args = parser.parse_args()
    actual = method((args.source_tree / "src/node/miner.cpp").read_text())
    template = Path(__file__).with_name("ready_heap_assembly_harness.cpp").read_text()
    source = template.replace("// INSERT_CANDIDATE_METHOD", actual)
    print("addTxs SHA256:", hashlib.sha256(actual.encode()).hexdigest(), flush=True)
    with tempfile.TemporaryDirectory(prefix="lotus-ready-heap-") as temp:
        cpp, exe = Path(temp) / "candidate.cpp", Path(temp) / "candidate"
        cpp.write_text(source)
        subprocess.run([args.cxx, "-std=c++17", "-Wall", "-Wextra", "-Werror",
                        "-O1", "-fsanitize=undefined", str(cpp), "-o", str(exe)], check=True)
        subprocess.run([str(exe)], check=True)


if __name__ == "__main__":
    main()
