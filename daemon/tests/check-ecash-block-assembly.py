#!/usr/bin/env python3
"""Characterize historical, superseded ecash/01 using its real C++ logic.

Exit zero means the documented failures were reproduced, NOT that the patch
is safe. This is a dependency-free algorithm harness, not a node/miner test.
"""
import argparse
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile


def new_side(patch, filename):
    """Read new-side text from unified hunks (unchanged gaps are not needed)."""
    active = False
    in_hunk = False
    lines = []
    for line in patch.splitlines(keepends=True):
        if line.startswith("diff --git "):
            active = line.rstrip().endswith(" b/" + filename)
            in_hunk = False
        elif active and line.startswith("@@ "):
            in_hunk = True
        elif active and in_hunk and line[:1] in ("+", " "):
            lines.append(line[1:])
    return "".join(lines)


def brace_block(text, start):
    begin = text.index(start)
    opening = text.index("{", begin)
    depth = 0
    for pos in range(opening, len(text)):
        if text[pos] == "{":
            depth += 1
        elif text[pos] == "}":
            depth -= 1
            if depth == 0:
                return text[begin:pos + 1]
    raise ValueError("Unterminated candidate block")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cxx", default=shutil.which("c++") or "c++")
    parser.add_argument("--source-tree", type=Path,
                        help="Also verify an existing source tree has the same assembly logic")
    parser.add_argument("--patch-file", type=Path,
                        help="Historical assembler patch (for shallow clones without the recorded commit)")
    args = parser.parse_args()
    daemon = Path(__file__).resolve().parents[1]
    if args.patch_file:
        patch_bytes = args.patch_file.read_bytes()
    else:
        # Current 01 uses the corrected heap. Keep the old failure reproducer tied
        # to the historical payload instead of silently testing a replacement.
        try:
            patch_bytes = subprocess.check_output([
                "git", "-C", str(daemon.parent), "show",
                "f67257e2:daemon/patches/ecash/01-nlogn-block-construction.patch"],
                stderr=subprocess.PIPE)
        except subprocess.CalledProcessError:
            parser.error("Historical source unavailable; supply --patch-file from commit f67257e2")
    patch = patch_bytes.decode()
    header = new_side(patch, "src/node/miner.h")
    # The hunk starts immediately after the unchanged tx field; restore just
    # this declaration. All candidate accounting logic is copied verbatim.
    header = "struct CBlockTemplateEntry {\n    CTransactionRef tx;\n" + header
    entry = brace_block(header, "struct CBlockTemplateEntry") + ";"
    method = brace_block(new_side(patch, "src/node/miner.cpp"),
                         "void BlockAssembler::addTxs(")
    if args.source_tree:
        source_header = (args.source_tree / "src/node/miner.h").read_text()
        source_cpp = (args.source_tree / "src/node/miner.cpp").read_text()
        assert brace_block(source_header, "struct CBlockTemplateEntry") + ";" == entry
        assert brace_block(source_cpp, "void BlockAssembler::addTxs(") == method
        print("Source tree has identical candidate accounting and assembly logic:",
              args.source_tree, flush=True)
    template = Path(__file__).with_name("ecash_block_assembly_harness.cpp").read_text()
    source = template.replace("// INSERT_CANDIDATE_ENTRY", entry).replace(
        "// INSERT_CANDIDATE_METHOD", method)
    print("Candidate SHA256:", hashlib.sha256(patch_bytes).hexdigest(), flush=True)
    with tempfile.TemporaryDirectory(prefix="lotus-ecash-assembly-") as temp:
        cpp = Path(temp) / "candidate.cpp"
        exe = Path(temp) / "candidate"
        cpp.write_text(source)
        subprocess.run([args.cxx, "-std=c++17", "-Wall", "-Wextra", "-Werror",
                        "-O1", "-fsanitize=undefined", str(cpp), "-o", str(exe)],
                       check=True)
        subprocess.run([str(exe)], check=True)


if __name__ == "__main__":
    main()
