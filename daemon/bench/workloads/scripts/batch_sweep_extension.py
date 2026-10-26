"""Append equal-count OP_TRUE batch sweeps after the frozen historical workload."""
import hashlib,io,math

def run_extension(context, series):
    c=context['clients'][0];clients=context['clients'];results=context['results']
    build=context['build_p2sh_op_true_tx'];to_hex=context['ToHex'];ingest=context['run_batch_ingestion']
    spk=context['op_true_spk'] if series=='l1' else context['V2_OP_TRUE_SCRIPT']
    def mine():
        if series=='l1':
            c.call('generatetoaddress',[1,context['ADDRESS_ECREG_P2SH_OP_TRUE']]);context['sync_all_blocks'](clients)
        else:
            c.call('generatetodescriptor',[1,context['V2_OP_TRUE_DESCRIPTOR']]);context['sync_all_blocks'](clients,base_dir=context['base_dir'])
    mine()
    available=[]
    for index,(txid,vout,sats) in enumerate(context['prebuilt_op_true_next_utxos']):
        second=context['CTransaction']();second.deserialize(io.BytesIO(bytes.fromhex(context['prebuilt_op_true_r2_hex'][index])))
        if c.call('gettxout',[f'{second.txid_int:064x}',0]) is not None:available.append((second.txid_int,0,sats-1000))
        elif c.call('gettxout',[f'{txid:064x}',vout]) is not None:available.append((txid,vout,sats))
        else:raise RuntimeError(f'No unspent OP_TRUE output at either known historical generation, index={index}, round1={txid:064x}, round2={second.txid_int:064x}')
    assert len(available)==6000,len(available)
    for size in (1,50,100,200,250,500,1000):
        raw=[];next_outputs=[]
        for txid,vout,sats in available:
            tx=build(txid,vout,sats-1000,spk);raw.append(to_hex(tx));next_outputs.append((tx.txid_int,0,sats-1000))
        digest=hashlib.sha256(''.join(raw).encode()).hexdigest()
        assert c.call('getmempoolinfo')['size']==0
        measured=ingest(raw,batch_size=size,num_workers=8,target_port=context['NODES_CFG'][0]['rpc_port'])
        assert measured['tx_count']==6000,measured
        measured.update({'request_count':math.ceil(6000/size),'transaction_fixture_sha256':digest,'script':'OP_TRUE','transaction_version':2 if series=='l1' else 7,'sequence_position':(1,50,100,200,250,500,1000).index(size)})
        results[f'batch_sweep_op_true_b{size}']=measured
        print(f'[Equal-count batch sweep] b={size}: {measured["tps"]:.1f} tx/s (6000 txs)',flush=True)
        mine();available=next_outputs
