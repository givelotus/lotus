import { html, useEffect, useRef, useState } from '../vendor/htm-preact-standalone.mjs';
import { ErrorText, Field } from '../ui/components.js';
import { BrowserMiner } from '../lib/browser-miner.js';
import { BrowserPoolMiner } from '../lib/browser-pool-miner.js';
import { poolTerms, poolWorkerId } from '../lib/pool-mining.js';

export function MiningView({ app, state }) {
  const [address, setAddress] = useState('');
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [generated, setGenerated] = useState(null);
  const [mining, setMining] = useState({ running: false, status: 'Stopped', hashes: 0, hashRate: 0 });
  const miner = useRef(null);
  const uiEpoch = useRef(0);
  const poolMiner = useRef(null);
  const [mode, setMode] = useState('solo');
  const [workerLabel, setWorkerLabel] = useState('browser');
  const [poolAddress, setPoolAddress] = useState('');
  const [poolReview, setPoolReview] = useState(null);
  const [payoutSource, setPayoutSource] = useState('wallet');
  const [addressWallet, setAddressWallet] = useState(null);
  const config = state.profile;
  const testMode = config.rpc.testBlockGeneration;
  const gpu = globalThis.isSecureContext && Boolean(navigator.gpu) && config.mining?.supported;
  useEffect(() => {
    ++uiEpoch.current;
    const instance = new BrowserMiner({ rpc: app.rpc, onState: (patch) => { if (mode === 'solo') setMining((s) => ({ ...s, ...patch })); }, onBlock: () => app.refresh() });
    miner.current = instance;
    const pool = new BrowserPoolMiner({ rpc: app.rpc, onState: (patch) => { if (mode === 'pool') setMining((s) => ({ ...s, ...patch })); }, onBlock: () => app.refresh() });
    poolMiner.current = pool;
    const hide = () => { if (document.hidden) { ++uiEpoch.current; instance.stop('Paused because this tab is hidden. Press Start to resume.'); pool.stop('Paused because this tab is hidden. Press Start to resume.'); } };
    const pagehide = () => { ++uiEpoch.current; instance.stop('Stopped because the page closed.'); pool.stop('Stopped because the page closed.'); };
    document.addEventListener('visibilitychange', hide); addEventListener('pagehide', pagehide);
    return () => { ++uiEpoch.current; document.removeEventListener('visibilitychange', hide); removeEventListener('pagehide', pagehide); instance.stop(); pool.stop(); };
  }, [app, config, state.wallet, mode]);
  const reviewPool = async () => {
    setBusy(true); setError(null); setPoolReview(null);
    try {
      const info = await app.rpc.call('getpoolinfo');
      setPoolReview({ info, terms: poolTerms(info) });
    } catch (err) { setError(err); }
    finally { setBusy(false); }
  };
  const start = async () => {
    const epoch = uiEpoch.current;
    setError(null); setBusy(true);
    try {
      if (mode === 'pool') {
        const id = poolWorkerId(poolAddress.trim(), workerLabel, config);
        if (!poolReview) throw new Error('Review pool terms before starting.');
        if (payoutSource === 'wallet') {
          if (!config.wallet?.nativeReceiving || state.wallet === null || addressWallet !== state.wallet) throw new Error('Create a native address in the selected wallet first.');
          const ownership = await app.walletCall('getaddressinfo', [poolAddress.trim()]);
          if (ownership.ismine !== true || ownership.native !== true || ownership.type !== 1) throw new Error('Selected wallet does not own this native payout address.');
        }
        if (epoch !== uiEpoch.current || document.hidden) return;
        poolMiner.current.start(id, config.mining.descriptor, poolReview.terms);
      } else miner.current.start(address.trim(), config.mining.descriptor);
    } catch (err) { setError(err); }
    finally { setBusy(false); }
  };
  const createNativeAddress = async () => {
    const epoch = uiEpoch.current;
    setBusy(true); setError(null);
    try {
      if (!config.wallet?.nativeReceiving || state.wallet === null) throw new Error('This node does not advertise native wallet receiving.');
      const selected = state.wallet;
      const value = await app.rpc.call('getnewaddress', ['Pool mining', 'native'], { wallet: selected });
      poolWorkerId(value, workerLabel, config);
      const ownership = await app.rpc.call('getaddressinfo', [value], { wallet: selected });
      if (ownership.ismine !== true || ownership.native !== true || ownership.type !== 1) throw new Error('Node returned a native address without selected-wallet ownership.');
      if (epoch !== uiEpoch.current) return;
      setPoolAddress(value); setAddressWallet(selected);
    } catch (err) { setError(err); }
    finally { setBusy(false); }
  };
  const stop = () => { ++uiEpoch.current; miner.current.stop(); poolMiner.current.stop(); };
  const poolSupported = config.network.kind === 'lotus-v2' && Boolean(config.address.nativeHrp);
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
      <h2>Mining mode</h2>
      <select aria-label="Mining mode" value=${mode} disabled=${busy || mining.running} onChange=${(e) => { setMode(e.currentTarget.value); setError(null); }}>
        <option value="solo">Solo</option><option value="pool" disabled=${!poolSupported}>Built-in Lotus V2 pool</option>
      </select>
      ${!poolSupported ? html`<p class="muted">The built-in pool requires Lotus V2 and an advertised native address codec.</p>` : null}
    </section>
    ${mode === 'solo' ? html`<section class="card">
      <h2>Mining payout</h2>
      <${Field} label="Payout address" id="mining-address" hint="Mining rewards go directly to this address. Wallet keys stay in the node.">
        <input id="mining-address" value=${address} onInput=${(e) => setAddress(e.currentTarget.value)} disabled=${busy || mining.running} autocomplete="off" />
      <//>
      <button type="button" class="secondary" onClick=${newAddress} disabled=${busy || mining.running || state.wallet === null}>Create payout address</button>
      <${ErrorText} error=${error} />
    </section>
    ` : html`<section class="card"><h2>Pool payout and worker</h2>
      <p>The pool uses this native address as the worker's PPLNS payout destination.</p>
      <${Field} label="Payout provider" id="pool-provider">
        <select id="pool-provider" value=${payoutSource} disabled=${busy || mining.running} onChange=${(e) => { setPayoutSource(e.currentTarget.value); setPoolAddress(''); setAddressWallet(null); }}>
          <option value="wallet">Selected node wallet</option><option value="external">External native wallet</option>
        </select>
      <//>
      ${payoutSource === 'wallet' ? html`<${Field} label="Payout wallet" id="pool-wallet">
        <select id="pool-wallet" value=${state.wallet ?? ''} disabled=${busy || mining.running || !state.wallets?.length} onChange=${(e) => { setPoolAddress(''); setAddressWallet(null); app.selectWallet(e.currentTarget.value); }}>
          ${(state.wallets ?? []).map((w) => html`<option value=${w}>${w || '(default wallet)'}</option>`)}
        </select>
      <//>
      <button type="button" class="secondary" onClick=${createNativeAddress} disabled=${busy || mining.running || state.wallet === null || !config.wallet?.nativeReceiving}>Create native payout address</button>
      ${!config.wallet?.nativeReceiving ? html`<p>This node does not advertise native wallet receiving. Use a node with native receive support or provide an external native wallet address.</p>` : html`<p>Native receipts are owned by this wallet. Ordinary wallet Send does not yet spend native funds; native transaction signing requires a compatible native transaction provider.</p>`}` : html`<p>Provide a native address from a wallet you control. Ownership is your responsibility; this app cannot verify an external wallet.</p>`}
      <${Field} label="Native payout address" id="pool-address">
        <input id="pool-address" value=${poolAddress} onInput=${(e) => { setPoolAddress(e.currentTarget.value); setAddressWallet(null); }} disabled=${busy || mining.running || payoutSource === 'wallet'} autocomplete="off" />
      <//>
      <${Field} label="Worker name" id="pool-worker" hint="Use a different name for each device mining to the same address.">
        <input id="pool-worker" value=${workerLabel} onInput=${(e) => setWorkerLabel(e.currentTarget.value)} disabled=${busy || mining.running} autocomplete="off" />
      <//>
      <button type="button" class="secondary" onClick=${reviewPool} disabled=${busy || mining.running}>Review pool terms</button>
      ${poolReview ? html`<dl class="details"><dt>Pool address</dt><dd class="mono wrap">${poolReview.terms.poolAddress}</dd><dt>Operator commission</dt><dd>${(poolReview.terms.feeBps / 100).toFixed(2)}% of miner rewards</dd>
        <dt>Operator destination</dt><dd class="mono wrap">${poolReview.terms.operatorAddress || 'No commission'}</dd>
        <dt>PPLNS reward window</dt><dd>${poolReview.terms.window} accepted shares</dd></dl>
        <p>Share statistics and the reward window are held in node memory and clear when the node restarts. Shares do not guarantee a payout. Press Start GPU mining to accept these terms.</p>` : null}
      <${ErrorText} error=${error} />
    </section>`}
    ${testMode && mode === 'solo' ? html`<section class="card"><h2>Regtest blocks</h2>
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
      <div class="actions"><button type="button" disabled=${busy || mining.running || !gpu || (mode === 'pool' ? !poolAddress.trim() || !poolReview : !address.trim())} onClick=${start}>Start GPU mining</button>
        <button type="button" class="secondary" disabled=${!mining.running} onClick=${stop}>Stop mining</button></div>
      <p role="status">${mining.status}</p>
      <dl class="details"><dt>Computed GPU hashes</dt><dd>${mining.hashes}</dd><dt>Session hash rate</dt><dd>${Math.round(mining.hashRate)} hashes/s</dd></dl>
      ${mode === 'pool' ? html`<dl class="details"><dt>Accepted shares</dt><dd>${String(mining.acceptedShares ?? 0)}</dd><dt>Rejected shares</dt><dd>${String(mining.rejectedShares ?? 0)}</dd>
        <dt>Worker estimated hash rate</dt><dd>${String(mining.workerStats?.estimated_hashrate ?? '–')}</dd><dt>PPLNS weight</dt><dd>${String(mining.workerStats?.pplns_weight ?? '–')}</dd>
        <dt>Current PPLNS window</dt><dd>${String(mining.poolInfo?.pplns_window_shares ?? poolReview?.info.pplns_window_shares ?? 0)} / ${poolReview?.terms.window ?? '–'} shares</dd><dt>Pool blocks found</dt><dd>${String(mining.poolInfo?.blocks_found ?? poolReview?.info.blocks_found ?? 0)}</dd></dl>` : null}
      <p class="muted">Counts include completed GPU dispatches only. Session rate includes setup, template refresh and submission time.</p>
    </section>
  </div>`;
}
