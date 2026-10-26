# Read-only proposal: preserve legacy-bridge functional gates on native currency

No source changes or heavy jobs have run for this proposal. C5 source remains isolated in its existing frozen prototype.

## Corrected diagnosis

At endpoint8b55, MiniWallet adapts RPC denominations via `_currency=RpcCurrency.from_node(...)` but remains a legacy transaction wallet. It creates defaultversion1 CTransaction, signs legacy scriptSig and generates version2 coinbases. NativeMiniWallet is an explicit separate class. Both failing scripts import MiniWallet, not NativeMiniWallet. Therefore the atomic RPC failure is currently a wrong-denomination legacy ForkID signature, not a v7 witness overwritten in the endpoint fixture. Intermediate pure-native wallet history differs and must not be confused with endpoint source.

The unchanged admission test fails constructing its fee_rate6000 conflict before peer admission. In shared XEC units this rate means600000atoms/kB; in native XPI units it means6000000000atoms/kB and exceeds its split UTXO. The unchanged atomic RPC test reaches its manually signed legacy batch, but signs input amount `int(utxo["value"]*XEC)` using XEC=100 while the native RPC reports1e6atoms/unit. The signature's input amount is wrong by10000.

Both failures reproduce on frozen exactC4 daemon SHA256ef91a419a7b4c6422e9b0ed6a645851f37a66e69f5ba4fc5027b65c316a2ae2d. Detailed candidate/baseline logs and inputs remain in this intake. Neither result is a functionalPASS.

## Earliest causal native owner

`ce6426e759811b005a5cb01fdda143aa4e95d819`, native position3 after sharedfec2, first adds currency.py/RpcCurrency and changes inherited MiniWallet amount/fee/signing conversions from XEC constants to node metadata. It changes default fee_rate3000XEC to `_currency.from_atoms(300000)` while leaving the two explicit fixture rates6000 and atomic test's XEC amount unchanged. `git log -S '_currency_unit'` yields no match in this frozen native range; the actual identifier here is `_currency`. `git log -S 'RpcCurrency.from_node'` identifiesce6426 first and later473c9 for NativeMiniWallet compatibility.

Relevant later native owners: position34 `73e3b2b2e5891e5c64b4ac5bb7fbfebf6869a334` temporarily migrates MiniWallet itself to v7; position129 `bfcdfd880d77b7d5a536b6d6ca1551fe2d65778a` restores explicit legacy-default / separateNativeMiniWallet behavior; position133 `473c9acda185e0f4b17c7d561f15b52927c949dd` completes native denomination/chain fixtures. Proposed two-script denomination repair belongs atce6426, not C5 or these later owners. Shared source files stay unchanged on the shared branch; native fixup uses helper introduced by its same owner.

## Exact smallest proposed diff

`FIXTURE-DENOMINATION-PROPOSAL.diff` contains only:

- Import RpcCurrency into each script and instantiate it from its first node.
- Convert both admission conflict rates with `currency.from_atoms(600_000)`. This exactly preserves600000atoms/kB:6000 in XEC and0.6 in XPI; default remains300000atoms/kB, so conflict alternatives still have distinct higher fees. No dynamic clamp, amount increase or skip.
- Replace atomic test's `int(utxo["value"]*XEC)` with `currency.to_atoms(utxo["value"])`, remove now-unused XEC import. Keep legacy Schnorr signing, sighash flags and all raw transaction/sig mutation logic unchanged.

All original assertions/ordering/conflict races/low-fee rejection/invalid-signature disconnects/atomic package failure/no-publication/relay/template/mining checks remain byte-identical. This preserves bridge coverage, rather than replacing the scripts with native-only equivalents. No helper or production source change is proposed.

## Validation / integration isolation

After root approves mutation and grants a host slot, apply the proposed Python-only diff as a separately exported fixture patch, keep it out of C5feature commit. Run both scripts unchanged otherwise against frozen C4 and C5 candidate with separate temp dirs/ports and exact binary overrides. Source helper/scripts/config hashes and binary identities recorded. Require both full scriptsPASS on both; any later assertion failures are investigated, not removed or weakened. Root can stage/fixup the earlier owner and preserve/replay history with the mandatory recovery ledger; executor lane must not autosquash/rewrite native history itself.

No C++ rebuild is needed for fixture-only proof if source binaries remain exact recorded C4/C5 identities. After paired full functionalPASS, root decides whether to allow C5source commit on preserved8b55 with fixture repair delivered separately, then carries it onto repaired native ancestry.

## Complementary native functional coverage

Existing `feature_miniwallet_native.py` explicitly uses NativeMiniWallet; it covers actualversion7 wire roundtrip, node validation via testrawtxbatch, per-input BIP340 signature corruption, output binding, unequal inputs, mempool submission, block inclusion and restart/rescan. It runs without built-in wallet support. It is a useful additional native gate on C5, with C4 baseline comparison if needed. It does not replace the admission script's peer ordering/conflict/shutdown checks or the40transaction atomic package/relay tests; report native versus legacy-bridge results separately.

`lotus_v2_native_e2e.py` uses a separate custom node harness and built-in wallet signing aroundline482; current BUILD_WALLET=OFF makes it a less suitable replacement for this immediate gate. It has no submitrawtxbatch/testrawtxbatch bulk exercise. No rewrite of these native counterparts is proposed.
