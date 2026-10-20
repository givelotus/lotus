import { html, useEffect, useRef, useState } from '../vendor/htm-preact-standalone.mjs';
import { ErrorText, Field } from '../ui/components.js';
import { BrowserMiner } from '../lib/browser-miner.js';

export function MiningView({ app, state }) {
  const [address, setAddress] = useState('');
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [generated, setGenerated] = useState(null);
  const [mining, setMining] = useState({ running: false, status: 'Stopped', hashes: 0, hashRate: 0 });
  const miner = useRef(null);
  const config = state.profile;
  const testMode = config.rpc.testBlockGeneration;
  const gpu = globalThis.isSecureContext && Boolean(navigator.gpu) && config.mining?.supported;
  useEffect(() => {
    const instance = new BrowserMiner({ rpc: app.rpc, onState: (patch) => setMining((s) => ({ ...s, ...patch })), onBlock: () => app.refresh() });
    miner.current = instance;
    const hide = () => { if (document.hidden) instance.stop('Paused because this tab is hidden. Press Start to resume.'); };
    const pagehide = () => instance.stop('Stopped because the page closed.');
    document.addEventListener('visibilitychange', hide); addEventListener('pagehide', pagehide);
    return () => { document.removeEventListener('visibilitychange', hide); removeEventListener('pagehide', pagehide); instance.stop(); };
  }, [app, config]);
  const newAddress = async () => {
    setBusy(true); setError(null);
    try { setAddress(await app.walletCall('getnewaddress', ['Mining'])); }
    catch (err) { setError(err); }
    finally { setBusy(false); }
  };
  const generate = async (count) => {
    setBusy(true); setError(null); setGenerated(null);
    try {
      // Check the node again rather than trusting a stale UI/profile.
      const chain = await app.rpc.call('getblockchaininfo');
      if (chain.chain !== 'regtest') throw new Error('Instant block generation is available only on regtest.');
      const result = await app.rpc.call('generatetoaddress', [count, address.trim()], { timeoutMs: 10 * 60 * 1000 });
      setGenerated(result.length); app.refresh();
    } catch (err) { setError(err); }
    finally { setBusy(false); }
  };
  return html`<div class="mining"><h1>Mining</h1>
    <section class="card">
      <h2>Mining payout</h2>
      <${Field} label="Payout address" id="mining-address" hint="Mining rewards go directly to this address. Wallet keys stay in the node.">
        <input id="mining-address" value=${address} onInput=${(e) => setAddress(e.currentTarget.value)} disabled=${busy || mining.running} autocomplete="off" />
      <//>
      <button type="button" class="secondary" onClick=${newAddress} disabled=${busy || mining.running || state.wallet === null}>Create payout address</button>
      <${ErrorText} error=${error} />
    </section>
    ${testMode ? html`<section class="card"><h2>Regtest blocks</h2>
      <p>Generate test blocks immediately in the node. This is RPC test-chain generation, not browser GPU hashing.</p>
      <div class="actions"><button type="button" onClick=${() => generate(1)} disabled=${busy || mining.running || !address.trim()}>Mine 1 test block</button>
        <button type="button" onClick=${() => generate(101)} disabled=${busy || mining.running || !address.trim()}>Mine 101 test blocks</button></div>
      ${generated !== null ? html`<p role="status">Generated ${generated} test block${generated === 1 ? '' : 's'}.</p>` : null}
    </section>` : null}
    <section class="card"><h2>Browser GPU mining</h2>
      <p>Opt in to WebGPU proof-of-work hashing on this device. Mining uses power and can warm the device. It stops when you leave this page or hide the tab. There is no automatic start or resume.</p>
      <p class="muted">This is experimental mining support; browser hashing is not a promise of profitable mining.</p>
      ${!config.mining?.supported ? html`<p class="muted">${config.mining?.reason ?? 'This node does not advertise a supported mining descriptor.'}</p>` : html`<p>Algorithm: ${config.mining.descriptor.algorithm}</p>`}
      ${!globalThis.isSecureContext || !navigator.gpu ? html`<p class="muted">WebGPU requires a compatible browser/GPU and a secure context (HTTPS or localhost).</p>` : null}
      <div class="actions"><button type="button" disabled=${busy || mining.running || !gpu || !address.trim()} onClick=${() => miner.current.start(address.trim(), config.mining.descriptor)}>Start GPU mining</button>
        <button type="button" class="secondary" disabled=${!mining.running} onClick=${() => miner.current.stop()}>Stop mining</button></div>
      <p role="status">${mining.status}</p>
      <dl class="details"><dt>Computed GPU hashes</dt><dd>${mining.hashes}</dd><dt>Session hash rate</dt><dd>${Math.round(mining.hashRate)} hashes/s</dd></dl>
      <p class="muted">Counts include completed GPU dispatches only. Session rate includes setup, template refresh and submission time.</p>
    </section>
  </div>`;
}
