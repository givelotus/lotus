import { test } from 'node:test';
import assert from 'node:assert/strict';
import { parseRoute, routeHash } from '../../src/router.js';

test('parse and build hash routes with wallet query', () => {
  assert.deepEqual(pick(parseRoute('')), ['overview', null, null]);
  assert.deepEqual(pick(parseRoute('#/send?w=w1')), ['send', null, 'w1']);
  assert.deepEqual(pick(parseRoute('#/tx/abcd?w=')), ['tx', 'abcd', '']);
  assert.deepEqual(pick(parseRoute('#/nonsense')), ['overview', null, null]);
  assert.equal(routeHash('tx', 'ab', 'my wallet'), '#/tx/ab?w=my%20wallet');
  assert.equal(routeHash('overview', null, ''), '#/overview?w=');
  assert.deepEqual(pick(parseRoute(routeHash('receive', null, 'a&b=c'))), ['receive', null, 'a&b=c']);
});
const pick = (r) => [r.view, r.arg, r.wallet];
