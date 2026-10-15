#!/usr/bin/env python3
"""Create conventional .deb and .rpm packages from the verified Lotus archive."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import tempfile


def run(args, env=None):
    subprocess.run([str(arg) for arg in args], check=True, env=env)


def package(archive, manifest_path, notes_path, output, build_info_path):
    manifest = json.loads(Path(manifest_path).read_text())
    if manifest['component'] != 'lotusd' or manifest['tag'] != f"lotusd-v{manifest['native_version']}":
        raise ValueError('Package source is not the reviewed Lotus release manifest')
    if not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', manifest['native_version']):
        raise ValueError('Release version is not a plain semantic version')
    if Path(archive).name != f"{manifest['tag']}-x86_64-linux-gnu.tar.gz":
        raise ValueError('Binary archive version differs from the release manifest')
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    if list(output.glob('lotusd_*_amd64.deb')) or list(output.glob('lotusd-*.rpm')):
        raise ValueError('Output already contains a Debian or RPM package')
    version = manifest['native_version']
    epoch = str(manifest['source_date_epoch'])
    env = {**os.environ, 'SOURCE_DATE_EPOCH': epoch, 'TZ': 'UTC'}

    with tempfile.TemporaryDirectory(prefix='lotusd-system-packages-') as temp:
        work = Path(temp)
        with tarfile.open(archive, 'r:gz') as bundle:
            members = bundle.getmembers()
            expected_prefix = manifest['tag'] + '/'
            for member in members:
                if member.name != manifest['tag'] and not member.name.startswith(expected_prefix):
                    raise ValueError(f'Unexpected path in binary archive: {member.name}')
            bundle.extractall(work, filter='data')
        payload = work / manifest['tag']
        for binary in manifest['binaries']:
            if not (payload / 'bin' / binary).is_file():
                raise ValueError(f'Missing release binary: {binary}')
        shutil.copyfile(manifest_path, payload / 'manifest.json')
        shutil.copyfile(notes_path, payload / 'NOTES.md')

        debroot = work / 'debroot'
        (debroot / 'usr/bin').mkdir(parents=True)
        docdir = debroot / 'usr/share/doc/lotusd'
        docdir.mkdir(parents=True)
        for binary in manifest['binaries']:
            shutil.copy2(payload / 'bin' / binary, debroot / 'usr/bin' / binary)
        shutil.copy2(payload / 'COPYING', docdir / 'copyright')
        shutil.copy2(payload / 'NOTES.md', docdir / 'README.Debian')
        shutil.copy2(payload / 'manifest.json', docdir / 'manifest.json')
        control = debroot / 'DEBIAN'
        control.mkdir()
        (control / 'control').write_text(
            f'Package: lotusd\nVersion: {version}\nArchitecture: amd64\n'
            'Maintainer: Lotus Project <support@givelotus.org>\n'
            'Depends: libc6 (>= 2.31), libgcc-s1, libstdc++6, '
            'libevent-2.1-7t64 | libevent-2.1-7, '
            'libdb5.3++t64 | libdb5.3++\n'
            'Section: net\nPriority: optional\n'
            'Description: Lotus daemon and command-line client\n'
            ' Includes lotusd and lotus-cli built with the in-process Chronik indexer.\n')
        deb = output / f'lotusd_{version}_amd64.deb'
        run(['dpkg-deb', '--build', '--root-owner-group', '--uniform-compression', debroot, deb], env)

        top = work / 'rpmbuild'
        for directory in ('BUILD', 'BUILDROOT', 'RPMS', 'SOURCES', 'SPECS', 'SRPMS'):
            (top / directory).mkdir(parents=True)
        rpmpayload = work / 'rpm-payload'
        (rpmpayload / 'usr/bin').mkdir(parents=True)
        docdir = rpmpayload / 'usr/share/doc/lotusd'
        docdir.mkdir(parents=True)
        licensedir = rpmpayload / 'usr/share/licenses/lotusd'
        licensedir.mkdir(parents=True)
        for binary in manifest['binaries']:
            shutil.copy2(payload / 'bin' / binary, rpmpayload / 'usr/bin' / binary)
        shutil.copy2(payload / 'COPYING', licensedir / 'COPYING')
        shutil.copy2(payload / 'NOTES.md', docdir / 'README')
        shutil.copy2(payload / 'manifest.json', docdir / 'manifest.json')
        source_payload = top / 'SOURCES/lotusd-payload.tar.gz'
        with source_payload.open('wb') as output_stream:
            with gzip.GzipFile(fileobj=output_stream, mode='wb', mtime=int(epoch), filename='') as compressed:
                with tarfile.open(fileobj=compressed, mode='w') as bundle:
                    for path in sorted(rpmpayload.rglob('*')):
                        if path.is_file():
                            info = bundle.gettarinfo(str(path), arcname=str(path.relative_to(rpmpayload)))
                            info.uid = info.gid = 0
                            info.uname = info.gname = ''
                            info.mtime = int(epoch)
                            with path.open('rb') as source_stream:
                                bundle.addfile(info, source_stream)
        files = '\n'.join(f'/usr/bin/{binary}' for binary in manifest['binaries'])
        spec = top / 'SPECS' / 'lotusd.spec'
        spec.write_text(
            f'Name: lotusd\nVersion: {version}\nRelease: 1%{{?dist}}\n'
            'Summary: Lotus daemon and command-line client\nLicense: MIT\n'
            'Source0: lotusd-payload.tar.gz\n'
            'BuildArch: x86_64\nRequires: glibc >= 2.31\n'
            '%description\nLotus daemon and CLI with in-process Chronik indexer.\n'
            '%prep\n%setup -q -c -T\ntar -xzf %{SOURCE0} -C .\n'
            '%build\n%install\nmkdir -p %{buildroot}\ncp -a usr %{buildroot}/\n'
            '%files\n%license /usr/share/licenses/lotusd/COPYING\n'
            '%doc /usr/share/doc/lotusd/*\n' + files + '\n')
        run(['rpmbuild', '--define', f'_topdir {top}', '--define', '_buildhost lotus-release',
             '--define', f'_source_date_epoch {epoch}', '-bb', spec], env)
        rpm = top / 'RPMS/x86_64' / f'lotusd-{version}-1.x86_64.rpm'
        if not rpm.is_file():
            found = list((top / 'RPMS').rglob('*.rpm'))
            if len(found) != 1:
                raise ValueError('rpmbuild did not produce exactly one Lotus RPM')
            rpm = found[0]
        shutil.copyfile(rpm, output / rpm.name)

    packages = sorted(output.glob('lotusd_*_amd64.deb')) + sorted(output.glob('lotusd-*.rpm'))
    for path in packages:
        path.with_name(path.name + '.sha256').write_text(
            f'{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n')
    build_info_path = Path(build_info_path)
    build_info = json.loads(build_info_path.read_text())
    build_info['system_packages'] = [
        {'file': path.name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
        for path in packages]
    build_info['system_package_reproducibility'] = (
        'packages are generated from the verified Guix archive; package metadata '
        'and container install tests are not part of the independent Guix rebuild comparison')
    build_info_path.write_text(json.dumps(build_info, indent=2) + '\n')
    build_info_path.with_name(build_info_path.name + '.sha256').write_text(
        f'{hashlib.sha256(build_info_path.read_bytes()).hexdigest()}  {build_info_path.name}\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', required=True, type=Path)
    parser.add_argument('--manifest', required=True, type=Path)
    parser.add_argument('--notes', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--build-info', required=True, type=Path)
    args = parser.parse_args()
    package(args.archive.resolve(), args.manifest.resolve(), args.notes.resolve(),
            args.output.resolve(), args.build_info.resolve())


if __name__ == '__main__':
    main()
