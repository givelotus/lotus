"""Native encrypted SQLite wallet -> compiled Payment -> complete offline blocks."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys


def load_pilot():
    name='lotus_v2_wallet_shared_chain_pilot'
    spec=importlib.util.spec_from_file_location(name,Path(__file__).parent.parent/'development-chain-pilot/run.py')
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    spec.loader.exec_module(module)
    return module


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--daemon',type=Path,required=True)
    parser.add_argument('--daemon-source',required=True)
    parser.add_argument('--wallet-helper',type=Path,required=True)
    parser.add_argument('--wallet-source',required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--node',default='node')
    args=parser.parse_args(argv)
    pilot=load_pilot()
    root=args.output.resolve()
    if root.exists():raise FileExistsError('wallet pilot output must be new')
    events=[]
    password=None
    compiled=None
    funding=None
    signed=None

    def save():
        (root/'wallet-evidence.json').write_text(json.dumps(events,indent=2)+'\n')

    def invoke(operation,request=None,expected=0):
        command=[str(args.wallet_helper.resolve()),str(args.manifest.resolve()),str(root/'home'),str(root/'wallet'),operation]
        result=subprocess.run(command,input=json.dumps(request or {}),capture_output=True,text=True,timeout=60)
        # Only helper responses are retained; requests may contain a passphrase-file
        # path but never its contents. The native helper must never emit secrets.
        events.append(dict(operation=operation,exit=result.returncode,stdout=result.stdout,stderr=result.stderr))
        save()
        if expected is not None:assert result.returncode==expected,events[-1]
        return json.loads(result.stdout)

    def compile_for_owner(owner):
        result=subprocess.run([args.node,str(Path(__file__).with_name('compile.mjs'))],input=json.dumps(dict(owner=owner)),capture_output=True,text=True,timeout=30)
        assert result.returncode==0,result.stderr
        return json.loads(result.stdout)

    def chain(operation,argument=None):
        command=[str(args.daemon.resolve()),'-lotusv2development',str(args.manifest.resolve()),str(root/'home'),operation]
        if argument is not None:command.append(str(argument))
        result=subprocess.run(command,capture_output=True,text=True,timeout=60)
        events.append(dict(operation='daemon-'+operation,exit=result.returncode,stdout=result.stdout,stderr=result.stderr));save()
        assert result.returncode==0,events[-1]
        return json.loads(result.stdout)

    def funding_status(reconciled):
        matches=[coin for coin in reconciled['coins'] if coin['prev_txid']==funding['prev_txid'] and coin['prev_index']==funding['prev_index']]
        assert len(matches)==1,reconciled
        return matches[0]

    def compiler(mode,request):
        nonlocal password,compiled,funding,signed
        if mode=='artifact':
            password=root/'temporary-passphrase'
            fd=os.open(password,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
            with os.fdopen(fd,'w') as stream:stream.write(secrets.token_urlsafe(48))
            created=invoke('create',dict(passphrase_file=str(password)))
            compiled=compile_for_owner(created['public_key'])
            registered=invoke('register',dict(script=compiled['script'],proof=compiled['proof'],root=compiled['root']))
            assert registered['policy_root']==compiled['root']
            return compiled
        context=request['context']
        if mode=='immature':
            funding=dict(prev_txid=context['prevTxid'],prev_index=context['prevIndex'])
            invoke('track',funding)
            view=invoke('reconcile')
            coin=funding_status(view)
            assert coin['present'] and not coin['mature'] and not coin['reserved'],coin
            result=invoke('sign',dict(passphrase_file=str(password),recipient=dict(flags=0,**context['outputs'][0]),fee='1000'),expected=None)
            # Native helper's explicit unsuccessful result is required, not inferred
            # from a missing signature or arbitrary process error.
            assert events[-1]['exit']==2 and result.get('result')=='insufficient_funds',result
            assert 'mature' in result.get('error',''),result
            return dict(accepted=False,reason='immature',evidence=dict(sign=result,reconciled=view))
        if mode!='sign':raise ValueError('unknown wallet compiler callback')
        # The sign callback runs only after real daemon maturity-block acceptance.
        before=chain('status')
        reconciled=invoke('reconcile')
        tracked=funding_status(reconciled)
        assert tracked['present'] and tracked['mature'] and not tracked['reserved'],tracked
        stale=invoke('stale',dict(passphrase_file=str(password),recipient=dict(flags=0,**context['outputs'][0]),fee='1000',expected_tip=before['tip']),expected=2)
        assert stale['result']=='stale' and stale['disconnected_tip']==before['tip'] and 'wire' not in stale,stale
        assert chain('status')['tip']==stale['tip']
        assert not funding_status(invoke('reconcile'))['reserved']
        maturity_block=root/('maturity-'+str(before['height'])+'.block')
        restored=chain('submit',maturity_block)
        assert all(restored[key]==before[key] for key in ['tip','height','utxo_root','state_root'])
        assert chain('status')==before
        signed=invoke('sign',dict(passphrase_file=str(password),recipient=dict(flags=0,**context['outputs'][0]),fee='1000'))
        from lotus_v2_reference.signing import TxProfile, decode_transaction, encode_transaction
        from dataclasses import replace
        manifest=json.loads(args.manifest.read_text())
        profile=TxProfile(*manifest['transaction_limits'])
        tx=decode_transaction(bytes.fromhex(signed['wire']),profile)
        witness=tx.inputs[0].witnesses[0]
        signature=bytearray(witness.arguments[0]);signature[0]^=1
        mutated_witness=replace(witness,arguments=(bytes(signature),))
        mutated_input=replace(tx.inputs[0],witnesses=(mutated_witness,))
        mutated=replace(tx,inputs=(mutated_input,))
        return {**signed,'bad_wire':encode_transaction(mutated,profile).hex()}

    config=pilot.PilotConfig(args.manifest,args.daemon,args.output,args.daemon_source,node=args.node,sign_after_maturity=True)
    try:
        summary=pilot.run_pilot(config,compiler)
        reconciled=invoke('reconcile')
        tracked=funding_status(reconciled)
        assert not tracked['present'] and tracked['reserved'],tracked
        before=chain('status')
        restored=chain('disconnect',before['tip'])
        assert restored['height']==before['height']-1
        tracked=funding_status(invoke('reconcile'))
        assert tracked['present'] and tracked['mature'] and tracked['reserved'],tracked
        # Local exported-byte reservations survive a chain undo and wallet reopen.
        replay=chain('submit',root/'signed-spend.block')
        assert all(replay[key]==before[key] for key in ['tip','height','utxo_root','state_root'])
        assert chain('status')==before
        assert not funding_status(invoke('reconcile'))['present']
        events.append(dict(operation='pilot-complete',summary=summary,reconciled=reconciled,wallet_source=args.wallet_source,
            wallet_helper_sha256=hashlib.sha256(args.wallet_helper.read_bytes()).hexdigest()))
        save()
        print('Native-wallet complete signed chain pilot passed:',root)
        return 0
    except Exception as error:
        if password is not None and root.is_dir():
            (root/'wallet-failure.json').write_text(json.dumps(dict(kind=type(error).__name__,error=str(error)),indent=2)+'\n')
        raise
    finally:
        if password is not None:password.unlink(missing_ok=True)

if __name__=='__main__':raise SystemExit(main())
