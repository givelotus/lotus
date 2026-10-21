#!/usr/bin/env python3
"""Read-only historical hunk audit against an immutable Git source revision.

Matches are textual evidence, never semantic or performance approval. A failed
reverse application or unmatched block is a review request, not proof of loss.
"""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tarfile
import tempfile
from collections import Counter


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args])


def sha(data):
    return hashlib.sha256(data).hexdigest()


def parse_patch(text):
    """Parse ordinary unified hunks, respecting counts and mail trailers."""
    files = []
    current = None
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith('diff --git '):
            parts = shlex.split(line)
            current = {'old_path': parts[2][2:], 'path': parts[3][2:],
                       'hunks': [], 'binary': False, 'deleted': False}
            files.append(current)
        elif current is not None:
            if line.startswith('deleted file mode '):
                current['deleted'] = True
            if line.startswith(('GIT binary patch', 'Binary files ')):
                current['binary'] = True
            m = re.match(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*)', line)
            if m:
                old_left = int(m[2]) if m[2] is not None else 1
                new_left = int(m[4]) if m[4] is not None else 1
                h = {'header': line, 'old_start': int(m[1]),
                     'new_start': int(m[3]), 'lines': []}
                while old_left or new_left:
                    i += 1
                    if i >= len(lines):
                        raise ValueError('Truncated hunk: ' + line)
                    item = lines[i]
                    if item.startswith('\\ No newline'):
                        continue
                    if not item or item[0] not in ' +-':
                        raise ValueError('Malformed hunk: ' + item)
                    h['lines'].append(item)
                    old_left -= item[0] in ' -'
                    new_left -= item[0] in ' +'
                    if old_left < 0 or new_left < 0:
                        raise ValueError('Invalid hunk counts')
                current['hunks'].append(h)
        i += 1
    return files


def find_lines(haystack, needle):
    if not needle:
        return []
    return [i + 1 for i, line in enumerate(haystack)
            if line == needle[0] and haystack[i:i + len(needle)] == needle]


def normalize(lines):
    return [re.sub(r'\s+', '', line) for line in lines if line.strip()]


def change_blocks(lines):
    blocks = []
    active = []
    for line in lines + [' ']:
        if line[0] in '+-':
            active.append(line)
        elif active:
            blocks.append({'before': [x[1:] for x in active if x[0] == '-'],
                           'after': [x[1:] for x in active if x[0] == '+']})
            active = []
    return blocks


def audit_hunk(file, hunk, source):
    old = [x[1:] for x in hunk['lines'] if x[0] in ' -']
    new = [x[1:] for x in hunk['lines'] if x[0] in ' +']
    lines = source.splitlines() if source is not None else []
    blocks = change_blocks(hunk['lines'])
    for b in blocks:
        b['after_lines'] = find_lines(lines, b['after'])
        b['before_lines'] = find_lines(lines, b['before'])
        b['after_whitespace_insensitive_lines'] = find_lines(normalize(lines), normalize(b['after']))
        meaningful = [x for x in b['after'] if len(re.sub(r'\W', '', x)) >= 8]
        b['substantial_after'] = bool(meaningful)
    exact_post = find_lines(lines, new)
    exact_pre = find_lines(lines, old)
    if file['deleted']:
        status = 'deleted_path_absent' if source is None else 'deleted_path_exists_review'
    elif source is None:
        status = 'path_missing_review'
    elif new and exact_post and new != old:
        status = 'exact_postimage_region'
    elif exact_pre and old != new and old:
        status = 'preimage_region_survives_review'
    elif blocks and all(b['after'] and b['substantial_after'] and b['after_lines'] for b in blocks):
        status = 'changed_blocks_present_context_diverged'
    elif blocks and all(b['after'] and b['substantial_after'] and b['after_whitespace_insensitive_lines'] for b in blocks):
        status = 'whitespace_insensitive_blocks_review'
    else:
        status = 'unresolved_review'
    return {'path': file['path'], 'old_path': file['old_path'],
            'header': hunk['header'], 'status': status,
            'postimage_lines': exact_post, 'preimage_lines': exact_pre,
            'blocks': blocks}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--ref', default='HEAD')
    parser.add_argument('--inventory', type=Path, required=True)
    parser.add_argument('--canonical-manifest', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Output must be a new directory to preserve previous evidence')
    commit = git(args.source, 'rev-parse', args.ref + '^{commit}').decode().strip()
    tree = git(args.source, 'rev-parse', commit + '^{tree}').decode().strip()
    inventory_bytes = args.inventory.read_bytes()
    inventory = list(csv.DictReader(io.StringIO(inventory_bytes.decode())))
    owners = []
    manifest_hash = None
    if args.canonical_manifest:
        manifest_bytes = args.canonical_manifest.read_bytes()
        manifest_hash = sha(manifest_bytes)
        owners = json.loads(manifest_bytes)['patches']
    loaded = {}
    records = []
    for entry in inventory:
        path = Path(entry['path'])
        data = path.read_bytes()
        if sha(data) != entry['sha256']:
            raise ValueError('Inventory checksum mismatch: ' + str(path))
        digest = sha(data)
        if digest not in loaded:
            loaded[digest] = (data, parse_patch(data.decode(errors='replace')))
        records.append((entry, digest))
    touched = {f[k] for _, files in loaded.values() for f in files for k in ('path', 'old_path')}
    tracked = set(git(args.source, 'ls-tree', '-r', '--name-only', '-z', commit).decode().split('\0'))
    present = sorted(touched & tracked)
    source = {}
    # Archive only committed files into a disposable tree; never checkout/apply
    # to the user's source, index, branch or build directory.
    with tempfile.TemporaryDirectory(prefix='lotus-historical-audit-') as tmp:
        work = Path(tmp)
        if present:
            archive = git(args.source, 'archive', '--format=tar', commit, '--', *present)
            with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
                for member in tar:
                    if not member.isfile():
                        continue
                    content = tar.extractfile(member).read()
                    target = work / member.name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(content)
                    source[member.name] = content.decode(errors='replace')
        results = {}
        for digest, (data, files) in loaded.items():
            check = subprocess.run(['git', 'apply', '--reverse', '--check', '--whitespace=nowarn', '-'],
                                   cwd=work, input=data, capture_output=True)
            hunks = [audit_hunk(f, h, source.get(f['path'])) for f in files for h in f['hunks']]
            counts = dict(Counter(h['status'] for h in hunks))
            binary = [f['path'] for f in files if f['binary']]
            if check.returncode == 0:
                classification = 'reverse_apply_check_pass'
            elif hunks and all(h['status'] == 'exact_postimage_region' for h in hunks) and not binary:
                classification = 'all_postimage_regions_present'
            else:
                classification = 'needs_review'
            paths = {f['path'] for f in files}
            candidates = [{'id': str(o.get('contract_id', o.get('canonical_id', ''))),
                           'patch': o.get('canonical_patch_path'), 'subject': o['subject']}
                          for o in owners if paths.intersection(o.get('files', []))]
            results[digest] = {'classification': classification,
                               'reverse_check_exit': check.returncode,
                               'reverse_check_stderr': check.stderr.decode(errors='replace')[:12000],
                               'hunk_counts': counts, 'hunks': hunks, 'binary_paths': binary,
                               'overlapping_current_owners_candidates_only': candidates,
                               'runtime_validation': 'not_run', 'semantic_equivalence': 'not_established'}
    args.output.mkdir(parents=True)
    patch_rows = []
    hunk_rows = []
    for entry, digest in records:
        r = results[digest]
        patch_rows.append({'set': entry['set'], 'layer': entry['layer'], 'patch': entry['patch'],
                           'path': entry['path'], 'sha256': digest, 'classification': r['classification'],
                           'hunks': len(r['hunks']), 'hunk_counts': json.dumps(r['hunk_counts'], sort_keys=True),
                           'runtime_validation': 'not_run', 'semantic_equivalence': 'not_established'})
        for h in r['hunks']:
            hunk_rows.append({'set': entry['set'], 'patch': entry['patch'], 'path': h['path'],
                              'header': h['header'], 'status': h['status'],
                              'postimage_lines': json.dumps(h['postimage_lines']),
                              'preimage_lines': json.dumps(h['preimage_lines'])})
    for filename, rows in [('patches.csv', patch_rows), ('hunks.csv', hunk_rows)]:
        with (args.output / filename).open('w') as f:
            fields = list(rows[0]) if rows else ['status']
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
    hunk_summary = dict(Counter(h['status'] for r in results.values() for h in r['hunks']))
    report = {'source_commit': commit, 'source_tree': tree,
              'invocation': [sys.executable, *sys.argv],
              'inventory_sha256': sha(inventory_bytes), 'manifest_sha256': manifest_hash,
              'script_sha256': sha(Path(__file__).read_bytes()),
              'patch_entries': len(records), 'unique_payloads': len(results),
              'summary': dict(Counter(r['classification'] for r in results.values())),
              'hunk_summary': hunk_summary,
              'results_by_sha256': results}
    (args.output / 'audit.json').write_text(json.dumps(report, indent=2) + '\n')
    summary = ['# Historical optimization source audit', '',
               f'Source `{commit}`, tree `{tree}`.', '',
               f'{len(records)} patch entries; {len(results)} unique payloads.', '',
               '| Mechanical result | Unique payloads |', '|---|---:|']
    summary.extend(f'| {key} | {count} |' for key, count in report['summary'].items())
    summary += ['', '| Hunk result | Count |', '|---|---:|']
    summary.extend(f'| {key} | {count} |' for key, count in hunk_summary.items())
    summary += ['', '## Interpretation', '',
                'Reverse-apply success means the original diff can be reversed against this committed source. '
                'It does not establish reachability, lock scope, configuration, correctness or speed.', '',
                'Unmatched/preimage results need review: subsequent refactoring, fixes, native consensus adaptations, '
                'moves and superseding implementations can all change text. They are not automatic evidence of loss. '
                'Whitespace matches are review hints; their line numbers refer to the normalized nonempty-line stream.', '',
                'Binary, mode-only and renamed files can require manual review. Owner candidates are file-overlap hints only. '
                'No builds, tests or benchmarks run. Historical patches are independent comparisons, not replayed in sequence.', '',
                'See patches.csv, hunks.csv and audit.json for every patch, hunk, change block and diagnostic.']
    (args.output / 'REPORT.md').write_text('\n'.join(summary) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'results_by_sha256'}))


if __name__ == '__main__':
    main()
