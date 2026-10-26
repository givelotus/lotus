"""Compile identical actual-tree harness against exact before/after headers/libs.
No CMake mutation, source worktree or cloned repository is created.
"""
import argparse
import hashlib
import json
import pathlib
import shlex
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument('--baseline-build', required=True)
parser.add_argument('--candidate-build', required=True)
parser.add_argument('--source', required=True)
args = parser.parse_args()
here = pathlib.Path(__file__).resolve().parent
source = pathlib.Path(args.source).resolve()
records = []
for label, directory in [('before', args.baseline_build), ('after', args.candidate_build)]:
    build = pathlib.Path(directory).resolve()
    compile_line = subprocess.check_output(['ninja', '-t', 'commands',
        'src/test/CMakeFiles/test_bitcoin.dir/radix_tests.cpp.o'], cwd=build, text=True).splitlines()[-1]
    link_line = subprocess.check_output(['ninja', '-t', 'commands', 'src/test/test_bitcoin'],
        cwd=build, text=True).splitlines()[-1]
    compile_cmd = shlex.split(compile_line)
    # Use the assigned current source for common headers. The three preserved
    # equality-tip headers override only the baseline's extraction definitions.
    old_source = next(arg[2:-len('/src/.')] for arg in compile_cmd
        if arg.startswith('-I') and arg.endswith('/src/.'))
    compile_cmd = [arg.replace(old_source, str(source)) for arg in compile_cmd]
    obj = here / (label + '.o')
    binary = here / (label + '-bench')
    compile_cmd[compile_cmd.index('-o') + 1] = str(obj)
    compile_cmd[compile_cmd.index('-c') + 1] = str(here / 'radix_nibble_bench.cpp')
    for flag in ['-MF', '-MT']:
        if flag in compile_cmd:
            index = compile_cmd.index(flag)
            compile_cmd[index + 1] = str(obj) + ('.d' if flag == '-MF' else '')
    if label == 'before': compile_cmd.insert(1, '-I' + str(here / 'baseline-headers'))
    link_cmd = shlex.split(link_line)
    link_cmd = link_cmd[link_cmd.index('&&') + 1:]
    link_cmd = link_cmd[:link_cmd.index('&&')]
    link_cmd = [arg for arg in link_cmd if not arg.endswith('.o')]
    link_cmd[link_cmd.index('-o') + 1] = str(binary)
    link_cmd.insert(1, str(obj))
    with (here / (label + '-build.log')).open('w') as output:
        subprocess.run(compile_cmd, cwd=build, stdout=output, stderr=subprocess.STDOUT, check=True)
        subprocess.run(link_cmd, cwd=build, stdout=output, stderr=subprocess.STDOUT, check=True)
    archives = {}
    for arg in link_cmd:
        if arg.endswith('.a'):
            path = pathlib.Path(arg)
            if not path.is_absolute(): path = build / path
            archives[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
    records.append({'label': label, 'build': str(build), 'compile': compile_cmd,
        'link': link_cmd, 'binary': str(binary),
        'binary_sha256': hashlib.sha256(binary.read_bytes()).hexdigest(), 'archives': archives})
(here / 'BUILD.json').write_text(json.dumps(records, indent=2) + '\n')
print(json.dumps([{key: record[key] for key in ['label', 'binary', 'binary_sha256']} for record in records], indent=2))
