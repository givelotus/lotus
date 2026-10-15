import test from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { compileContract } from '../dist/generic.js';

const options = { contract: 'Compare', bindings: {} };
const source = (op, type = 'Amount') => `contract Compare { function spend(a: ${type}, b: ${type}) { require(a ${op} b); } }`;
const python = process.env.LOTUS_V2_PYTHON ?? 'python3';
const reference = process.env.LOTUS_V2_VM_REFERENCE_PACKAGE ?? fileURLToPath(new URL('../../lotus-v2-reference/', import.meta.url));

// Amount currently uses VM signed int128 N, including for binding validation.
// Native coin values fit uint64; the upper half of uint128 is not positive N.
const max64 = (1n << 64n) - 1n;
const max128 = (1n << 127n) - 1n;
const pairs = [[0n, 0n], [0n, 1n], [1n, 0n], [max64, max64],
  [max64 - 1n, max64], [max64, max64 - 1n], [max64, max64 + 1n],
  [max128, max128], [max128 - 1n, max128], [max128, max128 - 1n]];
const comparisons = { '<': (a,b) => a < b, '<=': (a,b) => a <= b,
  '>': (a,b) => a > b, '>=': (a,b) => a >= b, '==': (a,b) => a === b };

test('Amount and Int <= emit the assigned signed comparison opcode', () => {
  for (const type of ['Amount', 'Int']) {
    const method = compileContract(source('<=', type), { ...options, optimize: false }).methods[0];
    const entry = method.sourceMap.find(entry => entry.op === 'LESSTHANOREQUAL');
    assert.ok(entry);
    assert.equal(method.scriptHex.slice(entry.byteStart * 2, entry.byteEnd * 2), 'ab');
  }
});

test('Amount comparison bytecode agrees with Python VM at uint64 and signed128 boundaries', () => {
  const cases = [];
  for (const optimize of [false, true]) for (const [op, predicate] of Object.entries(comparisons)) {
    const method = compileContract(source(op), { ...options, optimize }).methods[0];
    for (const [a,b] of pairs) cases.push({ script: method.scriptHex, a: String(a), b: String(b), expected: predicate(a,b), op, optimize });
  }
  const result = spawnSync(python, ['-c', `
import json, sys
from lotus_v2_reference.vm import ASSIGNED, VMError, VMProfile, evaluate, number
profile = VMProfile(8192, 8, 8192, 128, 16, 16384, 32, 1000000, 1, {op: 1 for op in ASSIGNED})
for case in json.load(sys.stdin):
    try:
        result = evaluate(bytes.fromhex(case['script']), (number(int(case['a'])), number(int(case['b']))), profile)
        accepted = result.success
    except VMError:
        accepted = False
    assert accepted == case['expected'], case
print('comparison boundary execution passed')
`], { env: { ...process.env, PYTHONPATH: reference }, input: JSON.stringify(cases), encoding: 'utf8' });
  assert.equal(result.status, 0, result.stderr || result.stdout);
  assert.match(result.stdout, /comparison boundary execution passed/);
});

test('Amount bindings retain signed128 limits rather than accepting unsigned128 overflow', () => {
  const boundSource = 'contract Compare<limit: Amount> { function spend(a: Amount) { require(a <= limit); } }';
  const bind = limit => compileContract(boundSource, { contract: 'Compare', bindings: { Compare: { limit: String(limit) } } });
  assert.doesNotThrow(() => bind(max128));
  for (const value of [1n << 127n, (1n << 128n) - 1n]) assert.throws(() => bind(value), /signed 128-bit range/);
});
