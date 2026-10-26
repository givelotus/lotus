#!/usr/bin/env python3
"""Populate requested private source repositories without working clones."""
import subprocess,pathlib,json,datetime,sys
ROOT=pathlib.Path.cwd();HERE=pathlib.Path(__file__).resolve().parent
STORE=ROOT/'daemon/.local-artifact-archive/github-source-transfer.git'
CONFIG=[('bitcoin-abc','Bitcoin-ABC/bitcoin-abc'),('doged','doged-io/doged'),('bitcoincashd','bitcoin-cash-node/bitcoin-cash-node'),('bitcoind','bitcoin/bitcoin')]
def git(*a):return subprocess.check_output(['git','--git-dir='+str(STORE),*a],text=True)
for name,source in CONFIG:
 if sys.argv[1:] and name not in sys.argv[1:]:continue
 ns='refs/source-copy/'+name+'/'
 source_url='https://gitlab.com/bitcoin-cash-node/bitcoin-cash-node.git' if name=='bitcoincashd' else 'https://github.com/'+source+'.git'
 print('FETCH',name,flush=True)
 with (HERE/(name+'-fetch.log')).open('w') as f:
  subprocess.run(['git','--git-dir='+str(STORE),'fetch','--no-tags',source_url,'+refs/heads/*:'+ns+'heads/*','+refs/tags/*:'+ns+'tags/*'],stdout=f,stderr=subprocess.STDOUT,check=True)
 refs={r.split()[0]:r.split()[1] for r in git('for-each-ref','--format=%(refname) %(objectname)',ns+'heads/',ns+'tags/').splitlines()}
 assert ns+'heads/master' in refs
 specs=[r+':refs/'+r.removeprefix(ns) for r in refs]
 print('PUSH',name,len(specs),'refs',flush=True)
 with (HERE/(name+'-push.log')).open('w') as f:
  subprocess.run(['git','--git-dir='+str(STORE),'-c','pack.threads=2','-c','core.sshCommand=ssh -o ServerAliveInterval=15 -o ServerAliveCountMax=4','push','--atomic','--progress','git@github.com:givelotus/'+name+'.git',*specs],stdout=f,stderr=subprocess.STDOUT,check=True)
 remote={r.split()[1]:r.split()[0] for r in subprocess.check_output(['git','ls-remote','git@github.com:givelotus/'+name+'.git'],text=True).splitlines() if not r.split()[1].endswith('^{}')}
 expected={'refs/'+r.removeprefix(ns):sha for r,sha in refs.items()}
 assert all(remote.get(r)==sha for r,sha in expected.items())
 meta=json.loads(subprocess.check_output(['gh','api','--method','PATCH','repos/givelotus/'+name,'-f','default_branch=master'],text=True));assert meta['private']
 result={'verified_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'repository':meta['html_url'],'upstream':source_url,'private':True,'default_branch':'master','ref_count':len(expected),'refs':expected,'submodules_added':False}
 (HERE/(name+'-verified.json')).write_text(json.dumps(result,indent=2)+'\n')
 print('VERIFIED',name,flush=True)
