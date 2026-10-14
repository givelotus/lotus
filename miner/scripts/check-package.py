#!/usr/bin/env python3
"""Smoke-check locally built packages without starting mining or opening the UI."""
import hashlib
from pathlib import Path
import plistlib
import subprocess
import tarfile
import tempfile

root = Path(__file__).resolve().parents[1]
archives = list((root / 'dist').glob('*.tar.gz'))
if not archives:
    raise SystemExit('No packages found; run scripts/package.py first.')
for archive in archives:
    expected = archive.with_suffix(archive.suffix + '.sha256').read_text().split()[0]
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == expected, archive
    with tempfile.TemporaryDirectory(prefix='lotus-miner-smoke-') as directory:
        with tarfile.open(archive) as source:
            source.extractall(directory, filter='data')
        package = next(Path(directory).iterdir())
        for filename in ('README.md', 'LICENSE', 'DEPENDENCIES.json', 'BUILD.txt',
                         'THIRD-PARTY-NOTICES.txt', 'config.example.toml'):
            assert (package / filename).is_file(), filename
        assert (package / 'licenses').is_dir()
        binaries = [package / 'bin' / 'lotus-miner-cli']
        if (package / 'bin' / 'lotus-miner-gui').exists():
            binaries.append(package / 'bin' / 'lotus-miner-gui')
        for app in package.glob('*.app'):
            contents = app / 'Contents'
            assert (contents / 'Resources' / 'LICENSE').is_file()
            assert (contents / 'Resources' / 'DEPENDENCIES.json').is_file()
            info = plistlib.loads((contents / 'Info.plist').read_bytes())
            binaries.append(contents / 'MacOS' / info['CFBundleExecutable'])
            subprocess.run(['codesign', '--verify', '--strict', str(app)], check=True)
        for binary in binaries:
            # Clap exits before config writes, RPC, OpenCL setup or GUI initialization.
            if '.app' in str(binary) or 'apple-darwin' in archive.name:
                linkage = subprocess.check_output(['otool', '-L', str(binary)], text=True)
                for library in linkage.splitlines()[1:]:
                    assert library.strip().startswith(('/usr/lib/', '/System/Library/')), library
            output = subprocess.check_output([str(binary), '--help'], cwd=directory, text=True)
            assert '--mine-to-address' in output and '--rpc-url' in output
    print(f'Verified {archive.name}')
