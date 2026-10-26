import { BrowserMiner } from './browser-miner.js';
import { poolTerms, assertPoolTerms, decodePoolJob, validatePoolCandidate } from './pool-mining.js';

// Same worker/session/stats ownership as solo mining. Every new dispatch uses
// fresh pool work, including the current VarDiff target after each submission.
export class BrowserPoolMiner extends BrowserMiner {
  constructor(options) { super(options); this.cursors = new Map(); }
  async start(workerId, descriptor, reviewedTerms) {
    this.stop();
    this.workerId = workerId; this.descriptor = descriptor; this.terms = reviewedTerms;
    this.cursor = null; this.prefix = null; this.jobGeneration = 0;
    this.totalHashes = 0; this.started = performance.now();
    this.controller = new AbortController();
    const generation = this.generation;
    this.onState({ running: true, status: 'Checking reviewed pool terms…', hashes: 0, hashRate: 0, acceptedShares: 0, rejectedShares: 0 });
    try {
      const raw = await this.call('getpoolinfo');
      const current = poolTerms(raw);
      assertPoolTerms(raw, reviewedTerms);
      if (current.window !== reviewedTerms.window) throw new Error('Pool reward window changed. Review the terms and press Start again.');
      if (generation === this.generation) await this.next(generation);
    } catch (error) { if (generation === this.generation) this.stop(error.message); }
  }
  async next(generation) {
    if (generation !== this.generation) return;
    const jobGeneration = ++this.jobGeneration;
    this.worker?.terminate(); this.worker = null; clearTimeout(this.timer);
    const [raw, info, stats] = await Promise.all([this.call('getminingjob', [this.workerId, false]), this.call('getpoolinfo'), this.call('getpoolworker', [this.workerId])]);
    if (generation !== this.generation || jobGeneration !== this.jobGeneration) return;
    const terms = poolTerms(info); assertPoolTerms(info, this.terms);
    if (terms.window !== this.terms.window) throw new Error('Pool reward window changed. Review the terms and press Start again.');
    const work = decodePoolJob(raw, this.descriptor, this.workerId, this.terms);
    this.onState({ poolInfo: info, workerStats: stats, acceptedShares: stats.accepted_shares, rejectedShares: stats.rejected_shares });
    const cursorKey = `${this.descriptor.chainid}:${this.workerId}:${raw.nonce_prefix}`;
    if (this.prefix !== raw.nonce_prefix) { this.prefix = raw.nonce_prefix; this.cursor = this.cursors.get(cursorKey) ?? work.nonceStart; }
    if (this.cursor >= work.nonceEnd) throw new Error('Assigned pool nonce range exhausted. Stop and use a new worker name.');
    const first = this.cursor;
    this.lastHashes = 0;
    const worker = this.createWorker(); this.worker = worker;
    const current = () => generation === this.generation && jobGeneration === this.jobGeneration && worker === this.worker;
    this.onState({ running: true, status: 'Hashing pool shares with WebGPU', poolJob: raw });
    worker.onmessage = async ({ data }) => {
      if (!current()) return;
      try {
        if (data.type === 'error') throw new Error(data.message);
        if (!['progress', 'candidate', 'exhausted'].includes(data.type)) throw new Error('Invalid GPU pool response.');
        this.updateStats(data);
        if (first + BigInt(data.hashes) > work.nonceEnd) throw new Error('Invalid GPU pool hash counter.');
        this.cursor = first + BigInt(data.hashes);
        this.cursors.set(cursorKey, this.cursor);
        if (this.cursors.size > 100) this.cursors.delete(this.cursors.keys().next().value);
        if (data.type === 'progress') return;
        clearTimeout(this.timer); worker.terminate(); this.worker = null;
        if (data.type === 'candidate') {
          const candidate = validatePoolCandidate(work, BigInt(data.nonce));
          if (BigInt(data.nonce) < first || BigInt(data.nonce) >= this.cursor) throw new Error('GPU pool candidate is outside its completed dispatch.');
          this.onState({ running: true, status: 'Submitting CPU-verified pool share…' });
          const result = await this.call('submitminingshare', [work.jobId, this.workerId, candidate.nonce]);
          if (generation !== this.generation || jobGeneration !== this.jobGeneration) return;
          if (typeof result?.accepted !== 'boolean' || typeof result.block_found !== 'boolean') throw new Error('Invalid pool share response.');
          this.onState({ shareResult: result, acceptedShares: result.accepted_shares, rejectedShares: result.rejected_shares });
          if (result.block_found) this.onBlock();
          if (!result.accepted && !['job-not-found', 'high-hash'].includes(result.reason)) throw new Error(`Pool rejected share: ${result.reason}`);

        }
        await this.next(generation);
      } catch (error) { if (generation === this.generation) this.stop(error.message); }
    };
    worker.onerror = (event) => { if (current()) this.stop(event.message || 'GPU pool worker failed.'); };
    worker.postMessage({ type: 'start', work: { descriptor: work.descriptor, header: work.header, target: work.target, chainid: work.chainid,
      nonceStart: first.toString(), nonceEnd: work.nonceEnd.toString() } });
    this.timer = setTimeout(async () => {
      try { if (current()) await this.next(generation); }
      catch (error) { if (generation === this.generation) this.stop(error.message); }
    }, 5000);
  }
}
