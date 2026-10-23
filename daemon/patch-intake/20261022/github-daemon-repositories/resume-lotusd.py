#!/usr/bin/env python3
import subprocess,pathlib,json,datetime
HERE=pathlib.Path(__file__).resolve().parent
STORE=HERE.parents[3]/'.local-artifact-archive/github-source-transfer.git'
# Resolve relative to the canonical repository, not an external scratch checkout.
STORE=pathlib.Path.cwd()/'daemon/.local-artifact-archive/github-source-transfer.git'
def push(specs,log,extra=()):
    with (HERE/log).open('w') as f:
        p=subprocess.run(['git','--git-dir='+str(STORE),'-c','pack.threads=2','-c','core.sshCommand=ssh -o ServerAliveInterval=15 -o ServerAliveCountMax=4','push','--progress','--atomic',*extra,'git@github.com:givelotus/lotusd.git',*specs],stdout=f,stderr=subprocess.STDOUT)
    print(log,'exit',p.returncode,flush=True)
    if p.returncode:raise SystemExit(p.returncode)
push(['refs/publish/lotusd/main:refs/heads/main','refs/source-copy/lotusv1-releases/tags/v7.3.3:refs/tags/v7.3.3'],'lotusd-main-retry-push.log',['--force-with-lease=refs/tags/v7.3.3:0a5a5b2b8437635f5d2f14fc58a52493bb18655b'])
push((HERE/'missing-lotusd-tags.refspecs').read_text().splitlines(),'lotusd-historical-tags-retry-push.log')
subprocess.run(['python3',str(HERE/'finalize-lotusd.py')],check=True)
