// Send: several recipients, labels, subtract fee, fee preview, confirm,
// unlock prompt for encrypted wallets, payment URIs.

import { html, useEffect, useRef, useState } from '../vendor/htm-preact-standalone.mjs';
import { Amount, Modal, ErrorText, Field } from '../ui/components.js';
import { AddressInput, useAddressValidation } from '../ui/address.js';
import { parseAmount, toRpc, fromRpc, AmountError } from '../lib/amount.js';
import { RpcError, describeError, RPC_WALLET_PASSPHRASE_INCORRECT } from '../lib/rpc.js';
import { routeHash } from '../router.js';
import { NoWallet } from './overview.js';

let nextId = 1;
const blank = () => ({ id: nextId++, address: '', label: '', amount: '', subtractFee: false });

/** Validate the form; returns {errors, outputs} where outputs is in recipient order. */
export function checkRecipients(recipients, validations, decimals) {
  const errors = {};
  const seen = new Set();
  const outputs = [];
  for (const r of recipients) {
    const e = {};
    const v = validations[r.id];
    const addr = r.address.trim();
    if (!addr) e.address = 'enter an address';
    else if (v?.status === 'invalid') e.address = v.message;
    else if (v?.status !== 'valid') e.address = 'address not checked yet';
    const norm = v?.normalized ?? addr;
    if (addr && seen.has(norm)) e.address = 'the same address appears twice; combine the amounts';
    seen.add(norm);
    let units = null;
    try {
      units = parseAmount(r.amount, decimals);
      if (units <= 0n) e.amount = 'amount must be more than zero';
    } catch (err) {
      e.amount = err instanceof AmountError ? err.message : String(err);
    }
    if (Object.keys(e).length) errors[r.id] = e;
    else outputs.push({ address: norm, units, label: r.label.trim(), subtractFee: r.subtractFee });
  }
  return { errors, outputs };
}

function Recipient({ app, profile, r, index, count, onChange, onRemove, onValidation, errors }) {
  const validation = useAddressValidation(app, profile, r.address);
  useEffect(() => onValidation(r.id, validation), [validation]);
  const set = (k) => (e) => onChange({ ...r, [k]: e.currentTarget.type === 'checkbox' ? e.currentTarget.checked : e.currentTarget.value });
  const onUri = (u) => {
    onChange({ ...r, address: u.address, amount: u.amount ?? r.amount, label: u.label ?? r.label });
    if (u.message) app.toast(`Payment request message: ${u.message}`, 'info', 8000);
  };
  return html`
    <fieldset class="card recipient" data-testid="recipient">
      <legend>Recipient ${count > 1 ? index + 1 : ''}</legend>
      <${Field} label="Pay to" id=${`addr-${r.id}`} error=${errors?.address && validation.status !== 'invalid' ? errors.address : null}>
        <${AddressInput} id=${`addr-${r.id}`} value=${r.address} validation=${validation}
          onInput=${(v) => onChange({ ...r, address: v })} onUri=${onUri} />
      <//>
      <${Field} label="Label" id=${`label-${r.id}`} hint="Saved in the wallet's address book">
        <input id=${`label-${r.id}`} value=${r.label} onInput=${set('label')} autocomplete="off" />
      <//>
      <${Field} label=${`Amount (${profile.ticker})`} id=${`amount-${r.id}`} error=${errors?.amount}>
        <input id=${`amount-${r.id}`} class="amount-input" inputmode="decimal" value=${r.amount} onInput=${set('amount')}
               autocomplete="off" placeholder=${(0).toFixed(profile.decimals)} />
      <//>
      <label class="check">
        <input type="checkbox" checked=${r.subtractFee} onChange=${set('subtractFee')} />
        Subtract fee from amount
      </label>
      ${count > 1 ? html`<button type="button" class="secondary small" onClick=${onRemove}>Remove recipient</button>` : null}
    </fieldset>`;
}

export function SendView({ app, state }) {
  const [recipients, setRecipients] = useState([blank()]);
  const validations = useRef({});
  const [, force] = useState(0);
  const [errors, setErrors] = useState({});
  const [confirm, setConfirm] = useState(null);
  const [result, setResult] = useState(null);
  const p = state.profile;
  if (state.wallet === null) return html`<${NoWallet} state=${state} />`;

  const onValidation = (id, v) => { validations.current[id] = v; force((n) => n + 1); };
  const update = (i) => (r) => setRecipients((rs) => rs.map((x, k) => (k === i ? r : x)));
  const remove = (i) => () => setRecipients((rs) => rs.filter((_, k) => k !== i));
  const clear = () => { setRecipients([blank()]); setErrors({}); setResult(null); };

  const review = async (e) => {
    e.preventDefault();
    // Addresses still inside the validation debounce are checked now.
    for (const r of recipients) {
      const v = validations.current[r.id];
      if (r.address.trim() && v?.status !== 'valid' && v?.status !== 'invalid') {
        try {
          const res = await app.rpc.call('validateaddress', [r.address.trim()]);
          validations.current[r.id] = res.isvalid
            ? { status: 'valid', message: '', normalized: res.address }
            : { status: 'invalid', message: 'not a valid address for this node' };
        } catch {
          // leave it unchecked; checkRecipients reports it
        }
      }
    }
    const { errors: errs, outputs } = checkRecipients(recipients, validations.current, p.decimals);
    setErrors(errs);
    if (Object.keys(errs).length) return;
    // Fee preview only; the real fee is read back after sending.
    let fee = null;
    let feeError = null;
    try {
      const funded = await app.walletCall('walletcreatefundedpsbt', [
        [],
        outputs.map((o) => ({ [o.address]: toRpc(o.units, p.decimals) })),
        0,
        { subtractFeeFromOutputs: outputs.flatMap((o, i) => (o.subtractFee ? [i] : [])) },
      ]);
      fee = fromRpc(funded.fee, p.decimals);
    } catch (err) {
      feeError = describeError(err);
    }
    const wi = state.walletInfo;
    setConfirm({ outputs, fee, feeError, needsUnlock: wi?.unlocked_until !== undefined && Number(wi.unlocked_until) === 0 });
  };

  return html`
    <form class="send" onSubmit=${review} aria-label="Send">
      <h1>Send</h1>
      ${result ? html`
        <div class="card success" role="status" data-testid="send-result">
          <h2>Sent</h2>
          <p>Transaction <a href=${routeHash('tx', result.txid, state.wallet)} data-testid="sent-txid">${result.txid}</a></p>
          ${result.fee !== null ? html`<p>Fee paid: <${Amount} units=${result.fee} profile=${p} /></p>` : null}
          <button type="button" class="secondary" onClick=${clear}>New payment</button>
        </div>` : null}
      ${recipients.map((r, i) => html`
        <${Recipient} key=${r.id} app=${app} profile=${p} r=${r} index=${i} count=${recipients.length}
          onChange=${update(i)} onRemove=${remove(i)} onValidation=${onValidation} errors=${errors[r.id]} />`)}
      <div class="actions">
        <button type="button" class="secondary" onClick=${() => setRecipients((rs) => [...rs, blank()])}>Add recipient</button>
        <button type="button" class="secondary" onClick=${clear}>Clear all</button>
        <span class="spacer"></span>
        <span class="muted">Available: <${Amount} value=${state.balances?.mine?.trusted} profile=${p} /></span>
        <button type="submit">Review</button>
      </div>
      ${confirm ? html`<${ConfirmSend} app=${app} state=${state} confirm=${confirm}
          onClose=${() => setConfirm(null)}
          onSent=${(r) => { setConfirm(null); setResult(r); setRecipients([blank()]); setErrors({}); app.refresh(); }} />` : null}
    </form>`;
}

function ConfirmSend({ app, state, confirm, onClose, onSent }) {
  const p = state.profile;
  const [passphrase, setPassphrase] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const total = confirm.outputs.reduce((s, o) => s + o.units, 0n);
  const anySubtract = confirm.outputs.some((o) => o.subtractFee);

  const send = async () => {
    setBusy(true);
    setError(null);
    let unlocked = false;
    try {
      if (confirm.needsUnlock) {
        await app.walletCall('walletpassphrase', [passphrase, 60]);
        unlocked = true;
      }
      const amounts = {};
      for (const o of confirm.outputs) Object.defineProperty(amounts, o.address, { value: toRpc(o.units, p.decimals), enumerable: true });
      const subtract = confirm.outputs.filter((o) => o.subtractFee).map((o) => o.address);
      const txid = await app.walletCall('sendmany', ['', amounts, null, null, subtract]);
      for (const o of confirm.outputs) {
        if (o.label) await app.walletCall('setlabel', [o.address, o.label]).catch(() => {});
      }
      let fee = null;
      try {
        const tx = await app.walletCall('gettransaction', [txid]);
        fee = -fromRpc(tx.fee, p.decimals);
      } catch {
        // the fee display is best effort
      }
      onSent({ txid, fee });
    } catch (e) {
      setError(e instanceof RpcError && e.code === RPC_WALLET_PASSPHRASE_INCORRECT ? new Error('The passphrase is incorrect.') : e);
    } finally {
      if (unlocked) await app.walletCall('walletlock').catch(() => {});
      setPassphrase('');
      setBusy(false);
    }
  };

  return html`
    <${Modal} title="Confirm payment" onClose=${busy ? null : onClose}>
      <table class="confirm-table">
        <tbody>
          ${confirm.outputs.map((o) => html`
            <tr><td class="mono wrap">${o.address}${o.label ? html`<div class="muted">${o.label}</div>` : null}</td>
                <td class="num"><${Amount} units=${o.units} profile=${p} />${o.subtractFee ? html`<div class="muted">minus fee</div>` : null}</td></tr>`)}
        </tbody>
        <tfoot>
          <tr><th>Fee</th><td class="num" data-testid="fee-preview">${confirm.fee !== null
            ? html`<${Amount} units=${confirm.fee} profile=${p} />`
            : html`<span class="muted" title=${confirm.feeError ?? ''}>calculated when sent</span>`}</td></tr>
          <tr><th>Total${anySubtract ? ' (fee included)' : ''}</th><td class="num"><${Amount}
            units=${anySubtract || confirm.fee === null ? total : total + confirm.fee} profile=${p} /></td></tr>
        </tfoot>
      </table>
      ${confirm.needsUnlock ? html`
        <${Field} label="Wallet passphrase" id="send-passphrase" hint="The wallet is unlocked for this payment only, then locked again.">
          <input id="send-passphrase" type="password" autocomplete="off" value=${passphrase}
                 onInput=${(e) => setPassphrase(e.currentTarget.value)} />
        <//>` : null}
      <${ErrorText} error=${error} />
      <div class="actions">
        <button type="button" class="secondary" onClick=${onClose} disabled=${busy}>Cancel</button>
        <button type="button" onClick=${send} disabled=${busy || (confirm.needsUnlock && !passphrase)} data-testid="confirm-send">
          ${busy ? 'Sending…' : 'Send'}</button>
      </div>
    <//>`;
}
