#!/usr/bin/env python3
"""Construct only the ledger's first inherited topic in fresh isolated paths.

This produces a draft with all build/behavior gates pending, never a promoted
series. A context failure preserves exact inputs and partial provenance; it
never invokes three-way merge, imports final files, exports mailboxes or retries.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys


class Refusal(RuntimeError):
    pass


def require(condition, message):
    if not condition:
        raise Refusal(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def git(root, *args, data=None, check=True):
    result = subprocess.run(['git', '-C', str(root), *args], input=data,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if check and result.returncode:
        raise Refusal(result.stderr.decode(errors='replace').strip())
    return result


def safe_path(name):
    path = Path(name)
    require(name and not path.is_absolute() and '..' not in path.parts and
            '.git' not in path.parts and '\\' not in name, 'unsafe source path')
    return path


def sections(raw):
    markers = list(re.finditer(rb'^diff --git a/(.+?) b/(.+)$', raw, re.M))
    require(markers, 'mailbox has no file diffs')
    result = []
    for index, marker in enumerate(markers):
        require(marker[1] == marker[2], 'renames require explicit construction support')
        name = marker[2].decode('utf-8')
        safe_path(name)
        end = markers[index + 1].start() if index + 1 < len(markers) else len(raw)
        section = raw[marker.start():end]
        if index + 1 == len(markers) and b'\n-- \n' in section:
            section = section[:section.rfind(b'\n-- \n') + 1]
        result.append((name, section))
    return result


def pinned_bytes(root, commit, name):
    safe_path(name)
    current = (root / name).read_bytes()
    require(git(root, 'show', f'{commit}:{name}').stdout == current,
            f'source differs from pinned commit: {name}')
    return current


def validate(root, ledger_commit, ledger_sha256, native):
    require(re.fullmatch('[0-9a-f]{40}', ledger_commit), 'exact ledger commit required')
    require(re.fullmatch('[0-9a-f]{64}', ledger_sha256), 'exact ledger SHA256 required')
    require(not git(root, 'status', '--porcelain', '--untracked-files=all').stdout,
            'source root is dirty')
    ledger_path = 'docs/plans/lotus-v2-consolidation-ledger.json'
    raw = pinned_bytes(root, ledger_commit, ledger_path)
    require(sha(raw) == ledger_sha256, 'ledger SHA256 mismatch')
    ledger = json.loads(raw)
    require(ledger['schema_version'] == 1, 'unsupported ledger schema')
    base = ledger['base_commit']
    require(re.fullmatch('[0-9a-f]{40}', base), 'exact base commit required')
    require(git(native, 'rev-parse', f'{base}^{{commit}}').stdout.decode().strip() == base,
            'native base is unavailable')
    source_pin = ledger['monorepo_commit']
    manifest_raw = pinned_bytes(root, source_pin, ledger['source_manifest'])
    evidence_raw = pinned_bytes(root, source_pin, ledger['replay_evidence'])
    require(sha(manifest_raw) == ledger['source_manifest_sha256'], 'manifest hash mismatch')
    require(sha(evidence_raw) == ledger['replay_evidence_sha256'], 'replay evidence hash mismatch')
    names = [line for line in manifest_raw.decode().splitlines() if line and not line.startswith('#')]
    evidence = json.loads(evidence_raw)
    require(evidence['base'] == base, 'replay base mismatch')
    require(len(names) == len(set(names)) == ledger['source_patch_count'] ==
            len(ledger['mailboxes']) == len(evidence['entries']), 'source coverage mismatch')
    groups = {group['id']: group for group in ledger['groups']}
    require(len(groups) == len(ledger['groups']), 'duplicate group')
    require(ledger['proposed_order'][0] == 'inherited', 'first topic must be inherited')
    group = groups['inherited']
    boundary = ledger['construction_policy']['first_boundary']
    require(boundary['group'] == 'inherited' and boundary['base'] == base and
            group['depends_on'] == [], 'invalid first boundary')
    units, selected = {}, []
    previous_tree = git(native, 'rev-parse', f'{base}^{{tree}}').stdout.decode().strip()
    mailbox_root = Path(ledger['source_manifest']).parent
    for ordinal, (name, mailbox, recorded) in enumerate(zip(names, ledger['mailboxes'], evidence['entries'])):
        require(mailbox['ordinal'] == ordinal and mailbox['mailbox'] == name == recorded['file'],
                'mailbox order mismatch')
        raw = pinned_bytes(root, source_pin, str(mailbox_root / safe_path(name)))
        require(sha(raw) == mailbox['mailbox_sha256'] == recorded['sha256'],
                f'mailbox hash mismatch: {name}')
        require(mailbox['original_parent_tree'] == previous_tree and
                mailbox['original_result_tree'] == recorded['tree'] == recorded['expected_tree'] and
                mailbox['recorded_source_commit'] == recorded['expected_commit'] and
                mailbox['recorded_replay_commit'] == recorded['replay_commit'], 'replay provenance mismatch')
        previous_tree = mailbox['original_result_tree']
        by_section = {}
        for unit in mailbox['units']:
            require(unit['id'] not in units and unit['group'] in groups, 'duplicate/unknown owner')
            units[unit['id']] = unit
            by_section.setdefault(unit.get('parent_section_id', unit['id']), []).append(unit)
        parts = sections(raw)
        require(len(parts) == len(by_section), 'file diff ownership coverage mismatch')
        for index, (path, section) in enumerate(parts):
            section_id = f'{ordinal:03}:{index:02}'
            owners = by_section.get(section_id, [])
            require(owners, f'unowned section: {section_id}')
            hunks = list(re.finditer(rb'^@@.*?@@.*$', section, re.M))
            for unit in owners:
                require(unit['path'] == path and unit['section_sha256'] == sha(section) and
                        unit['binary'] == (b'GIT binary patch' in section), 'section hash/path/type mismatch')
            if len(owners) == 1 and owners[0]['ownership'] == 'whole_file_diff':
                require(owners[0]['id'] == section_id, 'whole-file unit ID mismatch')
                require(owners[0]['hunk_headers'] == [h[0].decode() for h in hunks], 'hunk inventory mismatch')
            else:
                require(sorted(u['hunk_index'] for u in owners) == list(range(len(hunks))),
                        'overlapping/incomplete hunk owners')
                for unit in owners:
                    k = unit['hunk_index']
                    end = hunks[k + 1].start() if k + 1 < len(hunks) else len(section)
                    require(unit['ownership'] == 'hunk' and unit['hunk_sha256'] ==
                            sha(section[hunks[k].start():end]) and unit['hunk_headers'] ==
                            [hunks[k][0].decode()], 'hunk hash mismatch')
            for unit in owners:
                if unit['group'] == 'inherited':
                    require(unit['ownership'] == 'whole_file_diff', 'first topic hunk splitting unsupported')
                    selected.append((mailbox, unit, section))
    require(previous_tree == ledger['expected_final_tree'], 'final source tree mismatch')
    tree_ids = sorted({tree for mailbox in ledger['mailboxes']
                       for tree in (mailbox['original_parent_tree'], mailbox['original_result_tree'])})
    checked = git(native, 'cat-file', '--batch-check=%(objectname) %(objecttype)',
                  data=('\n'.join(tree_ids) + '\n').encode()).stdout.decode().splitlines()
    require(checked == [tree + ' tree' for tree in tree_ids], 'source tree objects unavailable')
    all_owned = [unit for owner in groups.values() for unit in owner['units']]
    require(len(all_owned) == len(set(all_owned)) == len(units) and set(all_owned) == set(units),
            'group ownership coverage mismatch')
    for owner in groups.values():
        require(all(units[u]['group'] == owner['id'] for u in owner['units']), 'group ownership mismatch')
    ids = [unit['id'] for _, unit, _ in selected]
    ordinals = list(dict.fromkeys(mailbox['ordinal'] for mailbox, _, _ in selected))
    require(ids == group['units'] == boundary['units'] and
            ordinals == boundary['source_mailboxes'], 'first boundary selection mismatch')
    binary = ledger['binary_preservation']
    owner = units[binary['unit']]
    require(owner['binary'] and owner['section_sha256'] == binary['section_sha256'] and
            owner['path'] == binary['path'], 'binary preservation ownership mismatch')
    binary_raw = git(native, 'cat-file', 'blob', binary['git_blob']).stdout
    require(sha(binary_raw) == binary['sha256'] and len(binary_raw) == binary['bytes'],
            'binary fixture blob mismatch')
    binary_entry = ledger['mailboxes'][int(binary['unit'].split(':', 1)[0])]
    require(binary_entry['mailbox'] == binary['mailbox'], 'binary mailbox ownership mismatch')
    binary_mailbox = pinned_bytes(root, source_pin, str(mailbox_root / binary['mailbox']))
    return ledger, selected, binary_raw, binary_mailbox


def blob(native, tree, path):
    row = git(native, 'ls-tree', tree, '--', path).stdout
    if not row:
        return None
    mode, kind, rest = row.decode().split(' ', 2)
    oid, found = rest.rstrip('\n').split('\t', 1)
    require(kind == 'blob' and found == path, 'unexpected tree entry')
    data = git(native, 'cat-file', 'blob', oid).stdout
    return {'mode': mode, 'git_blob': oid, 'sha256': sha(data), 'bytes': len(data)}


def save(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def construct(root, native, target, output, ledger_commit, ledger_sha256):
    # Reject pre-existing paths (including broken symlinks) before verification
    # and again immediately before mkdir/worktree creation. Never reuse/reset.
    for path in (target, output):
        require(not path.exists() and not path.is_symlink(), f'target already exists: {path}')
    require(target != output and target not in output.parents and output not in target.parents,
            'target and evidence must be separate paths')
    require(root not in target.parents and root not in output.parents and
            native not in target.parents and native not in output.parents,
            'outputs must be outside existing source/native roots')
    ledger, selected, binary_raw, binary_mailbox = validate(root, ledger_commit, ledger_sha256, native)
    output.mkdir(parents=False)
    report = {'schema_version': 1, 'status': 'constructing', 'group': 'inherited',
              'ledger_commit': ledger_commit, 'ledger_sha256': ledger_sha256,
              'source_pin': ledger['monorepo_commit'], 'base_commit': ledger['base_commit'],
              'source_manifest_sha256': ledger['source_manifest_sha256'],
              'replay_evidence_sha256': ledger['replay_evidence_sha256'],
              'target': str(target), 'units': [], 'conflicts': [], 'resolutions': [],
              'candidate_commit': None, 'candidate_tree': None,
              'gates': {'status': 'pending', 'recipe': next(g for g in ledger['groups'] if g['id'] == 'inherited')['verification']},
              'promotion': 'not_authorized', 'scope': 'first inherited draft boundary only'}
    save(output / 'provenance.json', report)
    try:
        preserved = output / 'preserved-inputs'
        preserved.mkdir()
        (preserved / ledger['binary_preservation']['mailbox']).write_bytes(binary_mailbox)
        (preserved / 'bip340_test_vectors.csv').write_bytes(binary_raw)
        save(preserved / 'binary-provenance.json', ledger['binary_preservation'])
        require(not target.exists() and not target.is_symlink(), 'target appeared during verification')
        git(native, 'worktree', 'add', '--detach', str(target), ledger['base_commit'])
        patches = output / 'units'
        patches.mkdir()
        for mailbox, unit, section in selected:
            path = unit['path']
            patch = patches / (unit['id'].replace(':', '-') + '.diff')
            patch.write_bytes(section)
            before_tree = git(target, 'write-tree').stdout.decode().strip()
            record = {'unit': unit['id'], 'path': path, 'mailbox': mailbox['mailbox'],
                      'mailbox_sha256': mailbox['mailbox_sha256'], 'section_sha256': sha(section),
                      'original_parent_tree': mailbox['original_parent_tree'],
                      'original_result_tree': mailbox['original_result_tree'],
                      'source_before': blob(native, mailbox['original_parent_tree'], path),
                      'source_after': blob(native, mailbox['original_result_tree'], path),
                      'candidate_before_tree': before_tree,
                      'candidate_before': blob(target, before_tree, path), 'method': 'git apply --index'}
            check = git(target, 'apply', '--index', '--check', str(patch), check=False)
            if check.returncode:
                record['error'] = check.stderr.decode(errors='replace')
                report['conflicts'].append(record)
                raise Refusal(f'context conflict at {unit["id"]}: {record["error"].strip()}')
            applied = git(target, 'apply', '--index', '--verbose', str(patch))
            record['application_log'] = applied.stderr.decode(errors='replace')
            after_tree = git(target, 'write-tree').stdout.decode().strip()
            record.update(candidate_after_tree=after_tree, candidate_after=blob(target, after_tree, path))
            report['units'].append(record)
            save(output / 'provenance.json', report)
        report['candidate_tree'] = git(target, 'write-tree').stdout.decode().strip()
        message = (next(g for g in ledger['groups'] if g['id'] == 'inherited')['proposed_subject'] + '\n\n'
                   'Draft first consolidation boundary from exact ledger-owned source units.\n'
                   'All configure, build, test and bisectability gates remain pending.\n'
                   'No active series or release assets are changed.\n\n'
                   f'Ledger: {ledger_commit}\nLedger-SHA256: {ledger_sha256}\n'
                   f'Owned units: {len(selected)}; original ordinal/file order.\n')
        git(target, '-c', 'core.hooksPath=/dev/null', '-c', 'user.name=Lotus candidate construction', '-c',
            'user.email=lotus-candidate@invalid', 'commit', '--no-gpg-sign', '-F', '-', data=message.encode())
        report['candidate_commit'] = git(target, 'rev-parse', 'HEAD').stdout.decode().strip()
        require(git(target, 'rev-parse', 'HEAD^{tree}').stdout.decode().strip() == report['candidate_tree'],
                'draft commit tree mismatch')
        require(not git(target, 'status', '--porcelain', '--untracked-files=all').stdout,
                'candidate remains dirty after draft commit')
        report['status'] = 'draft_constructed_gates_pending'
        save(output / 'provenance.json', report)
        return report
    except Exception as error:
        report['status'] = 'blocked_no_promotion'
        report['error'] = str(error)
        if (target / '.git').exists():
            report['partial_tree'] = git(target, 'write-tree', check=False).stdout.decode().strip()
        save(output / 'provenance.json', report)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('source-root', 'native-repo', 'target', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--ledger-commit', required=True)
    parser.add_argument('--ledger-sha256', required=True)
    args = parser.parse_args()
    # Resolve parents, retaining the final symlink so even a broken link refuses.
    try:
        report = construct(args.source_root.resolve(), args.native_repo.resolve(),
                           args.target.parent.resolve() / args.target.name,
                           args.output.parent.resolve() / args.output.name,
                           args.ledger_commit, args.ledger_sha256)
        print(json.dumps({'commit': report['candidate_commit'], 'tree': report['candidate_tree'],
                          'status': report['status'], 'units': len(report['units'])}))
    except (Refusal, ValueError, KeyError, OSError) as error:
        print(f'consolidation refused: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
