#!/usr/bin/env python3
"""Check optional BCHN patch ordering using disposable Git indexes only."""
import argparse
import hashlib
import itertools
import json
import os
from pathlib import Path
import subprocess
import tempfile

DAEMON = Path(__file__).resolve().parents[1]
PATCHES = {
    '01': '01-prioritize-ready-transactions.patch',
    '04': '04-topological-mempool-check.patch',
    '10': '10-nng-interface.patch',
    '11': '11-disable-zeromq.patch',
    '12': '12-remove-zeromq.patch',
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--upstream', type=Path, required=True, help='Existing clone containing the exact pinned base')
    parser.add_argument('--output', type=Path, help='Write JSON evidence instead of stdout')
    parser.add_argument('--expect-tree', help='Require this final source tree for every full order')
    args = parser.parse_args()
    base = (DAEMON / 'bchn-version').read_text().strip()
    patch_dir = DAEMON / 'patches/bchn'
    results = []
    with tempfile.TemporaryDirectory(prefix='bchn-order-index-') as tmp:
        env = dict(os.environ, GIT_INDEX_FILE=str(Path(tmp) / 'index'))

        def git(*argv):
            return subprocess.run(['git', '-C', str(args.upstream), *argv], env=env,
                                  check=True, text=True, capture_output=True).stdout.strip()

        for size in range(1, len(PATCHES) + 1):
            for order in itertools.permutations(PATCHES, size):
                if '12' in order and ('11' not in order or order.index('11') > order.index('12')):
                    continue
                git('read-tree', base)
                for slot in order:
                    git('apply', '--cached', '--whitespace=nowarn', str(patch_dir / PATCHES[slot]))
                results.append({'order': list(order), 'tree': git('write-tree'), 'status': 'pass'})

        # Source deletion deliberately follows the separately reviewable OFF-default patch.
        git('read-tree', base)
        try:
            git('apply', '--cached', '--whitespace=nowarn', str(patch_dir / PATCHES['12']))
        except subprocess.CalledProcessError:
            pass
        else:
            raise RuntimeError('Patch 12 unexpectedly applies without its declared patch 11 dependency')

    full = [row for row in results if len(row['order']) == len(PATCHES)]
    trees = {row['tree'] for row in full}
    if len(results) != 170 or len(full) != 60 or len(trees) != 1:
        raise RuntimeError('Unexpected ordering coverage or nonidentical final source trees')
    tree = next(iter(trees))
    if args.expect_tree and args.expect_tree != tree:
        raise RuntimeError(f'Tested source tree differs: expected {args.expect_tree}, got {tree}')
    # Four independently ordered feature units: removal expands into 11 then 12.
    feature_orders = [row for row in results if '11' not in row['order'] or (
        '12' in row['order'] and row['order'].index('12') == row['order'].index('11') + 1)]
    if len(feature_orders) != 64:
        raise RuntimeError('Expected all 64 ordered feature combinations')
    report = {
        'base': base,
        'patches': {slot: {'file': filename, 'sha256': hashlib.sha256((patch_dir / filename).read_bytes()).hexdigest()}
                    for slot, filename in PATCHES.items()},
        'dependency': '12 requires 11 before it; no NNG/mining/mempool dependency',
        '12_without_11_rejected': True,
        'raw_application_orders': results,
        'raw_order_count': len(results),
        'full_order_count': len(full),
        'feature_order_count': len(feature_orders),
        'full_tree': tree,
        'build': 'not-run-by-this-script',
        'behavior': 'not-run-by-this-script',
    }
    rendered = json.dumps(report, indent=2) + '\n'
    if args.output:
        args.output.write_text(rendered)
        print(json.dumps({key: report[key] for key in ('raw_order_count', 'full_order_count', 'feature_order_count', 'full_tree')}))
    else:
        print(rendered, end='')


if __name__ == '__main__':
    main()
