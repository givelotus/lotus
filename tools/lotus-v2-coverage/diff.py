#!/usr/bin/env python3
"""Intersect LLVM source coverage segments with added executable lines in a Git diff."""
import argparse,json,pathlib,re,subprocess
p=argparse.ArgumentParser();p.add_argument('native',type=pathlib.Path);p.add_argument('coverage',type=pathlib.Path);p.add_argument('--baseline',default='f5cd728ab');a=p.parse_args()
d=json.loads(a.coverage.read_text()); counts={}
for group in d['data']:
 for f in group['files']:
  path=pathlib.Path(f['filename']); rel=str(path.relative_to(a.native.resolve())) if path.is_relative_to(a.native.resolve()) else str(path)
  lines={}
  # LLVM segments: line,column,count,hasCount,isRegionEntry,isGapRegion.
  seg=f['segments']
  for i,s in enumerate(seg):
   if not s[3] or s[5]:continue
   end=max(s[0], seg[i+1][0]-1) if i+1<len(seg) else s[0]
   for n in range(s[0],end+1):lines[n]=max(lines.get(n,0),s[2])
  counts[rel]=lines
patch=subprocess.check_output(['git','-C',str(a.native),'diff','--unified=0',a.baseline,'HEAD','--','src'],text=True)
changed={};path=None;line=0
for s in patch.splitlines():
 if s.startswith('+++ b/'):path=s[6:]
 elif s.startswith('@@'):
  line=int(re.search(r'\+(\d+)',s).group(1))
 elif s.startswith('+') and not s.startswith('+++'):
  changed.setdefault(path,[]).append(line);line+=1
 elif s.startswith(' '):line+=1
rows=[]
for path,added in sorted(changed.items()):
 mapped=counts.get(path,{});executable=[n for n in added if n in mapped]
 rows.append(dict(file=path,added_lines=len(added),mapped_added_lines=len(executable),covered_added_lines=sum(mapped[n]>0 for n in executable),uncovered_added_lines=[n for n in executable if not mapped[n]],unmapped_added_lines=[n for n in added if n not in mapped]))
print(json.dumps({'baseline':a.baseline,'method':'LLVM segment counts intersect Git added lines; unmapped includes non-executable lines and uninstrumented files, never claimed covered','files':rows},indent=2))
