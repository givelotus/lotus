#!/usr/bin/env python3
"""Produce a review inventory, never an automatic commit exclusion list."""
import argparse
import collections
import csv
import json
from pathlib import Path
import subprocess


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True)


def category(subject, paths):
    text = subject.lower()
    if any(word in text for word in ("avalanche", "staking", "rtt", "stake contender")):
        return "avalanche-policy"
    if "chronik" in text or any(path.startswith("chronik/") for path in paths):
        return "chronik"
    if any(word in text for word in ("auxpow", "scrypt", "digishield", " daa", "subsidy", "coinbase", "bip", "max_money", "sigops", "script execution", "script vm", "script flags", "sighash_forkid", "legacy mode", "blockheader", "baseheader", "block header", "chain id")):
        return "dogecoin-consensus-serialization"
    if any(word in text for word in ("wallet", "sendtoaddress", "signrawtransaction", "signmessage", "address", "private keys", "extended keys", "fees", "feerate")):
        return "wallet-sdk"
    if any(word in text for word in ("seed", "checkpoint", "ports", "port ", "magic", "datadir", "user agent", "rebrand", "rename", "doge and", "ticker", "logos", "dogecoin in")):
        return "network-identity"
    if all(not path.startswith(("src/", "test/", "chronik/", "cmake/", "contrib/", "depends/")) and path not in ("CMakeLists.txt", "Cargo.toml", "Cargo.lock", "PackageOptions.cmake") for path in paths):
        return "applications-docs"
    if any(path.startswith("src/avalanche/") for path in paths):
        return "avalanche-policy"
    return "build-tests-upstream-infrastructure"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--candidate-report", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    report = json.loads(args.candidate_report.read_text())
    counterparts = {}
    for line in git(args.source, "log", "--format=%H%x09%s", report["abc"]).splitlines():
        commit, subject = line.split("\t", 1)
        counterparts.setdefault(subject, commit)
    counts = collections.Counter()
    with args.output.open("w", newline="") as output:
        writer = csv.writer(output, delimiter="\t", lineterminator="\n")
        writer.writerow(("original_commit", "review_category", "abc_same_subject_counterpart", "review_disposition", "subject", "paths"))
        for entry in report["unmatched_commits"]:
            commit, subject = entry["commit"], entry["subject"]
            paths = git(args.source, "diff-tree", "--no-commit-id", "--name-only", "-r", commit).splitlines()
            domain = category(subject, paths)
            counterpart = counterparts.get(subject, "")
            disposition = "review-derived-delta" if counterpart else "review-port"
            if commit.startswith(("3e443c33fb", "e43f0aea5c")):
                disposition = "superseded-test-skip-or-formatting"
            elif "bump" in subject.lower() and "version" in subject.lower():
                disposition = "consolidate-historical-version"
            elif domain == "applications-docs":
                disposition = "exclude-from-minimal-daemon-port-review-separately"
            counts[(domain, disposition)] += 1
            writer.writerow((commit, domain, counterpart, disposition, subject, ";".join(paths)))
    print(json.dumps({"abc": report["abc"], "doged": report["doged"],
                      "total": sum(counts.values()),
                      "category_and_disposition_counts": {" / ".join(k): v for k, v in sorted(counts.items())},
                      "warning": "Heuristic review inventory. Same subjects do not establish semantic equivalence; no commits are automatically excluded."}, indent=2))


if __name__ == "__main__":
    main()
