#!/usr/bin/env python3
"""Materialize global identities in the single ordered candidate manifest.

Unvalidated source parents/trees stay null; historical split trees are provenance,
never substituted for source identities after a repair.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path


def sha(value):
    return hashlib.sha256(value).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--data', type=Path)
    args = parser.parse_args()
    path = args.candidate / 'daemon/patch-audit/progression/canonical-manifest.json'
    manifest = json.loads(path.read_text())
    manifest['schema'] = 2
    manifest['layering_contract'] = 'One shared ABC/eCash optimization base preserves eCash consensus. Implement each generic optimization once; add minimal adapters and genuinely V2-specific mechanisms after the explicit V2 boundary. Historical V2 assumptions in shared code are backport defects, not authorized consensus changes.'
    manifest['hash_boundary_contract'] = 'User policy: shared eCash cryptographic identifiers, including internal batch IDs, use SHA256/SHA256d. BLAKE3 vendor and any hash adaptation remain entirely after the V2 boundary. PoW, signature transcripts and commitment hashes are separate explicit decisions; no blanket substitution or tree-structure performance claim.'
    manifest['patch_policy'] = 'One purposeful change, including its implementation, required declarations/build wiring and regressions. Fold later-discovered defects into their first responsible owner; preserve repair provenance separately.'
    prefix = sha(manifest['base'].encode())
    manifest['baseline'] = {'global_number': 0, 'source_commit': manifest['base'], 'prefix_sha256': prefix,
                            'layer': 'ABC baseline', 'original_ids': ['ABC baseline']}
    spec = importlib.util.spec_from_file_location('progression', Path(__file__).with_name('patch-progression.py'))
    driver = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(driver)
    contracts = json.loads(path.with_name('contracts.json').read_text())['patches']
    parent = manifest['base']
    for index, entry in enumerate(manifest['patches'], 1):
        entry.setdefault('canonical_id', 'split-' + str(entry['split_index']))
        entry.setdefault('contract_id', str(entry['split_index']))
        relative = 'daemon/patches/' + entry['series'] + '/' + entry['file']
        mailbox_hash = sha((args.candidate / relative).read_bytes())
        gate_digest = sha(json.dumps(driver.validation_requirements(contracts[entry['contract_id']]), sort_keys=True).encode())
        prefix = sha((prefix + '\0' + entry['series'] + '/' + entry['file'] + '\0' + mailbox_hash + '\0' + gate_digest).encode())
        entry.update(global_number=index, layer_number=entry['number'], layer=entry['series'],
                     canonical_patch_path=relative, mailbox_sha256=mailbox_hash, prefix_sha256=prefix,
                     original_ids=entry.get('original_ids', [entry['original_patch']]),
                     contract_ref=f"contracts.json#/patches/{entry['contract_id']}", repair_ledger_ref='repairs.json',
                     canonical_parent_commit=parent, canonical_source_commit=None, canonical_source_tree=None)
        record = args.data / f'patch_{index:03}.json' if args.data else None
        if record and record.exists():
            evidence = json.loads(record.read_text())
            if evidence.get('prefix_sha256') == prefix and evidence.get('source_sha'):
                entry['canonical_source_commit'] = evidence['source_sha']
                entry['canonical_source_tree'] = evidence['source_tree']
        parent = entry['canonical_source_commit']
    manifest['v2_boundary_global_number'] = next(p['global_number'] for p in manifest['patches'] if p['series'] == 'v2')
    manifest['source_identity_policy'] = 'canonical_* fields describe actual replay; null means not yet established. sha/tree/parent remain immutable split-stage provenance and are not repaired-source identities.'
    path.write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps({'patches': len(manifest['patches']), 'v2_boundary': manifest['v2_boundary_global_number']}))


if __name__ == '__main__':
    main()
