#!/usr/bin/env python3
"""Move identified split concerns before their first caller in a candidate only."""
import argparse
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--before', type=int, required=True, help='Immutable split-manifest ordinal of the first caller')
    parser.add_argument('--move', type=int, nargs='+', required=True, help='Immutable split ordinals, in dependency order')
    parser.add_argument('--reason', required=True)
    args = parser.parse_args()
    root = args.candidate.resolve()
    audit = root / 'daemon/patch-audit'
    historical = audit / 'split-manifest.json'
    canonical = audit / 'progression/canonical-manifest.json'
    if canonical.exists():
        manifest = json.loads(canonical.read_text())
    else:
        original = json.loads(historical.read_text())
        manifest = {'schema': 1, 'base': original['base'],
                    'split_manifest_sha256': hashlib.sha256(historical.read_bytes()).hexdigest(),
                    'patches': [{**patch, 'split_index': index, 'split_number': patch['number'],
                                 'split_file': patch['file']} for index, patch in enumerate(original['patches'], 1)],
                    'reorderings': []}
    patches = manifest['patches']
    for patch in patches:
        patch.setdefault('canonical_id', 'split-' + str(patch['split_index']))
    by_index = {patch['split_index']: patch for patch in patches if patch['split_index'] is not None}
    if len(set(args.move)) != len(args.move) or args.before in args.move:
        parser.error('Move ordinals must be distinct from each other and the caller')
    if any(by_index[index]['series'] != by_index[args.before]['series'] for index in args.move):
        parser.error('A prerequisite move cannot cross series')
    ordered = [patch for patch in patches if patch['split_index'] not in args.move]
    position = next(i for i, patch in enumerate(ordered) if patch['split_index'] == args.before)
    ordered[position:position] = [by_index[index] for index in args.move]
    # Read every mailbox before changing any path, so renumbering cannot clobber
    # another patch. The immutable historical manifest is never modified.
    payloads = {patch['canonical_id']: (root / 'daemon/patches' / patch['series'] / patch['file']).read_bytes()
                for patch in patches}
    for patch in patches:
        (root / 'daemon/patches' / patch['series'] / patch['file']).unlink()
    counts = {'ecash': 0, 'v2': 0}
    for patch in ordered:
        series = patch['series']
        counts[series] += 1
        patch['number'] = counts[series]
        patch['file'] = f"{patch['number']:03}-" + patch['file'].split('-', 1)[1]
        (root / 'daemon/patches' / series / patch['file']).write_bytes(payloads[patch['canonical_id']])
    for series in counts:
        header = '# Repaired candidate order; see ../../patch-audit/progression/canonical-manifest.json.\n'
        if series == 'v2':
            header += '@include ../ecash/series\n'
        (root / 'daemon/patches' / series / 'series').write_text(header + ''.join(patch['file'] + '\n' for patch in ordered if patch['series'] == series))
    manifest['patches'] = ordered
    manifest['reorderings'].append({'split_ordinals_moved': args.move, 'before_split_ordinal': args.before, 'reason': args.reason})
    canonical.write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps({'counts': counts, 'mapping': str(canonical), 'reordering': manifest['reorderings'][-1]}))


if __name__ == '__main__':
    main()
