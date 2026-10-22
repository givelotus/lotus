#!/usr/bin/env python3
"""Bounded aged native full-scope recovery proof, not a throughput benchmark.

Run with the candidate's test/functional on PYTHONPATH and its build config.
No manual mempool download, requested-body injection, proof or epoch glue.
"""
import hashlib
import json
import re
import time
from pathlib import Path
from decimal import Decimal

from test_framework.currency import RpcCurrency
from test_framework.test_framework import BitcoinTestFramework
from test_framework.util import assert_equal, assert_raises_rpc_error
from test_framework.wallet import NativeMiniWallet


def txid_digest(txids):
    return hashlib.sha256("".join(txid.lower() + "\n" for txid in sorted(txid.lower() for txid in txids)).encode()).hexdigest()


def negotiated_recon_flags(log, peer_ids):
    offers = {}
    for _version, flags, peer in re.findall(r"sendinvshort version=(\d+) flags=(\d+) peer=(\d+)", log):
        offers[int(peer)] = int(flags)
    return {peer_id: offers.get(peer_id, 0) for peer_id in peer_ids}


def json_metadata(value):
    if isinstance(value, Decimal):
        return str(value)
    raise TypeError(f"Unsupported evidence type: {type(value).__name__}")


class FullScopeCorrectness(BitcoinTestFramework):
    num_nodes = 3
    setup_clean_chain = True
    supports_cli = False
    extra_args = [["-avalanche=0", "-mocktime=0", "-debug=net", "-debug=txrelay",
                   "-txreconinterval=250", "-txreconfull=1"]
                  for _ in range(3)]

    def add_options(self, parser):
        parser.add_argument("--evidence", type=Path)

    def setup_network(self):
        super().setup_network()
        self.connect_nodes(0, 2)

    def persist(self):
        destination = self.options.evidence or Path(self.options.tmpdir) / "scheduler-evidence.json"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(self.evidence, indent=2, default=json_metadata) + "\n")

    def snapshot(self, label):
        value = {"phase": label, "monotonic": time.monotonic(), "nodes": []}
        for node in self.nodes:
            assert_raises_rpc_error(-32603, "Avalanche processor missing or disabled", node.getavalancheinfo)
            info = node.getnetworkinfo()
            assert not any("AVALANCHE" in service for service in info["localservicesnames"])
            peers = node.getpeerinfo()
            for peer in peers:
                assert_equal(peer.get("last_proof", 0), 0)
                for direction in ("bytessent_per_msg", "bytesrecv_per_msg"):
                    assert not any(count for name, count in peer.get(direction, {}).items()
                                   if name.startswith(("avap", "avar")) or name == "avahello")
            value["nodes"].append({"index": node.index, "mempool": node.getmempoolinfo(),
                                   "network_info": info, "peers": peers})
        self.evidence["snapshots"].append(value)
        self.persist()
        return value

    def require_full_scope(self):
        def ready():
            for node in self.nodes:
                peers = node.getpeerinfo()
                if len(peers) != 2 or any(not peer.get("version") for peer in peers):
                    return False
                log = (node.chain_path / "debug.log").read_text(errors="replace")
                flags = negotiated_recon_flags(log, [peer["id"] for peer in peers])
                if not all(value & 10 == 10 for value in flags.values()):
                    return False
            return True
        self.wait_until(ready, timeout=15)
        self.evidence["capability_proof"] = []
        for node in self.nodes:
            peers = node.getpeerinfo()
            log = (node.chain_path / "debug.log").read_text(errors="replace")
            self.evidence["capability_proof"].append({"node": node.index,
                "received_sendinvshort_flags": negotiated_recon_flags(log, [p["id"] for p in peers]),
                "required_bits": "TXRELAY_RECON=1<<1 and TXRELAY_FULL_MEMPOOL=1<<3, sourced from received sendinvshort flags"})
        self.persist()

    def require_sets(self, label, expected_sets, timeout=180):
        started = time.monotonic()
        previous = None
        while True:
            counts = [node.getmempoolinfo()["size"] for node in self.nodes]
            if counts != previous:
                self.evidence["inventory_progress"].append({"phase": label,
                    "seconds": time.monotonic() - started, "counts": counts})
                previous = counts
                self.persist()
            if counts == [len(expected) for expected in expected_sets]:
                actual = [set(node.getrawmempool()) for node in self.nodes]
                if any(got != expected for got, expected in zip(actual, expected_sets, strict=True)):
                    self.evidence['missing_set_diagnostic'] = {'phase': label,
                        'nodes': [{'node': i, 'actual_count': len(got),
                            'sorted_txid_sha256': txid_digest(got),
                            'missing_ids': sorted(expected - got),
                            'unexpected_ids': sorted(got - expected)}
                            for i, (got, expected) in enumerate(zip(actual, expected_sets, strict=True))]}
                    self.persist()
                for got, expected in zip(actual, expected_sets, strict=True):
                    assert_equal(got, expected)
                self.evidence["completed_sets"].append({"phase": label,
                    "seconds": time.monotonic() - started,
                    "counts": counts, "sorted_txid_sha256": [txid_digest(got) for got in actual]})
                self.persist()
                return
            if time.monotonic() - started > timeout:
                actual = [set(node.getrawmempool()) for node in self.nodes]
                self.evidence['missing_set_diagnostic'] = {'phase': label,
                    'nodes': [{'node': i, 'actual_count': len(got),
                        'sorted_txid_sha256': txid_digest(got),
                        'missing_ids': sorted(expected - got),
                        'unexpected_ids': sorted(got - expected)}
                        for i, (got, expected) in enumerate(zip(actual, expected_sets, strict=True))]}
                self.snapshot(label + "-timeout")
                raise AssertionError(f"{label}: exact inventory did not converge; counts={counts}")
            time.sleep(0.1)

    def require_full_scope_events(self):
        def collect():
            result = []
            for i, node in enumerate(self.nodes):
                lines = (node.chain_path / 'debug.log').read_text(errors='replace').splitlines()
                relevant = [line for line in lines[self.reconnect_log_offsets[i]:]
                    if 'fullrecon_' in line or 'verified remote snapshot peer=' in line
                    or 'full reconciliation admission peer=' in line or 'captured complete mempool count=' in line]
                result.append({'node': i, 'events_after_reconnect': relevant})
            self.evidence['full_scope_event_proof'] = result
            self.persist()
            return any('fullrecon_coverage_complete' in line or 'verified remote snapshot peer=' in line
                       for line in result[2]['events_after_reconnect'])
        self.wait_until(collect, timeout=15)

    def verify_raw_bodies(self, expected):
        evidence = []
        for node in self.nodes:
            verified = []
            ordered = sorted(expected)
            for offset in range(0, len(ordered), 128):
                chunk = ordered[offset:offset + 128]
                responses = node.batch({'jsonrpc': '2.0', 'id': offset + i,
                    'method': 'getrawtransaction', 'params': [txid, False]}
                    for i, txid in enumerate(chunk))
                for i, (response, txid) in enumerate(zip(responses, chunk, strict=True)):
                    assert_equal(response['id'], offset + i)
                    assert_equal(response['result'], self.expected_raw[txid])
                    verified.append(self.expected_hash[txid])
            evidence.append({'node': node.index, 'raw_body_exact_matches': len(verified),
                'sorted_txhash_sha256': txid_digest(verified),
                'identity_rule': 'native framework txhash_hex for prepared body, after exact fetched-body byte comparison'})
            self.evidence['raw_body_proof'] = evidence
            self.persist()

    def submit(self, transfers):
        for offset in range(0, len(transfers), 50):
            chunk = transfers[offset:offset + 50]
            responses = self.nodes[0].batch({"jsonrpc": "2.0", "id": offset + i,
                "method": "sendrawtransaction", "params": [tx["hex"], 0]}
                for i, tx in enumerate(chunk))
            for i, (response, tx) in enumerate(zip(responses, chunk, strict=True)):
                assert_equal(response["id"], offset + i)
                assert_equal(response["result"], tx["txid"])

    def run_test(self):
        self.evidence = {"status": "RUNNING_CORRECTNESS_ONLY", "snapshots": [],
            "inventory_progress": [], "completed_sets": [], "timed_throughput": False,
            "transactions": "10,000 independent native v7 OP_TRUE spends; no signature/TPS claim",
            "scope": "Full-mempool scope5; actual FULL capability bit3 and recovery events required",
            "reconnect_case": "5000 all peers; isolate node2;5000 new;real age64s;normalreconnect180s exactsets",
            "no_manual_recovery": "No BIP35, injected bodies, forced inventory, Avalanche or proofs"}
        try:
            self.snapshot("startup-no-avalanche-or-proofs")
            wallet = NativeMiniWallet(self.nodes[0])
            wallet.generate(150)
            self.sync_blocks()
            self.require_full_scope()
            outputs = []
            for _ in range(40):
                parent = wallet.send_self_transfer_multi(from_node=self.nodes[0],
                    num_outputs=250, confirmed_only=True, fee_per_output=1000)
                outputs.extend(parent["new_utxos"])
            wallet.generate(1)
            self.sync_blocks()
            self.require_sets("confirmed-funding-empty", [set(), set(), set()])
            currency = RpcCurrency.from_node(self.nodes[0])
            transfers = [wallet.create_self_transfer(utxo_to_spend=coin,
                fee=currency.from_atoms(10000)) for coin in outputs]
            ids = [tx["txid"] for tx in transfers]
            assert_equal(len(ids), 10000)
            assert_equal(len(set(ids)), 10000)
            self.expected_raw = {tx['txid']: tx['hex'] for tx in transfers}
            self.expected_hash = {tx['txid']: tx['tx'].txhash_hex for tx in transfers}
            self.evidence["prepared"] = {"count": len(ids),
                "sizes": sorted({len(tx["hex"]) // 2 for tx in transfers}),
                "sorted_txid_sha256": txid_digest(ids),
                "sorted_txhash_sha256": txid_digest(self.expected_hash.values())}
            self.submit(transfers[:5000])
            first = set(ids[:5000])
            self.require_sets("initial-5000-all-peers", [first, first, first])
            self.snapshot("initial-all-peer-proof")
            self.disconnect_nodes(0, 2)
            self.disconnect_nodes(1, 2)
            assert_equal(self.nodes[2].getpeerinfo(), [])
            self.submit(transfers[5000:])
            all_ids = set(ids)
            self.require_sets("isolated-node2-misses-5000", [all_ids, all_ids, first])
            aging_started = time.monotonic()
            admitted = self.nodes[0].getmempoolentry(ids[-1])['time']
            while time.monotonic() - aging_started < 64:
                self.evidence['aging'] = {'elapsed_monotonic_seconds': time.monotonic() - aging_started,
                    'last_new_transaction_admission_epoch_seconds': admitted,
                    'wall_seconds_since_last_admission': time.time() - admitted,
                    'mocktime_disabled': True}
                self.persist()
                time.sleep(max(0, min(5, 64 - (time.monotonic() - aging_started))))
            assert time.time() - admitted > 60
            self.evidence['aging']['completed_elapsed_monotonic_seconds'] = time.monotonic() - aging_started
            self.evidence['aging']['completed_wall_seconds_since_last_admission'] = time.time() - admitted
            self.require_sets('aged-isolation-still-missing5000', [all_ids, all_ids, first])
            self.snapshot("before-reconnect")
            self.reconnect_log_offsets = [len((node.chain_path / 'debug.log').read_text(errors='replace').splitlines())
                                          for node in self.nodes]
            self.connect_nodes(0, 2)
            self.connect_nodes(1, 2)
            self.require_full_scope()
            self.require_sets("reconnect-exact-10000-all-peers", [all_ids, all_ids, all_ids])
            self.wait_until(lambda: all(any(peer.get("bytessent_per_msg", {}).get("merklixsync", 0) > 0
                for peer in node.getpeerinfo()) for node in self.nodes), timeout=15)
            final = self.snapshot("final-no-avalanche-or-proofs")
            for node in final["nodes"]:
                assert any(peer.get("bytessent_per_msg", {}).get("merklixsync", 0) > 0
                           for peer in node["peers"]), "No actual reconciliation summary sent"
            self.require_full_scope_events()
            self.verify_raw_bodies(all_ids)
            self.evidence["status"] = "PASS_AGED_FULL_SCOPE_RECOVERY_NOT_TPS"
        except BaseException as error:
            self.evidence["status"] = "FAIL"
            self.evidence["error"] = repr(error)
            raise
        finally:
            self.persist()


if __name__ == "__main__":
    FullScopeCorrectness().main()
