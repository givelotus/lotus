"""Integrity of the author resolutions and terminal document-review step."""
import hashlib,json,re,subprocess
from pathlib import Path
here=Path(__file__).resolve().parent;repo=here.parents[2];passed=[]
def check(name,yes):
    assert yes,name
    passed.append(name)
initial=json.loads((here/'ledger-initial.json').read_text());final=json.loads((here/'ledger-final.json').read_text());decision=json.loads((here/'decision.json').read_text())
check('two independent revisions request no substantive changes',all(json.loads((here/f'revision-{n}.json').read_text())['operations']==[] for n in ('a','b')))
check('zero substantive step and no new locks',decision['substantive_operations']==[] and decision['locks_added']==[] and decision['substantive_distance']==0)
for before,after in zip(initial,final):
    rendered=''.join(c['text'] for c in after['claims'])
    check(after['path']+' matches ledger',rendered==(repo/after['path']).read_text())
    check(after['path']+' digest',hashlib.sha256(rendered.encode()).hexdigest()==after['sha256'])
    check(after['path']+' stable IDs',[c['id'] for c in before['claims']]==[c['id'] for c in after['claims']])
spec=(repo/final[0]['path']).read_text();tests=(repo/final[1]['path']).read_text();oldspec=''.join(c['text'] for c in initial[0]['claims']);oldtests=''.join(c['text'] for c in initial[1]['claims'])
def normative(text):return text[text.index('# Reconciliation core: normative specification\n'):text.index('\n---\n\n## Remaining contract questions')]
check('protocol normative text unchanged by terminal step',normative(spec)==normative(oldspec))
check('all test requirement rows unchanged by terminal step',re.findall(r'^\|.*$',tests,re.M)==re.findall(r'^\|.*$',oldtests,re.M))
check('104 historical source inventory rows retained',len(re.findall(r'^\| [a-z_]+\.cpp \|.*$',tests,re.M))==104)
check('gate mean and entry use conditional value','sum(gate_value[x] for x in W_before)' in spec and 'p=in and gate_value[x]>=mu' in spec and 'previous success side is IN, and 0 otherwise' in spec)
check('F1 blocked-and-final entry regression retained','its gate value zero and it cannot enter frozen W' in tests and 'twelve subsequent IN successes' in tests)
check('F5 retains trials and hard safety assertions','retain1000 fixed seeds' in tests and 'hard assertions: zero false freezes and zero split freezes' in tests)
check('old positive completion-rate assertion removed',';>=99% of1000 fixed seeds freeze within25 rounds;' not in tests)
bundle=(repo/'.scratch/inputs/SNOWSTORM-SPEC-INPUTS.md').read_bytes();amend=json.loads((here.parent/'iteration-4/author-resolutions.json').read_text());digest=hashlib.sha256(bundle).hexdigest()
check('input digest pinned in both proposals',digest==amend['input_sha256'] and digest in spec and digest in tests)
check('prior48180byte input prefix preserved',hashlib.sha256(bundle[:48180]).hexdigest()==amend['input_prefix_sha256'])
check('both instructions appended verbatim in order',bundle.decode().index(amend['messages'][0]['verbatim'])<bundle.decode().index(amend['messages'][1]['verbatim']))
check('freeze manifest unchanged',hashlib.sha256((repo/'daemon/lotusd/src/snowstorm/ACCEPTANCE.sha256').read_bytes()).hexdigest()=='4aa896175e94e472f645c2d7ca25552a3efb079a789dd8aaca203b0e318906db')
check('canonical parent unchanged',(repo/'docs/lotus-v2/snowstorm.md').read_bytes()==subprocess.check_output(['git','show','355ea9be55:docs/lotus-v2/snowstorm.md'],cwd=repo))
check('review patch applies',subprocess.run(['git','apply','--check','.scratch/oneshot/normative-PROPOSED.diff'],cwd=repo,capture_output=True).returncode==0)
check('Markdown and Python whitespace',subprocess.run(['git','diff','--check','--','*.md','*.py'],cwd=repo,capture_output=True).returncode==0)
print(json.dumps({'passed':len(passed),'checks':passed,'input_sha256':digest,'input_bytes':len(bundle),'input_lines':len(bundle.splitlines()),'spec_bytes':len(spec.encode()),'test_bytes':len(tests.encode()),'spec_growth_percent':100*(len(spec.encode())/77983-1)},indent=2))
