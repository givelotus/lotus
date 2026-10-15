"""Generate and verify a complete signed payment chain in a fresh offline home."""
import argparse, hashlib, json, subprocess
from dataclasses import dataclass, replace
from pathlib import Path
from lotus_v2_reference.block import (Coin, Parent, MonetaryState, utxo_root, state_root,
    connect_complete_block, disconnect, _complete_ordinary)
from lotus_v2_reference.block_wire import decode_block_wire, encode_block_wire, complete_transaction_root
from lotus_v2_reference.block_seal import Header, block_id
from lotus_v2_reference.header_context import HeaderChainProfile, parent_median_time
from lotus_v2_reference.asert import Parent as AsertParent, required_bits, compact_decode
from lotus_v2_reference.encoding import Output, encode_compact_size
from lotus_v2_reference.signing import TxProfile, Transaction, Input, decode_transaction, encode_transaction, identity_digests
from lotus_v2_reference.monetary import Profile, advance, block_cost
from lotus_v2_reference.block_cost import BlockCostProfile, authenticated_transaction_costs, authenticated_envelope_cost
from lotus_v2_reference.vm import ASSIGNED, VMProfile

@dataclass
class PilotConfig:
    manifest: Path
    daemon: Path
    output: Path
    daemon_source: str
    node: str = 'node'
    compiler_helper: Path | None = None
    source: str | None = None
    options: dict | None = None
    method: str = 'spend'
    arguments: dict | None = None
    signature_argument: str = 'signature'
    sign_after_maturity: bool = False
    reference_negative_errors: tuple[str, ...] = ('CHECKSIGVERIFY',)
    native_negative_errors: tuple[str, ...] = ('CHECKSIGVERIFY',)


def run_pilot(a: PilotConfig, compiler=None):
    """Run independent complete-block engines; compiler(mode, request) is optional.

    Compiler requests carry source/options/method/args/signature_argument plus
    context for sign. Responses follow payment.mjs artifact/sign JSON protocol.
    No state or process is created until explicitly called.
    """
    a.output.mkdir()  # Exclusive: preserve all previous runs, even failures.
    root=a.output.resolve()
    manifest=json.loads(a.manifest.read_text())
    (root/'manifest.json').write_bytes(a.manifest.read_bytes())
    records=[]
    def save():
        (root/'evidence.json').write_text(json.dumps(records,indent=2)+'\n')
    def node(mode, data=None):
        request=dict(source=a.source,options=a.options,method=a.method,args=a.arguments,signature_argument=a.signature_argument)
        if data is not None:request['context']=data
        if compiler is not None:return compiler(mode,request)
        r=subprocess.run([a.node,str(a.compiler_helper or Path(__file__).with_name('payment.mjs')),mode],input=json.dumps(request),capture_output=True,text=True,timeout=30)
        if r.returncode: raise RuntimeError(r.stderr)
        return json.loads(r.stdout)
    compiled=node('artifact')
    (root/'payment-artifact.json').write_text(json.dumps(compiled,indent=2)+'\n')
    artifact=compiled['artifact']; policy=bytes.fromhex(artifact['policy']['root'])
    chain=bytes.fromhex(manifest['header']['chain_id'])
    TX=TxProfile(*manifest['transaction_limits']); M=Profile(*manifest['monetary'])
    COST=BlockCostProfile(*manifest['outer_costs'])
    vm=manifest['vm_limits']; schedule=manifest['opcode_costs']
    VM=VMProfile(*vm[:7],int(manifest['invocation_limits'][0]),manifest['invocation_limits'][2],
        {op:(lambda operands,results,c=schedule[op]: c[0]+c[1]*sum(operands)+c[2]*sum(results)) for op in ASSIGNED})
    h=manifest['header']; HP=HeaderChainProfile(chain,h['version'],h['time'],h['bits'],int.from_bytes(bytes.fromhex(h['pow_limit']),'little'),h['half_life'],h['spacing'])
    genesis_block=decode_block_wire(bytes.fromhex(manifest['genesis']),TX,chain)
    genesis=genesis_block.header
    monetary=MonetaryState.from_bytes(bytes.fromhex(manifest['initial_monetary']))
    if manifest.get('schema')!=1 or manifest['field_sizes']:
        raise ValueError('pilot requires schema1 and no supplied field-size hints')
    if manifest['dust_limit']!=M.dust_limit:
        raise ValueError('pilot requires matching ordinary/monetary dust limits')
    if any(not output.flags&2 or output.value for tx in genesis_block.transactions for output in tx.outputs):
        raise ValueError('pilot requires zero-valued pruned genesis outputs')
    if state_root(chain,0,utxo_root({}),monetary)!=genesis.state_root:
        raise ValueError('pilot requires empty authenticated genesis UTXO state')
    if block_id(chain,genesis).hex()!=h['genesis_id']:
        raise ValueError('manifest genesis identity mismatch')
    coins={}; history=[genesis]; parent=Parent(chain,0,genesis.time,genesis.state_root,monetary,genesis)
    cap=int(manifest['invocation_limits'][1]); maturity=manifest['coinbase_maturity']
    if not 1<=maturity<=32: raise ValueError('pilot generation maturity bound 1..32')
    def mine(header):
        target=compact_decode(header.bits,HP.pow_limit)
        for nonce in range(1000000):
            candidate=replace(header,nonce=nonce)
            if int.from_bytes(block_id(chain,candidate),'little')<=target:return candidate
        raise RuntimeError('bounded nonce search exhausted')
    def status():
        return dict(tip=block_id(chain,parent.header).hex(),height=parent.height,utxo_root=utxo_root(coins).hex(),state_root=parent.state_root.hex())
    def daemon(label,args,expected=0):
        cmd=[str(a.daemon.resolve()),'-lotusv2development',str(root/'manifest.json'),str(root/'home'),*args]
        r=subprocess.run(cmd,capture_output=True,text=True,timeout=60)
        record=dict(label=label,argv=cmd,exit=r.returncode,stdout=r.stdout,stderr=r.stderr)
        records.append(record);save()
        assert r.returncode==expected,record
        result=json.loads(r.stdout)
        for key,value in status().items():assert result[key]==value,(label,key,result,value)
        return result

    def build(ordinary=()):
        height=parent.height+1; mtp=parent_median_time(HP,parent.header,history)
        cb=Transaction(0,(Input(block_id(chain,parent.header),height,0xffffffff,2),),(Output(0,100000,None,(policy,),((0,),)),))
        txs=(cb,*ordinary); staged=dict(coins); linear=[]; accounted=[]; invocation=0
        for n,tx in enumerate(txs):
            spent=[];vm_cost=0
            if n:
                record,vm_cost,spent=_complete_ordinary(tx,parent,staged,M,height=height,mtp=mtp,maturity=maturity,vm_profile=VM,tx_profile=TX,block_cap=cap)
                accounted.append(record)
            charge=authenticated_transaction_costs(tx,TX,staged,height,mtp,vm_cost,COST)
            linear.append(charge.account_linear);invocation+=vm_cost
            for coin in spent:del staged[coin.key()]
            ids=identity_digests(tx,TX,chain)
            for j,out in enumerate(tx.outputs):
                if not out.flags&2:
                    coin=Coin(ids.txid,j,out.value,out.branches[0],height,mtp,n==0,out);staged[coin.key()]=coin
        frames=sum(len(encode_compact_size(len(encode_transaction(tx,TX)))) for tx in txs)
        envelope=authenticated_envelope_cost(frames,len(txs),COST)
        cost=block_cost(envelope,tuple(linear),M)
        bits=required_bits(AsertParent(parent.header.time,parent.height),t0=HP.genesis_time,genesis_target=compact_decode(HP.genesis_bits,HP.pow_limit),spacing=HP.spacing_seconds,half_life=HP.half_life_seconds,pow_limit=HP.pow_limit)
        tr=advance(M,monetary,work=(1<<256)//(compact_decode(bits,HP.pow_limit)+1),transactions=tuple(accounted),coinbase_native_outputs=100000,coinbase_native_burn=0,coinbase_bytes=len(encode_transaction(cb,TX)),tx_frame_prefix_bytes=frames,account_block_cost=cost,enforce_block_cost=cost)
        size=138+frames+sum(len(encode_transaction(tx,TX)) for tx in txs)
        header=mine(Header(block_id(chain,parent.header),bits,parent.header.time+HP.spacing_seconds,0,HP.version,size,height,complete_transaction_root(txs,TX,chain),state_root(chain,height,utxo_root(staged),tr.state)))
        return encode_block_wire(header,txs,TX),dict(charges={key:str(value) for key,value in dict(invocation=invocation,account=cost,enforce=cost,required_underclaim=tr.required_underclaim,actual_underclaim=tr.actual_underclaim,fees=tr.total_fees,subsidy=tr.subsidy).items()},transaction_ids=[identity_digests(t,TX,chain).txid.hex() for t in txs],transaction_hashes=[identity_digests(t,TX,chain).txhash.hex() for t in txs])
    def connect(wire):
        return connect_complete_block(wire,parent,history,HP,coins,monetary,M,COST,tx_profile=TX,vm_profile=VM,block_cap=cap,coinbase_maturity=maturity)
    def accept(label,wire,charges):
        nonlocal parent,monetary,history
        path=root/(label+'.block');path.write_bytes(wire)
        result=connect(wire);header=decode_block_wire(wire,TX,chain).header
        monetary=MonetaryState.from_bytes(result.monetary_bytes)
        parent=Parent(chain,header.height,header.time,header.state_root,monetary,header)
        history=([header]+history)[:11]
        records.append(dict(label=label+'-reference',**status(),**charges,monetary_bytes=result.monetary_bytes.hex()));save()
        native=daemon(label,['submit',str(path)])
        assert native['accepted'] is True
        assert native['charges']==charges['charges'],(label,'charge discrepancy',native,charges)
        daemon(label+'-restart',['status'])
        return result

    try:
        daemon('genesis',['status'])
        wire,charges=build();accept('funding',wire,charges)
        funding=next(c for c in coins.values() if c.creation_height==1)
        context=dict(chainId=chain.hex(),prevTxid=funding.tx_id.hex(),prevIndex=funding.index,sequence=0xffffffff,
            coin=dict(value=str(funding.value),branches=[policy.hex()],paths=[[0]]),outputs=[dict(value=str(funding.value-1000),branches=[policy.hex()],paths=[[0]])])
        if a.sign_after_maturity:
            if maturity<=1:raise ValueError('deferred signing requires an actual immature height')
            probe=node('immature',context)
            records.append(dict(label='immature-wallet-probe',probe=probe));save()
            if not isinstance(probe,dict) or probe.get('accepted') is not False or probe.get('reason')!='immature' or not probe.get('evidence'):
                raise ValueError('explicit rejected immature wallet probe evidence required')
        else:
            signed=node('sign',context);(root/'signed-payment.json').write_text(json.dumps(signed,indent=2)+'\n')
            tx=decode_transaction(bytes.fromhex(signed['wire']),TX)
            assert identity_digests(tx,TX,chain).txid.hex()==signed['txid']
            assert identity_digests(tx,TX,chain).txhash.hex()==signed['txhash']
        if maturity>1 and not a.sign_after_maturity:
            # A correctly framed/mined immature spend must fail before state-root checks.
            height=parent.height+1
            cb=Transaction(0,(Input(block_id(chain,parent.header),height,0xffffffff,2),),(Output(0,100000,None,(policy,),((0,),)),))
            txs=(cb,tx)
            bits=required_bits(AsertParent(parent.header.time,parent.height),t0=HP.genesis_time,genesis_target=compact_decode(HP.genesis_bits,HP.pow_limit),spacing=HP.spacing_seconds,half_life=HP.half_life_seconds,pow_limit=HP.pow_limit)
            frames=sum(len(encode_compact_size(len(encode_transaction(t,TX)))) for t in txs)
            size=138+frames+sum(len(encode_transaction(t,TX)) for t in txs)
            immature_header=mine(Header(block_id(chain,parent.header),bits,parent.header.time+HP.spacing_seconds,0,HP.version,size,height,complete_transaction_root(txs,TX,chain),bytes(32)))
            immature=encode_block_wire(immature_header,txs,TX)
            path=root/'immature-spend.block';path.write_bytes(immature)
            prior=dict(coins)
            try:connect(immature)
            except ValueError as error:
                assert 'maturity' in str(error),str(error)
                records.append(dict(label='immature-reference',accepted=False,error=str(error)));save()
            else:raise AssertionError('immature coinbase spend accepted')
            assert coins==prior
            rejected=daemon('immature-spend',['submit',str(path)],2)
            assert 'maturity' in rejected.get('error',''),rejected
            daemon('restart-after-immature',['status'])
        for _ in range(maturity-1):
            wire,charges=build();accept('maturity-'+str(parent.height+1),wire,charges)
        if a.sign_after_maturity:
            signed=node('sign',context);(root/'signed-payment.json').write_text(json.dumps(signed,indent=2)+'\n')
            tx=decode_transaction(bytes.fromhex(signed['wire']),TX)
            assert identity_digests(tx,TX,chain).txid.hex()==signed['txid']
            assert identity_digests(tx,TX,chain).txhash.hex()==signed['txhash']
        before_parent=parent;before_history=list(history);before_coins=dict(coins);before_monetary=monetary
        wire,charges=build((tx,))
        # Signature changes full bytes/txhash, but never its core TxId or state effects.
        bad=decode_transaction(bytes.fromhex(signed['bad_wire']),TX)
        bad_ids=identity_digests(bad,TX,chain);good_ids=identity_digests(tx,TX,chain)
        assert bad_ids.txid==good_ids.txid and bad_ids.txhash!=good_ids.txhash
        framed=decode_block_wire(wire,TX,chain)
        negatives=[dict(name='bad-signature',wire=signed['bad_wire'],reference_errors=a.reference_negative_errors,native_errors=a.native_negative_errors)]
        negatives.extend(signed.get('negatives',[]))
        if len(negatives)>32:raise ValueError('pilot negative count exceeds 32')
        names=set()
        for negative in negatives:
            name=negative['name']
            if not isinstance(name,str) or not 1<=len(name)<=64 or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in name) or name in names:
                raise ValueError('invalid or duplicate negative name')
            names.add(name)
            bad_tx=decode_transaction(bytes.fromhex(negative['wire']),TX)
            bad_txs=(framed.transactions[0],bad_tx)
            bad_size=138+sum(len(encode_compact_size(len(encode_transaction(t,TX))))+len(encode_transaction(t,TX)) for t in bad_txs)
            bad_header=mine(replace(framed.header,size=bad_size,tx_root=complete_transaction_root(bad_txs,TX,chain)))
            bad_wire=encode_block_wire(bad_header,bad_txs,TX);bad_path=root/(name+'.block');bad_path.write_bytes(bad_wire)
            reference_errors=negative.get('reference_errors',('VERIFY',))
            native_errors=negative.get('native_errors',('VERIFY',))
            try:connect(bad_wire)
            except ValueError as error:
                records.append(dict(label=name+'-reference',accepted=False,error=str(error)));save()
                assert not reference_errors or any(text in str(error) for text in reference_errors),str(error)
            else:raise AssertionError(name+' accepted by reference')
            assert coins==before_coins
            rejected=daemon(name,['submit',str(bad_path)],2)
            assert not native_errors or any(text in rejected.get('error','') for text in native_errors),rejected
            daemon('restart-after-reject' if name=='bad-signature' else name+'-restart',['status'])
        accepted=accept('signed-spend',wire,charges);after=status()
        assert funding.key() not in coins
        monetary=disconnect(accepted.undo,coins);parent=before_parent;history=before_history
        assert monetary==before_monetary and coins==before_coins
        daemon('undo',['disconnect',after['tip']]);daemon('restart-after-undo',['status'])
        accept('reconnect',wire,charges)
        assert status()==after
        (root/'summary.json').write_text(json.dumps(dict(schema='lotus-v2/development-chain-pilot/1',accepted=True,**after,source_sha256=hashlib.sha256(compiled['source'].encode()).hexdigest(),daemon_sha256=hashlib.sha256(a.daemon.read_bytes()).hexdigest(),manifest_sha256=hashlib.sha256(a.manifest.read_bytes()).hexdigest(),native_charges_exposed=True,daemon_source=a.daemon_source),indent=2)+'\n')
        return json.loads((root/'summary.json').read_text())
    except Exception as error:
        (root/'failure.json').write_text(json.dumps(dict(kind=type(error).__name__,error=str(error)),indent=2)+'\n')
        raise
    finally:save()


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest',type=Path,required=True)
    p.add_argument('--daemon',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--node',default='node')
    p.add_argument('--daemon-source',required=True)
    p.add_argument('--compiler-helper',type=Path)
    p.add_argument('--sign-after-maturity',action='store_true')
    p.add_argument('--source',type=Path,help='optional contract source file')
    p.add_argument('--options',type=Path,help='compiler options JSON')
    p.add_argument('--method',default='spend')
    p.add_argument('--arguments',type=Path,help='non-signature arguments JSON')
    p.add_argument('--signature-argument',default='signature')
    p.add_argument('--reference-negative-error',action='append')
    p.add_argument('--native-negative-error',action='append')
    args=p.parse_args(argv)
    config=PilotConfig(args.manifest,args.daemon,args.output,args.daemon_source,
        node=args.node,compiler_helper=args.compiler_helper,sign_after_maturity=args.sign_after_maturity,
        source=None if args.source is None else args.source.read_text(),
        options=None if args.options is None else json.loads(args.options.read_text()),
        method=args.method,arguments=None if args.arguments is None else json.loads(args.arguments.read_text()),
        signature_argument=args.signature_argument,
        reference_negative_errors=tuple(args.reference_negative_error or ['CHECKSIGVERIFY']),
        native_negative_errors=tuple(args.native_negative_error or ['CHECKSIGVERIFY']))
    run_pilot(config)
    print('Signed mature payment accepted, restarted, undone and reconnected:',config.output.resolve())
    return 0

if __name__=='__main__':
    raise SystemExit(main())
