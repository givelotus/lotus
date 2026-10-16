#!/usr/bin/env python3
"""Small real-Git fixtures for fail-closed first-boundary construction."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('builder', Path(__file__).resolve().parents[1] /
                                              'scripts/consolidate-v2-candidate.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


def run(root, *args):
    return builder.git(root, *args).stdout.decode().strip()


def commit(root, message):
    run(root, 'add', '.')
    return run(root, '-c', 'user.name=Temporary fixture', '-c', 'user.email=fixture@invalid',
               'commit', '--no-gpg-sign', '-m', message) and run(root, 'rev-parse', 'HEAD')


class Construction(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='lotus-consolidation-test-')
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.native, self.source = self.home / 'native', self.home / 'source'
        for path in (self.native, self.source):
            path.mkdir()
            run(path, 'init', '-q')
        (self.native / 'owned.txt').write_text('base\n')
        self.base = commit(self.native, 'base')
        self.parent_tree = run(self.native, 'rev-parse', 'HEAD^{tree}')
        (self.native / 'owned.txt').write_text('owned\n')
        first = commit(self.native, 'owned change')
        self.first_tree = run(self.native, 'rev-parse', 'HEAD^{tree}')
        self.binary = bytes(range(256)) * 4
        (self.native / 'future.bin').write_bytes(self.binary)
        second = commit(self.native, 'future binary')
        self.final_tree = run(self.native, 'rev-parse', 'HEAD^{tree}')
        directory = self.source / 'daemon/patches/v2'
        directory.mkdir(parents=True)
        records = []
        for ordinal, revision in enumerate((first, second)):
            raw = builder.git(self.native, 'format-patch', '-1', revision, '--stdout', '--binary', '--full-index').stdout
            name = f'{ordinal:03}-fixture.patch'
            (directory / name).write_bytes(raw)
            path, section = builder.sections(raw)[0]
            group = 'inherited' if ordinal == 0 else 'future'
            unit = {'id': f'{ordinal:03}:00', 'path': path, 'group': group,
                    'ownership': 'whole_file_diff', 'section_sha256': builder.sha(section),
                    'hunk_headers': [m[0].decode() for m in builder.re.finditer(rb'^@@.*?@@.*$', section, builder.re.M)],
                    'binary': ordinal == 1}
            records.append({'ordinal': ordinal, 'mailbox': name, 'mailbox_sha256': builder.sha(raw),
                            'recorded_source_commit': revision, 'recorded_replay_commit': revision,
                            'original_parent_tree': self.parent_tree if ordinal == 0 else self.first_tree,
                            'original_result_tree': self.first_tree if ordinal == 0 else self.final_tree,
                            'units': [unit]})
        manifest = 'daemon/patches/v2/series'
        (self.source / manifest).write_text(''.join(p['mailbox'] + '\n' for p in records))
        evidence_path = 'daemon/evidence.json'
        evidence = {'base': self.base, 'entries': [
            {'file': p['mailbox'], 'sha256': p['mailbox_sha256'], 'tree': p['original_result_tree'],
             'expected_tree': p['original_result_tree'], 'expected_commit': p['recorded_source_commit'],
             'replay_commit': p['recorded_replay_commit']} for p in records]}
        (self.source / evidence_path).write_text(json.dumps(evidence))
        source_pin = commit(self.source, 'source mailboxes')
        self.ledger_path = self.source / 'docs/plans/lotus-v2-consolidation-ledger.json'
        self.ledger_path.parent.mkdir(parents=True)
        self.ledger = {'schema_version': 1, 'base_commit': self.base, 'monorepo_commit': source_pin,
                       'source_manifest': manifest, 'source_manifest_sha256': builder.sha((self.source / manifest).read_bytes()),
                       'replay_evidence': evidence_path, 'replay_evidence_sha256': builder.sha((self.source / evidence_path).read_bytes()),
                       'expected_final_tree': self.final_tree, 'source_patch_count': 2,
                       'proposed_order': ['inherited', 'future'], 'mailboxes': records,
                       'groups': [{'id': 'inherited', 'units': ['000:00'], 'depends_on': [],
                                   'proposed_subject': 'Inherited fixture draft', 'verification': {'status': 'pending'}},
                                  {'id': 'future', 'units': ['001:00']}],
                       'construction_policy': {'first_boundary': {'group': 'inherited', 'base': self.base,
                                                                  'units': ['000:00'], 'source_mailboxes': [0]}},
                       'binary_preservation': {'unit': '001:00', 'mailbox': records[1]['mailbox'],
                                               'section_sha256': records[1]['units'][0]['section_sha256'],
                                               'path': 'future.bin', 'git_blob': run(self.native, 'rev-parse', 'HEAD:future.bin'),
                                               'sha256': builder.sha(self.binary), 'bytes': len(self.binary)}}
        self.pin()
        self.target, self.output = self.home / 'candidate', self.home / 'evidence'

    def pin(self):
        self.ledger_path.write_text(json.dumps(self.ledger, indent=2) + '\n')
        self.ledger_commit = commit(self.source, 'ledger')
        self.digest = builder.sha(self.ledger_path.read_bytes())

    def construct(self):
        return builder.construct(self.source, self.native, self.target, self.output,
                                 self.ledger_commit, self.digest)

    def test_only_owned_units_and_preserved_binary(self):
        before = run(self.native, 'rev-parse', 'HEAD')
        report = self.construct()
        self.assertEqual(report['status'], 'draft_constructed_gates_pending')
        self.assertEqual(report['candidate_tree'], self.first_tree)
        self.assertEqual(len(report['units']), 1)
        self.assertEqual(report['conflicts'], [])
        self.assertEqual(report['resolutions'], [])
        self.assertFalse((self.target / 'future.bin').exists())
        self.assertEqual((self.output / 'preserved-inputs/bip340_test_vectors.csv').read_bytes(), self.binary)
        self.assertEqual(run(self.native, 'rev-parse', 'HEAD'), before)
        self.assertEqual(report['units'][0]['source_after'], report['units'][0]['candidate_after'])
        self.assertFalse(run(self.source, 'status', '--porcelain'))

    def test_existing_target_and_evidence_refused(self):
        for path in (self.target, self.output):
            path.mkdir()
            with self.assertRaisesRegex(builder.Refusal, 'already exists'):
                self.construct()
            path.rmdir()

    def test_dirty_root_refused_before_mutation(self):
        (self.source / 'untracked').write_text('keep')
        with self.assertRaisesRegex(builder.Refusal, 'dirty'):
            self.construct()
        self.assertFalse(self.target.exists())
        self.assertFalse(self.output.exists())

    def test_wrong_ledger_digest_refused(self):
        self.digest = '0' * 64
        with self.assertRaisesRegex(builder.Refusal, 'SHA256 mismatch'):
            self.construct()
        self.assertFalse(self.output.exists())

    def test_pinned_mailbox_tamper_refused(self):
        patch = self.source / 'daemon/patches/v2/000-fixture.patch'
        patch.write_bytes(patch.read_bytes() + b'tamper\n')
        commit(self.source, 'unauthorized source change')
        with self.assertRaisesRegex(builder.Refusal, 'differs from pinned commit'):
            self.construct()
        self.assertFalse(self.output.exists())

    def test_duplicate_owner_refused(self):
        self.ledger['groups'][1]['units'].append('000:00')
        self.pin()
        with self.assertRaisesRegex(builder.Refusal, 'ownership coverage'):
            self.construct()
        self.assertFalse(self.output.exists())

    def test_section_hash_refused(self):
        self.ledger['mailboxes'][0]['units'][0]['section_sha256'] = '0' * 64
        self.pin()
        with self.assertRaisesRegex(builder.Refusal, 'section hash'):
            self.construct()
        self.assertFalse(self.output.exists())

    def test_conflict_preserves_input_and_never_commits(self):
        # Only the second delta is owned: it depends on the omitted first
        # topic's text, so exact context application to base must fail closed.
        (self.native / 'owned.txt').write_text('requires omitted context\n')
        parent = run(self.native, 'rev-parse', 'HEAD')
        revision = commit(self.native, 'later owned delta')
        raw = builder.git(self.native, 'format-patch', '-1', revision, '--stdout', '--binary', '--full-index').stdout
        path, section = builder.sections(raw)[0]
        original = self.ledger['mailboxes'][0]
        original['units'][0]['group'] = 'future'
        entry = copy.deepcopy(original)
        entry.update(ordinal=2, mailbox='002-conflict.patch', mailbox_sha256=builder.sha(raw),
                     recorded_source_commit=revision, recorded_replay_commit=revision,
                     original_parent_tree=self.final_tree, original_result_tree=run(self.native, 'rev-parse', 'HEAD^{tree}'))
        entry['units'] = [{'id': '002:00', 'path': path, 'group': 'inherited', 'ownership': 'whole_file_diff',
                           'section_sha256': builder.sha(section), 'binary': False,
                           'hunk_headers': [m[0].decode() for m in builder.re.finditer(rb'^@@.*?@@.*$', section, builder.re.M)]}]
        (self.source / 'daemon/patches/v2/002-conflict.patch').write_bytes(raw)
        manifest = self.source / self.ledger['source_manifest']
        manifest.write_text(manifest.read_text() + entry['mailbox'] + '\n')
        evidence_path = self.source / self.ledger['replay_evidence']
        evidence = json.loads(evidence_path.read_text())
        evidence['entries'].append({'file': entry['mailbox'], 'sha256': entry['mailbox_sha256'],
                                    'tree': entry['original_result_tree'], 'expected_tree': entry['original_result_tree'],
                                    'expected_commit': revision, 'replay_commit': revision})
        evidence_path.write_text(json.dumps(evidence))
        self.ledger['monorepo_commit'] = commit(self.source, 'extended source fixture')
        self.ledger.update(source_patch_count=3, expected_final_tree=entry['original_result_tree'],
                           source_manifest_sha256=builder.sha(manifest.read_bytes()),
                           replay_evidence_sha256=builder.sha(evidence_path.read_bytes()))
        self.ledger['mailboxes'].append(entry)
        self.ledger['groups'][0]['units'] = ['002:00']
        self.ledger['groups'][1]['units'] = ['000:00', '001:00']
        self.ledger['construction_policy']['first_boundary'].update(units=['002:00'], source_mailboxes=[2])
        self.pin()
        with self.assertRaisesRegex(builder.Refusal, 'context conflict'):
            self.construct()
        report = json.loads((self.output / 'provenance.json').read_text())
        self.assertEqual(report['status'], 'blocked_no_promotion')
        self.assertIsNone(report['candidate_commit'])
        self.assertEqual(report['partial_tree'], self.parent_tree)
        self.assertEqual((self.output / 'units/002-00.diff').read_bytes(), section)
        self.assertEqual(run(self.target, 'rev-parse', 'HEAD'), self.base)
        self.assertEqual(run(self.native, 'rev-parse', 'HEAD'), revision)
        self.assertTrue(parent)


if __name__ == '__main__':
    unittest.main()
