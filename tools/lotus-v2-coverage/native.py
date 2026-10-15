#!/usr/bin/env python3
"""Measure all native V2 focused tests without excluding unexecuted source files."""
import argparse, json, os, pathlib, re, subprocess
p=argparse.ArgumentParser(); p.add_argument('native',type=pathlib.Path);p.add_argument('output',type=pathlib.Path);p.add_argument('--llvm',default='/opt/homebrew/opt/llvm/bin');a=p.parse_args()
a.native=a.native.resolve();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
b=a.native/'build-coverage';src=a.native/'src/lotus_v2';llvm=pathlib.Path(a.llvm)
def run(cmd,**kw):
    print(' '.join(map(str,cmd)),flush=True);return subprocess.run(list(map(str,cmd)),check=True,**kw)
targets=re.findall(r'add_executable\((test_lotus_v2_\w+)',(src/'CMakeLists.txt').read_text())
run(['cmake','--build',b,'-j2','--target',*targets])
profiles=a.output/'profiles';profiles.mkdir(exist_ok=True)
if list(profiles.glob('*.profraw')):raise SystemExit('Refusing to mix existing profiles; use a fresh output directory')
results=[];objects=[]
for target in targets:
    binary=b/'src/lotus_v2'/target;env=dict(os.environ,LLVM_PROFILE_FILE=str(profiles/(target+'-%p.profraw')))
    with (a.output/(target+'.log')).open('w') as log:
        result=subprocess.run([str(binary)],env=env,stdout=log,stderr=subprocess.STDOUT)
    found=list(profiles.glob(target+'-*.profraw'));results.append(dict(target=target,exit_code=result.returncode,profiles=[str(x) for x in found]))
    if result.returncode or not found:raise SystemExit(f'{target}: failure or missing profile; see log')
    objects.extend(['-object',str(binary)])
(a.output/'tests.json').write_text(json.dumps(results,indent=2)+'\n')
run([llvm/'llvm-profdata','merge','-sparse',*profiles.glob('*.profraw'),'-o',a.output/'native.profdata'])
# Pass every production V2 source, including unexecuted ones. Inventory separately catches files lacking mappings.
files=sorted(x for x in src.rglob('*') if x.suffix in ('.cpp','.h') and not x.name.startswith('test_') and 'vendor' not in x.parts)
wallet_files=sorted(x for x in (a.native/'src/wallet').glob('v2*') if x.suffix in ('.cpp','.h'))
for obj in sorted((b/'src/wallet/CMakeFiles/wallet.dir').glob('v2*.cpp.o')):objects.extend(['-object',str(obj)])
files += wallet_files
common=[*objects,'-instr-profile='+str(a.output/'native.profdata'),*files]
for fmt,name in [('text','native.json'),('lcov','native.lcov')]:
    with (a.output/name).open('w') as out:run([llvm/'llvm-cov','export','-format='+fmt,*common],stdout=out)
run([llvm/'llvm-cov','show',*common,'-format=html','-output-dir='+str(a.output/'html'),'-show-branches=count','-show-expansions','-show-instantiations'])
data=json.loads((a.output/'native.json').read_text());mapped={x['filename'] for d in data['data'] for x in d['files']}
(a.output/'inventory.json').write_text(json.dumps({'native_commit':subprocess.check_output(['git','-C',str(a.native),'rev-parse','HEAD'],text=True).strip(),'sources':[str(x) for x in files],'unmapped_sources':[str(x) for x in files if str(x) not in mapped],'totals':data['data'][0]['totals'],'scope':'V2 production and v2 wallet sources; vendor and test sources excluded; wallet object mappings explicitly included; Rust unmeasured'},indent=2)+'\n')
