#!/usr/bin/env python3
"""Build/test/package one reviewed component manifest; never tag or publish."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tarfile

import importlib.util
spec=importlib.util.spec_from_file_location('component_release',Path(__file__).with_name('component-release.py'))
release=importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


def command(args, **kwargs):
    subprocess.run([str(value) for value in args],check=True,**kwargs)


def output(args):
    return subprocess.check_output(args,text=True).strip()


def build(root, component, source, dist, target, jobs):
    release.verify(root, source, component)
    manifest_path=release.path_for(root,component)/'manifest.json'
    manifest=json.loads(manifest_path.read_text())
    if output(['git','-C',str(source),'rev-parse','HEAD^{tree}'])!=manifest['source_tree']:
        raise ValueError('Build source tree differs from reviewed manifest')
    if output(['git','-C',str(source),'rev-parse','HEAD'])!=manifest['source_commit']:
        raise ValueError('Build source commit differs from reviewed manifest')
    if output(['git','-C',str(source),'status','--porcelain','--untracked-files=no']):
        raise ValueError('Build source has tracked changes')
    expected={'Linux':'x86_64-linux-gnu','Darwin':'arm64-apple-darwin'}
    if expected.get(platform.system())!=target or platform.machine() not in ('x86_64','arm64','aarch64'):
        raise ValueError('Only native macOS arm64 and Linux x86_64 release targets are defined')
    if (target.startswith('x86_64') and platform.machine()!='x86_64') or (target.startswith('arm64') and platform.machine() not in ('arm64','aarch64')):
        raise ValueError('Cross compilation is not configured by this workflow')
    dist.mkdir(parents=True,exist_ok=True)
    flags=manifest['cmake_args']
    build_dir=source/'build'
    cmake=['cmake','-S',source,'-B',build_dir,'-GNinja','-DCMAKE_BUILD_TYPE=Release',*flags]
    if component!='bitcoin-core':
        cmake += ['-DPython_EXECUTABLE='+shutil.which('python3')]
        if manifest['toolchains']['rust']:
            cmake += ['-DRust_TOOLCHAIN='+manifest['toolchains']['rust']]
    command(cmake)
    command(['cmake','--build',build_dir,'--parallel',jobs,'--target',*manifest['binaries'],manifest['test_target']])
    if component=='bitcoin-core':
        # CTest also includes bundled secp256k1/UniValue binaries, not only test_bitcoin.
        command(['cmake','--build',build_dir,'--parallel',jobs])
        command(['ctest','--test-dir',build_dir,'--output-on-failure','--parallel',jobs])
    else:
        command(['cmake','--build',build_dir,'--parallel',jobs,'--target','check-bitcoin'])
        chronik=[flag for flag in flags if flag.startswith('-DBUILD_CHRONIK=')]
        if chronik and chronik[-1].endswith('=ON'):
            command(['cmake','--build',build_dir,'--parallel',jobs,'--target','check-crates'])
    name=manifest['tag']+'-'+target
    package=dist/name
    if package.exists():
        raise ValueError('Package destination already exists')
    (package/'bin').mkdir(parents=True)
    binary_dir=build_dir/('bin' if component=='bitcoin-core' else 'src')
    for binary in manifest['binaries']:
        shutil.copy2(binary_dir/binary,package/'bin'/binary)
    shutil.copy2(source/'COPYING',package/'COPYING')
    shutil.copy2(manifest_path,package/'manifest.json')
    shutil.copy2(release.path_for(root,component)/'NOTES.md',package/'NOTES.md')
    shutil.copy2(release.path_for(root,component)/'Dockerfile',package/'Dockerfile')
    if platform.system()=='Darwin':
        (package/'lib').mkdir()
        command(['dylibbundler','-od','-b',*[argument for binary in manifest['binaries'] for argument in ('-x',package/'bin'/binary)],'-d',str(package/'lib')+'/','-p','@executable_path/../lib/'])
        for path in sorted((package/'lib').iterdir())+list((package/'bin').iterdir()):
            command(['codesign','--force','--sign','-',path])
            command(['codesign','--verify','--strict',path])
    else:
        command(['strip',*[package/'bin'/binary for binary in manifest['binaries']]])
    versions={binary:output([str(package/'bin'/binary),'--version']) for binary in manifest['binaries']}
    if any(manifest['native_version'] not in text for text in versions.values()):
        raise ValueError('Packaged binary version does not match native source version')
    cache=dict(line.split('=',1) for line in (build_dir/'CMakeCache.txt').read_text().splitlines() if '=' in line and not line.startswith(('#','//')))
    compiler=cache['CMAKE_CXX_COMPILER:FILEPATH']
    info={'target':target,'source_commit':manifest['source_commit'],'source_tree':manifest['source_tree'],
          'mailbox_replay_commit':output(['git','-C',str(source),'rev-parse','replayed-patches']),
          'cmake':output(['cmake','--version']),'compiler_path':compiler,'compiler':output([compiler,'--version']),
          'python':platform.python_version(),'versions':versions,'tests':'native C++ suites passed',
          'behavior':'mainnet sync and host-specific Chronik behavior not established by packaging'}
    if manifest['toolchains']['rust']:
        info['rust']=output(['rustc','+'+manifest['toolchains']['rust'],'--version'])
    dependency_command = (['brew','list','--versions'] if platform.system()=='Darwin' else ['dpkg-query','--show'])
    dependencies = subprocess.run(dependency_command,capture_output=True,text=True,check=False)
    info['dependency_versions'] = dependencies.stdout.strip()
    (package/'build-info.json').write_text(json.dumps(info,indent=2)+'\n')
    archive=dist/(name+'.tar.gz')
    with tarfile.open(archive,'w:gz') as tar:
        tar.add(package,arcname=name)
    release.verify(root,source,component,dist/manifest['source_archive'])
    shutil.copy2(manifest_path,dist/'manifest.json')
    shutil.copy2(package/'build-info.json',dist/('build-info-'+target+'.json'))
    shutil.copy2(package/'NOTES.md',dist/'NOTES.md')
    shutil.copy2(package/'Dockerfile',dist/'Dockerfile')
    for path in (archive,dist/manifest['source_archive'],dist/'manifest.json',dist/('build-info-'+target+'.json'),dist/'NOTES.md',dist/'Dockerfile'):
        with path.open('rb') as stream:
            digest=hashlib.file_digest(stream,'sha256').hexdigest()
        (dist/(path.name+'.sha256')).write_text(digest+'  '+path.name+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--component',required=True,choices=release.registry(release.ROOT))
    parser.add_argument('--source',required=True,type=Path)
    parser.add_argument('--dist',required=True,type=Path)
    parser.add_argument('--target',required=True)
    parser.add_argument('--jobs',type=int,default=2)
    args=parser.parse_args()
    if args.jobs<1:
        parser.error('--jobs must be positive')
    build(release.ROOT,args.component,args.source.resolve(),args.dist.resolve(),args.target,args.jobs)
