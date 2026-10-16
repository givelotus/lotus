"""Explicitly gated native operator acceptance via unmodified public commands.

Set LOTUS_V2_APPROVED_OPERATOR to a root-approved pinned JSON specification.
This is a same-host, independent-session gate; it makes no Avalanche finality
or separate-machine deployment claim. Every home and listener is isolated.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import secrets
import socket
import sys
import time
import unittest


@unittest.skipUnless(os.environ.get('LOTUS_V2_APPROVED_OPERATOR'), 'native operator gate requires approved pinned specification')
class NativeOperatorFlowTests(unittest.TestCase):
    def test_independent_sessions_public_recipient_payment_resume_and_reorg(self):
        spec = json.loads(Path(os.environ['LOTUS_V2_APPROVED_OPERATOR']).read_bytes())
        module_spec = importlib.util.spec_from_file_location('native_operator_controller', Path(__file__).parents[1] / 'controller.py')
        api = importlib.util.module_from_spec(module_spec)
        module_spec.loader.exec_module(api)
        root = Path(spec['output'])
        self.assertTrue(root.is_absolute())
        self.assertEqual(root, root.resolve())
        self.assertFalse(root.exists())
        root.mkdir(mode=0o700)
        evidence = dict(schema=1, passed=False,
                        scope='same-host independent controller sessions; Avalanche OFF; no separate-machine/finality claim',
                        controller_sha256=api.sha256_file(Path(api.__file__)),
                        inputs=spec, commands=[])
        controllers = []
        def save():
            (root / 'evidence.json').write_text(json.dumps(evidence, indent=2) + '\n')
        def pinned(name):
            path = Path(spec[name]['path'])
            self.assertEqual(api.sha256_file(path), spec[name]['sha256'])
            return dict(path=str(path), sha256=spec[name]['sha256'])
        inputs = {name: pinned(name) for name in ('manifest', 'daemon', 'wallet_client')}
        manifest = json.loads(Path(inputs['manifest']['path']).read_bytes())
        used_ports = set()
        def port():
            while True:
                with socket.socket() as stream:
                    stream.bind(('127.0.0.1', 0))
                    value = stream.getsockname()[1]
                if value not in used_ports and value not in (10604, 10605, 8331):
                    used_ports.add(value)
                    return value
        ports = {name: dict(p2p=port(), chronik=port()) for name in ('sender', 'receiver')}
        config_paths = {}
        limits = dict(deadline_ms=60000, max_line_bytes=1048576,
                      max_wallet_bytes=4194304, max_events=256, max_blocks=256, max_batches=4096)
        for name in ports:
            network = dict(schema=1, magic='76327233',
                           listen=dict(address='127.0.0.1', port=ports[name]['p2p']),
                           connect=[dict(address='127.0.0.1', port=ports['receiver']['p2p'])] if name == 'sender' else [],
                           receive_limit=max(manifest['block_read_limit'], 1048576),
                           local_policy='bounded-local-v1', chronik_bind=f"127.0.0.1:{ports[name]['chronik']}")
            network_path = root / (name + '-network.json')
            api.Controller._write_new(network_path, api.encode_json(network) + b'\n')
            config = dict(schema=1, **inputs, compiler=spec['compiler'], limits=limits,
                          nodes=[dict(name=name, home='nodes/local', connect_to=[],
                                      network=dict(path=str(network_path), sha256=api.sha256_file(network_path)),
                                      chronik=dict(url=f"http://127.0.0.1:{ports[name]['chronik']}",
                                                   chain_id=spec['identity'][0], profile_id=spec['identity'][2]))])
            config_paths[name] = root / (name + '-config.json')
            api.Controller._write_new(config_paths[name], api.encode_json(config) + b'\n')
        secret = secrets.token_hex(32).encode()
        def start(name, resume=False):
            ctl = api.Controller(api.load_config(config_paths[name]), root / (name + '-session'),
                                 secret_prompt=lambda *_: bytearray(secret), resume=resume)
            controllers.append(ctl)
            ctl.start()
            self.assertEqual(ctl._record['identity'], spec['identity'])
            return ctl
        def execute(ctl, command):
            result = ctl.execute(command)
            evidence['commands'].append(dict(session=str(ctl.session), command=command, response=result))
            save()
            self.assertTrue(result.get('ok'), result)
            return result
        def status(ctl):
            return execute(ctl, 'status')['nodes'][ctl.config['nodes'][0]['name']]
        def wait(predicate, reason):
            end = time.monotonic() + 30
            while True:
                if predicate():
                    return
                self.assertLess(time.monotonic(), end, reason)
                time.sleep(.05)
        def mine(ctl, wallet):
            height = status(ctl)['height']
            clock = manifest['header']['time'] + (int(height) + 1) * manifest['header']['spacing']
            return execute(ctl, f'mine 1 --to {wallet} --claim 100000 --time {clock} --batches 16')['mined'][0]
        try:
            sender, receiver = start('sender'), start('receiver')
            wait(lambda: status(sender)['peer_active'] >= 1 and status(receiver)['peer_active'] >= 1,
                 'explicit private P2P peers did not connect')
            execute(sender, 'wallet create alice')
            execute(receiver, 'wallet create bob')
            execute(receiver, 'wallet create miner')
            for _ in range(manifest['coinbase_maturity'] + 1):
                mine(sender, 'alice')
            ancestor = status(sender)['tip']
            wait(lambda: status(receiver)['tip'] == ancestor, 'funding blocks did not relay')
            descriptor = root / 'bob-recipient.json'
            exported = execute(receiver, f'recipient export bob --output {descriptor}')
            imported = execute(sender, f'recipient import bob-remote --file {descriptor}')
            self.assertEqual(exported['sha256'], imported['sha256'])
            before = status(sender)['tip']
            submitted = execute(sender, 'wallet pay alice --to-recipient bob-remote --amount 10000 --fee 1000')['data']
            txid = submitted['txid']
            evidence['txid'] = txid
            self.assertEqual(status(sender)['tip'], before, 'wallet pay mined a block')
            self.assertFalse((sender.session / 'wallets/bob-remote').exists())
            # Stop the sender at the common ancestor. The receiver independently mines
            # the relayed payment, while its native pool remains live.
            execute(sender, 'stop')
            confirmation = mine(receiver, 'miner')
            self.assertEqual(confirmation['pool_selected'], 1)
            receipt = execute(receiver, 'wallet reconcile bob')['data']
            received = [coin for coin in receipt['coins'] if coin['prev_txid'] == txid]
            self.assertEqual(len(received), 1)
            self.assertTrue(received[0]['present'])
            self.assertEqual(received[0]['value'], '10000')
            evidence['confirmation_block'] = confirmation['block_id']
            execute(receiver, 'stop')
            # Clean reopen of the sender retains wallet history but starts a fresh
            # native pool. Mine a longer branch while the other peer is offline.
            sender = start('sender', resume=True)
            self.assertEqual(status(sender)['tip'], ancestor)
            for _ in range(3):
                alternative = mine(sender, 'alice')
                self.assertEqual(alternative['pool_selected'], 0)
            winning_tip = status(sender)['tip']
            receiver = start('receiver', resume=True)
            wait(lambda: status(receiver)['tip'] == winning_tip, 'competing branch did not relay after clean resume')
            detached = execute(receiver, 'wallet reconcile bob')['data']
            stale = [coin for coin in detached['coins'] if coin['prev_txid'] == txid]
            self.assertEqual(len(stale), 1)
            self.assertFalse(stale[0]['present'], 'detached receipt remained present')
            state = execute(sender, 'wallet status alice ' + txid)['data']
            self.assertNotEqual(state['state'], 'confirmed')
            evidence['post_reorg_state'] = state
            evidence['winning_tip'] = winning_tip
            # Rebroadcast the original persisted transaction and independently mine.
            execute(sender, 'wallet broadcast alice ' + txid)
            execute(sender, 'stop')
            remine = mine(receiver, 'miner')
            self.assertEqual(remine['pool_selected'], 1)
            reconciled = execute(receiver, 'wallet reconcile bob')['data']
            restored = [coin for coin in reconciled['coins'] if coin['prev_txid'] == txid]
            self.assertTrue(restored[0]['present'])
            execute(receiver, 'stop')
            evidence['reconfirmation_block'] = remine['block_id']
            evidence['passed'] = True
        finally:
            for ctl in reversed(controllers):
                ctl.close()
                self.assertFalse(ctl.cleanup_errors, ctl.cleanup_errors)
                for child in ctl.nodes.values():
                    self.assertIsNotNone(child.process.poll())
            evidence['sessions'] = {name: json.loads((root / (name + '-session/session.json')).read_bytes()) for name in ports}
            save()
