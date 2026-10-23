from pathlib import Path
import subprocess,json
P=Path(__file__).resolve().parent;S=P.parents[4]/'daemon/worktrees/merklix-slab-source';source=json.loads((P/'SELECTION.json').read_text())['source_owner']
def oldfile(ref,f):return subprocess.check_output(['git','-C',str(S),'show',ref+':'+f],text=True)
def resolve(f,fn):
 path=S/f;s=path.read_text();i=0
 while '<<<<<<< ours\n'in s:
  a=s.index('<<<<<<< ours\n');b=s.index('=======\n',a);c=s.index('>>>>>>> theirs',b);e=s.index('\n',c);o=s[a+len('<<<<<<< ours\n'):b];t=s[b+len('=======\n'):c];s=s[:a]+fn(i,o,t)+s[e+1:];i+=1
 path.write_text(s)
resolve('src/lotus_v2/CMakeLists.txt',lambda i,o,t:t.replace('target_sources(lotus_v2_header PRIVATE address.cpp)\n','').replace('target_link_libraries(lotus_v2_header PUBLIC lotus_v2_blake3)\n',''))
resolve('src/lotus_v2/mempool_overlay.h',lambda i,o,t:o+t)
def overlay(i,o,t):
 if i==0:return o.replace('    std::vector<std::pair<Hash, Hash>> tx_leaves;\n    tx_leaves.reserve(entries.size());\n\n','')
 if i==1:return t[:t.index('        entry.effective_cost =')]+o.replace('        tx_leaves.emplace_back(entry.tx_id, entry.tx_hash);\n','')
 if i==2:return '    positional_merkle_dirty_ = true;\n\n'+t
 if i==3:return o+t
 raise AssertionError(i)
resolve('src/lotus_v2/mempool_overlay.cpp',overlay)
# Preserve the shared legacy codec and sequential extraction path exactly;
# transplant only the original generic retained-body charge helper/calls.
f='src/primitives/block.cpp';s=oldfile('HEAD',f);s=s.replace('#include <consensus/amount.h>','#include <consensus/amount.h>\n#include <core_memusage.h>\n#include <limits>',1);native=oldfile(source,f);a=native.index('namespace {\n//! Retained-body charge');b=native.index('bool AddTransactionToOverlay',a);helper=native[a:b];s=s.replace('bool AddTransactionToOverlay',helper+'bool AddTransactionToOverlay',1);s=s.replace('                                  fee_sats, sigchecks, ptx);','                                  fee_sats, sigchecks, ptx,\n                                  OverlayPayloadBytes(ptx));',1);s=s.replace('        e.sigchecks = sigchecks;\n        e.tx_ref = ptx;','        e.sigchecks = sigchecks;\n        e.payload_bytes = OverlayPayloadBytes(ptx);\n        e.tx_ref = ptx;',1);(S/f).write_text(s)
# First complete generic suite is shared; retain the fullscope-dependent
# suite and its two legacy transaction helpers in the native companion.
f='src/test/tx_merklix_tests.cpp';s=oldfile(source,f);s=s[:s.index('BOOST_FIXTURE_TEST_SUITE(tx_merklix_mempool_tests')];s=s.replace('#include <net/full_mempool_reconciliation.h>\n','');a=s.index('CTransactionRef Member(');b=s.index('uint64_t Counter(',a);s=s[:a]+s[b:];(S/f).write_text(s.rstrip()+'\n')
f='src/test/CMakeLists.txt';s=(S/f).read_text();needle='\t\tv2_protocol_handler_tests.cpp\n';assert s.count(needle)==1;s=s.replace(needle,needle+'\t\ttx_merklix_tests.cpp\n',1);(S/f).write_text(s)
files=json.loads((P/'SELECTION.json').read_text())['selected_whole_file_deltas']+[f,'src/test/tx_merklix_tests.cpp'];subprocess.run(['git','-C',str(S),'add',*files],check=True)
assert not subprocess.check_output(['git','-C',str(S),'diff','--name-only','--diff-filter=U']).strip();print('SHARED_RESOLUTIONS_PRESERVE_LEGACY_RULES')
