#!/usr/bin/env python3
"""Profile validated native batch ingestion; instrumented rates are not benchmarks."""
import argparse
import fcntl
import importlib.util
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location('audit', ROOT / 'daemon/bench/commit-regressions/run.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--build-receipt', type=Path, required=True)
    parser.add_argument('--fixture-transactions', type=int, default=800000)
    args = parser.parse_args()
    if not 500000 <= args.fixture_transactions <= 1200000:
        parser.error('Use 500K..1.2M distinct signed transactions')
    data = args.data.resolve()
    data.mkdir(parents=True, exist_ok=False)
    import json
    receipt = json.loads(args.build_receipt.read_text())
    assert audit.sha(receipt['binary']) == receipt['binary_sha256']
    with (ROOT / 'daemon/.local-artifact-archive/benchmark-host.lock').open('a') as host_lock, \
            (audit.SOURCE / '.git/progression.lock').open('a') as source_lock:
        for lock in (host_lock, source_lock):
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        previous = audit.git('symbolic-ref', '-q', 'HEAD') if subprocess.run(
            ['git', '-C', str(audit.SOURCE), 'symbolic-ref', '-q', 'HEAD'],
            stdout=subprocess.DEVNULL).returncode == 0 else audit.git('rev-parse', 'HEAD')
        audit.checkout(receipt['commit'])
        command = [sys.executable, ROOT / 'daemon/bench/commit-regressions/steady_loopback.py',
                   '--series', 'v2', '--daemon', receipt['binary'], '--source', audit.SOURCE,
                   '--output', data / 'result.json', '--steady', '--case', 'signed_batch200_steady',
                   '--max-fixture-transactions', '1200000', '--exact-fixture-transactions',
                   str(args.fixture_transactions), '--fixture-hash-site',
                   ROOT / 'daemon/.local-artifact-archive/fixture-hash-site',
                   '--fixture-fee-sats', '10000', '--hierarchical-funding',
                   '--maxmempool-mb', '4096', '--port-base', '39110',
                   '--sample-node0-output', data / 'node0.sample.txt']
        tools = list((ROOT / 'daemon/patch-audit/consolidation/20261022/benchmark-tools').rglob('*.py'))
        tools += [Path(__file__), ROOT / 'daemon/bench/commit-regressions/steady_loopback.py']
        audit.write(data / 'INPUTS.json', dict(source=receipt,
            tools={str(p.relative_to(ROOT)): audit.sha(p) for p in tools},
            command=list(map(str, command)), previous_ref=previous,
            scope='Instrumented native V2 signed-batch200 acceptance; NOT publishable TPS, peer convergence or finality'))
        try:
            resources = audit.guarded(command, data / 'stdout.log', dict(os.environ,
                TMPDIR=str(ROOT / 'daemon/.local-artifact-archive/commit-regressions/runtime')))
            audit.write(data / 'RESOURCES.json', resources)
        finally:
            if previous.startswith('refs/heads/'):
                subprocess.run(['git', '-C', str(audit.SOURCE), 'switch', '--no-overwrite-ignore',
                                previous.removeprefix('refs/heads/')], check=True)
            else:
                audit.checkout(previous)


if __name__ == '__main__':
    main()
