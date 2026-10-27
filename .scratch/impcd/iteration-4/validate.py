"""Review integrity checks, deliberately independent of production acceptance."""
import hashlib,json,re,subprocess
from pathlib import Path
here=Path(__file__).resolve().parent;repo=here.parents[2]
initial=json.loads((here/'ledger-initial.json').read_text())
accepted=json.loads((here/'ledger-accepted.json').read_text())
checks=[]
def check(name,condition):
    assert condition,name
    checks.append(name)
for old,new in zip(initial,accepted):
    current=(repo/new['path']).read_text()
    check(new['path']+' ledger rendering',current==''.join(c['text'] for c in new['claims']))
    check(new['path']+' digest',hashlib.sha256(current.encode()).hexdigest()==new['sha256'])
    check(new['path']+' stable claim identities',[c['id'] for c in old['claims']]==[c['id'] for c in new['claims']])
    check(new['path']+' no premature locks',all(c['status']=='open' for c in new['claims']))
spec=(repo/accepted[0]['path']).read_text();tests=(repo/accepted[1]['path']).read_text()
baseline=''.join(c['text'] for c in initial[1]['claims'])
pattern=r'^\| [a-z_]+\.cpp \|.*$'
check('104 historical inventory rows unchanged',re.findall(pattern,tests,re.M)==re.findall(pattern,baseline,re.M) and len(re.findall(pattern,tests,re.M))==104)
oldclaims={c['id']:c['text'] for d in initial for c in d['claims']}
newclaims={c['id']:c['text'] for d in accepted for c in d['claims']}
check('P4 target and1000/25 workload unchanged',oldclaims['T0264']==newclaims['T0264'])
for prefix in ['D is the compatible','Item votes are the peer','For a reply still partially','For each nonfinal captured','For a nonfinal item with success','At epoch start W is the held']:
    oldline=next(x for x in ''.join(c['text'] for c in initial[0]['claims']).splitlines() if x.startswith(prefix))
    check('settled rule preserved: '+prefix,oldline in spec)
check('F1 counterexample test added','d[in]=22,d[out]=13,p=in,c=12,previous=out,not FINAL' in tests)
check('F4 total cost comparison explicit','positive n divided by zero is +infinity' in spec)
check('F2 root-vote test removed','valid root vote still counted' not in tests)
check('F3 answerer quorum instruction removed','round-end/answerer tests' not in tests)
check('F5 disclosed in both renderings',all('F5 remains OPEN' in x for x in [spec,tests]))
inputhash=hashlib.sha256((repo/'.scratch/inputs/SNOWSTORM-SPEC-INPUTS.md').read_bytes()).hexdigest()
check('input unchanged and pinned',inputhash=='e6ab26b85fe03c3c0a327b21bb5d2da7fc9c38f9a2aee178a0d584f42b1abd1d' and inputhash in spec and inputhash in tests)
manifest=repo/'daemon/lotusd/src/snowstorm/ACCEPTANCE.sha256'
check('frozen manifest unchanged',hashlib.sha256(manifest.read_bytes()).hexdigest()=='4aa896175e94e472f645c2d7ca25552a3efb079a789dd8aaca203b0e318906db')
canonical='docs/lotus-v2/snowstorm.md'
check('canonical parent unchanged',(repo/canonical).read_bytes()==subprocess.check_output(['git','show','6fa54f317c:'+canonical],cwd=repo))
check('patch applies',subprocess.run(['git','apply','--check','.scratch/oneshot/normative-PROPOSED.diff'],cwd=repo,capture_output=True).returncode==0)
check('Markdown whitespace',subprocess.run(['git','diff','--check','--','*.md'],cwd=repo,capture_output=True).returncode==0)
print(json.dumps({'passed':len(checks),'checks':checks,'spec_bytes':len(spec.encode()),'tests_bytes':len(tests.encode()),'spec_growth_percent':100*(len(spec.encode())/76725-1)},indent=2))
