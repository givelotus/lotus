// Overview: balances and recent transactions.

import { html } from '../vendor/htm-preact-standalone.mjs';
import { Amount, formatTime, txKind, Spinner } from '../ui/components.js';
import { routeHash } from '../router.js';

export function NoWallet({ state }) {
  return html`
    <section class="card" data-testid="no-wallet">
      <h2>No wallet loaded</h2>
      <p>${(state.wallets ?? []).length === 0
        ? 'This node has no wallet loaded. Create a new wallet or open an existing one.'
        : 'Select a wallet in the top bar.'}</p>
      <a class="button" href=${routeHash('wallets')}>Create or open a wallet</a>
    </section>`;
}

export function OverviewView({ state }) {
  if (state.wallet === null) return html`<${NoWallet} state=${state} />`;
  const p = state.profile;
  const b = state.balances;
  if (!b) return html`<${Spinner} />`;
  const rows = [
    ['Available', b.mine.trusted, 'available'],
    ['Pending', b.mine.untrusted_pending, 'pending'],
    ['Immature', b.mine.immature, 'immature'],
  ];
  if (b.mine.used !== undefined) rows.push(['Used (address reuse)', b.mine.used, 'used']);
  const recent = (state.txs ?? []).slice(0, 10);
  return html`
    <div class="grid two">
      <section class="card balances" aria-labelledby="bal-title">
        <h2 id="bal-title">Balances</h2>
        <dl>
          ${rows.map(([label, v, id]) => html`<dt>${label}</dt><dd data-testid=${`balance-${id}`}><${Amount} value=${v} profile=${p} /></dd>`)}
        </dl>
        ${b.watchonly ? html`
          <h3>Watch-only</h3>
          <dl>
            <dt>Available</dt><dd><${Amount} value=${b.watchonly.trusted} profile=${p} /></dd>
            <dt>Pending</dt><dd><${Amount} value=${b.watchonly.untrusted_pending} profile=${p} /></dd>
            <dt>Immature</dt><dd><${Amount} value=${b.watchonly.immature} profile=${p} /></dd>
          </dl>` : null}
      </section>
      <section class="card" aria-labelledby="recent-title">
        <h2 id="recent-title">Recent transactions</h2>
        ${recent.length === 0 ? html`<p class="muted">No transactions yet.</p>` : html`
          <ul class="tx-list">
            ${recent.map((t) => html`
              <li key=${`${t.txid}:${t.vout}:${t.category}`}>
                <a href=${routeHash('tx', t.txid, state.wallet)}>
                  <span class="tx-kind">${txKind(t)}</span>
                  <span class="tx-time muted">${formatTime(t.time)}</span>
                  <span class="tx-label">${t.label || t.address || ''}</span>
                  <${Amount} value=${t.amount} profile=${p} sign=${true} />
                  ${(t.confirmations ?? 0) < 1 ? html`<span class="badge warn">unconfirmed</span>` : null}
                </a>
              </li>`)}
          </ul>`}
        <a href=${routeHash('transactions', null, state.wallet)}>All transactions</a>
      </section>
    </div>`;
}
