#!/usr/bin/env python3
"""Combine adjacent fragments of one purpose, retaining every historical ID.

Requires successful application records for all fragments and a stopped runner.
This is not a bulk squashing tool: the operator must explain the single purpose.
"""
import argparse
import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess


def git(source, *args, **kwargs):
    return subprocess.check_output(['git', '-C', str(source), *args], **kwargs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--first', type=int, required=True)
    parser.add_argument('--last', type=int, required=True)
    parser.add_argument('--subject', required=True)
    parser.add_argument('--purpose', required=True)
    args = parser.parse_args()
    lock = (args.data / 'runner.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    path = args.candidate / 'daemon/patch-audit/progression/canonical-manifest.json'
    before_manifest = path.read_bytes()
    manifest = json.loads(before_manifest)
    entries = manifest['patches']
    assert 1 <= args.first < args.last <= len(entries)
    selected = entries[args.first - 1:args.last]
    assert len({p['series'] for p in selected}) == 1, 'Cannot combine across the consensus boundary'
    records = [json.loads((args.data / f'patch_{i:03}.json').read_text()) for i in range(args.first, args.last + 1)]
    for entry, record in zip(selected, records):
        mailbox = args.candidate / 'daemon/patches' / entry['series'] / entry['file']
        assert record['sha256'] == hashlib.sha256(mailbox.read_bytes()).hexdigest()
        assert record.get('source_sha'), 'Need actual applied source identity for each fragment'
    for previous, record in zip(records, records[1:]):
        assert git(args.source, 'rev-parse', record['source_sha'] + '^', text=True).strip() == previous['source_sha']
    parent = git(args.source, 'rev-parse', records[0]['source_sha'] + '^', text=True).strip()
    tree = records[-1]['source_tree']
    original_ids = list(dict.fromkeys(i for p in selected for i in p.get('original_ids', [p['original_patch']])))
    split_ids = [i for p in selected for i in p.get('source_split_ids', p.get('split_ids', [p['split_index']]))]
    body = args.subject + '\n\n' + args.purpose + '\n\nOriginal-Patches: ' + ', '.join(original_ids) + '\nSplit-Ids: ' + ', '.join(map(str, split_ids)) + '\n'
    meta = git(args.source, 'show', '-s', '--format=%an%x00%ae%x00%aI', records[0]['source_sha'], text=True).strip().split('\0')
    env = dict(os.environ, GIT_AUTHOR_NAME=meta[0], GIT_AUTHOR_EMAIL=meta[1], GIT_AUTHOR_DATE=meta[2],
               GIT_COMMITTER_NAME=meta[0], GIT_COMMITTER_EMAIL=meta[1], GIT_COMMITTER_DATE=meta[2])
    commit = git(args.source, 'commit-tree', tree, '-p', parent, input=body, text=True, env=env).strip()
    payload = git(args.source, 'format-patch', '-1', commit, '--stdout', '--no-signature', '--keep-subject', '--full-index')
    # Read every mailbox before renaming; source and all build artifacts remain untouched.
    old_paths = [args.candidate / 'daemon/patches' / p['series'] / p['file'] for p in entries]
    payloads = [p.read_bytes() for p in old_paths]
    merged = dict(selected[0], subject=args.subject, original_ids=original_ids, split_ids=split_ids,
                  files=sorted({f for p in selected for f in p['files']}))
    merged['file'] = '000-' + re.sub('[^a-z0-9]+', '-', args.subject.lower()).strip('-') + '.patch'
    merged['canonical_source_commit'] = commit
    merged['canonical_source_tree'] = tree
    entries[args.first - 1:args.last] = [merged]
    payloads[args.first - 1:args.last] = [payload]
    for old in old_paths:
        old.unlink()
    counts = {}
    for index, (entry, mailbox) in enumerate(zip(entries, payloads), 1):
        series = entry['series']
        counts[series] = counts.get(series, 0) + 1
        entry['number'] = counts[series]
        entry['global_number'] = index
        entry['file'] = f'{counts[series]:03}-' + entry['file'].split('-', 1)[1]
        (args.candidate / 'daemon/patches' / series / entry['file']).write_bytes(mailbox)
    for series in counts:
        names = [p['file'] for p in entries if p['series'] == series]
        (args.candidate / 'daemon/patches' / series / 'series').write_text(('@include ../ecash/series\n' if series == 'v2' else '') + '\n'.join(names) + '\n')
    ledger_path = path.with_name('repairs.json')
    ledger = json.loads(ledger_path.read_text())
    ledger.append({'operation': 'combine fragments of one purpose', 'purpose': args.purpose,
                   'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   'original_ids': original_ids, 'split_ids': split_ids, 'invalidate_from_index': args.first,
                   'old_boundaries': [{'global_number': r['index'], 'source_commit': r['source_sha'],
                                       'source_tree': r['source_tree'], 'mailbox_sha256': r['sha256']} for r in records],
                   'new_commit': commit, 'new_tree': tree, 'endpoint_tree_preserved': True,
                   'before_manifest_sha256': hashlib.sha256(before_manifest).hexdigest(),
                   'status': 'pending clean replay and gates'})
    ledger_path.write_text(json.dumps(ledger, indent=2) + '\n')
    contracts_path = path.with_name('contracts.json')
    contracts = json.loads(contracts_path.read_text())
    primary = contracts['patches'][str(selected[0].get('contract_id', selected[0]['split_index']))]
    primary['canonical_purpose'] = args.purpose
    primary['original_ids'] = original_ids
    primary['split_ids'] = split_ids
    primary['split_mechanism'] = args.purpose
    primary['provenance']['source_files'] = merged['files']
    primary['combined_contract_ids'] = split_ids
    primary['review_status'] = 'Purpose regrouped; clean replay and gates pending'
    contracts_path.write_text(json.dumps(contracts, indent=2) + '\n')
    path.write_text(json.dumps(manifest, indent=2) + '\n')
    subprocess.run(['python3', str(Path(__file__).with_name('refresh-progression-manifest.py')), '--candidate', str(args.candidate)], check=True)
    print(json.dumps({'combined': [args.first, args.last], 'new_count': len(entries), 'commit': commit, 'tree': tree}))


if __name__ == '__main__':
    main()
