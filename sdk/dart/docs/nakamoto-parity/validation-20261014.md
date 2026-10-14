# Validation of the chain-explicit Dart API

Reference Frank revision: `8c9e38f46ee429826ff918df6eb79214a06af98c`.
Reference fixture SHA256:
`086184bcd10a34ec3445c301d2b859167a221ffce3580d74f1ff4d2c68cc4cf2`.
Source and dependency hashes are recorded alongside the fixture. Repeated
generation produced byte-identical fixture and provenance JSON. Frank was
read-only throughout.

Validation used macOS arm64, Dart 3.13.3, Flutter 3.47.4 and PointyCastle 4.0.0.
The SDK dependency update is `dba77f2e` (equivalent integration commit
`9b1c81bb`). The integration worktree combines the new API with Vase's updated
client/server dependency branch at `2b37c9ae`; no dependency overrides were used.

- Complete SDK suite: 128 tests pass, including 42 existing tests.
- New API/source, tests, descriptor generator and browser smoke analysis:
  no issues. Whole-SDK analysis: no errors; 398 inherited warnings/style items.
- All 16 network descriptor tables match their pinned generated source.
- Reference parity covers addresses, WIF and BIP32 on all 16 networks;
  eight wire transactions; 66 supported signature digests; 84 exact DER
  signatures; nine exact signed standard-input transactions; six base headers;
  Bitcoin/Lotus Merkle roots; three ECDH and four tweak cases.
- Official standards evidence: BIP143 example; all 19 BIP340 verification
  vectors and eight exact signing vectors, including variable-length messages.
- Dart-to-JavaScript compilation and actual Node execution pass. The smoke
  exercises all 16 networks, uint64 maximum-value round trips, and independent
  Bech32, BIP32 and BIP340 expected bytes.
- Updated Vase: all 73 Flutter tests pass; web build passes. Analyzer has no
  errors, with 528 inherited warnings/style items. No existing wallet API or UI
  was changed by the chain-explicit API work.

The new tests include malformed/truncated transactions, noncanonical CompactSize,
trailing data, unsupported capabilities, wrong-chain identifiers/encodings,
invalid scalars/public points, immutable descriptors and defensive byte copies.

No real transaction was broadcast, funded wallet opened, or live chain/network
state modified. Native Android/iOS builds, six-chain live spending, AuxPoW/MWEB
extensions, Script execution, advanced transaction signing and side-channel
assurance remain outside this validation. See the API support matrix for exact
unsupported capabilities.
