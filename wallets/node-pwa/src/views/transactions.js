// Transactions: paged list with filters and search; details modal with
// abandon. Route #/tx/<txid> opens the modal over the list.

import { html, useState } from '../vendor/htm-preact-standalone.mjs';
import { Amount, Modal, ErrorText, Spinner, formatTime, txKind, useAsync, shortHash, CopyButton } from '../ui/components.js';
import { describeError } from '../lib/rpc.js';
import { stringify } from '../lib/json.js';
import { routeHash } from '../router.js';
import { NoWallet } from './overview.js';

const PAGE = 100;
const FILTERS = [
  ['all', 'All'],
  ['send', 'Sent'],
  ['receive', 'Received'],
  ['generate', 'Mined'],
  ['immature', 'Immature'],
  ['unconfirmed', 'Unconfirmed'],
];

/** Filter + search over listtransactions entries (pure, for tests). */
export function filterTransactions(txs, filter, search) {
  const q = search.trim().toLowerCase();
  return txs.filter((t) => {
    if (filter === 'unconfirmed' ? (t.confirmations ?? 0) >= 1 : filter !== 'all' && t.category !== filter) return false;
    if (!q) return true;
    return [t.txid, t.address, t.label, t.comment].some((f) => f && String(f).toLowerCase().includes(q));
  });
}

export function TransactionsView({ app, state, route }) {
  const [page, setPage] = useState(0);
  const [filter, setFilter] = useState('all');
  const [search, setSearch] = useState('');
  const w = state.wallet;
  const list = useAsync(
    () => (w === null ? Promise.resolve([]) : app.walletCall('listtransactions', ['*', PAGE, page * PAGE, true]).then((r) => r.slice().reverse())),
    [w, page, state.walletInfo?.txcount, state.chain?.bestblockhash],
  );
  if (w === null) return html`<${NoWallet} state=${state} />`;
  const p = state.profile;
  const rows = filterTransactions(list.value ?? [], filter, search);
  const closeHash = routeHash('transactions', null, w);
  return html`
    <div class="transactions">
      <h1>Transactions</h1>
      <div class="toolbar">
        <label>Show <select value=${filter} onChange=${(e) => setFilter(e.currentTarget.value)}>
          ${FILTERS.map(([v, l]) => html`<option value=${v}>${l}</option>`)}
        </select></label>
        <input type="search" placeholder="Search address, label or txid" value=${search}
               onInput=${(e) => setSearch(e.currentTarget.value)} aria-label="Search transactions" />
        <span class="spacer"></span>
        <button class="secondary small" disabled=${page === 0} onClick=${() => setPage(page - 1)}>Newer</button>
        <span class="muted">Page ${page + 1}</span>
        <button class="secondary small" disabled=${(list.value ?? []).length < PAGE} onClick=${() => setPage(page + 1)}>Older</button>
      </div>
      <${ErrorText} error=${list.error} />
      ${list.loading && !list.value ? html`<${Spinner} />` : rows.length === 0 ? html`<p class="muted">No matching transactions on this page.</p>` : html`
        <table class="table" data-testid="tx-table">
          <thead><tr><th>Date</th><th>Type</th><th>Label / address</th><th class="num">Amount</th><th class="num">Conf.</th></tr></thead>
          <tbody>
            ${rows.map((t) => html`
              <tr key=${`${t.txid}:${t.vout}:${t.category}`} class="clickable"
                  onClick=${() => { location.hash = routeHash('tx', t.txid, w); }}>
                <td>${formatTime(t.time)}</td>
                <td>${txKind(t)}</td>
                <td class="wrap">${t.label ? html`${t.label} <span class="muted mono">${shortHash(t.address, 8)}</span>` : html`<span class="mono">${t.address ?? ''}</span>`}</td>
                <td class="num"><${Amount} value=${t.amount} profile=${p} sign=${true} /></td>
                <td class="num">${(t.confirmations ?? 0) < 1 ? html`<span class="badge warn">${t.confirmations ?? 0}</span>` : t.confirmations}</td>
              </tr>`)}
          </tbody>
        </table>`}
      ${route.view === 'tx' && route.arg ? html`<${TxDetail} app=${app} state=${state} txid=${route.arg}
          onClose=${() => { location.hash = closeHash; }} />` : null}
    </div>`;
}

function TxDetail({ app, state, txid, onClose }) {
  const p = state.profile;
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState(null);
  const [showRaw, setShowRaw] = useState(false);
  const tx = useAsync(() => app.walletCall('gettransaction', [txid, true, true]), [txid, state.walletInfo?.txcount, state.chain?.bestblockhash]);
  const t = tx.value;
  const abandoned = t?.details?.some((d) => d.abandoned);
  const canAbandon = t && Number(t.confirmations) < 1 && !abandoned;
  const abandon = async () => {
    if (!confirm('Abandon this transaction? Its inputs become spendable again. This only works if the transaction is not in the mempool.')) return;
    setBusy(true);
    setActionError(null);
    try {
      await app.walletCall('abandontransaction', [txid]);
      app.toast('Transaction abandoned');
      tx.reload();
      app.refresh();
    } catch (e) {
      setActionError(e);
    } finally {
      setBusy(false);
    }
  };
  return html`
    <${Modal} title="Transaction details" onClose=${onClose} wide=${true}>
      ${tx.error ? html`<p class="error">${describeError(tx.error)}</p>` : !t ? html`<${Spinner} />` : html`
        <dl class="details" data-testid="tx-detail">
          <dt>Transaction ID</dt><dd class="mono wrap">${t.txid} <${CopyButton} text=${t.txid} toast=${app.toast} /></dd>
          <dt>Status</dt><dd>${Number(t.confirmations) > 0 ? `${t.confirmations} confirmation${t.confirmations === 1 ? '' : 's'}`
            : Number(t.confirmations) < 0 ? `conflicted (${t.confirmations})` : abandoned ? 'abandoned' : 'unconfirmed'}</dd>
          <dt>Date</dt><dd>${formatTime(t.time)}</dd>
          ${t.blockhash ? html`<dt>Block</dt><dd class="mono wrap">${t.blockheight !== undefined ? `${t.blockheight} · ` : ''}${t.blockhash}</dd>` : null}
          <dt>Net amount</dt><dd><${Amount} value=${t.amount} profile=${p} sign=${true} /></dd>
          ${t.fee !== undefined ? html`<dt>Fee</dt><dd><${Amount} value=${t.fee} profile=${p} /></dd>` : null}
          ${t.decoded ? html`<dt>Size</dt><dd>${t.decoded.size} bytes</dd>` : null}
          ${t.comment ? html`<dt>Comment</dt><dd>${t.comment}</dd>` : null}
          ${(t.walletconflicts ?? []).length ? html`<dt>Conflicts</dt><dd class="mono wrap">${t.walletconflicts.join(', ')}</dd>` : null}
        </dl>
        <h3>Entries</h3>
        <table class="table">
          <thead><tr><th>Type</th><th>Address</th><th>Label</th><th class="num">Output</th><th class="num">Amount</th></tr></thead>
          <tbody>
            ${(t.details ?? []).map((d) => html`
              <tr><td>${txKind(d)}</td><td class="mono wrap">${d.address ?? ''}</td><td>${d.label ?? ''}</td>
                  <td class="num">${d.vout}</td><td class="num"><${Amount} value=${d.amount} profile=${p} sign=${true} /></td></tr>`)}
          </tbody>
        </table>
        <${ErrorText} error=${actionError} />
        <div class="actions">
          ${canAbandon ? html`<button class="warn" disabled=${busy} onClick=${abandon}>Abandon transaction</button>` : null}
          <button class="secondary" onClick=${() => setShowRaw(!showRaw)}>${showRaw ? 'Hide' : 'Show'} raw data</button>
        </div>
        ${showRaw ? html`<pre class="raw">${stringify(t.decoded ?? t, 2)}</pre>` : null}`}
    <//>`;
}
