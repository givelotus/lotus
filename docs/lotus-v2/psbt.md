# Lotus V2 partially signed transactions

Status: provisional wallet interchange profile 1, subject to testnet revision.
This is an application format, not a consensus change or a threshold-signature
protocol. FROST and other multiparty signing protocols are outside its scope.
The authoritative specification lives with the Lotus V2 specifications in this
monorepo. Daemon copies under `doc/standards` are implementation mirrors.

## Relationship to Bitcoin PSBT

The container uses [BIP174](https://bips.dev/174/)'s magic `70736274ff`,
CompactSize key/value records, zero-terminated global/input/output maps,
proprietary keys, and creator/updater/signer/combiner/finalizer/extractor roles.
Unknown fields are preserved. Bitcoin PSBT and native Lotus PSBT are distinct
formats inside that container.

[BIP370](https://bips.dev/370/) assigns PSBT version 2 and reconstructs Bitcoin
transactions using required per-output Bitcoin amount/script fields. Lotus
outputs have unsigned amounts, optional asset/state commitments, branches and
paths; its transaction lock is 64 bits. Those fields cannot truthfully be
represented as Bitcoin outputs. This profile therefore uses its own explicit
version and native transaction template, not fabricated Bitcoin scriptPubKeys.
It reuses the count field encodings where their meaning is identical.

[BIP371](https://bips.dev/371/) carries Bitcoin Taproot signing metadata. Native
Lotus BIP340 signatures do not imply Bitcoin Taproot semantics: Lotus uses
its own leaf hashes, invocation selectors and sighash. Consequently BIP371's
Taproot signature and control-block fields are not reused.

Implementations MUST distinguish PSBT version from transaction version. Here
PSBT version is `0x4c560001` (four value bytes `0100564c`); transaction version
is 7. This locally assigned version is not a Bitcoin BIP registration. A
native document MUST NOT contain `PSBT_GLOBAL_UNSIGNED_TX` (`00`). Thus the
existing ABC PSBT parser, which requires that field, rejects it even though
that parser does not recognize `PSBT_GLOBAL_VERSION`. A dispatch layer MUST
inspect and validate the global map before selecting a parser; it MUST NOT
retry failed native parsing/signing as legacy PSBT. Legacy transaction PSBTs
retain their existing format and cannot spend native coins.

## Framing and limits

`CS(n)` is shortest-form Bitcoin CompactSize; `Bytes(b) = CS(len(b)) || b`.
Every integer below marked `u16`, `u32` or `u64` is little-endian. Hashes are
32 raw digest bytes, without display reversal. Keys are byte strings, beginning
with a minimally encoded CompactSize type. A map is repeated
`Bytes(key) || Bytes(value)` followed by one `00` separator.

Require exactly one global map, then the declared input maps and output maps,
with no trailing bytes. Duplicate complete keys reject even when values are
equal. Reject nonminimal lengths/types/proprietary subtypes, truncation,
incorrect field widths, unexpected keydata, and counts inconsistent with the
template. Serialize maps in unsigned lexicographic byte order of complete keys;
readers accept any map order. Preserve unknown keys and values byte-for-byte,
although record ordering may change.

Profile limits are 16,777,216 bytes per complete binary PSBT, 1,024 bytes per
key, 8,388,608 bytes per value, and 4,096 records per map. Check remaining bytes
and all size arithmetic before allocation. Base64 wrappers must enforce the
corresponding decoded limit. Native consensus/profile limits additionally
apply, including 1..256 inputs, 0..256 outputs, at most 16 witnesses per spend,
10,000 script bytes, 64 branch siblings, 65,535 arguments per witness, and
8,192 bytes per argument. An implementation may advertise stricter resource
limits; it MUST report rejection rather than silently discard data.

All global standard keys except `04`, `05`, `fb`, and `fc` reject in this
profile. All standard input/output keys except `fc` reject. This deliberately
avoids confusing legacy UTXOs, final scriptSigs, or Taproot data with native
fields. Unassigned standard types are not an extension mechanism for this
profile. Unknown proprietary identifiers are opaque and preserved. Within the
`lotus-v2` identifier, unknown subtypes below `0x80` reject; subtypes `0x80..` are
noncritical opaque metadata, preserved and never used to authorize signing.
A future critical semantic extension requires a new recognized subtype and
an explicit implementation update, or a new PSBT version.

## Exact field registry

A proprietary key is `fc || 08 || ASCII("lotus-v2") || CS(subtype) || keydata`.
The identifier's eight bytes are `6c6f7475732d7632`. Table type/subtype values are hexadecimal. Subtypes are independent
in each map. Unless specified, keydata is empty. `w` denotes a zero-based
witness position in the input's selected path, not a branch number; `a` is a
zero-based argument position. `slot = w:u16 || a:u16`.

| Map | Key/type or subtype | Name | Value |
| --- | --- | --- | --- |
| Global | standard `fb` | VERSION, required | `0100564c` |
| Global | standard `04` | INPUT_COUNT, required | `CS(input_count)` |
| Global | standard `05` | OUTPUT_COUNT, required | `CS(output_count)` |
| Global | proprietary `01` | CHAIN_ID, required | ChainID, exactly 32 bytes |
| Global | proprietary `02` | TX_TEMPLATE, required | Canonical full v7 transaction wire, with every witness argument vector empty |
| Global | proprietary `03` | UTXO_ROOT, optional | 32-byte proposed authentication root; never self-authenticating |
| Input | proprietary `01` | COIN, optional while incomplete; required to sign/finalize | Full canonical Coin-v2 bytes, including outpoint and all metadata |
| Input | proprietary `02`, keydata `w:u16` | ARGUMENTS | `CS(count) || Bytes(arg[0]) || ...`; signature slots contain empty bytes |
| Input | proprietary `03`, keydata `slot` | SIGN_REQUEST | `scheme:u8 || mode:u8 || public_key` |
| Input | proprietary `04`, keydata `slot` | PARTIAL_SIG | Signature bytes to insert at the requested slot |
| Input | proprietary `05`, keydata `w:u16` | FINAL_ARGUMENTS | Complete argument vector, same encoding as ARGUMENTS |
| Input | proprietary `06` | COIN_PROOF | `bitmap:32 || CS(sibling_count) || sibling:32*` |
| Input | proprietary `07`, keydata `public_key:33` | KEY_ORIGIN | `fingerprint:4 || child_index:u32*`, at most 255 child indices |
| Output | proprietary `01`, keydata `public_key:33` | KEY_ORIGIN | Same origin encoding; a change hint, not a proof of change |

`KEY_ORIGIN` public keys use valid compressed secp256k1 SEC encoding. For native
BIP340 signing derive the indicated key and compare its x-coordinate with the
32-byte request key, applying BIP340 scalar normalization. Fingerprints and
paths are untrusted hints, not authority to derive or sign arbitrary keys.
A signer MUST reconstruct and compare the entire output policy using its own
wallet descriptor/program and derive the recipient/change identification
independently. No address text or key-origin record replaces an output policy.
Unknown metadata has no effect on that comparison.

`scheme=0` is native BIP340: key length 32; mode 0, 1 or 2. `scheme=1` is
legacy bridge ECDSA and `scheme=2` is legacy bridge Schnorr: key length 33 or
65, valid SEC encoding; mode 0, 1 or 2. Other schemes/modes reject. Schemes
1/2 are valid only for a resolved legacy P2SH coin. Scheme 0 applies to native
coins and the existing legacy P2PKH bridge: for that bridge, the template
witness script and siblings are empty, path/witness position is zero, the
argument vector is exactly `[empty_signature_slot, compressed_SEC_pubkey]`,
and the request key is that SEC key's 32-byte x-coordinate. Verify the full
compressed key hashes to the legacy P2PKH coin before signing. No other
legacy script is authorized by scheme 0. An implementation may support only scheme 0, but MUST reject signing
or finalization requests for unsupported schemes, never reinterpret them.

The template MUST round-trip exactly through the native v7 codec, including
its 16-byte prefix (`version:u32`, `lock:u64`, counts `u16,u16`). Every input
must have spend flags `01`; coinbase `02` and mint `03` reject in profile 1.
Token transfers without mint inputs are representable; minting requires a
future profile with authenticated accounting/delta rules. The transaction's
scripts, membership proofs, path indices, outpoints, sequences, lock, output
order and all output bytes are fixed by the template. The zero-argument full
serialization is intentional; it is not `EncodeInputCore` bytes substituted
into the full-wire grammar. Outputs require no duplicate per-output record.

`ARGUMENTS` and `FINAL_ARGUMENTS` keydata must name existing witness positions.
An incomplete creator may omit argument vectors, requests and coins. A signing
request requires ARGUMENTS for that witness, an in-range argument index, and
an empty argument at that slot. PARTIAL_SIG requires the matching request;
there is only one request/key per slot. Before any signing or finalization,
every witness must have ARGUMENTS (including an explicit zero count when
appropriate), and every input must have COIN. All non-signature arguments
must already be fixed. Importers must not guess which arbitrary arguments
are signatures; a raw transaction converter either receives explicit slot
metadata or rejects nonempty witness arguments. It may convert a transaction
whose argument vectors are all empty into an incomplete document.

## Coin authentication and signing

COIN is precisely `EncodeCoin`/`DecodeCoinBytes` from `sparse_state`:

```
prev_txid:32 || prev_index:u32 || Bytes(CoinOutput)
|| creation_height:u64 || creation_parent_mtp:u64 || coinbase:u8
|| encoding_version:u8 (=2) || fee_per_output:u64 || expiration_height:u64
```

Its maximum is 10,085 bytes and the metadata suffix is 34 bytes. The last
17 bytes are the version and fee/expiry provenance extension. Native
CoinOutput uses the canonical native output codec; a legacy CoinOutput is
`80 || value:u64 || Bytes(scriptPubKey)`. Burn coins reject. Require exact
canonical round-trip and embedded outpoint equality with the template input.
Never replace absent provenance with fabricated zero metadata.

COIN_PROOF supplies a Present `CoinProof` for that COIN: use the input outpoint
as query, that exact coin as leaf, bitmap bit d for depth d, and siblings in
deepest-first order. Require sibling_count = popcount(bitmap), at most 256,
and exact consumption, then run the existing sparse-tree proof verifier.
UTXO_ROOT must exist if any proof exists. Neither a correct proof to an
attacker-selected root nor a parent transaction alone authenticates the full
coin metadata or current unspent status. A signer MUST obtain the trusted
chain identity and full coin records or UTXO root independently, through its
own validated chainstate, previously verified header/state commitments, or an
explicitly provisioned trusted snapshot. It must compare the supplied root
and coin bytes with that trusted source. A PSBT flag asserting authenticity
is not permitted. A transport-only updater can retain unauthenticated data,
but must not report it as signing-ready.

A verified inclusion proof authenticates a coin at its trusted root, not
its unspent status forever. Expiry, maturity, locks and current availability
must be checked against independently obtained validation context. The
transaction signatures commit CoinOutput via CoinsRoot/OwnInputHash, not
creation height, parent MTP, coinbase or fee/expiry metadata. Never claim
those metadata are signature-bound. This distinction is why full Coin and
its authentication are separate from the sighash coin encoding.

Before signing, verify ChainID against the selected local chain, authenticate
ALL input coins, validate each selected path and script/proof membership,
resolve witness position to the actual branch index, and apply ordinary
non-signature transaction rules. Compute totals separately per asset with
checked u128 arithmetic; native fee is native input total minus native output
total, not a token-unit sum. Present recipient amounts, burns, fees, locks,
change and requested signing scope. Validate the signing key's role against
a policy the signer actually understands; a SIGN_REQUEST alone is not
permission to sign arbitrary bytecode or an arbitrary externally supplied
digest. Unsupported script policy must fail closed in automated signing.

Use the existing `PrepareSigningContextChecked` and `SigningMessage` with
resolved CoinOutput values, the template's fixed scripts/proofs, actual input
and witness positions, and no mint delta. Mode 0 commits TxID and CoinsRoot;
mode 1 commits own input/coin and every output; mode 2 commits own input/coin
and the output at the same input index. Modes 1/2 also bind version and lock;
all bind ChainID and the invocation selector. Mode 2 requires that output to
exist. Partial modes require explicit wallet/user policy authorization and
must not be described as approving other inputs or the complete fee.

Native mode 0 signatures are exactly 64 bytes; modes 1/2 are 64 BIP340 bytes
followed by the one-byte mode. A 65-byte signature ending in `00` rejects.
Legacy P2PKH bridge signatures use this same BIP340 form. Legacy P2SH
bridge signatures use the existing bridge checker and selector,
including the legacy coin script/redeem-script binding; appended hash types
are exactly `41`, `c1`, `c3` for modes 0, 1, 2 respectively. Legacy P2SH Schnorr
is not BIP340. Never sign a v7 bridge input with the legacy transaction digest
routine. P2SH redeem scripts remain in the native witness's fixed script/core,
not substituted after a signature has been collected.

## Combination, finalization and extraction

A combiner requires equal VERSION, ChainID, and byte-identical TX_TEMPLATE;
TxID equality alone is insufficient. Missing metadata may be added, but any
same complete key with different value is a conflict, including unknown
proprietary fields. Equal repeated keys across documents coalesce; duplicate
keys within one document already reject. Validate the combined result again.
COIN, existing argument vectors, requests, origins and roots are not replaced.
No joining inputs, reordering outputs or changing core fields after signing
is defined. Mode 1/2 signatures could authorize other transactions at the
consensus layer; importing them into a changed template requires a new
reviewed signing workflow, not a permissive combiner.

A finalizer verifies every supplied partial signature against its requested
key, scheme, mode and freshly computed invocation digest before inserting it.
It copies ARGUMENTS, replaces only declared signature slots, and requires
all requested signatures. No argument, request, or core field is inferred
from a signature's length. Each FINAL_ARGUMENTS must exactly equal this
construction; non-signature bytes cannot change. If already present it must
match, otherwise reject. Preserve ARGUMENTS, requests, signatures, coins,
proofs and unknown fields even after finalization, so independent extractors
can verify the result. This intentionally differs from PSBT cleanup of
fields that Bitcoin finalizers no longer need.

A final marker is not proof of validity. A native finalizer/extractor must
reconstruct the full transaction, verify all signatures and execute all
required branches through the consensus-equivalent ordinary validation
path, with authenticated coins and applicable chain context. Missing data,
unsupported policies/schemes, stale or unavailable required context,
script failure, fee/accounting failure, missing signatures, and mismatched
final vectors cannot be reported as complete. Parsing and combining may
succeed for incomplete documents; extraction may not. Native no-signature
programs can finalize if their explicit arguments satisfy full validation.

Only arguments differ between template and extracted transaction. Recompute
and require unchanged TxID. Recompute TxHash from the final full wire; it
normally changes when arguments are filled. Recheck current node acceptance
before broadcast; successful offline extraction never guarantees future
mempool or block acceptance.

## Implementation and evidence boundary

The source audit for this profile uses combined405 (`b2c08f5c`, tree
`6913271`) native transaction/signing/output/sparse-state code and legacy
`src/script/bridge_checker.*` plus `CScriptCheck::CheckLegacyBridgeInput`. Existing ABC `src/psbt.*` only provides legacy
PSBT processing. This specification does not assert native RPC support exists.
Use a separate native container/dispatch path and reuse shared map framing
and the established consensus codecs, rather than routing native signatures
through `ProduceSignature` or `final_script_sig`.

The independent framing/schema fixtures are in
`examples/psbt-profile-vectors.json`, checked by
`tools/psbt_profile_checks.py`. They exercise container/schema rejection and
round-trip preservation; they do not establish cryptographic signature,
UTXO proof or VM correctness. Implementation tests must additionally exercise
a genuine native standard-program coin, mixed native/legacy bridge inputs,
authenticated coin substitution, wrong ChainID, altered core/proofs, all three
modes, per-slot signature conflicts, unknown metadata preservation, final
argument tampering, and full extraction/validation. Coinbase/mint rejection
is required; legacy wrapped unsatisfiable mining outputs are not valid
native signing fixtures.
