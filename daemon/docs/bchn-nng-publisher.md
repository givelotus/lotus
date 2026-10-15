# Historical incompatible BCHN NNG publisher (superseded)

The earlier raw-payload publisher described here used a new wire format with no
existing compatible consumers. It did not fulfill the requested Lotus/Tobias
FlatBuffers/RPC port and must not be submitted or advertised as that port.

It is superseded by the independently maintained
[FlatBuffers compatibility candidate](bchn-nng-flatbuffers.md), which replaces
`daemon/patches/bchn/10-nng-interface.patch`. The old
`bchn-nng-publisher-evidence.json` is retained only as historical evidence of
that rejected implementation, not validation of the replacement.

The replacement remains local pending review; this documentation does not claim
MR2176 already contains it or that upstream CI has validated it.
