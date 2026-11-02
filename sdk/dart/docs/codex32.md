# Codex32 and Frank recovery shares

The SDK exposes the BIP93 ms1 Codex32 format and Frank's typed fr1
recovery-share format through package:lotus_dart/codex32.dart. The implementation
adapts two MIT-licensed Frank packages:

- Codex32 core: packages/codex32/src/index.ts at commit
  6335eba26e415f64f9cdac7fcd89a02f924bebdb on
  crypto-primitives-foundation.
- Typed recovery envelope: packages/account-recovery/src/frank-shares.ts at
  commit 971f43a3.

The ms1 and fr1 formats are distinct; do not infer one from the other's length
or reinterpret its checksum.

BIP93 parsing validates the standard checksum and supported master-seed lengths.
The decoder discards residual payload bits as specified by BIP93. Share splitting
and recovery use GF(32) polynomial interpolation. The typed fr1 envelope adds
a version, secret type and length, threshold, identifier, share index, and a
domain-separated validation digest before splitting. Recovery rejects mismatched
headers, repeated indices, incomplete sets, invalid checksums, and inconsistent
shares.

Vase uses typed shares for two secret kinds:

- A Frank root is 32 bytes and derives payment keys through the Frank-specific
  domain-separated derivation.
- A historical BIP39 wallet is backed up as the 64-byte BIP39-derived BIP32
  seed. Its optional passphrase is already included. Shares preserve the wallet's
  keys but cannot reconstruct the original mnemonic or passphrase.

Random.secure supplies production randomness. The splitter requires an
explicit random-byte source, allowing deterministic test fixtures without a
fallback PRNG. Fixture tests cover Frank parity and malformed/incomplete inputs.
