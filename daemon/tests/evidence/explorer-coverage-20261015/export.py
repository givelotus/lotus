#!/usr/bin/env python3
"""Export the isolated explorer coverage runs; paths are explicit review artifacts."""
import argparse, json, os, pathlib, subprocess
p=argparse.ArgumentParser();p.add_argument('native',type=pathlib.Path);p.add_argument('rust_target',type=pathlib.Path);p.add_argument('rust_profiles',type=pathlib.Path);a=p.parse_args()
out=pathlib.Path(__file__).resolve().parent;n=a.native.resolve();r=out/'rust';r.mkdir(exist_ok=True)
commit=subprocess.check_output(['git','-C',str(n),'rev-parse','HEAD'],text=True).strip()
assert commit=='86201398e3df61605c2eb2d09c201ce774013e7f',commit
sysroot=pathlib.Path(subprocess.check_output(['rustc','+1.93.0','--print','sysroot'],text=True).strip())
llvm=sysroot/'lib/rustlib/aarch64-apple-darwin/bin'
objects=[]
for package in ['chronik_db','chronik_http','chronik_indexer','chronik_lib']:
    found=[x for x in (a.rust_target/'debug/deps').glob(package+'-*') if x.is_file() and '.' not in x.name and os.access(x,os.X_OK)]
    assert len(found)==1,(package,found)
    objects+=found
sources=[n/'chronik'/x for x in ['chronik-db/src/v2_explorer.rs','chronik-indexer/src/query/v2_explorer.rs','chronik-indexer/src/query/v2_assets.rs','chronik-indexer/src/query/v2_branches.rs','chronik-http/src/v2_explorer.rs','chronik-lib/src/v2.rs','chronik-lib/src/v2_server.rs','chronik-lib/src/v2_ffi.rs']]
profiles=sorted(a.rust_profiles.glob('*.profraw'))
subprocess.run([str(llvm/'llvm-profdata'),'merge','-sparse',*map(str,profiles),'-o',str(r/'api.profdata')],check=True)
args=[str(objects[0]),*['-object='+str(x) for x in objects[1:]],'-instr-profile='+str(r/'api.profdata'),*map(str,sources)]
for fmt,name in [('text','coverage.json'),('lcov','coverage.lcov')]:
    with (r/name).open('w') as dst,(r/('export-'+fmt+'.log')).open('w') as err:
        subprocess.run([str(llvm/'llvm-cov'),'export','-format='+fmt,*args],stdout=dst,stderr=err,check=True)
data=json.loads((r/'coverage.json').read_text())['data'][0]
mapped={x['filename'] for x in data['files']}
(r/'inventory.json').write_text(json.dumps({'native_commit':commit,'sources':list(map(str,sources)),'unmapped_sources':[str(x) for x in sources if str(x) not in mapped], 'objects':list(map(str,objects)),'raw_profile_count':len(profiles),'llvm_version':subprocess.check_output([str(llvm/'llvm-cov'),'--version'],text=True),'raw_totals_include_inline_http_tests':data['totals'],'branch_coverage':'unmeasured: stable Rust instrument-coverage supplies no branch records','scope':'explicit8Rustproductionfiles; inlineHTTPtestmodule must be excluded in summary; other production files are outside this denominator'},indent=2)+'\n')
