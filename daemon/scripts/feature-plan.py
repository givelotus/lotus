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
    'bchn': {'zmq': 'BUILD_BITCOIN_ZMQ'},
    'bitcoin': {'zmq': 'WITH_ZMQ'},
}
FEATURES = ('chronik', 'chronik-off', 'nng', 'nng-off', 'zeromq-on', 'zeromq-off', 'zeromq-remove',
            'block-construction', 'tx-chain-limit', 'long-chain-container-test')


def resolve(target, names, allow_experimental):
    flags, patches, evidence = [], [], []
    for feature in ('chronik', 'nng', 'zeromq'):
        enabled = 'zeromq-on' if feature == 'zeromq' else feature
        if enabled in names and feature + '-off' in names:
            raise ValueError(f'Conflicting selections for {feature}')
    for name in names:
        if name in ('chronik', 'chronik-off', 'nng', 'nng-off'):
            feature = name.removesuffix('-off')
            flag = TARGETS[target].get(feature)
            if not flag:
                raise ValueError(f'{target}: {feature} has no implemented port in this repository')
            flags.append(f'-D{flag}=' + ('OFF' if name.endswith('-off') else 'ON'))
            evidence.append({'feature': name, 'kind': 'existing-build-option', 'requires': []})
        elif name in ('zeromq-on', 'zeromq-off'):
            flags.append(f'-D{TARGETS[target]["zmq"]}=' + ('OFF' if name.endswith('-off') else 'ON'))
            evidence.append({'feature': name, 'kind': 'existing-build-option', 'requires': []})
        elif name == 'zeromq-remove':
            raise ValueError('ZeroMQ source-removal patches are placeholders; use zeromq-off')
        elif name in ('block-construction', 'tx-chain-limit') and target == 'v1':
            evidence.append({'feature': name, 'kind': 'integrated-mainnet-series',
                             'requires': ['complete-v1-series']})
        elif name == 'tx-chain-limit':
            raise ValueError('No standalone admission-policy change is implemented; patch 02 only calls addUnchecked')
        else:
            if target not in ('ecash', 'bchn', 'doged'):
                raise ValueError(f'{target}: no {name} candidate exists')
            if not allow_experimental:
                raise ValueError(f'{name} is unvalidated review material; use --allow-experimental explicitly')
            series = 'ecash' if target == 'doged' else target
            filename = ('01-nlogn-block-construction.patch' if name == 'block-construction'
                        else '02-remove-chaintx-limit.patch')
            patches.append(str(DAEMON / 'patches' / series / filename))
            evidence.append({'feature': name, 'kind': 'experimental-candidate', 'requires': [],
                             'warning': 'Clean application does not establish successful builds or behavior'})
    return {'target': target, 'cmake_args': flags, 'patches': patches, 'features': evidence}


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
