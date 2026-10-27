"""Apply independently shared repairs; retain author-owned blockers explicitly."""
import copy,difflib,hashlib,json
from pathlib import Path
here=Path(__file__).resolve().parent;repo=here.parents[2]
initial=json.loads((here/'ledger-initial.json').read_text());ledger=copy.deepcopy(initial)
a=json.loads((here/'revision-a.json').read_text());b=json.loads((here/'revision-b.json').read_text())
assert {o['finding'] for o in a['operations']}=={'EW4','EW5','EW6','EW7'}
# Both revisions agree on all three repairs. EW5 is placed in different claims;
# use A's single local statistical consequence instead of duplicating the rule.
operations=copy.deepcopy(a['operations']);claims={c['id']:c for d in ledger for c in d['claims']}
for op in operations:
    c=claims[op['claim_id']];assert c['text']==op['old_text'];c['text']=op['new_text']
metadata=[]
for c in claims.values():
    old=c['text'];new=old
    if old.startswith('# Snowstorm executable-contract test proposal — review round 5'):new=old.replace('round 5','round 6')
    if old.startswith('OPEN EW-INFINITY: H=0 and opposite infinite weights;'):new=old.rstrip()+' OPEN EW-RESPONSE: majority-answer response selection can produce opposite FINAL; hard safety assertions are preserved.\n'
    if old.startswith('The single-fast-voter attack is now guarded'):new='The single-fast-voter attack is guarded by the majority answer floor. D=1 zero-weight nontermination is a documented liveness limitation; no minimum D or special-case weight is invented. '
    if old.startswith('This revision follows the maintained input bundle in order, including the final per-item'):new='This revision follows the maintained input bundle in order, including evidence-weighted rounds, rules10–15 and Lotus C++ naming. These supersede earlier streak/full-sample-quorum and probe/deadline rules where they conflict. '
    if new!=old:metadata.append({'claim_id':c['id'],'old_text':old,'new_text':new});c['text']=new
for doc in ledger:
    content=''.join(c['text'] for c in doc['claims']);doc['sha256']=hashlib.sha256(content.encode()).hexdigest();(repo/doc['path']).write_text(content)
(here/'ledger-accepted.json').write_text(json.dumps(ledger,ensure_ascii=False,indent=2)+'\n')
(here/'decision.json').write_text(json.dumps({'substantive_operations':operations,'metadata_operations':metadata,'shared_repair_findings':['EW4 disclosure/regression','EW5 D1 limitation','EW6 advertised A operands','EW7 terminal outsider gate filter'],'raw_operation_disagreement':3/9,'substantive_repair_disagreement':0,'accepted':True,'locks_added':[],'unresolved':['EW1','EW2','EW3','EW4'],'converged':False,'iterations_used':1,'iteration_cap':8,'next_scope':'EW1 arithmetic, pending author answer','execution_status':'awaiting missing author semantics; not converged or cap-exhausted'},ensure_ascii=False,indent=2)+'\n')
old=(repo/'docs/lotus-v2/snowstorm.md').read_text();spec=(repo/'.scratch/oneshot/SPEC-PROPOSED.md').read_text();begin='<!-- snowstorm-core-normative:begin -->\n';end='<!-- snowstorm-core-normative:end -->\n'
assert old.count(begin)==old.count(end)==1
norm=spec[spec.index('# Reconciliation core: normative specification\n'):spec.index('\n---\n\n## Remaining contract questions')]
new=old[:old.index(begin)+len(begin)]+norm.rstrip()+'\n'+old[old.index(end):]
(repo/'.scratch/oneshot/normative-PROPOSED.diff').write_text(''.join(difflib.unified_diff(old.splitlines(keepends=True),new.splitlines(keepends=True),fromfile='a/docs/lotus-v2/snowstorm.md',tofile='b/docs/lotus-v2/snowstorm.md')))
print(json.dumps({d['path']:{'sha256':d['sha256'],'bytes':len((repo/d['path']).read_bytes())} for d in ledger},indent=2))
