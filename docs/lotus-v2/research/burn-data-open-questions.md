# Appendix: prunable burn data and historical receipts

Status: **open design questions, 2026-10-20; not a candidate consensus rule**.
The maintainer identified commitment-preserving pruning as an interesting
property and requested exploration of large paid data and possible script
references to burns. This appendix records that discussion. It does not request
rewriting block files, implement pruning, allocate a wire format/opcode/input
kind, select an activation, or change fees, burn distribution or conservation.
All choices remain provisional before and through testnet.

## Existing commitments and the missing distinction

Native transaction identities commit to indexed output leaves:

```
OutputLeaf(j) = H_output(Bytes(Output[j]))
OutputsRoot  = IndexedTreeRoot(OutputLeaf[0 .. output_count - 1])
```

Both TxID and TxHash commit OutputsRoot. Retaining a leaf hash and the necessary
indexed-tree context can preserve those commitments after deleting the leaf's
preimage. It does not preserve the original serialized transaction bytes or
revalidate the contents of an unknown output. In particular, an opaque existing
OutputLeaf does **not** reveal or independently prove `IS_BURN`, asset, amount,
serialized length or path structure. A peer cannot safely classify an arbitrary
opaque output as discardable merely because its hash fits the tree.

Under existing burn accounting, `IS_BURN` outputs are included in output totals
and excluded from the live UTXO map. Their value is permanently burned, not an
extra transaction fee or a future spendable balance. A zero-value commitment
still incurs applicable resource charges. Exclusion from UtxoRoot already avoids
live coin storage for burns; deleting historical payloads would address a
different cost. It would not create an additional spendable reserve or change
the effect of the original burn.

The current output format is bounded and carries branches/paths, not an
arbitrarily large inline data field. A branch hash can commit external data,
but a hash is neither publication of those bytes nor a guarantee of access.
Large inline burn payloads would need a separately reviewed format and resource
model, not just removal of an old size check.

**Source/spec boundary:** the earlier canonical P01/C05 text describes only
HAS_TOKEN/IS_BURN and no separate state field. The inspected implementation
(`b2c08f5c`, combined405, `src/lotus_v2/output.h/.cpp`) additionally defines
`HAS_STATE = 0x04`, a nonzero 32-byte `state_root` on non-burn outputs and a
844-byte output bound; it rejects HAS_STATE together with IS_BURN. That source
capability is relevant when comparing contract designs. This appendix neither
silently reconciles the older specification nor invents a state field on burns;
source/spec alignment is separate work.

## Hypothesis: keep a burn descriptor, prune its payload

A future commitment structure could expose a small authenticated descriptor
separately from a potentially large payload. The conceptual components are:

```
BurnDescriptor: format/type and burn classification,
                asset identity, burned value,
                payload byte length and payload hash/root,
                any explicitly required accounting fields
BurnOutputCommitment: domain-separated commitment to the descriptor
                      and the payload commitment
Payload: exact bytes, or a separately defined indexed chunk subtree
```

These are semantic fields, **not an encoding or allocated hash domain**. The
design must select canonical field widths/order, asset absence versus native
asset representation, zero/empty cases, version/type separation and exact
hash framing before it can be implemented. An output proof must bind the
output position/count and this typed descriptor to the native transaction's
OutputsRoot. Burn classification cannot be a detachable uncommitted flag.
If an enclosing output uses a descriptor hash, the descriptor still needs to
be disclosed and authenticated; merely making another opaque hash does not
solve classification or accounting.

The length and payload digest must describe exactly the bytes validators
process. A chunked alternative additionally needs canonical ordering/counts,
last-chunk length and a root that cannot equate distinct payload encodings.
Domain/type separation must prevent a payload leaf from being reinterpreted as
a descriptor, spendable output or another asset's receipt. Avoid duplicate
length/value fields with ambiguous authority. Bind all policy-relevant fields
through the transaction identities and signatures; do not accidentally make
an amount or payload declaration replaceable without changing the commitment.

The expected benefit is a validator retaining the small descriptor/proof while
dropping large data bytes after the validation and retention obligations that
need them are satisfied. A new receiver could authenticate the disclosed burn
classification and amount without storing the whole payload, under an explicit
historical/bootstrap verification policy. It still cannot infer that missing
payload bytes were downloaded, length-checked or correctly hashed by that
receiver. This is a smaller authenticated representation of an already committed
object, not a substitute for required fresh-block validation.

Descriptors expose the asset, burn value and length to readers who receive them;
this design does not promise value, asset or payload-length privacy. A hash
alone is not encryption and may reveal low-entropy content by guessing. Any
confidential accounting variant would require its own proof system and threat
model and is not proposed here.

## Paid data: validation cost is different from retention cost

Allowing developers to publish larger data could be useful when applications
want a chain-committed publication record. It is not free or physically
unbounded data availability. Newly connected blocks still require all existing
mandatory validation. A proposed payload format must permit incremental
length checking and hashing with bounded buffers, checked integer arithmetic,
explicit work limits and cancellation, while still consuming the declared data
before claiming its full validation. Charging wire bytes and hashing/validation
work is required under the applicable Cost Unit model; no fee constants or
burn shares are changed here. Token units cannot pay native resource charges
merely by being placed in a token burn output.

The complete original block size must include payload bytes and framing even
if a node later retains a compact representation. Pruned length is not the
original charged length. Re-encoding a compact representation must not silently
change the committed size, transaction identity or accounting result. Any
compressed transport needs bounded decompression and must specify which exact
canonical bytes are hashed and charged. Fees do not eliminate bandwidth,
latency, verification or denial-of-service limits: a design must still explain
how supported peers receive large objects without unbounded allocation,
queues, disk staging or starvation of live validation. N05/N06a's transport
and catch-up obligations remain applicable.

Download, streamed hashing, relay and temporary storage costs occur before
pruning; deleting retained payloads does not undo them. Disk savings depend on
what the node previously retained and on actual physical reclamation. A node
cannot promise both deletion of every payload copy and later serving the full
original raw block from local disk. Compact descriptor/proof responses and
full-body responses need distinguishable capabilities and availability status.
Applications needing arbitrary program/data bytes must arrange archives or
other availability sources; on-chain commitment alone does not make every
validator a permanent application-data server.

Retention must account for reorg, undo, recovery, optional historical execution,
indexer and archival obligations. A burn payload may be unnecessary for some
state rollback operations while still needed to serve or fully revalidate the
original body. The design must demonstrate that distinction rather than label
all payloads immediately disposable. No automatic block.dat rewriting is
requested or authorized by this discussion. Optional archive/backfill policy
must remain separate from consensus validity.

Commitment-preserving compact storage is specific to the chosen native identity
construction and retained proof material. It does not turn the modified bytes
into the original full-wire encoding. It also does not generalize automatically
to legacy or other-chain transaction IDs computed as a flat hash of complete
serialized bytes; those require their own authenticated representation/proof
and validation model. The native TxHash distinction does not change historical
legacy hashing rules.

## Can scripts refer to a burn?

A burned output is not a spendable UTXO, so it cannot simply become a consuming
input under the current rules. Calling a historical burn an “input” risks
accidentally resurrecting its value or counting the original amount twice.
Current C13 also forbids a read-only input kind. Three separate choices should
be evaluated without treating them as one feature:

| Choice | Potential benefit | Additional obligations |
| --- | --- | --- |
| Descriptor-only pruning | Authenticated burn classification/accounting with reduced payload retention | New commitment/representation design, streaming validation, historical provenance and retrieval semantics; no new script input |
| Script-readable historical receipt | A contract evaluates authenticated facts about an earlier burn/publication | Inclusion and chain-anchor verification, disclosure/availability rules and explicit proof/VM cost; no spendable value and no implicit once-only claim |
| Consumable receipt or nullifier | A protocol/application permits a particular historical event to authorize one state transition once | A separate substantial proposal for authorization, replay prevention, ownership, nullifier/state growth, rollback and accounting; not spending or refunding the burn |

For a readable receipt, a proof path might link the disclosed typed descriptor
and payload commitment through an indexed transaction output proof, TxID/TxHash
commitments and a block commitment to an admitted chain anchor. Exact proof
shape and anchoring remain open. A valid transaction-output inclusion proof
by itself does not establish canonical-chain membership, finality or historical
consensus validity. The chosen anchor must follow the node/application's
explicit snapshot, header and finalization trust rules; neither a supplied
root nor a majority of connected peers is sufficient.

A reference must identify chain, transaction, output position and application
purpose unambiguously. Reorg/finality handling, acceptable anchor age, replay
across forks/chains/contracts and duplicate claims need explicit policies.
Historical inclusion proves a past event, not current state, fresh external
data or continued payload availability. If a script needs content rather than
its commitment, the spender must supply the required bytes and prove their
hash/length, or use a separately reviewed selective-disclosure/chunk proof.
Bound proof bytes, processing, argument sizes and charged CU; do not smuggle a
large free payload through a receipt verifier.

The same readable receipt can normally be presented repeatedly. A once-only
claim requires a nullifier/consumed-receipt record or a contract state update
that prevents reuse. Defining that state raises persistent-growth, expiry,
reorg rollback and synchronization questions. Removing a nullifier too early
can reopen an old claim. Any resulting payout must come from an independently
authorized funded input or an explicitly reviewed issuance rule; it must not
credit the original burned value back into the consuming-input total. Existing
conservation and burn accounting stay intact.

Before adding read-only inputs or receipt opcodes, compare using existing
script proof primitives with an authenticated caller-supplied anchor, or a
spend-and-recreate contract coin committing application data and claimed-receipt
state in its branches or the implementation's HAS_STATE root. Those approaches
still need correct anchoring and replay policy, but may avoid a new input kind
or a global nullifier set. No current opcode is claimed to supply automatic
historical-chain authenticity, and no proposed reference silently overrides C13.

## Backwards verification and evaluation gates

Burn exclusion from live UtxoRoot does not make all historical transition data
unnecessary. Verifying a predecessor/successor transition still needs the
required authenticated old coin values, asset/policy fields, provenance and
spend/creation/expiry evidence until that verification is complete. It must also
account for the full StateRoot/monetary components. A retained burn descriptor
may help authenticate original output accounting; it cannot replace missing
spent coins, prove sweep completeness, establish script authorization, or
recover arbitrary historical payloads. N06a's root-checked versus fully
executed history distinction remains explicit.

Before promoting any choice, require independent vectors for descriptor/type,
length and asset/value binding; native identity preservation in the proposed
compact representation; rejection of opaque spendable-as-burn substitution;
streamed versus full hash equivalence and truncation/overflow handling; exact
wire/CU/size accounting; and physical retention/retrieval behavior across reorg
and restart. Script receipt alternatives additionally need adversarial anchor,
replay, duplicate-claim, nullifier rollback/growth and conservation tests. Measure
large-data download/hash/relay cost separately from saved disk capacity and
application availability. Compare the benefit against existing state/branch
commitments before adding new consensus machinery.

No new vectors, wire rules, fee parameters, pruning implementation or receipt
validation are claimed delivered by this appendix. The immediate result is a
recorded design space and its open proof, availability and accounting questions.
