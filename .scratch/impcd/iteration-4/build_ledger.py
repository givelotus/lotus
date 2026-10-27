import json,re,hashlib
from pathlib import Path
root=Path(__file__).resolve().parent
repo=root.parents[2]
paths=['.scratch/oneshot/SPEC-PROPOSED.md','.scratch/oneshot/TESTS-PROPOSED.md']
ledger=[]
for tag,path in zip(['S','T'],paths):
    text=(repo/path).read_text(); chunks=[]; fenced=False
    for line in text.splitlines(keepends=True):
        if line.startswith('```'): fenced=not fenced
        if fenced or line.startswith(('```','|','#')) or not line.strip(): chunks.append(line); continue
        chunks.extend(re.split(r'(?<=[.!?]) (?=[A-Z])',line))
        # Preserve the spaces removed by sentence splitting.
        n=len(re.split(r'(?<=[.!?]) (?=[A-Z])',line))
        if n>1:
            start=len(chunks)-n
            for i in range(start,len(chunks)-1): chunks[i]+=' '
    ledger.append({'path':path,'sha256':hashlib.sha256(text.encode()).hexdigest(),'claims':[{'id':f'{tag}{i:04}','status':'open','text':s} for i,s in enumerate(chunks,1)]})
(root/'ledger-initial.json').write_text(json.dumps(ledger,ensure_ascii=False,indent=2)+'\n')
for doc in ledger: assert ''.join(x['text'] for x in doc['claims'])==(repo/doc['path']).read_text()
print([(d['path'],len(d['claims'])) for d in ledger])
