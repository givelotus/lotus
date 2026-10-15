#!/usr/bin/env python3
"""Stage a verified Lotus Guix archive in the component-release artifact format."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    'component_release', Path(__file__).with_name('component-release.py'))
release = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release)


def command_output(args):
    return subprocess.check_output([str(arg) for arg in args], text=True).strip()


def parse_inputs(path, manifest):
    values = {}
    for line in Path(path).read_text().splitlines():
        key, separator, value = line.partition('=')
        if not separator or not key or key in values:
            raise ValueError('Malformed or duplicate Guix input record')
        values[key] = value
    if values.get('source_commit') != manifest['source_commit']:
        raise ValueError('Guix source commit differs from component manifest')
    if values.get('source_tree') != manifest['source_tree']:
        raise ValueError('Guix source tree differs from component manifest')
    if values.get('chronik') != 'ON' or values.get('nng') != 'ON':
        raise ValueError('Lotus release must retain its reviewed Chronik and NNG selections')
    for key in ('adapted_commit', 'adapted_tree', 'source_date_epoch'):
        if not values.get(key):
            raise ValueError(f'Missing Guix input field: {key}')
    return values


def archive_members(archive, tag, binaries):
    prefix = tag + '/'
    with tarfile.open(archive, 'r:gz') as bundle:
        names = set(bundle.getnames())
    if any(name and name != tag and not name.startswith(prefix) for name in names):
        raise ValueError('Guix archive contains paths outside its versioned package directory')
    required = {prefix + 'COPYING', *(prefix + 'bin/' + binary for binary in binaries)}
    missing = required - names
    if missing:
        raise ValueError('Guix archive is missing required release files: ' + ', '.join(sorted(missing)))
    return names


def package(root, source, upstream, raw_archive, inputs_path, dist, target):
    component = 'lotusd'
    release.verify(root, upstream, component)
    manifest_path = release.path_for(root, component) / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    if target != 'x86_64-linux-gnu':
        raise ValueError('Guix packaging currently supports x86_64-linux-gnu only')
    if command_output(['git', '-C', source, 'rev-parse', 'HEAD']) != manifest['source_commit']:
        raise ValueError('Release source commit differs from component manifest')
    if command_output(['git', '-C', source, 'rev-parse', 'HEAD^{tree}']) != manifest['source_tree']:
        raise ValueError('Release source tree differs from component manifest')
    inputs = parse_inputs(inputs_path, manifest)
    archive_members(raw_archive, manifest['tag'], manifest['binaries'])

    dist.mkdir(parents=True, exist_ok=True)
    archive = dist / f"{manifest['tag']}-{target}.tar.gz"
    shutil.copyfile(raw_archive, archive)
    source_archive = dist / manifest['source_archive']
    release.verify(root, upstream, component, source_archive)
    guix_source = inputs_path.parent / 'src' / f"{manifest['tag']}-source.tar.gz"
    guix_source_archive = dist / f"{manifest['tag']}-guix-source.tar.gz"
    if not guix_source.is_file():
        raise ValueError('Guix output is missing the exact adapted source archive')
    shutil.copyfile(guix_source, guix_source_archive)

    with tempfile.TemporaryDirectory(prefix='guix-release-smoke-') as temp:
        with tarfile.open(archive, 'r:gz') as bundle:
            bundle.extractall(temp, filter='data')
        binary_dir = Path(temp) / manifest['tag'] / 'bin'
        versions = {binary: command_output([binary_dir / binary, '--version'])
                    for binary in manifest['binaries']}
    if any(manifest['native_version'] not in text for text in versions.values()):
        raise ValueError('Packaged Guix binary version differs from reviewed native version')

    build_info = {
        'target': target,
        'source_commit': manifest['source_commit'],
        'source_tree': manifest['source_tree'],
        'build_method': 'GNU Guix',
        'guix_source_commit': inputs['adapted_commit'],
        'guix_source_tree': inputs['adapted_tree'],
        'guix_source_date_epoch': int(inputs['source_date_epoch']),
        'guix_features': {'chronik': inputs['chronik'], 'nng': inputs['nng']},
        'versions': versions,
        'tests': 'Guix build workflow C++ checks, security and symbol checks passed',
        'reproducibility': 'pending; publication is gated on matching independent Guix replicas',
        'guix_source_archive': guix_source_archive.name,
        'guix_source_archive_sha256': hashlib.sha256(guix_source_archive.read_bytes()).hexdigest(),
        'behavior': 'genesis wallet and Chronik smoke passed; full mainnet synchronization not established',
        'toolchains': {
            'guix_bootstrap_commit': Path(root, 'daemon/guix-bootstrap-version').read_text().strip(),
            'guix_environment_commit': 'c5eee3336cc1d10a3cc1c97fde2809c3451624d3',
            'compiler': 'GCC 14.3.0',
            'target_libc': 'glibc 2.31',
            'rust': manifest['toolchains']['rust'],
            'python': '3.11.14',
            'clang': '18',
        },
    }
    (dist / f'build-info-{target}.json').write_text(json.dumps(build_info, indent=2) + '\n')
    shutil.copyfile(manifest_path, dist / 'manifest.json')
    shutil.copyfile(release.path_for(root, component) / 'NOTES.md', dist / 'NOTES.md')
    shutil.copyfile(release.path_for(root, component) / 'Dockerfile', dist / 'Dockerfile')
    outputs = [archive, source_archive, guix_source_archive, dist / 'manifest.json',
               dist / f'build-info-{target}.json', dist / 'NOTES.md', dist / 'Dockerfile']
    for path in outputs:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        (dist / (path.name + '.sha256')).write_text(f'{digest}  {path.name}\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--upstream', required=True, type=Path)
    parser.add_argument('--archive', required=True, type=Path)
    parser.add_argument('--inputs', required=True, type=Path)
    parser.add_argument('--dist', required=True, type=Path)
    parser.add_argument('--target', default='x86_64-linux-gnu')
    args = parser.parse_args()
    package(ROOT, args.source.resolve(), args.upstream.resolve(), args.archive.resolve(),
            args.inputs.resolve(), args.dist.resolve(), args.target)


if __name__ == '__main__':
    main()
