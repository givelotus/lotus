import { decodeMiningWork, validateCandidate } from './mining-work.js';

// Lifecycle owner for one explicitly started mining session. No persistence,
// automatic start, or automatic resume after hidden tabs/device failures.
export class BrowserMiner {
  constructor({ rpc, createWorker, onState = () => {}, onBlock = () => {} }) {
    this.rpc = rpc;
    this.createWorker = createWorker ?? (() => new Worker(new URL('../mining/worker.js', import.meta.url), { type: 'module' }));
    this.onState = onState; this.onBlock = onBlock;
    this.generation = 0; this.totalHashes = 0; this.lastHashes = 0;
  }
  stop(reason = 'Stopped') {
    ++this.generation;
    clearTimeout(this.timer); this.timer = null;
    this.controller?.abort(); this.worker?.terminate(); this.worker = null;
    this.onState({ running: false, status: reason, hashes: this.totalHashes, hashRate: 0 });
  }
  async start(address, descriptor) {
    this.stop();
    this.address = address; this.descriptor = descriptor;
    this.totalHashes = 0; this.started = performance.now();
    this.controller = new AbortController();
    const generation = this.generation;
    this.onState({ running: true, status: 'Requesting a candidate from the node…', hashes: 0, hashRate: 0 });
    try { await this.next(generation); }
    catch (error) { if (generation === this.generation) this.stop(error.message); }
  }
  call(method, params = []) { return this.rpc.call(method, params, { signal: this.controller.signal }); }
  updateStats(message) {
    if (!Number.isSafeInteger(message.hashes) || message.hashes < this.lastHashes) throw new Error('Invalid GPU hash counter.');
    this.totalHashes += message.hashes - this.lastHashes; this.lastHashes = message.hashes;
    this.onState({ running: true, status: 'Hashing with WebGPU', hashes: this.totalHashes,
      hashRate: this.totalHashes / Math.max(0.001, (performance.now() - this.started) / 1000) });
  }
  async next(generation) {
    if (generation !== this.generation) return;
    this.worker?.terminate(); clearTimeout(this.timer);
    const parent = await this.call('getbestblockhash');
    if (generation !== this.generation) return;
    const raw = await this.call(this.descriptor.template_rpc, [this.address]);
    const work = decodeMiningWork(raw, this.descriptor, parent);
    if (generation !== this.generation) return;
    this.lastHashes = 0;
    const workStarted = performance.now();
    const worker = this.createWorker(); this.worker = worker;
    worker.onmessage = async ({ data }) => {
      if (generation !== this.generation || worker !== this.worker) return;
      try {
        if (data.type === 'error') throw new Error(data.message);
        this.updateStats(data);
        if (data.type === 'progress') return;
        worker.terminate(); this.worker = null;
        if (data.type === 'candidate') {
          const candidate = validateCandidate(work, BigInt(data.nonce));
          const current = await this.call('getbestblockhash');
          if (generation !== this.generation) return;
          if (current === work.parent) {
            this.onState({ running: true, status: 'Submitting CPU-verified candidate…' });
            const result = await this.call(this.descriptor.submit_rpc, [candidate.blockhex]);
            if (generation !== this.generation) return;
            if (result !== null) throw new Error(`Node rejected candidate: ${String(result)}`);
            this.onBlock();
          }
        }
        await this.next(generation);
      } catch (error) { if (generation === this.generation) this.stop(error.message); }
    };
    worker.onerror = (event) => { if (generation === this.generation && worker === this.worker) this.stop(event.message || 'GPU worker failed.'); };
    worker.postMessage({ type: 'start', work: { descriptor: work.descriptor, header: work.header, target: work.target, chainid: work.chainid } });
    const poll = async () => {
      try {
        const current = await this.call('getbestblockhash');
        if (generation !== this.generation || worker !== this.worker) return;
        if (current !== work.parent || performance.now() - workStarted >= 15000) await this.next(generation);
        else this.timer = setTimeout(poll, 5000);
      } catch (error) { if (generation === this.generation) this.stop(error.message); }
    };
    this.timer = setTimeout(poll, 5000);
  }
}
