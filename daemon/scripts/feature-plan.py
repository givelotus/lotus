#!/usr/bin/env python3
"""Resolve independent daemon features without changing a checkout or chain data."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile

DAEMON = Path(__file__).resolve().parents[1]
TARGETS = {
    'v1': {'chronik': 'BUILD_CHRONIK', 'nng': 'BUILD_BITCOIN_NNG', 'zmq': 'BUILD_ZMQ'},
    'ecash': {'chronik': 'BUILD_CHRONIK', 'zmq': 'BUILD_ZMQ'},
    'doged': {'chronik': 'BUILD_CHRONIK', 'zmq': 'BUILD_ZMQ'},
    'bchn': {'chronik': 'BUILD_CHRONIK', 'zmq': 'BUILD_BITCOIN_ZMQ'},
    'bitcoin': {'chronik': 'BUILD_CHRONIK', 'zmq': 'WITH_ZMQ'},
}
FEATURES = ('chronik', 'chronik-off', 'nng', 'nng-off', 'zeromq-on', 'zeromq-off', 'zeromq-default-off', 'zeromq-remove',
            'block-construction', 'tx-chain-limit', 'long-chain-container-test', 'mempool-check')


def resolve(target, names, allow_experimental):
    flags, patches, evidence = [], [], []
    if 'zeromq-remove' in names and {'zeromq-on', 'zeromq-off'}.intersection(names):
        raise ValueError('ZeroMQ source removal cannot be combined with removed ZeroMQ build flags')
    for feature in ('chronik', 'nng', 'zeromq'):
        enabled = 'zeromq-on' if feature == 'zeromq' else feature
        if enabled in names and feature + '-off' in names:
            raise ValueError(f'Conflicting selections for {feature}')
    for name in names:
        if target == 'bchn' and name in ('nng', 'nng-off'):
            if not allow_experimental:
                raise ValueError('BCHN NNG is an experimental FlatBuffers port; use --allow-experimental explicitly')
            patches.append(str(DAEMON / 'patches' / 'bchn' / '10-nng-interface.patch'))
            flags.append('-DBUILD_BITCOIN_NNG=' + ('OFF' if name.endswith('-off') else 'ON'))
            evidence.append({'feature': name, 'kind': 'experimental-candidate', 'requires': [],
                             'warning': 'Existing Lotus/Rust FlatBuffers data/mining/event contract with separate Tobias legacy RPC; native macOS validation, no standalone Chronik'})
        elif name in ('chronik', 'chronik-off', 'nng', 'nng-off'):
            feature = name.removesuffix('-off')
            flag = TARGETS[target].get(feature)
            if not flag:
                raise ValueError(f'{target}: {feature} has no implemented port in this repository')
            flags.append(f'-D{flag}=' + ('OFF' if name.endswith('-off') else 'ON'))
            evidence.append({'feature': name, 'kind': 'existing-build-option', 'requires': []})
        elif name in ('zeromq-on', 'zeromq-off'):
            flags.append(f'-D{TARGETS[target]["zmq"]}=' + ('OFF' if name.endswith('-off') else 'ON'))
            evidence.append({'feature': name, 'kind': 'existing-build-option', 'requires': []})
        elif name in ('zeromq-default-off', 'zeromq-remove'):
            if target != 'bchn':
                raise ValueError(f'{target}: no implemented ZeroMQ source-change candidate')
            if not allow_experimental:
                raise ValueError('BCHN ZeroMQ source changes require --allow-experimental')
            patches.append(str(DAEMON / 'patches' / 'bchn' / '11-disable-zeromq.patch'))
            requires = []
            warning = 'Changes only the build default; implementation and explicit ON remain available'
            if name == 'zeromq-remove':
                patches.append(str(DAEMON / 'patches' / 'bchn' / '12-remove-zeromq.patch'))
                requires = ['zeromq-default-off']
                warning = 'Removes ZeroMQ source, dependencies and public API; does not require NNG'
            evidence.append({'feature': name, 'kind': 'experimental-candidate',
                             'requires': requires, 'warning': warning})
        elif name == 'block-construction' and target == 'v1':
            evidence.append({'feature': name, 'kind': 'integrated-custom-assembler',
                             'requires': ['complete-v1-series'],
                             'warning': 'Corrected snapshot/ready-heap implementation in patch 001; no measured speedup over modern ABC'})
        elif name == 'long-chain-container-test' and target == 'v1':
            evidence.append({'feature': name, 'kind': 'integrated-test-only',
                             'requires': ['complete-v1-series']})
        elif name == 'mempool-check':
            if target not in ('bchn', 'v1', 'ecash', 'doged'):
                raise ValueError(f'{target}: no topological consistency-check candidate is implemented')
            if not allow_experimental:
                raise ValueError('Consistency-check candidate requires --allow-experimental')
            if target == 'bchn':
                patch = DAEMON / 'patches' / 'bchn' / '04-topological-mempool-check.patch'
            else:
                patch = (DAEMON / 'candidates' / 'mempool-diagnostics' / target /
                         '0001-avoid-redundant-ancestor-check.patch')
            patches.append(str(patch))
            evidence.append({'feature': name, 'kind': 'experimental-diagnostic-optimization', 'requires': [],
                             'warning': 'Optimizes optional consistency checking; no admission-policy change'})
        elif name == 'long-chain-container-test' and target == 'bchn':
            raise ValueError('BCHN historical 02 is not maintained at the current pin; use mempool-check for diagnostic coverage')
        elif name == 'tx-chain-limit':
            raise ValueError('No standalone admission-policy change is implemented; patch 02 only calls addUnchecked')
        else:
            if target not in ('ecash', 'bchn', 'doged'):
                raise ValueError(f'{target}: no {name} candidate exists')
            if not allow_experimental:
                raise ValueError(f'{name} is unvalidated review material; use --allow-experimental explicitly')
            series = 'ecash' if target == 'doged' else target
            filename = (('01-prioritize-ready-transactions.patch' if target == 'bchn' else
                         '01-nlogn-block-construction.patch') if name == 'block-construction'
                        else '02-remove-chaintx-limit.patch')
            patches.append(str(DAEMON / 'patches' / series / filename))
            warning = 'Clean application does not establish successful builds or behavior'
            if series == 'ecash' and name == 'block-construction':
                warning = ('Corrected custom snapshot/ready-heap assembler with native regression evidence; '
                           'expected O(n + m + n log n), no measured speedup over modern ABC')
            if target == 'bchn' and name == 'block-construction':
                warning = ('Ready-backlog fee-priority fix; current BCHN already avoids quadratic dependency '
                           'traversal. Native regression evidence, no measured performance speedup')
            evidence.append({'feature': name, 'kind': 'experimental-candidate', 'requires': [],
                             'warning': warning})
    return {'target': target, 'cmake_args': flags, 'patches': list(dict.fromkeys(patches)), 'features': evidence}


def check(plan, workspace):
    def git(*args, **kwargs):
        return subprocess.run(['git', '-C', str(workspace), *args], check=True,
                              capture_output=True, text=True, **kwargs)
    plan['checked_revision'] = git('rev-parse', 'HEAD').stdout.strip()
    # Refuse to mistake local changes for the exact upstream revision.
    if git('status', '--porcelain', '--untracked-files=no').stdout:
        raise ValueError('Check requires a clean tracked source tree; use an isolated checkout')
    with tempfile.TemporaryDirectory(prefix='lotus-feature-index-') as tmp:
        env = dict(os.environ, GIT_INDEX_FILE=str(Path(tmp) / 'index'))
        git('read-tree', 'HEAD', env=env)
        for patch in plan['patches']:
            git('apply', '--cached', '--whitespace=nowarn', patch, env=env)
        plan['resulting_tree'] = git('write-tree', env=env).stdout.strip()
    plan['application'] = 'passed' if plan['patches'] else 'no-patches-required'
    plan['build'] = 'not-run'
    plan['behavior'] = 'not-run'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', required=True, choices=TARGETS)
    parser.add_argument('--features', required=True, help='Comma-separated: ' + ', '.join(FEATURES))
    parser.add_argument('--allow-experimental', action='store_true')
    parser.add_argument('--check-workspace', type=Path, help='Check patches against clean HEAD using a temporary Git index')
    parser.add_argument('--patches', action='store_true', help='Print selected patch paths, one per line')
    args = parser.parse_args()
    names = list(dict.fromkeys(args.features.split(',')))
    unknown = set(names) - set(FEATURES)
    try:
        if unknown:
            raise ValueError('Unknown features: ' + ', '.join(sorted(unknown)))
        plan = resolve(args.target, names, args.allow_experimental)
        if args.check_workspace:
            check(plan, args.check_workspace)
    except (ValueError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f'{getattr(exc, "stderr", None) or str(exc)}\n')
    print('\n'.join(plan['patches']) if args.patches else json.dumps(plan, indent=2))


if __name__ == '__main__':
    main()
