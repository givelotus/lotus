#!/usr/bin/env python3
"""Collect patch deliveries without applying them or overwriting source files."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import re


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--output', default='daemon/patch-intake/20261021')
    args = parser.parse_args()
    root = args.root.resolve()
    output = root / args.output
    output.mkdir(parents=True, exist_ok=True)
    payloads = output / 'patches'
    payloads.mkdir(exist_ok=True)
    canonical = {}
    for series in ('ecash', 'v2'):
        for path in (root / 'daemon/patches' / series).glob('*.patch'):
            canonical.setdefault(digest(path.read_bytes()), []).append(str(path.relative_to(root)))

    roots = []
    for parent in (Path.home() / 'repos', Path('/private/tmp')):
        if not parent.exists():
            continue
        for path in sorted(parent.iterdir()):
            name = path.name.lower()
            wanted = ('lotus', 'ecash', 'patch', 'beast', 'zero-copy', 'slab',
                      'layered', 'track', 'series-consolidate', 'claude-501')
            if path.is_dir() and not path.is_symlink() and (
                    any(word in name for word in wanted) or name == 'bitcoin-abc-test-harness'):
                roots.append(path)
    brain = Path.home() / '.gemini/antigravity/brain'
    if brain.exists():
        roots.append(brain)
    if (output / 'exports').exists():
        roots.append(output / 'exports')
    excluded = {'.git', 'node_modules', '.venv', 'venv', '__pycache__',
                'CMakeFiles', '_deps', 'target', '.dart_tool', '.pub-cache'}
    records = {}
    errors = []
    files_seen = 0
    for source_root in roots:
        for directory, dirs, files in os.walk(source_root, followlinks=False):
            here = Path(directory)
            dirs[:] = [name for name in dirs if name not in excluded
                       and not (here / name).is_symlink()
                       and (here / name).resolve() != output.resolve()]
            for name in sorted(files):
                if Path(name).suffix.lower() not in {'.patch', '.mbox', '.diff'}:
                    continue
                path = here / name
                if path.is_symlink():
                    continue
                try:
                    data = path.read_bytes()
                    sha = digest(data)
                    files_seen += 1
                    if sha not in records:
                        first = data[:65536].decode('utf-8', errors='replace')
                        subject = re.search(r'^Subject: (.*(?:\n[ \t].*)*)', first, re.M)
                        original = re.findall(r'^Original-Patch:\s*(.+)$', first, re.M)
                        origin = re.sub(r'[^a-zA-Z0-9_-]+', '-', source_root.name)[:48]
                        stem = re.sub(r'[^a-zA-Z0-9_.-]+', '-', path.stem)[:105]
                        destination = payloads / f'{stem}__from-{origin}__{sha[:16]}{path.suffix.lower()}'
                        entry = {'sha256': sha, 'bytes': len(data), 'origins': [],
                                 'subject': subject.group(1).replace('\n', ' ') if subject else None,
                                 'original_patch': original,
                                 'canonical_exact_matches': canonical.get(sha, []),
                                 'status': 'already_in_series_exact_bytes' if sha in canonical else 'unreviewed_intake',
                                 'applied_by_collector': False}
                        if sha in canonical:
                            entry['collected_path'] = canonical[sha][0]
                        elif path.is_relative_to(output):
                            entry['collected_path'] = str(path.relative_to(root))
                        else:
                            if destination.exists():
                                if digest(destination.read_bytes()) != sha:
                                    raise RuntimeError(f'Refusing to overwrite different content: {destination}')
                            else:
                                # Exclusive creation protects existing deliveries from clobbering.
                                with destination.open('xb') as handle:
                                    handle.write(data)
                            entry['collected_path'] = str(destination.relative_to(root))
                        records[sha] = entry
                    records[sha]['origins'].append(str(path))
                except (OSError, RuntimeError) as error:
                    errors.append({'path': str(path), 'error': str(error)})
    entries = sorted(records.values(), key=lambda row: (row['status'], row['collected_path']))
    manifest = {'schema': 1, 'scope': 'Discovered Lotus/eCash delivery files; not an application or validation claim',
                'source_roots': [str(path) for path in roots], 'excluded_directory_names': sorted(excluded),
                'source_files_seen': files_seen, 'unique_payloads': len(entries),
                'new_unique_payloads': sum(row['status'] == 'unreviewed_intake' for row in entries),
                'duplicate_source_copies': files_seen - len(entries),
                'copied_payload_bytes': sum(row['bytes'] for row in entries if row['status'] == 'unreviewed_intake'),
                'errors': errors, 'patches': entries}
    temporary = output / 'manifest.json.tmp'
    temporary.write_text(json.dumps(manifest, indent=2) + '\n')
    temporary.replace(output / 'manifest.json')
    with (output / 'index.csv').open('w', newline='') as handle:
        writer = csv.writer(handle)
        writer.writerow(['status', 'subject', 'original_patch', 'collected_path',
                         'sha256', 'bytes', 'origin_count', 'origins'])
        for row in entries:
            writer.writerow([row['status'], row['subject'], '; '.join(row['original_patch']),
                             row['collected_path'], row['sha256'], row['bytes'],
                             len(row['origins']), '\n'.join(row['origins'])])
    (output / 'README.md').write_text(
        '# Collected patch intake\n\n'
        'These files are collected for review, not appended to either series. '
        'Names retain a source label and content hash; distinct versions cannot overwrite each other. '
        'Identical payloads have one copy with every discovered origin recorded in manifest.json. '
        'Exact matches already in the maintained series point there instead of creating another copy.\n\n'
        f'Scanned {files_seen} source files; {len(entries)} unique payloads; '
        f'{manifest["new_unique_payloads"]} unique intake payloads. '
        f'Read errors: {len(errors)}.\n\n'
        'Re-run: python3 daemon/scripts/collect-patch-intake.py\n')
    print(json.dumps({key: manifest[key] for key in (
        'source_files_seen', 'unique_payloads', 'new_unique_payloads',
        'duplicate_source_copies', 'copied_payload_bytes')}))
    print(f'Read errors: {len(errors)}; manifest: {output / "manifest.json"}')


if __name__ == '__main__':
    main()
