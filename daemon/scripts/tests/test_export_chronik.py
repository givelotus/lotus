"""Pinned extraction must preserve source and reject dependency/scope drift."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import shutil
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'export-chronik.py'
SPEC = importlib.util.spec_from_file_location('export_chronik', SCRIPT)
EXPORT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EXPORT)


class ChronikExport(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / 'repo'
        self.repo.mkdir()
        self.git('init', '-q')
        self.git('config', 'user.email', 'fixture@example.invalid')
        self.git('config', 'user.name', 'Fixture')
        files = {
            'Cargo.toml': '[workspace]\nmembers = [\n    "chronik/core",\n    "apps/unrelated",\n]\n[workspace.package]\nrust-version = "1.80.0"\n',
            'Cargo.lock': 'version = 4\n[[package]]\nname = "core"\nversion = "0.1.0"\n[[package]]\nname = "unrelated"\nversion = "0.1.0"\n',
            'COPYING': 'MIT fixture\n',
            'cmake/modules/RustHelper.cmake': '# fixture Rust helper\n',
            'chronik/core/Cargo.toml': '[package]\nname = "core"\nversion = "0.1.0"\nrust-version.workspace = true\n',
            'chronik/core/src/lib.rs': 'pub const VALUE: u64 = 42;\n',
            'chronik/CMakeLists.txt': '# Original CMake\n',
        }
        for name, text in files.items():
            target = self.repo / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text)
        self.git('add', '.')
        self.git('commit', '-qm', 'Fixture source')
        self.provider = self.root / 'provider'
        self.provider.mkdir()
        lock = b'version = 4\n[[package]]\nname = "core"\nversion = "0.1.0"\n'
        (self.provider / 'Cargo.lock').write_bytes(lock)
        self.pin = {
            'format': 1,
            'upstream_url': 'https://example.invalid/upstream.git',
            'upstream_commit': self.git('rev-parse', 'HEAD').decode().strip(),
            'chronik_tree': self.git('rev-parse', 'HEAD:chronik').decode().strip(),
            'rust_toolchain': '1.93.0',
            'upstream_files': {name: EXPORT.digest((self.repo / name).read_bytes()) for name in ['Cargo.toml', 'Cargo.lock', 'COPYING', 'cmake/modules/RustHelper.cmake']},
            'derived_lockfile': 'Cargo.lock',
            'derived_lockfile_sha256': EXPORT.digest(lock),
            'host_profiles': {'abc': {'status': 'fixture'}},
        }
        self.pin_path = self.provider / 'source.json'
        self.save_pin()

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.repo), *args], stderr=subprocess.PIPE)

    def save_pin(self):
        self.pin_path.write_text(json.dumps(self.pin))

    def test_deterministic_source_preserving_export_ignores_dirty_checkout(self):
        source = self.repo / 'chronik/core/src/lib.rs'
        source.write_text('uncommitted bytes must not leak\n')
        first = EXPORT.export(self.repo, self.root / 'first', self.pin_path)
        second = EXPORT.export(self.repo, self.root / 'second', self.pin_path)
        self.assertEqual(first, second)
        self.assertEqual((self.root / 'first/chronik/core/src/lib.rs').read_text(), 'pub const VALUE: u64 = 42;\n')
        self.assertEqual(source.read_text(), 'uncommitted bytes must not leak\n')
        workspace = (self.root / 'first/Cargo.toml').read_text()
        self.assertNotIn('apps/unrelated', workspace)
        self.assertIn('resolver = "1"', workspace)
        self.assertEqual(first['lockfile'], {'upstream_packages': 2, 'export_packages': 1})

    def test_embedded_python_support_tree_is_preserved(self):
        support = self.repo / 'test/functional/test_framework/script.py'
        support.parent.mkdir(parents=True)
        support.write_text('VALUE = 42\n')
        self.git('add', '.')
        self.git('commit', '-qm', 'Embedded Python module')
        self.pin['upstream_commit'] = self.git('rev-parse', 'HEAD').decode().strip()
        self.pin['support_trees'] = {'test/functional/test_framework': self.git('rev-parse', 'HEAD:test/functional/test_framework').decode().strip()}
        self.save_pin()
        result = EXPORT.export(self.repo, self.root / 'supported', self.pin_path)
        name = 'test/functional/test_framework/script.py'
        self.assertEqual((self.root / 'supported' / name).read_bytes(), support.read_bytes())
        self.assertEqual(result['source_files_sha256'][name], EXPORT.digest(support.read_bytes()))

    @unittest.skipUnless(shutil.which('cmake'), 'CMake not installed')
    def test_cmake_rejects_modified_export_before_building(self):
        out = self.root / 'export'
        EXPORT.export(self.repo, out, self.pin_path)
        module = SCRIPT.parents[1] / 'chronik/cmake/ChronikProvider.cmake'
        copied = self.provider / 'cmake/ChronikProvider.cmake'
        copied.parent.mkdir()
        shutil.copyfile(module, copied)
        self.pin['export_manifest_sha256'] = EXPORT.digest((out / 'chronik-source.json').read_bytes())
        self.save_pin()
        script = self.root / 'verify.cmake'
        script.write_text(f'include("{copied}")\nlotus_add_chronik_from_source(SOURCE_DIR "{out}" HOST_PROFILE abc)\n')
        for name, message in (
            ('chronik/core/src/lib.rs', 'Chronik source differs from export'),
            ('cmake/modules/RustHelper.cmake', 'Chronik upstream input differs from export'),
        ):
            with self.subTest(name=name):
                target = out / name
                original = target.read_bytes()
                target.write_text('tampered executable source')
                result = subprocess.run(['cmake', '-P', str(script)], text=True, capture_output=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(message, result.stderr)
                target.write_bytes(original)

    def test_existing_output_and_symlink_are_refused(self):
        out = self.root / 'existing'
        out.mkdir()
        (out / 'keep').write_text('kept')
        with self.assertRaisesRegex(ValueError, 'already exists'):
            EXPORT.export(self.repo, out, self.pin_path)
        link = self.root / 'link'
        link.symlink_to(out)
        with self.assertRaisesRegex(ValueError, 'already exists'):
            EXPORT.export(self.repo, link, self.pin_path)
        self.assertEqual((out / 'keep').read_text(), 'kept')

    def test_bad_source_pin_leaves_no_partial_export(self):
        self.pin['chronik_tree'] = '0' * 40
        self.save_pin()
        with self.assertRaisesRegex(ValueError, 'source tree'):
            EXPORT.export(self.repo, self.root / 'out', self.pin_path)
        self.assertFalse((self.root / 'out').exists())
        self.assertEqual(list(self.root.glob('.chronik-export-*')), [])

    def test_changed_lockfile_and_escaping_paths_are_refused(self):
        (self.provider / 'Cargo.lock').write_text('changed')
        with self.assertRaisesRegex(ValueError, 'checksum'):
            EXPORT.export(self.repo, self.root / 'out', self.pin_path)
        self.pin['derived_lockfile'] = '../outside'
        self.save_pin()
        with self.assertRaisesRegex(ValueError, 'escapes'):
            EXPORT.export(self.repo, self.root / 'out', self.pin_path)

    def test_pinned_manifest_hash_is_enforced(self):
        self.pin['export_manifest_sha256'] = '0' * 64
        self.save_pin()
        with self.assertRaisesRegex(ValueError, 'export manifest'):
            EXPORT.export(self.repo, self.root / 'out', self.pin_path)
        self.assertFalse((self.root / 'out').exists())
        self.assertEqual(list(self.root.glob('.chronik-export-*')), [])

    def test_dependency_identity_changes_are_refused(self):
        before = b'version=4\n[[package]]\nname="core"\nversion="0.1.0"\n'
        after = before.replace(b'0.1.0', b'0.2.0')
        with self.assertRaisesRegex(ValueError, 'dependency version'):
            EXPORT.verify_lock(before, after, {'core'})

    def test_lock_dependency_disambiguation_is_not_a_version_change(self):
        before = b'''version=4
[[package]]
name="core"
version="0.1.0"
dependencies=["lib 1.0.0"]
[[package]]
name="lib"
version="1.0.0"
source="registry+https://example.invalid"
checksum="aaa"
[[package]]
name="lib"
version="2.0.0"
source="registry+https://example.invalid"
checksum="bbb"
'''
        after = before[:before.rindex(b'[[package]]')].replace(b'lib 1.0.0', b'lib')
        self.assertEqual(EXPORT.verify_lock(before, after, {'core'})['export_packages'], 2)


if __name__ == '__main__':
    unittest.main()
