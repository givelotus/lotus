"""Operator contract tests using transport fixtures; no native consensus claims."""
import copy
import json
import os
from pathlib import Path
import time
from unittest import mock

from test_controller import ControllerCase
import test_interactive_flow as flows
from test_interactive_flow import pinned


class OperatorTests(ControllerCase):
    make_controller = flows.CommandFlowTests.make_controller
    def tearDown(self):
        for controller in getattr(self, "controllers", []):
            controller.close()
        super().tearDown()

    def info(self):
        return dict(chain_id='00'*32, genesis_id='33'*32, profile_digest='44'*32,
                    public_key='55'*32, payment_policy_registered=True,
                    payment_output=dict(flags=0, value='0', branches=['88'*32], paths=[[0]]))

    def descriptor(self):
        info = self.info()
        info.pop('payment_policy_registered')
        return dict(schema=1, kind='lotus-v2-payment-recipient', **info)

    def closed_session(self):
        ctl, config_path = self.make_controller()
        for name, node in [('alice', 'left'), ('bob', 'right')]:
            self.assertTrue(ctl.execute(f'wallet create {name} --node {node}')['ok'])
        ctl.close()
        record = json.loads((ctl.session / 'session.json').read_bytes())
        self.assertEqual(record['lifecycle'], 'stopped')
        return ctl, config_path

    def resume(self, ctl, config_path):
        resumed = self.api.Controller(self.api.load_config(config_path), ctl.session, resume=True)
        native = resumed._invoke
        def invoke(name, command, *args, **kwargs):
            result = native(name, command, *args, **kwargs)
            if command == 'info':
                result.update(self.info())
            return result
        resumed._invoke = invoke
        self.controllers.append(resumed)
        return resumed

    def test_resume_retains_multiple_bindings_and_generation_networks(self):
        ctl, config_path = self.closed_session()
        original = (ctl.session / 'network/right.json').read_bytes()
        resumed = self.resume(ctl, config_path)
        before = (ctl.session / 'session.json').read_bytes()
        resumed.check_resume()
        self.assertEqual(before, (ctl.session / 'session.json').read_bytes())
        resumed.start()
        self.assertEqual(resumed.wallet_nodes, {'alice': 'left', 'bob': 'right'})
        self.assertEqual(resumed._wallet('bob').node.name, 'right')
        self.assertEqual(original, (ctl.session / 'network/right.json').read_bytes())
        self.assertTrue((ctl.session / 'network/right-2.json').exists())
        resumed.close()
        self.assertEqual(json.loads((ctl.session / 'session.json').read_bytes())['generation'], 2)

    def test_lock_is_exclusive_and_never_unlinked(self):
        ctl, path = self.make_controller()
        foreign = self.api.Controller(ctl.config, ctl.session, resume=True)
        with self.assertRaises(self.api.ControllerError):
            foreign._acquire_lock()
        self.assertIsNone(foreign._lock_fd)
        self.assertFalse(foreign.nodes)
        lock = ctl.session / 'session.lock'
        inode = lock.stat().st_ino
        ctl.close()
        self.assertEqual(inode, lock.stat().st_ino)

    def test_resume_refuses_drift_missing_home_old_live_and_symlinks_without_changes(self):
        ctl, path = self.closed_session()
        metadata = ctl.session / 'session.json'
        original = metadata.read_bytes()
        record = json.loads(original)
        variants = [dict(record, schema=1), dict(record, lifecycle='running'),
                    dict(record, lifecycle='starting'), dict(record, node_sha256='00'*32),
                    dict(record, config={}), dict(record, identity=['00'*32])]
        for variant in variants:
            metadata.write_text(json.dumps(variant))
            before = metadata.read_bytes()
            with self.assertRaises(self.api.ControllerError):
                self.resume(ctl, path).check_resume()
            self.assertEqual(before, metadata.read_bytes())
        metadata.write_bytes(original)
        home = ctl.session / 'nodes/right'
        home.rmdir()
        with self.assertRaises(self.api.ControllerError):
            self.resume(ctl, path).check_resume()
        home.symlink_to(ctl.session / 'nodes/left', target_is_directory=True)
        with self.assertRaises(self.api.ControllerError):
            self.resume(ctl, path).check_resume()
        home.unlink()
        home.mkdir(mode=0o777)
        home.chmod(0o777)
        with self.assertRaises(self.api.ControllerError):
            self.resume(ctl, path).check_resume()
        home.chmod(0o700)
        compiler = Path(ctl.config['compiler']['directory']) / 'dist/generic.js'
        compiler.write_text('changed')
        with self.assertRaises(self.api.ControllerError):
            self.resume(ctl, path).check_resume()
        self.assertEqual(original, metadata.read_bytes())

    def test_failed_start_and_uncertain_cleanup_never_mark_stopped(self):
        ctl, path = self.closed_session()
        resumed = self.resume(ctl, path)
        with mock.patch.object(self.api.NodeProcess, 'wait_ready', side_effect=self.api.ControllerError('invalid', 'startup')):
            with self.assertRaises(self.api.ControllerError):
                resumed.start()
        self.assertEqual(json.loads((ctl.session / 'session.json').read_bytes())['lifecycle'], 'starting')
        self.assertFalse(any(node.process.poll() is None for node in resumed.nodes.values()))
        self.assertIsNone(resumed._lock_fd)

    def test_wrong_ready_identity_never_accepts_resume(self):
        ctl, path = self.closed_session()
        metadata = ctl.session / 'session.json'
        record = json.loads(metadata.read_bytes())
        record['identity'][0] = '66'*32
        metadata.write_text(json.dumps(record))
        resumed = self.resume(ctl, path)
        with self.assertRaises(self.api.ControllerError):
            resumed.start()
        self.assertEqual(json.loads(metadata.read_bytes())['lifecycle'], 'starting')

    def test_config_native_optional_fields_passthrough_and_rejections(self):
        ctl, path = self.make_controller()
        config = json.loads(path.read_bytes())
        network_path = Path(config['nodes'][0]['network']['path'])
        network = json.loads(network_path.read_bytes())
        network.update(chronik_bind='[::1]:29331', avalanche=dict(credentials=None,
                       initial_download=dict(minimum_height=3, maximum_tip_age_seconds=900)))
        def load(value):
            network_path.write_text(json.dumps(value))
            for node in config['nodes']:
                node['network'] = pinned(network_path)
            path.write_text(json.dumps(config))
            return self.api.load_config(path)
        normalized = load(network)
        self.assertEqual(normalized['nodes'][0]['resolved_network'], network)
        other = self.api.Controller(normalized, self.root / 'optional-session')
        self.controllers.append(other)
        other.start()
        effective = json.loads((other.session / 'network/left.json').read_bytes())
        self.assertEqual(effective['chronik_bind'], network['chronik_bind'])
        self.assertEqual(effective['avalanche'], network['avalanche'])
        other.close()
        for field, value in [('chronik_bind', None), ('chronik_bind', 'localhost:1234'),
                             ('chronik_bind', '[::1]:0'), ('chronik_bind', '0.0.0.0:29331'),
                             ('chronik_bind', '8.8.8.8:29331'), ('chronik_bind', '127.0.0.2:29331'),
                             ('chronik_bind', '127.0.0.1:029331'), ('avalanche', None),
                             ('avalanche', dict(credentials='relative', initial_download={})),
                             ('unknown', 3)]:
            bad = dict(network, **{field: value})
            with self.assertRaises(self.api.ControllerError):
                load(bad)
        for field, value in [('minimum_height', True), ('maximum_tip_age_seconds', 0)]:
            bad = copy.deepcopy(network)
            bad['avalanche']['initial_download'][field] = value
            with self.assertRaises(self.api.ControllerError):
                load(bad)

    def test_recipient_roundtrip_remote_pay_has_no_receiver_or_mining(self):
        ctl, path = self.make_controller("pay-accepted")
        self.assertTrue(ctl.execute('wallet create alice')['ok'])
        native = ctl._invoke
        ctl._invoke = lambda name, command, *args, **kw: (self.info() if command == 'info' else native(name, command, *args, **kw))
        output = self.root / 'recipient.json'
        exported = ctl.execute(f'recipient export alice --output {output}')
        self.assertTrue(exported['ok'], exported)
        self.assertEqual(output.stat().st_mode & 0o777, 0o600)
        imported = ctl.execute(f'recipient import remote --file {output}')
        self.assertTrue(imported['ok'], imported)
        self.assertEqual(exported['sha256'], imported['sha256'])
        self.assertFalse(ctl.execute(f'recipient import remote --file {output}')['ok'])
        self.assertFalse(ctl.execute(f'recipient export alice --output {output}')['ok'])
        before = self.events()
        result = ctl.execute('wallet pay alice --to-recipient remote --amount 10000 --fee 1000')
        self.assertTrue(result['ok'], result)
        events = self.events()[len(before):]
        self.assertFalse(any(event.get('kind') == 'node-request' and event['request']['command'] in ('mineblock', 'minepool') for event in events))
        self.assertFalse((ctl.session / 'wallets/remote').exists())
        self.assertEqual(ctl.wallet_nodes, {'alice': 'left'})

    def test_recipient_validation_before_secret_and_bounded_import(self):
        prompts = []
        ctl, path = self.make_controller(secret_prompt=lambda *args: prompts.append(args))
        descriptor = self.descriptor()
        compiler = ctl._compile
        ctl._compile = lambda key, deadline: (compiler(key, deadline) if key == '55'*32 else dict(root='99'*32))
        candidate = self.root / 'received.json'
        for field, value in [('public_key', '99'*32), ('chain_id', '66'*32), ('passphrase', 'secret'),
                             ('payment_output', dict(flags=0, value='1', branches=['88'*32], paths=[[0]]))]:
            bad = dict(descriptor, **{field: value})
            candidate.write_text(json.dumps(bad))
            self.assertFalse(ctl.execute(f'recipient import remote --file {candidate}')['ok'])
        for data in ('{"schema":1,"schema":1}', '['*100+'0'+']'*100, ' '*16385):
            candidate.write_text(data)
            self.assertFalse(ctl.execute(f'recipient import remote --file {candidate}')['ok'])
        self.assertFalse(ctl.execute('wallet pay alice --to-recipient remote --amount 1 --fee 1')['ok'])
        self.assertEqual(prompts, [])
        self.assertFalse(ctl.execute('wallet pay alice --to bob --to-recipient remote --amount 1 --fee 1')['ok'])

    def test_import_persists_and_check_is_process_free_resume_recompiles(self):
        ctl, config_path = self.closed_session()
        descriptor_path = ctl.session / 'public/recipients/remote.json'
        ctl._write_new(descriptor_path, json.dumps(self.descriptor()).encode())
        resumed = self.resume(ctl, config_path)
        with mock.patch.object(self.api.subprocess, 'Popen', side_effect=AssertionError('check launched child')):
            resumed.check_resume()
        with mock.patch.object(resumed, '_compile', wraps=resumed._compile) as compile_payment:
            resumed.start()
            compile_payment.assert_called_once()
        self.assertEqual(resumed._read_recipient(descriptor_path, resumed.deadline()), self.descriptor())
        bad = self.descriptor()
        bad['payment_output']['branches'] = ['99'*32]
        descriptor_path.write_text(json.dumps(bad))
        prompts = []
        resumed.secret_prompt = lambda *args: prompts.append(args)
        self.assertFalse(resumed.execute('wallet pay alice --to-recipient remote --amount 2 --fee 1')['ok'])
        self.assertEqual(prompts, [])

    def test_remote_unknown_signing_result_reuses_persisted_wire(self):
        from test_controller import TXID
        ctl, config_path = self.make_controller('lost-sign')
        self.assertTrue(ctl.execute('wallet create alice')['ok'])
        descriptor = self.root / 'recipient.json'
        descriptor.write_text(json.dumps(self.descriptor()))
        self.assertTrue(ctl.execute(f'recipient import remote --file {descriptor}')['ok'])
        before = len(self.events())
        answer = ctl.execute('wallet pay alice --to-recipient remote --amount 2 --fee 1')
        self.assertEqual(answer['result'], 'outcome_unknown')
        self.assertEqual(ctl.execute('wallet pending alice')['data']['pending'], [TXID])
        self.assertTrue(ctl.execute('wallet export alice ' + TXID)['ok'])
        events = self.events()[before:]
        self.assertEqual([event['command'] for event in events if event['kind'] == 'wallet-start'], ['pay', 'pending', 'export'])
        self.assertFalse(any(event.get('kind') == 'node-request' and event['request']['command'] in ('mineblock', 'minepool') for event in events))

    def test_alias_file_symlink_or_orphan_wallet_cannot_be_adopted(self):
        ctl, config_path = self.closed_session()
        record = (ctl.session / 'session.json').read_bytes()
        orphan = ctl.session / 'wallets/orphan'
        orphan.mkdir(mode=0o700)
        with self.assertRaises(self.api.ControllerError):
            self.resume(ctl, config_path).check_resume()
        orphan.rmdir()
        link = self.root / 'alias-session'
        link.symlink_to(ctl.session, target_is_directory=True)
        with self.assertRaises(self.api.ControllerError):
            self.api.Controller(ctl.config, link, resume=True).check_resume()
        with self.assertRaises(self.api.ControllerError):
            self.api.Controller(ctl.config, link / '..' / 'session', resume=True)
        self.assertEqual(record, (ctl.session / 'session.json').read_bytes())

    def test_cleanup_failure_is_sticky_and_never_signals_recorded_pid(self):
        ctl, config_path = self.make_controller()
        node = ctl.nodes['right']
        with mock.patch.object(node, 'request', side_effect=KeyboardInterrupt):
            ctl.close()
        self.assertTrue(ctl.cleanup_errors)
        self.assertEqual(json.loads((ctl.session / 'session.json').read_bytes())['lifecycle'], 'running')
        ctl.close()
        self.assertFalse(ctl.cleanup_errors)
        self.assertEqual(json.loads((ctl.session / 'session.json').read_bytes())['lifecycle'], 'running')
        # Metadata deliberately has no PID. An unknown field cannot cause attach/signaling.
        record = json.loads((ctl.session / 'session.json').read_bytes())
        record.update(lifecycle='stopped', pid=os.getpid())
        (ctl.session / 'session.json').write_text(json.dumps(record))
        with mock.patch.object(self.api.os, 'killpg', side_effect=AssertionError('foreign signaling')):
            with self.assertRaises(self.api.ControllerError):
                self.resume(ctl, config_path).check_resume()

    def test_schema_chronik_binding_matches_supported_loopback_endpoints(self):
        import re
        schema = json.loads((Path(__file__).parents[1] / 'config.schema.json').read_bytes())
        self.assertEqual(schema['properties']['nodes']['items']['properties']['chronik'],
                         {'$ref': '#/$defs/discovery_endpoint'})
        binding = schema['$defs']['discovery_endpoint']
        self.assertFalse(binding['additionalProperties'])
        pattern = binding['properties']['url']['pattern']
        for url in ('http://127.0.0.1:29331', 'http://127.0.1.2:65535/', 'http://[::1]:1'):
            self.assertTrue(re.fullmatch(pattern, url))
            self.api.discovery_endpoint(dict(url=url, chain_id='00'*32, profile_id='44'*32))
        for url in ('http://127.0.0.1:0', 'http://127.0.0.1:65536', 'http://localhost:29331',
                    'http://127.999.0.1:29331', 'http://user@127.0.0.1:29331'):
            self.assertFalse(re.fullmatch(pattern, url))
