import test from 'node:test';
import assert from 'node:assert/strict';
import { compileContract, compileContractAsync, compileContractWithTrace } from '../dist/generic.js';
import { PromiseScheduler } from '../dist/scheduler.js';

const options = contract => ({ contract, bindings: {}, optimize: false });

test('forward declarations compile through awaited leaf and root jobs', async () => {
  const source = `contract A { function use() { require(contract_root(B) == contract_root(B)); require(leaf_hash(B.one) == leaf_hash(B.one)); } }
    contract B { function one() { require(true); } function two() { require(false == false); } }`;
  const { artifact, trace } = await compileContractWithTrace(source, options('A'));
  assert.deepEqual(artifact, compileContract(source, options('A')));
  assert.deepEqual(trace.filter(event => event.kind === 'start').map(event => event.job),
    ['root:A', 'leaf:A.use', 'root:B', 'leaf:B.one', 'leaf:B.two']);
  assert(trace.some(event => event.kind === 'await' && event.job === 'leaf:A.use' && event.dependency === 'root:B'));
  assert(trace.some(event => event.kind === 'start' && event.job === 'leaf:A.use' && Number.isInteger(event.source?.start)));
  assert(trace.findIndex(event => event.kind === 'resolve' && event.job === 'root:B') <
    trace.findIndex(event => event.kind === 'resolve' && event.job === 'leaf:A.use'));
});

test('diamond dependencies share one in-flight leaf job', async () => {
  const source = `contract A {
    function one() { require(leaf_hash(B.one) == leaf_hash(B.one)); }
    function two() { require(contract_root(B) == contract_root(B)); }
  }
  contract B { function one() { require(true); } function two() { require(false == false); } }`;
  const { trace } = await compileContractWithTrace(source, options('A'));
  assert.equal(trace.filter(event => event.kind === 'start' && event.job === 'leaf:B.one').length, 1);
  assert(trace.some(event => event.kind === 'await' && event.job === 'leaf:A.one' && event.dependency === 'leaf:B.one'));
  assert(trace.some(event => event.kind === 'await' && event.job === 'root:B' && event.dependency === 'leaf:B.one'));
});

test('dependencies inside helpers declared after their callers are awaited', async () => {
  const source = `contract A { function check() { require(target() == contract_root(B)); } }
    contract B { function one() { require(true); } }
    function target(): ContractRootHash { return contract_root(B); }`;
  const { artifact, trace } = await compileContractWithTrace(source, options('A'));
  assert.deepEqual(artifact, compileContract(source, options('A')));
  assert.equal(trace.filter(event => event.kind === 'start' && event.job === 'root:B').length, 1);
  assert(trace.some(event => event.kind === 'await' && event.job === 'leaf:A.check' && event.dependency === 'root:B'));
});

test('diamond helper expansion scans each declaration once before bounded compilation', async () => {
  const helpers = ['function h0(): Bool { return contract_root(B) == contract_root(B); }'];
  for (let i = 1; i <= 15; i++) helpers.push(`function h${i}(): Bool { return h${i-1}() && h${i-1}(); }`);
  const source = `contract A { function check() { require(h15()); } }
    contract B { function one() { require(true); } } ${helpers.join(' ')}`;
  const events = [];
  await assert.rejects(compileContractAsync(source, options('A'), event => events.push(event)), /MAX_SCRIPT_BYTES exceeded|helper expansion budget|type inference visit budget/);
  assert.equal(events.filter(event => event.kind === 'start' && event.job === 'root:B').length, 1);
});

test('mixed root/leaf cycles reject with stable paths and no waiting', async () => {
  const source = `contract A { function one() { require(contract_root(B) == contract_root(B)); } }
    contract B { function one() { require(leaf_hash(A.one) == leaf_hash(A.one)); } }`;
  const errors = [];
  for (let i = 0; i < 2; i++) {
    await assert.rejects(compileContractAsync(source, options('A')), error => {
      errors.push(error.message);
      return /dependency cycle: leaf:A.one@UTF-8 bytes \d+\.\.\d+ -> root:B@UTF-8 bytes \d+\.\.\d+ -> leaf:B.one@UTF-8 bytes \d+\.\.\d+ -> leaf:A.one@UTF-8 bytes \d+\.\.\d+/.test(error.message);
    });
  }
  assert.deepEqual(errors, [errors[0], errors[0]]);
  await assert.rejects(compileContractAsync('contract C { function m() { require(leaf_hash(C.m) == leaf_hash(C.m)); } }', options('C')), /dependency cycle/);
});

test('unused invalid declarations do not block selected contract and errors reject', async () => {
  const source = `contract Good { function m() { require(true); } }
    contract Bad { function m() { require(leaf_hash(Missing.m) == leaf_hash(Missing.m)); } }`;
  assert.deepEqual(await compileContractAsync(source, options('Good')), compileContract(source, options('Good')));
  await assert.rejects(compileContractAsync('contract C { function m() { require(missing); } }', options('C')), /unbound name/);
});

test('promise scheduler memoizes concurrent callers and propagates a failure', async () => {
  const events = [];
  const scheduler = new PromiseScheduler(event => events.push(event));
  let calls = 0;
  scheduler.register('shared', [], () => { calls++; return 7; });
  scheduler.register('left', ['shared'], () => 1);
  scheduler.register('right', ['shared'], () => 2);
  assert.deepEqual(await Promise.all([scheduler.run('left'), scheduler.run('right')]), [1, 2]);
  assert.equal(calls, 1);
  assert.equal(events.filter(event => event.kind === 'start' && event.job === 'shared').length, 1);
  scheduler.register('bad', [], () => { throw new Error('bad job'); });
  await assert.rejects(scheduler.run('bad'), /bad job/);
  assert(events.some(event => event.kind === 'reject' && event.job === 'bad' && event.error === 'bad job'));
});

test('scheduler enforces job, edge and dependency-depth limits', async () => {
  const jobs = new PromiseScheduler(undefined, { maxJobs: 2 });
  jobs.register('a', [], () => 1);
  jobs.register('b', [], () => 2);
  assert.throws(() => jobs.register('c', [], () => 3), /job limit exceeded/);

  const edges = new PromiseScheduler(undefined, { maxEdges: 1 });
  edges.register('a', ['b', 'c'], () => 1, { start: 10, end: 11 });
  edges.register('b', [], () => 2);
  edges.register('c', [], () => 3);
  assert.throws(() => edges.run('a'), /edge limit exceeded.*a@UTF-8 bytes 10\.\.11/);

  const depth = new PromiseScheduler(undefined, { maxDepth: 2 });
  depth.register('a', ['b'], () => 1);
  depth.register('b', ['c'], () => 2);
  depth.register('c', [], () => 3, { start: 20, end: 21 });
  assert.throws(() => depth.run('a'), /depth limit exceeded.*c@UTF-8 bytes 20\.\.21/);
});

test('trace callback errors cannot strand sibling dependency promises', async () => {
  const scheduler = new PromiseScheduler(() => { throw new Error('observer'); });
  scheduler.register('a', ['b', 'c'], () => 3);
  scheduler.register('b', [], () => 1);
  scheduler.register('c', [], () => 2);
  assert.equal(await scheduler.run('a'), 3);
});
