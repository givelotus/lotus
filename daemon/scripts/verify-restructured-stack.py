#!/usr/bin/env python3
"""Replay each split mailbox in an isolated Git index and verify all trees."""
import argparse,hashlib,json,os,pathlib,subprocess,tempfile

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--root',required=True);args=p.parse_args();root=pathlib.Path(args.root);manifest_path=root/'daemon/patch-audit/split-manifest.json';m=json.loads(manifest_path.read_text());index=pathlib.Path(tempfile.mktemp(prefix='lotus-split-verify-'));env={**os.environ,'GIT_INDEX_FILE':str(index)}
 def git(*a):return subprocess.check_output(['git','-C',args.source,*a],env=env).decode().strip()
 result={'schema':1,'manifest_sha256':hashlib.sha256(manifest_path.read_bytes()).hexdigest(),'base':m['base'],'candidate_tip':m['candidate_tip'],'patches':[],'original_boundaries':[],'native_builds':'not_run'}
 originals={o['new_shas'][-1]:o for o in m['originals']};parent=m['base']
 try:
  git('read-tree',m['base'])
  for row in m['patches']:
   path=root/'daemon/patches'/row['series']/row['file'];data=path.read_bytes();assert row['parent']==parent
   git('apply','--cached','--check',str(path));git('apply','--cached',str(path));tree=git('write-tree');assert tree==row['tree'],(path,tree,row['tree']);assert git('rev-parse',row['sha']+'^{tree}')==tree
   result['patches'].append({'patch':row['series']+'/'+row['file'],'sha256':hashlib.sha256(data).hexdigest(),'tree':tree,'status':'ok'})
   if row['sha'] in originals:
    o=originals[row['sha']];assert tree==o['tree']==git('rev-parse',o['sha']+'^{tree}');result['original_boundaries'].append({'original_patch':o['series']+f"/{o['number']:03}",'tree':tree,'status':'ok'})
   parent=row['sha']
  assert len(result['original_boundaries'])==84
  assert git('write-tree')==git('rev-parse',m['original_tip']+'^{tree}')
  for series in ('ecash','v2'):
   entries=[l.strip() for l in (root/'daemon/patches'/series/'series').read_text().splitlines() if l.strip() and not l.startswith(('#','@'))];assert entries==[r['file'] for r in m['patches'] if r['series']==series]
  result['status']='ok';result['verified_patch_count']=len(result['patches']);result['verified_original_boundary_count']=84
  (root/'daemon/patch-audit/replay-verification.json').write_text(json.dumps(result,indent=2)+'\n');print(f"Verified {len(result['patches'])} exported mailboxes and all 84 original trees; both endpoint trees unchanged.")
 finally:index.unlink(missing_ok=True)
if __name__=='__main__':main()
