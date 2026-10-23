#!/usr/bin/env python3
"""Summarize native sampling stacks, including blocked time (not CPU shares)."""
import argparse
import collections
import json
from pathlib import Path
import re


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sample', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    text = args.sample.read_text()
    graph = text.split('Call graph:', 1)[1].split('Total number in stack', 1)[0]
    blocks = re.split(r'\n(?=    \d+ Thread_)', graph)
    result = []
    for block in blocks:
        header = re.search(r'^\s*(\d+) (Thread_[^\n]+)', block)
        if not header:
            continue
        frames = []
        for line in block.splitlines():
            match = re.match(r'^([\s+!|:]*)(\d+) (.*?)  \(in ', line)
            if match:
                frames.append(dict(depth=len(match[1]), count=int(match[2]),
                                   symbol=match[3], children=0, ancestors=[]))
        stack = []
        for frame in frames:
            while stack and stack[-1]['depth'] >= frame['depth']:
                stack.pop()
            if stack:
                stack[-1]['children'] += frame['count']
            frame['ancestors'] = [p['symbol'] for p in stack]
            stack.append(frame)
        counts = collections.Counter()
        for frame in frames:
            count = frame['count'] - frame['children']
            assert count >= 0, frame
            symbol = frame['symbol']
            parents = '\n'.join(frame['ancestors'])
            if '__psynch_cvwait' in symbol:
                category = 'condition wait'
            elif '__psynch_mutexwait' in symbol or '__ulock_wait' in symbol:
                category = 'mutex wait'
            elif symbol.startswith(('kevent', '__select', 'read ', 'readv ', 'recv', 'pread')):
                category = 'other syscall/read'
            elif 'CompareTopologically' in parents + symbol:
                category = 'relay topology comparison'
            elif 'secp256k1_' in parents + symbol:
                category = 'curve/signature work'
            elif 'make_heap' in parents + symbol:
                category = 'relay heap other'
            else:
                category = 'other execution'
            counts[category] += count
        total = int(header[1])
        assert sum(counts.values()) == total
        result.append(dict(thread=header[2], samples=total, categories=dict(counts),
                           percent={k: round(100*v/total, 2) for k, v in counts.items()},
                           rpc_worker='thread_pool::thread_function' in block,
                           message_handler='ThreadMessageHandler' in block,
                           signing_worker='SigningWorkerPool' in block))
    assert result
    args.output.write_text(json.dumps(dict(
        scope='Exclusive wall-stack samples, including blocked/idle time; not CPU percentages or throughput attribution',
        threads=result), indent=2)+'\n')


if __name__ == '__main__':
    main()
