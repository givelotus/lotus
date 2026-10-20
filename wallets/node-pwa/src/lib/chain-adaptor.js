// Connection-scoped adaptor: one authoritative discovery call, one immutable
// ChainConfig instance. No global cache shared by different nodes/sessions.
import { ChainConfig } from './chainconfig.js';
import { RpcError } from './rpc.js';

export class UnsupportedDiscoveryError extends Error {}

export class ChainAdaptor {
  constructor({ rpc, onIdentityChange = () => {} }) {
    this.rpc = rpc;
    this.onIdentityChange = onIdentityChange;
    this.epoch = 0;
    this.promise = null;
    this.config = null;
    this.previousIdentity = null;
  }
  invalidate() {
    ++this.epoch;
    this.promise = null;
    this.config = null;
  }
  discover() {
    if (this.promise) return this.promise;
    const epoch = this.epoch;
    this.promise = (async () => {
      let raw;
      try { raw = await this.rpc.call('getchainconfig'); }
      catch (error) {
        if (error instanceof RpcError && error.code === -32601) throw new UnsupportedDiscoveryError('This node does not support getchainconfig. Use a node build with chain discovery enabled.');
        throw error;
      }
      const config = new ChainConfig(raw);
      if (epoch !== this.epoch) throw new Error('Node discovery was invalidated while connecting.');
      const identity = `${config.chainIdentifier}|${config.network.genesis}|${config.network.chainid ?? ''}`;
      if (this.previousIdentity !== null && identity !== this.previousIdentity) this.onIdentityChange(config);
      this.previousIdentity = identity;
      this.config = config;
      return config;
    })();
    const pending = this.promise;
    pending.catch(() => { if (this.promise === pending) this.promise = null; });
    return pending;
  }
}
