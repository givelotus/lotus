#!/usr/bin/env python3
"""Replay canonical mailboxes, then gate and measure every individual boundary.

The supervising agent repairs the committed candidate and invokes -N again. This
process never applies unrecorded repair recipes and never continues after failure.
"""
import argparse
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import signal
import statistics
import subprocess
import sys
import time

VERSION = 2
FLAGS = ['-DCMAKE_BUILD_TYPE=Release', '-DBUILD_WALLET=OFF', '-DBUILD_QT=OFF',
         '-DBUILD_ZMQ=OFF', '-DBUILD_CLI=ON', '-DBUILD_TX=OFF',
         '-DBUILD_CHRONIK=OFF', '-DBUILD_SEEDER=OFF', '-DENABLE_UPNP=OFF',
         '-DENABLE_NATPMP=OFF']


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def digest(value):
    return hashlib.sha256(value).hexdigest()


def atomic(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    with temporary.open('w') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def git(source, *args):
    return subprocess.check_output(['git', '-C', str(source), *args], text=True).strip()


class GateFailure(RuntimeError):
    pass


def validation_requirements(contract):
    # Editorial/source-provenance changes do not alter runtime evidence. Actual
    # gate additions change this patch's prefix and every dependent boundary.
    return {key: contract.get(key, {} if key == 'required_native_suites' else [])
            for key in ('required_native_suites', 'required_python_unittests', 'required_functional_tests')}


def manifest(candidate):
    historical = candidate / 'daemon/patch-audit/split-manifest.json'
    canonical = candidate / 'daemon/patch-audit/progression/canonical-manifest.json'
    original = json.loads((canonical if canonical.exists() else historical).read_text())
    if canonical.exists() and original['split_manifest_sha256'] != digest(historical.read_bytes()):
        raise GateFailure('Immutable split-stage mapping changed underneath the canonical order')
    contract_path = candidate / 'daemon/patch-audit/progression/contracts.json'
    contracts = json.loads(contract_path.read_text())['patches']
    patches = []
    for entry in original['patches']:
        entry = dict(entry)
        path = candidate / 'daemon/patches' / entry['series'] / entry['file']
        entry['path'] = str(path)
        entry['sha256'] = digest(path.read_bytes())
        entry['files'] = sorted(set(entry['files']) | set(re.findall(r'^\+\+\+ b/(.+)$', path.read_text(), re.M)))
        historical_number = re.fullmatch(r'(ecash|v2)/(\d+)', entry['original_patch'])
        entry['original_step'] = (
            int(historical_number.group(2)) + (52 if historical_number.group(1) == 'v2' else 0)
            if historical_number else None
        )
        patches.append(entry)
    for series in ('ecash', 'v2'):
        actual = [line.strip() for line in (candidate / 'daemon/patches' / series / 'series').read_text().splitlines()
                  if line.strip() and not line.startswith(('#', '@'))]
        expected = [p['file'] for p in patches if p['series'] == series]
        if actual != expected:
            raise GateFailure('Canonical series differs from original-to-split mapping')
    prefix = digest(original['base'].encode())
    entries = [{'index': 0, 'label': 'ABC baseline', 'original_step': 0, 'files': [],
                'prefix_sha256': prefix, 'split_tree': original['base']}]
    for index, entry in enumerate(patches, 1):
        contract = contracts[str(entry.get('contract_id', entry.get('split_index', index)))]
        gate_digest = digest(json.dumps(validation_requirements(contract), sort_keys=True).encode())
        prefix = digest((prefix + '\0' + entry['series'] + '/' + entry['file'] + '\0' + entry['sha256'] + '\0' + gate_digest).encode())
        entries.append({**entry, 'index': index, 'label': f"{entry['series']}/{entry['number']:03}",
                        'prefix_sha256': prefix, 'split_tree': entry['tree'], 'contract': contract,
                        'contract_sha256': digest(json.dumps(contract, sort_keys=True).encode())})
    return original['base'], entries


def fingerprint(candidate, repetitions):
    files = [Path(__file__)] + sorted((candidate / 'daemon/patch-audit/progression').rglob('*.py'))
    hashes = {str(p.relative_to(candidate)): digest(p.read_bytes()) for p in files}
    compilers = {}
    for tool in ('cc', 'c++', 'cmake', 'ninja', 'python3', 'rustc', 'cargo'):
        executable = Path(shutil.which(tool)).resolve()
        compilers[tool] = {'path': str(executable), 'sha256': digest(executable.read_bytes()),
                           'version': subprocess.check_output([tool, '--version'], text=True, stderr=subprocess.STDOUT).strip()}
    chronik_python = shutil.which('python3.13') or sys.executable
    compilers['chronik_python'] = {'path': str(Path(chronik_python).resolve()),
        'sha256': digest(Path(chronik_python).resolve().read_bytes()),
        'version': subprocess.check_output([chronik_python, '--version'], text=True).strip()}
    value = {'version': VERSION, 'files': hashes, 'flags': FLAGS, 'repetitions': repetitions,
             'compilers': compilers, 'platform': platform.platform(), 'machine': platform.machine()}
    return digest(json.dumps(value, sort_keys=True).encode()), value


def matching_harness(record, current, data):
    if record.get('harness_sha256') == current:
        return True
    # Explicit user-authorized 3 -> 1 timing-only transition after patch 26.
    # Earlier records stay immutable and must match their complete pinned data.
    policy_path = data / 'one-repetition-transition.json'
    if not policy_path.exists():
        return False
    policy = json.loads(policy_path.read_text())
    evidence = policy['evidence']
    if digest(json.dumps(evidence, sort_keys=True).encode()) != policy['sha256']:
        raise GateFailure('Timing transition record integrity mismatch')
    pinned = evidence['prior_records'].get(str(record.get('index')))
    return bool(evidence['through_index'] == 26 and pinned and
                evidence['new_harness_sha256'] == current and
                evidence['old_harness_sha256'] == record.get('harness_sha256') and
                record.get('status') == 'ok' and
                pinned['record_sha256'] == digest(json.dumps(record, sort_keys=True).encode()) and
                all(record.get(key) == pinned[key] for key in
                    ('source_sha', 'source_tree', 'prefix_sha256', 'harness_sha256')))


def save_mtimes(source):
    saved = {}
    for path in source.rglob('*'):
        if '.git' in path.relative_to(source).parts or not path.is_file() or path.is_symlink():
            continue
        stat = path.stat()
        saved[str(path.relative_to(source))] = (digest(path.read_bytes()), stat.st_atime_ns, stat.st_mtime_ns)
    return saved


def restore_mtimes(source, saved):
    for name, (sha, atime, mtime) in saved.items():
        path = source / name
        if path.is_file() and not path.is_symlink() and digest(path.read_bytes()) == sha:
            os.utime(path, ns=(atime, mtime))


def patch_apply_command(source, mailbox):
    # Qt removal includes upstream files whose actual contents use CRLF.
    return ['git', '-C', str(source), '-c', 'commit.gpgsign=false', 'am',
            '--keep-non-patch', '--keep-cr', '--committer-date-is-author-date', str(mailbox)]


def parse_kernel_output(content):
    workloads = set(re.findall(r'^LOTUS_V2_WORKLOAD=([A-Za-z0-9_.-]+)\s*$', content, re.MULTILINE))
    if len(workloads) > 1:
        raise GateFailure('Kernel output contains conflicting workload identities')
    values = {key: float(value) for key, value in re.findall(
        r'\b([A-Z][A-Z0-9_]+)\s*=\s*([0-9.]+(?:e[+-]?\d+)?)', content)
        if key.endswith(('_TPS', '_MBPS', '_HPS', '_US', '_MS', '_PS'))}
    return values, next(iter(workloads), None)


def runtime_workloads(entry, source, available_tests):
    layer1 = entry.get('series', 'base') != 'v2'
    workloads = [('legacy', 'legacy_loopback.py', ['--source', source])] if layer1 else []
    rpc = source / 'src/rpc/mempool.cpp'
    batch_registered = rpc.exists() and bool(re.search(r'\{\s*"rawtransactions",\s*submitrawtxbatch\s*\}', rpc.read_text()))
    # Original ordinals cease to describe capabilities after prerequisite
    # reordering: moved hash primitives from original /020 do not add batch RPC.
    if batch_registered and (layer1 or 'v2_kernel_throughput_benchmark' in available_tests):
        workloads.append(('batch', 'historical_loopback.py', ['--series', 'l1' if layer1 else 'v2', '--source', source]))
    return workloads


def native_suite_selection(source, entries, available, av_available):
    suites = {'bitcoin': ['mempool_tests', 'rpc_tests', 'miner_tests'],
              'avalanche': ['proof_tests', 'delegation_tests']}
    origins = {}
    for entry in entries:
        for kind, names in entry.get('contract', {}).get('required_native_suites', {}).items():
            for name in names:
                if name not in suites[kind]:
                    suites[kind].append(name)
                origins[(kind, name)] = 'contract: ' + entry.get('canonical_id', entry.get('label', 'unknown'))
        for name in entry['files']:
            file = source / name
            if not file.is_file() or file.suffix != '.cpp':
                continue
            kind = ('bitcoin' if name.startswith('src/test/') else
                    'avalanche' if name.startswith('src/avalanche/test/') else None)
            if kind:
                for suite in re.findall(r'BOOST_(?:FIXTURE|AUTO)_TEST_SUITE\(\s*(\w+)', file.read_text()):
                    if suite not in suites[kind]:
                        suites[kind].append(suite)
                    origins[(kind, suite)] = name
    missing = [{'binary': kind, 'suite': name, 'origin': origins.get((kind, name), 'baseline gate')}
               for kind, listing in [('bitcoin', available), ('avalanche', av_available)]
               for name in suites[kind] if name + '*' not in listing]
    return suites['bitcoin'], suites['avalanche'], missing


def run_command(argv, log, timeout=7200, env=None):
    start = time.monotonic()
    with log.open('w') as stream:
        stream.write(json.dumps({'argv': list(map(str, argv)), 'started': now()}) + '\n')
        stream.flush()
        process = subprocess.Popen(list(map(str, argv)), stdout=stream, stderr=subprocess.STDOUT,
                                   start_new_session=True, env=env)
        try:
            code = process.wait(timeout=timeout)
        except (subprocess.TimeoutExpired, KeyboardInterrupt):
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
            raise
    return {'argv': list(map(str, argv)), 'returncode': code,
            'seconds': time.monotonic() - start, 'log': str(log)}


def ensure_source(source, base, upstream, log):
    if (source / '.git').exists():
        return
    if source.exists() and any(source.iterdir()):
        raise GateFailure('New replay source must be absent or empty: ' + str(source))
    with log.open('w') as stream:
        for argv in (
                ['git', 'clone', '--no-checkout', '--filter=blob:none', upstream, str(source)],
                ['git', '-C', str(source), 'config', 'user.name', 'Canonical patch progression'],
                ['git', '-C', str(source), 'config', 'user.email', 'patch-progression@localhost'],
                ['git', '-C', str(source), 'checkout', '-b', 'canonical-progress', base]):
            completed = subprocess.run(argv, stdout=stream, stderr=subprocess.STDOUT)
            if completed.returncode:
                raise GateFailure('Replay source initialization failed; see ' + str(log))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--upstream', default='https://github.com/Bitcoin-ABC/bitcoin-abc.git',
                        help='Public ABC URL or explicit local clone used only to create an absent --source')
    parser.add_argument('-N', '--start', type=int, default=0, help='Replay base and patches 1..N, then validate N and continue')
    parser.add_argument('--end', type=int)
    parser.add_argument('--point', type=int, help='Replay and verify the prefix, then gate/measure only this boundary; no earlier benchmark results required')
    parser.add_argument('--repetitions', type=int, default=1)
    parser.add_argument('--jobs', type=int, default=2)
    args = parser.parse_args()
    if args.point is not None:
        if args.start != 0 or args.end is not None:
            parser.error('--point cannot be combined with -N/--start or --end')
        args.start = args.end = args.point
    if args.repetitions < 1:
        parser.error('At least one runtime repetition is required')
    candidate, data, source, build = (p.resolve() for p in (args.candidate, args.data, args.source, args.build))
    data.mkdir(parents=True, exist_ok=True)
    lock = (data / 'runner.lock').open('w')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    base, entries = manifest(candidate)
    ensure_source(source, base, args.upstream, data / 'source-initialization.log')
    source_lock = Path(git(source, 'rev-parse', '--path-format=absolute', '--git-path', 'progression.lock')).open('w')
    fcntl.flock(source_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    end = len(entries) - 1 if args.end is None else args.end
    if not 0 <= args.start <= end < len(entries):
        parser.error('Invalid patch range')
    harness, environment = fingerprint(candidate, args.repetitions)
    atomic(data / 'environment.json', environment)
    outer = git(candidate, 'rev-parse', 'HEAD')
    if git(candidate, 'status', '--porcelain', '--untracked-files=no'):
        raise GateFailure('Commit candidate changes before starting canonical replay')
    atomic(data / 'manifest.json', {'base': base, 'candidate_commit': outer, 'entries': entries})
    # Refuse a resume past absent, stale, or failed evidence. Earlier repairs must
    # resume at the first invalidated patch, never at an old later success.
    for entry in ([] if args.point is not None else entries[:args.start]):
        path = data / f"patch_{entry['index']:03}.json"
        old = json.loads(path.read_text()) if path.exists() else {}
        if old.get('status') != 'ok' or old.get('prefix_sha256') != entry['prefix_sha256'] or not matching_harness(old, harness, data):
            raise GateFailure(f"Resume blocked at {entry['index']}: missing, stale, or failed preceding gates")
    for entry in entries:
        path = data / f"patch_{entry['index']:03}.json"
        if path.exists():
            old = json.loads(path.read_text())
            if old.get('prefix_sha256') != entry['prefix_sha256'] or not matching_harness(old, harness, data):
                old['invalidated_at'] = now()
                old['invalidated_reason'] = 'canonical prefix or harness/compiler identity changed'
                old['previous_status'] = old['status']
                old['status'] = 'invalidated'
                atomic(path, old)
    saved = save_mtimes(source)
    if git(source, 'status', '--porcelain'):
        raise GateFailure('Source has uncommitted changes; fold repairs into canonical mailboxes before resuming')
    am_state = Path(git(source, 'rev-parse', '--path-format=absolute', '--git-path', 'rebase-apply'))
    if am_state.exists():
        subprocess.run(['git', '-C', str(source), 'am', '--abort'], check=True, stdout=subprocess.DEVNULL)
    subprocess.run(['git', '-C', str(source), 'reset', '--hard', base], check=True, stdout=subprocess.DEVNULL)
    subprocess.run(['git', '-C', str(source), 'clean', '-fd'], check=True, stdout=subprocess.DEVNULL)
    harness_dir = candidate / 'daemon/patch-audit/progression/scripts'
    for entry in entries[:end + 1]:
        index = entry['index']
        attempt = data / 'attempts' / f"patch_{index:03}" / dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        attempt.mkdir(parents=True)
        path = data / f'patch_{index:03}.json'
        previous = json.loads(path.read_text()) if path.exists() else {}
        record = {**entry, 'status': 'running', 'candidate_commit': outer, 'harness_sha256': harness,
                  'started_utc': now(), 'commands': [], 'metrics': {'runs': [], 'kernel_runs': []},
                  'repetitions': args.repetitions, 'attempt': str(attempt)}

        def persist():
            atomic(attempt / 'record.json', record)
            if index >= args.start or record['status'] != 'running':
                atomic(path, record)

        def run(name, argv, timeout=7200, env=None):
            command = run_command(argv, attempt / (name + '.log'), timeout, env)
            record['commands'].append(command)
            persist()
            if command['returncode']:
                raise GateFailure(name + ' failed')
            return command

        try:
            if index:
                run('apply', patch_apply_command(source, entry['path']), 120)
            record['source_sha'] = git(source, 'rev-parse', 'HEAD')
            record['source_tree'] = git(source, 'rev-parse', 'HEAD^{tree}')
            if args.point is not None:
                expected = (git(source, 'rev-parse', base + '^{tree}') if index == 0
                            else entry.get('canonical_source_tree'))
                if not expected or expected != record['source_tree']:
                    raise GateFailure('Sparse replay does not match canonical source tree at ' + str(index))
            if index < args.start:
                if args.point is None:
                    old = json.loads(path.read_text())
                    if old['source_tree'] != record['source_tree']:
                        raise GateFailure('Clean prefix replay does not match validated source tree')
                continue
            if index == args.start:
                restore_mtimes(source, saved)
            old = previous
            if (old.get('status') == 'ok' and old.get('prefix_sha256') == entry['prefix_sha256']
                    and matching_harness(old, harness, data) and old.get('source_tree') == record['source_tree']):
                print(json.dumps({'patch': index, 'label': entry['label'], 'status': 'reused'}), flush=True)
                atomic(path, old)
                continue
            print(json.dumps({'patch': index, 'label': entry['label'], 'status': 'start'}), flush=True)
            persist()
            run('configure', ['cmake', '-GNinja', '-S', source, '-B', build, *FLAGS])
            daemon = 'lotusd' if 'add_executable(lotusd' in (source / 'src/CMakeLists.txt').read_text() else 'bitcoind'
            targets = subprocess.check_output(['ninja', '-C', str(build), '-t', 'targets', 'all'], text=True)
            extras = [target for target in ('bitcoin-bench', 'bitcoin-cli', 'lotus-cli', 'test_lotus_v2_disk_state') if re.search('^' + target + ':', targets, re.M)]
            built = run('build', ['ninja', '-C', build, '-j', str(args.jobs), daemon, 'test_bitcoin', 'test-avalanche', *extras])
            record['incremental_build_seconds'] = built['seconds']
            record['binary_sha256'] = digest((build / 'src' / daemon).read_bytes())
            record['build_passed'] = True
            listing = subprocess.run([build / 'src/test/test_bitcoin', '--list_content'], text=True, capture_output=True)
            if listing.returncode:
                raise GateFailure('Native test enumeration failed')
            available = listing.stdout + listing.stderr
            av_listing = subprocess.run([build / 'src/avalanche/test/test-avalanche', '--list_content'], text=True, capture_output=True)
            if av_listing.returncode:
                raise GateFailure('Avalanche test enumeration failed')
            suites, av_suites, missing_suites = native_suite_selection(
                source, entries[:index + 1], available, av_listing.stdout + av_listing.stderr)
            record['unit_suites'] = suites
            record['avalanche_suites'] = av_suites
            record['missing_native_suites'] = missing_suites
            if missing_suites:
                raise GateFailure('Native test suites exist in source but are not registered: ' + json.dumps(missing_suites))
            run('unit', [build / 'src/test/test_bitcoin', '--run_test=' + ','.join(suites), '--report_level=detailed'], 3600)
            run('avalanche', [build / 'src/avalanche/test/test-avalanche', '--run_test=' + ','.join(av_suites), '--report_level=detailed'], 3600)
            python_modules = sorted({module for prior in entries[:index + 1]
                                     for module in prior.get('contract', {}).get('required_python_unittests', [])})
            record['python_unittests'] = python_modules
            if python_modules:
                python_env = dict(os.environ, PYTHONPATH=str(source / 'test/functional'))
                run('python_wire', [sys.executable, '-m', 'unittest', *python_modules], 300, env=python_env)
            functional_tests = sorted({test for prior in entries[:index + 1]
                                       for test in prior.get('contract', {}).get('required_functional_tests', [])})
            record['functional_tests'] = functional_tests
            for test in functional_tests:
                test_path = source / 'test/functional' / test
                if not test_path.is_file():
                    raise GateFailure('Required functional test missing: ' + test)
                test_env = dict(os.environ, TEST_RUNNER_PORT_MIN='32000')
                run('functional_' + Path(test).stem, [sys.executable, test_path,
                    '--configfile=' + str(build / 'test/config.ini'), '--portseed=0',
                    '--cachedir=' + str(attempt / 'functional-cache'),
                    '--tmpdir=' + str(attempt / ('functional-' + Path(test).stem))], 600, env=test_env)
            if 'test_lotus_v2_disk_state' in extras:
                run('disk_state', [next(build.rglob('test_lotus_v2_disk_state'))], 3600)
            # Compile the migrated Chronik backend and its subsequent integration
            # boundaries, independently of the default daemon feature selection.
            if index and (any(name.startswith('chronik/') for name in entry['files'])):
                chronik = build.with_name(build.name + '-chronik')
                chronik_python = environment['compilers']['chronik_python']['path']
                env = dict(os.environ, PYO3_PYTHON=chronik_python)
                run('chronik_configure', ['cmake', '-GNinja', '-S', source, '-B', chronik,
                    *[f for f in FLAGS if not f.startswith('-DBUILD_CHRONIK=')], '-DBUILD_CHRONIK=ON',
                    '-DPython_EXECUTABLE=' + chronik_python], env=env)
                run('chronik_build', ['ninja', '-C', chronik, '-j', '8', 'chronik'], env=env)
                record['chronik_compile_passed'] = True
                if any(name.startswith('chronik/chronik-db/') for name in entry['files']):
                    test_env = dict(env, CARGO_TARGET_DIR=str(chronik / 'cargo-tests'))
                    run('chronik_db_tests', ['cargo', 'test', '--locked', '--manifest-path', source / 'Cargo.toml',
                                            '-p', 'chronik-db', '--lib'], 3600, env=test_env)
                    record['chronik_db_tests_passed'] = True
            record['correctness_passed'] = True
            run('source_unchanged', ['git', '-C', source, 'diff', '--exit-code', 'HEAD'], 30)
            for repetition in range(args.repetitions):
                if 'v2_kernel_throughput_benchmark' in available:
                    command = run(f'kernel_{repetition}', [build / 'src/test/test_bitcoin',
                        '--run_test=lotus_v2_tests/v2_kernel_throughput_benchmark', '--report_level=detailed'], 3600)
                    values, workload = parse_kernel_output(Path(command['log']).read_text())
                    if repetition and record['metrics'].get('kernel_workload_id') != workload:
                        raise GateFailure('Kernel workload changed between repetitions')
                    record['metrics']['kernel_workload_id'] = workload
                    record['metrics']['kernel_benchmark_source_sha256'] = digest(
                        (source / 'src/test/lotus_v2_tests.cpp').read_bytes())
                    record['metrics']['kernel_runs'].append(values)
                workloads = runtime_workloads(entry, source, available)
                record['runtime_workloads'] = [name for name, _, _ in workloads]
                for name, script, options in workloads:
                    output = attempt / f'{name}_{repetition}.json'
                    run(f'{name}_{repetition}', [sys.executable, harness_dir / script, '--daemon', build / 'src' / daemon,
                                                '--output', output, *options], 1800)
                    measured = json.loads(output.read_text())
                    if measured.get('status') != 'ok':
                        raise GateFailure(name + ' workload did not report success')
                    record['metrics']['runs'].append(measured)
                    persist()
            keys = set().union(*(value.keys() for value in record['metrics']['kernel_runs']))
            record['metrics']['kernel'] = {key: statistics.median(value[key] for value in record['metrics']['kernel_runs'] if key in value) for key in keys}
            record['kernel_availability'] = 'measured' if keys else 'native benchmark absent at this source boundary'
            record['status'] = 'ok'
            record['finished_utc'] = now()
            persist()
            atomic(data / 'journal.json', {'last_passed': index, 'next_patch': index + 1, 'candidate_commit': outer, 'updated': now()})
            print(json.dumps({'patch': index, 'label': entry['label'], 'status': 'ok'}), flush=True)
        except (Exception, KeyboardInterrupt) as error:
            record['status'] = 'interrupted' if isinstance(error, KeyboardInterrupt) else 'failed'
            record['error'] = str(error)
            record['finished_utc'] = now()
            record['working_diff'] = git(source, 'diff', 'HEAD')
            failures = []
            for command in record['commands']:
                if not command['returncode']:
                    continue
                content = re.sub(r'\x1b\[[0-9;]*m', '', Path(command['log']).read_text(errors='replace'))
                failures.append({**command, 'test_names': sorted(set(re.findall(r'error: in "([^"]+)"', content))),
                                 'errors': [line for line in content.splitlines() if 'error:' in line or 'FAILED:' in line][-30:]})
            record['failure_details'] = failures
            persist()
            packet = {'patch': index, 'label': entry['label'], 'original_patch': entry.get('original_patch'),
                      'contract': entry.get('contract'), 'contract_sha256': entry.get('contract_sha256'),
                      'status': record['status'], 'error': str(error), 'record': str(path),
                      'source': str(source), 'candidate': str(candidate), 'failure_details': failures,
                      'resume': [sys.executable, str(Path(__file__)), '--data', str(data), '--source', str(source),
                                 '--build', str(build), '-N', str(index), '--repetitions', str(args.repetitions)]}
            if args.point is not None:
                packet['resume'] = [sys.executable, str(Path(__file__)), '--candidate', str(candidate),
                                    '--data', str(data), '--source', str(source), '--build', str(build),
                                    '--point', str(args.point), '--repetitions', str(args.repetitions),
                                    '--jobs', str(args.jobs), '--upstream', args.upstream]
            atomic(data / 'failure.json', packet)
            atomic(data / 'journal.json', {**packet, 'updated': now()})
            print(json.dumps(packet), flush=True)
            source_lock.close()
            lock.close()
            return 1
    print(json.dumps({'status': 'complete' if end == len(entries) - 1 else 'segment_complete', 'last_patch': end, 'candidate_commit': outer}), flush=True)
    source_lock.close()
    lock.close()
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as error:
        print(json.dumps({'status': 'preflight_failed', 'error': str(error)}), flush=True)
        sys.exit(1)
