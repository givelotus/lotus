// Receive: request form, payment request modal with QR, request history
// (IndexedDB, per wallet), and amounts received by address.

import { html, useEffect, useState } from '../vendor/htm-preact-standalone.mjs';
import { Amount, Modal, ErrorText, Field, QR, CopyButton, formatTime, qrSvgDocument, qrPngBlob, downloadBlob, useAsync } from '../ui/components.js';
import { parseAmount, toRpc, AmountError } from '../lib/amount.js';
import { buildUri } from '../lib/uri.js';
import { listRequests, addRequest, deleteRequest } from '../lib/storage.js';
import { NoWallet } from './overview.js';

export function ReceiveView({ app, state }) {
  const [label, setLabel] = useState('');
  const [amount, setAmount] = useState('');
  const [message, setMessage] = useState('');
  const [amountError, setAmountError] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [shown, setShown] = useState(null);
  const [history, setHistory] = useState([]);
  const p = state.profile;
  const w = state.wallet;
  const scope = `${p.chainIdentifier}:${w}`;

  const reloadHistory = () => { if (w !== null) listRequests(scope).then(setHistory); };
  useEffect(reloadHistory, [scope]);
  const received = useAsync(
    () => (w === null ? Promise.resolve([]) : app.walletCall('listreceivedbyaddress', [0, true])),
    [w, state.walletInfo?.txcount],
  );
  if (w === null) return html`<${NoWallet} state=${state} />`;

  const createAddress = async () => {
    setError(null);
    setBusy(true);
    try {
      const address = await app.walletCall('getnewaddress', [label.trim()]);
      setShown({ address, label: label.trim(), kind: 'address' });
      setLabel('');
      received.reload();
      app.refresh();
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  };

  const submit = async (e) => {
    e.preventDefault();
    setError(null);
    let amountText = '';
    if (amount.trim()) {
      try {
        const units = parseAmount(amount, p.decimals);
        if (units <= 0n) throw new AmountError('amount must be more than zero');
        amountText = toRpc(units, p.decimals);
      } catch (err) {
        setAmountError(err.message);
        return;
      }
    }
    setAmountError(null);
    setBusy(true);
    try {
      const address = await app.walletCall('getnewaddress', [label.trim()]);
      received.reload();
      app.refresh();
      const req = { wallet: scope, address, label: label.trim(), amount: amountText, message: message.trim(), created: Math.floor(Date.now() / 1000) };
      await addRequest(req);
      setShown(req);
      setLabel(''); setAmount(''); setMessage('');
      reloadHistory();
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  };

  return html`
    <div class="receive">
      <h1>Receive</h1>
      <form class="card" onSubmit=${submit} aria-label="Receive funds">
        <h2>Create a receiving address</h2>
        <p>Addresses and labels are saved in the node's wallet. They remain available if you close this browser or clear its data.</p>
        <${Field} label="Label (optional)" id="rcv-label" hint="Stored with the new address in the wallet">
          <input id="rcv-label" value=${label} onInput=${(e) => setLabel(e.currentTarget.value)} autocomplete="off" />
        <//>
        <div class="actions"><button type="button" disabled=${busy} onClick=${createAddress}>Create receiving address</button></div>
        <h3>Optional payment request</h3>
        <p class="muted">Add an amount or message to share with the address. Request details and history are saved only in this browser; the address and label are saved in the node's wallet.</p>
        <${Field} label=${`Amount (${p.ticker}, optional)`} id="rcv-amount" error=${amountError}>
          <input id="rcv-amount" class="amount-input" inputmode="decimal" value=${amount} onInput=${(e) => setAmount(e.currentTarget.value)} autocomplete="off" />
        <//>
        <${Field} label="Message (optional)" id="rcv-message" hint="Included in the payment URI; not stored on the node">
          <input id="rcv-message" value=${message} onInput=${(e) => setMessage(e.currentTarget.value)} autocomplete="off" />
        <//>
        <${ErrorText} error=${error} />
        <div class="actions"><button type="submit" disabled=${busy}>Create payment request</button></div>
      </form>

      <section class="card" aria-labelledby="req-title">
        <h2 id="req-title">Requested payments</h2>
        ${history.length === 0 ? html`<p class="muted">No requests yet. Request details are stored in this browser only; receiving addresses are saved in the node's wallet.</p>` : html`
          <table class="table">
            <thead><tr><th>Date</th><th>Label</th><th>Message</th><th class="num">Amount</th><th></th></tr></thead>
            <tbody>
              ${history.map((r) => html`
                <tr key=${r.id} class="clickable" onClick=${() => setShown(r)}>
                  <td>${formatTime(r.created)}</td><td>${r.label || html`<span class="muted">(no label)</span>`}</td>
                  <td>${r.message}</td><td class="num">${r.amount ? html`<${Amount} value=${r.amount} profile=${p} />` : '–'}</td>
                  <td><button class="secondary small" onClick=${(e) => { e.stopPropagation(); deleteRequest(r.id, scope).then(reloadHistory); }}>Remove</button></td>
                </tr>`)}
            </tbody>
          </table>`}
      </section>

      <section class="card" aria-labelledby="rcvd-title">
        <h2 id="rcvd-title">Received by address</h2>
        <${ErrorText} error=${received.error} />
        ${(received.value ?? []).length === 0 ? html`<p class="muted">No addresses yet.</p>` : html`
          <table class="table">
            <thead><tr><th>Address</th><th>Label</th><th class="num">Received</th><th class="num">Confirmations</th></tr></thead>
            <tbody>
              ${received.value.map((r) => html`
                <tr key=${r.address}><td class="mono wrap">${r.address}</td><td>${r.label}</td>
                  <td class="num"><${Amount} value=${r.amount} profile=${p} /></td><td class="num">${r.confirmations}</td></tr>`)}
            </tbody>
          </table>`}
      </section>
      ${shown ? html`<${RequestModal} app=${app} profile=${p} req=${shown} onClose=${() => setShown(null)} />` : null}
    </div>`;
}

function RequestModal({ app, profile, req, onClose }) {
  const fmt = profile.addressFormat;
  const uri = buildUri(req, fmt);
  const qrText = buildUri(req, fmt, { qr: true });
  const base = `payment-request-${req.address.replace(/^[a-z]+:/, '').slice(0, 12)}`;
  return html`
    <${Modal} title=${req.kind === 'address' ? 'Receiving address' : 'Payment request'} onClose=${onClose}>
      <div class="request">
        <${QR} text=${qrText} label="QR code of the payment URI" />
        <dl>
          <dt>Address</dt><dd class="mono wrap" data-testid="request-address">${req.address}</dd>
          ${req.amount ? html`<dt>Amount</dt><dd><${Amount} value=${req.amount} profile=${profile} /></dd>` : null}
          ${req.label ? html`<dt>Label</dt><dd>${req.label}</dd>` : null}
          ${req.message ? html`<dt>Message</dt><dd>${req.message}</dd>` : null}
          <dt>URI</dt><dd class="mono wrap">${uri}</dd>
        </dl>
      </div>
      <div class="actions">
        <${CopyButton} text=${req.address} label="Copy address" toast=${app.toast} />
        <${CopyButton} text=${uri} label="Copy URI" toast=${app.toast} />
        <button type="button" class="secondary" onClick=${() => downloadBlob(new Blob([qrSvgDocument(qrText)], { type: 'image/svg+xml' }), `${base}.svg`)}>Save SVG</button>
        <button type="button" class="secondary" onClick=${async () => downloadBlob(await qrPngBlob(qrText), `${base}.png`)}>Save PNG</button>
      </div>
    <//>`;
}
