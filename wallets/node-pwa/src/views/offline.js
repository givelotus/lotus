// Shown when the node cannot be reached, and while it is warming up.

import { html, useEffect, useState } from '../vendor/htm-preact-standalone.mjs';

export function OfflineView({ app, state }) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, []);
  const since = state.offlineSince ? Math.round((now - state.offlineSince) / 1000) : 0;
  return html`
    <main class="center-page">
      <div class="card" role="alert" data-testid="offline">
        <h1>Node unreachable</h1>
        <p>The wallet cannot reach the node${since ? ` (for ${since} s)` : ''}. It reconnects automatically.</p>
        <p class="muted">Check that the node is running. If it was restarted, you will need to log in again.</p>
        <button onClick=${() => app.retryNow()}>Retry now</button>
      </div>
    </main>`;
}

export function WarmupView({ state }) {
  return html`
    <main class="center-page">
      <div class="card" aria-live="polite" data-testid="warmup">
        <h1>Node is starting</h1>
        <p>${state.warmup || 'Waiting for the node…'}</p>
      </div>
    </main>`;
}

export function BootView() {
  return html`<main class="center-page"><p class="muted">Connecting to the node…</p></main>`;
}
