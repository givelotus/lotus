// Wallets: create, open (load), close (unload), select.

import { html, useState } from '../vendor/htm-preact-standalone.mjs';
import { useAsync, ErrorText, Field, walletLabel } from '../ui/components.js';

// Creating an encrypted wallet tops up and encrypts the whole keypool, and
// loading a wallet may rescan; both can take minutes on a real node.
const SLOW = { timeoutMs: 30 * 60 * 1000 };

export function WalletsView({ app, state }) {
  const loaded = state.wallets ?? [];
  const dir = useAsync(() => app.rpc.call('listwalletdir'), [loaded.join('\u0000')]);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const onDisk = (dir.value?.wallets ?? []).map((w) => w.name).filter((n) => !loaded.includes(n));

  const act = async (fn, ok) => {
    setBusy(true);
    setError(null);
    try {
      const r = await fn();
      if (r?.warning) app.toast(r.warning, 'warn', 8000);
      if (ok) app.toast(ok);
      app.refresh();
      dir.reload();
      return true;
    } catch (e) {
      setError(e);
      return false;
    } finally {
      setBusy(false);
    }
  };

  const load = (name) => act(async () => {
    const r = await app.rpc.call('loadwallet', [name], SLOW);
    app.selectWallet(name);
    return r;
  }, `Opened ${walletLabel(name)}`);
  const defaultExists = loaded.includes('') || (dir.value?.wallets ?? []).some((w) => w.name === '');
  const createDefault = () => act(async () => {
    // Recheck before creating: another tab may have opened or created it.
    const current = await app.rpc.call('listwallets');
    if (current.includes('')) {
      app.selectWallet('');
      return;
    }
    const disk = await app.rpc.call('listwalletdir');
    const method = disk.wallets.some((w) => w.name === '') ? 'loadwallet' : 'createwallet';
    const r = await app.rpc.call(method, [''], SLOW);
    app.selectWallet('');
    return r;
  }, 'Opened default wallet');
  const unload = (name) => {
    if (!confirm(`Close wallet ${walletLabel(name)}? It stays on disk and can be opened again.`)) return;
    act(async () => {
      const r = await app.rpc.call('unloadwallet', [name], SLOW);
      if (state.wallet === name) app.selectWallet(null);
      return r;
    }, `Closed ${walletLabel(name)}`);
  };

  return html`
    <div class="wallets">
      <h1>Wallets</h1>
      <${ErrorText} error=${error} />
      <section class="card">
        <h2>Open wallets</h2>
        ${loaded.length === 0 ? html`<p class="muted" data-testid="no-wallets">No wallet is loaded.</p>` : html`
          <ul class="plain">
            ${loaded.map((w) => html`
              <li key=${w}>
                <span class=${w === state.wallet ? 'selected' : ''}>${walletLabel(w)}</span>
                ${w !== state.wallet ? html`<button class="secondary small" onClick=${() => app.selectWallet(w)}>Select</button>` : html`<span class="badge ok">selected</span>`}
                <button class="secondary small" disabled=${busy} onClick=${() => unload(w)}>Close</button>
              </li>`)}
          </ul>`}
      </section>
      <section class="card">
        <h2>Wallets on the node's disk</h2>
        ${onDisk.length === 0 ? html`<p class="muted">No other wallets found in the node's wallet directory.</p>` : html`
          <ul class="plain">
            ${onDisk.map((w) => html`<li key=${w}>${walletLabel(w)} <button class="secondary small" disabled=${busy} onClick=${() => load(w)}>Open</button></li>`)}
          </ul>`}
      </section>
      ${!defaultExists ? html`<section class="card">
        <h2>Default wallet</h2>
        <p>Create the node's unnamed wallet. You can also create named wallets below.</p>
        <button type="button" disabled=${busy || !dir.value} onClick=${createDefault}>Create default wallet</button>
      </section>` : null}
      <${CreateWallet} app=${app} busy=${busy} act=${act} />
    </div>`;
}

function CreateWallet({ app, busy, act }) {
  const [name, setName] = useState('');
  const [pass, setPass] = useState('');
  const [pass2, setPass2] = useState('');
  const [noKeys, setNoKeys] = useState(false);
  const [blank, setBlank] = useState(false);
  const [descriptors, setDescriptors] = useState(false);
  const [localError, setLocalError] = useState(null);
  const submit = async (e) => {
    e.preventDefault();
    if (pass !== pass2) { setLocalError('The passphrases do not match.'); return; }
    setLocalError(null);
    const n = name.trim();
    const ok = await act(async () => {
      const r = await app.rpc.call('createwallet', [n, noKeys, blank, pass, false, descriptors], SLOW);
      app.selectWallet(r.name);
      return r;
    }, `Created wallet ${walletLabel(n)}`);
    if (ok) { setName(''); setPass(''); setPass2(''); }
  };
  return html`
    <form class="card" onSubmit=${submit} aria-labelledby="create-title">
      <h2 id="create-title">Create a wallet</h2>
      <${Field} label="Wallet name" id="cw-name" hint="Created in the node's wallet directory">
        <input id="cw-name" value=${name} onInput=${(e) => setName(e.currentTarget.value)} autocomplete="off" required />
      <//>
      <${Field} label="Passphrase (optional, encrypts the wallet)" id="cw-pass">
        <input id="cw-pass" type="password" value=${pass} onInput=${(e) => setPass(e.currentTarget.value)} autocomplete="new-password" />
      <//>
      ${pass ? html`<${Field} label="Repeat passphrase" id="cw-pass2" error=${localError}>
        <input id="cw-pass2" type="password" value=${pass2} onInput=${(e) => setPass2(e.currentTarget.value)} autocomplete="new-password" />
      <//>` : null}
      <label class="check"><input type="checkbox" checked=${noKeys} onChange=${(e) => setNoKeys(e.currentTarget.checked)} /> Disable private keys (watch-only)</label>
      <label class="check"><input type="checkbox" checked=${blank} onChange=${(e) => setBlank(e.currentTarget.checked)} /> Blank wallet (no keys or HD seed)</label>
      <label class="check"><input type="checkbox" checked=${descriptors} onChange=${(e) => setDescriptors(e.currentTarget.checked)} /> Descriptor wallet</label>
      <div class="actions">
        <button type="submit" disabled=${busy || !name.trim()}>Create wallet</button>
        ${busy ? html`<span class="muted" aria-live="polite">Working… encrypting a new wallet can take several minutes.</span>` : null}
      </div>
    </form>`;
}
