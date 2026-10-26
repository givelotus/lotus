"""Offline deterministic fixture derivation; requires the independent reference package."""
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
from blake3 import blake3
from lotus_v2_reference.block import empty_utxo_root, state_root
from lotus_v2_reference.block_seal import Header, block_id
from lotus_v2_reference.block_wire import complete_transaction_root, encode_block_wire, decode_block_wire
from lotus_v2_reference.encoding import Output
from lotus_v2_reference.signing import Input, Transaction, TxProfile
from lotus_v2_reference.monetary import Profile, initialize_genesis

NAME = 'lotus-v2-local-test-20261015-absolute1'
HERE = Path(__file__).resolve().parent

def tagged(domain, body):
    return blake3(domain.encode('ascii') + b'\0' + body).digest()

def profile_digest(m):
    """Exact native BlockValidationProfileDigest schema 2 byte order."""
    wire = bytearray()
    def put(n, width=8):
        wire.extend(int(n).to_bytes(width, 'little'))
    h = m['header']
    put(2)
    for key in ('chain_id', 'genesis_id'):
        wire.extend(bytes.fromhex(h[key]))
    for key in ('version', 'time', 'bits'):
        put(h[key])
    wire.extend(bytes.fromhex(h['pow_limit']))
    for n in (h['half_life'], h['spacing'], *m['transaction_limits'], *m['vm_limits'],
              m['coinbase_maturity'], m['dust_limit']):
        put(n)
    inv = m['invocation_limits']
    put(inv[1], 16)
    put(inv[0], 16)
    put(inv[2])
    for row in m['opcode_costs']:
        for n in row:
            put(n)
    put(len(m['field_sizes']))
    for opcode, sizes in sorted(m['field_sizes']):
        put(opcode, 1)
        put(len(sizes))
        for n in sizes:
            put(n)
    for n in m['monetary'][:10]:
        put(n)
    put(m['tail_formula_version'])
    put(m['monetary'][10])
    wire.extend(bytes.fromhex(m['monetary'][11]))
    for n in m['outer_costs']:
        put(n)
    return tagged('Lotus/v2/storage-validator-profile', wire).hex()

def reproduce():
    m = json.loads((HERE / 'legacy-schema1-local-test-manifest.json').read_text())
    m['schema'] = 2
    m['tail_formula_version'] = 1
    m['monetary'] += [1000000, (2).to_bytes(32, 'little').hex()]
    chain = tagged('Lotus/v2/development-chain', NAME.encode('ascii'))
    m['header']['chain_id'] = chain.hex()
    profile = Profile(*m['monetary'][:11], 2)
    initial = initialize_genesis(profile, bootstrap_reserve=1048576000000,
        tail_subsidy=1000000, genesis_work=2, ema_block_cost=65536)
    assert initial.to_bytes().hex() == m['initial_monetary']
    tx_profile = TxProfile(*m['transaction_limits'])
    note = tagged('Lotus/v2/development-genesis-note', NAME.encode('ascii'))
    tx = Transaction(0, (Input(bytes(32), 0, 0xffffffff, 2),),
                     (Output(2, 0, None, (note,), ()),))
    header = Header(bytes(32), m['header']['bits'], m['header']['time'], 0,
                    m['header']['version'], 240, 0,
                    complete_transaction_root((tx,), tx_profile, chain),
                    state_root(chain, 0, empty_utxo_root(), initial))
    target = int.from_bytes(bytes.fromhex(m['header']['pow_limit']), 'little')
    assert (1 << 256) // (target + 1) == 2
    while int.from_bytes(block_id(chain, header), 'little') > target:
        header = replace(header, nonce=header.nonce + 1)
    wire = encode_block_wire(header, (tx,), tx_profile)
    assert decode_block_wire(wire, tx_profile, chain).transactions == (tx,)
    m['genesis'] = wire.hex()
    m['header']['genesis_id'] = block_id(chain, header).hex()
    return m

if __name__ == '__main__':
    result = reproduce()
    encoded = (json.dumps(result, indent=2) + '\n').encode()
    actual = (HERE / 'local-test-manifest.json').read_bytes()
    assert encoded == actual, 'checked-in manifest differs from deterministic derivation'
    provenance = json.loads((HERE / 'provenance.json').read_text())
    assert sha256(encoded).hexdigest() == provenance['manifest_sha256']
    assert profile_digest(result) == provenance['profile_digest']
    assert result['header']['chain_id'] == provenance['chain_id']
    assert result['header']['genesis_id'] == provenance['genesis_id']
    print(json.dumps(dict(name=NAME, manifest_sha256=sha256(encoded).hexdigest(),
        chain_id=result['header']['chain_id'], genesis_id=result['header']['genesis_id'],
        profile_digest=profile_digest(result)), indent=2))
