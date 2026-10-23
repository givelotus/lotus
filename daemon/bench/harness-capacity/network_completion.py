#!/usr/bin/env python3
"""Observe complete peer inventories separately from RPC admission timing."""
import hashlib
import json
from pathlib import Path
import time


def wait_for_counts(clients, expected, output, *, timeout=180):
    """Bounded observation, preserving progress even when convergence fails."""
    assert len(clients) >= 2 and expected >= 0
    output = Path(output)
    started = time.perf_counter()
    rows = []
    while True:
        counts = [client.call('getmempoolinfo')['size'] for client in clients]
        now = time.perf_counter()
        if not rows or counts != rows[-1]['counts'] or now-rows[-1]['monotonic'] >= 1:
            rows.append(dict(monotonic=now, seconds=now-started, counts=counts))
            output.write_text(json.dumps(dict(expected=expected, progress=rows), indent=2)+'\n')
        if any(count > expected for count in counts):
            raise RuntimeError('Peer inventory exceeds unique accepted workload')
        if all(count == expected for count in counts):
            return dict(monotonic=now, seconds=now-started, counts=counts, progress=rows)
        if now-started > timeout:
            raise TimeoutError(f'Peer completion timed out: expected{expected}, observed{counts}; progress at{output}')
        time.sleep(.05)


def verify_inventories(clients, expected):
    rows = []
    for index, client in enumerate(clients):
        txids = client.call('getrawmempool')
        assert len(txids) == len(set(txids)) == expected
        assert all(len(txid) == 64 and txid == txid.lower() for txid in txids)
        digest = hashlib.sha256()
        for txid in sorted(txids):
            digest.update(txid.encode('ascii')+b'\n')
        rows.append(dict(node=index, count=len(txids), sorted_txids_sha256=digest.hexdigest()))
    assert len({row['sorted_txids_sha256'] for row in rows}) == 1, 'Peer transaction ID sets differ'
    return rows


def finish(clients, result, warmup, directory, *, timeout=180):
    expected = result['tx_count'] + warmup
    directory = Path(directory)
    observation = wait_for_counts(clients, expected, directory/'NETWORK-PROGRESS.json', timeout=timeout)
    counts_seen = observation['monotonic']
    inventories = verify_inventories(clients, expected)
    verified = time.perf_counter()
    value = dict(measurement='three-peer completion after validated admission',
        timed_transactions=result['tx_count'], warmup_transactions=warmup,
        admission_seconds=result['seconds'], admission_tps=result['tps'],
        counts_converged_from_ingestion_start_seconds=counts_seen-result['started_monotonic'],
        counts_converged_after_admission_seconds=max(0, counts_seen-result['finished_monotonic']),
        exact_inventory_verified_from_ingestion_start_seconds=verified-result['started_monotonic'],
        exact_inventory_verified_after_admission_seconds=max(0, verified-result['finished_monotonic']),
        all_peer_verified_tps=result['tx_count']/(verified-result['started_monotonic']),
        inventories=inventories,
        digest_rule='SHA256(sorted lowercase txids, ASCII plus newline); not consensus Merklix roots',
        scope='Warmup propagated before ingestion GO; 50ms count polling begins only after timed admission; exact digest verification cost INCLUDED in all_peer_verified_tps; no block confirmation or Avalanche finality')
    (directory/'NETWORK-COMPLETION.json').write_text(json.dumps(value, indent=2)+'\n')
    return value
