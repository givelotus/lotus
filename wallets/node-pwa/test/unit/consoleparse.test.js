import { test } from 'node:test';
import assert from 'node:assert/strict';
import { parseCommandLine, evaluate, literalValue, isSensitive, ConsoleSyntaxError } from '../../src/lib/consoleparse.js';
import { Decimal } from '../../src/lib/json.js';

async function run(line, impl) {
  const calls = [];
  const result = await evaluate(parseCommandLine(line), async (m, p) => { calls.push([m, p]); return impl(m, p); });
  return { result, calls };
}

test('whitespace arguments and the JSON-or-string rule', async () => {
  const { calls } = await run(`sendmany "" '{"ecregtest:qq":"10.00"}' 1 "123" abc true null 1.50`, () => null);
  const p = calls[0][1];
  assert.equal(calls[0][0], 'sendmany');
  assert.equal(p[0], '');
  assert.deepEqual(p[1], { 'ecregtest:qq': '10.00' });
  assert.equal(p[2], 1);
  assert.equal(p[3], '123');
  assert.equal(p[4], 'abc');
  assert.equal(p[5], true);
  assert.equal(p[6], null);
  assert.ok(p[7] instanceof Decimal);
  assert.equal(p[7].toString(), '1.50');
});

test('bare JSON objects with spaces inside brackets stay one argument', async () => {
  const { calls } = await run('walletcreatefundedpsbt [] [{"a b": 1}]', () => null);
  assert.deepEqual(calls[0][1], [[], [{ 'a b': 1 }]]);
});

test('nested calls and [index] selection', async () => {
  const impl = (m, p) => {
    if (m === 'getbestblockhash') return 'h1';
    if (m === 'getblockhash') return `hash${p[0]}`;
    if (m === 'getblock') return { hash: p[0], verbosity: p[1], tx: ['t0', 't1'] };
    throw new Error(m);
  };
  let r = await run('getblock(getbestblockhash())', impl);
  assert.deepEqual(r.calls.map((c) => c[0]), ['getbestblockhash', 'getblock']);
  assert.equal(r.result.hash, 'h1');
  r = await run('getblock( getblockhash(0) , 1 )[tx][1]', impl);
  assert.equal(r.result, 't1');
  r = await run('getblock getblockhash(7)', impl);
  assert.equal(r.result.hash, 'hash7');
  r = await run('getblock(getbestblockhash())[hash]', impl);
  assert.equal(r.result, 'h1');
  await assert.rejects(run('getblock(getbestblockhash())[tx][5]', impl), ConsoleSyntaxError);
  await assert.rejects(run('getblock(getbestblockhash())[nope]', impl), ConsoleSyntaxError);
});

test('quotes and escapes', () => {
  const c = parseCommandLine(`setlabel "a \\"b\\"" 'it''s'`);
  assert.equal(c.args[0].text, 'a "b"');
  assert.equal(c.args[1].text, 'it');
  assert.equal(literalValue({ type: 'lit', text: '5', quote: "'" }), 5);
  assert.equal(literalValue({ type: 'lit', text: '5', quote: '"' }), '5');
});

test('empty, comments and syntax errors', () => {
  assert.equal(parseCommandLine('   '), null);
  assert.equal(parseCommandLine('# note'), null);
  for (const bad of ['getblock(', 'getblock(1', 'f("x', '123', 'getblock(1)[0', 'a(b) c']) {
    assert.throws(() => parseCommandLine(bad), ConsoleSyntaxError, bad);
  }
});

test('sensitive commands are kept out of history', () => {
  assert.ok(isSensitive('walletpassphrase secret 60'));
  assert.ok(isSensitive('  encryptwallet x'));
  assert.ok(isSensitive('getinfo(walletpassphrase(x, 1))'));
  assert.ok(isSensitive('createwallet w false false pass'));
  assert.ok(!isSensitive('getwalletinfo'));
  assert.ok(!isSensitive('help walletpassphrase'));
});
