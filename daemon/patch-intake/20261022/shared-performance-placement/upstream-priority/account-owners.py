import pathlib,subprocess,json,hashlib,collections
P=pathlib.Path(__file__).resolve().parent;S=P.parents[4]/'daemon/worktrees/merklix-slab-source'
def git(*a):return subprocess.check_output(['git','-C',str(S),*a],text=True).strip()
d=json.loads((P/'CANDIDATE.json').read_text());old=json.loads((P/'OLD-ORDER.json').read_text());first=[x['commit']for x in json.loads((P/'ORDER-PLAN.json').read_text())['early_group']];want=first+[x for x in old if x not in first]
def find(subject):return next(c for c in old if git('show','-s','--format=%s',c)==subject)
checker=find('mempool: make topological consistency checking optional on every network');framework=find('test: test parameters can be class attributes');policy=find('policy: derive adaptive capacity from active-chain history');want.remove(checker);want.insert(want.index(old[2])+1,checker);want=[None]+want;new=git('rev-list','--reverse','base/abc..'+d['new_tip']).splitlines();assert len(want)==len(new)==530
feature='test/functional/feature_mempool_consistency.py';cm='src/CMakeLists.txt'
def byfile(c):
 result={}
 for f in git('diff','--name-only',c+'^',c).splitlines():
  diff=git('diff','--unified=0','--no-ext-diff',c+'^',c,'--',f);result[f]=[l for l in diff.splitlines()if l.startswith(('+','-'))and not l.startswith(('+++','---'))]
 return result
featureops=byfile(checker)[feature];buildops=byfile(policy)[cm];rows=[]
for i,(o,n)in enumerate(zip(want,new),1):
 a=byfile(o)if o else{cm:buildops};b=byfile(n);exceptions=[]
 if o==policy:assert a.pop(cm)==buildops;exceptions.append('CMake worktree metadata hunk -> new global1 build owner')
 if o==checker:assert a.pop(feature)==featureops;exceptions.append('functional class-attribute test -> framework prerequisite owner')
 if o==framework:a[feature]=featureops;exceptions.append('functional companion from checker retained byte-identically')
 assert set(a)==set(b),(i,o,n,list(a),list(b))
 for f in a:
  assert collections.Counter(a[f])==collections.Counter(b[f]),(i,o,n,f)
  if a[f]!=b[f]:exceptions.append(f+': identical signed-line multiset; Git hunk alignment differs around repeated context lines')
 rows.append({'global':i,'old_commit':o,'old_global':old.index(o)+1 if o else None,'new_commit':n,'tree':git('rev-parse',n+'^{tree}'),'subject':git('show','-s','--format=%s',n),'files':list(b),'operation_digests':{f:hashlib.sha256('\n'.join(sorted(v)).encode()).hexdigest()for f,v in b.items()},'exceptions':exceptions,'all_source_operations_accounted':True})
(P/'FINAL-OWNER-MAPPING.json').write_text(json.dumps(rows,indent=2)+'\n');print('ALL530_OWNER_OPERATIONS_ACCOUNTED')
x=(P.parent/'snapshot-reset-defer/verify-source.py').read_text().replace('shared-placement-snapshot-replay.index','upstream-priority-replay.index').replace('529','530').replace("tip='5dcb81d975a654f8c36fa6e36f3605fa217fd084'","tip="+repr(d['new_tip']));(P/'verify-source.py').write_text(x)
