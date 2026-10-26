import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createPoller } from '../../src/lib/poller.js';

function fakeTimers() {
  let now = 0;
  let seq = 0;
  const q = new Map();
  return {
    setTimeout(fn, ms) { const id = ++seq; q.set(id, { fn, at: now + ms }); return id; },
    clearTimeout(id) { q.delete(id); },
    get now() { return now; },
    pending() { return [...q.values()].map((t) => t.at - now).sort((a, b) => a - b); },
    async advance(ms) {
      const end = now + ms;
      for (let i = 0; i < 10; i++) await Promise.resolve();
      for (;;) {
        const due = [...q.entries()].filter(([, t]) => t.at <= end).sort((a, b) => a[1].at - b[1].at)[0];
        if (!due) break;
        q.delete(due[0]);
        now = due[1].at;
        due[1].fn();
        for (let i = 0; i < 10; i++) await Promise.resolve();
      }
      now = end;
    },
  };
}

test('ticks every 5 s when visible, 30 s when hidden', async () => {
  const t = fakeTimers();
  let visible = true, n = 0;
  const p = createPoller({ tick: async () => { n++; }, isVisible: () => visible, setTimeout: t.setTimeout, clearTimeout: t.clearTimeout });
  p.start();
  await t.advance(0);
  assert.equal(n, 1);
  await t.advance(5000);
  assert.equal(n, 2);
  visible = false;
  await t.advance(5000);
  assert.equal(n, 3);
  await t.advance(29000);
  assert.equal(n, 3);
  await t.advance(1000);
  assert.equal(n, 4);
  p.stop();
  await t.advance(100000);
  assert.equal(n, 4);
});

test('ticks never overlap; a poke during a tick runs once afterwards', async () => {
  const t = fakeTimers();
  let active = 0, maxActive = 0, n = 0, release;
  const p = createPoller({
    tick: () => { n++; active++; maxActive = Math.max(maxActive, active); return new Promise((r) => { release = () => { active--; r(); }; }); },
    setTimeout: t.setTimeout, clearTimeout: t.clearTimeout, isVisible: () => true,
  });
  p.start();
  await t.advance(0);
  assert.equal(n, 1);
  p.poke(); p.poke(); p.poke();
  await t.advance(20000);
  assert.equal(n, 1, 'no second tick while the first is in flight');
  release();
  await t.advance(0);
  assert.equal(n, 2, 'exactly one follow-up tick');
  assert.equal(maxActive, 1);
  release();
  await t.advance(0);
  assert.equal(n, 2);
  p.stop();
});

test('failures back off 1 s doubling to 30 s, success resets', async () => {
  const t = fakeTimers();
  let fail = true, n = 0;
  const p = createPoller({ tick: async () => { n++; if (fail) throw new Error('down'); }, setTimeout: t.setTimeout, clearTimeout: t.clearTimeout, isVisible: () => true });
  p.start();
  await t.advance(0);
  const delays = [];
  for (let i = 0; i < 7; i++) { delays.push(p.backoffMs); await t.advance(p.backoffMs); }
  assert.deepEqual(delays, [1000, 2000, 4000, 8000, 16000, 30000, 30000]);
  fail = false;
  await t.advance(30000);
  assert.equal(p.backoffMs, 0);
  assert.deepEqual(t.pending(), [5000]);
  assert.equal(p.stats.failures, 8);
  p.stop();
});

test('long-poll pokes a tick when the best block changes', async () => {
  const t = fakeTimers();
  let n = 0, blocks = [];
  const hashes = ['h0', 'h0', 'h1'];
  const p = createPoller({
    tick: async () => { n++; },
    waitForBlock: async () => { const h = hashes.shift(); if (!h) return new Promise(() => {}); return h; },
    setTimeout: t.setTimeout, clearTimeout: t.clearTimeout, isVisible: () => true,
  });
  p.onChange('block', () => blocks.push(1));
  p.setBestHash('h0');
  p.start();
  await t.advance(0);
  assert.equal(blocks.length, 1);
  assert.equal(n, 2, 'initial tick plus one poked by the new block');
  p.stop();
});

test('long-poll errors back off', async () => {
  const t = fakeTimers();
  let calls = 0;
  const p = createPoller({
    tick: async () => {}, waitForBlock: async () => { calls++; throw new Error('x'); },
    setTimeout: t.setTimeout, clearTimeout: t.clearTimeout, isVisible: () => true,
  });
  p.start();
  await t.advance(0);
  assert.equal(calls, 1);
  await t.advance(999);
  assert.equal(calls, 1);
  await t.advance(1);
  assert.equal(calls, 2);
  await t.advance(2000);
  assert.equal(calls, 3);
  p.stop();
});

test('long-poll pauses while the page is hidden', async () => {
  const t = fakeTimers();
  let calls = 0, visible = false;
  const p = createPoller({
    tick: async () => {}, waitForBlock: () => { calls++; return new Promise(() => {}); },
    isVisible: () => visible, setTimeout: t.setTimeout, clearTimeout: t.clearTimeout,
  });
  p.start();
  await t.advance(10000);
  assert.equal(calls, 0);
  visible = true;
  await t.advance(1000);
  assert.equal(calls, 1);
  p.stop();
});
