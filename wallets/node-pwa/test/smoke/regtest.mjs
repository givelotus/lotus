// Starts and stops a throwaway regtest lotusd for the smoke test: fresh
// datadir, free ports, P2P listening disabled. Never touches other datadirs.

import { spawn } from 'node:child_process';
import { mkdtempSync, readFileSync, existsSync } from 'node:fs';
import { createServer } from 'node:net';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

export function freePort() {
  return new Promise((resolve, reject) => {
    const s = createServer();
    s.once('error', reject);
    s.listen(0, '127.0.0.1', () => {
      const { port } = s.address();
      s.close(() => resolve(port));
    });
  });
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

export async function startNode(binary, options = {}) {
  const base = options.datadirBase ?? process.env.NODE_PWA_SMOKE_TMP ?? tmpdir();
  const datadir = mkdtempSync(join(base, 'node-pwa-regtest-'));
  const rpcPort = options.rpcPort ?? await freePort();
  const p2pPort = options.p2pPort ?? await freePort();
  const args = ['-regtest', `-datadir=${datadir}`, `-rpcport=${rpcPort}`, `-port=${p2pPort}`, '-listen=0',
    '-server=1', '-rpcbind=127.0.0.1', '-rpcallowip=127.0.0.1', '-printtoconsole=0', '-discover=0', '-dnsseed=0', '-fixedseeds=0',
    // Encrypting a wallet encrypts its whole keypool, which is slow with the default 1000 keys.
    '-keypool=5', ...(options.extraArgs ?? [])];
  const proc = spawn(binary, args, { stdio: ['ignore', 'ignore', 'pipe'] });
  let stderr = '';
  proc.stderr.on('data', (d) => { stderr += d; });
  const cookieFile = join(datadir, 'regtest', '.cookie');
  const rpcUrl = `http://127.0.0.1:${rpcPort}/`;
  const node = {
    datadir, rpcPort, p2pPort, rpcUrl, cookieFile, proc,
    async rpc(method, params = [], wallet) {
      const auth = 'Basic ' + Buffer.from(readFileSync(cookieFile, 'utf8').trim()).toString('base64');
      const resp = await fetch(new URL(wallet === undefined ? '/' : `/wallet/${encodeURIComponent(wallet)}`, rpcUrl), {
        method: 'POST', headers: { Authorization: auth, 'Content-Type': 'application/json' },
        body: JSON.stringify({ jsonrpc: '1.0', id: 1, method, params }),
      });
      const j = await resp.json();
      if (j.error) throw new Error(`${method}: ${j.error.message} (${j.error.code})`);
      return j.result;
    },
    async stop() {
      if (proc.exitCode !== null) return;
      const exited = new Promise((r) => proc.once('exit', r));
      try { await node.rpc('stop'); } catch { proc.kill('SIGTERM'); }
      const t = setTimeout(() => proc.kill('SIGKILL'), 30000);
      await exited;
      clearTimeout(t);
    },
  };
  for (let i = 0; i < 300; i++) {
    if (proc.exitCode !== null) throw new Error(`lotusd exited (${proc.exitCode}): ${stderr}`);
    if (existsSync(cookieFile)) {
      try {
        await node.rpc('getblockcount');
        return node;
      } catch {
        // warming up
      }
    }
    await sleep(100);
  }
  await node.stop();
  throw new Error('lotusd did not become ready');
}
