"""Current amended proposal integrity; does not assert unresolved protocol correctness."""
import hashlib,json,re,subprocess
from pathlib import Path
here=Path(__file__).resolve().parent;repo=here.parents[2];checks=[]
def Check(name,condition):
    assert condition,name
    checks.append(name)
a=json.loads((here/'author-amendment.json').read_text());bundle=(repo/'.scratch/inputs/SNOWSTORM-SPEC-INPUTS.md').read_bytes();digest=hashlib.sha256(bundle).hexdigest()
Check('all input prefixes preserved',hashlib.sha256(bundle[:a['prefix_bytes']]).hexdigest()==a['prefix_sha256'])
messages=[a['verbatim']]+[x['verbatim'] for x in a['followup_messages']]
positions=[bundle.decode().index(m) for m in messages]
Check('all operator messages verbatim in order',positions==sorted(positions))
Check('latest input digest matches recorded authority',digest==a['current_input_sha256'])
ledger_path=here/'ledger-accepted.json'
if not ledger_path.exists():ledger_path=here/'ledger-initial.json'
ledger=json.loads(ledger_path.read_text())
for d in ledger:
 s=(repo/d['path']).read_text()
 Check(d['path']+' exact ledger rendering',s==''.join(c['text'] for c in d['claims']))
 Check(d['path']+' digest',hashlib.sha256(s.encode()).hexdigest()==d['sha256'])
 Check(d['path']+' pinned input',digest in s)
spec=(repo/ledger[0]['path']).read_text();tests=(repo/ledger[1]['path']).read_text()
old=subprocess.check_output(['git','show','b3d6351b94:.scratch/oneshot/TESTS-PROPOSED.md'],cwd=repo).decode();pattern=r'^\| [a-z_]+\.cpp \|.*$'
Check('104 historical inventory rows preserved',re.findall(pattern,tests,re.M)==re.findall(pattern,old,re.M) and len(re.findall(pattern,tests,re.M))==104)
Check('answer floor guards all item updates','voteCount>=answerFloor' in spec and 'below this floor add0, count no success' in spec)
Check('majority-answer deadline backoff replaces zero-only','fewer than floor(K/2)+1 sampled peers answering at all' in spec)
Check('no n0 ambiguity remains','OPEN EW-ZERO' not in spec and 'OPEN EW-ZERO' not in tests)
Check('floor counterexample regression added','T16OneFastYesFifteenSlowNo' in tests)
Check('own Pending vs received YES distinction explicit','never casts a yes for its own Pending' in spec and 'does not prohibit receiving a yes' in spec)
Check('FINAL-in Pending freeze guard','AND there is no live FINAL-in Pending item' in spec)
Check('FINAL-out projection and no exclusions','FINAL-out IDs occur in neither cells nor exclusions' in spec and 'Ref=(A union Pending) minus FINAL-out' in spec)
Check('probe fallback uses difference estimate','RequiredSymbols(estimatedProbeDifference)' in spec and 'max(2*(h+1)' not in spec)
Check('K crossover intentionally unselected','OPEN K-CROSSOVER' in spec and 'K=min(D' not in spec)
Check('arithmetic blockers not hidden','OPEN EW-INFINITY' in spec and 'OPEN EW-PREFERENCE' in spec)
Check('reference vectors cover required D/all/half answers','| 500 |' in tests and 'Half-answer rows never meet' in tests)
cpp=re.search(r'```cpp\n(.*?)```',spec,re.S).group(1)
Check('C++ methods use UpperCamelCase','OnTransactionAdmitted' in cpp and 'GetStatistics' in cpp and not re.search(r'\b[a-z]+_[a-z_]+\s*\(',cpp))
Check('C++ public interface braces and indentation','class SnowstormNode\n{\npublic:\n    explicit' in cpp)
Check('frozen manifest unchanged',hashlib.sha256((repo/'daemon/lotusd/src/snowstorm/ACCEPTANCE.sha256').read_bytes()).hexdigest()=='4aa896175e94e472f645c2d7ca25552a3efb079a789dd8aaca203b0e318906db')
Check('canonical parent unchanged',(repo/'docs/lotus-v2/snowstorm.md').read_bytes()==subprocess.check_output(['git','show','b3d6351b94:docs/lotus-v2/snowstorm.md'],cwd=repo))
Check('review patch applies',subprocess.run(['git','apply','--check','.scratch/oneshot/normative-PROPOSED.diff'],cwd=repo,capture_output=True).returncode==0)
Check('Markdown/Python whitespace',subprocess.run(['git','diff','--check','--','*.md','*.py'],cwd=repo,capture_output=True).returncode==0)
print(json.dumps(dict(passed=len(checks),checks=checks,input_sha256=digest,input_bytes=len(bundle),spec_bytes=len(spec.encode()),test_bytes=len(tests.encode()),unresolved_mathematical_cases=True,implementation_executed=False),indent=2))
