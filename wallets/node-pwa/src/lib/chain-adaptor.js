// Connection-scoped adaptor: one authoritative discovery call, one immutable
// ChainConfig instance. No global cache shared by different nodes/sessions.
import { ChainConfig } from './chainconfig.js';
import { RpcError } from './rpc.js';
import { LEGACY_MESSAGE_SCHEME, NATIVE_MESSAGE_CAPABILITY, validateCompactSignature } from './message-signing.js';

export class UnsupportedDiscoveryError extends Error {}
export class ConnectionInvalidatedError extends Error {}

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
  async messageSigningCapabilities() {
    const config = await this.discover();
    return Object.freeze({ legacy: Object.freeze({ supported: config.features.messageSigning === 'legacy-p2pkh', scheme: LEGACY_MESSAGE_SCHEME }), native: NATIVE_MESSAGE_CAPABILITY });
  }
  async signMessage({ address, message, walletProvider, addressKind = 'legacy-p2pkh' }) {
    const capabilities = await this.messageSigningCapabilities();
    if (addressKind !== 'legacy-p2pkh' || !capabilities.legacy.supported) throw new Error(NATIVE_MESSAGE_CAPABILITY.reason);
    if (typeof address !== 'string' || typeof message !== 'string' || !walletProvider || typeof walletProvider.signMessage !== 'function') throw new TypeError('Address, exact message text and a wallet signing provider are required.');
    const epoch = this.epoch;
    const signature = await walletProvider.signMessage({ scheme: LEGACY_MESSAGE_SCHEME.id, address, message });
    if (epoch !== this.epoch) throw new Error('Message signing was invalidated by a connection change.');
    validateCompactSignature(signature);
    // Full recovery verification is delegated to the existing node RPC. The
    // local structure check is never presented as cryptographic verification.
    if (!await this.verifyMessage({ address, message, signature, addressKind })) throw new Error('Signing provider returned a signature that does not verify.');
    return signature;
  }
  async verifyMessage({ address, signature, message, addressKind = 'legacy-p2pkh' }) {
    const capabilities = await this.messageSigningCapabilities();
    if (addressKind !== 'legacy-p2pkh' || !capabilities.legacy.supported) throw new Error(NATIVE_MESSAGE_CAPABILITY.reason);
    if (typeof address !== 'string' || typeof signature !== 'string' || typeof message !== 'string') throw new TypeError('Address, signature and exact message text are required.');
    // Preserve the existing verifier's malformed-signature/address errors and
    // false/mismatch result rather than replacing them with a new wire format.
    const epoch = this.epoch;
    const valid = await this.rpc.call('verifymessage', [address, signature, message]);
    if (epoch !== this.epoch) throw new Error('Message verification was invalidated by a connection change.');
    return valid;
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
      let config;
      try { config = new ChainConfig(raw); }
      catch (error) { throw new UnsupportedDiscoveryError(`Node discovery is unsupported or invalid: ${error.message}`); }
      if (epoch !== this.epoch) throw new ConnectionInvalidatedError('Node discovery was invalidated while connecting.');
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
