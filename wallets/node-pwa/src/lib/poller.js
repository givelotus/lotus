// Refresh loop plus waitfornewblock long-poll.
//
// - tick() runs every `visibleMs` while the page is visible and every
//   `hiddenMs` otherwise. Ticks never overlap: a tick requested while one is
//   in flight is skipped (and one more runs right after, if it was a poke).
// - After a failed tick the next one waits with exponential backoff
//   (1 s doubling to 30 s). A success resets it.
// - The long-poll loop calls waitForBlock(); when it returns a different
//   block hash it pokes an immediate tick. Its errors back off the same way.
//   It runs only while the page is visible: every waiting call holds one of
//   the node's RPC worker threads (-rpcthreads) for up to 30 s.
//
// Timers are injected so tests can use fake ones. onChange(topic, fn) is the
// hook views subscribe to; a later WebSocket event stream can call emit()
// instead without touching views.

/**
 * @param {{
 *   tick: () => Promise<void>,
 *   waitForBlock?: (lastHash: string|null, signal: AbortSignal) => Promise<string|null>,
 *   isVisible?: () => boolean,
 *   setTimeout?: typeof setTimeout, clearTimeout?: typeof clearTimeout,
 *   visibleMs?: number, hiddenMs?: number, minBackoffMs?: number, maxBackoffMs?: number,
 * }} cfg
 */
export function createPoller(cfg) {
  const st = cfg.setTimeout ?? globalThis.setTimeout.bind(globalThis);
  const ct = cfg.clearTimeout ?? globalThis.clearTimeout.bind(globalThis);
  const visibleMs = cfg.visibleMs ?? 5000;
  const hiddenMs = cfg.hiddenMs ?? 30000;
  const minBackoff = cfg.minBackoffMs ?? 1000;
  const maxBackoff = cfg.maxBackoffMs ?? 30000;
  const isVisible = cfg.isVisible ?? (() => globalThis.document?.visibilityState !== 'hidden');

  let running = false;
  let inFlight = false;
  let pokedWhileBusy = false;
  let timer = null;
  let backoff = 0;
  let lpBackoff = 0;
  let lpTimer = null;
  let lpAbort = null;
  let lastHash = null;
  const listeners = new Map();
  const stats = { ticks: 0, skipped: 0, failures: 0 };

  function schedule(ms) {
    if (!running) return;
    if (timer !== null) ct(timer);
    timer = st(() => { timer = null; void runTick(); }, ms);
  }

  async function runTick() {
    if (!running) return;
    if (inFlight) { stats.skipped++; return; }
    inFlight = true;
    let ok = true;
    try {
      stats.ticks++;
      await cfg.tick();
    } catch {
      ok = false;
      stats.failures++;
    } finally {
      inFlight = false;
    }
    if (!running) return;
    if (ok) backoff = 0;
    else backoff = backoff ? Math.min(backoff * 2, maxBackoff) : minBackoff;
    if (pokedWhileBusy && ok) { pokedWhileBusy = false; schedule(0); return; }
    pokedWhileBusy = false;
    schedule(ok ? (isVisible() ? visibleMs : hiddenMs) : backoff);
  }

  async function longPoll() {
    if (!running || !cfg.waitForBlock) return;
    if (!isVisible()) {
      // Each waiting long-poll occupies one of the node's RPC worker threads
      // for up to 30 s, so hidden tabs leave it to the periodic tick.
      lpTimer = st(() => { lpTimer = null; void longPoll(); }, 1000);
      return;
    }
    lpAbort = new AbortController();
    try {
      const hash = await cfg.waitForBlock(lastHash, lpAbort.signal);
      lpBackoff = 0;
      if (hash && hash !== lastHash) {
        const first = lastHash === null;
        lastHash = hash;
        if (!first) { emit('block'); poke(); }
      }
      if (running) lpTimer = st(() => { lpTimer = null; void longPoll(); }, 0);
    } catch {
      if (!running) return;
      lpBackoff = lpBackoff ? Math.min(lpBackoff * 2, maxBackoff) : minBackoff;
      lpTimer = st(() => { lpTimer = null; void longPoll(); }, lpBackoff);
    }
  }

  function poke() {
    if (!running) return;
    if (inFlight) { pokedWhileBusy = true; return; }
    schedule(0);
  }

  function emit(topic, data) {
    for (const fn of listeners.get(topic) ?? []) {
      try { fn(data); } catch (e) { console.error(e); }
    }
  }

  return {
    start() {
      if (running) return;
      running = true;
      schedule(0);
      void longPoll();
    },
    stop() {
      running = false;
      if (timer !== null) ct(timer);
      if (lpTimer !== null) ct(lpTimer);
      timer = lpTimer = null;
      lpAbort?.abort();
    },
    poke,
    emit,
    /** Note the best block hash seen by a tick, so the long-poll compares against it. */
    setBestHash(hash) { lastHash = hash; },
    /** @returns {() => void} unsubscribe */
    onChange(topic, fn) {
      if (!listeners.has(topic)) listeners.set(topic, new Set());
      listeners.get(topic).add(fn);
      return () => listeners.get(topic).delete(fn);
    },
    get backoffMs() { return backoff; },
    get running() { return running; },
    stats,
  };
}
