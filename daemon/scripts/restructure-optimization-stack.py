#!/usr/bin/env python3
"""Reproduce a tree-preserving logical split of the original Lotus optimization stack.

This is history surgery, not source repair. Every original completed-commit tree
is checked. Intermediate split commits inherit pre-existing missing prerequisites;
see daemon/patch-audit/README.md before treating this candidate as buildable.
"""
import argparse, difflib, hashlib, json, os, pathlib, re, subprocess, tempfile
BASE='1fb7db17c176cdea8a2c60d887891589382ee4e3'
TIP='09f95c297a67de61836c495904ce9f20551bf415'

# Ordered parts are implementation boundaries, not arbitrary file-size chunks.
PARTS={
4:[('daemon-db','db: migrate the daemon database wrapper to MDBX'),('chronik-db','chronik: migrate index storage and merge operations to MDBX')],
14:[('snapshot','rpc: introduce immutable chain and mempool snapshots with publication hooks'),('read-rpc','rpc: serve blockchain and mempool reads from snapshots'),('mining-rpc','mining: serve compact templates and mined-header submission from snapshots'),('loopback','test: add the standalone loopback throughput stress harness')],
20:[('hash','crypto: supply SHA256 tagged-hash primitives'),('vendor','vendor: preserve libmdbx license and obsolete lockfile cleanup'),('signing','script: implement legacy Schnorr batch MSM and signature-cache integration'),('recon','net: implement GF64 reconciliation arithmetic'),('filter','mempool: implement the sharded UTXO spent filter'),('fees','policy: supply fee-hysteresis implementation and block accounting'),('batch','validation: implement all-or-nothing raw transaction batches and deferred notifications'),('relay','net: wire concrete Merklix peer handling and transaction relay'),('sync','sync: implement shard swarm and reverse-peel peer handlers'),('rcu','mempool: coalesce snapshot publication and expose cached transaction metadata'),('miner','mining: reuse eligible speculative overlays for templates and block script checks'),('http','rpc: add direct HTTP dispatch paths for frequently polled methods'),('txcheck','validation: fast-path single-input duplicate checks and disabled sequence locks'),('undo','db: coalesce undo writes and cache written block sizes'),('bench','bench: add database, Merkle, RPC and script microbenchmarks'),('rollback','maintenance: preserve historical interface and test removals from ecash020'),('build','build: register newly supplied validation, snapshot and peer-handler sources')],
29:[('policy','policy: adapt block capacity and fees to measured congestion'),('rpc','rpc: expose adaptive capacity and fee-estimation methods'),('wallet','wallet: use adaptive fee estimates for transaction creation')],
34:[('size','transaction: cache serialized transaction size'),('overlay','mempool: defer block-removal overlay walks and coalesce snapshot updates')],
35:[('arena','mempool: expose lazy arena digest interfaces'),('gf64','net: accelerate GF64 multiplication with PCLMUL and PMULL'),('relay','net: batch peer-known updates and mempool relay notifications')],
39:[('hash','transaction: precompute transaction identities and preserve cached metadata'),('inputs','validation: resolve batch inputs in one wave using PeekCoin'),('parents','mempool: link known parent iterators without repeated lookup')],
41:[('peel','sync: declare windowed reverse block peeling'),('prune','node: register finalized-block pruning option')],
60:[('header','v2: define 134-byte header serialization and boundary checks'),('money','v2: define monetary transitions and block resource costs'),('asert','v2: implement ASERT candidate primitives'),('context','v2: validate header admission and contextual commitments')],
61:[('wire','v2: define v7 transaction serialization and output corpus'),('signing','v2: implement signing identities and Schnorr signing tests')],
62:[('vm','v2: implement the capability VM and cost model with differential tests'),('ordinary','v2: validate ordinary transactions against VM and state rules')],
63:[('disk','v2: implement MDBX state, flat-file block and body storage'),('block','v2: implement block wire, transition and template assembly'),('candidate','v2: add candidate stores, chain index and selection'),('avalanche','v2: add proof, peer, quorum and poll runtime facades'),('pool','v2: implement transaction pool, history and share-pool coordinator'),('chronik','v2: provide Chronik synchronization and explorer adapters'),('recovery','v2: recover chain state and storage across reorganizations'),('development','v2: provide development genesis, chain, runtime and command interfaces'),('build','build(v2): register standalone storage and runtime libraries')],
64:[('wire','chronik(v2): define native transaction and output models'),('database','chronik(v2): isolate MDBX access and persist branch, asset and explorer indexes'),('query','chronik(v2): ingest native blocks and expose typed index queries'),('http','chronik(v2): expose native HTTP, Electrum and WebSocket views'),('runtime','chronik(v2): wire native server and FFI entry points')],
67:[('consensus','consensus(v2): connect native state, monetary and script rules'),('wallet','wallet(v2): replace Berkeley DB with SQLite and native transaction providers'),('fixtures','test(v2): migrate functional fixtures and harnesses to native transactions')],
72:[('snapshot','rpc(v2): publish native state roots and snapshot metadata'),('rpc','rpc(v2): adapt blockchain, mempool and mining endpoints'),('tests','test(v2): validate native RPC snapshots and kernel throughput')],
76:[('primitives','transaction(v2): integrate native transaction identities and serialization'),('overlay','mempool(v2): reconcile overlay algorithms and native transaction bookkeeping'),('state','v2: reconcile state decoding, VM, ASERT and fast-sync primitives'),('validation','validation(v2): reconcile native batch and block admission'),('avalanche','avalanche: remove obsolete duplicated batch and treasury paths'),('build','build(v2): remove obsolete dependencies and register native fixtures'),('fuzz','fuzz(v2): exercise sealed headers, transactions, VM and reconciliation')],
78:[('outputs','transaction(v2): cache outputs roots and avoid legacy sighash precomputation'),('vm','vm(v2): eliminate temporary allocation during witness and program scans')],
81:[('prefetch','validation(v2): resolve batch inputs and state checks in one wave'),('parents','mempool(v2): avoid repeated parent and overlay work'),('peel','sync(v2): implement reverse disk-window peeling and pruning configuration')],
}

def choose(n,p,old,new,body):
    """Assign a complete edit to a reviewed concern; positions are 1-based."""
    if n==4:return 'chronik-db' if p.startswith('chronik/') else 'daemon-db'
    if n==14:
        if p.startswith('test/functional/lotus'):return 'loopback'
        if p in ('src/rpc/mining.cpp','src/rpc/client.cpp'):return 'mining-rpc'
        if p.startswith('src/rpc/'):return 'read-rpc'
        return 'snapshot'
    if n==20:
        if p in ('src/lotus_v2/tagged_hash.cpp','src/lotus_v2/tagged_hash.h'):return 'hash'
        if p in ('Cargo.lock','src/lotus_v2/vendor/libmdbx/LICENSE'):return 'vendor'
        if '/signing.' in p or '/secp256k1/' in p or p=='src/script/sigcache.cpp':return 'signing'
        if p.endswith('set_reconciliation.cpp'):return 'recon'
        if p.endswith('utxo_fast_filter.cpp'):return 'filter'
        if p.endswith('fee_hysteresis.cpp') or p.startswith('chronik/'):return 'fees'
        if p.startswith('src/bench/'):return 'bench'
        if p.endswith('CMakeLists.txt'):return 'build'
        if p=='src/httprpc.cpp':return 'http'
        if p in ('src/consensus/tx_check.cpp','src/consensus/tx_verify.cpp'):return 'txcheck'
        if p=='src/node/blockstorage.cpp':return 'undo'
        if p.startswith('src/primitives/'):return 'rcu'
        if p.startswith('src/validationinterface') or p=='src/rpc/mempool.cpp':return 'batch'
        if p=='src/validation.cpp':
            if old<2200:return 'batch'
            if 2600<=old<2650 or 2670<=old<2800:return 'miner'
            if 2650<=old<2670:return 'txcheck'
            if 2880<=old<2900:return 'fees'
            if 3710<=old<3730:return 'sync'
            return 'rcu'
        if p=='src/validation.h':return 'batch' if old<500 else 'rollback'
        if p=='src/node/miner.cpp':return 'miner'
        if p=='src/node/snapshot.cpp':return 'rcu'
        if p=='src/kernel/disconnected_transactions.cpp':return 'rcu'
        if p in ('src/txmempool.cpp','src/txmempool.h','src/test/mempool_tests.cpp'):return 'rcu'
        if p=='src/net/v2_protocol_handler.cpp':
            if new>=1616 and new<2715:return 'sync'
            if old<330 or 800<old<1100 or 1250<old<1400:return 'rollback'
            return 'relay'
        if p=='src/net_processing.cpp':return 'relay'
        if p=='src/avalanche/processor.cpp':return 'sync' if 1230<=old<1820 else 'relay'
        if p=='src/avalanche/processor.h' and ('StateAnchor' in body or 'cs_stateAnchors' in body):return 'sync'
        # These delete APIs/tests that existed earlier and are restored later;
        # retaining them is required for exact historical trees, not an optimization.
        return 'rollback'
    if n==29:return 'wallet' if '/wallet/' in p else 'rpc' if '/rpc/' in p else 'policy'
    if n==34:return 'size' if '/primitives/' in p else 'overlay'
    if n==35:return 'arena' if 'mempool_overlay' in p else 'gf64' if 'set_reconciliation' in p else 'relay'
    if n==39:
        if '/primitives/' in p:return 'hash'
        return 'parents' if 'txmempool' in p or p=='src/net_processing.cpp' else 'inputs'
    if n==41:return 'prune' if p=='src/init.cpp' else 'peel'
    if n==60:
        if any(s in p for s in ('monetary','block_cost')):return 'money'
        if 'asert' in p:return 'asert'
        if any(s in p for s in ('header_context','header_admission')):return 'context'
        return 'header'
    if n==61:return 'signing' if 'signing' in p else 'wire'
    if n==62:return 'ordinary' if 'ordinary' in p else 'vm'
    if n==63:
        if p=='src/lotus_v2/CMakeLists.txt':return 'build'
        name=p.removeprefix('src/lotus_v2/').removeprefix('test_')
        if name.startswith(('disk_','existing_home','reorg_storage')):return 'disk'
        if name.startswith(('avalanche',)):return 'avalanche'
        if name.startswith(('transaction_','pool_')):return 'pool'
        if name.startswith(('chronik_',)):return 'chronik'
        if name.startswith(('candidate_','chain_index')):return 'candidate'
        if name.startswith(('reorg_',)):return 'recovery'
        if name.startswith(('development_','dev_genesis')):return 'development'
        return 'block'
    if n==64:
        if p.startswith('chronik/bitcoinsuite-core/'):return 'wire'
        if p.startswith('chronik/chronik-db/'):return 'database'
        if p.startswith('chronik/chronik-indexer/'):return 'query'
        if p.startswith('chronik/chronik-http/'):return 'http'
        return 'runtime'
    if n==67:
        if '/wallet/' in p or p.startswith('depends/') or p=='src/bitcoin-wallet.cpp' or p.startswith('test/functional/wallet') or p.endswith('tool_wallet.py'):return 'wallet'
        if p.startswith('test/functional/'):return 'fixtures'
        return 'consensus'
    if n==72:
        if p=='src/test/snapshot_rcu_tests.cpp':return 'snapshot'
        if '/test/' in p or p.startswith('test/'):return 'tests'
        if '/node/snapshot' in p or p=='src/validation.cpp':return 'snapshot'
        return 'rpc'
    if n==76:
        if '/fuzz/' in p:return 'fuzz'
        if '/avalanche/' in p or p in ('src/net_processing.cpp','src/protocol.h') or p.endswith('messages.py'):return 'avalanche'
        if '/primitives/' in p:return 'primitives'
        if p in ('src/validation.cpp','src/validation.h','src/rpc/mempool.cpp','src/consensus/activation.cpp','src/coins.cpp','src/blockencodings.cpp'):return 'validation'
        if 'mempool' in p:return 'overlay'
        if '/lotus_v2/' in p and not p.endswith('CMakeLists.txt') and '/vendor/' not in p:return 'state'
        return 'build'
    if n==78:return 'vm' if p.endswith('/vm.cpp') else 'outputs'
    if n==81:
        if p=='src/init.cpp' or 'fast_sync' in p:return 'peel'
        if 'txmempool' in p or 'mempool_overlay' in p or p=='src/net_processing.cpp':return 'parents'
        return 'prefetch'
    return 'whole'

RENAMED={
8:'test: preserve an assembler-provided Merkle root in prepared blocks',
25:'mempool: declare parallel arena batch insertion',
27:'validation: declare the optional batch Schnorr collector parameter',
28:'policy: declare the congestion fee-hysteresis controller API',
36:'snapshot: clone chain scalars and track mempool reset generations',
37:'snapshot: restore lazy vectors and pending overlay declarations',
40:'overlay: expose UTXO SMT tracking and state-root commitment switches',
79:'disk_state: defer digests and cache nodes within write transactions',
}

RETAIN={8:'The payload only preserves an existing Merkle root in a test helper; it does not implement the advertised assembler. Correct the extracted subject and retain this small fixture change whole.',25:'Only the InsertBatchParallel declaration is added; it is an API prerequisite, not measured implementation of a parallel algorithm.',27:'Only an optional BatchSigCollector parameter is declared. Keep this interface prerequisite whole and correct its subject.',28:'This patch adds the fee-controller header only; the implementation appeared in original /020. Keep its declarations together and correct its subject.',36:'The payload updates snapshot cloning and reset generations, not the advertised wire capabilities or undo horizon. Retain the coherent snapshot change under an accurate subject.',37:'The payload restores lazy-vector/root and pending-overlay declarations already expected by existing code. Retain this interface prerequisite under an accurate subject.',40:'The payload adds state-root commitment/SMT tracking accessors only; it does not introduce the advertised open-addressed table. Correct the subject.',3:'Vendored libmdbx is one upstream import; splitting vendor implementation internals obscures provenance.',5:'Persistent overlay arenas, commitment helpers and their tests form one shared representation API. Missing tagged-hash prerequisites are separately recorded, not silently repaired.',10:'Reconciliation message handlers, scoped state and adversarial tests implement one protocol; header omissions are historical build defects.',12:'Batch vote identity, processor polling, policy and wire tests form one consensus-coordination feature. Later interface deletions and controller re-additions are exposed separately.',13:'Coroutine ownership, HTTP scheduling and long-poll migration share one lifetime contract.',16:'Snapshot root/shard format, storage hooks and swarm integration share one synchronization protocol.',17:'Undo wire format and reverse block peeling implement the same reconstruction contract.',18:'Worker scheduling and sharded signature-cache lifetime are coupled for the new parallel script path.',23:'The controller, epoch policy and associated tests form one feature; duplicates already present in earlier history are not corrected by splitting.',43:'Slab allocation, mempool aliases and ownership tests form one allocator conversion.',53:'Genesis activation policy changes are one coordinated consensus boundary.',54:'DAA removal and target spacing belong to the same difficulty-policy transition.',65:'Header/block-index encoding and header-dependent fixtures must agree at the wire migration.',66:'Native transaction wire migration requires all serialization callers and fixtures to move together.',68:'Chronik FFI representations and bridge callers must agree across the Rust/C++ boundary.',69:'Native state-root and monetary template assembly share one block-construction invariant.',70:'Native peer message/header identity conversion is one wire compatibility change.',71:'Native shard commitments and reverse peeling share the V2 state/header contract.',74:'Treasury contender voting, distribution and default slate implement one reward policy.',75:'Quorum-count and circulating-supply gates jointly define Avalanche activation.',79:'Lazy node digests and transaction-local node cache cooperate in one persistent-state mutation path. Despite its subject, this patch only changes disk_state.cpp; it contains no GBT endpoint changes.',80:'Stack identity construction and Mode-0 witness identity share the transaction hashing fast path; keep declaration and definition changes together.',82:'Expiry scheduling, deterministic cleaning crew validation and tests form one consensus feature.',83:'Coordinator API, P2P share relay and daemon registration implement one share-pool feature.',84:'Packed four-level binary SMT groups in one MDBX record require coordinated parser/update/digest handling; no independent unrelated behavior found.'}

def git(repo,*args,input=None,env=None):
    return subprocess.check_output(['git','-C',str(repo),*args],input=input,env=env,stderr=subprocess.DEVNULL)
def text(repo,*args):return git(repo,*args).decode().strip()
def blob(repo,c,p):
    try:return git(repo,'show',f'{c}:{p}')
    except subprocess.CalledProcessError:return b''
def mode(repo,c,p):
    s=text(repo,'ls-tree',c,'--',p);return s.split()[0] if s else None

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--source',required=True);ap.add_argument('--output-root',required=True);ap.add_argument('--source-ref',default='refs/heads/review/split-lotus-source-20261018');args=ap.parse_args()
    repo=pathlib.Path(args.source);out=pathlib.Path(args.output_root);audit=out/'daemon/patch-audit';audit.mkdir(parents=True,exist_ok=True)
    commits=text(repo,'rev-list','--reverse',BASE+'..'+TIP).splitlines();assert len(commits)==84
    if not args.source_ref.startswith('refs/heads/review/'):
        raise SystemExit('Use a dedicated refs/heads/review/ source branch.')
    for series in ('ecash','v2'):
        for mailbox in (out/'daemon/patches'/series).glob('*.patch'):
            mailbox.unlink()
    originals=[];mapping=[];index=pathlib.Path(tempfile.mktemp(prefix='lotus-split-index-'));env={**os.environ,'GIT_INDEX_FILE':str(index)};parent=BASE;counts={'ecash':0,'v2':0}
    git(repo,'read-tree',BASE,env=env)
    try:
        for n,c in enumerate(commits,1):
            series='ecash' if n<=52 else 'v2';oldid=n if n<=52 else n-52;prior=c+'^';subject=text(repo,'show','-s','--format=%s',c);parts=PARTS.get(n,[('whole',RENAMED.get(n,subject))])
            paths=text(repo,'diff','--name-only','--no-renames',prior,c).splitlines();file_edits={};assignment=[]
            for p in paths:
                a=blob(repo,prior,p);b=blob(repo,c,p);al=a.splitlines(keepends=True);bl=b.splitlines(keepends=True)
                # Whole-file additions retain intact implementation classes. For
                # changed files split edits within the same file by concern.
                ops=[]
                for tag,i,j,k,l in difflib.SequenceMatcher(None,al,bl,autojunk=False).get_opcodes():
                    if tag=='equal':continue
                    # ecash020 appends a complete SnapSync implementation after
                    # HandleShortTx in the same original diff hunk. Split that
                    # insertion at the method boundary, not the whole file.
                    cuts=[k,l]
                    if n==20 and p=='src/net/v2_protocol_handler.cpp' and i==j and k<1615<l:cuts=[k,1615,l]
                    for s,t in zip(cuts,cuts[1:]):
                        part=choose(n,p,i+1,s+1,b''.join(bl[s:t]).decode(errors='replace')) if n in PARTS else 'whole'
                        assert part in dict(parts),(n,p,part)
                        ops.append((i,j,s,t,part));assignment.append({'path':p,'old_start':i+1,'old_count':j-i,'new_start':s+1,'new_count':t-s,'part':part})
                file_edits[p]=(al,bl,ops,mode(repo,c,p),mode(repo,prior,p))
            included=set();newrows=[]
            for part,title in parts:
                included.add(part);touched=[]
                for p,(al,bl,ops,newmode,oldmode) in file_edits.items():
                    if not any(x[4]==part for x in ops):continue
                    result=[];cursor=0
                    for i,j,k,l,key in ops:
                        result.extend(al[cursor:i]);result.extend(bl[k:l] if key in included else al[i:j]);cursor=j
                    result.extend(al[cursor:]);data=b''.join(result)
                    if newmode is None and all(x[4] in included for x in ops):git(repo,'update-index','--force-remove','--',p,env=env)
                    else:
                        oid=git(repo,'hash-object','-w','--stdin',input=data).decode().strip();git(repo,'update-index','--add','--cacheinfo',newmode or oldmode,oid,p,env=env)
                    touched.append(p)
                if not touched:continue
                tree=git(repo,'write-tree',env=env).decode().strip()
                if tree==text(repo,'rev-parse',parent+'^{tree}'):continue
                meta=json.loads(git(repo,'show','-s','--format={"name":"%an","email":"%ae","date":"%aI"}',c))
                message=title+'\n\n'+('Extract this concern so its mechanism can be reviewed and measured independently.\nNo source semantics are added or removed by this history operation.\n\nOriginal patch rationale (describes the unsplit source, not every extracted part):\n'+text(repo,'show','-s','--format=%b',c)+'\n' if len(parts)>1 or n in RENAMED else text(repo,'show','-s','--format=%b',c)+'\n')+'\nOriginal-Commit: '+c+'\nOriginal-Patch: '+f'{series}/{oldid:03}'+'\nSplit-Concern: '+part+'\n\nHistorical compilation prerequisites are tracked separately in daemon/patch-audit;\nthis provenance-preserving split does not imply standalone build validation.\n'
                ce={**os.environ,'GIT_AUTHOR_NAME':meta['name'],'GIT_AUTHOR_EMAIL':meta['email'],'GIT_AUTHOR_DATE':meta['date'],'GIT_COMMITTER_NAME':meta['name'],'GIT_COMMITTER_EMAIL':meta['email'],'GIT_COMMITTER_DATE':meta['date']}
                sha=git(repo,'commit-tree',tree,'-p',parent,input=message.encode(),env=ce).decode().strip();counts[series]+=1
                slug=re.sub('[^a-z0-9]+','-',title.lower()).strip('-')[:100];filename=f'{counts[series]:03}-{slug}.patch';target=out/'daemon/patches'/series/filename;target.parent.mkdir(exist_ok=True)
                target.write_bytes(git(repo,'format-patch','-1','--stdout','--full-index','--binary',sha));row={'series':series,'number':counts[series],'file':filename,'sha':sha,'tree':tree,'parent':parent,'original_sha':c,'original_patch':f'{series}/{oldid:03}','concern':part,'subject':title,'files':touched,'build_status':'not_run'};mapping.append(row);newrows.append(sha);parent=sha
            expected=text(repo,'rev-parse',c+'^{tree}');actual=git(repo,'write-tree',env=env).decode().strip();assert actual==expected,(n,actual,expected)
            originals.append({'step':n,'series':series,'number':oldid,'sha':c,'subject':subject,'tree':expected,'split':len(newrows)>1,'new_shas':newrows,'rationale':'Independent concerns split with edits assigned within shared files.' if len(newrows)>1 else RETAIN.get(n,'One cohesive implementation/API change; no independent behavior identified requiring a separate patch.'),'edits':assignment})
            print(f'{series}/{oldid:03}: {len(newrows)} parts; original tree verified',flush=True)
        git(repo,'update-ref',args.source_ref,parent)
        for series in counts:
            rows=[r for r in mapping if r['series']==series];prefix='# Tree-preserving logical split; see ../../patch-audit/README.md.\n'+('@include ../ecash/series\n' if series=='v2' else '')
            (out/'daemon/patches'/series/'series').write_text(prefix+'\n'.join(r['file'] for r in rows)+'\n')
        manifest={'schema':1,'base':BASE,'original_tip':TIP,'source_ref':args.source_ref,'candidate_tip':parent,'counts':counts,'original_boundary_trees_verified':len(originals),'endpoints':{'ecash':next(o for o in originals if o['step']==52)['tree'],'v2':originals[-1]['tree']},'patches':mapping,'originals':originals}
        (audit/'split-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    finally:index.unlink(missing_ok=True)
if __name__=='__main__':main()
