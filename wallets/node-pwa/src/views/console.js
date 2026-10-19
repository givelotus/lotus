// RPC console, like bitcoin-qt's debug console: any RPC, nested calls,
// [index] selection, wallet selector, history (100 entries, sensitive
// commands excluded), clear, font size, and the scam warning.

import { html, useEffect, useRef, useState } from '../vendor/htm-preact-standalone.mjs';
import { parseCommandLine, evaluate, isSensitive } from '../lib/consoleparse.js';
import { stringify } from '../lib/json.js';
import { describeError } from '../lib/rpc.js';
import { load, save } from '../lib/storage.js';
import { walletLabel } from '../ui/components.js';

const HISTORY_MAX = 100;
const HELP = `Type "help" for a list of RPC commands, or "help <command>" for one command.
Arguments are separated by spaces; quote arguments that contain spaces.
Nested calls and selection work like bitcoin-qt:  getblock(getbestblockhash())[tx][0]
Double-quoted arguments are always strings; other arguments are JSON when they parse as JSON.
Ctrl+L or "clear" clears the output. Up/Down recall history.`;

/** Format an RPC result for display. */
export function formatResult(r) {
  if (typeof r === 'string') return r;
  if (r === null || r === undefined) return 'null';
  return stringify(r, 2);
}

/** Add a line to history (most recent last), skipping duplicates and sensitive commands. */
export function pushHistory(history, line) {
  if (!line.trim() || isSensitive(line)) return history;
  const h = history.filter((x) => x !== line);
  h.push(line);
  return h.slice(-HISTORY_MAX);
}

export function ConsoleView({ app, state }) {
  const [entries, setEntries] = useState([{ kind: 'info', text: 'Welcome to the RPC console.\n' + HELP }]);
  const [line, setLine] = useState('');
  const [history, setHistory] = useState(() => load('console-history', []));
  const [pos, setPos] = useState(-1);
  const [fontSize, setFontSize] = useState(() => load('console-font', 13));
  const [wallet, setWallet] = useState(state.wallet);
  const [busy, setBusy] = useState(false);
  const out = useRef(null);
  const input = useRef(null);

  useEffect(() => { out.current?.lastElementChild?.scrollIntoView({ block: 'end' }); }, [entries]);
  useEffect(() => { if (!busy) input.current?.focus(); }, [busy]);
  useEffect(() => {
    save('console-font', fontSize);
    // CSSOM, not a style attribute: allowed by the strict CSP.
    if (out.current) out.current.style.fontSize = `${fontSize}px`;
  }, [fontSize]);

  const add = (...e) => setEntries((xs) => [...xs, ...e].slice(-1000));
  const run = async (text) => {
    const trimmed = text.trim();
    if (!trimmed) return;
    const h = pushHistory(history, trimmed);
    setHistory(h);
    save('console-history', h);
    setPos(-1);
    setLine('');
    if (trimmed === 'clear') { setEntries([]); return; }
    add({ kind: 'cmd', text: isSensitive(trimmed) ? trimmed.split(/[\s(]/)[0] + ' …' : trimmed });
    if (trimmed === 'help-console') { add({ kind: 'info', text: HELP }); return; }
    setBusy(true);
    try {
      const node = parseCommandLine(trimmed);
      if (!node) return;
      const result = await evaluate(node, (method, params) => app.rpc.call(method, params, { wallet, timeoutMs: 600000 }));
      add({ kind: 'result', text: formatResult(result) });
      app.refresh();
    } catch (e) {
      add({ kind: 'error', text: describeError(e) });
    } finally {
      setBusy(false);
    }
  };

  const onKey = (e) => {
    if (e.key === 'Enter') { e.preventDefault(); if (!busy) run(line); }
    else if (e.key === 'ArrowUp' && history.length) {
      e.preventDefault();
      const p = pos < 0 ? history.length - 1 : Math.max(0, pos - 1);
      setPos(p); setLine(history[p]);
    } else if (e.key === 'ArrowDown' && pos >= 0) {
      e.preventDefault();
      const p = pos + 1;
      if (p >= history.length) { setPos(-1); setLine(''); } else { setPos(p); setLine(history[p]); }
    } else if (e.key === 'l' && e.ctrlKey) { e.preventDefault(); setEntries([]); }
  };

  const wallets = state.wallets ?? [];
  return html`
    <div class="console">
      <div class="banner warn" role="note">
        WARNING: Scammers have been active, telling users to type commands here, stealing their wallet contents.
        Do not use this console without fully understanding the ramifications of a command.
      </div>
      <div class="toolbar">
        <label>Wallet <select aria-label="Console wallet" value=${wallet === null ? '-1' : String(wallets.indexOf(wallet))}
            onChange=${(e) => { const i = Number(e.currentTarget.value); setWallet(i >= 0 ? wallets[i] : null); }}>
          <option value="-1">(node, no wallet)</option>
          ${wallets.map((w, i) => html`<option value=${String(i)}>${walletLabel(w)}</option>`)}
        </select></label>
        <span class="spacer"></span>
        <button class="secondary small" aria-label="Smaller font" onClick=${() => setFontSize(Math.max(9, fontSize - 1))}>A−</button>
        <button class="secondary small" aria-label="Larger font" onClick=${() => setFontSize(Math.min(24, fontSize + 1))}>A+</button>
        <button class="secondary small" onClick=${() => setEntries([])}>Clear</button>
      </div>
      <div class="console-out" ref=${out} role="log" aria-live="polite" data-testid="console-output">
        ${entries.map((e, i) => html`<pre key=${i} class=${`entry ${e.kind}`}>${e.text}</pre>`)}
      </div>
      <div class="console-in">
        <span class="prompt" aria-hidden="true">${'>'}</span>
        <input ref=${input} value=${line} onInput=${(e) => { setLine(e.currentTarget.value); setPos(-1); }} onKeyDown=${onKey}
               aria-label="Console command" spellcheck="false" autocomplete="off" autocapitalize="off" disabled=${busy}
               data-testid="console-input" placeholder=${busy ? 'Running…' : 'Enter a command'} />
      </div>
    </div>`;
}
