// Implemented scheme: the existing eCash/Qt compact ECDSA message format.
// This module never handles a private key or invents a native V2 domain.
import { sha256 } from './mining-hashes.js';

export const LEGACY_MESSAGE_SCHEME = Object.freeze({
  id: 'ecash-compact-ecdsa-v1',
  addressKind: 'legacy-p2pkh',
  domain: 'eCash Signed Message:\n',
  digest: 'sha256d',
  encoding: 'base64',
  signatureBytes: 65,
});
export const NATIVE_MESSAGE_CAPABILITY = Object.freeze({
  supported: false,
  reason: 'Native key-hash address encoding, a chain-bound message scheme and its signing provider are not implemented.',
});

function compactSize(length) {
  if (length < 253) return Uint8Array.of(length);
  if (length <= 0xffff) return Uint8Array.of(253, length & 255, length >>> 8);
  const out = new Uint8Array(5); out[0] = 254;
  new DataView(out.buffer).setUint32(1, length, true);
  return out;
}
export function legacyMessageDigest(message) {
  if (typeof message !== 'string') throw new TypeError('Message must be text.');
  const utf8 = new TextEncoder();
  const domain = utf8.encode(LEGACY_MESSAGE_SCHEME.domain);
  const body = utf8.encode(message);
  const prefix = compactSize(body.length);
  const encoded = new Uint8Array(1 + domain.length + prefix.length + body.length);
  encoded[0] = domain.length; encoded.set(domain, 1);
  encoded.set(prefix, domain.length + 1); encoded.set(body, domain.length + 1 + prefix.length);
  return sha256(sha256(encoded));
}

// Structure is checked locally; this is not public-key recovery or proof of
// ownership. Full cryptographic verification uses the existing node verifier.
export function validateCompactSignature(signature) {
  if (typeof signature !== 'string' || !/^[A-Za-z0-9+/]{87}=$/.test(signature)) throw new Error('Signing provider returned a malformed compact signature.');
  const decoded = Uint8Array.from(atob(signature), (c) => c.charCodeAt(0));
  if (decoded.length !== 65 || decoded[0] < 27 || decoded[0] > 34) throw new Error('Signing provider returned a malformed compact signature.');
  return decoded;
}

/** Existing daemon-wallet provider; no key extraction, signing-domain RPC or
 * browser cryptographic signer. Unlock/relock remains the secure wallet UX.
 */
export class DaemonWalletMessageProvider {
  constructor({ rpc, wallet }) {
    if (typeof wallet !== 'string') throw new TypeError('A selected wallet is required.');
    this.rpc = rpc; this.wallet = wallet;
  }
  async signMessage({ scheme, address, message }) {
    if (scheme !== LEGACY_MESSAGE_SCHEME.id) throw new Error('The daemon provider does not implement this message scheme.');
    return this.rpc.call('signmessage', [address, message], { wallet: this.wallet });
  }
}
