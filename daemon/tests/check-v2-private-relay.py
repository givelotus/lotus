#!/usr/bin/env python3
"""Three native nodes, encrypted native wallet, compiler Payment and private FD bridge.

Every acceptance assertion uses native authoritative state. Payment bytes enter
only through submittransaction via the wallet's private Unix socket channel.
This development test does not establish Avalanche quorum or mainnet readiness.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import threading
import time


def local_module():
    spec = importlib.util.spec_from_file_location('local_nodes', Path(__file__).with_name('check-v2-local-nodes.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('daemon', 'wallet-client', 'manifest', 'compiler', 'output'):
        p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--timeout', type=float, default=30)
    p.add_argument('--node', default='node')
    p.add_argument('--daemon-source', required=True)
    p.add_argument('--wallet-source', required=True)
    p.add_argument('--compiler-source', required=True)
    args = p.parse_args(argv)
    local = local_module()
    require = local.require
    require(1 <= args.timeout <= 60, 'timeout must be 1..60 seconds')
    for pin in (args.daemon_source, args.wallet_source, args.compiler_source):
        require(local.hex_string(pin, 20), 'full exact source commit required')
    root = args.output.resolve()
    root.mkdir()  # Existing output/home must never be reused or reset.
    manifest = json.loads(args.manifest.read_text())
    require(manifest['schema'] == 2, 'absolute monetary schema 2 manifest required')
    require(2 <= manifest['coinbase_maturity'] <= 16, 'bounded maturity fixture required')
    (root/'manifest.json').write_bytes(args.manifest.read_bytes())
    daemon, wallet = args.daemon.resolve(), args.wallet_client.resolve()
    compiler = args.compiler.resolve()
    record = dict(schema='lotus-v2/private-relay-check/1', passed=False,
                  scope='native relay, wallet persistence and competing-chain reconciliation; no Avalanche quorum claim',
                  daemon_source=args.daemon_source, wallet_source=args.wallet_source,
                  compiler_source=args.compiler_source, daemon_sha256=local.digest(daemon),
                  wallet_sha256=local.digest(wallet), manifest_sha256=local.digest(args.manifest),
                  compiler_sha256=local.digest(compiler/'dist/generic.js'),
                  harness_sha256=local.digest(Path(__file__)), processes=[], checks=[])
    nodes = []
    def save():
        (root/'evidence.json').write_text(json.dumps(record, indent=2)+'\n')
    def check(name, **fields):
        record['checks'].append(dict(check=name, **fields)); save()
    def launch(label, home, peers):
        config = root/(label+'.network.json')
        config.write_text(json.dumps(dict(schema=1, magic='76327233',
            listen=dict(address='127.0.0.1', port=0), connect=peers,
            receive_limit=max(manifest['block_read_limit'], 1048576), local_policy='bounded-local-v1'))+'\n')
        node = local.Node(label, daemon, root/'manifest.json', home, config, root, args.timeout)
        nodes.append(node); node.await_ready()
        record['processes'].append(dict(label=label, pid=node.process.pid, command=node.command, ready=node.ready)); save()
        return node
    def eventually(fn, predicate, reason):
        end = time.monotonic()+args.timeout
        value = None
        while time.monotonic() < end:
            value = fn()
            if predicate(value): return value
            time.sleep(.05)
        raise AssertionError(reason+': '+str(value))
    def status(node):
        return eventually(lambda: node.request('status'), lambda s: s.get('tip_known') and s.get('mempool_ready') and not any(s.get(k) for k in ('pending_journal','pending_receipt','pending_propagation','execution_paused','reopen_required')), node.label+' not quiescent')
    def same(nodes, wanted):
        for node in nodes:
            eventually(lambda: status(node), lambda s: all(s[k] == wanted[k] for k in local.STATE_FIELDS), 'chain did not converge '+node.label)
    def call(node, home, command, payload=None):
        """Forward bounded JSONL requests unchanged over a private socketpair.

        The bridge owns no chain/wallet logic. Each invocation reopens the real
        encrypted SQLite wallet, testing durability on every operation.
        """
        parent, child = socket.socketpair()
        parent.settimeout(args.timeout)
        read_fd = write_fd = None
        fds = [child.fileno()]
        cmd = [str(wallet), str(root/'manifest.json'), str(home), command,
               '--node-fd='+str(child.fileno()), '--timeout-ms='+str(int(args.timeout*1000))]
        if command in ('create','sign','pay'):
            read_fd, write_fd = os.pipe()
            os.write(write_fd, b'isolated-public-test-passphrase')
            os.close(write_fd); fds.append(read_fd)
            cmd.append('--passphrase-fd='+str(read_fd))
        failures = []
        def bridge():
            try:
                stream = parent.makefile('rb')
                while True:
                    raw = stream.readline(1048577)
                    if not raw: break
                    require(len(raw) <= 1048576 and raw.endswith(b'\n'), 'private request bound')
                    request = json.loads(raw)
                    identity = request.pop('id'); operation = request.pop('command')
                    require(operation in ('walletcontext','submittransaction','transactionstatus'), 'private command allowlist')
                    response = node.request(operation, **request)
                    response['id'] = identity
                    parent.sendall((json.dumps(response,separators=(',',':'))+'\n').encode())
            except Exception as error: failures.append(str(error))
            finally: parent.close()
        worker = threading.Thread(target=bridge, daemon=True); worker.start()
        try:
            result = subprocess.run(cmd, input=json.dumps(payload or {}), text=True,
                                    capture_output=True, pass_fds=fds, timeout=args.timeout+2)
        finally:
            child.close()
            if read_fd is not None: os.close(read_fd)
            worker.join(timeout=args.timeout+1)
        require(not worker.is_alive() and not failures, 'private bridge failure '+str(failures))
        require(result.returncode == 0, command+' failed '+result.stdout+' '+result.stderr)
        value = json.loads(result.stdout)
        require(value.get('result') == 'success', command+' unsuccessful '+str(value))
        check('wallet-'+command, node=node.label, home=str(home), request=payload or {}, response=value)
        return value
    def compile_payment(public_key):
        source = compiler/'examples/gallery/payment.lotus'
        js = "import {readFileSync} from 'node:fs';const {compileContract}=await import(process.argv[1]); console.log(JSON.stringify(compileContract(readFileSync(process.argv[2],'utf8'),{contract:'Payment',bindings:{Payment:{owner:process.argv[3]}}})));"
        answer = subprocess.run([args.node,'--input-type=module','-e',js,(compiler/'dist/generic.js').as_uri(),str(source),public_key], capture_output=True,text=True,timeout=args.timeout)
        require(answer.returncode == 0, answer.stderr)
        artifact = json.loads(answer.stdout)
        (root/'payment-artifact.json').write_text(json.dumps(artifact,indent=2)+'\n')
        return artifact['methods'][0]['scriptHex'], artifact['policy']['root']
    def mine(node, destination, peers=(), selected=None, branch=0):
        before = status(node)
        answer = node.request('minepool', expected_parent=before['tip'],
            time=manifest['header']['time']+(before['height']+1)*manifest['header']['spacing']+branch,
            max_claim='100000', coinbase_output=destination, coinbase_data=None,
            start_nonce='0', max_attempts=256)
        require(answer.get('found') is True and answer.get('accepted') is False and answer.get('pending_validation') is True, 'minepool did not enter normal validation '+str(answer))
        if selected is not None: require(answer['pool_selected'] == selected, 'minepool selected wrong transaction count')
        after = eventually(lambda: status(node), lambda s: s['tip'] == answer['block_id'], 'native mined candidate unaccepted')
        same(peers, after)
        check('minepool-accepted', node=node.label, response=answer, status=after)
        return answer, after
    def txstatus(node, payment, wanted):
        answer = eventually(lambda: node.request('transactionstatus',txid=payment['txid'],txhash=payment['txhash'],wire=payment['wire']), lambda s: s.get('state') == wanted, 'transaction did not become '+wanted+' on '+node.label)
        require(answer['txid'] == payment['txid'] and answer['txhash'] == payment['txhash'], 'transaction identity mismatch')
        check('transaction-'+wanted,node=node.label,response=answer)
        return answer
    try:
        a = launch('a',root/'home-a',[])
        b = launch('b',root/'home-b',[a.ready['listen']])
        c = launch('c',root/'home-c',[b.ready['listen']])
        for node, count in ((a,1),(b,2),(c,1)):
            eventually(lambda: status(node),lambda s:s['peer_active']==count,'A-B-C topology activation')
        wa = root/'wallet-a'
        created = call(a,wa,'create')
        script, policy = compile_payment(created['public_key'])
        call(a,wa,'register',dict(script=script,proof=[],root=policy))
        info = call(a,wa,'info'); destination = info['payment_output_hex']
        funding = []
        for _ in range(2):
            answer,_ = mine(a,destination,(b,c),0)
            funding.append(answer)
        for _ in range(manifest['coinbase_maturity']): mine(a,destination,(b,c),0)
        for answer in funding:
            call(a,wa,'track',dict(prev_txid=answer['coinbase_txid'],prev_index=0))
        balances = call(a,wa,'reconcile')
        require(sum(int(x['value']) for x in balances['coins'] if x['present'] and x['mature']) == sum(int(x['coinbase_value']) for x in funding),'funded wallet balance differs from native coinbase outputs')
        require(all(int(x['coinbase_value']) > 22000 for x in funding),'funding claim insufficient for two independent wallet payments')
        # Snapshot only stopped native homes and a closed SQLite wallet.
        c.stop(); shutil.copytree(root/'home-c',root/'fork-home')
        shutil.copytree(wa,root/'fork-wallet')
        c = launch('c-resume',root/'home-c',[b.ready['listen']])
        baseline = {n.label:status(n) for n in (a,b,c)}
        recipient = dict(info['payment_output'],value='10000')
        payments = [call(a,wa,'pay',dict(recipient=recipient,fee='1000')) for _ in range(2)]
        require(len({v['txid'] for v in payments}) == 2,'two distinct payments required')
        for payment in payments:
            require(payment['submission'] in ('accepted','duplicate'),'wallet submission not accepted')
            for node in (a,b,c): txstatus(node,payment,'pending')
        for node in (a,b,c):
            current=status(node); old=baseline[node.label]
            require(current['peer_active']==old['peer_active'] and current['peer_activations']==old['peer_activations'],'multiple relay actions disconnected/reconnected a peer')
        pending=call(a,wa,'pending')
        require(set(pending['pending']) == {v['txid'] for v in payments},'durable pending payments missing')
        # Reopen node A and wallet, rebroadcast persisted exact bytes.
        a.stop(); a=launch('a-restart',root/'home-a',[])
        b.stop(); b=launch('b-reconnect',root/'home-b',[a.ready['listen']])
        c.stop(); c=launch('c-reconnect',root/'home-c',[b.ready['listen']])
        for payment in payments:
            exported=call(a,wa,'export',dict(txid=payment['txid'],max_bytes=1000000))
            require(all(exported[k]==payment[k] for k in ('wire','txid','txhash')),'restart changed persisted signed bytes')
            call(a,wa,'broadcast',dict(txid=payment['txid']))
            txstatus(c,payment,'pending')
        confirmation,confirmed=mine(c,destination,(a,b),2)
        for payment in payments:
            for node in (a,b,c):
                state=txstatus(node,payment,'confirmed')
                require(state['block_id']==confirmation['block_id'],'wrong payment confirmation block')
            require(call(a,wa,'status',dict(txid=payment['txid']))['state']=='confirmed','wallet did not observe confirmation')
            coin=a.request('coin',txid=payment['txid'],index=0)
            require(coin['coin'] is not None,'confirmed recipient output missing')
            check('confirmed-recipient-output',txid=payment['txid'],coin=coin)
        call(a,wa,'reconcile')
        # Partition at the saved common ancestor. The competing wallet signs a
        # real conflicting spend; C mines it from its pool, never supplied wires.
        for node in (a,b,c): node.stop()
        c=launch('c-fork',root/'fork-home',[])
        conflict=call(c,root/'fork-wallet','pay',dict(recipient=dict(recipient,value='11000'),fee='1000'))
        txstatus(c,conflict,'pending')
        _,fork=mine(c,destination,selected=1,branch=1)
        while fork['height'] <= confirmed['height']+1:
            _,fork=mine(c,destination,selected=0,branch=1)
        b=launch('b-reorg',root/'home-b',[c.ready['listen']])
        a=launch('a-reorg',root/'home-a',[b.ready['listen']])
        same((a,b),fork)
        states=[]
        for payment in payments:
            observed=eventually(lambda:a.request('transactionstatus',txid=payment['txid'],txhash=payment['txhash'],wire=payment['wire']),lambda s:s.get('state') in ('pending','conflicted'),'detached transaction reconciliation')
            wallet_state=call(a,wa,'status',dict(txid=payment['txid']))
            require(wallet_state['state']==observed['state'],'wallet/node reorg status mismatch')
            states.append(observed['state'])
            check('detached-payment',response=observed,wallet=wallet_state)
        require('conflicted' in states,'competing confirmed spend did not conflict original payment')
        txstatus(a,conflict,'confirmed')
        call(a,wa,'reconcile')
        record['passed']=True; record['final']=fork; save()
    except Exception as error:
        record['failure']=dict(kind=type(error).__name__,error=str(error)); raise
    finally:
        errors=[]
        for node in reversed(nodes):
            try: node.stop()
            except Exception as error: errors.append(str(error))
        record['cleanup']=[dict(label=n.label,pid=n.process.pid,exit=n.process.poll()) for n in nodes]
        record['cleanup_errors']=errors
        if errors: record['passed']=False
        save()
        require(not errors,'native child cleanup failed '+str(errors))
    print('Three native nodes/private wallet relay passed:',root)


if __name__ == '__main__':
    main()
