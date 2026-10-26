#!/usr/bin/env python3
"""Actual Chronik -> controller discovery -> native encrypted wallet lifecycle.

Derived from the private relay lifecycle; imports its bounded node transport only.
No caller-supplied outpoint is tracked. Discovery uses real HTTP and native ownership.

Every acceptance assertion uses native authoritative state. Payment bytes enter
only through submittransaction via the wallet's private Unix socket channel.
This development test does not establish Avalanche quorum or mainnet readiness.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import time
import signal


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
    p.add_argument('--run-deadline', type=int, default=180)
    p.add_argument('--node', default='node')
    p.add_argument('--daemon-source', required=True)
    p.add_argument('--wallet-source', required=True)
    p.add_argument('--compiler-source', required=True)
    args = p.parse_args(argv)
    local = local_module()
    require = local.require
    require(1 <= args.timeout <= 60, 'timeout must be 1..60 seconds')
    require(30 <= args.run_deadline <= 600, 'run deadline must be 30..600 seconds')
    for pin in (args.daemon_source, args.wallet_source, args.compiler_source):
        require(local.hex_string(pin, 20), 'full exact source commit required')
    root = args.output.resolve()
    root.mkdir()  # Existing output/home must never be reused or reset.
    manifest = json.loads(args.manifest.read_text())
    require(manifest['schema'] == 2, 'absolute monetary schema 2 manifest required')
    require(2 <= manifest['coinbase_maturity'] <= 16, 'bounded maturity fixture required')
    (root/'manifest.json').write_bytes(args.manifest.read_bytes())
    (root/'public').mkdir(mode=0o700)
    daemon, wallet = args.daemon.resolve(), args.wallet_client.resolve()
    compiler = args.compiler.resolve()
    record = dict(schema='lotus-v2/wallet-discovery-live-check/1', passed=False,
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
        require(local.digest(daemon)==record['daemon_sha256'],'daemon changed before launch')
        config = root/(label+'.network.json')
        config.write_text(json.dumps(dict(schema=1, magic='76327233',
            listen=dict(address='127.0.0.1', port=0), connect=peers,
            receive_limit=max(manifest['block_read_limit'], 1048576), local_policy='bounded-local-v1', chronik_bind='127.0.0.1:0'))+'\n')
        node = local.Node(label, daemon, root/'manifest.json', home, config, root, args.timeout)
        nodes.append(node); node.await_ready()
        port=int(node.ready['chronik_address'].split(':')[1])
        require(port not in local.FORBIDDEN_PORTS and port > 0,'forbidden Chronik port')
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
    # The process driver is reused only for bounded JSONL transport. Every wallet
    # operation, HTTP discovery and private FD bridge uses the actual controller.
    controller_path = Path(__file__).parents[2]/'tools/lotus-v2-devnet/controller.py'
    spec = importlib.util.spec_from_file_location('discovery_live_controller', controller_path)
    import sys
    controller = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = controller
    spec.loader.exec_module(controller)
    record['controller_sha256'] = local.digest(controller_path)
    record['discovery_sha256'] = local.digest(controller_path.with_name('chronik_discovery.py'))
    record['integration_source'] = subprocess.check_output(['git','rev-parse','HEAD'],cwd=Path(__file__).parents[2],text=True).strip()
    class Adapter:
        def __init__(self,node):
            self.native=node; self.name=node.label; self.ready=node.ready
        def request(self,payload,deadline):
            payload=dict(payload); command=payload.pop('command')
            return self.native.request(command,wait_timeout=controller.remaining(deadline),**payload)
    def call(node, home, command, payload=None):
        require(local.digest(wallet)==record['wallet_sha256'],'wallet changed before invocation')
        binding=dict(url='http://'+node.ready['chronik_address'],chain_id=node.ready['chain_id'],profile_id=node.ready['profile_digest'])
        limits=dict(deadline_ms=int(args.timeout*1000),max_line_bytes=8388608,max_wallet_bytes=4194304,max_events=32,max_blocks=16,max_batches=8)
        ctl=controller.Controller(dict(nodes=[dict(name=node.label,chronik=binding)],limits=limits),root,
            secret_prompt=lambda *_:bytearray(b'isolated-public-test-passphrase'))
        ctl.started=True
        ctl.wallet_nodes={'wallet':node.label,'recipient':node.label}
        adapter=Adapter(node)
        ctl._wallet=lambda name,allow_new=False: controller.WalletProcess(wallet,root/'manifest.json',wc if name=='recipient' else home,adapter,limits)
        deadline=ctl.deadline()
        if command in ('reconcile','discover','prepare','sign','pay'):
            if command in ('reconcile','discover'):
                line='wallet balance wallet'
            else:
                line=f"wallet {command} wallet --to recipient --amount {payload['recipient']['value']} --fee {payload['fee']}"
            response=ctl.execute(line)
            require(response.get('ok') is True,'controller public command failed '+str(response))
            value=response['data']
            check('controller-public-command',node=node.label,command=line,response=response)
        else:
            value=ctl._invoke('wallet',command,payload or {},deadline,command=='create')
        check('wallet-'+command,node=node.label,home=str(home),request=payload or {},response=value)
        return value
    def compile_payment(public_key):
        require(local.digest(compiler/'dist/generic.js')==record['compiler_sha256'],'compiler changed before invocation')
        source = compiler/'examples/gallery/payment.lotus'
        js = "import {readFileSync} from 'node:fs';const {compileContract}=await import(process.argv[1]); console.log(JSON.stringify(compileContract(readFileSync(process.argv[2],'utf8'),{contract:'Payment',bindings:{Payment:{owner:process.argv[3]}}})));"
        answer = subprocess.run([args.node,'--input-type=module','-e',js,(compiler/'dist/generic.js').as_uri(),str(source),public_key], capture_output=True,text=True,timeout=args.timeout)
        require(answer.returncode == 0, answer.stderr)
        artifact = json.loads(answer.stdout)
        (root/('payment-artifact-'+public_key+'.json')).write_text(json.dumps(artifact,indent=2)+'\n')
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
    def expired(_signal, _frame):
        raise TimeoutError('overall native discovery acceptance deadline exceeded')
    signal.signal(signal.SIGALRM,expired)
    signal.alarm(args.run_deadline)
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
        wc = root/'wallet-c-recipient'
        recipient_created = call(c,wc,'create')
        recipient_script, recipient_root = compile_payment(recipient_created['public_key'])
        call(c,wc,'register',dict(script=recipient_script,proof=[],root=recipient_root))
        recipient_info = call(c,wc,'info')
        require(recipient_info['public_key'] != info['public_key'], 'recipient must have an independent native wallet key')
        funding = []
        for _ in range(2):
            answer,_ = mine(b,destination,(a,c),0)
            funding.append(answer)
        sink = destination.replace(policy, 'ab'*32)
        require(sink != destination, 'distinct unfunded miner destination required')
        for _ in range(manifest['coinbase_maturity']): mine(b,sink,(a,c),0)
        require(call(a,wa,'reconcile')['confirmed_discovery']['candidate_count']==2,'external funding not automatically discovered')
        balances = call(a,wa,'reconcile')
        require(sum(int(x['value']) for x in balances['coins'] if x['present'] and x['mature']) == sum(int(x['coinbase_value']) for x in funding),'funded wallet balance differs from native coinbase outputs')
        require(all(int(x['coinbase_value']) > 22000 for x in funding),'funding claim insufficient for two independent wallet payments')
        # Snapshot only stopped native homes and a closed SQLite wallet.
        c.stop(); shutil.copytree(root/'home-c',root/'fork-home')
        shutil.copytree(wa,root/'fork-wallet')
        c = launch('c-resume',root/'home-c',[b.ready['listen']])
        baseline = {n.label:status(n) for n in (a,b,c)}
        recipient = dict(recipient_info['payment_output'],value='10000')
        prepared=call(a,wa,'prepare',dict(recipient=recipient,fee='1000'))
        check('controller-prepare',response=prepared)
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
        confirmation,confirmed=mine(c,sink,(a,b),2)
        for payment in payments:
            for node in (a,b,c):
                state=txstatus(node,payment,'confirmed')
                require(state['block_id']==confirmation['block_id'],'wrong payment confirmation block')
            require(call(a,wa,'status',dict(txid=payment['txid']))['state']=='confirmed','wallet did not observe confirmation')
            coin=a.request('coin',txid=payment['txid'],index=0)
            require(coin['coin'] is not None,'confirmed recipient output missing')
            check('confirmed-recipient-output',txid=payment['txid'],coin=coin)
        def tracked(state, txid, index):
            matches = [coin for coin in state['coins'] if coin['prev_txid'] == txid and int(coin['prev_index']) == index]
            require(len(matches) == 1, 'wallet must track exactly one requested outpoint')
            return matches[0]
        def present_total(state):
            return sum(int(coin['value']) for coin in state['coins'] if coin['present'])
        sender_confirmed = call(a,wa,'reconcile')
        recipient_confirmed = call(c,wc,'reconcile')
        for payment in payments:
            received = tracked(recipient_confirmed,payment['txid'],0)
            change = tracked(sender_confirmed,payment['txid'],1)
            require(received['present'] and received['mature'] and not received['reserved'] and received['value'] == '10000', 'recipient confirmed output/value differs')
            require(change['present'] and change['mature'] and not change['reserved'] and int(change['value']) in [int(coin['coinbase_value'])-11000 for coin in funding], 'sender confirmed change/value differs')
        require(present_total(recipient_confirmed) == 20000 and present_total(sender_confirmed) == sum(int(coin['coinbase_value']) for coin in funding)-22000, 'independent wallet confirmed balance arithmetic differs')
        check('independent-wallet-confirmed-balances',sender=sender_confirmed,recipient=recipient_confirmed)
        # Partition at the saved common ancestor. The competing wallet signs a
        # real conflicting spend; C mines it from its pool, never supplied wires.
        for node in (a,b,c): node.stop()
        c=launch('c-fork',root/'fork-home',[])
        conflict=call(c,root/'fork-wallet','pay',dict(recipient=dict(recipient,value='11000'),fee='1000'))
        txstatus(c,conflict,'pending')
        _,fork=mine(c,sink,selected=1,branch=1)
        while fork['height'] <= confirmed['height']+1:
            _,fork=mine(c,sink,selected=0,branch=1)
        b=launch('b-reorg',root/'home-b',[c.ready['listen']])
        a=launch('a-reorg',root/'home-a',[b.ready['listen']])
        same((a,b),fork)
        detached=a.request('blockstatus',block_id=confirmation['block_id'])
        require(detached.get('ever_connected') is True and detached.get('is_active_tip') is False,'original confirmation block lacks native detach evidence')
        check('confirmation-block-detached',response=detached)
        states=[]
        detached_pending=[]
        for payment in payments:
            observed=eventually(lambda:a.request('transactionstatus',txid=payment['txid'],txhash=payment['txhash'],wire=payment['wire']),lambda s:s.get('state') in ('pending','conflicted'),'detached transaction reconciliation')
            wallet_state=call(a,wa,'status',dict(txid=payment['txid']))
            require(wallet_state['state']==observed['state'],'wallet/node reorg status mismatch')
            states.append(observed['state'])
            if observed['state'] == 'pending': detached_pending.append(payment)
            check('detached-payment',response=observed,wallet=wallet_state)
        require('conflicted' in states,'competing confirmed spend did not conflict original payment')
        txstatus(a,conflict,'confirmed')
        sender_detached = call(a,wa,'reconcile')
        recipient_detached = call(c,wc,'reconcile')
        require(present_total(recipient_detached) == 11000, 'recipient retained detached received balance')
        for payment in payments:
            require(not tracked(recipient_detached,payment['txid'],0)['present'], 'detached recipient output remains present')
            require(not tracked(sender_detached,payment['txid'],1)['present'], 'detached sender change remains present')
        require(present_total(sender_detached) == sum(int(coin['coinbase_value']) for coin in funding)-12000, 'sender reorg balance did not restore unspent original funding')
        require(len(detached_pending) == 1, 'one valid detached payment must remain pending')
        remine_payment = detached_pending[0]
        txstatus(c,remine_payment,'pending')
        remined,remined_state = mine(c,sink,(a,b),selected=1,branch=1)
        for node in (a,b,c):
            confirmed_again=txstatus(node,remine_payment,'confirmed')
            require(confirmed_again['block_id'] == remined['block_id'], 'detached payment did not confirm in new native pool block')
        require(call(a,wa,'status',dict(txid=remine_payment['txid']))['state'] == 'confirmed', 'sender wallet failed to observe re-mined confirmation')
        sender_remined = call(a,wa,'reconcile')
        recipient_remined = call(c,wc,'reconcile')
        received = tracked(recipient_remined,remine_payment['txid'],0)
        change = tracked(sender_remined,remine_payment['txid'],1)
        require(received['present'] and received['mature'] and not received['reserved'] and received['value'] == '10000', 'recipient wallet failed to restore re-mined received output')
        require(change['present'] and change['mature'] and not change['reserved'] and int(change['value']) in [int(coin['coinbase_value'])-11000 for coin in funding], 'sender wallet failed to restore re-mined change')
        require(present_total(recipient_remined) == 21000 and present_total(sender_remined) == present_total(sender_detached)-11000, 're-mined independent wallet balance arithmetic differs')
        for payment in payments:
            if payment not in detached_pending:
                require(call(a,wa,'status',dict(txid=payment['txid']))['state'] == 'conflicted', 'conflicting original payment lost its conflict status')
                require(not tracked(recipient_remined,payment['txid'],0)['present'], 'conflicting original recipient output reappeared')
        check('detached-payment-remined-wallet-balances',block_id=remined['block_id'],sender=sender_remined,recipient=recipient_remined)
        record['passed']=True; record['final']=remined_state; save()
    except Exception as error:
        record['failure']=dict(kind=type(error).__name__,error=str(error)); raise
    finally:
        signal.alarm(0)
        errors=[]
        for node in reversed(nodes):
            try: node.stop()
            except Exception as error: errors.append(str(error))
        record['cleanup']=[dict(label=n.label,pid=n.process.pid,exit=n.process.poll()) for n in nodes]
        record['cleanup_errors']=errors
        if errors: record['passed']=False
        save()
        require(not errors,'native child cleanup failed '+str(errors))
    print('Three native nodes/controller discovery wallet lifecycle passed:',root)


if __name__ == '__main__':
    main()
