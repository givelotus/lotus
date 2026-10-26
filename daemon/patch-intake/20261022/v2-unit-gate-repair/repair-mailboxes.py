from pathlib import Path
import subprocess, os
root=Path.cwd(); repo=root/'daemon/worktrees/grok-progression-source'; out=root/'daemon/patch-intake/20261022/v2-unit-gate-repair'
def git(*a,env=None,data=None):
 return subprocess.check_output(['git','-C',str(repo),*a],env=env,input=data)
def amend(owner, glob, path, modify):
 patch=next(root.glob(glob)); raw=patch.read_bytes(); old=git('show',f'{owner}:{path}'); new=modify(old)
 assert new!=old
 idx=out/(owner[:10]+'.index'); env=dict(os.environ,GIT_INDEX_FILE=str(idx))
 git('read-tree',owner,env=env)
 blob=git('hash-object','-w','--stdin',data=new).decode().strip()
 git('update-index','--cacheinfo',f'100644,{blob},{path}',env=env)
 diff=git('diff','--cached','--binary','--full-index',owner+'^',env=env)
 pre=raw.split(b'diff --git ',1)[0]
 patch.write_bytes(pre+diff+b'-- \n2.50.1\n')
 checkidx=out/(owner[:10]+'.parent.index'); checkenv=dict(os.environ,GIT_INDEX_FILE=str(checkidx))
 git('read-tree',owner+'^',env=checkenv)
 git('apply','--cached','--check',str(patch),env=checkenv)
 git('apply','--cached',str(patch),env=checkenv)
 print(patch.name, git('write-tree',env=checkenv).decode().strip())
 idx.unlink();checkidx.unlink()
amend('6a43a2381660a14b3ba585d538fea2e9c87ac800','daemon/patches/v2/001*.patch','src/test/v2_protocol_handler_tests.cpp',lambda b:b.replace(b'''        peerman->GetV2ProtocolHandler()->SetHighBandwidthShortTxPeer(
            node.GetId(), high_bandwidth);''',b'''        DataStream capability{};
        capability << txrelay::SENDINVSHORT_VERSION
                   << (high_bandwidth
                           ? uint64_t{txrelay::TXRELAY_HIGH_BANDWIDTH}
                           : uint64_t{0});
        std::atomic<bool> interrupt{false};
        peerman->ProcessMessage(config, node, NetMsgType::SENDINVSHORT,
                                capability, 0us, interrupt);'''))
amend('a3dea125128df8353f16d3ab29a3b5908a9e3db9','daemon/patches/v2/003*.patch','src/test/data/script_tests.json',lambda b:b.replace(b'123450000000.00',b'12345000.000000'))
