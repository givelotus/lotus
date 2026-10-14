#!/usr/bin/env python3
"""Build a native CLI/desktop archive with dependency notices and checksums."""
import argparse
import hashlib
import json
import os
import plistlib
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--cli-only', action='store_true', help='omit the desktop GUI')
options = parser.parse_args()


def run(*args):
    return subprocess.check_output(args, text=True)


host = next(line.split(': ', 1)[1] for line in run('rustc', '-vV').splitlines()
            if line.startswith('host: '))
if not (host.endswith('apple-darwin') or host.endswith('unknown-linux-gnu')):
    raise SystemExit('Packaging currently supports native macOS and GNU/Linux builds.')
build = ['cargo', 'build', '--locked', '--release', '--target', host, '-p', 'lotus-miner-cli']
if not options.cli_only:
    build += ['-p', 'lotus-miner-gui']
subprocess.run(build, check=True)
metadata = json.loads(run('cargo', 'metadata', '--locked', '--format-version', '1',
                         '--filter-platform', host))
packages = {p['id']: p for p in metadata['packages']}
nodes = {n['id']: n for n in metadata['resolve']['nodes']}
cli = next(p for p in packages.values() if p['name'] == 'lotus-miner-cli')
entrypoints = {'lotus-miner-cli'} if options.cli_only else {'lotus-miner-cli', 'lotus-miner-gui'}
pending = [p['id'] for p in packages.values() if p['name'] in entrypoints]
selected = set()
while pending:
    package_id = pending.pop()
    if package_id in selected:
        continue
    selected.add(package_id)
    pending.extend(nodes[package_id]['dependencies'])
component = "lotus-miner-cli" if options.cli_only else "lotus-miner"
name = f"{component}-{cli['version']}-{host}"
dist = ROOT / 'dist'
dist.mkdir(exist_ok=True)
# Respect Cargo's target directory override (e.g. shared CI caches).
target = Path(metadata['target_directory'])
with tempfile.TemporaryDirectory(prefix='lotus-miner-package-') as temporary:
    stage = Path(temporary) / name
    (stage / 'bin').mkdir(parents=True)
    shutil.copy2(target / host / 'release' / 'lotus-miner-cli', stage / 'bin')
    if not options.cli_only:
        gui_binary = target / host / 'release' / 'lotus-miner-gui'
        if host.endswith('apple-darwin'):
            app = stage / 'Lotus GPU Miner.app'
            contents = app / 'Contents'
            (contents / 'MacOS').mkdir(parents=True)
            shutil.copy2(gui_binary, contents / 'MacOS' / 'lotus-miner-gui')
            info = {'CFBundleExecutable': 'lotus-miner-gui',
                    'CFBundleIdentifier': 'org.givelotus.gpu-miner',
                    'CFBundleName': 'Lotus GPU Miner', 'CFBundlePackageType': 'APPL',
                    'CFBundleShortVersionString': cli['version'],
                    'CFBundleVersion': cli['version'], 'NSHighResolutionCapable': True}
            (contents / 'Info.plist').write_bytes(plistlib.dumps(info))
        else:
            shutil.copy2(gui_binary, stage / 'bin')
    for filename in ('README.md', 'LICENSE', 'config.example.toml'):
        shutil.copy2(ROOT / filename, stage / filename)
    notices = []
    for package_id in sorted(selected):
        package = packages[package_id]
        source = Path(package['manifest_path']).parent
        license_paths = set()
        for pattern in ('LICENSE*', 'LICENCE*', 'COPYING*', 'NOTICE*', 'license*',
                        'licence*', '*/LICENSE*', '*/COPYING*'):
            license_paths.update(p for p in source.glob(pattern) if p.is_file())
        if package.get('license_file'):
            license_paths.add(source / package['license_file'])
        if package['source'] is None:
            license_paths.add(ROOT / 'LICENSE')
        supplement = ROOT / 'licenses' / f"{package['name']}-{package['version']}"
        if supplement.is_dir():
            license_paths.update(p for p in supplement.iterdir() if p.is_file())
        if not any(p.name.upper().startswith(('LICENSE', 'COPYING', 'LICENCE')) for p in license_paths):
            expression = package.get('license') or ''
            standard = {
                'MIT': 'MIT', 'Apache-2.0': 'Apache-2.0',
                'MIT OR Apache-2.0': 'Apache-2.0',
                'Apache-2.0 OR MIT': 'Apache-2.0',
                'MIT/Apache-2.0': 'Apache-2.0',
            }.get(expression)
            if standard:
                license_paths.add(ROOT / 'licenses' / f'{standard}.txt')
                # Preserve every source notice when upstream omitted a license file.
                shutil.copytree(source, stage / 'license-sources' / f"{package['name']}-{package['version']}")
            else:
                raise SystemExit(f"Missing license text for {package['name']} {package['version']}")
        destination = stage / 'licenses' / f"{package['name']}-{package['version']}"
        destination.mkdir(parents=True)
        for index, path in enumerate(sorted(license_paths)):
            shutil.copy2(path, destination / f'{index}-{path.name}')
        notices.append({key: package.get(key) for key in
                        ('name', 'version', 'authors', 'license', 'repository', 'source')})
    (stage / 'DEPENDENCIES.json').write_text(json.dumps(notices, indent=2) + '\n')
    (stage / 'THIRD-PARTY-NOTICES.txt').write_text(
        'See DEPENDENCIES.json for names, authors, licenses and source locations.\n'
        'licenses/ preserves distributed license files and documented supplements.\n'
        'Where no dedicated license text was distributed, the selected standard\n'
        'MIT or Apache-2.0 license is supplied and the complete published crate\n'
        'source is retained in license-sources/ to preserve original notices.\n')
    (stage / 'BUILD.txt').write_text(run('rustc', '-vV') + run('cargo', '-V') +
                                   'Native build; OpenCL GPU driver/runtime required.\n')
    for app in stage.glob('*.app'):
        resources = app / 'Contents' / 'Resources'
        resources.mkdir()
        for filename in ('README.md', 'LICENSE', 'DEPENDENCIES.json', 'BUILD.txt',
                         'THIRD-PARTY-NOTICES.txt', 'config.example.toml'):
            shutil.copy2(stage / filename, resources / filename)
        for directory in ('licenses', 'license-sources'):
            if (stage / directory).exists():
                shutil.copytree(stage / directory, resources / directory)
        subprocess.run(['codesign', '--force', '--sign', '-', str(app)], check=True)
        subprocess.run(['codesign', '--verify', '--strict', str(app)], check=True)
    archive = dist / f'{name}.tar.gz'
    with tarfile.open(archive, 'w:gz') as output:
        output.add(stage, arcname=name)
checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
archive.with_suffix(archive.suffix + '.sha256').write_text(f'{checksum}  {archive.name}\n')
print(archive)
