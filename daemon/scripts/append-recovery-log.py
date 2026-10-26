#!/usr/bin/env python3
"""Append a durable, process-serialized recovery entry; never rewrite the log."""
import argparse
from datetime import datetime, timezone
import fcntl
import os
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--agent', required=True)
    parser.add_argument('--log', type=Path, default=Path(__file__).resolve().parents[2]
                        / 'daemon/patch-audit/progression/RECOVERY-APPEND.md')
    args = parser.parse_args()
    message = sys.stdin.read()
    if not message.strip():
        parser.error('Supply a checkpoint on stdin')
    args.log.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).isoformat(timespec='seconds')
    payload = f'\n## {timestamp} — {args.agent}\n\n{message.rstrip()}\n'.encode()
    fd = os.open(args.log, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        remaining = memoryview(payload)
        while remaining:
            count = os.write(fd, remaining)
            if count <= 0:
                raise OSError('Recovery append made no progress')
            remaining = remaining[count:]
        os.fsync(fd)
    finally:
        os.close(fd)
    directory = os.open(args.log.parent, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)
    print(args.log)


if __name__ == '__main__':
    main()
