// Address input with instant local checks (xpi format) and debounced
// validateaddress (authoritative). Pasting a payment URI fills in the amount
// and label through onUri.

import { html, useEffect, useRef, useState } from '../vendor/htm-preact-standalone.mjs';
import { decode, XpiAddrError, looksLikeXpi } from '../lib/xpiaddr.js';
import { parseUri } from '../lib/uri.js';

/**
 * Local (client-side) verdict on an address string. Returns an error reason,
 * or null when the node must decide.
 */
export function localAddressError(text, profile) {
  const s = text.trim();
  if (!s) return null;
  if (profile?.addressFormat === 'xpi' || looksLikeXpi(s)) {
    try {
      decode(s, profile?.hrp ?? undefined);
    } catch (e) {
      if (e instanceof XpiAddrError) return e.reason === 'wrong network' ? `wrong network (this node is ${profile?.chain})` : e.reason;
      throw e;
    }
  }
  return null;
}

/** Hook: validates `address` with the node after 300 ms of quiet. */
export function useAddressValidation(app, profile, address) {
  const [state, setState] = useState({ status: 'empty', message: '' });
  const seq = useRef(0);
  useEffect(() => {
    const s = address.trim();
    const n = ++seq.current;
    if (!s) { setState({ status: 'empty', message: '' }); return undefined; }
    const local = localAddressError(s, profile);
    if (local) { setState({ status: 'invalid', message: local }); return undefined; }
    setState({ status: 'checking', message: '' });
    const t = setTimeout(async () => {
      try {
        const v = await app.rpc.call('validateaddress', [s]);
        if (n !== seq.current) return;
        setState(v.isvalid ? { status: 'valid', message: '', normalized: v.address } : { status: 'invalid', message: 'not a valid address for this node' });
      } catch (e) {
        if (n === seq.current) setState({ status: 'unknown', message: `could not check: ${e.message}` });
      }
    }, 300);
    return () => clearTimeout(t);
  }, [address, profile]);
  return state;
}

export function AddressInput({ id, value, onInput, onUri, validation, placeholder }) {
  const handle = (e) => {
    const v = e.currentTarget.value;
    // Only pasted or dropped text (or a jump of several characters, e.g. an
    // autofill) is treated as a URI, so typing a "?" by hand is not eaten.
    const bulk = /^insertFrom/.test(e.inputType ?? '') || v.length - value.length > 1;
    if (onUri && bulk && (/\?/.test(v) || /^(xpi|web\+xpi|web\+ecash):/i.test(v.trim()))) {
      try {
        const u = parseUri(v);
        onInput(u.address);
        onUri(u);
        return;
      } catch {
        // fall through: keep the raw text; validation reports the problem
      }
    }
    onInput(v);
  };
  const st = validation?.status;
  return html`
    <div class="address-input">
      <input id=${id} class=${st === 'invalid' ? 'invalid' : st === 'valid' ? 'valid' : ''} value=${value}
             onInput=${handle} spellcheck="false" autocomplete="off" autocapitalize="off"
             placeholder=${placeholder ?? 'Address or payment URI'} aria-invalid=${st === 'invalid' ? 'true' : 'false'} />
      <span class="address-status" aria-live="polite">
        ${st === 'checking' ? 'checking…' : st === 'valid' ? '✓ valid' : st === 'invalid' ? validation.message : st === 'unknown' ? validation.message : ''}
      </span>
    </div>`;
}
