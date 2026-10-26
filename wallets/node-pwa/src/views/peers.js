// Peers and banned peers: disconnect, ban (1 h / 1 d / 1 w / 1 y), unban, clear.

import { html, useState } from '../vendor/htm-preact-standalone.mjs';
import { ErrorText, useAsync, formatBytes, formatDuration, formatTime, Spinner } from '../ui/components.js';
import { describeError } from '../lib/rpc.js';

const BAN_TIMES = [['1 hour', 3600], ['1 day', 86400], ['1 week', 604800], ['1 year', 31536000]];

/** "1.2.3.4:5678" → "1.2.3.4", "[::1]:123" → "::1"; anything else unchanged. */
export function hostOfPeerAddr(addr) {
  const s = String(addr ?? '');
  const v6 = /^\[([^\]]+)\](?::\d+)?$/.exec(s);
  if (v6) return v6[1];
  const v4 = /^([^:]+):\d+$/.exec(s);
  return v4 ? v4[1] : s;
}

export function PeersView({ app, state }) {
  const peers = useAsync(() => app.rpc.call('getpeerinfo'), [], { intervalMs: 5000 });
  const banned = useAsync(() => app.rpc.call('listbanned'), [], { intervalMs: 5000 });
  const [error, setError] = useState(null);
  const [banFor, setBanFor] = useState(86400);

  const act = async (fn, okText) => {
    setError(null);
    try {
      await fn();
      if (okText) app.toast(okText);
    } catch (e) {
      setError(e);
    }
    peers.reload();
    banned.reload();
    app.refresh();
  };

  const n = state.net;
  return html`
    <div class="peers">
      <h1>Peers</h1>
      <p class="muted">
        ${n ? `${n.connections ?? 0} connections. P2P network is ${n.networkactive ? 'active' : 'disabled'}.` : ''}
        Use the network switch in the status bar to turn all P2P activity off or on.
      </p>
      <${ErrorText} error=${error} />
      <section class="card">
        <div class="toolbar">
          <h2>Connected peers</h2>
          <span class="spacer"></span>
          <label>Ban for <select value=${banFor} onChange=${(e) => setBanFor(Number(e.currentTarget.value))}>
            ${BAN_TIMES.map(([l, s]) => html`<option value=${s}>${l}</option>`)}
          </select></label>
        </div>
        ${peers.error ? html`<p class="error">${describeError(peers.error)}</p>` : !peers.value ? html`<${Spinner} />`
          : peers.value.length === 0 ? html`<p class="muted" data-testid="no-peers">No peers connected.</p>` : html`
          <table class="table" data-testid="peer-table">
            <thead><tr><th>ID</th><th>Address</th><th>Direction</th><th>Client</th><th class="num">Ping</th>
              <th class="num">Sent</th><th class="num">Received</th><th class="num">Connected</th><th></th></tr></thead>
            <tbody>
              ${peers.value.map((p) => html`
                <tr key=${p.id}>
                  <td>${p.id}</td><td class="mono">${p.addr}</td><td>${p.inbound ? 'inbound' : 'outbound'}${p.connection_type ? ` (${p.connection_type})` : ''}</td>
                  <td>${p.subver}</td><td class="num">${p.pingtime !== undefined ? `${Math.round(Number(p.pingtime) * 1000)} ms` : '–'}</td>
                  <td class="num">${formatBytes(p.bytessent)}</td><td class="num">${formatBytes(p.bytesrecv)}</td>
                  <td class="num">${formatDuration(Date.now() / 1000 - Number(p.conntime))}</td>
                  <td class="row-actions">
                    <button class="secondary small" onClick=${() => act(() => app.rpc.call('disconnectnode', ['', p.id]), `Disconnected peer ${p.id}`)}>Disconnect</button>
                    <button class="warn small" onClick=${() => act(() => app.rpc.call('setban', [hostOfPeerAddr(p.addr), 'add', banFor]), `Banned ${hostOfPeerAddr(p.addr)}`)}>Ban</button>
                  </td>
                </tr>`)}
            </tbody>
          </table>`}
      </section>
      <section class="card">
        <div class="toolbar">
          <h2>Banned</h2>
          <span class="spacer"></span>
          <button class="secondary small" disabled=${!(banned.value ?? []).length} onClick=${() => act(() => app.rpc.call('clearbanned'), 'Ban list cleared')}>Clear all</button>
        </div>
        ${banned.error ? html`<p class="error">${describeError(banned.error)}</p>` : !banned.value ? html`<${Spinner} />`
          : banned.value.length === 0 ? html`<p class="muted" data-testid="no-bans">No banned addresses.</p>` : html`
          <table class="table" data-testid="ban-table">
            <thead><tr><th>Address</th><th>Banned</th><th>Until</th><th></th></tr></thead>
            <tbody>
              ${banned.value.map((b) => html`
                <tr key=${b.address}><td class="mono">${b.address}</td><td>${formatTime(b.ban_created)}</td><td>${formatTime(b.banned_until)}</td>
                  <td><button class="secondary small" onClick=${() => act(() => app.rpc.call('setban', [b.address, 'remove']), `Unbanned ${b.address}`)}>Unban</button></td></tr>`)}
            </tbody>
          </table>`}
      </section>
    </div>`;
}
