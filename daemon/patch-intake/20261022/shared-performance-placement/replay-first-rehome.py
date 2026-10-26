import json,subprocess,datetime
from pathlib import Path
p=Path(__file__).resolve().parent;s=p.parents[3]/'worktrees/merklix-slab-source'
# Explicit assignedsource; no newworktree, noreset, stopfirstconflict.
s=Path('/Users/shammah/repos/lotus-v2-optimizations/daemon/worktrees/merklix-slab-source')
inv=json.loads((p/'native-owner-source-inventory.json').read_text());out=p/'FIRST-REHOME-REPLAY.json'
d=json.loads(out.read_text())if out.exists()else{'status':'RUNNING','source':str(s),'moved_native_owner':149,'new_shared_tip':'59cf9ad39a529449eba48dc9544bcac3c0538071','mapping':[]}
g=lambda *a:subprocess.check_output(['git','-C',str(s),*a],text=True).strip()
completed={x['old_commit']for x in d['mapping']}
for row in inv['owners']:
 if row['native_owner']==149 or row['commit']in completed:continue
 before=g('rev-parse','HEAD');c=row['commit']
 with(p/'first-rehome-replay.log').open('a')as log:
  z=subprocess.run(['git','-C',str(s),'cherry-pick',c],stdout=log,stderr=subprocess.STDOUT)
 if z.returncode:
  d.update(status='STOPPED_CONFLICT',failed_native_owner=row['native_owner'],failed_commit=c,head_before=before,utc=datetime.datetime.now(datetime.timezone.utc).isoformat());out.write_text(json.dumps(d,indent=2)+'\n');print('STOP',row['native_owner'],c,flush=True);raise SystemExit(z.returncode)
 d['mapping'].append({'native_owner':row['native_owner'],'old_commit':c,'new_commit':g('rev-parse','HEAD'),'new_tree':g('rev-parse','HEAD^{tree}')});out.write_text(json.dumps(d,indent=2)+'\n')
 print('REPLAY',row['native_owner'],flush=True)
d.update(status='ALL_COMMITS_REPLAYED_FINAL_TREE_CHECK_REQUIRED',head=g('rev-parse','HEAD'),tree=g('rev-parse','HEAD^{tree}'));out.write_text(json.dumps(d,indent=2)+'\n')
