#!/usr/bin/env python3
"""Prepare, verify, build and publish explicitly named daemon components."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


legacy = module('lotus_release', Path(__file__).with_name('prepare-release.py'))
planner = module('feature_plan', Path(__file__).with_name('feature-plan.py'))
run = legacy.run


def registry(root):
    return json.loads((root / 'daemon/components.json').read_text())['components']


def identity(component, version, revision):
    if component not in registry(ROOT):
        raise ValueError('Unknown daemon component')
    if not legacy.VERSION.fullmatch(version) or not re.fullmatch(r'[1-9][0-9]*', str(revision)):
        raise ValueError('Distributor version must be numeric x.y.z and patch revision a positive integer')
    return f'{component}-v{version}'


def entries(root, series):
    directory = root / 'daemon/patches' / series
    return [directory / name for name in (directory / 'series').read_text().splitlines()
            if name and not name.startswith('#')]


def native_version(text):
    match = re.search(r'(?m)^\s*VERSION (\d+\.\d+\.\d+)\s*$', text)
    if match:
        return match[1]
    values = [re.search(rf'set\(CLIENT_VERSION_{part} (\d+)\)', text) for part in ('MAJOR', 'MINOR', 'BUILD')]
    if all(values):
        return '.'.join(value[1] for value in values)
    raise ValueError('Cannot determine native version from pinned source CMakeLists.txt')


def scoped_describe(replay, native, component, version):
    """Never derive native versions from other monorepo components' tags."""
    pattern = f'{component}-v{version}*' if component == 'lotusd' else f'v{native}*'
    paths = replay.git('ls-files', '-z').decode().split('\0')
    changes = {}
    # These executable consumers include inherited Guix helpers; Electrum remains
    # separately scoped to its own native v tags rather than the daemon namespace.
    for path in paths:
        if not path.endswith(('.sh', '.bash', '.cmake')):
            continue
        old = replay.read(path)
        if not re.search(r'(?:git|GIT_EXECUTABLE).*\bdescribe\b', old):
            continue
        selected = pattern
        if path.startswith('electrum/'):
            # Electrum has its own native version and cannot consume node tags.
            electrum = next((name for name in paths if name.endswith('/version.py') and name.startswith('electrum/electrumabc/')), None)
            value = re.search(r'VERSION_TUPLE = \((\d+), (\d+), (\d+)\)', replay.read(electrum)) if electrum else None
            selected = 'v'+'.'.join(value.groups())+'*' if value else 'electrum-v[0-9]*'
        new = re.sub(r'\bdescribe\s+(?=--(?:abbrev|exact-match|tags))',
                     f'describe --match "{selected}" ', old)
        if new != old:
            changes[path] = new
    return changes


def path_for(root, component):
    return root / 'daemon/releases' / component


def prepare(root, upstream, component, version, revision, profile=None, features=(), experimental=False,
            check=False, archive=None, network=None, allow_network_rpc=False):
    config = registry(root)[component]
    tag = identity(component, version, revision)
    profile = profile or config['default_profile']
    if profile not in ('stock', 'maintained', 'custom'):
        raise ValueError('Profile must be stock, maintained or custom')
    if component == 'lotusd' and profile != 'maintained':
        raise ValueError('Lotus requires its complete maintained consensus series')
    if features and profile != 'custom' and component != 'lotusd':
        raise ValueError('Feature selections require an explicit custom profile')
    if profile == 'stock' and component == 'doged':
        raise ValueError('Doged native tests need maintained compatibility patches; select maintained or custom')
    base = (root / 'daemon' / config['pin_file']).read_text().splitlines()[0]
    if not re.fullmatch(r'[0-9a-f]{40}', base):
        raise ValueError('Upstream must be pinned to a full immutable commit')
    unknown = set(features) - set(planner.FEATURES)
    if unknown:
        raise ValueError('Unknown features: '+', '.join(sorted(unknown)))
    plan = planner.resolve(config['series'], list(features), experimental)
    if component == 'lotusd':
        # Delegate complete Arch/Docker/version/network preparation to the same
        # implementation used by the historical CLI. No second packaging engine.
        legacy.prepare(root, upstream, version, write=not check, check=check,
                       network=network, allow_network_rpc=allow_network_rpc, namespace='lotusd')
    elif network is not None or allow_network_rpc:
        raise ValueError('Verified network-input preparation currently supports Lotus only')
    selected = entries(root, config['series']) if profile != 'stock' else []
    selected += [root / 'daemon' / Path(path).relative_to(planner.DAEMON) for path in plan['patches']]
    selected = list(dict.fromkeys(selected))
    flags = config['cmake_args'] + plan['cmake_args']
    # Preserve native upstream versions, even for patched distribution builds.
    # Lotus is itself maintained here and its numeric version is prepared above.
    target = path_for(root, component)
    with tempfile.TemporaryDirectory(prefix='lotus-component-') as temporary:
        replay = legacy.Replay(upstream, temporary)
        replay.git('read-tree', base)
        upstream_version = native_version(replay.read('CMakeLists.txt'))
        patch_rows = []
        for path in selected:
            payload = path.read_bytes()
            replay.apply(payload)
            patch_rows.append({'path': str(path.relative_to(root)), 'sha256': hashlib.sha256(payload).hexdigest()})
        native = native_version(replay.read('CMakeLists.txt'))
        before = replay.git('write-tree').decode().strip()
        parent = replay.git('commit-tree', before, '-p', base, input=b'Component maintained and selected patches\n').decode().strip()
        changes = scoped_describe(replay, native, component, version)
        if changes:
            replay.apply(legacy.diff(replay, changes))
        tree = replay.git('write-tree').decode().strip()
        commit = replay.git('commit-tree', tree, '-p', parent,
                            input=f'Scope {component} source build labels to native version tags\n\nKeep distributor release identity in the component manifest.\nUnrelated monorepo component tags must not override native build labels.\n'.encode()).decode().strip()
        patch = replay.git('format-patch', '-1', '--stdout', '--no-signature', '--full-index', '--no-stat', commit)
        source_archive = Path(temporary) / 'source.tar.gz'
        replay.git('archive', '--format=tar.gz', f'--prefix={tag}/', '--output='+str(source_archive), commit)
        with source_archive.open('rb') as stream:
            source_sha256 = hashlib.file_digest(stream, 'sha256').hexdigest()
        manifest = {'schema': 1, 'component': component, 'tag': tag, 'distributor_version': version,
                    'patch_revision': int(revision), 'profile': profile, 'channel': config['channel'],
                    'upstream_remote': config['remote'], 'upstream_commit': base, 'upstream_version': upstream_version,
                    'native_version': native, 'source_tree': tree, 'source_commit': commit,
                    'patches': patch_rows, 'generated_patch_sha256': hashlib.sha256(patch).hexdigest(),
                    'features': list(features), 'experimental_opt_in': experimental, 'feature_evidence': plan['features'],
                    'cmake_args': flags, 'binaries': config['binaries'], 'test_target': config['test_target'],
                    'toolchains': {'rust': config['rust'], 'python': config['python'],
                                   'nng_source': {'linux':{'version':'1.9.0','commit':'29aff2bacc9e2cfa6dcc52155d2816582617f918'},'macos':'Homebrew; actual package version recorded in build-info'} if component=='lotusd' and 'nng-off' not in features else None,
                                   'cmake': 'runner package; actual version recorded in artifact build-info',
                                   'compiler': 'runner package; actual version recorded in artifact build-info'},
                    'network_evidence': (json.loads((root/'daemon/release-network.json').read_text()) if component=='lotusd' and (root/'daemon/release-network.json').exists() else None),
                    'source_archive': f'{tag}-source.tar.gz', 'source_archive_sha256': source_sha256, 'source_date_epoch': 1000684800,
                    'publication_workflow': 'Daemon component artifacts and releases',
                    'validation_scope': 'prepared source identity only; CI/native and behavioral results are separate'}
        notes = (f'# {tag}\n\nDistributor build from {config["remote"]} commit `{base}`.\n'
                 f'Upstream native version: `{upstream_version}`; built native version: `{native}`.\n'
                 f'Distributor patch revision: `{revision}`; profile: `{profile}`; channel: `{config["channel"]}`.\n'
                 f'Explicit features: `{",".join(features) or "registry defaults"}`.\nSource tree: `{tree}`.\n\n'
                 'This is a givelotus distribution, not an official upstream release.\n'
                 'Build checks do not establish mainnet synchronization, consensus parity, or a Chronik host port.\n'
                 'No production deployment or container-registry push is performed.\n')
        docker = '''FROM ubuntu:24.04
ARG RELEASE_ARCHIVE
COPY ${RELEASE_ARCHIVE} /tmp/release.tar.gz
RUN apt-get update && apt-get install -y --no-install-recommends libevent-2.1-7t64 libevent-pthreads-2.1-7t64 libdb5.3++t64 libsqlite3-0 libstdc++6 libnng1 libboost-filesystem1.83.0 libboost-thread1.83.0 && rm -rf /var/lib/apt/lists/* && tar xzf /tmp/release.tar.gz -C /usr/local --strip-components=1 && rm /tmp/release.tar.gz
RUN useradd -rm node && mkdir /data && chown node:node /data
USER node
VOLUME /data
''' + f'ENTRYPOINT ["{config["binaries"][0]}", "-datadir=/data"]\n'
        if component == 'lotusd':
            docker = replay.read('contrib/docker/lotus/Dockerfile')
        outputs = {target / 'manifest.json': (json.dumps(manifest, indent=2, sort_keys=True)+'\n').encode(),
                   target / 'source-metadata.patch': patch, target / 'NOTES.md': notes.encode(),
                   target / 'Dockerfile': docker.encode()}
        changed = [str(path.relative_to(root)) for path, data in outputs.items() if not path.exists() or path.read_bytes()!=data]
        if check and changed:
            raise ValueError('Component metadata drift: '+', '.join(changed))
        if not check:
            target.mkdir(parents=True, exist_ok=True)
            legacy.atomic_write(outputs)
        if archive:
            shutil.copyfile(source_archive, Path(archive).resolve())
        return {'component': component, 'tag': tag, 'source_tree': tree, 'changed': changed}


def verify(root, upstream, component, archive=None):
    saved = json.loads((path_for(root, component) / 'manifest.json').read_text())
    return prepare(root, upstream, component, saved['distributor_version'], saved['patch_revision'],
                   saved['profile'], saved['features'], saved['experimental_opt_in'], check=True, archive=archive)


def materialize(root, upstream, component, destination):
    if destination.exists():
        raise ValueError('Source destination must be new; existing workspaces are preserved')
    verify(root, upstream, component)
    manifest = json.loads((path_for(root, component) / 'manifest.json').read_text())
    with tempfile.TemporaryDirectory(prefix='component-materialize-', dir=destination.parent) as temp:
        temporary = Path(temp)
        # A private git repository, not a subdirectory that accidentally discovers
        # monorepo .git. Never fetch component or upstream tags into build sources.
        source = temporary / 'source'
        run(['git', 'clone', '--quiet', '--shared', '--no-tags', '--no-checkout', str(upstream), str(source)])
        run(['git', '-C', str(source), 'checkout', '--quiet', '--detach', manifest['upstream_commit']])
        config = ['-c','user.name=Lotus Builder','-c','user.email=build@givelotus.org','-c','commit.gpgsign=false','-c','core.hooksPath=/dev/null']
        for row in manifest['patches']:
            run(['git','-C',str(source),*config,'am','--keep-non-patch','--keep-cr','--whitespace=nowarn','--committer-date-is-author-date',str(root/row['path'])])
        run(['git','-C',str(source),*config,'am','--keep-non-patch','--whitespace=nowarn','--committer-date-is-author-date',str(path_for(root,component)/'source-metadata.patch')])
        tree = run(['git','-C',str(source),'rev-parse','HEAD^{tree}']).decode().strip()
        if tree != manifest['source_tree']:
            raise ValueError('Mailbox replay source tree differs from manifest')
        run(['git','-C',str(source),'update-ref','refs/heads/replayed-patches','HEAD'])
        # Reconstruct the same fixed-epoch archive commits after proving native
        # git-am replay. Build labels and export-subst now share one source ID.
        env = {**os.environ, 'GIT_AUTHOR_NAME':'Lotus Release Tool', 'GIT_AUTHOR_EMAIL':'build@givelotus.org',
               'GIT_COMMITTER_NAME':'Lotus Release Tool', 'GIT_COMMITTER_EMAIL':'build@givelotus.org',
               'GIT_AUTHOR_DATE':'2001-09-17T00:00:00Z', 'GIT_COMMITTER_DATE':'2001-09-17T00:00:00Z'}
        before = run(['git','-C',str(source),'rev-parse','HEAD~1^{tree}']).decode().strip()
        parent = run(['git','-C',str(source),'commit-tree',before,'-p',manifest['upstream_commit']],
                     env=env,input=b'Component maintained and selected patches\n').decode().strip()
        message = run(['git','-C',str(source),'show','-s','--format=%B','HEAD']).rstrip()+b'\n'
        commit = run(['git','-C',str(source),'commit-tree',tree,'-p',parent],env=env,input=message).decode().strip()
        if commit != manifest['source_commit']:
            raise ValueError('Reconstructed archive/build commit differs from manifest')
        run(['git','-C',str(source),'checkout','--quiet','--detach',commit])
        if run(['git','-C',str(source),'tag','--list']).strip():
            raise ValueError('Build source unexpectedly inherited tags')
        os.rename(source, destination)
    return {'source_tree': tree, 'workspace':str(destination)}


def publish(root, component, upstream, reviewed_commit, validation_run):
    """Publish only the component and bytes validated on the exact main commit."""
    verify(root, upstream, component)
    manifest_path = path_for(root, component) / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())

    def git(*args):
        return run(['git', '-C', str(root), *args]).decode().strip()

    if (not re.fullmatch('[0-9a-f]{40}', reviewed_commit)
            or git('rev-parse', 'HEAD') != reviewed_commit
            or git('status', '--porcelain')):
        raise ValueError('Publication requires the exact clean reviewed checkout')

    canonical = re.compile(
        r'(?:https://github\.com/givelotus/lotus(?:\.git)?'
        r'|git@github\.com:givelotus/lotus(?:\.git)?'
        r'|ssh://git@github\.com/givelotus/lotus(?:\.git)?)\Z'
    )
    for option in ((), ('--push',)):
        urls = git('remote', 'get-url', *option, '--all', 'origin').splitlines()
        if len(urls) != 1 or not canonical.fullmatch(urls[0]):
            raise ValueError('Publication requires canonical single origin fetch/push URLs')
    remote_main = git('ls-remote', 'origin', 'refs/heads/main').split()
    if not remote_main or remote_main[0] != reviewed_commit:
        raise ValueError('Exact reviewed commit must be on origin/main')

    validation = json.loads(run([
        'gh', 'run', 'view', str(validation_run), '--repo', 'givelotus/lotus',
        '--json', 'headSha,conclusion,event,workflowName',
    ]))
    if (validation.get('headSha') != reviewed_commit
            or validation.get('conclusion') != 'success'
            or validation.get('event') != 'workflow_dispatch'
            or validation.get('workflowName') != manifest['publication_workflow']):
        raise ValueError('Require successful component artifact CI for exact commit')

    # Another component's successful run at the same commit is insufficient.
    # Compare the exact bytes, matching the independent tag-workflow guard.
    with tempfile.TemporaryDirectory(prefix='component-validation-') as temporary:
        run([
            'gh', 'run', 'download', str(validation_run), '--repo', 'givelotus/lotus',
            '--name', component + '-x86_64-linux-gnu', '--dir', temporary,
        ])
        if (Path(temporary) / 'manifest.json').read_bytes() != manifest_path.read_bytes():
            raise ValueError('Validation artifacts do not match this exact component manifest')

    tag = manifest['tag']
    if git('tag', '--list', tag) or git('ls-remote', 'origin', 'refs/tags/' + tag):
        raise ValueError('Existing tags/releases are immutable')
    message = (f'{tag}\nSource tree: {manifest["source_tree"]}'
               f'\nDistributor patch revision: {manifest["patch_revision"]}'
               f'\nValidation run: {validation_run}')
    git('tag', '-a', tag, reviewed_commit, '-m', message)
    git('push', '--atomic', 'origin', 'refs/tags/' + tag)
    return {'tag': tag, 'published_trigger': True}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--component',required=True,choices=registry(ROOT))
    parser.add_argument('--upstream',required=True,type=Path)
    parser.add_argument('--version')
    parser.add_argument('--patch-revision',type=int,default=1)
    parser.add_argument('--profile',choices=('stock','maintained','custom'))
    parser.add_argument('--features',default='')
    parser.add_argument('--allow-experimental',action='store_true')
    parser.add_argument('--network-input',type=Path)
    parser.add_argument('--allow-network-rpc',action='store_true')
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--candidate',type=Path)
    mode.add_argument('--check',action='store_true')
    mode.add_argument('--materialize',type=Path)
    mode.add_argument('--publish',action='store_true')
    parser.add_argument('--archive',type=Path)
    parser.add_argument('--reviewed-commit')
    parser.add_argument('--validation-run',type=int)
    args=parser.parse_args()
    if args.archive and not args.check:
        parser.error('--archive requires --check')
    if not args.candidate and (args.version or args.profile or args.features or args.network_input or args.allow_network_rpc or args.allow_experimental):
        parser.error('Preparation inputs require --candidate; verification/build/publication read the reviewed manifest')
    if not args.publish and (args.reviewed_commit or args.validation_run):
        parser.error('Publication identity inputs require --publish')
    try:
        if args.candidate:
            if not args.version:
                raise ValueError('--candidate requires --version')
            network=json.loads(args.network_input.read_text()) if args.network_input else None
            def operation(checkout):
                result=prepare(checkout,args.upstream,args.component,args.version,args.patch_revision,args.profile,
                               list(filter(None,args.features.split(','))),args.allow_experimental,
                               network=network,allow_network_rpc=args.allow_network_rpc)
                verify(checkout,args.upstream,args.component)
                return result
            result=legacy.candidate(ROOT,args.upstream,args.version,args.candidate,prepare_operation=operation)
        elif args.materialize:
            result=materialize(ROOT,args.upstream,args.component,args.materialize.resolve())
        elif args.publish:
            if not args.reviewed_commit or not args.validation_run:
                raise ValueError('--publish requires --reviewed-commit and --validation-run')
            result=publish(ROOT,args.component,args.upstream,args.reviewed_commit,args.validation_run)
        else:
            result=verify(ROOT,args.upstream,args.component,args.archive)
        print(json.dumps(result,indent=2))
    except (ValueError,KeyError,subprocess.CalledProcessError,FileNotFoundError) as error:
        parser.exit(1,str(getattr(error,'stderr',None) or error)+'\n')


if __name__=='__main__':
    main()
