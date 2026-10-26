import pathlib,json,subprocess,collections,hashlib,re
P=pathlib.Path(__file__).resolve().parent;S=P.parents[4]/'daemon/worktrees/merklix-slab-source';D=json.loads((P/'CANDIDATE.json').read_text());old=D['owner_order']
def git(*a):return subprocess.check_output(['git','-C',str(S),*a],text=True).strip()
new=git('rev-list','--reverse','base/abc..'+D['new_tip']).splitlines();assert len(old)==len(new)==530
oldrows=json.loads((P.parent/'upstream-priority/FINAL-OWNER-MAPPING.json').read_text());byold={x['new_commit']:x for x in oldrows};db=next(c for c in old if byold[c]['subject']=='db: migrate the daemon database wrapper to MDBX');logger=next(c for c in old if byold[c]['subject']=='logging: write log lines on a logger thread')
def ops(c):
 diff=git('diff','--binary','--unified=0','--no-ext-diff',c+'^',c,'--');out={};cur=None
 for line in diff.splitlines():
  if line.startswith('diff --git '):
   match=re.fullmatch(r'diff --git a/(.*) b/(.*)',line);assert match,line;cur=match[2];out[cur]=[]
  elif cur and line.startswith(('+','-'))and not line.startswith(('+++','---')):out[cur].append(line)
 return out
rows=[]
for i,(o,n)in enumerate(zip(old,new),1):
 a=ops(o);b=ops(n);exceptions=[]
 if o==db:a['src/validation.cpp'].remove('+        LogInstance().Flush();');exceptions.append('Exact test-pause Flush call -> async logger owner where API first exists')
 if o==logger:a.setdefault('src/validation.cpp',[]).append('+        LogInstance().Flush();');exceptions.append('Exact test-pause Flush call from MDBX owner; no behavior change at endpoint')
 assert set(a)==set(b),(i,o,n,set(a)^set(b))
 for f in a:
  ca=collections.Counter(a[f]);cb=collections.Counter(b[f])
  if ca!=cb:
   aa=ca.copy();bb=cb.copy();aa.pop('+',None);aa.pop('-',None);bb.pop('+',None);bb.pop('-',None);assert aa==bb,(i,o,n,f,ca-cb,cb-ca)
   exceptions.append(f+': blank-line ownership alignment recorded; final complete tree exactly equal')
  elif a[f]!=b[f]:exceptions.append(f+': identical signed operations; repeated-line Git hunk alignment differs')
 rows.append({'global':i,'old_global':byold[o]['global'],'old_commit':o,'new_commit':n,'subject':byold[o]['subject'],'files':list(b),'tree':git('rev-parse',n+'^{tree}'),'signed_operation_sha256':{f:hashlib.sha256('\n'.join(sorted(v)).encode()).hexdigest()for f,v in b.items()},'exceptions':exceptions,'all_nonwhitespace_operations_accounted':True})
 if i%100==0:print('ACCOUNTED',i,flush=True)
(P/'OWNER-MAPPING.json').write_text(json.dumps(rows,indent=2)+'\n');assert git('rev-parse',D['new_tip']+'^{tree}')==D['tree'];assert git('rev-parse',D['new_shared']+'^{tree}')==D['shared_tree'];print('ALL530_ACCOUNTED_EXACT_TREES',flush=True)
