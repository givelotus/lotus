// Shared UI components. Rendering goes only through htm's escaping templates;
// no HTML strings are ever inserted (enforced by tools/lint.mjs).

import { html, useState, useEffect, useRef, useCallback } from '../vendor/htm-preact-standalone.mjs';
import { QrCode } from '../vendor/qrcodegen.mjs';
import { fromRpc, formatAmount } from '../lib/amount.js';
import { describeError } from '../lib/rpc.js';

export { html };

/** Subscribe a component to a store. */
export function useStore(store) {
  const [s, set] = useState(store.get());
  useEffect(() => {
    const unsubscribe = store.subscribe(set);
    // Boot/discovery can finish before this effect subscribes. Reconcile the
    // current snapshot after subscribing so a fast error cannot strand Boot.
    set(store.get());
    return unsubscribe;
  }, [store]);
  return s;
}

/** Run an async loader on mount and whenever deps change; optional refresh interval. */
export function useAsync(fn, deps, { intervalMs = 0 } = {}) {
  const [state, setState] = useState({ loading: true, error: null, value: undefined });
  const counter = useRef(0);
  const run = useCallback(async () => {
    const n = ++counter.current;
    try {
      const value = await fn();
      if (n === counter.current) setState({ loading: false, error: null, value });
    } catch (error) {
      if (n === counter.current) setState((s) => ({ loading: false, error, value: s.value }));
    }
  }, deps);
  useEffect(() => {
    run();
    if (!intervalMs) return undefined;
    const t = setInterval(run, intervalMs);
    return () => clearInterval(t);
  }, [run, intervalMs]);
  return { ...state, reload: run };
}

/** An RPC amount rendered with the profile's decimals and ticker. */
export function Amount({ value, profile, units, sign = false, ticker = true }) {
  if (!profile) return html`<span class="amount">–</span>`;
  let u;
  try {
    u = units !== undefined ? units : fromRpc(value, profile.decimals);
  } catch {
    return html`<span class="amount">${String(value)}</span>`;
  }
  const cls = `amount${u < 0n ? ' neg' : ''}`;
  return html`<span class=${cls}>${formatAmount(u, profile.decimals, { group: true, sign, minDecimals: profile.currency?.displayDecimals ?? profile.decimals })}${ticker ? html` <span class="ticker">${profile.ticker}</span>` : ''}</span>`;
}

export function ErrorText({ error }) {
  if (!error) return null;
  return html`<p class="error" role="alert">${describeError(error)}</p>`;
}

export function Modal({ title, onClose, children, wide = false }) {
  const ref = useRef(null);
  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') onClose?.(); };
    document.addEventListener('keydown', onKey);
    ref.current?.querySelector('input, button, select, textarea')?.focus();
    return () => document.removeEventListener('keydown', onKey);
  }, []);
  return html`
    <div class="modal-backdrop" onClick=${(e) => { if (e.target === e.currentTarget) onClose?.(); }}>
      <div class=${`modal${wide ? ' wide' : ''}`} role="dialog" aria-modal="true" aria-label=${title} ref=${ref}>
        <header class="modal-head">
          <h2>${title}</h2>
          ${onClose ? html`<button class="icon-button" aria-label="Close" onClick=${onClose}>×</button>` : null}
        </header>
        <div class="modal-body">${children}</div>
      </div>
    </div>`;
}

export function CopyButton({ text, label = 'Copy', toast }) {
  const [done, setDone] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setDone(true);
      setTimeout(() => setDone(false), 1500);
    } catch {
      toast?.('Copy failed: the browser refused clipboard access', 'error');
    }
  };
  return html`<button type="button" class="secondary" onClick=${copy}>${done ? 'Copied' : label}</button>`;
}

/** QR code as SVG. */
export function qrSvgPath(text) {
  const qr = QrCode.encodeText(text, QrCode.Ecc.MEDIUM);
  const parts = [];
  for (let y = 0; y < qr.size; y++) {
    for (let x = 0; x < qr.size; x++) if (qr.getModule(x, y)) parts.push(`M${x + 4},${y + 4}h1v1h-1z`);
  }
  return { size: qr.size + 8, d: parts.join('') };
}

export function QR({ text, label }) {
  const { size, d } = qrSvgPath(text);
  return html`
    <svg class="qr" viewBox=${`0 0 ${size} ${size}`} role="img" aria-label=${label ?? 'QR code'} shape-rendering="crispEdges">
      <rect width=${size} height=${size} fill="#fff" />
      <path d=${d} fill="#000" />
    </svg>`;
}

/** Standalone SVG document text for download. */
export function qrSvgDocument(text) {
  const { size, d } = qrSvgPath(text);
  const scale = 8;
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${size * scale}" height="${size * scale}" viewBox="0 0 ${size} ${size}" shape-rendering="crispEdges"><rect width="${size}" height="${size}" fill="#fff"/><path d="${d}" fill="#000"/></svg>`;
}

/** Trigger a download of a Blob. */
export function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/** QR code as a PNG Blob, drawn on a canvas. */
export function qrPngBlob(text, scale = 8) {
  const qr = QrCode.encodeText(text, QrCode.Ecc.MEDIUM);
  const size = (qr.size + 8) * scale;
  const canvas = document.createElement('canvas');
  canvas.width = canvas.height = size;
  const ctx = canvas.getContext('2d');
  ctx.fillStyle = '#fff';
  ctx.fillRect(0, 0, size, size);
  ctx.fillStyle = '#000';
  for (let y = 0; y < qr.size; y++) {
    for (let x = 0; x < qr.size; x++) if (qr.getModule(x, y)) ctx.fillRect((x + 4) * scale, (y + 4) * scale, scale, scale);
  }
  return new Promise((resolve) => canvas.toBlob(resolve, 'image/png'));
}

export function Field({ label, hint, error, children, id }) {
  return html`
    <div class=${`field${error ? ' invalid' : ''}`}>
      <label for=${id}>${label}</label>
      ${children}
      ${error ? html`<div class="field-error">${error}</div>` : hint ? html`<div class="field-hint">${hint}</div>` : null}
    </div>`;
}

export function Spinner({ label = 'Loading…' }) {
  return html`<p class="muted" aria-live="polite">${label}</p>`;
}

export function formatTime(unix) {
  if (!unix) return '–';
  const d = new Date(Number(unix) * 1000);
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export function formatBytes(n) {
  const v = Number(n);
  if (!Number.isFinite(v)) return '–';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let i = 0;
  let x = v;
  while (x >= 1000 && i < units.length - 1) { x /= 1000; i++; }
  return `${i === 0 ? x : x.toFixed(1)} ${units[i]}`;
}

export function formatDuration(seconds) {
  const s = Math.max(0, Math.floor(Number(seconds)));
  const d = Math.floor(s / 86400), h = Math.floor((s % 86400) / 3600), m = Math.floor((s % 3600) / 60);
  if (d) return `${d}d ${h}h`;
  if (h) return `${h}h ${m}m`;
  if (m) return `${m}m ${s % 60}s`;
  return `${s}s`;
}

export function shortHash(h, n = 10) {
  const s = String(h ?? '');
  return s.length > 2 * n + 1 ? `${s.slice(0, n)}…${s.slice(-n)}` : s;
}

export function walletLabel(name) {
  return name === '' ? '(default wallet)' : name;
}

/** Category of a listtransactions entry, as shown to users. */
export function txKind(t) {
  if (t.abandoned) return 'abandoned';
  switch (t.category) {
    case 'send': return 'sent';
    case 'receive': return 'received';
    case 'generate': return 'mined';
    case 'immature': return 'mined (immature)';
    case 'orphan': return 'orphaned';
    default: return t.category ?? '?';
  }
}
