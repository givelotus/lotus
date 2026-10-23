#!/usr/bin/env python3
"""Measure preserved Git commit prefixes; never replay mailboxes or modify submodules."""
import argparse, datetime, fcntl, hashlib, json, os, platform, re, shutil
import signal, statistics, subprocess, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT/'daemon/worktrees/grok-progression-source'
BUILD = ROOT/'daemon/.local-artifact-archive/grok-progression-build'
TOOLS = ROOT/'daemon/patch-audit/consolidation/20261022/benchmark-tools'
FLAGS = ['-DCMAKE_BUILD_TYPE=Release','-DBUILD_WALLET=OFF','-DBUILD_QT=OFF',
         '-DBUILD_ZMQ=OFF','-DBUILD_CLI=ON','-DBUILD_TX=OFF','-DBUILD_CHRONIK=OFF',
         '-DBUILD_SEEDER=OFF','-DENABLE_UPNP=OFF','-DENABLE_NATPMP=OFF',
         '-DUSE_JEMALLOC=OFF','-DENABLE_HTTP2=OFF','-DENABLE_WEBTRANSPORT=OFF']
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(value,indent=2)+'\n');tmp.replace(path)
def git(*args):return subprocess.check_output(['git','-C',str(SOURCE),*args],text=True).strip()
def checkout(commit):
    if git('status','--porcelain'):raise RuntimeError('Benchmark checkout has source changes; preserve them before proceeding')
    subprocess.run(['git','-C',str(SOURCE),'checkout','--no-overwrite-ignore','--detach',commit],check=True,capture_output=True)
def run(argv,log,timeout=1800,cwd=None):
    began=time.monotonic()
    with log.open('w') as f:subprocess.run([str(x) for x in argv],stdout=f,stderr=subprocess.STDOUT,check=True,timeout=timeout,cwd=cwd)
    return time.monotonic()-began
def host():
    out={'utc':now(),'load':os.getloadavg()}
    if sys.platform=='darwin':
        text=subprocess.check_output(['memory_pressure','-Q'],text=True)
        percent=int(re.search(r'free percentage: (\d+)%',text)[1])
        ram=int(subprocess.check_output(['sysctl','-n','hw.memsize'],text=True))
        out['available_indicator_bytes']=ram*percent//100
        out['pressure']=int(subprocess.check_output(['sysctl','-n','kern.memorystatus_vm_pressure_level'],text=True))
        swap=subprocess.check_output(['sysctl','-n','vm.swapusage'],text=True)
        out['swap_bytes']=float(re.search(r'used = ([\d.]+)M',swap)[1])*1048576
    return out
def guarded(argv,log,env):
    before=host();samples=[];start=time.monotonic()
    if before.get('available_indicator_bytes',2**63)<6*1024**3:raise RuntimeError('Host free-memory indicator below 6 GiB before workload')
    with log.open('w') as f:
        p=subprocess.Popen([str(x) for x in argv],stdout=f,stderr=subprocess.STDOUT,env=env,start_new_session=True)
        try:
            while p.poll() is None:
                lines=subprocess.check_output(['ps','-axo','pid=,pgid=,rss='],text=True).splitlines()
                rss=sum(int(row.split()[2])*1024 for row in lines if len(row.split())==3 and int(row.split()[1])==p.pid)
                memory=host();samples.append({'elapsed':time.monotonic()-start,'owned_group_rss':rss,**memory})
                if (rss>12*1024**3 or memory.get('available_indicator_bytes',2**63)<6*1024**3
                    or memory.get('pressure',0)>=4 or memory.get('swap_bytes',0)-before.get('swap_bytes',0)>4*1024**3
                    or time.monotonic()-start>1800):raise RuntimeError('Owned workload exceeded recorded memory/time envelope')
                time.sleep(1)
            if p.returncode:raise RuntimeError(f'Workload exited {p.returncode}; see {log}')
        finally:
            if p.poll() is None:
                os.killpg(p.pid,signal.SIGTERM)
                try:p.wait(timeout=15)
                except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
    return {'before':before,'after':host(),'samples':samples,'owned_group':p.pid,'seconds_including_untimed_setup':time.monotonic()-start}
def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--points',default='376,377');ap.add_argument('--rounds',type=int,default=3)
    ap.add_argument('--cases',default='single_tx_steady,json_rpc_batch50_steady')
    ap.add_argument('--data',type=Path,default=ROOT/'benchmark-results/20261023/commit-regressions')
    ap.add_argument('--jobs',type=int,default=10);ap.add_argument('--build-only',action='store_true');ap.add_argument('--skip-build',action='store_true')
    ap.add_argument('--fixture-smoke',action='store_true')
    ap.add_argument('--plan',type=Path,default=ROOT/'daemon/stack-review.json')
    ap.add_argument('--variant',default='reference')
    ap.add_argument('--override-ref',action='append',default=[],metavar='POINT=REF')
    ap.add_argument('--diagnostic-net',action='store_true',help='Enable network logs; results are diagnostics, not progression timing samples')
    ap.add_argument('--fixed-transactions',type=int,help='Fixed-count latency diagnostic, not a sustained TPS claim');args=ap.parse_args()
    assert 1<=args.jobs<=10 and args.rounds>=1
    if not re.fullmatch(r'[a-zA-Z0-9_-]+',args.variant):raise RuntimeError('Invalid variant label')
    if args.plan.resolve()!=(ROOT/'daemon/stack-review.json').resolve() and args.variant=='reference':raise RuntimeError('Candidate history requires a separate --variant cache')
    points=[int(x) for x in args.points.split(',')];cases=args.cases.split(',')
    if args.fixed_transactions and (not 100000<=args.fixed_transactions<=500000 or cases!=['json_rpc_batch50_steady']):raise RuntimeError('Fixed diagnostic requires array50 and100k..500k transactions')
    if any(c not in ['single_tx_steady','json_rpc_batch50_steady','single_tx_loaded_steady'] for c in cases):raise RuntimeError('Unsupported common workload')
    plan=json.loads(args.plan.read_text())['stages']
    ordered=[{'commit':plan['ecash']['input_commit'],'subject':'Unmodified ABC baseline'}]+plan['ecash']['commits']+plan['v2']['commits']
    if args.override_ref and args.variant=='reference':raise RuntimeError('Candidate refs require a separate --variant cache')
    for override in args.override_ref:
        position,ref=override.split('=',1);position=int(position)
        original=ordered[position]
        ordered[position]={**original,'reference_commit':original['commit'],'commit':git('rev-parse',ref+'^{commit}'),'subject':'Candidate variant of: '+original['subject']}
    if any(n<0 or n>=len(ordered) for n in points):raise RuntimeError('Invalid ordered Git prefix')
    data=args.data.resolve();data.mkdir(parents=True,exist_ok=True)
    if not args.build_only and any(data.glob('round-*')):raise RuntimeError('Existing attempts are preserved; select a fresh --data directory')
    archive=ROOT/'daemon/.local-artifact-archive/commit-regressions'
    if args.variant!='reference':archive=archive/args.variant
    archive.mkdir(parents=True,exist_ok=True)
    lock=(SOURCE/'.git/progression.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    shared_lock=(ROOT/'daemon/.local-artifact-archive/benchmark-host.lock').open('a');fcntl.flock(shared_lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    fingerprint={'parent_commit':subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(),'flags':FLAGS,'compiler':subprocess.check_output(['c++','--version'],text=True),'platform':platform.platform(),'runner_sha256':sha(__file__),'startup_adapter_sha256':sha(Path(__file__).with_name('steady_loopback.py')),
                 'history_plan':str(args.plan.resolve()),'history_plan_sha256':sha(args.plan),'variant':args.variant,
                 'fixed_transactions':args.fixed_transactions,'diagnostic_net':args.diagnostic_net,
                 'frozen_tools':{str(p.relative_to(TOOLS)):sha(p) for p in TOOLS.rglob('*.py')},'points':{str(n):ordered[n] for n in points},
                 'semantics':'RPC admission and unloaded reads; not confirmed blocks, Avalanche finality or all-peer convergence',
                 'policy':'At least 5 seconds per measured throughput window; 3 rotated A/B rounds by default. Flag >=5% median losses for paired confirmation and profiling; never assume monotonic prefix performance.'}
    write(data/'GIT-AUDIT-INPUTS.json',fingerprint)
    binaries={}
    for n in points:
        commit=ordered[n]['commit'];checkout(commit);tree=git('rev-parse','HEAD^{tree}')
        dest=archive/f'point-{n:03}';dest.mkdir(exist_ok=True);receipt=dest/'BUILD.json'
        if receipt.exists() and not args.skip_build:raise RuntimeError(f'Frozen binary cache already exists: {dest}; use --skip-build or a fresh --variant')
        if not args.skip_build:
            print('BUILD',n,commit,flush=True)
            configure=run(['cmake','-GNinja','-S',SOURCE,'-B',BUILD,*FLAGS],data/f'point-{n:03}-configure.log')
            target='lotusd' if n>len(plan['ecash']['commits']) else 'bitcoind'
            elapsed=run(['ninja','-C',BUILD,'-j',args.jobs,'-k','0',target,'test_bitcoin'],data/f'point-{n:03}-build.log')
            test=BUILD/'src/test/test_bitcoin';listing=subprocess.run([str(test),'--list_content'],capture_output=True,text=True,check=True);suites=['mempool_tests','rpc_tests','miner_tests']
            for optional in ['mempool_admission_tests','txrelay_tests','mempool_overlay_tests','snapshot_rcu_tests','v2_protocol_handler_tests','validationinterface_tests']:
                if re.search(r'^'+optional+r'\*?$',listing.stdout+listing.stderr,re.M):suites.append(optional)
            unit_dir=archive/f'point-{n:03}-unit-work';unit_dir.mkdir(exist_ok=True)
            run([test,'--run_test='+','.join(suites),'--log_level=test_suite'],data/f'point-{n:03}-units.log',cwd=unit_dir)
            binary=dest/target;shutil.copy2(BUILD/'src'/target,binary);shutil.copy2(BUILD/'CMakeCache.txt',dest/'CMakeCache.txt')
            write(receipt,{'point':n,'commit':commit,'tree':tree,'binary':str(binary),'binary_sha256':sha(binary),'cache_sha256':sha(dest/'CMakeCache.txt'),'flags':FLAGS,'suites':suites,'build_seconds':elapsed,'configure_seconds':configure})
        r=json.loads(receipt.read_text());assert r['commit']==commit and r['tree']==tree and r['flags']==FLAGS and sha(r['binary'])==r['binary_sha256'];binaries[n]=r
    if args.build_only:return
    temp=archive/'runtime';temp.mkdir(exist_ok=True);env=dict(os.environ,TMPDIR=str(temp));results=[]
    for round_number in range(args.rounds):
        order=points if round_number%2==0 else list(reversed(points))
        for n in order:
            checkout(ordered[n]['commit'])
            for case in cases:
                directory=data/f'round-{round_number+1}'/f'point-{n:03}'/case;directory.mkdir(parents=True,exist_ok=True)
                output=directory/'result.json'
                argv=[sys.executable,Path(__file__).with_name('steady_loopback.py'),'--series','v2' if n>len(plan['ecash']['commits']) else 'l1',
                      '--daemon',binaries[n]['binary'],'--source',SOURCE,'--output',output,'--steady','--case',case,
                      '--max-fixture-transactions','800000','--fixture-fee-sats','10000','--hierarchical-funding','--maxmempool-mb','4096','--port-base','39110']
                if args.fixture_smoke:argv+=['--fixture-smoke']
                if args.diagnostic_net:argv+=['--audit-debug-net']
                if args.fixed_transactions:argv+=['--exact-fixture-transactions',str(args.fixed_transactions),'--diagnostic-fixed-work','--progress-chunk-transactions','10000']
                write(directory/'INPUTS.json',{'point':n,'round':round_number+1,'source':binaries[n],'argv':[str(x) for x in argv],'host_before':host(),'fixture_smoke':args.fixture_smoke})
                print('RUN',n,'round',round_number+1,case,flush=True)
                resources=guarded(argv,directory/'stdout.log',env);write(directory/'RESOURCES.json',resources)
                payload=json.loads(output.read_text());metrics=payload.get('metrics',payload)
                value=metrics[case] if not args.fixture_smoke else metrics
                if not args.fixture_smoke:assert value['seconds']>=5 and value['tx_count']>0
                results.append({'point':n,'round':round_number+1,'case':case,'source_commit':binaries[n]['commit'],'diagnostic_net':args.diagnostic_net,'result':value,'unloaded_reads':metrics.get('read_unloaded_steady'),'evidence':str(output)})
                write(data/'RESULTS.json',{'status':'partial','runs':results})
                if not args.fixture_smoke:print('RESULT',n,case,value['tx_count'],value['seconds'],flush=True)
    write(data/'RESULTS.json',{'status':'fixture-smoke-pass' if args.fixture_smoke else 'complete','runs':results})
if __name__=='__main__':
    try:main()
    except Exception as error:
        print('STOP:',repr(error),file=sys.stderr);raise
