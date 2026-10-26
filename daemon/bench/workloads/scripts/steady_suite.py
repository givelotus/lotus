"""Untimed funding/signing adapter around immutable legacy/native tx builders."""
from decimal import Decimal
import http.client
import hashlib
import importlib
import json
import math
import os
from pathlib import Path
import resource
import re
import subprocess
import threading
import time

from steady_ingestion import DiskFixture, measure, measure_reads, submit
from network_observation import NetworkObservation, inventory_digest, wait_for_sizes


def observe_after_ingestion(clients, memory_snapshot, ingestion_end, emit,
                            clock=time.perf_counter, sleep=time.sleep):
    """Four bounded read-only observations; never extend ingestion timing."""
    observations = []
    for offset in (0, 5, 15, 30):
        delay = ingestion_end + offset - clock()
        if delay > 0:
            sleep(delay)
        began = clock()
        row = {'target_seconds_after_ingestion': offset,
               'actual_started_seconds_after_ingestion': began - ingestion_end,
               'nodes': [{'node': index, 'mempool': client.call('getmempoolinfo')}
                         for index, client in enumerate(clients)],
               'memory': memory_snapshot()}
        row['actual_finished_seconds_after_ingestion'] = clock() - ingestion_end
        observations.append(row)
        emit(list(observations))
    return observations


def legacy_fixture_signer(key):
    """Regtest key42 only: cache nonce points, as the frozen native fixture does.

    Repeated nonces expose the key. This is deliberately unsuitable for wallets;
    the public deterministic benchmark key never holds real funds.
    """
    module = importlib.import_module(type(key).__module__)
    secret = int.from_bytes(key.get_bytes(), 'big')
    if secret != 42:
        raise ValueError('Fast fixture signer accepts only public regtest secret42')
    public = key.get_pubkey()
    public_bytes = public.get_bytes()
    nonces = []
    for index in range(1, 17):
        nonce = (secret * 1000003 + index * 9176) % module.SECP256K1_ORDER
        point = module.SECP256K1.affine(module.SECP256K1.mul([(module.SECP256K1_G, nonce)]))
        if module.jacobi_symbol(point[1], module.SECP256K1.p) == -1:
            nonce = module.SECP256K1_ORDER - nonce
        nonces.append((nonce, point[0].to_bytes(32, 'big')))

    class Signer:
        index = 0

        def sign_schnorr(self, message):
            nonce, rx = nonces[self.index % len(nonces)]
            self.index += 1
            challenge = int.from_bytes(hashlib.sha256(rx + public_bytes + message).digest(), 'big')
            scalar = (nonce + challenge * secret) % module.SECP256K1_ORDER
            return rx + scalar.to_bytes(32, 'big')

    signer = Signer()
    for index in range(16):
        message = hashlib.sha256(bytes([index])).digest()
        if not public.verify_schnorr(signer.sign_schnorr(message), message):
            raise ValueError('Fixture signer failed frozen verifier negative gate')
    return signer


def fixture_budget(pilot_count, pilot_seconds, batch_size, max_transactions, exact_count=None, minimum_supply_seconds=7.5):
    if not math.isfinite(minimum_supply_seconds) or not 6.0 <= minimum_supply_seconds <= 15.0:
        raise ValueError('Predicted supply cushion must be finite and between6 and15seconds')
    if pilot_count <= 0 or pilot_seconds <= 0 or batch_size <= 0 or max_transactions <= 0:
        raise ValueError('Invalid pilot result')
    try:
        rate = pilot_count / pilot_seconds
        finite = math.isfinite(rate) and math.isfinite(rate * 15.0 + 16 * batch_size)
    except (OverflowError, TypeError):
        raise ValueError('Pilot rate is nonfinite or overflows') from None
    if not finite or rate <= 0:
        raise ValueError('Pilot rate is nonfinite or overflows')
    # Three times the measured window accommodates a noisy short sizing pilot.
    # Unused rows are never included in accepted counts or timed throughput.
    preferred = math.ceil((rate * 15.0 + 16 * batch_size) / batch_size) * batch_size
    minimum = math.ceil((rate * minimum_supply_seconds + 16 * batch_size) / batch_size) * batch_size
    capacity = (max_transactions // batch_size) * batch_size
    if capacity < minimum:
        raise ValueError(f'Pilot needs at least {minimum} distinct transactions (rate={rate:.1f}/s); '
                         f'budget is {max_transactions}; refusing short or duplicate work')
    if exact_count is not None:
        if (not isinstance(exact_count, int) or isinstance(exact_count, bool)
                or exact_count > capacity or exact_count < minimum
                or exact_count % batch_size):
            raise ValueError(f'Exact fixture count must be batch-aligned and within [{minimum}, {capacity}]')
        return exact_count
    return min(preferred, capacity)


def fixed_diagnostic_budget(count, batch_size, maximum):
    if (not isinstance(count, int) or isinstance(count, bool) or count > maximum
            or batch_size <= 0 or count % batch_size or count <= 16 * batch_size):
        raise ValueError('Fixed diagnostic corpus must be batch-aligned, bounded, and exceed warmup')
    return count


def batch_rpc_available(client, evidence=None):
    # ABC help for unknown methods can succeed with an error *string*.
    try:
        reply = client.call('help', ['submitrawtxbatch'])
    except RuntimeError:
        return False
    if evidence is not None:
        evidence['help_response'] = reply
    return isinstance(reply, str) and reply.startswith('submitrawtxbatch ')


def funding_fanout_width(source, native):
    if not native:
        return 1000
    text = (Path(source) / 'src/consensus/consensus.h').read_text()
    match = re.search(r'MAX_V2_TX_OUTPUTS\s*=\s*(\d+)\s*;', text)
    if match is None:
        # Early native prefixes use the wire profile before the tighter consensus
        # constant exists. Accept only that source-declared codec/profile pair.
        header = Path(source) / 'src/lotus_v2/transaction.h'
        codec = Path(source) / 'src/primitives/transaction.cpp'
        if header.exists() and codec.exists() and 'lotus::v2::DefaultTxProfile' in codec.read_text():
            match = re.search(
                r'inline\s+constexpr\s+TxProfile\s+DefaultTxProfile\s*\{\s*\d+\s*,\s*(\d+)\s*,',
                header.read_text())
    if match is None or int(match.group(1)) < 1:
        raise ValueError('Native funding requires an explicit positive output bound')
    return min(1000, int(match.group(1)))


def run_suite(context, series, max_transactions=1200000, fixture_smoke=False,
              case_filter=None, budget_only=False, exact_fixture_count=None, sample_node0_output=None, diagnostic_fixed_work=False, minimum_supply_seconds=7.5, progress_every=0, hierarchical_funding=False, fixture_fee_sats=1000, network_observe=False, distributed_injection=False, post_ingestion_observe=False):
    if not isinstance(fixture_fee_sats, int) or not 1000 <= fixture_fee_sats <= 1000000:
        raise ValueError('Fixture fee must be a bounded integer1000..1000000sats')
    if (network_observe or distributed_injection) and (not diagnostic_fixed_work or series != 'v2'):
        raise ValueError('Network observation/distributed injection require native fixed-work diagnostics')
    if distributed_injection and not network_observe:
        raise ValueError('Distributed injection requires explicit network observation')
    if post_ingestion_observe and (not diagnostic_fixed_work or series != 'v2'):
        raise ValueError('Post-ingestion observation requires one native fixed-work case')
    if progress_every and not diagnostic_fixed_work:
        raise ValueError('Completion progress is restricted to fixed-work diagnostics')
    if budget_only and (fixture_smoke or case_filter not in
                        ('single_tx_steady', 'json_rpc_batch50_steady', 'single_tx_loaded_steady',
                         'optrue_batch50_steady', 'signed_batch200_steady')):
        raise ValueError('Budget-only pass permits common ingestion, OP_TRUE batch50 and signed batch200')
    c = context['clients'][0]
    clients = context['clients']
    directory = Path(context['base_dir']) / 'steady-fixtures'
    directory.mkdir()
    results = context['results']
    rpc_failure_lock = threading.Lock()
    rpc_failure_batches = []
    results['workload_definition'] = {
        'track': 'native-bip340-steady-v2' if series == 'v2' else 'legacy-schnorr-steady-v2',
        'target_seconds': 5.0, 'ingestion_workers': 8, 'loaded_reader_workers': 12,
        'fixture_sizing_seconds': 15.0,
        'minimum_predicted_supply_seconds': minimum_supply_seconds,
        'json_rpc_array_size': 50, 'dedicated_batch_sizes': [1, 50, 100, 200, 250, 500, 1000],
        'maxmempool_bytes_per_node': c.call('getmempoolinfo')['maxmempool'], 'warmup_batches_per_worker': 2,
        'public_regtest_secret': 42, 'signature_fixture_distribution': '16 reused deterministic nonce points; intentionally insecure public benchmark key only',
        'historical_legacy_signing_distribution_identical': False,
        'case': case_filter, 'diagnostic_fixed_work': diagnostic_fixed_work,
        'fixture_fee_sats': fixture_fee_sats,
        'unloaded_reader_phase': 'after-pilot-clear-before-final-fixture-and-ingestion',
        'post_ingestion_large_clear_block': False,
        'network_observe': network_observe, 'distributed_injection': distributed_injection,
        'post_ingestion_observe': post_ingestion_observe}
    if network_observe:
        results['node_runtime_configuration'] = [
            {'node': index, 'pid': process.pid,
             'argv': [arg if not arg.startswith(('-rpcpassword=', '-rpcuser='))
                      else arg.split('=', 1)[0] + '=<public-fixture-credential-redacted>'
                      for arg in process.args],
             'network_info': clients[index].call('getnetworkinfo'),
             'peer_info': clients[index].call('getpeerinfo')}
            for index, process in enumerate(context['procs'])]
    # Preparation ceilings can differ by resource allocation; they do not alter
    # the timed RPC protocol. Exhaustion remains a failed measurement.
    results['preparation_limits'] = {
        'fixture_disk_cap_bytes': (16 if budget_only else 512) * 1024 * 1024,
        'max_fixture_transactions': max_transactions,
        'exact_fixture_transactions': exact_fixture_count}
    to_hex = context['ToHex']
    native = series == 'v2'
    legacy_signer = None if native else legacy_fixture_signer(context['privkey'])
    op_script = context['V2_OP_TRUE_SCRIPT'] if native else context['op_true_spk']
    mesh_deadline = time.monotonic() + 30
    while not all(sum(peer.get('version', 0) > 0 for peer in node.call('getpeerinfo')) >= 2
                  for node in clients):
        if time.monotonic() > mesh_deadline:
            raise RuntimeError('Steady suite requires all three nodes to have two negotiated peers')
        time.sleep(0.05)

    def memory_snapshot():
        pids = [str(process.pid) for process in context['procs']]
        client_pid = str(os.getpid())
        rows = subprocess.check_output(['ps', '-o', 'pid=,rss=', '-p',
                                        ','.join(pids + [client_pid])], text=True)
        rss = {line.split()[0]: int(line.split()[1]) for line in rows.splitlines()}
        return {'node_rss_kib': {pid: rss[pid] for pid in pids},
                'benchmark_client_pid': int(client_pid),
                'benchmark_client_current_rss_kib': rss[client_pid],
                'python_peak_rss_platform_units': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                'python_peak_rss_units': 'bytes on macOS; KiB on Linux'}

    class Client:
        def __init__(self, node_index=0):
            self.node_index = node_index
            self.connection = http.client.HTTPConnection(
                '127.0.0.1', context['NODES_CFG'][node_index]['rpc_port'], timeout=180)

        def request(self, payload):
            self.connection.request('POST', '/', json.dumps(payload),
                                    {'Authorization': context['AUTH_HEADER'],
                                     'Content-Type': 'application/json'})
            reply = json.loads(self.connection.getresponse().read())
            for item in reply if isinstance(reply, list) else [reply]:
                if item.get('error'):
                    responses = reply if isinstance(reply, list) else [reply]
                    record = {
                        'utc_ns': time.time_ns(),
                        'request_count': len(payload) if isinstance(payload, list) else 1,
                        'request_sha256': hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest(),
                        'successful_response_count': sum(response.get('error') is None and 'result' in response for response in responses),
                        'successful_txids': [response['result'] for response in responses
                                            if response.get('error') is None and isinstance(response.get('result'), str)],
                        'rejections': [{'id': response.get('id'), 'error': response['error']}
                                       for response in responses if response.get('error')],
                        'interpretation': 'Partial JSON arrays may contain accepted transactions; never count every requested row as accepted.'}
                    with rpc_failure_lock:
                        rpc_failure_batches.append(record)
                        results['failed_rpc_batches'] = list(rpc_failure_batches)
                    raise RuntimeError(str(item['error']))
            return reply

        def call(self, method, params=None):
            return self.request({'jsonrpc': '2.0', 'id': 1,
                                 'method': method, 'params': params or []})['result']

    def mine(count=1):
        if native:
            hashes = c.call('generatetodescriptor', [count, context['V2_OP_TRUE_DESCRIPTOR']])
            context['sync_all_blocks'](clients, base_dir=context['base_dir'])
        else:
            hashes = c.call('generatetoaddress', [count, context['ADDRESS_ECREG_P2SH_OP_TRUE']])
            context['sync_all_blocks'](clients)
        return hashes

    def clear_by_mining():
        for _ in range(100):
            if all(node.call('getmempoolinfo')['size'] == 0 for node in clients):
                return
            mine()
        raise RuntimeError('Mempools did not clear after bounded mining')

    def fixture(name, count, signed, chained=False):
        started = time.perf_counter()
        output = DiskFixture(directory / (name + '.bin'),
                             max_bytes=(16 if budget_only else 512) * 1024 * 1024)
        roots = math.ceil(count / (4 if chained else 1))
        hierarchical = not chained and (roots > 100000 or hierarchical_funding)
        fanout_width = (funding_fanout_width(context['NativeSource'], True) if native
                        else 256 if hierarchical else 1000)
        roots_per_coinbase = fanout_width ** (2 if hierarchical else 1)
        chunks = math.ceil(roots / roots_per_coinbase)
        hashes = mine(chunks + 100)
        remaining = count
        sizes = set()
        first_level = []

        def append_spends(txid, width, value):
            nonlocal remaining
            for index in range(min(width, math.ceil(remaining / (4 if chained else 1)))):
                previous, previous_index, previous_value = int(txid, 16), index, value
                for hop in range(min(4 if chained else 1, remaining)):
                    if signed and native:
                        child = context['build_signed_p2pkh_tx'](
                            previous, previous_index, previous_value, previous_value - fixture_fee_sats,
                            context['signer'], nonce_idx=index + hop)
                    elif signed:
                        child = context['build_signed_p2pkh_tx'](
                            previous, previous_index, previous_value, previous_value - fixture_fee_sats,
                            legacy_signer, context['pubkey_bytes'], context['p2pkh_spk'])
                    else:
                        child = context['build_p2sh_op_true_tx'](
                            previous, previous_index, previous_value - fixture_fee_sats, op_script)
                    raw = to_hex(child)
                    sizes.add(len(raw) // 2)
                    output.append(raw)
                    remaining -= 1
                    previous, previous_index, previous_value = child.txid_int, 0, previous_value - fixture_fee_sats

        def funding_tx(previous, index, amount, width, leaf, intermediate=False):
            value = (amount - 200000) // width
            if value <= fixture_fee_sats + 1000:
                raise ValueError(f'Coinbase/funding output cannot fund bounded fixture: amount={amount}, width={width}')
            tx = context['build_p2sh_op_true_tx'](previous, index, amount - 200000, op_script)
            if native:
                tx.vout = [context['make_v2_txout'](value, leaf) for _ in range(width)]
            else:
                script = (context['p2pkh_spk'] if signed and not intermediate
                          else context['CScript'](op_script))
                tx.vout = [context['CTxOut'](value, script) for _ in range(width)]
                # Replacing the builder's outputs can remove its100-byte padding.
                context['pad_tx'](tx)
            txid = f'{tx.txid_int:064x}'
            c.call('sendrawtransaction', [to_hex(tx)])
            return txid, value

        final_leaf = (context['signer']['branch_leaf'] if signed else context['V2_OP_TRUE_BRANCH_LEAF']) if native else None
        allocated_roots = 0
        for block_hash in hashes[:chunks]:
            cb = c.call('getblock', [block_hash, 2])['tx'][0]
            scale = int(c.call('getcurrencyinfo')['satoshisperunit']) if native else 100
            amount = Decimal(str(cb['vout'][0]['value'])) * scale
            if amount != amount.to_integral_value():
                raise ValueError('Nonintegral coinbase amount')
            amount = int(amount)
            if hierarchical:
                target = min(roots_per_coinbase, roots - allocated_roots)
                width = math.ceil(target / fanout_width)
                txid, value = funding_tx(int(cb['txid'], 16), 0, amount, width,
                                         context['V2_OP_TRUE_BRANCH_LEAF'] if native else None,
                                         intermediate=True)
                for index in range(width):
                    leaves = min(fanout_width, target - index * fanout_width)
                    # Prove every second-level output can pay its fixed fee and
                    # all final independent signed spends before allocating them.
                    if (value - 200000) // leaves <= fixture_fee_sats + 1000:
                        raise ValueError('Early coinbase cannot fund two-level independent fixture')
                    first_level.append((int(txid, 16), index, value, leaves))
                allocated_roots += target
            else:
                width = min(fanout_width, max(100, math.ceil(remaining / (4 if chained else 1))))
                txid, value = funding_tx(int(cb['txid'], 16), 0, amount, width, final_leaf)
                append_spends(txid, width, value)
        if hierarchical:
            # Confirm the small OP_TRUE first level before creating independent
            # funding parents, avoiding descendant-limit assumptions entirely.
            clear_by_mining()
            for previous, index, amount, width in first_level:
                txid, value = funding_tx(previous, index, amount, width, final_leaf)
                append_spends(txid, width, value)
        if remaining != 0 or len(output.offsets) != count:
            raise RuntimeError('Funding plan did not construct the exact unique fixture count')
        clear_by_mining()
        output.seal()
        return output, {'fund_and_sign_seconds': time.perf_counter() - started,
                        'transaction_count': count, 'transaction_sizes': sorted(sizes),
                        'funding_fanout_width': fanout_width, 'funding_coinbase_chunks': chunks,
                        'funding_levels': 2 if hierarchical else 1,
                        'intermediate_outputs': len(first_level),
                        'disk_bytes': output.path.stat().st_size,
                        'index_bytes': len(output.offsets) * output.offsets.itemsize}

    if fixture_smoke:
        evidence = {}
        batch_available = batch_rpc_available(c, evidence)
        results['batch_capability'] = {'available': batch_available, **evidence}
        for signed in (True, False):
            prepared, details = fixture('smoke-signed' if signed else 'smoke-optrue', 32, signed)
            try:
                client = Client()
                for _ in range(8):
                    submit(client, 'individual', prepared.take(1))
                submit(client, 'json_array', prepared.take(8))
                remaining = prepared.take(16)
                if batch_available:
                    submit(client, 'dedicated_batch', remaining)
                else:
                    submit(client, 'json_array', remaining)
                if c.call('getmempoolinfo')['size'] != 32:
                    raise RuntimeError('Bounded fixture smoke inventory mismatch')
                results['smoke_signed' if signed else 'smoke_optrue'] = {
                    'accepted_unique_transactions': 32, 'fixture_sha256': prepared.digest.hexdigest(),
                    'preparation': details, 'throughput_measured': False,
                    'batch_available': batch_available, 'memory': memory_snapshot()}
            finally:
                prepared.close()
                prepared.path.unlink()
            clear_by_mining()
        return

    if case_filter is None:
        raise ValueError('Select one steady case per fresh three-node datadir')

    cases = [('single_tx_steady', 'individual', 1, True, 0, False),
             ('json_rpc_batch50_steady', 'json_array', 50, True, 0, False),
             ('single_tx_loaded_steady', 'individual', 1, True, 12, False)]
    evidence = {}
    batch_available = batch_rpc_available(c, evidence)
    results['batch_capability'] = {'available': batch_available, **evidence}
    if batch_available:
        cases.append(('signed_batch200_steady', 'dedicated_batch', 200, True, 0, False))
        cases.append(('chained_signed_batch200_steady', 'dedicated_batch', 200, True, 0, True))
        cases.extend((f'optrue_batch{size}_steady', 'dedicated_batch', size, False, 0, False)
                     for size in (1, 50, 100, 200, 250, 500, 1000))
    cases = [case for case in cases if case[0] == case_filter]
    if not cases and case_filter != 'fixed_latency':
        raise ValueError('Requested steady case is unavailable: ' + case_filter)
    for name, mode, size, signed, readers, chained in cases:
        # Pilot is a different, finite transaction fixture and is never a metric.
        pilot, preparation = fixture(name + '-pilot', max(4096, 32 * size), signed, chained)
        pilot_result = measure(pilot, Client, mode, size, pilot=True,
                               reader_workers=readers)
        count, duration = pilot_result['tx_count'], pilot_result['seconds']
        pilot_pool = c.call('getmempoolinfo')
        results['preparation_pilot'] = {
            'throughput_measured': False, 'fixture_count': pilot_result['fixture_count'],
            'fixture_sha256': pilot_result['fixture_sha256'],
            'accepted_count': count, 'seconds': duration,
            'preparation': preparation, 'mempool': pilot_pool}
        pilot.close()
        pilot.path.unlink()
        results['preparation_pilot_cleanup'] = {
            'file_closed': pilot.file.closed, 'mapping_closed': pilot.mapping.closed,
            'fixture_removed': not pilot.path.exists()}
        clear_by_mining()
        if name == 'single_tx_steady':
            empty_pool = c.call('getmempoolinfo')
            if empty_pool['size'] != 0:
                raise RuntimeError('C1 unloaded reads require an empty pool before ingestion')
            results['read_unloaded_mempool'] = empty_pool
            results['read_unloaded_steady'] = measure_reads(Client)
        needed = (fixed_diagnostic_budget(exact_fixture_count, size, max_transactions)
                  if diagnostic_fixed_work else
                  fixture_budget(count, duration, size, max_transactions, exact_fixture_count, minimum_supply_seconds))
        bytes_per_entry = pilot_pool['usage'] / max(1, pilot_pool['size'])
        predicted_usage = needed * bytes_per_entry
        if predicted_usage > 0.8 * pilot_pool['maxmempool']:
            raise ValueError(f'Pilot projects {predicted_usage:.0f} mempool bytes; exceeds80% '
                             f'of actual{pilot_pool["maxmempool"]}B/node budget; no heavy fixture allocated')
        if budget_only:
            results['pilot_budget'] = {
                'case': name, 'budget_only': True, 'throughput_measured': False,
                'pilot_tx_count': count, 'pilot_seconds': duration,
                'pilot_fixture_count': pilot_result['fixture_count'],
                'pilot_fixture_sha256': pilot_result['fixture_sha256'],
                'pilot_preparation': preparation, 'pilot_mempool': pilot_pool,
                'projected_fixture_count': needed,
                'projected_disk_bytes': needed * preparation['disk_bytes'] / preparation['transaction_count'],
                'projected_mempool_bytes_per_node': predicted_usage,
                'memory': memory_snapshot()}
            return
        print(f'[steady prepare] {name}: pilot={count}/{duration:.6f}s, '
              f'presigning {needed} distinct transactions; no measured clock running', flush=True)
        prepared, details = fixture(name, needed, signed, chained)
        results['prepared_fixture'] = {**details, 'fixture_sha256': prepared.digest.hexdigest(),
                                       'warmup_transaction_count': 16 * size,
                                       'requested_timed_transaction_count': needed - 16 * size,
                                       'fee_sats': fixture_fee_sats}
        try:
            before_memory = memory_snapshot()
            sampler = None
            def launch_sample(ingestion_start, ingestion_utc_ns, warmup_count):
                nonlocal sampler
                sample_path = Path(sample_node0_output)
                sample_path.parent.mkdir(parents=True, exist_ok=True)
                if sample_path.exists():
                    raise ValueError('Refusing to overwrite a prior CPU trace')
                sampled_pid = context['procs'][0].pid
                sample_seconds = 1 if diagnostic_fixed_work else 4
                launched_ns = time.time_ns()
                sampler = subprocess.Popen(['/usr/bin/sample', str(sampled_pid), str(sample_seconds), '1',
                                            '-file', str(sample_path)],
                                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                results['diagnostic_cpu_sample'] = {
                    'target_pid': sampled_pid, 'path': str(sample_path),
                    'duration_seconds': sample_seconds, 'interval_milliseconds': 1,
                    'launch_phase': 'AFTER ingestion go-signal; persistent connections and warmup complete',
                    'ingestion_start_monotonic': ingestion_start,
                    'ingestion_start_utc_ns': ingestion_utc_ns,
                    'warmup_fixture_count': warmup_count,
                    'sample_launch_utc_ns': launched_ns,
                    'sample_launch_return_monotonic': time.perf_counter(),
                    'profiled_throughput_publishable': False}
                print(f'[ingestion-go profiler] node0pid={sampled_pid} warmup={warmup_count} '
                      f'ingestion_utc_ns={ingestion_utc_ns} sample_launch_ns={launched_ns}', flush=True)
            network = None
            observer_clients = []
            client_lock = threading.Lock()
            client_assignments = []
            def ingestion_client():
                with client_lock:
                    index = len(client_assignments) % len(clients) if distributed_injection else 0
                    client_assignments.append(index)
                return Client(index)
            if network_observe:
                observer_clients = [Client(index) for index in range(len(clients))]
                for client in observer_clients:
                    client.call('getmempoolinfo')
                network = NetworkObservation(observer_clients, needed)
            def before_network_started():
                if network_observe:
                    results['network_warmup_inventory'] = wait_for_sizes(clients, 16 * size)
            def ingestion_started(*arguments):
                if network is not None:
                    network.begin(*arguments)
                if sample_node0_output:
                    launch_sample(*arguments)
            try:
                value = measure(prepared, ingestion_client if distributed_injection else Client,
                                mode, size, reader_workers=readers,
                                seconds=1200.0 if diagnostic_fixed_work and progress_every else 5.0,
                                pilot=diagnostic_fixed_work,
                                on_started=ingestion_started if network_observe or sample_node0_output else None,
                                progress_every=progress_every,
                                before_started=before_network_started if network_observe else None)
            except BaseException:
                if network is not None:
                    network.close()
                    results['failed_network_observation'] = {'progress': network.records, 'errors': network.errors}
                failed_inventory = {}
                for index, node in enumerate(clients):
                    try:
                        failed_inventory[str(index)] = node.call('getmempoolinfo')
                    except BaseException as error:
                        failed_inventory[str(index)] = {'capture_error': repr(error)}
                results['failed_case_inventory_after_workers_drained'] = failed_inventory
                raise
            if diagnostic_fixed_work:
                value.pop('tps', None)
                value['measurement'] = 'profiled-fixed-work-latency-diagnostic'
                value['throughput_publishable'] = False
            if sampler is not None:
                sample_path = Path(sample_node0_output)
                results['diagnostic_cpu_sample']['returncode'] = sampler.wait(timeout=15)
                results['diagnostic_cpu_sample']['ingestion_end_monotonic'] = value['finished_monotonic']
                if sampler.returncode != 0 or not sample_path.exists():
                    raise RuntimeError('CPU diagnostic sampler failed')
            if network is not None:
                try:
                    observation = network.finish(value['finished_monotonic'])
                    finals = []
                    for index, node in enumerate(clients):
                        info = node.call('getmempoolinfo')
                        digest = inventory_digest(node.call('getrawmempool'), needed)
                        finals.append({'node': index, 'mempool': info, 'sorted_txid_sha256': digest})
                    if len({entry['sorted_txid_sha256'] for entry in finals}) != 1:
                        raise RuntimeError('Peer final transaction ID sets differ')
                    observation['final_inventories'] = finals
                    observation['writer_node_assignments'] = client_assignments if distributed_injection else [0] * 8
                    observation['txid_digest_rule'] = 'SHA256(sorted lowercase txids, each ASCII plus newline); not a consensus root'
                    results['network_observation'] = observation
                except BaseException:
                    network.close()
                    results['failed_network_observation'] = {'progress': network.records, 'errors': network.errors}
                    raise
                finally:
                    for client in observer_clients:
                        client.connection.close()
            after_memory = memory_snapshot()
            expected = value['tx_count'] + 16 * size
            pool = c.call('getmempoolinfo')
            if pool['size'] != expected:
                raise RuntimeError(f'Mempool inventory {pool["size"]} != {expected} '
                                   'accepted unique transactions; eviction/incomplete admission')
            value.update({'preparation': details, 'pilot': {'tx_count': count,
                          'seconds': duration, 'excluded_from_measurement': True,
                          'mempool_bytes_per_entry': bytes_per_entry,
                          'estimated_supply_seconds': (needed - 16 * size) * duration / count,
                          'predicted_fixture_mempool_bytes': predicted_usage},
                          'memory_before': before_memory, 'memory_after': after_memory,
                          'post_measurement_mempool': pool,
                          'script': 'BIP340-P2PK' if native and signed else
                                    'legacy-Schnorr-P2PKH' if signed else 'OP_TRUE',
                          'transaction_version': 7 if native else 2, 'chain_depth': 4 if chained else 1,
                          'topology': 'three connected loopback nodes'})
            results[name] = value
            if post_ingestion_observe:
                def persist_observations(rows):
                    value['post_ingestion_observations'] = rows
                    results[name] = value
                    print('[post-ingestion-observation] ' + json.dumps(rows[-1]), flush=True)
                observe_after_ingestion(clients, memory_snapshot,
                                        value['finished_monotonic'], persist_observations)
            if diagnostic_fixed_work:
                print(f'[fixed-work CPU diagnostic] {name}: {value["tx_count"]} transactions / '
                      f'{value["seconds"]:.6f}s; not a throughput benchmark', flush=True)
            else:
                print(f'[steady measured] {name}: {value["tx_count"]} / '
                      f'{value["seconds"]:.6f}s = {value["tps"]:.1f} tx/s', flush=True)
        finally:
            prepared.close()
            prepared.path.unlink()
        # Each case owns fresh nodes. C1 was measured with the empty pool
        # before ingestion; no unrelated large-block connect follows its timer.
    if native and case_filter == 'fixed_latency':
        # Fixed-work latency controls are separate from saturation throughput.
        prepared, details = fixture('fixed-relay500', 500, True)
        try:
            fixed = measure(prepared, Client, 'individual', 1, warmup_batches=0, pilot=True)
        finally:
            prepared.close()
            prepared.path.unlink()
        deadline = time.perf_counter() + 90
        while not all(node.call('getmempoolinfo')['size'] == 500 for node in clients):
            if time.perf_counter() > deadline:
                raise TimeoutError('Fixed500 propagation did not converge')
            time.sleep(0.002)
        results['relay500'] = {'seconds': time.perf_counter() - fixed['started_monotonic'],
                               'transaction_count': 500, 'all_converged': True,
                               'measurement': 'fixed-work propagation latency'}
        for name, parameters in [('gbt_standard', {'rules': ['segwit']}),
                                 ('gbt_compact', {'mode': 'compact_template'})]:
            samples = []
            started = time.perf_counter()
            while len(samples) < 31 or time.perf_counter() - started < 5:
                before = time.perf_counter()
                response = c.call('getblocktemplate', [parameters])
                samples.append((time.perf_counter() - before) * 1000)
            samples.sort()
            if name == 'gbt_compact' and 'transactions' in response:
                results[name] = {'status': 'unavailable', 'reason': 'standard template returned'}
            else:
                results[name] = {'samples': len(samples), 'sampling_seconds': time.perf_counter() - started,
                                  **{f'p{q}_ms': samples[min(len(samples) - 1, math.ceil(q * len(samples) / 100) - 1)]
                                     for q in (50, 95, 99)}}
        clear_by_mining()
        prepared, details = fixture('fixed-block801', 801, True)
        try:
            measure(prepared, Client, 'individual', 1, warmup_batches=0, pilot=True)
        finally:
            prepared.close()
            prepared.path.unlink()
        before = time.perf_counter()
        c.call('generatetodescriptor', [1, context['V2_OP_TRUE_DESCRIPTOR']])
        node0 = time.perf_counter() - before
        context['sync_all_blocks'](clients, base_dir=context['base_dir'])
        results['block801'] = {'mine_connect_node0_ms': node0 * 1000,
                                'three_node_ms': (time.perf_counter() - before) * 1000,
                                'tx_count': 801, 'measurement': 'fixed-work block latency'}
