# Lotus V2 consolidation ownership and dependency ledger

Status: **review candidate; ownership complete; construction and bisectability
unproved**. This is a docs/data design artifact from monorepo
`9ab0c7c783de2fbc881fe9e90ae34c74ed5262f7`. No patches, source, active manifest,
nodes or published assets were changed. No builds or test binaries were run.
The current heavy-work window remains with the quorum owner.

The [machine-readable ledger](lotus-v2-consolidation-ledger.json) maps all **318
mailboxes, 000–317**, to **51 proposed topic commits**. It records 1,051 original
file diffs as 1,053 exclusive ownership units: almost all are complete file
diffs; the three hunks of patch178's `block_transition.cpp` are individually
assigned because template preview and complete-block validation are different
features. Every original mailbox appears once in the source inventory. A mailbox
may contribute different files to different topics; this is an explicit split,
not duplicate application.

The immutable replay reference is
[v2-series-replay-317.json](../../daemon/docs/evidence/v2-series-replay-317.json),
base `1fb7db17c176cdea8a2c60d887891589382ee4e3`, expected final tree
`a14a946342d31ee07ee8851906500746800b0c46`. Original intermediate trees identify
the source material; they are **not** expected trees for reordered topics. New
boundary trees remain null until independently constructed and replayed. Native
follow-ups absent from maintained000–317 are excluded even if a newer live
checkout contains them. Extending this scope requires a new source pin, complete
manifest/evidence hashes, ownership coverage and final-tree target.

## Why 51, and what remains unresolved

The requested end state is self-contained, bisectable topic commits with their
tests and build integration. The count follows those boundaries, not a fixed
58-commit target. Build-only and late repair mailboxes are folded into the feature
whose behavior they complete. No prototype, audit artifact, test or binary
fixture is deleted. The prior [consensus/consolidation review](lotus-v2-argon-consensus-and-consolidation-review.md)
explains why cost/VM semantic changes do not belong in this operation.

A first split produced 54 topics. Source inspection found that the proposed
schema3 model/query/store/service boundaries were not self-contained:
patch278 registers the model/query modules and changes store signatures used by
patch280/281 consumers. Those four subdivisions are now one complete `explorer`
topic, giving 51. It is large; a future finer split needs an explicit API/hunk
plan and passing intermediate Rust/bridge tests before increasing the count.

The proposed semantic dependency graph is acyclic. This does **not** mean the
original mailboxes can be applied in that order. Their exact shared-file context
graph contains **17 backward edges and three strongly connected components**.
The full edges and affected ownership-unit IDs are recorded under `unresolved`.
They identify rebase/context work, not proven semantic dependency cycles. No
claim of clean replay, successful compilation or bisectability is made.

## Proposed topics and prerequisites

This is the proposed topological order. Numbers in “Source mailboxes” mean that
the topic owns at least one explicit unit of that mailbox. Consult the JSON for
exclusive file/hunk ownership; never apply the same complete mailbox in each row
where its number appears. Prerequisites are topic IDs, reviewed as a proposed API
dependency map rather than derived from incidental line order.

| Order / topic ID | Proposed commit subject | Source mailboxes | Prerequisites |
| --- | --- | --- | --- |
| 1. `inherited` | Adapt inherited node policy, mining, consensus fixtures and identity | 000–006, 173, 253, 255–257, 260, 310 | ABC base |
| 2. `header` | Introduce V2 header primitives and parser boundary | 007, 042 | `inherited` |
| 3. `codec` | Introduce bounded output/transaction codecs and commitments | 008–009, 011–012, 015–016 | `header` |
| 4. `state` | Introduce compact sparse state and incremental UTXO tree | 010, 018–019 | `codec` |
| 5. `signing` | Introduce signing identities, BIP340 and prepared signing | 013–014, 017, 061, 109 | `codec` |
| 6. `vm` | Introduce VM, static costs, prepared ownership and differential corpus | 020–027, 030–031, 033, 035, 060–062, 064–067, 110, 313 | `signing`, `state` |
| 7. `ordinary` | Introduce ordinary transaction validation and storage lookup contract | 028, 032, 035, 061, 070, 072, 110 | `vm`, `state` |
| 8. `monetary` | Introduce absolute monetary anchors and development genesis/template | 029, 036–038, 050, 068, 178, 180 | `ordinary`, `header` |
| 9. `header_context` | Introduce contextual ASERT/header history validation | 055, 057–059 | `header` |
| 10. `oracle` | Retain ordinary-block oracle and persistent prototype/seal coverage | 034, 039–041, 043–049, 051–054, 056, 063, 110, 178 | `monetary`, `header_context` |
| 11. `block` | Introduce framed block accounting and abortable complete transition | 069, 071, 073–074, 178–179 | `oracle`, `ordinary`, `header_context` |
| 12. `disk` | Introduce atomic LevelDB state, authenticated undo and clock admission | 075–077, 080–086, 110 | `block` |
| 13. `sqlite` | Select SQLite-only inherited wallet storage | 078–079 | `inherited` |
| 14. `peer_codec` | Introduce bounded V2 transport and compact block codecs | 087–091, 110 | `block`, `signing` |
| 15. `genesis` | Initialize exact development profiles and guard genesis/undo | 092–101, 178, 317 | `disk` |
| 16. `offline` | Introduce manifest-driven offline node command and home helpers | 102–103, 112, 140, 146, 178 | `genesis` |
| 17. `session_body` | Introduce peer sessions and authenticated retained-body serving | 104–108, 110 | `peer_codec`, `disk` |
| 18. `index` | Introduce active header index and bounded header admission | 111, 113–114 | `genesis`, `session_body` |
| 19. `download` | Introduce bounded socket-free block downloads | 115–116, 132 | `index`, `session_body` |
| 20. `wallet` | Introduce encrypted V2 payment wallet and outgoing recovery | 117–118, 167, 182, 254, 316 | `sqlite`, `monetary`, `signing` |
| 21. `recovery` | Introduce bounded reorg recovery and source restoration | 119–125, 249, 317 | `disk`, `index`, `oracle` |
| 22. `transport` | Introduce nonblocking peer transport | 126–127 | `session_body` |
| 23. `typed` | Introduce typed operational/consensus failure evidence and consumers | 128–131 | `block`, `offline`, `wallet`, `recovery` |
| 24. `candidates` | Introduce durable candidate inventory, selection and receipts | 133–137 | `recovery`, `typed` |
| 25. `body_pool` | Introduce bounded volatile candidate bodies | 138–139 | `candidates`, `download` |
| 26. `tcp` | Introduce explicit POSIX TCP streams and loopback checks | 141–142 | `transport` |
| 27. `runtime` | Introduce bounded candidate/recovery runtime | 143–145, 147, 188, 317 | `candidates`, `body_pool`, `genesis`, `typed` |
| 28. `dispatcher` | Introduce runtime peer dispatcher and explicit clock interface | 148–151, 159–160, 249, 311 | `runtime`, `download`, `tcp` |
| 29. `preview` | Introduce abort-only block template preview | 152–154, 178, 250 | `disk`, `typed` |
| 30. `assembler` | Introduce signed block assembly and runtime facade | 155–156, 161–162, 251 | `preview`, `runtime`, `dispatcher` |
| 31. `provider` | Introduce authenticated native wallet provider | 165–166, 169–170, 182, 316 | `wallet`, `index`, `typed` |
| 32. `node` | Introduce development node TCP, mining and wallet context command | 157–158, 163–164, 168 | `assembler`, `dispatcher`, `offline`, `provider` |
| 33. `client` | Introduce private-FD wallet client with restored descriptor flags | 171–172, 315 | `provider`, `offline` |
| 34. `pool` | Introduce bounded transaction pool and resumable reconciliation | 174–175, 184, 314 | `runtime`, `ordinary` |
| 35. `relay` | Introduce negotiated transaction relay, bounded queue and FIFO inventories | 176–177, 181, 252, 309 | `pool`, `dispatcher`, `transport` |
| 36. `history` | Introduce durable transaction history and pool coordination | 185–187, 192 | `pool`, `relay`, `runtime` |
| 37. `wallet_submit` | Introduce wallet submission and verified transaction receipts | 182–183 | `provider`, `client`, `history` |
| 38. `node_tx` | Integrate node transaction pool, relay and bounded pool mining | 189–191 | `node`, `history`, `relay`, `wallet_submit` |
| 39. `chronik_query` | Introduce Rust lossless V2 output/query kernel and native build consistency | 193–196, 218, 248, 258 | `codec`, `inherited` |
| 40. `avalanche_core` | Introduce native Avalanche proof, quorum, polling and durable policy decisions | 197–212, 215–217, 235, 243, 259, 261, 301, 308 | `runtime`, `assembler`, `monetary` |
| 41. `chronik_db` | Introduce bounded durable V2 branch index with undo | 213–214 | `chronik_query` |
| 42. `chronik_service` | Introduce bounded native Chronik service and bridge | 219–220, 229 | `chronik_db` |
| 43. `peer_store` | Introduce durable bounded public Avalanche peer storage | 221–226 | `avalanche_core` |
| 44. `chronik_http` | Introduce opt-in confirmed HTTP and fenced lifecycle authority | 227–228, 234, 238–239 | `chronik_service` |
| 45. `avalanche_peer` | Introduce negotiated Avalanche wire adapter and preserved application frames | 230–233, 307–308, 312 | `avalanche_core`, `relay`, `dispatcher` |
| 46. `chronik_sync` | Integrate bounded authoritative native Chronik catchup | 236–237, 240–242 | `chronik_http`, `node_tx`, `index` |
| 47. `avalanche_driver` | Introduce single-owner Avalanche driver, status and peer fault policy | 244–247, 259, 304–305, 307–308 | `avalanche_peer`, `peer_store`, `avalanche_core` |
| 48. `avalanche_node` | Integrate Avalanche node/provisioning/recovery lifecycle and initial-download authority | 262–270, 304, 306–307 | `avalanche_driver`, `node_tx`, `offline`, `chronik_sync` |
| 49. `explorer_native` | Expose authenticated native explorer facts | 271–272 | `chronik_sync` |
| 50. `explorer` | Introduce complete schema3 explorer model, durable store, bounded queries and HTTP service | 273–299, 302 | `chronik_db`, `explorer_native`, `chronik_http` |
| 51. `explorer_node` | Isolate schema3 native index and retain unchanged-turn explorer tokens | 300, 303 | `explorer`, `avalanche_node` |

## Explicit ownership corrections

The Argon numeric map is not the source of truth. Actual mailbox payloads establish:

| Mailboxes | Ledger ownership |
| --- | --- |
| 215–217 | `avalanche_core`: native CMake registrations, generated-header includes, translation hook |
| 226 | `peer_store`: native durable peer-store source/test integration |
| 247 | `avalanche_driver`: native driver/test linkage |
| 248, 258 | `chronik_query`: coherent Debug lock definitions and inherited Chronik C++ lock-contract tests, available from Chronik introduction |
| 061 | Signing implementation to `signing`, ordinary consumer to `ordinary`, prepared VM/test work to `vm` |
| 110 | Each whole CMake file diff follows its signing consumer; global validation linkage belongs to `disk` |
| 178–180 | Monetary algebra to `monetary`; complete-block, prototype, genesis and offline consumer changes follow those topics; preview hunk178:01:h1 belongs to `preview` |
| 182 | Wallet/provider monetary fixture file diffs follow their introductions; submission APIs/tests stay in `wallet_submit` |
| 249, 316, 317 | Reorg, dispatcher, wallet/provider, runtime and genesis fixture files follow their owning feature |
| 259, 304, 307, 308 | Quorum/poll, peer, driver and node files follow their corresponding topics, including terminal/late response policy |
| 301 | `avalanche_core`, including the complete update-batch regression project |
| 302 | `explorer`, with service/HTTP/FFI and authority tests |
| 303 | `explorer_node`, preserving stable tokens on unchanged native turns |
| 304–306 | Lifecycle/IBD node work and tests in `avalanche_node`; driver stop/cache behavior/docs in `avalanche_driver` |
| 309, 311–315 | FIFO relay, temporary dispatcher fixtures, application traffic, VM lifetime, pool lookup gate and FD restoration follow their feature topics |

Patch033's `GIT binary patch`/`literal 6892` is preserved in the original mailbox.
The ledger records its exact section digest, resulting CSV blob ID, byte length
and SHA256. `differential_wide.py` remains a caller. Export new mailboxes with
`git format-patch --binary --full-index`; retain the original mailbox byte for
byte in provenance and require the rewritten history to produce the identical
CSV blob. Do not normalize line endings or use a text-only exporter.

## Resolve these blockers before constructing final commits

1. **Shared CMake/source context.** Introduce only the targets, source lists,
   includes and dependencies owned at that boundary. Do not copy a final CMake
   blob containing future features. Reconcile every backward edge, including
   042/110/127/142/154 and the early placement of Chronik Debug definitions.
   Record exact rewritten context and the resulting boundary tree.
2. **Typed API migration and VM ownership.** Patch313 adds noncopyable/nonmovable
   ownership to a class whose original hunk context already contains patch128's
   typed APIs. Preserve the ownership declarations/assertions at `vm` without
   importing typed APIs prematurely; migrate those APIs and consumers together
   at `typed`. Provider depends on `typed`. Compile both boundaries.
3. **Absolute-tail fixtures and complete-block APIs.** Late monetary repair
   files cannot all be moved into the monetary primitive commit. The ledger
   already separates their consumers, including patch178's preview hunk. Check
   every aggregate `MonetaryProfile` initializer when the owning feature appears.
   Preserve existing constants and exact reference/native results; a missing
   fixture repair is a boundary blocker, not permission to invent one silently.
4. **Private client and submission.** Patch315 follows patch182 in the original
   client source. Carry only its scoped stdin/stdout flag-restoration changes to
   the earlier client and apply the submission feature afterward. The client
   and submission topics both require the descriptor regression.
5. **Node lifecycle and explorer authority.** Startup/recovery, stop/cache, IBD
   and terminal peer handling share `development_node_command.cpp` with later
   schema3 namespace/publication changes. Preserve the lifecycle behavior first
   and schema3 tokens afterward; verify exact final bytes plus both topics'
   authority/lifecycle tests. Do not weaken finality or error classification.
6. **Registration discovery.** The ledger statically inventories 44 standalone
   CMake projects and 32 integrated V2 `check-*` targets. It does not expand all
   CMake variables, nested projects, Rust targets or inherited functional variants.
   Configure each actual candidate boundary and discover the complete inventory;
   failed registration or missing tests prevents acceptance.

The JSON includes exact context edges, SCC membership and review obligations
R1–R8. These are unresolved construction/review tasks. A reviewer may approve a
smaller hunk partition or merge related topics when needed. Any ownership change
must rerun the validator below and update the proposed count/dependencies.

## First candidate boundary and concrete conflict procedure

Begin with topic `inherited`: mailboxes000–006,173,253,255–257,260,310,
**64 exact file-diff units**, on the pinned ABC base. The JSON's
`construction_policy.first_boundary` lists those unit IDs. In a new source
checkout, apply only these selected deltas in original ordinal/file order,
record context conflicts, and create one draft commit containing the complete
inherited policy/mining/identity change and its assigned regressions. Do not
apply later feature changes from the source replay. Its expected tree is not yet
known. Capture the constructed tree and configure/build/test evidence before
marking this boundary accepted.

The builder may save unvalidated draft commits while constructing the candidate,
with every gate explicitly pending. That does not waive any intermediate gate
or authorize promotion. Start implementation with this concrete first boundary
rather than waiting to invent a guaranteed final count.

For each subsequent topic, preserve original ordinal/file/hunk order within its
ownership set. If **all** changes to a path belong to the current prefix, its
exact final blob is a safe construction shortcut; otherwise translate only the
owned deltas. Record the source unit, original parent/result blob, rewritten
context and resulting candidate blob. A three-way application is a tool for
finding conflicts, not permission to import unowned future code.

Resolve the three context SCCs as follows:

- **Large native/shared-registration SCC:** construct CMake targets from the
  already introduced source/link/guard changes, then rebase the owned source and
  fixture deltas onto that prefix. Use the enumerated backward edges as the
  work queue. If an owned hunk actually needs a future API, refine its explicit
  hunk ownership/dependency or merge the topics; do not add stubs or a new fix.
- **Client/submission SCC:** construct171/172 with315's scoped flag-restoration
  class and call substitutions, run its descriptor regression, then add182's
  submission interface. Compare the final client blob and rerun the regression.
- **Avalanche-node/explorer-node SCC:** compose startup/recovery, IBD and peer
  outcomes before adding schema3 namespace/token publication. Inspect overlaps
  in startup/poll/stop and authority calls. A real later-service dependency needs
  an explicit hunk reassignment or merged boundary; it cannot be hidden behind
  a provisional authority stub.

After resolving each SCC, update this ledger with the actual candidate trees and
replay results. Context rewriting may change commit boundaries and messages;
source semantics, every original change's ownership and the final tree remain
fixed. An independent reviewer checks the conflict resolutions before accepting
the candidate history.

## Executable construction and verification contract

Construction is a later task in a new isolated checkout from the pinned ABC base.
Preserve the current maintained series and replay evidence. Process topics in
`proposed_order`, loading only their owned original file sections/hunks. Existing
`section_sha256`, `hunk_sha256`, mailbox digest and source-tree provenance make
that selection auditable. Recontextualizing a diff must preserve its owned
behavior and final bytes; unresolved overlaps require review. Never substitute
an entire final file with future-topic changes merely to make a patch apply.

Before finalizing each candidate commit, save its tree and actual target/test
inventory and execute the applicable commands under `verification_recipes` and
that group's `verification`. The recipes use explicit variables, not paths to
production or someone else's active build. Required variables are `SRC`, `BUILD`,
`EVIDENCE`, `BUILD_TYPE`, `CHRONIK`, `PYTHON`, `JOBS`, plus the exact standalone
project/dependency paths. `REFERENCE`, `MONOREPO` and `MANIFEST` must identify the
pinned reference/profile artifacts. Use fresh build/evidence directories for
each boundary/configuration; same-boundary secp/ABC archives for standalone tests.

The required matrix is Debug and Release, each with Chronik OFF and ON, wallet
ON, plugins/Qt/seeder/ZMQ OFF, pinned Rust1.93.0 and Python<=3.13. This defines the
candidate review matrix; it makes no other-platform/plugin/GUI claim. Additional
supported configurations remain explicit final gates, not implicit passes.

At **every** candidate commit:

- Configure and record `cmake --build "$BUILD" --target help` and CTest JSON.
- Build daemon, CLI, wallet tool and native tests; build the V2 wallet pilot/client
  when introduced. Run inherited `check-all` and
  `check-upgrade-activated-extended`, preserving all registered functional variants.
- Run every cumulative V2 custom `check-*` target. CTest alone does not execute
  these custom targets. Run CTest separately.
- Configure/build/run each cumulative standalone project and its registered
  CTest suite. Enable `LOTUS_INITIAL_DOWNLOAD_NATIVE_AUTHORITY=ON` for the real
  authority test; it is not covered by the default lightweight latch test alone.
- With Chronik ON, run the registered CMake `check-crates` target using the exact
  generated CXX bridge and Python environment.
- Run cumulative auxiliary VM/reference/FD/relay queue commands recorded in the
  JSON. Add the pinned node/process scripts' complete documented invocations and
  inputs to their boundary record before acceptance. No node script is run by
  this docs-only task.

Missing tools, failed configuration, empty unexpected inventory, failed tests,
resource limits and timeouts remain failures or unexecuted gates. Neither
omitting tests nor preserving a known broken intermediate boundary satisfies
the requested end state. Merge/repartition a topic or produce a separately
reviewed baseline repair before continuing. Record exact commands and logs;
`boundary_status` remains unbuilt until evidence exists.

Finally export the candidate and replay it in a second fresh checkout, comparing
every recorded candidate boundary tree and the exact final tree above. Compare
all blobs/modes, including patch033's binary fixture. Independently review the
ledger, source attribution, all intermediate build/test evidence and equality.
Do not replace the active manifest or publish merely because coverage/count
validation passes. Source changes, prototype retirement, resource calibration
and semantic fixes remain separate reviewed work.

## Reproduce the docs/data validation

Run the following from the pinned monorepo root. It checks manifest/evidence
hashes, all 318 mailbox records, every original file/hunk ownership unit, the
proposed DAG, binary-section retention and registration references. It writes
nothing and runs no builds or nodes.

```python
from pathlib import Path
import collections
import hashlib
import json
import re

root = Path.cwd()
ledger = json.loads((root / "docs/plans/lotus-v2-consolidation-ledger.json").read_text())
digest = lambda data: hashlib.sha256(data).hexdigest()
manifest_path = root / ledger["source_manifest"]
evidence_path = root / ledger["replay_evidence"]
assert digest(manifest_path.read_bytes()) == ledger["source_manifest_sha256"]
assert digest(evidence_path.read_bytes()) == ledger["replay_evidence_sha256"]
names = [s for s in manifest_path.read_text().splitlines() if s and not s.startswith("#")]
evidence = json.loads(evidence_path.read_text())
assert len(names) == len(ledger["mailboxes"]) == 318
assert evidence["base"] == ledger["base_commit"]
assert evidence["final_tree"] == ledger["expected_final_tree"]
groups = {g["id"]: g for g in ledger["groups"]}
order = ledger["proposed_order"]
assert len(groups) == len(order) == ledger["proposed_group_count"] == 51
assert set(order) == set(groups)
positions = {g: i for i, g in enumerate(order)}
for gid, group in groups.items():
    assert group["proposed_position"] == positions[gid] + 1
    assert all(positions[d] < positions[gid] for d in group["depends_on"])
    assert group["result_tree"] is None  # This is an unexecuted design ledger.
units = {}
for n, (name, entry, recorded) in enumerate(zip(names, ledger["mailboxes"], evidence["entries"])):
    assert entry["ordinal"] == int(name[:3]) == n
    assert name == entry["mailbox"] == recorded["file"]
    raw = (manifest_path.parent / name).read_bytes()
    assert digest(raw) == entry["mailbox_sha256"] == recorded["sha256"]
    assert entry["original_result_tree"] == recorded["tree"]
    markers = list(re.finditer(rb"^diff --git a/(.+?) b/(.+)$", raw, re.M))
    partition = collections.defaultdict(list)
    for unit in entry["units"]:
        assert unit["id"] not in units
        units[unit["id"]] = unit
        parent = unit.get("parent_section_id", unit["id"])
        partition[parent].append(unit)
    assert set(partition) == {f"{n:03}:{j:02}" for j in range(len(markers))}
    for j, marker in enumerate(markers):
        end = markers[j + 1].start() if j + 1 < len(markers) else len(raw)
        section = raw[marker.start():end]
        if j + 1 == len(markers) and b"\n-- \n" in section:
            section = section[:section.rfind(b"\n-- \n") + 1]
        owned = partition[f"{n:03}:{j:02}"]
        for unit in owned:
            assert unit["path"] == marker.group(2).decode()
            assert unit["section_sha256"] == digest(section)
            assert unit["binary"] == (b"GIT binary patch" in section)
            assert unit["group"] in groups
        if owned[0]["ownership"] == "whole_file_diff":
            assert len(owned) == 1
        else:
            hunks = list(re.finditer(rb"^@@.*?@@.*$", section, re.M))
            assert sorted(u["hunk_index"] for u in owned) == list(range(len(hunks)))
            for unit in owned:
                k = unit["hunk_index"]
                stop = hunks[k + 1].start() if k + 1 < len(hunks) else len(section)
                assert unit["ownership"] == "hunk"
                assert unit["hunk_sha256"] == digest(section[hunks[k].start():stop])
assigned = [u for group in groups.values() for u in group["units"]]
assert len(assigned) == len(set(assigned)) == len(units) == 1053
assert set(assigned) == set(units)
for gid, group in groups.items():
    assert all(units[u]["group"] == gid for u in group["units"])
for edge in ledger["unresolved"]["patch_context_edges"]:
    assert edge["before_unit"] in units and edge["after_unit"] in units
    assert edge["order_reversed"] == (positions[edge["before_group"]] > positions[edge["after_group"]])
assert not ledger["unresolved"]["file_introduction_conflicts"]
binary = ledger["binary_preservation"]
assert units[binary["unit"]]["binary"]
assert units[binary["unit"]]["section_sha256"] == binary["section_sha256"]
assert binary["bytes"] == 6892
assert all(p["introduced_by_group"] in groups for p in ledger["registration_catalog"]["standalone_projects"])
assert all(c["introduced_by_group"] in groups for c in ledger["registration_catalog"]["lotus_checks"])
print("PASS: 318 mailboxes; 1051 file diffs; 1053 exclusive units; 51 proposed topics; source hashes and DAG valid.")
print("NOT RUN: candidate replay, per-boundary builds/tests, final candidate tree comparison.")
```

The source replay's CSV was also read by its exact Git blob and checked against
the recorded SHA256/length during ledger preparation. No new candidate source
or build evidence was generated. Independent review is required before treating
this design as an approved construction plan.
