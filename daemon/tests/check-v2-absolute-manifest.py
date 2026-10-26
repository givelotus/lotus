#!/usr/bin/env python3
"""Exercise absolute-profile loader in fresh offline homes; starts no peers."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import subprocess


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--daemon', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=False, exist_ok=False)
    manifest = json.loads(args.manifest.read_text())
    results = []

    def run(name, value, accepted=False, home=None):
        path = args.output / (name + '.json')
        path.write_text(json.dumps(value, indent=2) + '\n')
        home = home or args.output / (name + '-home')
        command = [str(args.daemon.resolve()), '-lotusv2development',
                   str(path.resolve()), str(home.resolve()), 'status']
        proc = subprocess.run(command, capture_output=True, text=True, timeout=30)
        row = dict(name=name, command=command, returncode=proc.returncode,
                   stdout=proc.stdout, stderr=proc.stderr)
        results.append(row)
        (args.output / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
        assert (proc.returncode == 0) == accepted, row
        if accepted:
            status = json.loads(proc.stdout)
            assert status['tip'] == manifest['header']['genesis_id'], row
            assert status['height'] == 0, row
        return home

    home = run('valid', manifest, True)
    run('reopen', manifest, True, home)
    variants = {}
    for name in ('schema1', 'missing-version', 'wrong-version', 'ten-fields',
                 'zero-work', 'wrong-tail', 'zero-floor', 'wrong-chain'):
        variants[name] = copy.deepcopy(manifest)
    variants['schema1']['schema'] = 1
    del variants['missing-version']['tail_formula_version']
    variants['wrong-version']['tail_formula_version'] = 2
    variants['ten-fields']['monetary'] = manifest['monetary'][:10]
    variants['zero-work']['monetary'][11] = '00' * 32
    variants['wrong-tail']['monetary'][10] += 1
    variants['zero-floor']['monetary'][6] = 0
    variants['wrong-chain']['header']['chain_id'] = '00' * 32
    for name, value in variants.items():
        run(name, value)
    before = {str(p.relative_to(home)): digest(p) for p in home.rglob('*') if p.is_file()}
    incompatible = copy.deepcopy(manifest)
    incompatible['monetary'][7] += 1
    run('incompatible-home', incompatible, home=home)
    after = {str(p.relative_to(home)): digest(p) for p in home.rglob('*') if p.is_file()}
    assert before == after, 'incompatible profile changed existing home'
    evidence = dict(daemon_sha256=digest(args.daemon), manifest_sha256=digest(args.manifest),
                    checks=len(results), home_unchanged_on_profile_refusal=True,
                    scope='offline profile initialization/reopen/refusal; no network or block acceptance')
    (args.output / 'summary.json').write_text(json.dumps(evidence, indent=2) + '\n')
    print(json.dumps(evidence, sort_keys=True))


if __name__ == '__main__':
    main()
