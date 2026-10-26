"""Declared compatibility adapters for the frozen native benchmark, not consensus rules."""
from decimal import Decimal
import importlib.util
from pathlib import Path


def amount_to_sats(client, value):
    info = client.call('getcurrencyinfo')
    scale = int(info['satoshisperunit'])
    if scale <= 0:
        raise ValueError('Invalid currency denomination')
    amount = Decimal(str(value)) * scale
    if amount != amount.to_integral_value():
        raise ValueError('RPC amount is not an integral number of satoshis')
    return int(amount)


def install(client_class, source, branch_leaf):
    source = Path(source)
    mining = (source / 'src/rpc/mining.cpp').read_text()
    if 'Legacy descriptors are unsupported for native coinbases' not in mining:
        return {'mining': 'historical raw native descriptor'}
    module_path = source / 'test/functional/test_framework/xpiaddr.py'
    spec = importlib.util.spec_from_file_location('benchmark_native_address', module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    address = module.encode('rxpi', branch_leaf)
    original = client_class.call

    def call(self, method, params=None):
        values = list(params or [])
        if method == 'generatetodescriptor':
            if len(values) < 2 or values[1] != 'raw(4e)':
                raise ValueError('Benchmark adapter accepts only its explicit native OP_TRUE policy')
            method = 'generatetoaddress'
            values[1] = address
        elif method == 'getblocktemplate':
            template = dict(values[0]) if values else {}
            template['mineraddress'] = address
            values = [template, *values[1:]]
        return original(self, method, values)

    client_class.call = call
    return {'mining': 'explicit type0 native OP_TRUE payout', 'address': address,
            'address_encoder': str(module_path)}


def adapt(code, source):
    source = Path(source)
    old = 'int(round(float(cb_tx["vout"][0]["value"]) * 100))'
    if code.count(old) != 1:
        raise ValueError('Frozen native amount-conversion anchor changed')
    code = code.replace(old, 'NativeAmountToSats(clients[0], cb_tx["vout"][0]["value"])')
    # The negative fixture spends a native coin, so rejection remains mandatory.
    verify = (source / 'src/consensus/tx_verify.cpp').read_text()
    rejection = ('bad-txns-legacy-spends-v2-coin' if 'bad-txns-legacy-spends-v2-coin' in verify
                 else 'bad-txns-non-v7-format')
    code = code.replace('bad-txns-non-v7-format', rejection)
    if rejection == 'bad-txns-legacy-spends-v2-coin':
        code = code.replace('legacy_check["results"][0].get("reject-reason") == "bad-txns-legacy-spends-v2-coin"',
                            'legacy_check["results"][0].get("reject-reason") in ("bad-txns-legacy-spends-v2-coin", "bad-txns-nonstandard-inputs")')
    if rejection == 'bad-txns-legacy-spends-v2-coin':
        old_output = 'legacy_tx.vout = [CTxOut(mature_cb_utxos[0][2] - 1000, CScript(V2_OP_TRUE_SCRIPT))]'
        if code.count(old_output) != 1:
            raise ValueError('Frozen native negative-spend fixture changed')
        code = code.replace(old_output,
            'legacy_tx.vout = [CTxOut(mature_cb_utxos[0][2] - 1000, CScript(bytes.fromhex("a914da1745e9b549bd0bfa1a569971c77eba30cd5a4b87")))]\n        legacy_tx.vin[0].scriptSig = bytes(legacy_tx.vin[0].scriptSig) + b"\\x00" * 20')
    code = code.replace('def main():',
                        'NativeAdapterDetails = InstallNativeAdapter(KeepAliveRPCClient, NativeSource, V2_OP_TRUE_BRANCH_LEAF)\n\ndef main():', 1)
    return code, {'rejection': rejection, 'permitted_earlier_policy_rejection': 'bad-txns-nonstandard-inputs' if rejection == 'bad-txns-legacy-spends-v2-coin' else None, 'amounts': 'getcurrencyinfo.satoshisperunit',
                  'payout': 'explicit native type0 when strict payout policy is present'}
