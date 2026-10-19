// Login: one-time link (handled at boot) or RPC credentials.

import { html, useState } from '../vendor/htm-preact-standalone.mjs';

export function LoginView({ app, state }) {
  const [user, setUser] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    await app.loginPassword(user.trim(), password);
    setBusy(false);
    setPassword('');
  };
  return html`
    <main class="center-page">
      <form class="card login" onSubmit=${submit} aria-labelledby="login-title">
        <h1 id="login-title">Log in to your node</h1>
        <p class="muted">
          Open the link printed by <code>lotusd -gui</code> or <code>lotus-cli getwalletpwaurl</code>, or log in with an
          RPC user and password. To use the node's cookie file, leave the user empty and paste the whole
          <code>__cookie__:…</code> line as the password.
        </p>
        ${state.loginError ? html`<p class="error" role="alert">${state.loginError}</p>` : null}
        <label for="login-user">RPC user</label>
        <input id="login-user" autocomplete="username" value=${user} onInput=${(e) => setUser(e.currentTarget.value)} />
        <label for="login-password">Password or cookie line</label>
        <input id="login-password" type="password" autocomplete="current-password" value=${password}
               onInput=${(e) => setPassword(e.currentTarget.value)} />
        <button type="submit" disabled=${busy || !password}>${busy ? 'Logging in…' : 'Log in'}</button>
      </form>
    </main>`;
}
