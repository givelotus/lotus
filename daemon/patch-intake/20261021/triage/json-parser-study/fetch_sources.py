#!/usr/bin/env python3
"""Fetch exact official benchmark-only sources; never touches production dependencies."""
from concurrent.futures import ThreadPoolExecutor
import hashlib,json,pathlib,subprocess
ROOT=pathlib.Path(__file__).resolve().parent
SOURCES={
'simdjson.h':('simdjson/simdjson','a7228cb376bf54d475cd86e451bb7cac92adf7c1','singleheader/simdjson.h'),
'simdjson.cpp':('simdjson/simdjson','a7228cb376bf54d475cd86e451bb7cac92adf7c1','singleheader/simdjson.cpp'),
'yyjson.h':('ibireme/yyjson','556bf1c12b99608957271d319a546010e301da63','src/yyjson.h'),
'yyjson.c':('ibireme/yyjson','556bf1c12b99608957271d319a546010e301da63','src/yyjson.c'),
}
def fetch(item):
 name,(repo,commit,path)=item
 url=f'https://raw.githubusercontent.com/{repo}/{commit}/{path}'
 data=subprocess.check_output(['curl','--fail','--silent','--show-error','--location','--max-time','60',url])
 (ROOT/'cache'/name).write_bytes(data)
 return name,{'repository':'https://github.com/'+repo,'commit':commit,'path':path,'url':url,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
(ROOT/'cache').mkdir(exist_ok=True)
with ThreadPoolExecutor(max_workers=4) as pool:
 manifest=dict(pool.map(fetch,SOURCES.items()))
(ROOT/'sources.json').write_text(json.dumps(manifest,indent=2))
print(json.dumps(manifest,indent=2))
