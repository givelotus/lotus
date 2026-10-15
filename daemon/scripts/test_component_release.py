"""Offline component identity, tag isolation and publication guard regressions."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('component_release',Path(__file__).with_name('component-release.py'))
release=importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)
build_spec=importlib.util.spec_from_file_location('component_build',Path(__file__).with_name('component-build.py'))
build=importlib.util.module_from_spec(build_spec)
build_spec.loader.exec_module(build)
fixture_spec=importlib.util.spec_from_file_location('legacy_fixtures',Path(__file__).with_name('test_prepare_release.py'))
fixtures=importlib.util.module_from_spec(fixture_spec)
fixture_spec.loader.exec_module(fixtures)


class ComponentTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory()
        self.root=Path(self.temporary.name)/'root'
        self.upstream=Path(self.temporary.name)/'upstream'
        (self.root/'daemon/patches/bitcoin').mkdir(parents=True)
        self.upstream.mkdir()
        subprocess.run(['git','init','-q',str(self.upstream)],check=True)
        (self.upstream/'CMakeLists.txt').write_text('set(CLIENT_VERSION_MAJOR 32)\nset(CLIENT_VERSION_MINOR 99)\nset(CLIENT_VERSION_BUILD 0)\n')
        (self.upstream/'share').mkdir()
        (self.upstream/'share/genbuild.sh').write_text('#!/bin/sh\ncd "$2" || exit 1\nDESC=$(git describe --abbrev=0 2>/dev/null)\nif [ -n "$DESC" ]; then echo "$DESC" > "$1"; else git rev-parse --short HEAD > "$1"; fi\n')
        self.git('add','.')
        self.git('-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-qm','Native development source')
        self.base=self.git('rev-parse','HEAD').strip().decode()
        shutil.copy2(release.ROOT/'daemon/components.json',self.root/'daemon/components.json')
        (self.root/'daemon/bitcoin-core-version').write_text(self.base+'\n')
        (self.root/'daemon/patches/bitcoin/series').write_text('# No feature patches\n')

    def tearDown(self):
        self.temporary.cleanup()

    def git(self,*args):
        return subprocess.check_output(['git','-C',str(self.upstream),*args])

    def prepare(self,**kwargs):
        return release.prepare(self.root,self.upstream,'bitcoin-core','1.0.0',1,**kwargs)

    def manifest(self):
        return json.loads((self.root/'daemon/releases/bitcoin-core/manifest.json').read_text())

    def test_native_and_distributor_versions_are_distinct_and_deterministic(self):
        self.prepare()
        data=self.manifest()
        self.assertEqual(data['tag'],'bitcoin-core-v1.0.0')
        self.assertEqual(data['upstream_version'],'32.99.0')
        self.assertEqual(data['native_version'],'32.99.0')
        self.assertEqual(data['channel'],'development-snapshot')
        archive=self.root/'source.tar.gz'
        self.prepare(check=True,archive=archive)
        before=hashlib.sha256(archive.read_bytes()).hexdigest()
        time.sleep(1.05)
        self.prepare(check=True,archive=archive)
        self.assertEqual(before,hashlib.sha256(archive.read_bytes()).hexdigest())
        self.assertEqual(self.git('status','--porcelain'),b'')

    def test_unsupported_features_and_bad_identity_fail_before_writes(self):
        for feature in ('nng','tx-chain-limit','unknown'):
            with self.assertRaises(ValueError):
                self.prepare(profile='custom',features=[feature],experimental=True)
        for version in ('v1.0.0','01.0.0','1.0','1.0.0;echo x'):
            with self.assertRaises(ValueError):
                release.identity('bitcoin-core',version,1)
        self.assertEqual(release.identity('lotusd','11.6.2',1), 'lotusd-v11.6.2')
        self.assertFalse((self.root/'daemon/releases').exists())

    def test_core_chronik_selects_the_reviewed_host_adapter(self):
        (self.root/'daemon/chronik/hosts/bitcoin-core/node').mkdir(parents=True)
        (self.root/'daemon/chronik/hosts/bitcoin-core').mkdir(exist_ok=True)
        (self.root/'daemon/chronik/hosts/bitcoin-core/profile.json').write_text('{"name":"fixture"}\n')
        (self.root/'daemon/chronik/hosts/bitcoin-core/node/0001-wire-chronik-lifecycle-and-native-storage.patch').write_text(
            'diff --git a/CMakeLists.txt b/CMakeLists.txt\n--- a/CMakeLists.txt\n+++ b/CMakeLists.txt\n@@ -1,3 +1,4 @@\n set(CLIENT_VERSION_MAJOR 32)\n+ # fixture adapter\n set(CLIENT_VERSION_MINOR 99)\n set(CLIENT_VERSION_BUILD 0)\n')
        (self.root/'daemon/chronik/source.json').write_text(json.dumps({
            'upstream_commit':'a'*40, 'export_manifest_sha256':'b'*64})+'\n')
        self.prepare(profile='custom',features=['chronik'])
        manifest=self.manifest()
        self.assertEqual(manifest['features'],['chronik'])
        self.assertEqual(manifest['chronik_host']['profile'],'bitcoin-core')
        self.assertEqual(manifest['patches'][0]['path'],
                         'daemon/chronik/hosts/bitcoin-core/node/0001-wire-chronik-lifecycle-and-native-storage.patch')

    def test_core_chronik_build_receives_required_rust_toolchain(self):
        manifest={'cmake_args':['-DBUILD_CHRONIK=ON'],
                  'toolchains':{'rust':'1.87.0'}}
        flags=build.cmake_flags(manifest,'bitcoin-core','/usr/bin/python3')
        self.assertIn('-DRust_TOOLCHAIN=1.87.0',flags)
        self.assertNotIn('-DPython_EXECUTABLE=/usr/bin/python3',flags)

    def test_drift_rejected_and_stock_cannot_silently_enable_candidates(self):
        self.prepare()
        with self.assertRaises(ValueError):
            self.prepare(features=['zeromq-on'])
        path=self.root/'daemon/releases/bitcoin-core/manifest.json'
        path.write_text('{}\n')
        with self.assertRaisesRegex(ValueError,'drift'):
            self.prepare(check=True)

    def test_source_clone_excludes_tags_and_foreign_tag_does_not_override_native_version(self):
        self.git('-c','user.name=Fixture','-c','user.email=fixture@example.invalid','tag','-a','v999.0.0','-m','Foreign old tag')
        self.prepare()
        destination=self.root/'source'
        release.materialize(self.root,self.upstream,'bitcoin-core',destination)
        manifest=self.manifest()
        self.assertEqual(subprocess.check_output(['git','-C',str(destination),'tag','--list']),b'')
        self.assertEqual(subprocess.check_output(['git','-C',str(destination),'rev-parse','HEAD']).decode().strip(),manifest['source_commit'])
        subprocess.run(['git','-C',str(destination),'-c','user.name=Fixture','-c','user.email=fixture@example.invalid','tag','-a','vase-v99.0.0','-m','Unrelated component'],check=True)
        header=self.root/'header'
        subprocess.run(['sh',str(destination/'share/genbuild.sh'),str(header),str(destination)],check=True)
        self.assertNotIn('vase',header.read_text())
        with self.assertRaisesRegex(ValueError,'must be new'):
            release.materialize(self.root,self.upstream,'bitcoin-core',destination)

    def test_lotus_reuses_full_packaging_and_network_engine_with_namespace(self):
        fixture=fixtures.ReleaseTests()
        fixture.setUp()
        try:
            with tempfile.TemporaryDirectory() as directory:
                replay=release.legacy.Replay(fixture.upstream,directory)
                replay.git('read-tree',fixture.git('rev-parse','HEAD').decode().strip())
                changes=release.legacy.metadata(replay,'12.0.0',namespace='lotusd')
            for name in ('lotus','lotus-qt'):
                text=changes[f'contrib/aur/{name}/PKGBUILD']
                self.assertIn('/download/lotusd-v$pkgver/lotusd-v$pkgver-source.tar.gz',text)
                self.assertIn('lotusd-v${pkgver',text)
            self.assertIn('lotusd-v12.0.0-x86_64-linux-gnu',changes['contrib/docker/lotus/README.md'])
        finally:
            fixture.tearDown()

    def test_publish_rejects_wrong_exact_commit_before_network_tag_mutation(self):
        self.prepare()
        def fake_run(args,**kwargs):
            if args[-2:]==['rev-parse','HEAD']:
                return b'b'*40
            raise AssertionError('Unexpected network/mutation: '+str(args))
        with patch.object(release,'verify'),patch.object(release,'run',side_effect=fake_run):
            with self.assertRaisesRegex(ValueError,'exact clean'):
                release.publish(self.root,'bitcoin-core',self.upstream,'a'*40,1)

    def test_publication_requires_same_component_artifact_and_refuses_existing_tags(self):
        self.prepare()
        manifest=self.manifest()
        for scenario in ('wrong-component','existing-tag','multiple-origins','valid'):
            mutations=[]
            def fake_run(args,**kwargs):
                if args[0]=='git':
                    operation=args[3:]
                    if operation==['rev-parse','HEAD']: return b'a'*40+b'\n'
                    if operation==['status','--porcelain']: return b''
                    if operation[:2]==['remote','get-url']:
                        return b'git@github.com:givelotus/lotus.git\n'+(b'https://example.invalid/other.git\n' if scenario=='multiple-origins' else b'')
                    if operation[:2]==['ls-remote','origin']:
                        if operation[-1]=='refs/heads/main': return b'a'*40+b'\trefs/heads/main\n'
                        return b''
                    if operation[:2]==['tag','--list']:
                        return b'bitcoin-core-v1.0.0\n' if scenario=='existing-tag' else b''
                    if operation[:2] in (['tag','-a'],['push','--atomic']):
                        mutations.append(operation)
                        return b''
                if args[:3]==['gh','run','view']:
                    return json.dumps({'headSha':'a'*40,'conclusion':'success','event':'workflow_dispatch','workflowName':'Daemon component artifacts and releases'}).encode()
                if args[:3]==['gh','run','download']:
                    artifact=dict(manifest)
                    if scenario=='wrong-component': artifact['component']='bchn'
                    (Path(args[-1])/'manifest.json').write_bytes((self.root/'daemon/releases/bitcoin-core/manifest.json').read_bytes() if artifact==manifest else json.dumps(artifact).encode())
                    return b''
                raise AssertionError(str(args))
            with self.subTest(scenario=scenario),patch.object(release,'verify'),patch.object(release,'run',side_effect=fake_run):
                if scenario=='valid':
                    release.publish(self.root,'bitcoin-core',self.upstream,'a'*40,123)
                    self.assertEqual(len(mutations),2)
                    self.assertIn('Validation run: 123',mutations[0][-1])
                else:
                    with self.assertRaises(ValueError):
                        release.publish(self.root,'bitcoin-core',self.upstream,'a'*40,123)
                    self.assertEqual(mutations,[])

    def test_custom_candidate_reads_its_snapshot_patch_not_live_checkout(self):
        relative=Path('patches/ecash/01-nlogn-block-construction.patch')
        snapshot_patch=self.root/'daemon'/relative
        snapshot_patch.parent.mkdir(parents=True)
        snapshot_patch.write_text('diff --git a/CMakeLists.txt b/CMakeLists.txt\n--- a/CMakeLists.txt\n+++ b/CMakeLists.txt\n@@ -1,3 +1,4 @@\n+# snapshot-only fixture\n set(CLIENT_VERSION_MAJOR 32)\n set(CLIENT_VERSION_MINOR 99)\n set(CLIENT_VERSION_BUILD 0)\n')
        plan={'cmake_args':['-DWITH_ZMQ=ON'],'patches':[str(release.planner.DAEMON/relative)],'features':[]}
        with patch.object(release.planner,'resolve',return_value=plan):
            self.prepare(profile='custom',features=['zeromq-on'])
        row=self.manifest()['patches'][0]
        self.assertEqual(row['path'],'daemon/'+str(relative))
        self.assertEqual(row['sha256'],hashlib.sha256(snapshot_patch.read_bytes()).hexdigest())

    def test_cli_does_not_silently_ignore_inputs_for_other_modes(self):
        script=Path(release.__file__)
        for options in (['--candidate',str(self.root/'candidate'),'--archive',str(self.root/'archive')],
                        ['--check','--features','chronik'],['--check','--validation-run','123']):
            command=['python3',str(script),'--component','bitcoin-core','--upstream',str(self.upstream),*options]
            result=subprocess.run(command,capture_output=True,text=True)
            self.assertEqual(result.returncode,2,result.stderr)
        self.assertFalse((self.root/'candidate').exists())
        self.assertFalse((self.root/'archive').exists())
