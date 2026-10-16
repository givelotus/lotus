#!/usr/bin/env python3
"""Bounded real-process Avalanche acceptance on caller-pinned public test stake."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import time


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--daemon',type=Path,required=True)
    p.add_argument('--daemon-source',required=True)
    p.add_argument('--daemon-sha256',required=True)
    p.add_argument('--bootstrap',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--phase',choices=('seed','quorum'),default='quorum')
    p.add_argument('--seed',type=Path,help='reuse a stopped enabled seed produced by this harness')
    p.add_argument('--resume-seed',action='store_true',help='continue a cleanly stopped enabled seed after an import deadline')
    p.add_argument('--seed-daemon-sha256',help='explicit compatible old seed binary hash when upgrading only observational API')
    p.add_argument('--require-block-observation',action='store_true')
    p.add_argument('--timeout',type=float,default=30)
    p.add_argument('--deadline-seconds',type=float,default=1800)
    a=p.parse_args()
    spec=importlib.util.spec_from_file_location('local',Path(__file__).with_name('check-v2-local-nodes.py'))
    local=importlib.util.module_from_spec(spec);spec.loader.exec_module(local)
    require=local.require
    daemon=a.daemon.resolve();bootstrap=a.bootstrap.resolve();root=a.output.resolve()
    require(root.as_posix().startswith('/private/tmp/'),'isolated canonical /private/tmp output required')
    require(not a.resume_seed or a.seed,'resume requires an explicit stopped enabled seed')
    require(local.digest(daemon)==a.daemon_sha256,'immutable daemon hash differs')
    require(local.hex_string(a.daemon_source,20),'full source pin required')
    require(60<=a.deadline_seconds<=14400 and 1<=a.timeout<=60,'bounded deadlines required')
    root.mkdir(mode=0o700)
    (root/'harness.py').write_bytes(Path(__file__).read_bytes())
    manifest=root/'manifest.json';manifest.write_bytes((bootstrap/'manifest.json').read_bytes())
    original=json.loads((bootstrap/'evidence.json').read_text());report=json.loads((bootstrap/'candidate-report.json').read_text())
    require(original['passed'] and original['accepted_blocks']==2024,'actual accepted bootstrap evidence required')
    require([f['public_fixture_scalar'] for f in original['funding']]==list(range(1,10)),'exact public fixture scalars 1..9 required')
    require(report['quorum']==1000000000000 and report['stake_dust']==10000000000 and report['stake_confirmations']==2016,'upstream proof policy differs')
    evidence=dict(schema='lotus-v2/native-quorum-acceptance/1',passed=False,phase=a.phase,
        daemon_source=a.daemon_source,daemon_sha256=local.digest(daemon),harness_sha256=local.digest(Path(__file__)),
        manifest_sha256=local.digest(manifest),bootstrap_ledger_sha256=local.digest(bootstrap/'accepted-blocks.jsonl'),
        public_fixture_keys='Public scalars 1..9 only; no production funds',checks=[],processes=[],cleanup=[])
    end=time.monotonic()+a.deadline_seconds;nodes=[]
    def save():
        temporary=root/'evidence.pending.json'
        temporary.write_text(json.dumps(evidence,indent=2)+'\n');temporary.replace(root/'evidence.json')
    def check(name,**fields):evidence['checks'].append(dict(check=name,**fields));save()
    def start(label,home,connect=(),port=0,credentials=None):
        config=root/(label+'.network.json')
        config.write_text(json.dumps(dict(schema=1,magic='76327139',listen=dict(address='127.0.0.1',port=port),connect=list(connect),receive_limit=2097152,local_policy='bounded-local-v1',avalanche=dict(credentials=str(credentials) if credentials else None,initial_download=dict(minimum_height=2024,maximum_tip_age_seconds=172800))))+'\n')
        node=local.Node(label,daemon,manifest,home,config,root,a.timeout);nodes.append(node)
        evidence['processes'].append(dict(label=label,pid=node.process.pid,command=node.command));save()
        node.await_ready();return node
    def status(node):
        while time.monotonic()<end:
            value=node.request('status')
            if value.get('tip_known') and value.get('mempool_ready') and not any(value.get(k) for k in ('pending_journal','pending_receipt','pending_propagation','execution_paused','reopen_required')):return value
            time.sleep(.01)
        raise AssertionError('global deadline expired waiting for quiescence')
    def stop(node):
        node.stop();evidence['cleanup'].append(dict(label=node.label,pid=node.process.pid,exit=node.process.poll()));save()
        require(node.process.poll()==0,'unclean node exit')
    try:
        if a.seed:
            previous=a.seed.resolve(); prior=json.loads((previous/'evidence.json').read_text())
            resumable=a.resume_seed and prior.get('phase')=='seed' and prior.get('failure',{}).get('error') in ('import deadline expired','global deadline expired waiting for quiescence')
            require((prior.get('seed_passed') or resumable) and prior['daemon_sha256']==(a.seed_daemon_sha256 or a.daemon_sha256) and prior['manifest_sha256']==local.digest(manifest),'stopped enabled seed evidence mismatch')
            seed_cleanup=[x for x in prior['cleanup'] if x['label']=='seed']
            require(seed_cleanup and all(x['exit']==0 for x in seed_cleanup),'seed not cleanly stopped')
            evidence['seed_source']=dict(directory=str(previous),evidence_sha256=local.digest(previous/'evidence.json'),daemon_source=prior['daemon_source'],daemon_sha256=prior['daemon_sha256'])
            save()
            shutil.copytree(previous/'seed-home',root/'seed-home')
        seed=start('seed',root/'seed-home')
        initial=status(seed)
        require(initial['avalanche']['observer'] and (0<=initial['height']<=2024 if a.resume_seed else initial['height']==(2024 if a.seed else 0)),'enabled observer state differs')
        ledger=[json.loads(row) for row in (bootstrap/'accepted-blocks.jsonl').read_text().splitlines()]
        if initial['height']:
            require(all(initial[k]==ledger[initial['height']-1]['status'][k] for k in local.STATE_FIELDS),'resumed enabled seed differs from actual accepted ledger')
            check('resumed-enabled-seed-ledger-prefix',status=initial)
        for row in [r for r in ledger if r['height']>initial['height']]:
            require(time.monotonic()<end,'import deadline expired')
            height=row['height'];body=bootstrap/'blocks'/(str(height)+'.block')
            require(local.digest(body)==row['body_sha256'],'bootstrap body hash mismatch')
            answer=seed.request('submitblock',block=body.read_bytes().hex())
            require(answer.get('ok'),'native import rejected block '+str(height)+': '+str(answer))
            until=min(end,time.monotonic()+a.timeout)
            while True:
                current=status(seed)
                if current['tip']==row['status']['tip']:break
                require(time.monotonic()<until,'import block failed to connect '+str(height))
            require(all(current[k]==row['status'][k] for k in local.STATE_FIELDS),'imported state differs')
            if height%100==0 or height==2024:
                check('enabled-seed-import',height=height,status=current);print('Enabled seed accepted',height,flush=True)
        for funding in original['funding']:
            coin=seed.request('coin',txid=funding['txid'],index=0)
            require(coin.get('coin')==funding['coin'],'actual funding coin mismatch')
        evidence['seed_final']=status(seed)
        require(evidence['seed_final']['height']==2024 and evidence['seed_final']['avalanche']['observer'] and evidence['seed_final']['avalanche']['proof_count']==0 and not evidence['seed_final']['avalanche']['tip_finalized'],'seed must remain an unfinalized proof-free enabled observer')
        stop(seed)
        evidence['seed_passed']=True
        check('seed-stopped-before-copy',namespace_marker=(root/'seed-home'/'lotus-v2-development.identity').read_text())
        if a.phase=='seed':
            evidence['seed_passed']=True;evidence['remaining']='provisioning, authenticated quorum, real finality, competing fork, recovery and restart';save();return
        credentials=[];homes=[]
        for i,funding in enumerate(original['funding']):
            home=root/('node-'+str(i+1)+'-home');shutil.copytree(root/'seed-home',home);homes.append(home)
            scalar=funding['public_fixture_scalar'];key=format(scalar,'064x');session_key=format(scalar%9+1,'064x')
            # All keys below are the explicitly public fixture scalars 1..9.
            request=dict(schema=1,sequence=1,expiration=0,master_key=key,session_key=session_key,payout_script='76a914'+'11'*20+'88ac',stakes=[dict(tx_id=funding['txid'],index=0,amount=int(funding['value']),height=funding['creation_height'],coinbase=True,key=key,payment_lock=funding['script'])])
            private=root/('node-'+str(i+1)+'.private.json');fd=os.open(private,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
            with os.fdopen(fd,'w') as out:json.dump(request,out)
            credential=root/('node-'+str(i+1)+'.credentials.json')
            result=subprocess.run([str(daemon),'-lotusv2provision',str(manifest),str(home),str(private),str(credential)],capture_output=True,text=True,timeout=a.timeout)
            check('native-offline-provision',node=i+1,exit=result.returncode,stdout=result.stdout,stderr=result.stderr,home=str(home),credential_mode=oct(credential.stat().st_mode&0o777) if credential.exists() else None)
            require(result.returncode==0,'native provision failed node '+str(i+1))
            require(credential.stat().st_mode&0o777==0o600,'credential mode differs')
            credentials.append(credential)
        active=[];endpoints=[]
        for i in range(9):
            node=start('quorum-'+str(i+1),homes[i],endpoints,credentials=credentials[i]);active.append(node);endpoints.append(node.ready['listen'])
        def wait_all(name,predicate,seconds=180):
            until=min(end,time.monotonic()+seconds)
            while time.monotonic()<until:
                values=[status(n) for n in active]
                if all(predicate(v) for v in values):check(name,statuses=values);return values
                evidence['last_statuses']=values;save();time.sleep(.25)
            raise AssertionError(name+' deadline expired')
        values=wait_all('authenticated-default-quorum',lambda s:s['height']==2024 and not s['avalanche']['failed'] and not s['avalanche']['error'] and not s['avalanche']['reconcile_error'] and s['peer_active']>=8 and s['avalanche']['authenticated_peer_count']>=8 and s['avalanche']['eligible_peer_count']>=8 and s['avalanche']['quorum_ready'] and s['avalanche']['quorum_established'])
        wait_all('real-polled-seed-finality',lambda s:s['avalanche']['tip_finalized'],300)
        evidence['quorum_passed']=True;save()
        forkhome=root/'fork-producer-home';shutil.copytree(root/'seed-home',forkhome)
        producer=start('fork-producer',forkhome)
        def mine(node,tag,timestamp):
            before=status(node);nonce='0'
            for _ in range(4096):
                require(time.monotonic()<end,'mining overall deadline expired')
                answer=node.request('minepool',expected_parent=before['tip'],time=timestamp,max_claim='100000',coinbase_output=original['funding'][0]['coinbase_output'],coinbase_data=tag.encode().hex(),start_nonce=nonce,max_attempts=256)
                require(answer.get('ok'),'native mining failed '+str(answer))
                if answer.get('found'):break
                require(answer.get('result')=='nonce_exhausted' and answer.get('next_nonce') is not None,'invalid mining continuation')
                nonce=answer['next_nonce']
            require(answer.get('found'),'bounded mining exhausted')
            until=min(end,time.monotonic()+a.timeout)
            while status(node)['tip']!=answer['block_id']:require(time.monotonic()<until,'mined block failed to connect')
            read=node.request('readblock',block_id=answer['block_id'],offset=0,length=2097152)
            require(read.get('ok') and read['eof'],'mined body read incomplete')
            path=root/(tag+'.block');path.write_bytes(bytes.fromhex(read['data']))
            check('native-mined-'+tag,result=answer,status=status(node),body_sha256=local.digest(path))
            return answer['block_id'],read['data']
        timestamp=ledger[-1]['time']+1
        fork_id,fork_body=mine(producer,'competing-2025',timestamp)
        fork_child_id,fork_child_body=mine(producer,'competing-2026',timestamp+1)
        stop(producer)
        selected_id,selected_body=mine(active[0],'selected-2025',timestamp)
        selected=wait_all('selected-block-network-propagation',lambda s:s['height']==2025 and s['tip']==selected_id)
        # Equal work preserves the selected tip. Poll this retained rival while
        # it is still eligible, before finality would suppress reconciliation.
        for node in active:
            answer=node.request('submitblock',block=fork_body)
            require(answer.get('ok'),'equal-work fork submission failed')
            check('competing-fork-submitted-before-finality',node=node.label,block_id=fork_id,response=answer)
        if a.require_block_observation:
            until=min(end,time.monotonic()+180)
            while time.monotonic()<until:
                observations=[n.request('blockstatus',block_id=fork_id) for n in active]
                if all(q.get('block_observation',{}).get('observation_available') and q['block_observation']['parked'] for q in observations):
                    check('real-polled-competing-fork-parked',statuses=observations);break
                evidence['last_fork_observations']=observations;save();time.sleep(.25)
            else:raise AssertionError('real-polled competing fork did not park')
        selected=wait_all('selected-block-real-finality',lambda s:s['tip']==selected_id and s['avalanche']['tip_finalized'],300)
        for node in active:
            answer=node.request('submitblock',block=fork_child_body)
            require(answer.get('ok'),'higher-work competing child submission failed')
            check('competing-child-submitted-after-finality',node=node.label,block_id=fork_child_id,response=answer)
        wait_all('higher-work-competing-fork-excluded',lambda s:s['tip']==selected_id and s['height']==2025 and s['avalanche']['tip_finalized'])
        for node in active:
            for identity in (fork_id,fork_child_id):
                query=node.request('blockstatus',block_id=identity)
                require(query['known_header'] and not query['deterministic_invalid'] and not query['is_active_tip'],'competing fork not retained as non-active valid header')
                if a.require_block_observation:
                    observation=query['block_observation']
                    require(query['block_id']==identity and observation['observation_available'] and observation['known'] and observation['valid'] and not observation['active'] and observation['parked'] and observation['conflicting_finalized'],'requested competing-fork observation differs')
                check('competing-fork-retained',node=node.label,block_id=identity,status=query)
        for node in active:stop(node)
        for i,home in enumerate(homes):
            store=home/'chainstate-v2'/'avalanche-peers.dat'
            check('stopped-peer-proof-store',node=i+1,size=store.stat().st_size,sha256=local.digest(store))
        active=[];endpoints=[]
        for i in range(9):
            node=start('restart-'+str(i+1),homes[i],endpoints,credentials=credentials[i]);active.append(node);endpoints.append(node.ready['listen'])
            initial_restart=status(node)
            if i==0:require(initial_restart['peer_active']==0 and initial_restart['avalanche']['authenticated_peer_count']==0 and initial_restart['avalanche']['proof_count']==9,'proofs must reload before any remote peer reconnects')
            check('restart-initial-proof-count',node=i+1,status=initial_restart)
        restarted=wait_all('restart-authenticated-default-quorum',lambda s:s['tip']==selected_id and s['height']==2025 and s['avalanche']['proof_count']==9 and s['avalanche']['authenticated_peer_count']>=8 and s['avalanche']['quorum_ready'] and s['avalanche']['quorum_established'])
        wait_all('restart-real-finality',lambda s:s['tip']==selected_id and s['avalanche']['tip_finalized'],300)
        for node in active:
            for identity in (fork_id,fork_child_id):
                query=node.request('blockstatus',block_id=identity)
                require(query['known_header'] and not query['is_active_tip'],'competing fork lost on restart')
                if a.require_block_observation:
                    observation=query['block_observation']
                    require(query['block_id']==identity and observation['observation_available'] and observation['known'] and observation['valid'] and not observation['active'] and observation['parked'] and observation['conflicting_finalized'],'restart competing-fork observation differs')
                check('restart-competing-fork-retained',node=node.label,block_id=identity,status=query)
        evidence['restart_passed']=True
        evidence['remaining']='Direct parked/conflicting-finalized observations unavailable in pinned blockstatus API; higher-work fork exclusion is recorded without claiming its internal parked reason.'
        if a.require_block_observation:
            evidence['passed']=True;evidence['remaining']=None
        save()

    except Exception as error:
        evidence['failure']=dict(kind=type(error).__name__,error=str(error));save();raise
    finally:
        cleanup_errors=[]
        for node in nodes:
            try:
                if node.process.poll() is None:stop(node)
                elif not any(c['pid']==node.process.pid for c in evidence['cleanup']):
                    evidence['cleanup'].append(dict(label=node.label,pid=node.process.pid,exit=node.process.poll()))
                    require(node.process.poll()==0,'owned node exited unexpectedly')
            except Exception as error:cleanup_errors.append(dict(node=node.label,error=str(error)))
        if cleanup_errors:
            evidence['passed']=False;evidence['cleanup_errors']=cleanup_errors
        save()
        require(not cleanup_errors,'owned process cleanup failed')


if __name__=='__main__':main()
