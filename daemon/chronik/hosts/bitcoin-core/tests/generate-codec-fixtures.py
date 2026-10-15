#!/usr/bin/env python3
"""Generate deterministic wire fixtures through an exact Bitcoin Core oracle."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess

CORE_PIN = 'f13ae519de94394314cd63a27924b0998ac65d45'


def compact(value):
    if value < 253:
        return bytes([value])
    if value <= 0xffff:
        return b'\xfd' + struct.pack('<H', value)
    if value <= 0xffffffff:
        return b'\xfe' + struct.pack('<I', value)
    return b'\xff' + struct.pack('<Q', value)


def transaction(inputs=1, outputs=None, witness=None, version=2, script=b'\x51', flags=None, coinbase=False):
    if outputs is None:
        outputs = [b'\x00\x14' + b'\x22' * 20]
    extended = witness is not None or flags is not None
    data = bytearray(struct.pack('<I', version))
    positions = {}
    if extended:
        data.extend(bytes([0, 1 if flags is None else flags]))
    positions['input_count'] = len(data)
    data.extend(compact(inputs))
    for index in range(inputs):
        data.extend((bytes(32) if coinbase else bytes([17 + index % 100]) * 32) + struct.pack('<I', 0xffffffff if coinbase else index))
        positions[f'input_script_{index}'] = len(data)
        data.extend(compact(len(script)) + script + b'\xfe\xff\xff\xff')
    positions['output_count'] = len(data)
    data.extend(compact(len(outputs)))
    for index, output in enumerate(outputs):
        data.extend(struct.pack('<q', 100_000 + index))
        positions[f'output_script_{index}'] = len(data)
        data.extend(compact(len(output)) + output)
    if extended:
        for index, stack in enumerate(witness or [[] for _ in range(inputs)]):
            positions[f'witness_count_{index}'] = len(data)
            data.extend(compact(len(stack)))
            for item_index, item in enumerate(stack):
                positions[f'witness_item_{index}_{item_index}'] = len(data)
                data.extend(compact(len(item)) + item)
    data.extend(struct.pack('<I', 10))
    return bytes(data), positions


def segments(data):
    """Compact long uniform payloads without hiding any fixture byte."""
    result, literal = [], bytearray()
    position = 0
    while position < len(data):
        end = position + 1
        while end < len(data) and data[end] == data[position]:
            end += 1
        if end - position >= 32:
            if literal:
                result.append({'hex': literal.hex()})
                literal.clear()
            result.append({'byte': data[position], 'count': end - position})
        else:
            literal.extend(data[position:end])
        position = end
    if literal:
        result.append({'hex': literal.hex()})
    return result


def cases():
    rows = []
    def add(name, **kwargs):
        raw, positions = transaction(**kwargs)
        rows.append((name, raw))
        return raw, positions
    legacy, legacy_pos = add('legacy')
    witness, witness_pos = add('witness', witness=[[b'\x30\x01', b'\x02' + b'\x33' * 32]])
    add('witness_mutation_same_txid', witness=[[b'\x30\x02', b'\x02' + b'\x33' * 32]])
    add('mixed_empty_and_present_witness', inputs=2, witness=[[], [b'']])
    add('single_empty_witness_item', witness=[[b'']])
    add('coinbase_with_witness_reserved', script=b'\x01\x01', witness=[[bytes(32)]], coinbase=True)
    add('legacy_coinbase', script=b'\x01\x01', coinbase=True)
    add('p2wsh_and_p2tr_outputs', outputs=[b'\x00\x20' + b'\x44'*32, b'\x51\x20' + b'\x55'*32], witness=[[b'\x01']])
    add('nested_script_and_high_version', script=b'\x16\x00\x14' + b'\x66'*20, version=0x80000000, witness=[[b'\x51']])
    add('253_inputs', inputs=253)
    add('253_outputs', outputs=[b'\x51']*253)
    for size in (252, 253, 65535, 65536):
        add(f'witness_item_{size}', witness=[[b'\x42'*size]])
    for size in (252, 253):
        add(f'input_script_{size}', script=b'\x61'*size)
        add(f'output_script_{size}', outputs=[b'\x61'*size])
    add('superfluous_witness', witness=[[]])
    add('superfluous_witness_zero_inputs', inputs=0, witness=[])
    for flag in (2, 3, 128):
        add(f'unknown_flag_{flag}', witness=[[b'\x01']], flags=flag)
    rows.append(('empty_legacy', b'\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00'))
    rows.append(('trailing_byte', witness+b'\x00'))
    rows.append(('concatenated_transactions', legacy+witness))
    for name, original, position in (
        ('input_count', legacy, legacy_pos['input_count']),
        ('output_count', legacy, legacy_pos['output_count']),
        ('input_script', legacy, legacy_pos['input_script_0']),
        ('output_script', legacy, legacy_pos['output_script_0']),
        ('witness_count', witness, witness_pos['witness_count_0']),
        ('witness_item', witness, witness_pos['witness_item_0_0']),
    ):
        value = original[position]
        rows.append(('noncanonical_'+name, original[:position]+b'\xfd'+struct.pack('<H',value)+original[position+1:]))
    for encoded in (b'\xfe\x00\x00\x00\x02', b'\xfe\x01\x00\x00\x02', b'\xff'+b'\xff'*8,
                    b'\xfe\xff\xff\x00\x00', b'\xff\x00\x00\x01\x00\x00\x00\x00\x00'):
        rows.append(('invalid_count_'+encoded.hex(), legacy[:4]+encoded+legacy[5:]))
    for end in range(len(witness)):
        rows.append((f'truncated_witness_{end}', witness[:end]))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--core-source', type=Path, required=True)
    parser.add_argument('--oracle', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if subprocess.check_output(['git','-C',str(args.core_source),'status','--porcelain','--untracked-files=no']).strip():
        raise SystemExit('Core oracle source has tracked working-tree changes')
    changed = subprocess.check_output(['git','-C',str(args.core_source),'diff','--name-only',CORE_PIN,'HEAD'],text=True).splitlines()
    if any(name.startswith('src/') for name in changed):
        raise SystemExit('Core native source differs from the exact oracle pin')
    rows = cases()
    process = subprocess.run([str(args.oracle.resolve())], input=''.join(raw.hex()+'\n' for _,raw in rows),
                             capture_output=True, text=True, check=True)
    answers = process.stdout.splitlines()
    if len(answers) != len(rows):
        raise SystemExit('Native oracle result count differs')
    fixtures = []
    for (name, raw), answer in zip(rows, answers):
        expected = json.loads(answer)
        if expected['accepted']:
            assert bytes.fromhex(expected['full']) == raw, name
            expected['stripped'] = segments(bytes.fromhex(expected['stripped']))
            del expected['full']
        fixtures.append({'name':name,'raw':segments(raw),'core':expected})
    result = {'core_pin':CORE_PIN,'oracle_source_sha256':hashlib.sha256(Path(__file__).with_name('wire_oracle.cpp').read_bytes()).hexdigest(),
              'scope':'Native transaction decoding/serialization/hashes and synthetic block offsets; not consensus validity or indexer behavior',
              'cases':fixtures}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    header = {key: value for key, value in result.items() if key != 'cases'}
    lines = json.dumps(header, indent=2).splitlines()[:-1]
    lines[-1] += ','
    lines.append('  \"cases\": [')
    for index, case in enumerate(fixtures):
        lines.append('    ' + json.dumps(case, sort_keys=True) + (',' if index + 1 < len(fixtures) else ''))
    lines.extend(['  ]', '}'])
    args.output.write_text('\n'.join(lines) + '\n')
    print(f'{len(fixtures)} Core oracle cases; {sum(row["core"]["accepted"] for row in fixtures)} accepted')


if __name__ == '__main__':
    main()
