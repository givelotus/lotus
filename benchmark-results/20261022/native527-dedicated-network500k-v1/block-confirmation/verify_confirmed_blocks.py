"""Source-prepared verifier for existing RPC clients; no daemon startup on import."""
import hashlib,io,time

def verify_confirmed_blocks(clients, hashes, expected_txids, messages):
    expected=set(expected_txids)
    assert len(expected)==len(expected_txids), "duplicate expected IDs"
    covered=set(); rows=[]
    for blockhash in hashes:
        headers=[n.call('getblockheader',[blockhash]) for n in clients]
        for key in ('hash','height','merkleroot','stateroot'):
            assert len({h[key] for h in headers})==1,(key,headers)
        rpcblocks=[n.call('getblock',[blockhash,1]) for n in clients]
        assert all(b['tx']==rpcblocks[0]['tx'] for b in rpcblocks)
        raw=[bytes.fromhex(n.call('getblock',[blockhash,0])) for n in clients]
        assert raw[0]==raw[1]==raw[2], "raw block mismatch"
        stream=io.BytesIO(raw[0]);block=messages.CBlock();block.deserialize(stream)
        assert stream.read()==b'', "unparsed block suffix"
        parsed=[messages.lotus_v2_compute_tx_identities(tx)[0][::-1].hex() for tx in block.vtx]
        assert parsed==rpcblocks[0]['tx'], "raw decoder vs RPC transaction mismatch"
        assert f'{block.hashStateRoot:064x}'==headers[0]['stateroot']
        assert f'{block.calc_merkle_root():064x}'==headers[0]['merkleroot']
        ordinary=set(parsed[1:]);assert not covered.intersection(ordinary),"duplicate included transaction"
        assert ordinary<=expected,"unexpected ordinary transaction"
        covered.update(ordinary)
        rows.append({'hash':blockhash,'height':headers[0]['height'],'stateroot':headers[0]['stateroot'],'ordinary_count':len(ordinary),'raw_sha256':hashlib.sha256(raw[0]).hexdigest()})
    assert covered==expected,{'missing':sorted(expected-covered),'unexpected':sorted(covered-expected)}
    tips=[n.call('getbestblockhash') for n in clients];assert len(set(tips))==1 and tips[0]==hashes[-1]
    assert all(n.call('verifychain',[4,len(hashes)]) for n in clients)
    # Current native output0 is an ordinary UTXO; sample boundary/spaced IDs.
    ordered=sorted(expected);sample=ordered[::max(1,len(ordered)//32)]
    for txid in sample:
        coins=[n.call('gettxout',[txid,0,False]) for n in clients]
        assert coins[0] is not None and coins[0]==coins[1]==coins[2]
    return {'status':'PASS','all_three_tip':tips[0],'covered_unique_transactions':len(covered),'blocks':rows,'utxo_samples_equal':len(sample),'avalanche_finalization_proven':False,'global_utxo_dump_equality_proven':False}
