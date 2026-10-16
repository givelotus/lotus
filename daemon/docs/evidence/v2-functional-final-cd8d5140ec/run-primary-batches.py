#!/usr/bin/env python3
"""Run only an explicitly authorized inclusive range of frozen primary batches."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

GIB = 1 << 30


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def members(pgid):
    rows = subprocess.check_output(['ps', '-axo', 'pid,ppid,pgid'], text=True)
    return [list(map(int, row.split())) for row in rows.splitlines()[1:]
            if len(row.split()) == 3 and int(row.split()[2]) == pgid]


def usage(root):
    size = count = 0
    for directory, _, files in os.walk(root, followlinks=False):
        for name in files:
            count += 1
            if count > 50000:
                raise RuntimeError('scratch_file_scan_cap')
            path = Path(directory) / name
            try:
                st = path.lstat()
            except FileNotFoundError:
                continue
            if not path.is_symlink():
                size += st.st_blocks * 512
    st = os.statvfs(root)
    return st.f_bavail * st.f_frsize, size


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, default=Path(__file__).with_name('primary-continuation.json'))
    parser.add_argument('--through', required=True, help='Last batch explicitly authorized by root')
    parser.add_argument('--start', default='batch-003')
    parser.add_argument('--execute', action='store_true', help='Requires separate owner execution authorization')
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    selected = [b for b in manifest['batches'] if args.start <= b['id'] <= args.through]
    if not selected or selected[0]['id'] != args.start or selected[-1]['id'] != args.through:
        parser.error('requested endpoints must exist in ordinary primary manifest')
    if not args.execute:
        print(json.dumps({'dry_run': True, 'batches': [{'id': b['id'], 'command': b['command'],
              'unresolved_ports': b['port_preflight_unresolved_scripts']} for b in selected]}, indent=2))
        return 0
    root = Path(manifest['root'])
    for batch in selected:
        target = root / batch['id']
        if target.exists():
            raise RuntimeError(f'refuse existing batch directory: {target}')
        target.mkdir()
        receipt = {'native_source': manifest['native_commit'], 'batch': batch['id'],
                   'command': batch['command'], 'environment': batch['environment'],
                   'started_wall_seconds': time.time(), 'outer_timeout_seconds': 1800,
                   'manifest_sha256': digest(args.manifest), 'supervisor_sha256': digest(Path(__file__)),
                   'launch_minimum_bytes': 4 * GIB, 'free_disk_floor_bytes': 2 * GIB,
                   'scratch_cap_bytes': 2 * GIB, 'resource_samples': [], 'signals': []}
        output = target / 'supervisor.json'
        process = None
        failure = None
        try:
            for name, expected in manifest['binary_hashes'].items():
                if digest(root / 'build-frozen/src' / name) != expected:
                    raise RuntimeError(f'binary_hash_changed:{name}')
            if digest(root / 'build-frozen/test/config.ini') != manifest['config_sha256']:
                raise RuntimeError('config_hash_changed')
            if digest(root / 'source/test/functional/test_runner.py') != manifest['runner_sha256']:
                raise RuntimeError('runner_hash_changed')
            for script in batch['scripts']:
                if digest(root / 'source/test/functional' / script['name']) != script['source_sha256']:
                    raise RuntimeError(f'script_hash_changed:{script["name"]}')
            free, scratch = usage(target)
            if free < 4 * GIB:
                raise RuntimeError('launch_disk_below_4GiB')
            if batch['port_preflight_unresolved_scripts']:
                raise RuntimeError('unresolved_port_node_count:' + ','.join(batch['port_preflight_unresolved_scripts']))
            # Runner sorts timing then assigns seeds0..N-1; check every possible
            # script/seed pairing. UniquePort uses base+64*seed+node offset.
            checked = []
            for seed in range(batch['variant_count']):
                for base in (44000, 47000, 50000, 53000, 56000):
                    for node in range(batch['port_preflight_max_nodes']):
                        port = base + 64 * seed + node
                        with socket.socket() as probe:
                            probe.bind(('127.0.0.1', port))
                        checked.append(port)
            receipt['port_preflight'] = {'checked': checked, 'max_nodes': batch['port_preflight_max_nodes'],
                                         'scope': 'framework initial allocation, all script/seed pairings'}
            env = os.environ.copy()
            env.update(batch['environment'])
            env['PYTHONUNBUFFERED'] = '1'
            with (target / 'runner.log').open('wb') as log:
                process = subprocess.Popen(batch['command'], env=env, stdout=log,
                                           stderr=subprocess.STDOUT, start_new_session=True)
                receipt.update(pid=process.pid, process_group=process.pid)
                write(output, receipt)
                print(json.dumps({'batch': batch['id'], 'pid': process.pid}), flush=True)
                start = time.monotonic()
                while process.poll() is None:
                    free, scratch = usage(target)
                    elapsed = time.monotonic() - start
                    receipt['resource_samples'].append({'elapsed_seconds': elapsed, 'free_bytes': free,
                                                        'scratch_allocated_bytes': scratch})
                    write(output, receipt)
                    if elapsed >= 1800:
                        raise RuntimeError('deadline')
                    if free < 2 * GIB:
                        raise RuntimeError('free_disk_floor')
                    if scratch > 2 * GIB:
                        raise RuntimeError('scratch_cap')
                    time.sleep(2)
            receipt['exit_code'] = process.wait()
            cases = ET.parse(target / 'results.xml').getroot().findall('testcase')
            actual = [case.attrib['name'] for case in cases]
            expected = [variant['id'] for variant in batch['variants']]
            if sorted(actual) != sorted(expected):
                raise RuntimeError('junit_identity_mismatch')
            receipt['cases'] = [{'id': c.attrib['name'], 'seconds': float(c.attrib['time']),
                'status': 'failed' if c.find('failure') is not None else 'not_run_or_skip_requires_review'
                if c.find('skipped') is not None else 'passed'} for c in cases]
            if receipt['exit_code'] or any(c['status'] != 'passed' for c in receipt['cases']):
                raise RuntimeError('substantive_failure_or_skip')
        except BaseException as error:
            failure = f'{type(error).__name__}:{error}'
        finally:
            # Cleanup only the process group this supervisor created, including
            # stragglers after runner exit. Never touch unrelated listeners.
            if process is not None:
                for sig, seconds in ((signal.SIGINT, 30), (signal.SIGTERM, 10), (signal.SIGKILL, 10)):
                    owned = members(process.pid)
                    if not owned:
                        break
                    receipt['signals'].append({'signal': sig.name, 'owned_members': owned})
                    write(output, receipt)
                    try:
                        os.killpg(process.pid, sig)
                    except ProcessLookupError:
                        break
                    deadline = time.monotonic() + seconds
                    while members(process.pid) and time.monotonic() < deadline:
                        process.poll()
                        time.sleep(.2)
                receipt['exit_code'] = process.wait(timeout=10)
                receipt['remaining_process_group'] = members(process.pid)
                if receipt['remaining_process_group'] or receipt['signals']:
                    failure = failure or 'process_group_required_cleanup'
            receipt.update(failure=failure, elapsed_seconds=time.time() - receipt['started_wall_seconds'])
            try:
                free, scratch = usage(target)
                receipt.update(final_free_bytes=free, final_scratch_allocated_bytes=scratch)
                if free < 2 * GIB or scratch > 2 * GIB:
                    failure = failure or 'terminal_resource_limit'
                    receipt['failure'] = failure
            except BaseException as error:
                failure = failure or str(error)
                receipt['failure'] = failure
            write(output, receipt)
        print(json.dumps({'batch': batch['id'], 'failure': failure, 'receipt': str(output)}), flush=True)
        if failure:
            return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
