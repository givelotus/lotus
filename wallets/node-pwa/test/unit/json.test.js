import { test } from 'node:test';
import assert from 'node:assert/strict';
import { parse, stringify, Decimal } from '../../src/lib/json.js';

test('safe integers stay numbers, other numbers become exact Decimals', () => {
  const v = parse('{"a":1,"b":-9007199254740991,"c":9007199254740993,"d":50000000.00,"e":1e3,"f":0.1}');
  assert.equal(v.a, 1);
  assert.equal(v.b, -9007199254740991);
  assert.ok(v.c instanceof Decimal);
  assert.equal(v.c.toString(), '9007199254740993');
  assert.equal(v.d.toString(), '50000000.00');
  assert.equal(v.e.toString(), '1e3');
  assert.equal(Number(v.f), 0.1);
});

test('strings, escapes, nesting, literals', () => {
  assert.deepEqual(parse(' [true,false,null,"x\\n\\u00e9\\"",{"k":[]}] '), [true, false, null, 'x\né"', { k: [] }]);
});

test('__proto__ keys are plain data', () => {
  const v = parse('{"__proto__":{"polluted":1}}');
  assert.equal(Object.getPrototypeOf(v), Object.prototype);
  assert.deepEqual(Object.keys(v), ['__proto__']);
  assert.equal({}.polluted, undefined);
});

test('rejects malformed JSON', () => {
  for (const bad of ['', '{', '[1,]', '01', '1.', '"\u0001"', '{"a" 1}', 'nul', '[1] x', '"\\x"']) {
    assert.throws(() => parse(bad), SyntaxError, bad);
  }
});

test('stringify writes Decimals back verbatim and round-trips', () => {
  const text = '{"amount":1234567890.12,"big":123456789012345678901234,"list":[1,"two",null]}';
  assert.equal(stringify(parse(text)), text);
  assert.equal(stringify({ a: new Decimal('0.10') }, 1), '{\n "a": 0.10\n}');
  assert.equal(stringify({ a: undefined, b: 1 }), '{"b":1}');
});
