"""Regenerate current proposals from the terminal ledger; no protocol edits."""
import copy,difflib,hashlib,json
from pathlib import Path
here=Path(__file__).resolve().parent;repo=here.parents[2]
ledger=copy.deepcopy(json.loads((here/'ledger-initial.json').read_text()))
for name in ('a','b'):
    assert json.loads((here/f'revision-{name}.json').read_text())['operations']==[]
status='F1 and F5 are CLOSED by the final operator resolutions in the maintained input bundle. The gate and its mean use c only for previous success IN, otherwise zero. Fixtures report freeze-round distributions at a horizon long enough to finish; zero false freezes and zero split freezes remain hard assertions. Iteration5 found no new concrete internal defect in either independent revision, and no unresolved contract finding remains from this document review. Implementation, acceptance execution and empirical security/performance validation remain future work.\n'
metadata=[]
for doc in ledger:
    for c in doc['claims']:
        old=c['text'];new=old
        if c['id']=='S0003':new='REVIEW ROUND 5: technical IMPCD document review reached an empty consensus after the author resolutions of F1 and F5. '
        if c['id'] in ('S0887','T0401'):new=status
        new=new.replace('test proposal — review round 4','test proposal — review round 5')
        new=new.replace('Review records are in `.scratch/impcd/iteration-4/`.','Review records are in `.scratch/impcd/iteration-5/`; author amendments remain recorded under iteration-4/author-resolutions.json.')
        if new!=old:metadata.append({'claim_id':c['id'],'old_text':old,'new_text':new});c['text']=new
    rendered=''.join(c['text'] for c in doc['claims'])
    doc['sha256']=hashlib.sha256(rendered.encode()).hexdigest();(repo/doc['path']).write_text(rendered)
(here/'ledger-final.json').write_text(json.dumps(ledger,ensure_ascii=False,indent=2)+'\n')
(here/'decision.json').write_text(json.dumps({'iteration':5,'substantive_operations':[],'substantive_distance':0,'disagreement':0,'disputed_changes':[],'metadata_operations':metadata,'locks_added':[],'stop':'Converged document-review fixed point; no-new-major condition met','implementation_validated':False},ensure_ascii=False,indent=2)+'\n')
parent=repo/'docs/lotus-v2/snowstorm.md';old=parent.read_text();proposal=(repo/'.scratch/oneshot/SPEC-PROPOSED.md').read_text()
begin='<!-- snowstorm-core-normative:begin -->\n';end='<!-- snowstorm-core-normative:end -->\n'
assert old.count(begin)==old.count(end)==1
norm=proposal[proposal.index('# Reconciliation core: normative specification\n'):proposal.index('\n---\n\n## Remaining contract questions')]
new=old[:old.index(begin)+len(begin)]+norm.rstrip()+'\n'+old[old.index(end):]
(repo/'.scratch/oneshot/normative-PROPOSED.diff').write_text(''.join(difflib.unified_diff(old.splitlines(keepends=True),new.splitlines(keepends=True),fromfile='a/docs/lotus-v2/snowstorm.md',tofile='b/docs/lotus-v2/snowstorm.md')))
print(json.dumps({d['path']:{'sha256':d['sha256'],'bytes':len((repo/d['path']).read_bytes())} for d in ledger},indent=2))
