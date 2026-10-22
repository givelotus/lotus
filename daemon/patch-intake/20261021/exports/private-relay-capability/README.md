# MR06: negotiate private high-bandwidth relay explicitly

Source base: `a60bba6facc924cdf43c34dc881805bb114fe373` (521 stack).
Source worktree: `/Users/shammah/repos/lotus-v2-private-relay-capability`.
Branch: `repair/private-relay-capability-20261021`.
Current delivery identities and validation state: `delivery.json`.

## Problem and resulting behavior

Local `-highbandwidthtx=1` previously marked every transaction-relay peer private-capable during initialization/VERACK. Ordinary BIP152 high-bandwidth negotiation or NoBan also sufficed to push private `shorttx` bodies. Neither establishes that a remote peer understands those formats. A stock ABC peer could therefore receive a private block announcement instead of its ordinary block announcement, or an unsolicited body instead of INV.

This repair adds `TXRELAY_HIGH_BANDWIDTH = 1 << 2` to the **existing** `sendinvshort` version-1 feature word. Its precise meaning is: the sender accepts `sealedheader` block announcements and unsolicited `shorttx` transaction bodies. It does not imply either INVSHORT or continuous reconciliation. Existing unknown-bit masking remains unchanged.

Nodes offer that bit when `-highbandwidthtx` or `-txrelaypushhb` enables their local high-bandwidth mode. High-bandwidth support remains independent of `-txrelayshortids`. The regtest disable override suppresses the offer. Only an explicit remote bit intersecting the local offer marks the connection private-capable. Block-only peers never acquire it.

Both outgoing private paths require the negotiated bit. Sealed-header announcements additionally retain `-highbandwidthtx`; unsolicited bodies additionally retain `-txrelaypushhb`. Neither BIP152 nor NoBan substitutes for remote support. Stock and INVSHORT-only peers keep their ordinary INV/compact/header paths; an INVSHORT-only peer still gets short-id announcements. Removing the private bit in a subsequent offer revokes the capability. Initialization/finalization clears connection state.

No new message, service bit, alias, version fallback, migration, or compatibility shim was added. Root explicitly approved extending the existing feature word for this unreleased protocol. Full block acceptance and all consensus rules are unchanged.

## Source commits and tests

1. `0f38c6237e`: frozen negative-control test against unchanged 521 production. Real PeerManager plus real version/VERACK handshake, ordinary compact-capable stock peer, local high-bandwidth and push enabled. Twenty transactions must produce INV rather than SHORTTX; the peer must not be marked private-capable.
2. `758dcecb67`: production repair, mixed-peer negotiation tests, adapted body-push test, actual sealed-header path regression using real negotiation rather than manually inserting handler state.
3. `09efb790d0`: tests for local opt-out and independent operation with INVSHORT disabled; ensures the no-body default is checked even with successfully negotiated private support.

N1 owns the single incremental build and focused checks. Requested cases:

- `txrelay_tests/stock_peer_does_not_support_private_relay`
- `txrelay_tests/private_relay_requires_explicit_remote_offer`
- `txrelay_tests/private_relay_local_willingness_and_disabled_shortids`
- `txrelay_tests/no_body_push_by_default`
- `v2_protocol_handler_tests/high_bandwidth_sealedheader_push_and_peer_cleanup`

Until N1 supplies results, these are prepared tests, not passing claims. No standalone daemon-to-stock-ABC pair or broad functional suite has been run in this lane.

## Causal ownership / integration constraint

The original local-only sealed opt-in is in shared owner `42aa88cce2b0de0e20a4763d83ef1c61a873bca0` (push SealedHeader). The ordinary BIP152/NoBan body qualification is from `bed33d81cf` (coalesce outbound inventory), later gated by local `-txrelaypushhb` in `6e26776089`.

The existing capability exchange and feature header are introduced later in shared owner `56443331da6c8658581fd324a89dfcf4248610e7` (announce by 8-byte short ids). Fixup commits currently target this negotiation owner because the new bit and message branch cannot compile before it. Do not blindly squash the whole final diff into the earlier sealed owner. If all earlier intermediate trees must already enforce the new boundary, the integrator should stage the removal of local-only opt-in in the earlier owner and introduce the actual feature exchange at `56443331da`, preserving later source adaptations and tests. Native header adaptation changes must stay in their native owners. Canonical refs are untouched by this lane.

## Specification follow-up

Record the bit-2 semantics above with the `sendinvshort` feature table in the authoritative protocol specification. Receiving an ordinary `sendcmpct` is expressly insufficient. This delivery documents the decision; it does not edit the separate specification repository concurrently with its owner.
