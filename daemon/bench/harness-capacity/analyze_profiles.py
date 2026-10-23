#!/usr/bin/env python3
"""Classify sampled RPC worker stacks; these shares are not CPU percentages."""
import argparse
import collections
import json
from pathlib import Path
import re


def analyze(path):
    text = path.read_text()
    graph = text.split('Call graph:', 1)[1].split('Total number in stack', 1)[0]
    blocks = re.split(r'\n(?=    \d+ Thread_)', graph)
    workers = [block for block in blocks if 'thread_pool::thread_function' in block]
    assert len(workers) == 16, 'Verify executor identities before interpreting this profile'
    counts = collections.Counter()
    examples = {}
    total = 0
    for block in workers:
        total += int(re.search(r'^\s*(\d+) Thread_', block)[1])
        stack = []
        for line in block.splitlines():
            match = re.match(r'^([\s+!|:]*)(\d+) (.*?)  \(in ', line)
            if not match:
                continue
            depth, count, symbol = len(match[1]), int(match[2]), match[3]
            while stack and stack[-1][0] >= depth:
                stack.pop()
            parents = '\n'.join(frame[1] for frame in stack)
            stack.append((depth, symbol))
            if symbol.startswith('__psynch_cvwait'):
                if '__assoc_sub_state::__sub_wait' in parents:
                    category = 'future condition wait'
                elif ('scheduler::do_run_one' in parents and not any(
                      key in parents for key in ('BroadcastTransaction', 'SubmitRpcAdmission',
                                                'JSONRPCExec', 'sendrawtransaction'))):
                    category = 'executor idle'
                elif 'BoundedTaskQueue' in parents or 'SyncWith' in parents:
                    category = 'validation fence wait'
                else:
                    category = 'other condition wait'
            elif symbol.startswith(('__psynch_mutexwait', '__ulock_wait')):
                if 'PrecomputeMempoolAdmission' in parents:
                    category = 'admission preparation lock'
                elif 'GetFeeRateInfo' in parents:
                    category = 'fee diagnostics lock'
                elif 'MempoolInfoToJSON' in parents:
                    category = 'mempool info lock'
                else:
                    category = 'other mutex wait'
            else:
                continue
            counts[category] += count
            examples.setdefault(category, [frame[1] for frame in stack[-8:]])
    counts['all other stacks'] = total - sum(counts.values())
    return {'rpc_threads': len(workers), 'thread_samples': total,
            'sample_counts': dict(counts),
            'percent': {key: round(100 * value / total, 2) for key, value in counts.items()},
            'examples': examples,
            'scope': 'Stack-sampling shares across16RPC workers; includes blocked/idle time. Not CPU-time shares, throughput, or exact lock-hold measurements.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = {side: analyze(args.data / 'round-1' / ('clients-64-' + side) / 'node0.sample.txt')
              for side in ('blocking', 'co_await')}
    args.output.write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    main()
