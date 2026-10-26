import datetime,hashlib,json,pathlib,re,subprocess,os
P=pathlib.Path(__file__).resolve().parent;R=P.parents[3];S=R/'daemon/.local-artifact-archive/github-source-transfer.git'
x=json.loads((P/'v11.6.0-reconstructed.json').read_text());lines=(P/'v11.6.0-linux-commit-lines.txt').read_text().splitlines();assert len(lines)==len(x['rows'])==153
parent=x['base'];out=[]
env=dict(os.environ,GIT_INDEX_FILE=str(P/'.original-ci-private.index'),GIT_ALTERNATE_OBJECT_DIRECTORIES='/Users/shammah/repos/bitcoin-abc/.git/objects')
for row,line in zip(x['rows'],lines,strict=True):
 if len(out)>=104:
  subprocess.run(['git','--git-dir='+str(S),'read-tree',row['tree']],env=env,check=True)
  subprocess.run(['git','--git-dir='+str(S),'update-index','--index-info'],input=b'0 0000000000000000000000000000000000000000\tsrc/qt/res/icons/Archive.zip\n',env=env,check=True)
  row=dict(row,tree=subprocess.check_output(['git','--git-dir='+str(S),'write-tree'],env=env).decode().strip())
 m=re.match(r'(\S+) \[lotus-v1-work ([a-f0-9]+)\] Apply patch: (.*)',line);assert m and m[3]==row['patch']
 dt=datetime.datetime.fromisoformat(m[1].replace('Z','+00:00'));sec=int(dt.timestamp());matches=[]
 for stamp in range(sec-2,sec+2):
  body=f'tree {row["tree"]}\nparent {parent}\nauthor Lotus Builder <build@givelotus.org> {stamp} +0000\ncommitter Lotus Builder <build@givelotus.org> {stamp} +0000\n\nApply patch: {row["patch"]}\n'.encode()
  sha=hashlib.sha1(b'commit '+str(len(body)).encode()+b'\0'+body).hexdigest()
  if sha.startswith(m[2]):matches.append((sha,body,stamp))
 assert len(matches)==1,(row['patch'],m[2],sec,len(matches))
 sha,body,stamp=matches[0];written=subprocess.check_output(['git','--git-dir='+str(S),'hash-object','-t','commit','-w','--stdin'],input=body).decode().strip();assert written==sha
 out.append({'patch':row['patch'],'commit':sha,'tree':row['tree'],'logged_commit_prefix':m[2],'commit_unix_second':stamp,'log_timestamp':m[1]});parent=sha
assert parent.startswith('62fff661852a'),parent
subprocess.run(['git','--git-dir='+str(S),'update-ref','refs/audit/releases/v11.6.0-original-ci-source',parent],check=True)
result={'status':'PASS_ORIGINAL_CI_COMMIT_HISTORY_RECOVERED','source':parent,'tree':out[-1]['tree'],'base':x['base'],'workflow_run':38523489729,'logged_commits_verified':153,'published_binary_suffix':'62fff661852a','method':'Every exact reconstructed Git commit matches the original timestamped CI commit-prefix output (mostly9/10hex), final matches published12hex binaryversion; original metadata and parent chain reconstructed, not newly attributed source identity.','rows':out};(P/'v11.6.0-original-ci-source.json').write_text(json.dumps(result,indent=2)+'\n');(P/'.original-ci-private.index').unlink(missing_ok=True);print('RECOVERED',parent,result['tree'],flush=True)
