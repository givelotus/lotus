import test from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { join } from 'node:path';
import { compileContract, compileContractAsync } from '../dist/generic.js';
import { optimizeInstructions } from '../dist/optimizer.js';

test('unmodeled stack operations disable symbolic rewriting', () => {
  const instruction = (op, byte, delta) => ({ wire:Uint8Array.of(byte), delta,
    map:{ op, source:{ start:0, end:1 }, byteStart:0, byteEnd:1 } });
  const entries = [instruction('UNMODELED_STACK_OP',0x71,2),
    instruction('DUP',0x7a,1), instruction('DUP',0x7a,1),
    instruction('EQUALVERIFY',0x92,-2)];
  assert.deepEqual(optimizeInstructions(entries,1),entries);
});

test('scheduled symbolic compilation agrees with unoptimized VM on seeded expressions', async t => {
  const python = process.env.LOTUS_V2_PYTHON ?? 'python3';
  const reference = process.env.LOTUS_V2_REFERENCE_PATH ?? join(import.meta.dirname,'../../lotus-v2-reference');
  const env = { ...process.env, PYTHONPATH:reference };
  const probe = spawnSync(python,['-c','import blake3; import lotus_v2_reference.vm'],{ env, encoding:'utf8' });
  if (probe.status !== 0) { t.skip('install reference requirements-vm.txt and set LOTUS_V2_PYTHON'); return; }
  let seed = 0x13579;
  const choose = n => { seed = (Math.imul(seed,1664525) + 1013904223) >>> 0; return seed % n; };
  const ints = ['x','y','0','1','-1'];
  const atoms = ['flag','!flag','x == x','x == y','x + 1 > y','x - y == 0','true','false'];
  function expression(depth) {
    if (!depth || choose(3) === 0) return atoms[choose(atoms.length)];
    if (choose(3) === 0) return `${ints[choose(ints.length)]} == ${ints[choose(ints.length)]}`;
    return `(${expression(depth - 1)}) ${choose(2) ? '&&' : '||'} (${expression(depth - 1)})`;
  }
  const encode = n => {
    let value = BigInt.asUintN(128,n), hex = '';
    for (let i = 0; i < 16; i++, value >>= 8n) hex += Number(value & 255n).toString(16).padStart(2,'0');
    return hex;
  };
  const max = (1n << 127n) - 1n, min = -(1n << 127n);
  const argumentsList = [
    [encode(0n),encode(0n),encode(0n)], [encode(1n),encode(1n),encode(0n)],
    [encode(1n),encode(max),encode(-1n)], [encode(0n),encode(min),encode(1n)],
    [encode(2n),encode(0n),encode(0n)], ['01',encode(0n),encode(0n)],
    [encode(1n),'',encode(0n)], [encode(0n),encode(0n),'ff'.repeat(32)],
  ];
  const cases = [];
  for (let i = 0; i < 32; i++) {
    const source = `contract C { function m(flag: Bool, x: Int, y: Int) {
      if (flag) { require(${expression(3)}); } else { require(${expression(3)}); }
    } }`;
    const options = { contract:'C', bindings:{} };
    const scheduled = await compileContractAsync(source,options);
    assert.deepEqual(scheduled,compileContract(source,options));
    const plain = compileContract(source,{ ...options, optimize:false });
    for (const args of argumentsList) cases.push({ name:`seeded ${i}`, source, args,
      before:plain.methods[0].scriptHex, after:scheduled.methods[0].scriptHex });
  }
  const run = spawnSync(python,['-c',`
import json, sys
from lotus_v2_reference.vm import ASSIGNED, VMError, VMProfile, evaluate
p = VMProfile(8192, 16, 8192, 128, 64, 65536, 32, 1000000, 1, {op: 1 for op in ASSIGNED})
def run(script, args):
    try:
        r = evaluate(bytes.fromhex(script), tuple(bytes.fromhex(a) for a in args), p, input_count=0, output_count=0)
        return ('ok', r.stack, r.success, r.charged_cost)
    except VMError:
        return ('error',)
cases = json.load(sys.stdin)
for c in cases:
    a, b = run(c['before'], c['args']), run(c['after'], c['args'])
    if a[:3] != b[:3] or (a[0] == 'ok' and b[3] > a[3]):
        raise AssertionError((c, a, b))
print(f'{len(cases)} seeded VM comparisons passed')
`],{ env, encoding:'utf8', input:JSON.stringify(cases), maxBuffer:4 * 1024 * 1024 });
  assert.equal(run.status,0,run.stderr || run.stdout);
  assert.match(run.stdout,/256 seeded VM comparisons passed/);
});
