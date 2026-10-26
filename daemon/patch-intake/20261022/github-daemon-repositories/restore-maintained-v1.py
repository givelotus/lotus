#!/usr/bin/env python3
"""Restore maintained V1 as linear commits without a checkout or source edits."""
import os,subprocess,pathlib,json,hashlib,tempfile,re
ROOT=pathlib.Path.cwd(); HERE=pathlib.Path(__file__).resolve().parent
STORE=ROOT/'daemon/.local-artifact-archive/github-source-transfer.git'
BASE='8c67fe1e85a602204a2ce65aa3b643469c2c3a1d'
manifest=json.loads((ROOT/'daemon/releases/lotusd/manifest.json').read_text())
expected=json.loads((HERE.parent/'release-source-tag-audit/v11.6.1-reconstructed.json').read_text())['rows']
expected={r['patch']:r['tree'] for r in expected}
names=[s.strip() for s in (ROOT/'daemon/patches/v1/series').read_text().splitlines() if s.strip() and not s.startswith('#')]
with tempfile.TemporaryDirectory(prefix='.v1-history-',dir=HERE) as td:
 td=pathlib.Path(td);env=dict(os.environ,GIT_INDEX_FILE=str(td/'index'))
 def git(*args,input=None,e=None):return subprocess.check_output(['git','--git-dir='+str(STORE),*args],input=input,env=e or env)
 git('read-tree',BASE);parent=BASE;rows=[]
 for i,name in enumerate(names,1):
  local_data=(ROOT/'daemon/patches/v1'/name).read_bytes()
  data=subprocess.check_output(['git','show','v11.6.1:daemon/patches/v1/'+name]) if name=='999-release-metadata.patch' else local_data
  info=git('mailinfo','-b',str(td/'message'),str(td/'diff'),input=data).decode()
  fields=dict(s.split(': ',1) for s in info.splitlines() if ': ' in s)
  git('apply','--cached','--whitespace=nowarn','-',input=(td/'diff').read_bytes())
  tree=git('write-tree').decode().strip()
  assert tree==expected[name],(name,tree,expected[name])
  msg=(fields['Subject']+'\n\n').encode()+(td/'message').read_bytes()
  author={'GIT_AUTHOR_NAME':fields['Author'],'GIT_AUTHOR_EMAIL':fields['Email'],'GIT_AUTHOR_DATE':fields['Date'],'GIT_COMMITTER_NAME':'Lotus Source History Recovery','GIT_COMMITTER_EMAIL':'build@givelotus.org','GIT_COMMITTER_DATE':fields['Date']}
  commit=git('commit-tree',tree,'-p',parent,input=msg,e=dict(env,**author)).decode().strip()
  rows.append({'number':i,'patch':name,'sha256':hashlib.sha256(data).hexdigest(),'mailbox_original_from':data.splitlines()[0].decode(),'restored_commit':commit,'tree':tree,'parent':parent});parent=commit
 assert tree=='2f67d96795f6c3e6236fbb189838bc28e420a97e',tree
 git('update-ref','refs/publish/lotusd/lotusv1',parent)
 result={'status':'PASS_EXACT_RELEASE_TREE_WITH_LINEAR_REBASED_HISTORY','base':BASE,'head':parent,'tree':tree,'patch_count':len(rows),'reference':'refs/publish/lotusd/lotusv1','source':'All 153 current implementation mailboxes and intermediate trees match published V1 release replay; append exact published v11.6.1 metadata. Current generated 999 metadata differs from stale local component manifest and is preserved tracked but excluded from this verified release branch.','identity_note':'Restored linear commit identities preserve mailbox author/date/message; explicit recovery committer. Historical published version tags retain original release identities.','validation':'Source-tree and per-patch preservation only; no new builds or runtime tests performed.','rows':rows}
 (HERE/'maintained-lotusv1-history.json').write_text(json.dumps(result,indent=2)+'\n')
 print('PASS maintained lotusv1',parent,tree,len(rows),flush=True)
