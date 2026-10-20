// Legacy compact message signatures are produced/verified by the daemon.
// Keys and passphrases are never persisted by this page.
import { html, useState } from '../vendor/htm-preact-standalone.mjs';
import { CopyButton, ErrorText, Field, Modal } from '../ui/components.js';
import { routeHash } from '../router.js';

export function MessagesView({ app, state }) {
  const [tab, setTab] = useState(state.wallet === null ? 'verify' : 'sign');
  const keyboard = (event) => {
    let next;
    if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') next = tab === 'sign' ? 'verify' : 'sign';
    else if (event.key === 'Home') next = 'sign';
    else if (event.key === 'End') next = 'verify';
    else return;
    event.preventDefault();
    setTab(next);
    document.getElementById(`message-tab-${next}`).focus();
  };
  return html`<div class="messages">
    <h1>Sign / verify message</h1>
    <section class="card">
      <div class="tabs" role="tablist" aria-label="Message action" onKeyDown=${keyboard}>
        ${['sign', 'verify'].map((name) => html`<button type="button" role="tab" id=${`message-tab-${name}`} aria-controls=${`message-panel-${name}`}
          aria-selected=${tab === name ? 'true' : 'false'} tabindex=${tab === name ? 0 : -1} class=${tab === name ? '' : 'secondary'}
          onClick=${() => setTab(name)}>${name === 'sign' ? 'Sign message' : 'Verify message'}</button>`)}
      </div>
      <p>These node RPCs support legacy single-key (P2PKH) addresses. Native V2 and script addresses are not supported by this message-signature format. The node checks the address and reports unsupported types.</p>
      <p class="muted">Spaces and line breaks matter: messages are sent exactly as entered. A valid signature proves control of the address key, not the truth of a message or anyone's identity.</p>
      <div role="tabpanel" id="message-panel-sign" aria-labelledby="message-tab-sign" hidden=${tab !== 'sign'} tabindex="0">
        <${SignMessage} app=${app} wallet=${state.wallet} />
      </div>
      <div role="tabpanel" id="message-panel-verify" aria-labelledby="message-tab-verify" hidden=${tab !== 'verify'} tabindex="0">
        <${VerifyMessage} app=${app} />
      </div>
    </section>
  </div>`;
}

function SignMessage({ app, wallet }) {
  const [address, setAddress] = useState('');
  const [message, setMessage] = useState('');
  const [signature, setSignature] = useState(null);
  const [pending, setPending] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  // Bind every step, including relocking, to the originally selected wallet.
  const call = (method, params = []) => app.rpc.call(method, params, { wallet });
  const sign = async (request, passphrase) => {
    setBusy(true);
    setError(null);
    let unlocked = false;
    try {
      if (passphrase !== undefined) {
        await call('walletpassphrase', [passphrase, 60]);
        unlocked = true;
      }
      const value = await call('signmessage', [request.address, request.message]);
      setSignature({ ...request, value });
      setPending(null);
    } catch (err) {
      setError(err);
    } finally {
      if (unlocked) {
        try { await call('walletlock'); }
        catch (err) { setError(new Error(`Could not relock the wallet: ${err.message}. Lock it manually; the temporary unlock expires after 60 seconds.`)); }
      }
      setBusy(false);
      app.refresh();
    }
  };
  const submit = async (event) => {
    event.preventDefault();
    if (wallet === null) return;
    setSignature(null);
    setError(null);
    setBusy(true);
    const request = { address: address.trim(), message };
    try {
      const info = await call('getwalletinfo');
      if (info.unlocked_until !== undefined && Number(info.unlocked_until) === 0) setPending(request);
      else await sign(request);
    } catch (err) { setError(err); }
    finally { setBusy(false); }
  };
  const edit = (setter) => (event) => { setter(event.currentTarget.value); setSignature(null); };
  return html`<div>
    <h2>Sign a message</h2>
    ${wallet === null ? html`<p><a href=${routeHash('wallets')}>Create or open a wallet</a> to sign. Verification below does not need a wallet.</p>` : null}
    <form onSubmit=${submit} aria-label="Sign message">
      <${Field} label="Signing address" id="msg-sign-address" hint="An address whose private key is in the selected wallet">
        <input id="msg-sign-address" value=${address} onInput=${edit(setAddress)} disabled=${busy} required autocomplete="off" spellcheck="false" />
      <//>
      <${Field} label="Message to sign" id="msg-sign-text">
        <textarea id="msg-sign-text" value=${message} onInput=${edit(setMessage)} disabled=${busy} rows="5" spellcheck="false" />
      <//>
      <button type="submit" disabled=${busy || pending !== null || wallet === null || !address.trim()}>Sign message</button>
    </form>
    <${ErrorText} error=${error} />
    ${signature ? html`<div role="status" class="card" data-testid="signed-message">
      <h3>Signature</h3><pre class="wrap">${signature.value}</pre>
      <div class="actions"><${CopyButton} text=${signature.value} label="Copy signature" toast=${app.toast} />
        <${CopyButton} text=${signature.address} label="Copy signing address" toast=${app.toast} /></div>
    </div>` : null}
    ${pending ? html`<${UnlockMessage} busy=${busy} error=${error} onClose=${() => setPending(null)} onSign=${(pass) => sign(pending, pass)} />` : null}
  </div>`;
}

function UnlockMessage({ busy, error, onClose, onSign }) {
  const [passphrase, setPassphrase] = useState('');
  const submit = async (event) => {
    event.preventDefault();
    const value = passphrase;
    setPassphrase('');
    await onSign(value);
  };
  return html`<${Modal} title="Unlock wallet to sign" onClose=${busy ? null : onClose}>
    <form onSubmit=${submit} aria-label="Unlock wallet to sign">
      <${Field} label="Wallet passphrase" id="msg-passphrase" hint="Unlock for this signature, then relock. The passphrase is not saved.">
        <input id="msg-passphrase" type="password" value=${passphrase} onInput=${(e) => setPassphrase(e.currentTarget.value)} autocomplete="off" disabled=${busy} required />
      <//>
      <${ErrorText} error=${error} />
      <button type="submit" disabled=${busy || !passphrase}>Unlock and sign</button>
    </form>
  <//>`;
}

function VerifyMessage({ app }) {
  const [address, setAddress] = useState('');
  const [signature, setSignature] = useState('');
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const [valid, setValid] = useState(null);
  const [error, setError] = useState(null);
  const edit = (setter) => (event) => { setter(event.currentTarget.value); setValid(null); setError(null); };
  const submit = async (event) => {
    event.preventDefault();
    setBusy(true); setValid(null); setError(null);
    try { setValid(await app.rpc.call('verifymessage', [address.trim(), signature.trim(), message])); }
    catch (err) { setError(err); }
    finally { setBusy(false); }
  };
  return html`<div>
    <h2>Verify a message</h2>
    <form onSubmit=${submit} aria-label="Verify message">
      <${Field} label="Verification address" id="msg-verify-address">
        <input id="msg-verify-address" value=${address} onInput=${edit(setAddress)} disabled=${busy} autocomplete="off" required spellcheck="false" />
      <//>
      <${Field} label="Signature to verify" id="msg-verify-signature">
        <textarea id="msg-verify-signature" value=${signature} onInput=${edit(setSignature)} disabled=${busy} rows="3" required spellcheck="false" />
      <//>
      <${Field} label="Message to verify" id="msg-verify-text">
        <textarea id="msg-verify-text" value=${message} onInput=${edit(setMessage)} disabled=${busy} rows="5" spellcheck="false" />
      <//>
      <button type="submit" disabled=${busy || !address.trim() || !signature.trim()}>Verify message</button>
    </form>
    <${ErrorText} error=${error} />
    ${valid === null ? null : html`<p role="status" class=${valid ? 'success' : 'error'}>${valid ? 'Valid signature for this address and exact message.' : 'Signature does not match this address and message.'}</p>`}
  </div>`;
}
