/**
 * Lotus V2 Portal Frontend Application (`web/lotus-v2-portal/public/app.js`)
 *
 * Connects:
 * 1. The Lotus V2 Dispatch ($10/mo Paid Newsletter) with 3 unlock flows:
 *    - Browser WebGPU / Worker mining under `worker = "sub:<email_or_id>"`
 *    - Lotus V2 Native Covenant payment verifier (`POST /api/newsletter/unlock-covenant`)
 *    - Card / Fiat $10/mo checkout modal (`POST /api/newsletter/unlock-card`)
 * 2. Live SSE job stream (`GET /pool/jobs?worker=...`) -> `LotusV2MinerEngine` -> `POST /pool/submit`
 * 3. Real-time pool & miner telemetry dashboard.
 */

(function () {
  'use strict';

  const Core = window.LotusV2MinerCore;
  const WebGPUModule = window.LotusV2WebGPUMiner;

  const state = {
    subscriber: 'satoshi@lotus.org',
    miningMode: 'newsletter', // 'newsletter' | 'wallet'
    walletWorker: 'lotus_16PSJ2WalletWorkerPPLNS8x9k',
    activeWorker: 'sub:satoshi@lotus.org',
    activeJob: null,
    eventSource: null,
    minerEngine: null,
    submittingShare: false,
    lastShareSubmitTs: 0,
    unlockedState: false,
  };

  // DOM Elements
  const el = {
    sseIndicator: document.getElementById('sse-indicator'),
    sseStatusText: document.getElementById('sse-status-text'),
    topBackendLabel: document.getElementById('top-backend-label'),
    topSubBadge: document.getElementById('top-sub-badge'),
    subPill: document.getElementById('sub-pill'),

    subscriberInput: document.getElementById('subscriber-input'),
    heroMineBtn: document.getElementById('hero-mine-btn'),
    subStatusTag: document.getElementById('sub-status-tag'),
    subProgressFill: document.getElementById('sub-progress-fill'),
    subCreditText: document.getElementById('sub-credit-text'),
    subMethodText: document.getElementById('sub-method-text'),

    unlockWorkerLabel: document.getElementById('unlock-worker-label'),
    cardMineToggleBtn: document.getElementById('card-mine-toggle-btn'),
    unlockCovenantBtn: document.getElementById('unlock-covenant-btn'),
    openCardModalBtn: document.getElementById('open-card-modal-btn'),
    articlesContainer: document.getElementById('articles-container'),

    modeNewsletterBtn: document.getElementById('mode-newsletter-btn'),
    modeWalletBtn: document.getElementById('mode-wallet-btn'),
    workerInput: document.getElementById('worker-input'),
    miningModeHint: document.getElementById('mining-mode-hint'),
    startMinerBtn: document.getElementById('start-miner-btn'),
    stopMinerBtn: document.getElementById('stop-miner-btn'),
    mineSingleShareBtn: document.getElementById('mine-single-share-btn'),

    gaugeLocalHashrate: document.getElementById('gauge-local-hashrate'),
    gaugeLocalHashes: document.getElementById('gauge-local-hashes'),
    gaugeBackend: document.getElementById('gauge-backend'),
    gaugeBackendSub: document.getElementById('gauge-backend-sub'),
    gaugeJobId: document.getElementById('gauge-job-id'),
    gaugeBodyHash: document.getElementById('gauge-body-hash'),
    gaugeAcceptedShares: document.getElementById('gauge-accepted-shares'),
    gaugePplnsEarned: document.getElementById('gauge-pplns-earned'),
    gaugeVardiff: document.getElementById('gauge-vardiff'),
    gaugePoolHashrate: document.getElementById('gauge-pool-hashrate'),
    gaugePoolMiners: document.getElementById('gauge-pool-miners'),
    gaugeLastShare: document.getElementById('gauge-last-share'),
    gaugeLastBlockid: document.getElementById('gauge-last-blockid'),
    recentBlocksTbody: document.getElementById('recent-blocks-tbody'),

    cardModal: document.getElementById('card-modal'),
    closeCardModalBtn: document.getElementById('close-card-modal-btn'),
    cardCheckoutForm: document.getElementById('card-checkout-form'),
    checkoutEmail: document.getElementById('checkout-email'),
  };

  function formatHashrate(hps) {
    if (!hps || hps <= 0) return '0.00 KH/s';
    if (hps >= 1e6) return `${(hps / 1e6).toFixed(2)} MH/s`;
    if (hps >= 1e3) return `${(hps / 1e3).toFixed(2)} KH/s`;
    return `${hps.toFixed(0)} H/s`;
  }

  function shortHex(hex, prefix = 10, suffix = 8) {
    if (!hex || hex.length <= prefix + suffix + 2) return hex || '—';
    return `${hex.slice(0, prefix)}…${hex.slice(-suffix)}`;
  }

  function syncWorkerFromInputs() {
    const cleanSub = (el.subscriberInput.value || 'satoshi@lotus.org').trim().replace(/^sub:/, '');
    state.subscriber = cleanSub || 'satoshi@lotus.org';
    el.checkoutEmail.value = state.subscriber;

    if (state.miningMode === 'newsletter') {
      state.activeWorker = `sub:${state.subscriber}`;
      el.workerInput.value = state.activeWorker;
      el.miningModeHint.textContent = 'Mode: Newsletter Subscription Unlock ($2.50 credit / share)';
    } else {
      if (el.workerInput.value.startsWith('sub:')) {
        el.workerInput.value = state.walletWorker;
      }
      state.activeWorker = el.workerInput.value.trim() || state.walletWorker;
      el.miningModeHint.textContent = 'Mode: Direct Wallet PPLNS Pool Payouts (50% Miner Share)';
    }

    el.unlockWorkerLabel.textContent = `sub:${state.subscriber}`;
    el.subMethodText.innerHTML = `Worker: <code>sub:${state.subscriber}</code>`;
  }

  function renderArticles(articles, unlocked) {
    if (!el.articlesContainer) return;
    el.articlesContainer.innerHTML = articles
      .map((art) => {
        const lockBadge = unlocked
          ? '<span class="pill live">🔓 SUBSCRIBER UNLOCKED</span>'
          : '<span class="pill">🔒 $10/MO PAYWALL</span>';
        const boxClass = unlocked ? 'premium-box unlocked' : 'premium-box locked';
        const itemsHtml = (art.premium_content || [])
          .map((line) => `<li>${line}</li>`)
          .join('');
        return `
          <article class="article-card" data-article-id="${art.id}">
            <div class="article-meta">
              <span>${art.issue}</span>
              ${lockBadge}
            </div>
            <h4>${art.title}</h4>
            <p class="article-subtitle">${art.subtitle}</p>
            <p class="article-preview">${art.free_preview}</p>
            <div class="${boxClass}">
              <strong>${unlocked ? 'Subscriber Technical Deep-Dive:' : 'Premium Subscriber Section:'}</strong>
              <ul class="premium-list">${itemsHtml}</ul>
            </div>
            <pre class="code-block">${art.code_snippet}</pre>
          </article>
        `;
      })
      .join('');
  }

  function updateSubscriptionUI(sub) {
    if (!sub) return;
    const isUnlocked = Boolean(sub.unlocked || sub.active_mining_access);
    const usd = Number(sub.usd_credited || 0).toFixed(2);
    const pct = Math.min(100, Number(sub.progress_pct || 0));

    el.subProgressFill.style.width = `${pct}%`;
    el.subCreditText.textContent = `$${usd} / $10.00 credited (${sub.shares_submitted || 0} / ${sub.shares_required || 4} BLAKE3 shares)`;

    if (isUnlocked) {
      el.subStatusTag.textContent =
        pct >= 100 ? 'UNLOCKED ($10.00 FULL MONTH)' : 'UNLOCKED (ACTIVE MINING)';
      el.subStatusTag.className = 'pill live';
      el.subPill.className = 'pill live';
      el.topSubBadge.textContent = `Unlocked ($${usd} / $10.00)`;
    } else {
      el.subStatusTag.textContent = 'LOCKED';
      el.subStatusTag.className = 'pill';
      el.subPill.className = 'pill';
      el.topSubBadge.textContent = `Locked ($${usd} / $10.00)`;
    }

    if (isUnlocked !== state.unlockedState) {
      state.unlockedState = isUnlocked;
      fetchArticles();
    }
  }

  async function fetchArticles() {
    try {
      const resp = await fetch(
        `/api/newsletter/articles?subscriber=${encodeURIComponent(state.subscriber)}`
      );
      const data = await resp.json();
      if (data.subscription) {
        state.unlockedState = Boolean(
          data.subscription.unlocked || data.subscription.active_mining_access
        );
        updateSubscriptionUI(data.subscription);
      }
      if (data.articles) {
        renderArticles(data.articles, state.unlockedState);
      }
    } catch (err) {
      console.error('Failed to load newsletter articles:', err);
    }
  }

  async function fetchPoolStats() {
    try {
      const url = `/api/pool/stats?worker=${encodeURIComponent(state.activeWorker)}&subscriber=${encodeURIComponent(state.subscriber)}`;
      const resp = await fetch(url);
      const stats = await resp.json();

      if (stats.active_job) {
        el.gaugeJobId.textContent = `${stats.active_job.job_id} (#${stats.active_job.height})`;
        el.gaugeBodyHash.textContent = `BodyHash: ${shortHex(stats.active_job.body_hash, 12, 10)}`;
        if (!state.activeJob || state.activeJob.job_id !== stats.active_job.job_id) {
          applyNewJob(stats.active_job);
        }
      }

      if (stats.worker_stats) {
        el.gaugeAcceptedShares.textContent = String(stats.worker_stats.shares_accepted || 0);
        el.gaugePplnsEarned.textContent = `Est. PPLNS Credit: ${(stats.worker_stats.pplns_xpi_earned || 0).toFixed(2)} XPI`;
        el.gaugeVardiff.textContent = shortHex(stats.worker_stats.vardiff_target, 10, 8);
      }

      el.gaugePoolHashrate.textContent = formatHashrate(stats.pool_hashrate_hps || 1420000);
      el.gaugePoolMiners.textContent = `${stats.connected_miners || 12} active miners • ${stats.total_shares_accepted || 0} pool shares`;

      if (stats.subscription) {
        updateSubscriptionUI(stats.subscription);
      }

      if (Array.isArray(stats.recent_blocks)) {
        el.recentBlocksTbody.innerHTML = stats.recent_blocks
          .slice(0, 6)
          .map(
            (b) => `
            <tr>
              <td>#${b.height}</td>
              <td title="${b.block_id}">${shortHex(b.block_id, 12, 10)}</td>
              <td>${b.finder}</td>
              <td>${b.miner_xpi} / ${b.staker_xpi} / ${b.treasury_xpi} XPI</td>
            </tr>
          `
          )
          .join('');
      }
    } catch (err) {
      console.error('Failed to fetch pool stats:', err);
    }
  }

  function applyNewJob(jobData) {
    state.activeJob = jobData;
    el.gaugeJobId.textContent = jobData.height
      ? `${jobData.job_id} (#${jobData.height})`
      : jobData.job_id;

    try {
      const headerBytes = Core.hexToBytes(jobData.header);
      const chainBytes = Core.hexToBytes(jobData.chain_id);
      const { bodyHash } = Core.hashes(headerBytes, chainBytes);
      el.gaugeBodyHash.textContent = `BodyHash: ${shortHex(Core.bytesToHex(bodyHash), 12, 10)}`;
    } catch (_) {}

    if (state.minerEngine) {
      state.minerEngine.setJob(jobData);
    }
  }

  function connectSseJobStream() {
    if (state.eventSource) {
      state.eventSource.close();
      state.eventSource = null;
    }

    const sseUrl = `/pool/jobs?worker=${encodeURIComponent(state.activeWorker)}`;
    if (typeof EventSource !== 'undefined') {
      const es = new EventSource(sseUrl);
      state.eventSource = es;

      es.onopen = () => {
        el.sseIndicator.className = 'pill live';
        el.sseStatusText.textContent = `SSE: Connected (/pool/jobs)`;
      };

      es.addEventListener('job', (ev) => {
        try {
          const job = JSON.parse(ev.data);
          el.sseIndicator.className = 'pill live';
          el.sseStatusText.textContent = `SSE: Active (${job.job_id})`;
          applyNewJob(job);
        } catch (err) {
          console.error('Invalid SSE job JSON:', err);
        }
      });

      es.onerror = () => {
        el.sseIndicator.className = 'pill';
        el.sseStatusText.textContent = 'SSE: Reconnecting…';
      };
    }
  }

  async function submitShareToPool(shareMsg) {
    const now = performance.now();
    // Rate-limit browser automatic submissions to at most ~4 shares/sec so UI animation is readable
    if (state.submittingShare || now - state.lastShareSubmitTs < 220) {
      return null;
    }
    state.submittingShare = true;
    state.lastShareSubmitTs = now;

    try {
      const resp = await fetch('/pool/submit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          protocol: 'v2',
          job_id: shareMsg.job_id,
          worker: state.activeWorker,
          nonce: Number(shareMsg.nonce),
          nonce_hex: shareMsg.nonce_hex,
          header: shareMsg.header_hex,
          block_id: shareMsg.block_id_hex,
        }),
      });
      const result = await resp.json();
      if (result.accepted) {
        el.gaugeLastShare.textContent = result.block_found
          ? `🎉 Block Found! (Nonce #${result.nonce})`
          : `Accepted (Nonce #${result.nonce})`;
        el.gaugeLastBlockid.textContent = `BlockID: ${shortHex(result.block_id, 12, 10)}`;
        el.gaugeAcceptedShares.textContent = String(result.shares_accepted || 1);
        if (result.vardiff_target) {
          el.gaugeVardiff.textContent = shortHex(result.vardiff_target, 10, 8);
        }
        if (result.subscription) {
          updateSubscriptionUI(result.subscription);
        }
        await fetchPoolStats();
      }
      return result;
    } catch (err) {
      console.error('Failed to submit share:', err);
      return null;
    } finally {
      state.submittingShare = false;
    }
  }

  async function mineAndSubmitSingleVerifiedShare() {
    syncWorkerFromInputs();
    if (!state.activeJob) {
      await fetchPoolStats();
    }
    if (!state.activeJob) return;

    const header = Core.hexToBytes(state.activeJob.header);
    const chainId = Core.hexToBytes(state.activeJob.chain_id);
    const target = Core.hexToBytes(state.activeJob.target);
    const prepared = Core.prepareTemplates(header, chainId, target);

    // Search in chunks of 1024 nonces until a valid share meeting `target` is found
    let startNonce = BigInt(Math.floor(Math.random() * 100000));
    for (let attempt = 0; attempt < 64; attempt++) {
      const { matches } = Core.hashNoncesWordBatch(
        prepared.workWords,
        prepared.idPrefixWords,
        prepared.targetWords,
        startNonce,
        1024,
        false
      );
      if (matches.length > 0) {
        const hit = matches[0];
        const solvedHeader = Core.writeNonceLE(header, hit.nonce);
        state.lastShareSubmitTs = 0; // bypass throttle for explicit user action
        await submitShareToPool({
          job_id: state.activeJob.job_id,
          nonce: hit.nonce.toString(),
          nonce_hex: hit.nonce.toString(16).padStart(16, '0'),
          header_hex: Core.bytesToHex(solvedHeader),
          block_id_hex: Core.bytesToHex(hit.blockId),
        });
        return;
      }
      startNonce += 1024n;
    }
  }

  async function startMining(forceNewsletterMode = false) {
    if (forceNewsletterMode) {
      state.miningMode = 'newsletter';
      el.modeNewsletterBtn.classList.add('active');
      el.modeWalletBtn.classList.remove('active');
    }
    syncWorkerFromInputs();
    connectSseJobStream();

    if (!state.activeJob) {
      await fetchPoolStats();
    }
    if (state.activeJob) {
      state.minerEngine.setJob(state.activeJob);
    }

    await state.minerEngine.start();
    el.startMinerBtn.style.display = 'none';
    el.stopMinerBtn.style.display = 'inline-flex';
    el.cardMineToggleBtn.textContent = `⏹ Stop Subscription Miner (${state.activeWorker})`;
  }

  function stopMining() {
    if (state.minerEngine) {
      state.minerEngine.stop();
    }
    el.startMinerBtn.style.display = 'inline-flex';
    el.stopMinerBtn.style.display = 'none';
    el.cardMineToggleBtn.textContent = `⚡ Start Mining Subscription (${state.activeWorker})`;
  }

  async function initPortal() {
    state.minerEngine = new WebGPUModule.LotusV2MinerEngine({
      workerScriptUrl: '/miner-worker.js',
      onBackendChange: (backend) => {
        const label =
          backend === 'webgpu-wgsl' ? 'WebGPU WGSL Compute' : 'Web Worker CPU/SIMD';
        el.topBackendLabel.textContent = label;
        el.gaugeBackend.textContent = label;
        el.gaugeBackendSub.textContent =
          backend === 'webgpu-wgsl'
            ? '@compute @workgroup_size(256) • 4B atomic readback'
            : 'Background Web Worker • Pre-packed u32 BLAKE3';
      },
      onStats: (stats) => {
        el.gaugeLocalHashrate.textContent = formatHashrate(stats.hashrate_hps);
        el.gaugeLocalHashes.textContent = `${stats.total_hashes.toLocaleString()} nonces • ${stats.dispatch_ms.toFixed(1)}ms slice`;
      },
      onShare: (shareMsg) => {
        submitShareToPool(shareMsg);
      },
    });

    await state.minerEngine.init();
    syncWorkerFromInputs();
    await fetchArticles();
    await fetchPoolStats();
    connectSseJobStream();

    // Event Listeners
    el.subscriberInput.addEventListener('change', () => {
      syncWorkerFromInputs();
      fetchArticles();
      fetchPoolStats();
      connectSseJobStream();
    });

    el.heroMineBtn.addEventListener('click', () => startMining(true));
    el.cardMineToggleBtn.addEventListener('click', () => {
      if (state.minerEngine && state.minerEngine.running) {
        stopMining();
      } else {
        startMining(true);
      }
    });

    el.startMinerBtn.addEventListener('click', () => startMining(false));
    el.stopMinerBtn.addEventListener('click', () => stopMining());
    el.mineSingleShareBtn.addEventListener('click', () => mineAndSubmitSingleVerifiedShare());

    el.modeNewsletterBtn.addEventListener('click', () => {
      state.miningMode = 'newsletter';
      el.modeNewsletterBtn.classList.add('active');
      el.modeWalletBtn.classList.remove('active');
      syncWorkerFromInputs();
      connectSseJobStream();
      fetchPoolStats();
    });

    el.modeWalletBtn.addEventListener('click', () => {
      state.miningMode = 'wallet';
      el.modeWalletBtn.classList.add('active');
      el.modeNewsletterBtn.classList.remove('active');
      el.workerInput.value = state.walletWorker;
      syncWorkerFromInputs();
      connectSseJobStream();
      fetchPoolStats();
    });

    el.unlockCovenantBtn.addEventListener('click', async () => {
      syncWorkerFromInputs();
      const resp = await fetch('/api/newsletter/unlock-covenant', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ subscriber: state.subscriber }),
      });
      const data = await resp.json();
      if (data.subscription) {
        updateSubscriptionUI(data.subscription);
        await fetchArticles();
      }
    });

    el.openCardModalBtn.addEventListener('click', () => {
      syncWorkerFromInputs();
      el.cardModal.classList.add('open');
    });

    el.closeCardModalBtn.addEventListener('click', () => {
      el.cardModal.classList.remove('open');
    });

    el.cardCheckoutForm.addEventListener('submit', async (ev) => {
      ev.preventDefault();
      state.subscriber = (el.checkoutEmail.value || 'satoshi@lotus.org').trim();
      el.subscriberInput.value = state.subscriber;
      syncWorkerFromInputs();
      const resp = await fetch('/api/newsletter/unlock-card', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ subscriber: state.subscriber, plan: 'monthly-10-usd' }),
      });
      const data = await resp.json();
      el.cardModal.classList.remove('open');
      if (data.subscription) {
        updateSubscriptionUI(data.subscription);
        await fetchArticles();
      }
    });

    setInterval(fetchPoolStats, 4000);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initPortal);
  } else {
    initPortal();
  }
})();
