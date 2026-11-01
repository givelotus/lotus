"""Render in-place proposals only from the accepted claim ledger."""
import copy,difflib,hashlib,json
from pathlib import Path
here=Path(__file__).resolve().parent
repo=here.parents[2]
initial=json.loads((here/'ledger-initial.json').read_text())
a=json.loads((here/'revision-a.json').read_text())['operations']
b=json.loads((here/'revision-b.json').read_text())['operations']
# Reviser texts differ; these eleven stable-ID operations have the same repair.
# The root's substantive comparison is recorded in accepted-changes.md.
common={x['claim_id'] for x in a}&{x['claim_id'] for x in b}
assert len(common)==11
accepted=[copy.deepcopy(x) for x in a if x['claim_id'] in common]
# Preserve both the original FINAL-in entry case and the legal nonfinal case.
for op in accepted:
    if op['claim_id']=='T0067':op['new_text']=op['new_text'].replace('T13_later_nonfinal_gate_entry','T13_later_gate_entry')
    if op['claim_id']=='T0256':
        op['new_text']=op['new_text'].replace('a synthetic quantile fixture whose every stored length exceeds5','an exact DIFF sample32768: scaling the positive4096-grid quantiles by8 makes every length at least8, greater than5')
# Bookkeeping/reporting fragments are generated from the actual review outcome.
ledger=copy.deepcopy(initial)
claims={c['id']:c for doc in ledger for c in doc['claims']}
for op in accepted:
    claim=claims[op['claim_id']]
    assert claim['text']==op['old_text']
    claim['text']=op['new_text']
status='IMPCD iteration 4 found and corrected F1–F4. F5 remains OPEN: P4 still requires >=99% of1000 fixed seeds to freeze within25 rounds, but a permitted RTT configuration of the silent/slow fixture has an independently calculated completion probability of about50.4% under the current quorum and consecutive-success rules. The target, seeds and protocol are unchanged; actual fixture outcomes have not been executed. This unresolved acceptance conflict requires an author decision before the contract can be called finished.\n'
for claim in claims.values():
    s=claim['text']
    if s=='No unresolved contract question was identified in this regeneration.\n':s=status
    s=s.replace('Review records are in `.scratch/impcd/iteration-3/`.','Review records are in `.scratch/impcd/iteration-4/`.')
    if s.startswith('REVIEW ROUND 3:'):s='REVIEW ROUND 4: independent technical IMPCD review applied in place; F5 remains OPEN. '
    if s=='# Snowstorm executable-contract test proposal — review round 3\n':s=s.replace('round 3','round 4')
    claim['text']=s
for doc in ledger:
    rendered=''.join(c['text'] for c in doc['claims'])
    doc['sha256']=hashlib.sha256(rendered.encode()).hexdigest()
    (repo/doc['path']).write_text(rendered)
(here/'ledger-accepted.json').write_text(json.dumps(ledger,ensure_ascii=False,indent=2)+'\n')
(here/'consensus-operations.json').write_text(json.dumps(accepted,ensure_ascii=False,indent=2)+'\n')
# Generate review-only normative patch. Canonical parent stays untouched.
parent=repo/'docs/lotus-v2/snowstorm.md'
old=parent.read_text(); proposal=(repo/'.scratch/oneshot/SPEC-PROPOSED.md').read_text()
begin='<!-- snowstorm-core-normative:begin -->\n';end='<!-- snowstorm-core-normative:end -->\n'
assert old.count(begin)==old.count(end)==1
normative=proposal[proposal.index('# Reconciliation core: normative specification\n'):proposal.index('\n---\n\n## Remaining contract questions')]
start=old.index(begin)+len(begin);stop=old.index(end)
new=old[:start]+normative.rstrip()+'\n'+old[stop:]
patch=''.join(difflib.unified_diff(old.splitlines(keepends=True),new.splitlines(keepends=True),fromfile='a/docs/lotus-v2/snowstorm.md',tofile='b/docs/lotus-v2/snowstorm.md'))
(repo/'.scratch/oneshot/normative-PROPOSED.diff').write_text(patch)
print(json.dumps({'shared_substantive_operations':len(accepted),'substantive_disagreement':0.0,'raw_operation_disagreement':2/13,'sha256':{d['path']:d['sha256'] for d in ledger}},indent=2))
