// JSON-RPC client for the node.
//
// Requests go to "/" (node RPCs) or "/wallet/<name>" (wallet RPCs) on the
// page's own origin. Authentication is delegated to an auth object (see
// session.js), which supplies extra headers and is told about 401 replies.
// That is the only difference between the dev proxy mode (the proxy adds Basic
// auth) and the daemon's browser sessions (cookie plus X-CSRF-Token).

import { parse, stringify } from './json.js';

export class RpcError extends Error {
  /** @param {number} code @param {string} message @param {string} method */
  constructor(code, message, method) {
    super(message);
    this.code = code;
    this.method = method;
  }
}

/** HTTP-level failure: 401 (login required), 403 (not permitted), others. */
export class HttpError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

/** The node could not be reached (connection refused, timeout, offline). */
export class NetworkError extends Error {}

export const RPC_IN_WARMUP = -28;
export const RPC_WALLET_NOT_FOUND = -18;
export const RPC_WALLET_NOT_SPECIFIED = -19;
export const RPC_WALLET_UNLOCK_NEEDED = -13;
export const RPC_WALLET_PASSPHRASE_INCORRECT = -14;

/**
 * @typedef {{headers(): Record<string,string>, onUnauthorized(): void}} RpcAuth
 * @typedef {{wallet?: string|null, timeoutMs?: number, signal?: AbortSignal}} CallOpts
 */

/**
 * @param {{auth: RpcAuth, fetch?: typeof fetch, base?: string,
 *          onNetworkError?: (e: Error) => void, onReachable?: () => void,
 *          onWarmup?: (msg: string) => void}} cfg
 */
export function createRpc(cfg) {
  const doFetch = cfg.fetch ?? globalThis.fetch.bind(globalThis);
  const base = cfg.base ?? '';
  let nextId = 1;

  const urlFor = (wallet) =>
    wallet === null || wallet === undefined ? `${base}/` : `${base}/wallet/${encodeURIComponent(wallet)}`;

  async function post(body, opts) {
    const ctl = new AbortController();
    const timeout = setTimeout(() => ctl.abort(new NetworkError('request timed out')), opts.timeoutMs ?? 60000);
    const onAbort = () => ctl.abort(opts.signal.reason);
    if (opts.signal) opts.signal.addEventListener('abort', onAbort, { once: true });
    let resp;
    try {
      resp = await doFetch(urlFor(opts.wallet), {
        method: 'POST',
        credentials: 'same-origin',
        cache: 'no-store',
        headers: { 'Content-Type': 'application/json', ...cfg.auth.headers() },
        body: stringify(body),
        signal: ctl.signal,
      });
    } catch (e) {
      if (opts.signal?.aborted) throw e;
      const err = e instanceof NetworkError ? e : new NetworkError(`node unreachable: ${e?.message ?? e}`);
      cfg.onNetworkError?.(err);
      throw err;
    } finally {
      clearTimeout(timeout);
      opts.signal?.removeEventListener('abort', onAbort);
    }
    cfg.onReachable?.();
    if (resp.status === 401) {
      cfg.auth.onUnauthorized();
      throw new HttpError(401, 'login required');
    }
    if (resp.status === 403) throw new HttpError(403, 'not permitted for this user');
    const text = await resp.text();
    let json;
    try {
      json = parse(text);
    } catch {
      // The node answers some failures (e.g. 405, 503 during shutdown) with no JSON.
      throw new HttpError(resp.status, `HTTP ${resp.status}${text ? ': ' + text.slice(0, 200) : ''}`);
    }
    return json;
  }

  function unwrap(reply, method) {
    if (reply === null || typeof reply !== 'object') throw new RpcError(-32700, 'malformed reply', method);
    if (reply.error) {
      const err = new RpcError(reply.error.code ?? -1, reply.error.message ?? 'unknown error', method);
      if (err.code === RPC_IN_WARMUP) cfg.onWarmup?.(err.message);
      return err;
    }
    return reply.result;
  }

  return {
    /**
     * @param {string} method
     * @param {any[]} [params]
     * @param {CallOpts} [opts]
     */
    async call(method, params = [], opts = {}) {
      const id = nextId++;
      const reply = await post({ jsonrpc: '1.0', id, method, params }, opts);
      const r = unwrap(reply, method);
      if (r instanceof RpcError) throw r;
      return r;
    },

    /**
     * One POST with several calls. Results come back in input order; failed
     * calls are returned as RpcError values instead of throwing.
     * @param {Array<[string, any[]?]>} calls
     * @param {CallOpts} [opts]
     */
    async batch(calls, opts = {}) {
      if (calls.length === 0) return [];
      const first = nextId;
      nextId += calls.length;
      const body = calls.map(([method, params = []], k) => ({ jsonrpc: '1.0', id: first + k, method, params }));
      const reply = await post(body, opts);
      if (!Array.isArray(reply)) {
        // A whole-batch failure (e.g. a whitelist refusal) arrives as one object.
        const r = unwrap(reply, 'batch');
        const err = r instanceof RpcError ? r : new RpcError(-32700, 'batch reply is not an array', 'batch');
        return calls.map(() => err);
      }
      const byId = new Map(reply.map((r) => [r?.id, r]));
      return calls.map(([method], k) => {
        const r = byId.get(first + k);
        return r === undefined ? new RpcError(-32603, 'missing reply in batch', method) : unwrap(r, method);
      });
    },
  };
}

/** Human-readable text for any error the RPC layer throws. */
export function describeError(e) {
  if (e instanceof RpcError) return `${e.message} (code ${e.code})`;
  if (e instanceof HttpError || e instanceof NetworkError) return e.message;
  return String(e?.message ?? e);
}
