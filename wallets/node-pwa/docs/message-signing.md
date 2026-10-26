# Message-signing ownership

`ChainAdaptor.signMessage` and `ChainAdaptor.verifyMessage` own scheme
selection from the authenticated connection's immutable `ChainConfig`.
They are an application interface, not new JSON-RPC methods. A caller cannot
supply arbitrary signing domains or executable scheme descriptions.
`DaemonWalletMessageProvider` uses the existing wallet `signmessage` RPC;
keys stay in that wallet. Unlock/relock belongs to the existing secure wallet
interaction, not to a browser key implementation.

The current Sign/Verify UI remains the implemented legacy P2PKH flow.
It now invokes the adapter/provider boundary after one-call discovery;
this does not change the current daemon's cryptography.

## Implemented legacy scheme

The adapter's `ecash-compact-ecdsa-v1` preserves existing Qt/daemon behavior:

1. Encode `eCash Signed Message:\n` and the exact message as UTF-8 strings,
   each prefixed with Bitcoin CompactSize byte length.
2. Double-SHA256 that serialization.
3. Use the daemon's recoverable compact ECDSA signature: 65 bytes, including
   the recovery/compression header, encoded as base64.
4. Recover the public key and compare its existing serialized-key PKHash
   destination with the supplied legacy P2PKH address.

Message whitespace, Unicode and line breaks are not trimmed or normalized
by the adapter. Verification preserves the existing RPC's false result for
a mismatch and its errors for malformed signatures or unsupported addresses.
There is no new message-domain RPC, no eCash format replacement and no
transaction-signature change. This compact ECDSA format is separate from
transaction Schnorr signatures.

The local digest oracle and compact-signature structure checks are not
presented as cryptographic ownership verification. The bundle currently has
no secp256k1 recovery/HASH160 verifier. Full verification uses the existing
node `verifymessage` RPC; adapter signing also checks the provider's returned
signature with it before reporting success. Private keys are never exported.

## Native Lotus messages: explicitly unsupported

`nativeMessageSigning` and `messageSigningCapabilities().native.supported`
remain false. A native request fails before invoking a signing provider.
The current native-tier daemon still exposes the legacy eCash message magic
and legacy PKHash-only RPCs. Calling it with another label does not implement
a native message scheme.

A possible future design under discussion is recoverable compact ECDSA for
an explicitly recognized native key-hash template, using exactly the public
key serialization committed by that template and a distinct chain-bound
Lotus message domain. The domain/preimage bytes, address template and key
encoding have not been approved or implemented here. No speculative magic
string, signing preimage, or native wire format is shipped by this work.

Enabling a future native capability requires all of the following:

- an implemented native address codec and recognized key-hash destination;
- an approved unambiguous chain-bound message preimage;
- adapter hashing and verification of its exact key/address commitment;
- a wallet provider capable of signing that precise scheme/digest while
  retaining custody; the existing legacy `signmessage` provider cannot be
  treated as a generic arbitrary-domain signer;
- independent vectors and full address/sign/verify/provider tests, including
  wrong-chain, wrong-key, malformed signature and unsupported-template cases.

Future provider integration can extend an existing operation where suitable;
this interface does not require a new RPC merely to select a signature format.
Until every layer exists, discovery and UI must continue reporting native
message signing as unsupported. Native transaction Schnorr rules remain
unchanged regardless of the eventual message-signature decision.
