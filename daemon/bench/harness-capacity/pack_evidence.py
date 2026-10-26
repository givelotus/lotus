#!/usr/bin/env python3
"""Preserve raw benchmark evidence compactly; verify every archived byte."""
import argparse
import hashlib
import json
from pathlib import Path
import tarfile

ROOT = Path(__file__).resolve().parents[3]


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('directories', type=Path, nargs='+')
    args = parser.parse_args()
    args.output = args.output.resolve()
    assert not args.output.exists(), 'Preserve existing evidence; choose a fresh archive'
    paths = set()
    for directory in args.directories:
        for path in directory.rglob('*'):
            if path.is_file() and path.suffix in ('.json', '.log', '.py', '.stderr', '.txt', '.bundle'):
                paths.add(path.resolve())
    records = [{'path': str(path.relative_to(ROOT)), 'sha256': digest(path), 'bytes': path.stat().st_size}
               for path in sorted(paths)]
    with tarfile.open(args.output, 'w:gz', compresslevel=3) as archive:
        for record in records:
            archive.add(ROOT / record['path'], arcname=record['path'], recursive=False)
    with tarfile.open(args.output, 'r:gz') as archive:
        for record in records:
            stream = archive.extractfile(record['path'])
            assert hashlib.file_digest(stream, 'sha256').hexdigest() == record['sha256']
    args.output.with_suffix('.manifest.json').write_text(json.dumps({
        'archive': str(args.output.relative_to(ROOT)), 'archive_sha256': digest(args.output),
        'verified_members': len(records), 'members': records,
        'scope': 'Raw evidence, generated measurement scripts and historical tool versions; no fixture databases or signing corpora removed.'
    }, indent=2) + '\n')


if __name__ == '__main__':
    main()
