# TCP session review before runtime integration

Review date: 2026-10-15. Inspected monorepo `0aa04844` and native
`74ac986ec`; the later accepted-cost diagnostics do not alter networking.
This records review of the proposed N01–N06 contract. It does not adopt the
candidate magic, consensus/genesis profile, or authorize a listening node.

## Packet authorized for isolated implementation

Implement a parameterized, socket-free version codec and session state machine.
Reuse the reviewed envelope and hello codecs. Advertise services zero; explicit
profile arguments and injected time/nonce checks make unit tests independent of
network allocations. The session must not dispatch through legacy ABC
`ProcessMessage`, which sends verack and initializes relay before V2 identity
checks. Root integrates the packet after independent review and tests.

### Inherited version compatibility

The ABC version parser at `src/net_processing.cpp:4952–5057` requires a 46-byte
prefix: i32 version, u64 services, i64 time, and receiver address (u64 services,
16 address bytes, big-endian u16 port). Ordinary integers are little-endian.
Optional suffix groups, parsed when bytes remain, are sender address plus u64
nonce (34 bytes), shortest-CompactSize user agent (at most 256 bytes), i32
starting height, one relay byte, then u64 entropy. Partial groups reject.
Defaults are nonce/entropy 1, height -1, relay true, empty user agent; negative
time becomes zero. Any nonzero relay byte is true. Bounded trailing bytes after
entropy are ignored as upstream does. Thus 352 bytes bounds a complete emitted
modern version, not every compatible received payload; the existing 2 MiB
pre-handshake envelope bound still applies.

Raise the accepted minimum to 70017 as proposed. Ignore duplicate version
without reparsing or changing peer state. Ignore established duplicate verack.
Duplicate hello closes. Check self-connection against outstanding outbound local
nonces, including the inherited default nonce 1 when the sender group is omitted
(`net_processing.cpp:5034`, `net.cpp:399`). This is a collision/self-connection
heuristic, not authenticated peer identity. User-agent bytes are
untrusted and must be sanitized before diagnostic display.

The integrated V2 envelope codec requires empty `verack` and `sendaddrv2`
payloads. This is an explicit stricter control-message rule: ABC handlers ignore
payload bytes for these commands. Session tests must retain that distinction;
only the version optional suffix behavior above claims inherited compatibility.

### Session ordering and resource limits

Send version first, hello after accepted version, and verack after accepted
hello. Activate only after both hellos and both veracks. Reject premature
application data and verack. Optional sendaddrv2 follows version but starts no
address relay. Use a fixed monotonic handshake deadline; duplicate traffic never
extends it. Inject time, randomness and nonce lookup rather than consulting
wall-clock/network globals inside the state machine.

Compute negotiated capacity on hello, but switch the decoder only at activation
between messages. For coalesced reads, switch before decoding the application
frame after the final handshake message. Test advertised limits 1, 117 and 118;
handshake framing uses its independent cap until activation. Bound generated
outbound actions and prohibit renegotiation without reconnecting.

## Runtime dependencies still open

- Services remain zero until a V2 body-availability interface proves and serves
  validated history. Inherited NODE_NETWORK_LIMITED initialization and pruning
  flags do not prove that availability. Decide whether a future limited service
  means the inherited 288 blocks; that count is not two days at 120-second spacing.
- Add explicit exact-body retrieval, full-TxHash transaction lookup, common
  complete-block admission, and bounded download scheduling interfaces. Current
  chainstate admission and atomic undo alone do not implement synchronization or
  best-chain selection.
- Bound compact reconstruction and tombstone counts per peer and globally. Once
  a missing request is issued, retain its peer/BlockID guard until disconnect;
  blocktxn has no request nonce. Release heavy buffers on cancellation but never
  evict a guard and reissue on that connection. At quota refuse or rotate the
  connection. Capacity or reconstruction failures are not consensus invalidity.
- Keep Bloom, filters, Avalanche, snapshots and package/mempool handlers disabled.
  Initial explicit peers cannot inherit automatic outbound service requirements
  that reject services-zero test peers.
- Profile adoption, socket binding, full/compact synchronization, signed relay,
  restart and reorg tests remain separate gates. QUIC remains milestone two.

This review is source inspection, not runtime evidence. The proposed profile's
successful offline acceptance and compiler payment pilot do not prove peer
synchronization. See [peering milestones](lotus-v2-peering-milestones.md).
