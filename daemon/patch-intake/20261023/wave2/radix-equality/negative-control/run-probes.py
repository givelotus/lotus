"""Build the same actual-tree probe with the recorded pre-fix and current key."""
import json
import pathlib
import shlex
import subprocess
import sys

here = pathlib.Path(__file__).resolve().parent
build = pathlib.Path(sys.argv[1]).resolve()
compile_line = subprocess.check_output(
    ['ninja', '-t', 'commands', 'src/test/CMakeFiles/test_bitcoin.dir/radix_tests.cpp.o'],
    cwd=build, text=True).splitlines()[-1]
link_line = subprocess.check_output(
    ['ninja', '-t', 'commands', 'src/test/test_bitcoin'],
    cwd=build, text=True).splitlines()[-1]
link_template = shlex.split(link_line)
# Ninja's CMake link rule wraps one compiler command in shell no-ops.
link_template = link_template[link_template.index('&&') + 1:]
link_template = link_template[:link_template.index('&&')]
results = []
for version in ['pre-fix', 'current']:
    obj = here / (version + '.o')
    binary = here / (version + '-probe')
    compile_cmd = shlex.split(compile_line)
    compile_cmd[compile_cmd.index('-o') + 1] = str(obj)
    compile_cmd[compile_cmd.index('-c') + 1] = str(here / 'radix_equality_probe.cpp')
    for flag in ['-MF', '-MT']:
        if flag in compile_cmd:
            index = compile_cmd.index(flag)
            compile_cmd[index + 1] = str(obj) + ('.d' if flag == '-MF' else '')
    if version == 'pre-fix':
        compile_cmd.insert(1, '-I' + str(here / 'pre-fix'))
    link_cmd = [arg for arg in link_template if not arg.endswith('.o')]
    link_cmd[link_cmd.index('-o') + 1] = str(binary)
    link_cmd.insert(1, str(obj))
    record = {'version': version, 'compile': compile_cmd, 'link': link_cmd}
    with (here / (version + '-build.log')).open('w') as output:
        subprocess.run(compile_cmd, cwd=build, stdout=output, stderr=subprocess.STDOUT, check=True)
        subprocess.run(link_cmd, cwd=build, stdout=output, stderr=subprocess.STDOUT, check=True)
    result = subprocess.run([str(binary)], capture_output=True, text=True)
    (here / (version + '-run.log')).write_text(result.stdout + result.stderr)
    record.update(exit_code=result.returncode, output=result.stdout)
    results.append(record)
(here / 'RESULT.json').write_text(json.dumps(results, indent=2) + '\n')
print(json.dumps([{k: record[k] for k in ['version', 'exit_code', 'output']} for record in results], indent=2))
assert results[0]['exit_code'] == 1, 'Pre-fix probe must expose wrong leaf identity'
assert results[1]['exit_code'] == 0, 'Corrected actual-tree probe must pass'
