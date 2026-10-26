// Node information (bitcoin-qt's debug window "Information" tab).

import { html } from '../vendor/htm-preact-standalone.mjs';
import { useAsync, ErrorText, Spinner, formatBytes, formatDuration, formatTime } from '../ui/components.js';
import { RpcError } from '../lib/rpc.js';

export function NodeView({ app, state }) {
  const info = useAsync(async () => {
    const [net, chain, mempool, uptime, memory, rpcinfo] = await app.rpc.batch([
      ['getnetworkinfo'], ['getblockchaininfo'], ['getmempoolinfo'], ['uptime'], ['getmemoryinfo'], ['getrpcinfo'],
    ]);
    return { net, chain, mempool, uptime, memory, rpcinfo };
  }, [], { intervalMs: 5000 });
  if (!info.value) return info.error ? html`<${ErrorText} error=${info.error} />` : html`<${Spinner} />`;
  const { net, chain, mempool, uptime, memory, rpcinfo } = info.value;
  const ok = (v) => !(v instanceof RpcError) && v !== undefined;
  const p = state.profile;
  const row = (label, value) => html`<dt>${label}</dt><dd>${value}</dd>`;
  return html`
    <div class="node">
      <h1>Node</h1>
      <div class="grid two">
        <section class="card">
          <h2>General</h2>
          <dl>
            ${ok(net) ? row('Client', net.subversion) : null}
            ${ok(net) ? row('Protocol version', net.protocolversion) : null}
            ${row('Profile', p ? `${p.profile} (${p.addressFormat} addresses, ${p.ticker}, ${p.decimals} decimals)` : '–')}
            ${ok(uptime) ? row('Uptime', formatDuration(uptime)) : null}
            ${ok(rpcinfo) && rpcinfo.logpath ? row('Debug log', html`<span class="mono wrap">${rpcinfo.logpath}</span>`) : null}
            ${ok(memory) && memory.locked ? row('Locked memory', `${formatBytes(memory.locked.used)} used of ${formatBytes(memory.locked.total)}`) : null}
          </dl>
        </section>
        <section class="card">
          <h2>Network</h2>
          <dl>
            ${ok(net) ? html`
              ${row('Connections', `${net.connections} (${net.connections_in ?? 0} in, ${net.connections_out ?? 0} out)`)}
              ${row('Network active', net.networkactive ? 'yes' : 'no')}
              ${row('Relay fee', `${net.relayfee} ${p?.ticker ?? ''}/kB`)}
              ${row('Networks', (net.networks ?? []).filter((n) => n.reachable).map((n) => n.name).join(', ') || 'none')}
              ${row('Proxies', (net.networks ?? []).filter((n) => n.proxy).map((n) => `${n.name}: ${n.proxy}`).join(', ') || 'none')}
              ${row('Local addresses', (net.localaddresses ?? []).map((a) => `${a.address}:${a.port}`).join(', ') || 'none')}
              ${net.warnings ? row('Warnings', String(net.warnings)) : null}` : null}
          </dl>
        </section>
        <section class="card">
          <h2>Block chain</h2>
          <dl>
            ${ok(chain) ? html`
              ${row('Chain', chain.chain)}
              ${row('Blocks', chain.blocks)}
              ${row('Headers', chain.headers)}
              ${row('Best block', html`<span class="mono wrap">${chain.bestblockhash}</span>`)}
              ${row('Last block time', formatTime(chain.mediantime))}
              ${row('Verification progress', `${(Number(chain.verificationprogress) * 100).toFixed(2)}%`)}
              ${row('Initial block download', chain.initialblockdownload ? 'yes' : 'no')}
              ${row('Size on disk', formatBytes(chain.size_on_disk))}
              ${row('Pruned', chain.pruned ? 'yes' : 'no')}` : null}
          </dl>
        </section>
        <section class="card">
          <h2>Mempool</h2>
          <dl>
            ${ok(mempool) ? html`
              ${row('Transactions', mempool.size)}
              ${row('Size', formatBytes(mempool.bytes))}
              ${row('Memory usage', `${formatBytes(mempool.usage)} of ${formatBytes(mempool.maxmempool)}`)}
              ${row('Minimum fee', `${mempool.mempoolminfee} ${p?.ticker ?? ''}/kB`)}` : null}
          </dl>
        </section>
      </div>
      <p class="muted">Settings such as pruning, database cache, proxy and listening are changed in the node's configuration file and take effect after a restart.</p>
    </div>`;
}
