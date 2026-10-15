#!/usr/bin/env python3
"""Rerun selected native suites, preserving unchanged-suite profiles and provenance."""
import argparse,json,os,pathlib,re,shutil,subprocess
p=argparse.ArgumentParser();p.add_argument('native',type=pathlib.Path);p.add_argument('previous',type=pathlib.Path);p.add_argument('output',type=pathlib.Path);p.add_argument('--target',action='append',required=True);a=p.parse_args()
a.native=a.native.resolve();a.previous=a.previous.resolve();a.output=a.output.resolve()
if a.output.exists():raise SystemExit('Use a fresh output directory')
a.output.mkdir(parents=True);profiles=a.output/'profiles';profiles.mkdir()
old=json.loads((a.previous/'tests.json').read_text());inventory=json.loads((a.previous/'inventory.json').read_text())
old_pin=inventory['native_commit'];new_pin=subprocess.check_output(['git','-C',str(a.native),'rev-parse','HEAD'],text=True).strip()
changed=subprocess.check_output(['git','-C',str(a.native),'diff','--name-only',old_pin,new_pin],text=True).splitlines()
def test_source(path):
 q=pathlib.PurePosixPath(path)
 return q.name.startswith('test_') or any(part.endswith('_test') for part in q.parts)
if any(not test_source(f) for f in changed):raise SystemExit('Reusing profiles requires test-only source changes')
# Check Ninja's actual compiler dependency inventory, including transitive test headers.
deps=subprocess.check_output(['ninja','-C',str(a.native/'build-coverage'),'-t','deps'],text=True)
changed_absolute={str(a.native/f) for f in changed};affected=set();owner=None
for line in deps.splitlines():
 if line and not line.startswith(' '):
  match=re.search(r'CMakeFiles/(test_lotus_v2_\w+)\.dir/',line);owner=match.group(1) if match else None
 elif owner and line.strip() in changed_absolute:affected.add(owner)
if not affected.issubset(set(a.target)):raise SystemExit('Changed dependencies require rerunning: '+str(sorted(affected-set(a.target))))

rows=[]
for result in old:
 target=result['target'];record=dict(result);record['profiles']=[]
 if target in a.target:
  work=a.output/'work'/target;work.mkdir(parents=True)
  env=dict(os.environ,LLVM_PROFILE_FILE=str(profiles/(target+'-%p.profraw')))
  with (a.output/(target+'.log')).open('w') as log:
   run=subprocess.run([str(a.native/'build-coverage/src/lotus_v2'/target)],cwd=work,env=env,stdout=log,stderr=subprocess.STDOUT)
  record.update(exit_code=run.returncode,source_pin=new_pin,reused=False)
  record['profiles']=[str(f) for f in profiles.glob(target+'-*.profraw')]
 else:
  for name in result['profiles']:
   old_file=pathlib.Path(name);new_file=profiles/old_file.name;shutil.copyfile(old_file,new_file);record['profiles'].append(str(new_file))
  log=a.previous/(target+'.log')
  if log.exists():shutil.copyfile(log,a.output/log.name)
  record.update(source_pin=old_pin,reused=True)
 if not record['profiles']:raise SystemExit(f'Missing profiles for {target}')
 rows.append(record)
(a.output/'tests.json').write_text(json.dumps(rows,indent=2)+'\n')
(a.output/'rerun-provenance.json').write_text(json.dumps({'original_pin':old_pin,'repaired_pin':new_pin,'changed_test_files':changed,'affected_targets_from_ninja_dependencies':sorted(affected),'rerun_targets':a.target,'original_report':str(a.previous),'reused_profiles':'Only unchanged suites; production source diff is empty'},indent=2)+'\n')
# Existing exporter verifies the complete target/profile inventory and fails for any failed test.
subprocess.run(['python3',str(pathlib.Path(__file__).with_name('native.py')),str(a.native),str(a.output),'--export-existing'],check=True)
