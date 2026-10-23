import subprocess,json,pathlib,time
P=pathlib.Path(__file__).resolve().parent;R=P.parents[3];S=R/'daemon/.local-artifact-archive/github-source-transfer.git';B='/Users/shammah/repos/bitcoin-abc/.git';roots=['refs/audit/releases/v11.6.1-exact-metadata','refs/audit/releases/v11.6.0-reconstructed-source','refs/audit/releases/v11.6.0-original-ci-source'];rows=[];t=time.monotonic()
for round in range(20):
 p=subprocess.run(['git','--git-dir='+str(S),'rev-list','--objects','--missing=print',*roots],capture_output=True,text=True);assert p.returncode==0,p.stderr
 missing=[l[1:] for l in p.stdout.splitlines() if l.startswith('?')];print('round',round,'missing',len(missing),flush=True)
 if not missing:break
 for sha in missing:
  typ=subprocess.check_output(['git','--git-dir='+B,'cat-file','-t',sha]).decode().strip();raw=subprocess.check_output(['git','--git-dir='+B,'cat-file',typ,sha]);got=subprocess.check_output(['git','--git-dir='+str(S),'hash-object','-t',typ,'-w','--stdin'],input=raw).decode().strip();assert sha==got;rows.append({'oid':sha,'type':typ,'bytes':len(raw),'source':B})
else:raise RuntimeError('closure rounds exhausted')
(P/'release-original-history-closure.json').write_text(json.dumps({'status':'PASS_NO_MISSING_OBJECTS','roots':roots,'objects_copied_exact':rows,'seconds':time.monotonic()-t},indent=2)+'\n');print('PASS',len(rows),flush=True)
