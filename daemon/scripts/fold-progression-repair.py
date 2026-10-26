#!/usr/bin/env python3
"""Fold a defect and regression into its first responsible canonical mailbox.

Replay to --index before editing. --failure-index may name a later boundary that
exposed the defect; it does not determine where the correction belongs.
"""
import argparse
import datetime
import fcntl
import hashlib
import json
from pathlib import Path
import subprocess


def git(source, *args, **kwargs):
    return subprocess.check_output(['git', '-C', str(source), *args], **kwargs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--index', type=int, required=True)
    parser.add_argument('--failure-index', type=int,
                        help='Boundary exposing the defect (defaults to its owner --index)')
    parser.add_argument('--rationale', required=True)
    parser.add_argument('--subject', help='Correct an overstated historical subject for this purpose')
    parser.add_argument('--application-resolution', action='store_true',
                        help='Fold an inspected manual resolution of a failed git am at this owner')
    args = parser.parse_args()
    lock = (args.data / 'runner.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    if args.index < 1:
        parser.error('The ABC baseline is immutable')
    record = json.loads((args.data / f'patch_{args.index:03}.json').read_text())
    failure_index = args.failure_index if args.failure_index is not None else args.index
    failure_path = args.data / f'patch_{failure_index:03}.json'
    failure = json.loads(failure_path.read_text())
    if failure_index < args.index or failure.get('status') != 'failed':
        parser.error('Expected a failed boundary at or after the first responsible patch')
    source, candidate = args.source.resolve(), args.candidate.resolve()
    head = git(source, 'rev-parse', 'HEAD', text=True).strip()
    if not git(source, 'status', '--porcelain', text=True):
        parser.error('Inspect a nonempty working diff before folding')
    if args.application_resolution:
        previous = json.loads((args.data / f'patch_{args.index - 1:03}.json').read_text())
        am_state = Path(git(source, 'rev-parse', '--git-path', 'rebase-apply', text=True).strip())
        if not am_state.is_absolute():
            am_state = source / am_state
        if (failure_index != args.index or record.get('source_sha') or
                head != previous.get('source_sha') or previous.get('status') != 'ok' or
                not am_state.is_dir() or failure.get('error') != 'apply failed'):
            parser.error('Application resolution requires the failed owner git am on its validated parent')
    elif head != record.get('source_sha'):
        parser.error('Replay to the first responsible patch before folding')
    path = candidate / 'daemon/patches' / record['series'] / record['file']
    before = path.read_bytes()
    manifest = json.loads((candidate / 'daemon/patch-audit/progression/canonical-manifest.json').read_text())
    owner = manifest['patches'][args.index - 1]
    if (owner['series'], owner['file']) != (record['series'], record['file']) or hashlib.sha256(before).hexdigest() != record['sha256']:
        parser.error('Owner mapping or mailbox changed since the recorded source; replay its current canonical prefix first')
    if args.application_resolution:
        subprocess.run(['git', '-C', str(source), 'add', '-A'], check=True)
        subprocess.run(['git', '-C', str(source), '-c', 'commit.gpgsign=false',
                        'am', '--continue'], check=True, stdout=subprocess.DEVNULL)
    message = git(source, 'log', '-1', '--format=%B', text=True).rstrip()
    if args.subject:
        message = args.subject + '\n' + message.partition('\n')[2]
    message = message.replace('No source semantics are added or removed by this history operation.',
                              'The original split preserved source semantics. The candidate repair below\nchanges this boundary and requires new validation evidence.')
    message += '\n\nCandidate-Repair: ' + args.rationale + '\n'
    subprocess.run(['git', '-C', str(source), 'add', '-A'], check=True)
    subprocess.run(['git', '-C', str(source), '-c', 'commit.gpgsign=false', 'commit', '--amend', '-F', '-'],
                   input=message, text=True, check=True, stdout=subprocess.DEVNULL)
    after = git(source, 'format-patch', '-1', '--stdout', '--no-signature', '--keep-subject', '--full-index')
    path.write_bytes(after)
    ledger_path = candidate / 'daemon/patch-audit/progression/repairs.json'
    ledger = json.loads(ledger_path.read_text()) if ledger_path.exists() else []
    ledger.append({'index': args.index, 'label': record['label'], 'original_patch': record['original_patch'],
                   'split_index': record.get('split_index', args.index),
                   'split_patch': record.get('contract', {}).get('split_patch', record['label']),
                   'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   'rationale': args.rationale, 'before_mailbox_sha256': hashlib.sha256(before).hexdigest(),
                   'after_mailbox_sha256': hashlib.sha256(after).hexdigest(),
                   'before_source_commit': record.get('source_sha'),
                   'before_source_tree': record.get('source_tree'),
                   'application_resolution_parent': head if args.application_resolution else None,
                   'after_source_commit': git(source, 'rev-parse', 'HEAD', text=True).strip(),
                   'after_source_tree': git(source, 'rev-parse', 'HEAD^{tree}', text=True).strip(),
                   'discovered_at_index': failure_index,
                   'failure_record': str(Path(failure['attempt']) / 'record.json'),
                   'failure_source_commit': failure.get('source_sha'),
                   'invalidate_from_index': args.index,
                   'placement': 'first responsible logical patch, including its regression tests',
                   'status': 'pending clean replay and gates'})
    ledger_path.write_text(json.dumps(ledger, indent=2) + '\n')
    print(json.dumps(ledger[-1]))


if __name__ == '__main__':
    main()
