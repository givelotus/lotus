#!/usr/bin/env python3
"""Prepare pinned local controller inputs offline; never launch a process."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil

MANIFEST_SHA256 = 'edad7f53b49ce09f62250947240fa4590664e16e53d40fe0cc873e3d6cfb590b'
LIMITS = dict(deadline_ms=60000, max_line_bytes=8388608,
              max_wallet_bytes=4194304, max_events=256, max_blocks=256,
              max_batches=4096)


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def executable(value):
    path = Path(value).expanduser().resolve(strict=True)
    if not path.is_file() or not os.access(path, os.X_OK):
        raise ValueError(f'not an executable file: {path}')
    return path


def prepare(args):
    fixtures = Path(__file__).resolve().parent / 'fixtures'
    manifest = fixtures / 'local-test-manifest.json'
    network = fixtures / 'loopback-network.json'
    if digest(manifest) != MANIFEST_SHA256:
        raise ValueError('bundled tested manifest digest differs')
    expected_network = dict(schema=1, magic='31435769',
                            listen=dict(address='127.0.0.1', port=0), connect=[],
                            receive_limit=2097152, local_policy='bounded-local-v1')
    if json.loads(network.read_text()) != expected_network:
        raise ValueError('bundled loopback network differs')
    daemon, wallet, node = map(executable, (args.daemon, args.wallet_client, args.node))
    compiler = Path(args.compiler).expanduser().resolve(strict=True)
    compiler_files = [compiler / 'dist/generic.js',
                      compiler / 'examples/gallery/payment.lotus']
    for path in compiler_files:
        if not path.is_file():
            raise ValueError(f'missing built compiler input: {path}')
    output_arg = Path(args.output).expanduser()
    session_arg = Path(args.session).expanduser()
    # Refuse leaf symlinks before resolving parent aliases and '..'.
    if output_arg.is_symlink() or session_arg.is_symlink():
        raise ValueError('output and session must not be symlinks')
    output = output_arg.resolve(strict=False)
    session = session_arg.resolve(strict=False)
    if output.exists() or output.is_symlink():
        raise ValueError('output must be a fresh directory')
    if session.exists() or session.is_symlink() or not session.parent.is_dir():
        raise ValueError('session must not exist and its parent must exist')
    if output == session or output in session.parents or session in output.parents:
        raise ValueError('output and session must be separate directories')
    if not output.parent.is_dir():
        raise ValueError('output parent must already exist')
    pinned = lambda path: dict(path=str(path), sha256=digest(path))
    config = dict(schema=1, manifest=dict(path='manifest.json', sha256=digest(manifest)),
                  daemon=pinned(daemon), wallet_client=pinned(wallet),
                  compiler=dict(directory=str(compiler), node=str(node)), limits=LIMITS,
                  nodes=[dict(name=name, home=f'nodes/{name}',
                              network=dict(path='network.json', sha256=digest(network)),
                              connect_to=[] if name == 'a' else ['a']) for name in ('a', 'b')])
    # Compiler/Node audit pins supplement the controller's native executable pins.
    provenance = dict(schema=1, purpose='isolated-local-test-only',
                      fixture=json.loads((fixtures / 'provenance.json').read_text()),
                      inputs=dict(node=pinned(node), compiler_files=[pinned(p) for p in compiler_files]),
                      session=str(session), preparation='offline; no executable invoked')
    output.mkdir(mode=0o700)  # exclusive creation; never overwrite prior evidence
    shutil.copyfile(manifest, output / 'manifest.json')
    shutil.copyfile(network, output / 'network.json')
    for name, data in [('config.json', config), ('provenance.json', provenance)]:
        (output / name).write_text(json.dumps(data, indent=2) + '\n')
    command = ['python3', str(Path(__file__).resolve().parent / 'devnet.py'),
               '--config', str(output / 'config.json'), '--session', str(session)]
    (output / 'commands.txt').write_text(shlex.join(command + ['--check']) + '\n' + shlex.join(command) + '\n')
    return dict(config=str(output / 'config.json'), session=str(session),
                session_created=False, commands=str(output / 'commands.txt'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ('daemon', 'wallet-client', 'compiler', 'node', 'output', 'session'):
        parser.add_argument('--' + option, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(prepare(args), sort_keys=True))
    except (OSError, ValueError) as error:
        parser.exit(2, f'prepare-local: {error}\n')


if __name__ == '__main__':
    main()
